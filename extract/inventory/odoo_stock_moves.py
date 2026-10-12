"""
Odoo stock moves with their valuation (unified inventory design, step 1:
docs/analytics-inventory-unified-design.md).

Loads every DONE stock.move of the group's companies (branches and internal
providers) into odoo_stock_move_snapshot, one row per move, with the sum of
its stock.valuation.layer rows (quantity and value in pesos). All moves since
each company's first one are kept, not only those after its Odoo start date:
Odoo's stock on a day is the sum of every move up to it (the migrated
branches captured in Odoo in parallel since June), so the full history is
what makes the stock rebuildable. The unified movements table applies the
start-date rule later.

Incremental: the first run reads everything; later runs read the moves
written since the last load (minus a safety margin) plus the moves that got
new valuation layers (landed costs, revaluations). Rows are upserted by move
id; the table is never emptied.

Quantities: done_qty is the quantity actually done in the PRODUCT's unit
(converted with Odoo's unit factors) and is what moves the stock; only
products with product_is_storable = 1 have stock in Odoo (consumables such as
paper napkins are moved but never stocked). Validated on 2026-10-12 against
Odoo's own stock per branch x product (only moves that existed at the
capture: many are registered later with an earlier date): exact for 9 of the
10 branches; Antenas, the 2024 prototype, carries stock values in Odoo that
differ from the sum of its moves (docs/analytics-inventory-unified-design.md).

Dates: Odoo stores UTC; movement_date is the Mexico City date (UTC-6, no
daylight saving since 2022), the business day of the move.

    python -m extract.inventory.odoo_stock_moves            # incremental
    python -m extract.inventory.odoo_stock_moves --full     # everything again
"""
import argparse
from collections import defaultdict
from datetime import datetime, timedelta

from core.config.companies import COMPANY_SOURCE, get_company_source_key, is_internal_provider_company
from core.database.mysql import get_db_connection
from core.database.odoo import get_odoo_connection

TABLE = "odoo_stock_move_snapshot"
CHUNK = 2000
MARGIN_DAYS = 3
UTC_OFFSET = timedelta(hours=-6)  # Mexico City

MOVE_FIELDS = [
    "date", "company_id", "product_id", "product_uom", "product_qty", "quantity",
    "location_id", "location_dest_id", "picking_type_id", "reference", "origin",
    "scrapped", "is_inventory", "price_unit", "write_date",
]

DDL = f"""
    CREATE TABLE IF NOT EXISTS {TABLE} (
        odoo_move_id INT NOT NULL PRIMARY KEY,
        odoo_company_id INT NOT NULL,
        odoo_company_name VARCHAR(255) NULL,
        company_source_key VARCHAR(100) NULL,
        move_datetime_utc DATETIME NOT NULL,
        movement_date DATE NOT NULL,
        odoo_product_id INT NOT NULL,
        product_display_name VARCHAR(500) NULL,
        uom_name VARCHAR(100) NULL,
        product_uom_name VARCHAR(100) NULL,
        product_is_storable TINYINT(1) NOT NULL DEFAULT 0,
        done_qty DECIMAL(18,6) NOT NULL,
        product_qty DECIMAL(18,4) NOT NULL,
        move_uom_qty DECIMAL(18,4) NULL,
        location_id INT NOT NULL,
        location_name VARCHAR(500) NULL,
        location_usage VARCHAR(30) NULL,
        location_company_id INT NULL,
        location_dest_id INT NOT NULL,
        location_dest_name VARCHAR(500) NULL,
        location_dest_usage VARCHAR(30) NULL,
        location_dest_company_id INT NULL,
        picking_type_name VARCHAR(255) NULL,
        reference VARCHAR(255) NULL,
        origin VARCHAR(255) NULL,
        scrapped TINYINT(1) NOT NULL DEFAULT 0,
        is_inventory TINYINT(1) NOT NULL DEFAULT 0,
        price_unit DECIMAL(18,6) NULL,
        valuation_qty DECIMAL(18,4) NULL,
        valuation_value DECIMAL(18,4) NULL,
        valuation_layer_count INT NOT NULL DEFAULT 0,
        odoo_write_date DATETIME NULL,
        loaded_at DATETIME NOT NULL,
        KEY idx_move_company_date (company_source_key, movement_date),
        KEY idx_move_product (odoo_product_id, movement_date),
        KEY idx_move_write (odoo_write_date)
    )
"""

COLUMNS = [
    "odoo_move_id", "odoo_company_id", "odoo_company_name", "company_source_key",
    "move_datetime_utc", "movement_date", "odoo_product_id", "product_display_name", "uom_name",
    "product_uom_name", "product_is_storable", "done_qty", "product_qty", "move_uom_qty", "location_id", "location_name", "location_usage", "location_company_id",
    "location_dest_id", "location_dest_name", "location_dest_usage", "location_dest_company_id",
    "picking_type_name", "reference", "origin", "scrapped", "is_inventory", "price_unit",
    "valuation_qty", "valuation_value", "valuation_layer_count", "odoo_write_date", "loaded_at",
]


def group_companies(models, db, uid, password):
    """Odoo companies of the group: branches (COMPANY_SOURCE keys) and internal providers."""
    kept, skipped = {}, []
    for c in models.execute_kw(db, uid, password, "res.company", "search_read", [[]], {"fields": ["name"]}):
        key = get_company_source_key(c["name"])
        if key in COMPANY_SOURCE or is_internal_provider_company(c["name"]):
            kept[c["id"]] = (c["name"], key if key in COMPANY_SOURCE else None)
        else:
            skipped.append(c["name"])
    return kept, skipped


def chunks(items, size=CHUNK):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def m2o(value, part=0):
    return value[part] if value else None


def ensure_table(conn):
    cur = conn.cursor()
    cur.execute(DDL)
    conn.commit()
    cur.close()


def last_write_date(conn):
    cur = conn.cursor()
    cur.execute(f"SELECT MAX(odoo_write_date) FROM {TABLE}")
    value = cur.fetchone()[0]
    cur.close()
    return value


def move_ids_to_read(models, db, uid, password, company_ids, since):
    base = [["state", "=", "done"], ["company_id", "in", company_ids]]
    if since is None:
        return models.execute_kw(db, uid, password, "stock.move", "search", [base])
    cutoff = since.strftime("%Y-%m-%d %H:%M:%S")
    ids = set(models.execute_kw(db, uid, password, "stock.move", "search", [base + [["write_date", ">=", cutoff]]]))
    layers = models.execute_kw(
        db, uid, password, "stock.valuation.layer", "search_read",
        [[["company_id", "in", company_ids], ["create_date", ">=", cutoff], ["stock_move_id", "!=", False]]],
        {"fields": ["stock_move_id"]},
    )
    ids |= {m2o(layer["stock_move_id"]) for layer in layers}
    return sorted(ids)


def read_moves(models, db, uid, password, ids):
    moves = []
    for part in chunks(ids):
        moves += models.execute_kw(db, uid, password, "stock.move", "read", [part], {"fields": MOVE_FIELDS})
    return moves


def read_valuation(models, db, uid, password, ids):
    totals = defaultdict(lambda: [0.0, 0.0, 0])
    for part in chunks(ids):
        for layer in models.execute_kw(
            db, uid, password, "stock.valuation.layer", "search_read",
            [[["stock_move_id", "in", part]]], {"fields": ["stock_move_id", "quantity", "value"]},
        ):
            t = totals[m2o(layer["stock_move_id"])]
            t[0] += layer["quantity"] or 0.0
            t[1] += layer["value"] or 0.0
            t[2] += 1
    return totals


def read_uoms(models, db, uid, password):
    """Odoo unit factors: quantity_in_reference = quantity / factor (kg factor 1, g factor 1000)."""
    return {
        u["id"]: (u["name"], u["factor"])
        for u in models.execute_kw(db, uid, password, "uom.uom", "search_read", [[]],
                                   {"fields": ["name", "factor"], "context": {"active_test": False}})
    }


def read_products(models, db, uid, password, moves, cache):
    """Storable flag and unit of each product (cached across batches)."""
    missing = sorted({m2o(m["product_id"]) for m in moves} - set(cache))
    for part in chunks(missing):
        for p in models.execute_kw(db, uid, password, "product.product", "read", [part],
                                   {"fields": ["is_storable", "uom_id"], "context": {"active_test": False}}):
            cache[p["id"]] = (bool(p["is_storable"]), m2o(p["uom_id"]))
    return cache


def done_qty_in_product_uom(move, products, uoms):
    """
    The quantity actually done, in the product's unit. stock.move.quantity is
    in the MOVE's unit (recipes consume grams of a product bought in kg), and
    product_qty is the demand, not what was done; Odoo's stock (stock.quant)
    is in the product's unit and counts what was done.
    """
    _storable, product_uom = products.get(m2o(move["product_id"]), (False, None))
    move_factor = uoms.get(m2o(move["product_uom"]), (None, None))[1]
    product_factor = uoms.get(product_uom, (None, None))[1]
    if not move_factor or not product_factor:
        return move["quantity"] or 0.0
    return (move["quantity"] or 0.0) / move_factor * product_factor


def read_locations(models, db, uid, password, moves):
    ids = sorted({m2o(m["location_id"]) for m in moves} | {m2o(m["location_dest_id"]) for m in moves})
    locations = {}
    for part in chunks(ids):
        for loc in models.execute_kw(db, uid, password, "stock.location", "read", [part],
                                     {"fields": ["complete_name", "usage", "company_id"]}):
            locations[loc["id"]] = loc
    return locations


def build_rows(moves, valuation, locations, companies, products, uoms, loaded_at):
    rows = []
    for m in moves:
        storable, product_uom = products.get(m2o(m["product_id"]), (False, None))
        company_id = m2o(m["company_id"])
        company_name, company_key = companies.get(company_id, (m2o(m["company_id"], 1), None))
        utc = datetime.strptime(m["date"], "%Y-%m-%d %H:%M:%S")
        src, dst = locations.get(m2o(m["location_id"]), {}), locations.get(m2o(m["location_dest_id"]), {})
        qty, value, layers = valuation.get(m["id"], (None, None, 0))
        rows.append((
            m["id"], company_id, company_name, company_key,
            utc, (utc + UTC_OFFSET).date(), m2o(m["product_id"]), m2o(m["product_id"], 1), m2o(m["product_uom"], 1),
            uoms.get(product_uom, (None, None))[0], int(storable), round(done_qty_in_product_uom(m, products, uoms), 6),
            round(m["product_qty"] or 0.0, 4), round(m["quantity"] or 0.0, 4),
            m2o(m["location_id"]), src.get("complete_name"), src.get("usage"), m2o(src.get("company_id")),
            m2o(m["location_dest_id"]), dst.get("complete_name"), dst.get("usage"), m2o(dst.get("company_id")),
            m2o(m["picking_type_id"], 1), m["reference"] or None, m["origin"] or None,
            int(bool(m["scrapped"])), int(bool(m["is_inventory"])), m["price_unit"],
            None if qty is None else round(qty, 4), None if value is None else round(value, 4), layers,
            m["write_date"], loaded_at,
        ))
    return rows


def save(conn, rows):
    marks = ", ".join(["%s"] * len(COLUMNS))
    updates = ", ".join(f"{c} = VALUES({c})" for c in COLUMNS if c != "odoo_move_id")
    sql = f"INSERT INTO {TABLE} ({', '.join(COLUMNS)}) VALUES ({marks}) ON DUPLICATE KEY UPDATE {updates}"
    cur = conn.cursor()
    for part in chunks(rows, 5000):
        cur.executemany(sql, part)
        conn.commit()
    cur.close()


def run(full=False):
    loaded_at = datetime.now().replace(microsecond=0)
    uid, models, db, password = get_odoo_connection()
    companies, skipped = group_companies(models, db, uid, password)

    conn = get_db_connection()
    try:
        ensure_table(conn)
        last = None if full else last_write_date(conn)
        since = None if last is None else last - timedelta(days=MARGIN_DAYS)
        print(f"Odoo stock moves: {'full load' if since is None else f'changed since {since}'}; "
              f"{len(companies)} companies of the group (skipped: {', '.join(sorted(skipped))})")

        ids = move_ids_to_read(models, db, uid, password, sorted(companies), since)
        print(f"  moves to read: {len(ids)}")
        uoms = read_uoms(models, db, uid, password)
        products = {}
        total = 0
        for part in chunks(ids, 20000):
            moves = read_moves(models, db, uid, password, part)
            valuation = read_valuation(models, db, uid, password, part)
            locations = read_locations(models, db, uid, password, moves)
            read_products(models, db, uid, password, moves, products)
            rows = build_rows(moves, valuation, locations, companies, products, uoms, loaded_at)
            save(conn, rows)
            total += len(rows)
            print(f"  saved {total} of {len(ids)}")
    finally:
        conn.close()

    print(f"Odoo stock moves loaded: {total}")
    return total


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--full", action="store_true", help="read every done move again")
    args = parser.parse_args(argv)
    run(full=args.full)


if __name__ == "__main__":
    main()
