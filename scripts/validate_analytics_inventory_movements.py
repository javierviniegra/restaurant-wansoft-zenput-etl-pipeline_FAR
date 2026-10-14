"""
Validate analytics_inventory_movements (Wansoft side) against its source tables.

For every branch and source (entries / exits) since --since:
1. rows: source rows (main table + parallel rows the main table does not
   have, same identity as the build) == movement rows;
2. quantity: the same, summed (exits negative in the movements table);
3. status: no branch-day counted from both main history and parallel
   (wansoft_parallel_after_odoo only from the branch's Odoo start date).
4. Odoo side (--odoo-stock-date): per branch x Odoo product, the sum of the
   storable movements written before Odoo's daily capture equals that
   capture (odoo_inventory_quant_daily, internal locations). Reported, not
   failed: Antenas (the 2024 prototype) carries stock in Odoo that is not
   the sum of its own moves.
Prints only the differences, then PASS / FAIL. Read-only.

    python -m scripts.validate_analytics_inventory_movements --since 2026-09-01
    python -m scripts.validate_analytics_inventory_movements --since 2026-09-01 --odoo-stock-date 2026-10-13
"""
import argparse

from core.database.mysql import get_db_connection

TABLE = "analytics_inventory_movements"
MEXICO_CITY_TO_UTC_HOURS = 6  # captured_at is Mexico City time; odoo_write_date is UTC

SOURCES = [
    # record, main, parallel, same-row condition (indexed), business date, sign
    ("wansoft_entrada", "getinputinventory_entrada", "wansoft_parallel_inputinventory_entrada",
     "m.IdEntrada = s.IdEntrada", "DATE(s.FechaEntrada)", 1),
    ("wansoft_salida", "getoutgoinginventory_salida", "wansoft_parallel_outgoinginventory_salida",
     "m.Fecha <=> s.Fecha AND m.IdSalida = s.IdSalida", "COALESCE(NULLIF(s.Fecha, '0000-00-00'), s.FechaReal)", -1),
]


def source_totals(cur, main, parallel, same_row, date_expr, sign, since):
    """(subsidiary, rows, quantity) of main + parallel-only rows since `since`."""
    cur.execute(f"""
        SELECT subsidiary_name, COUNT(*), SUM(qty) FROM (
            SELECT s.subsidiary_name, {sign} * s.Cantidad AS qty
            FROM {main} s WHERE {date_expr} >= %s
            UNION ALL
            SELECT s.subsidiary_name, {sign} * s.Cantidad
            FROM {parallel} s
            WHERE {date_expr} >= %s
              AND NOT EXISTS (SELECT 1 FROM {main} m
                              WHERE m.subsidiary_name = s.subsidiary_name AND {same_row})
        ) x GROUP BY subsidiary_name
    """, (since, since))
    return {row[0]: (row[1], float(row[2] or 0)) for row in cur.fetchall()}


def odoo_vs_capture(cur, stock_date):
    """Odoo side against Odoo's own stock capture of stock_date (see docstring, 4)."""
    cur.execute("SELECT MAX(captured_at) FROM odoo_inventory_quant_daily WHERE stock_date = %s", (stock_date,))
    captured_at = cur.fetchone()[0]
    if captured_at is None:
        print(f"Odoo: no hay foto de existencias para {stock_date}")
        return
    cur.execute(f"""
        CREATE TEMPORARY TABLE tmp_val_moves (PRIMARY KEY (k, pid))
        SELECT m.company_source_key k, m.odoo_product_id pid, SUM(m.quantity) qty
        FROM {TABLE} m JOIN odoo_stock_move_snapshot s ON s.odoo_move_id = m.source_movement_id
        WHERE m.source_system = 'odoo' AND m.counts_in_stock = 1
          AND s.odoo_write_date <= %s + INTERVAL {MEXICO_CITY_TO_UTC_HOURS} HOUR
        GROUP BY 1, 2
    """, (captured_at,))
    cur.execute("""
        CREATE TEMPORARY TABLE tmp_val_quant (PRIMARY KEY (k, pid))
        SELECT company_source_key k, odoo_product_id pid, SUM(quantity) qty
        FROM odoo_inventory_quant_daily
        WHERE stock_date = %s AND location_usage = 'internal' AND company_source_key IS NOT NULL
        GROUP BY 1, 2
    """, (stock_date,))
    cur.execute("""
        SELECT k, COUNT(*), SUM(ABS(dif) < 0.01), SUM(ABS(dif) >= 0.01), ROUND(SUM(ABS(dif)), 2)
        FROM (SELECT a.k, a.pid, a.qty - COALESCE(q.qty, 0) dif FROM tmp_val_moves a LEFT JOIN tmp_val_quant q USING (k, pid)
              UNION ALL
              SELECT q.k, q.pid, -q.qty FROM tmp_val_quant q LEFT JOIN tmp_val_moves a USING (k, pid) WHERE a.pid IS NULL) x
        GROUP BY k ORDER BY k
    """)
    print(f"Odoo contra su foto de existencias del {stock_date} (tomada {captured_at}):")
    print("  sucursal | productos | exactos | distintos | suma |diferencia|")
    for row in cur.fetchall():
        print("  ", row)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--since", required=True, help="business date to start from, YYYY-MM-DD")
    parser.add_argument("--odoo-stock-date", help="also compare the Odoo side with Odoo's capture of this stock date")
    args = parser.parse_args(argv)

    from core.config.companies import WANSOFT_SUBSIDIARY_SOURCE_KEY
    key_by_subsidiary = WANSOFT_SUBSIDIARY_SOURCE_KEY
    conn = get_db_connection()
    cur = conn.cursor()
    failures = 0
    for record, main_table, parallel, same_row, date_expr, sign in SOURCES:
        source = source_totals(cur, main_table, parallel, same_row, date_expr, sign, args.since)
        cur.execute(f"""
            SELECT company_source_key, COUNT(*), SUM(quantity) FROM {TABLE}
            WHERE source_record = %s AND movement_date >= %s GROUP BY 1
        """, (record, args.since))
        target = {row[0]: (row[1], float(row[2] or 0)) for row in cur.fetchall()}
        checked = 0
        for subsidiary, (rows, qty) in sorted(source.items()):
            key = key_by_subsidiary.get(subsidiary)
            if key is None:
                print(f"  [{record}] sucursal {subsidiary} fuera de la configuración: {rows:,} filas no cargadas")
                continue
            got_rows, got_qty = target.pop(key, (0, 0.0))
            checked += 1
            if got_rows != rows or abs(got_qty - qty) > 0.001:
                failures += 1
                print(f"  [FAIL {record}] {key}: origen {rows:,} filas / {qty:,.3f}  tabla {got_rows:,} / {got_qty:,.3f}")
        for key, (rows, _) in target.items():
            failures += 1
            print(f"  [FAIL {record}] {key}: {rows:,} filas en la tabla sin origen")
        print(f"{record}: {checked} sucursales comparadas")

    cur.execute(f"""
        SELECT company_source_key, movement_date, COUNT(DISTINCT final_source_status)
        FROM {TABLE}
        WHERE source_system = 'wansoft' AND movement_date >= %s
          AND final_source_status IN ('wansoft_history_before_odoo', 'wansoft_parallel_after_odoo')
        GROUP BY 1, 2 HAVING COUNT(DISTINCT final_source_status) > 1
    """, (args.since,))
    mixed = cur.fetchall()
    for row in mixed:
        failures += 1
        print(f"  [FAIL estado] {row[0]} {row[1]}: el mismo día como historia y como paralelo")
    cur.execute(f"""
        SELECT final_source_status, include_in_business_views, COUNT(*), MIN(movement_date), MAX(movement_date)
        FROM {TABLE} WHERE source_system = 'wansoft' AND movement_date >= %s GROUP BY 1, 2
    """, (args.since,))
    for row in cur.fetchall():
        print("  estado:", row)
    if args.odoo_stock_date:
        odoo_vs_capture(cur, args.odoo_stock_date)
    conn.close()
    print("RESULTADO:", "PASS" if failures == 0 else f"FAIL ({failures})")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
