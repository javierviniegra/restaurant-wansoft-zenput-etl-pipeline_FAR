"""
Build analytics_inventory_movements: one row per inventory movement of one
product in one branch, Wansoft and Odoo together, with their whole history
(design: docs/analytics-inventory-unified-design.md, Table 1, approved by the
owner on 2026-10-13).

Wansoft side (this block):
- Sources: getinputinventory_entrada / getoutgoinginventory_salida (main) and
  wansoft_parallel_inputinventory_entrada / wansoft_parallel_outgoinginventory_salida
  (what the Odoo branches keep capturing in Wansoft). The main tables load
  first; a parallel row with the same identity changes nothing. The parallel
  tables also hold September rows missing from the main tables (captured
  after the main load stopped for those branches); those enter here.
- Identity of a row = the loaders' own: entries IdEntrada per branch, exits
  Fecha + IdSalida per branch (Fecha is NULL on adjustments and waste, whose
  date is FechaReal; IdSalida alone is unique among them).
- movement_type / counts_in_stock: the catalog approved on 2026-10-13
  (counts_in_stock reproduces analytics_inventory_balance). A type not in the
  catalog becomes 'other' and counts, and is reported.
- final_source_status: 'wansoft_final' for a branch on Wansoft;
  'wansoft_history_before_odoo' before an Odoo branch's start date
  (odoo_company_migration_policy.operational_start_date) and
  'wansoft_parallel_after_odoo' from it (include_in_business_views = 0).

Odoo side (odoo_stock_move_snapshot, done moves with valuation):
- One row per move and branch it touches: 'out' for the branch whose internal
  location is the source, 'in' for the branch whose internal location is the
  destination. A move between two locations of the same branch (Almacen ->
  Cocina) is not stored (owner, 2026-10-13). Internal providers (El Bodegon,
  Las Empanadas) are not branches and are left out, as in purchases.
- movement_type from the other side's location usage: customer -> sale,
  supplier -> purchase receipt, production -> production in/out, inventory ->
  adjustment (waste when scrapped), another branch or transit -> transfer.
- quantity = done_qty (the product's unit), total_cost = the valuation layers'
  value, both signed; counts_in_stock = product_is_storable.
- wansoft_code from the approved dictionary mapping when the Odoo product has
  exactly one and it is not under review (EXCLUDED_DICTIONARY_IDS);
  product_code / product_code_status (generated columns) carry the Wansoft
  code or a temporary ODOO-<id> until the weekly name matcher maps it.
- final_source_status: 'odoo_final' for an Odoo branch from its start date,
  'odoo_parallel_before_start' otherwise (include_in_business_views = 0).
- Rebuilt in full on every run (about 1.6 M moves).

Runs inside MySQL (INSERT ... SELECT): a full rebuild by ranges of the source
tables' primary key; the nightly window by capture date (Wansoft).

    python -m scripts.build_analytics_inventory_movements --full      # rebuild everything
    python -m scripts.build_analytics_inventory_movements             # nightly window
    python -m scripts.build_analytics_inventory_movements --window-days 10
"""
import argparse
import time
from datetime import date, timedelta

from core.config.companies import COMPANY_SOURCE, WANSOFT_SUBSIDIARY_SOURCE_KEY, get_company_source_key
from core.database.mysql import get_db_connection

TABLE = "analytics_inventory_movements"
DEFAULT_WINDOW_DAYS = 10
ODOO_SOURCE = "odoo_stock_move_snapshot"
# Approved mappings whose Odoo id is another product but is in use in 2026;
# waiting for the owner's review (reports/inventory_mapping_review/
# revision_mapeos_odoo_wansoft_20261013.xlsx). Their moves keep odoo_product_id
# and get no wansoft_code until then.
EXCLUDED_DICTIONARY_IDS = (70, 120, 138, 144, 189, 233, 243, 262, 291, 346, 352, 485, 1346)
CHUNK = 200_000  # source primary-key ids per statement in a full rebuild

# (TipoEntrada / TipoSalida) -> (movement_type, counts_in_stock); owner, 2026-10-13
ENTRY_TYPES = {
    "Factura": ("purchase_receipt", 1),
    "Transferencia": ("transfer_in", 0),
    "Entrada con canal": ("production_in", 1),
    "Ajuste de inventario": ("adjustment", 1),
    "Producto procesado": ("production_in", 1),
    "Orden de compra a proveedor": ("other", 0),
    "Inventario inicial": ("initial_inventory", 1),
    "Eliminado por ajuste de lote": ("adjustment", 1),
    "Anulación": ("other", 1),
    "Ajuste por lote": ("adjustment", 1),
    "Cancelación de transferencia": ("other", 1),
    "Devolución": ("other", 1),
}
EXIT_TYPES = {
    "Venta": ("sale_consumption", 1),
    "Transferencia": ("transfer_out", 0),
    "Producción de subproducto": ("production_out", 1),
    "Merma": ("waste", 1),
    "Producción de subproducto con canal": ("production_out", 1),
    "Consumo": ("consumption", 1),
    "Ajuste de inventario": ("adjustment", 1),
    "Venta cancelada": ("sale_cancellation", 1),
    "Ajuste por lote": ("adjustment", 1),
    "Error de captura": ("other", 0),
    "Desperdicio": ("waste", 1),
    "Devolución de producto": ("other", 1),
    "Registro de nota de crédito": ("other", 1),
    "Factura de egresos rechazada": ("other", 0),
    "Robo": ("theft", 1),
}

DDL = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    movement_key              BIGINT AUTO_INCREMENT PRIMARY KEY,
    movement_date             DATE NOT NULL,
    company_source_key        VARCHAR(100) NOT NULL,
    source_system             VARCHAR(10)  NOT NULL,
    source_record             VARCHAR(20)  NOT NULL,
    source_movement_id        VARCHAR(80)  NOT NULL,
    captured_date             DATE NULL,
    direction                 CHAR(3)      NOT NULL,
    movement_type             VARCHAR(20)  NOT NULL,
    source_movement_type      VARCHAR(100) NULL,
    wansoft_code              VARCHAR(50)  NULL,
    odoo_product_id           INT          NULL,
    product_name              VARCHAR(255) NULL,
    unit_name                 VARCHAR(50)  NULL,
    quantity                  DECIMAL(18,6) NOT NULL,
    unit_cost                 DECIMAL(18,6) NULL,
    total_cost                DECIMAL(18,4) NULL,
    location_name             VARCHAR(255) NULL,
    counts_in_stock           TINYINT(1)   NOT NULL,
    final_source_status       VARCHAR(40)  NOT NULL,
    include_in_business_views TINYINT(1)   NOT NULL,
    loaded_at                 DATETIME     NOT NULL,
    -- One product code for both systems (owner, 2026-10-14): the Wansoft code,
    -- or a temporary ODOO-<id> while the Odoo product has no approved mapping.
    -- Computed by MySQL, so a mapping approved later reaches every row on the
    -- next rebuild of the Odoo side.
    product_code              VARCHAR(60) AS (COALESCE(wansoft_code,
                                  IF(source_system = 'odoo', CONCAT('ODOO-', odoo_product_id), NULL))) STORED,
    product_code_status       VARCHAR(15) AS (CASE WHEN wansoft_code IS NOT NULL THEN 'wansoft'
                                  WHEN source_system = 'odoo' THEN 'temporal_odoo' ELSE 'sin_codigo' END) STORED,
    UNIQUE KEY uq_movement (source_record, company_source_key, source_movement_id),
    KEY idx_company_date (company_source_key, movement_date),
    KEY idx_product_date (product_code, movement_date),
    KEY idx_captured (source_system, captured_date)
)
"""

# Per source table: how each column of the target is read.
WANSOFT_SOURCES = [
    {
        "label": "entradas",
        "table": "getinputinventory_entrada",
        "record": "wansoft_entrada",
        "direction": "in",
        "sign": "",
        "type_col": "TipoEntrada",
        "types": ENTRY_TYPES,
        "id_expr": "s.IdEntrada",
        "date_expr": "DATE(s.FechaEntrada)",
        "captured_expr": "DATE(s.FechaEntrada)",
        "window_col": "s.FechaEntrada",  # indexed (sql/migrations/inventory_capture_date_indexes.sql)
    },
    {
        "label": "salidas",
        "table": "getoutgoinginventory_salida",
        "record": "wansoft_salida",
        "direction": "out",
        "sign": "-",
        "type_col": "TipoSalida",
        "types": EXIT_TYPES,
        "id_expr": "CONCAT(COALESCE(s.Fecha, ''), '|', s.IdSalida)",  # Fecha is NULL on adjustments/waste
        "date_expr": "COALESCE(NULLIF(s.Fecha, '0000-00-00'), s.FechaReal)",
        "captured_expr": "DATE(s.FechaSalida)",
        "window_col": "s.FechaSalida",  # indexed (sql/migrations/inventory_capture_date_indexes.sql)
    },
]
PARALLEL_TABLES = {
    "getinputinventory_entrada": "wansoft_parallel_inputinventory_entrada",
    "getoutgoinginventory_salida": "wansoft_parallel_outgoinginventory_salida",
}

UPDATE_COLUMNS = [
    "movement_date", "captured_date", "direction", "movement_type", "source_movement_type",
    "wansoft_code", "product_name", "unit_name", "quantity", "unit_cost", "total_cost",
    "location_name", "counts_in_stock", "final_source_status", "include_in_business_views", "loaded_at",
]


def load_branches(cur):
    """Wansoft subsidiary id -> (company_source_key, Odoo start date or None)."""
    cur.execute("SELECT company_name, operational_start_date FROM odoo_company_migration_policy WHERE is_active = 1")
    starts = {}
    for company_name, start in cur.fetchall():
        key = get_company_source_key(company_name)
        if key:
            starts[key] = start
    branches = {}
    for subsidiary_id, key in WANSOFT_SUBSIDIARY_SOURCE_KEY.items():
        start = starts.get(key) if COMPANY_SOURCE.get(key) == "odoo" else None
        branches[subsidiary_id] = (key, start)
    return branches


def create_helper_tables(cur, branches):
    cur.execute("DROP TEMPORARY TABLE IF EXISTS tmp_aim_branch")
    cur.execute(
        "CREATE TEMPORARY TABLE tmp_aim_branch ("
        " subsidiary_name VARCHAR(255) PRIMARY KEY, company_source_key VARCHAR(100), odoo_start_date DATE NULL)"
    )
    cur.executemany(
        "INSERT INTO tmp_aim_branch VALUES (%s, %s, %s)",
        [(sid, key, start) for sid, (key, start) in branches.items()],
    )
    cur.execute("DROP TEMPORARY TABLE IF EXISTS tmp_aim_type")
    cur.execute(
        "CREATE TEMPORARY TABLE tmp_aim_type ("
        " source_record VARCHAR(20), source_type VARCHAR(100), movement_type VARCHAR(20), counts_in_stock TINYINT(1),"
        " PRIMARY KEY (source_record, source_type))"
    )
    rows = [("wansoft_entrada", t, m, c) for t, (m, c) in ENTRY_TYPES.items()]
    rows += [("wansoft_salida", t, m, c) for t, (m, c) in EXIT_TYPES.items()]
    cur.executemany("INSERT INTO tmp_aim_type VALUES (%s, %s, %s, %s)", rows)


def wansoft_insert_sql(src, table, mode):
    """INSERT ... SELECT for one Wansoft source table, one branch, one date range.

    mode 'upsert' (main tables: their values win) or 'ignore' (parallel
    tables: only rows the main tables do not have)."""
    date_expr = src["date_expr"]
    status = (
        f"CASE WHEN b.odoo_start_date IS NULL THEN 'wansoft_final' "
        f"WHEN {date_expr} < b.odoo_start_date THEN 'wansoft_history_before_odoo' "
        f"ELSE 'wansoft_parallel_after_odoo' END"
    )
    verb = "INSERT IGNORE INTO" if mode == "ignore" else "INSERT INTO"
    sql = f"""
        {verb} {TABLE} (
            movement_date, company_source_key, source_system, source_record, source_movement_id,
            captured_date, direction, movement_type, source_movement_type, wansoft_code,
            odoo_product_id, product_name, unit_name, quantity, unit_cost, total_cost,
            location_name, counts_in_stock, final_source_status, include_in_business_views, loaded_at
        )
        SELECT
            {date_expr},
            b.company_source_key,
            'wansoft',
            '{src["record"]}',
            {src["id_expr"]},
            {src["captured_expr"]},
            '{src["direction"]}',
            COALESCE(t.movement_type, 'other'),
            s.{src["type_col"]},
            NULLIF(s.CodigoProducto, ''),
            NULL,
            s.NombreProducto,
            s.UnidadDeMedida,
            {src["sign"]}s.Cantidad,
            s.CostoUnitario,
            {src["sign"]}s.Cantidad * s.CostoUnitario,
            s.Almacen,
            COALESCE(t.counts_in_stock, 1),
            {status},
            ({status}) <> 'wansoft_parallel_after_odoo',
            NOW()
        FROM {table} s
        JOIN tmp_aim_branch b ON b.subsidiary_name = s.subsidiary_name
        LEFT JOIN tmp_aim_type t ON t.source_record = '{src["record"]}' AND t.source_type = s.{src["type_col"]}
        WHERE {{where}}
    """
    if mode == "upsert":
        sql += " ON DUPLICATE KEY UPDATE " + ", ".join(f"{c} = VALUES({c})" for c in UPDATE_COLUMNS)
    return sql


def id_chunks(cur, table):
    """[from, to) ranges of the source table's primary key, CHUNK ids each."""
    cur.execute(f"SELECT MIN(id), MAX(id) FROM {table}")
    low, high = cur.fetchone()
    if low is None:
        return
    for first in range(low, high + 1, CHUNK):
        yield first, first + CHUNK


def load_wansoft(conn, window_start=None):
    """Full rebuild (window_start None): every source row, by primary-key
    ranges. Nightly: rows captured since window_start, one statement per
    table (a scan of the table, no per-branch loop)."""
    cur = conn.cursor()
    totals = {}
    for src in WANSOFT_SOURCES:
        for table, mode in ((src["table"], "upsert"), (PARALLEL_TABLES[src["table"]], "ignore")):
            started, rows = time.time(), 0
            if window_start is None:
                sql = wansoft_insert_sql(src, table, mode).replace("{where}", "s.id >= %s AND s.id < %s")
                for first, last in id_chunks(cur, table):
                    cur.execute(sql, (first, last))
                    rows += cur.rowcount
                    conn.commit()
            else:
                # Same rows as DATE(col) >= window_start, but able to use the index.
                where = f"{src['window_col']} >= %s"
                sql = wansoft_insert_sql(src, table, mode).replace("{where}", where)
                cur.execute(sql, (window_start,))
                rows += cur.rowcount
                conn.commit()
            totals[table] = rows
            print(f"  {table}: {rows:,} filas afectadas ({time.time() - started:.0f} s)")
    cur.close()
    return totals


def create_odoo_helpers(cur):
    """Odoo company -> branch with its start date; Odoo product -> one Wansoft code."""
    cur.execute(f"SELECT DISTINCT odoo_company_id, company_source_key FROM {ODOO_SOURCE} WHERE company_source_key IS NOT NULL")
    companies = cur.fetchall()
    cur.execute("SELECT odoo_company_id, operational_start_date FROM odoo_company_migration_policy WHERE is_active = 1")
    starts = dict(cur.fetchall())
    cur.execute("DROP TEMPORARY TABLE IF EXISTS tmp_aim_odoo_company")
    cur.execute(
        "CREATE TEMPORARY TABLE tmp_aim_odoo_company ("
        " odoo_company_id INT PRIMARY KEY, company_source_key VARCHAR(100), odoo_start_date DATE NULL, is_odoo_branch TINYINT(1))"
    )
    cur.executemany(
        "INSERT INTO tmp_aim_odoo_company VALUES (%s, %s, %s, %s)",
        [(cid, key, starts.get(cid), int(COMPANY_SOURCE.get(key) == "odoo")) for cid, key in companies],
    )
    cur.execute("DROP TEMPORARY TABLE IF EXISTS tmp_aim_odoo_product")
    cur.execute(f"""
        CREATE TEMPORARY TABLE tmp_aim_odoo_product (PRIMARY KEY (odoo_product_id))
        SELECT odoo_product_id, MIN(wansoft_code) AS wansoft_code
        FROM inventory_mapping_dictionary
        WHERE mapping_status = 'approved' AND odoo_product_id IS NOT NULL
          AND wansoft_code IS NOT NULL AND wansoft_code <> ''
          AND id NOT IN ({",".join(["%s"] * len(EXCLUDED_DICTIONARY_IDS))})
        GROUP BY odoo_product_id
        HAVING COUNT(DISTINCT wansoft_code) = 1
    """, EXCLUDED_DICTIONARY_IDS)


def odoo_insert_sql(direction):
    """INSERT ... SELECT of the 'out' or 'in' side of Odoo moves, one id range."""
    if direction == "out":
        here, other, sign = "location", "location_dest", "-"
        mtype = """CASE m.location_dest_usage
            WHEN 'customer' THEN 'sale_consumption' WHEN 'production' THEN 'production_out'
            WHEN 'inventory' THEN IF(m.scrapped = 1, 'waste', 'adjustment')
            WHEN 'transit' THEN 'transfer_out' WHEN 'internal' THEN 'transfer_out' ELSE 'other' END"""
    else:
        here, other, sign = "location_dest", "location", ""
        mtype = """CASE m.location_usage
            WHEN 'supplier' THEN 'purchase_receipt' WHEN 'production' THEN 'production_in'
            WHEN 'inventory' THEN 'adjustment'
            WHEN 'transit' THEN 'transfer_in' WHEN 'internal' THEN 'transfer_in' ELSE 'other' END"""
    status = ("CASE WHEN c.is_odoo_branch = 1 AND c.odoo_start_date IS NOT NULL "
              "AND m.movement_date >= c.odoo_start_date THEN 'odoo_final' ELSE 'odoo_parallel_before_start' END")
    return f"""
        INSERT INTO {TABLE} (
            movement_date, company_source_key, source_system, source_record, source_movement_id,
            captured_date, direction, movement_type, source_movement_type, wansoft_code,
            odoo_product_id, product_name, unit_name, quantity, unit_cost, total_cost,
            location_name, counts_in_stock, final_source_status, include_in_business_views, loaded_at
        )
        SELECT
            m.movement_date,
            c.company_source_key,
            'odoo',
            'odoo_move',
            m.odoo_move_id,
            DATE(m.odoo_write_date),
            '{direction}',
            {mtype},
            LEFT(CONCAT(m.location_usage, ' -> ', m.location_dest_usage,
                        IFNULL(CONCAT(' (', m.picking_type_name, ')'), '')), 100),
            p.wansoft_code,
            m.odoo_product_id,
            LEFT(m.product_display_name, 255),
            LEFT(m.product_uom_name, 50),
            {sign}m.done_qty,
            CASE WHEN m.valuation_layer_count > 0 AND COALESCE(m.valuation_qty, 0) <> 0
                 THEN ABS(m.valuation_value / m.valuation_qty) ELSE m.price_unit END,
            {sign}ABS(m.valuation_value),
            LEFT(m.{here}_name, 255),
            m.product_is_storable,
            {status},
            ({status}) = 'odoo_final',
            NOW()
        FROM {ODOO_SOURCE} m
        JOIN tmp_aim_odoo_company c ON c.odoo_company_id = COALESCE(m.{here}_company_id, m.odoo_company_id)
        LEFT JOIN tmp_aim_odoo_product p ON p.odoo_product_id = m.odoo_product_id
        WHERE m.{here}_usage = 'internal'
          AND NOT (m.{other}_usage = 'internal'
                   AND COALESCE(m.{other}_company_id, m.odoo_company_id) = COALESCE(m.{here}_company_id, m.odoo_company_id))
          AND m.odoo_move_id >= %s AND m.odoo_move_id < %s
    """


def load_odoo(conn):
    """Odoo side, rebuilt in full (deleted and reinserted by move-id ranges)."""
    cur = conn.cursor()
    create_odoo_helpers(cur)
    started = time.time()
    cur.execute(f"DELETE FROM {TABLE} WHERE source_system = 'odoo'")
    conn.commit()
    print(f"  borrado del lado Odoo: {cur.rowcount:,} filas ({time.time() - started:.0f} s)")
    cur.execute(f"SELECT MIN(odoo_move_id), MAX(odoo_move_id) FROM {ODOO_SOURCE}")
    low, high = cur.fetchone()
    for direction in ("out", "in"):
        started, rows = time.time(), 0
        sql = odoo_insert_sql(direction)
        for first in range(low or 0, (high or -1) + 1, CHUNK):
            cur.execute(sql, (first, first + CHUNK))
            rows += cur.rowcount
            conn.commit()
        print(f"  {ODOO_SOURCE} ({direction}): {rows:,} filas ({time.time() - started:.0f} s)")
    cur.close()


def report(conn, since=None):
    """Summary of the table. Nightly (since = window start): only the Wansoft
    rows captured in the window plus the Odoo side, through idx_captured, so
    it does not scan the ~40 M rows every night."""
    started = time.time()
    cur = conn.cursor()
    scope = "" if since is None else (
        "WHERE (source_system = 'wansoft' AND captured_date >= %(since)s) OR source_system = 'odoo'")
    wansoft_scope = "" if since is None else "AND captured_date >= %(since)s"
    params = {"since": since}
    cur.execute(f"""
        SELECT source_record, final_source_status, include_in_business_views, COUNT(*), MIN(movement_date), MAX(movement_date)
        FROM {TABLE} {scope} GROUP BY 1, 2, 3 ORDER BY 1, 2
    """, params)
    print("Resumen por origen y estado:" if since is None else f"Resumen (Wansoft capturado desde {since} + Odoo):")
    for row in cur.fetchall():
        print("  ", row)
    cur.execute(f"""
        SELECT source_record, source_movement_type, COUNT(*) FROM {TABLE}
        WHERE source_system = 'wansoft' {wansoft_scope} GROUP BY 1, 2
    """, params)
    catalog = {"wansoft_entrada": ENTRY_TYPES, "wansoft_salida": EXIT_TYPES}
    unknown = [row for row in cur.fetchall() if row[1] not in catalog[row[0]]]
    if unknown:
        print("[AVISO] Tipos de Wansoft fuera del catálogo (cargados como 'other', cuentan en existencias):")
        for row in unknown:
            print("  ", row)
    cur.execute(f"""
        SELECT COUNT(*), COUNT(DISTINCT odoo_product_id) FROM {TABLE}
        WHERE source_system = 'odoo' AND final_source_status = 'odoo_final'
          AND counts_in_stock = 1 AND wansoft_code IS NULL
    """)
    rows, products = cur.fetchone()
    print(f"Odoo final almacenable sin código Wansoft: {rows:,} filas de {products:,} productos (se ven por odoo_product_id)")
    print(f"  resumen: {time.time() - started:.0f} s")
    cur.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--full", action="store_true", help="rebuild the whole history")
    parser.add_argument("--window-days", type=int, default=DEFAULT_WINDOW_DAYS, help="nightly window, by capture date")
    args = parser.parse_args(argv)

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(DDL)
        branches = load_branches(cur)
        create_helper_tables(cur, branches)
        today = date.today()
        window_start = None
        if args.full:
            print(f"Reconstrucción completa de {TABLE} (lado Wansoft)")
            cur.execute(f"DELETE FROM {TABLE} WHERE source_system = 'wansoft'")
            conn.commit()
            load_wansoft(conn)
            print("Reconstrucción del lado Odoo")
            load_odoo(conn)
        else:
            window_start = today - timedelta(days=args.window_days)
            print(f"Ventana nocturna de {TABLE} (lado Wansoft): capturado desde {window_start}")
            started = time.time()
            cur.execute(f"DELETE FROM {TABLE} WHERE source_system = 'wansoft' AND captured_date >= %s", (window_start,))
            conn.commit()
            print(f"  borrado de la ventana Wansoft: {cur.rowcount:,} filas ({time.time() - started:.0f} s)")
            load_wansoft(conn, window_start)
            print("Reconstrucción del lado Odoo")
            load_odoo(conn)
        cur.close()
        report(conn, None if args.full else window_start)
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
