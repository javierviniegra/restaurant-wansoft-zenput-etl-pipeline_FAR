"""
Daily history of Odoo stock (owner, 2026-10-08, "part a").

Until now the warehouse only kept Odoo's CURRENT stock, overwritten every
night (odoo_inventory_snapshot, and only the products with an approved
mapping). For the branches on Odoo there was no way to know the stock of a
past day. This stage stores, every night, the raw stock.quant of Odoo in
odoo_inventory_quant_daily: one row per stock day, location and product,
for every company, without mappings or scope rules (those can be applied
later on the history, and a mapping bug cannot damage it).

Kept: locations whose usage is 'internal' (warehouses, kitchens) or
'transit' (goods between warehouses). Odoo's virtual locations (customer,
supplier, production, inventory adjustment) are not physical stock and are
left out (about 35,000 of 42,000 quants on 2026-10-08).

stock_date: the cycle runs at 01:30, so a capture before 06:00 is labelled
with the previous day (the stock at the close of that day, as far as Odoo
has processed it); a capture later in the day is labelled with that day and
is replaced by the next night's capture. Each run deletes and rewrites its
stock_date, so re-running is safe.

There is no history before the first run: Odoo's past stock has to be
rebuilt from its stock moves (stock.move), a separate piece of work.

    python -m extract.inventory.odoo_quant_daily          # writes to the database ENV points at
"""
from collections import defaultdict
from datetime import datetime, timedelta

from core.config.companies import get_company_source_key
from core.database.mysql import get_db_connection
from core.database.odoo import get_odoo_connection

TABLE = "odoo_inventory_quant_daily"
KEPT_USAGES = ("internal", "transit")
CLOSE_HOUR = 6  # captures before this hour belong to the previous day

DDL = f"""
    CREATE TABLE IF NOT EXISTS {TABLE} (
        stock_date DATE NOT NULL,
        odoo_location_id INT NOT NULL,
        odoo_product_id INT NOT NULL,
        captured_at DATETIME NOT NULL,
        odoo_company_id INT NULL,
        odoo_company_name VARCHAR(255) NULL,
        company_source_key VARCHAR(100) NULL,
        location_name VARCHAR(500) NULL,
        location_usage VARCHAR(30) NOT NULL,
        product_code VARCHAR(100) NULL,
        product_name VARCHAR(500) NULL,
        quantity DECIMAL(18,4) NOT NULL,
        reserved_quantity DECIMAL(18,4) NOT NULL DEFAULT 0,
        quant_count INT NOT NULL,
        PRIMARY KEY (stock_date, odoo_location_id, odoo_product_id),
        KEY idx_quant_daily_company (company_source_key, stock_date),
        KEY idx_quant_daily_product (odoo_product_id, stock_date)
    )
"""


def stock_date_for(captured_at):
    day = captured_at.date()
    return day - timedelta(days=1) if captured_at.hour < CLOSE_HOUR else day


def split_code(display_name):
    """'[1000-100-101-001] Aguacate Hass' -> ('1000-100-101-001', 'Aguacate Hass')."""
    if display_name and display_name.startswith("[") and "]" in display_name:
        code, name = display_name[1:].split("]", 1)
        return code.strip() or None, name.strip()
    return None, display_name


def fetch_quants():
    uid, models, db, password = get_odoo_connection()
    quants = models.execute_kw(
        db, uid, password, "stock.quant", "search_read", [[]],
        {"fields": ["company_id", "product_id", "location_id", "quantity", "reserved_quantity"]},
    )
    location_ids = sorted({q["location_id"][0] for q in quants if q["location_id"]})
    locations = {
        loc["id"]: loc
        for loc in models.execute_kw(
            db, uid, password, "stock.location", "read", [location_ids],
            {"fields": ["usage", "complete_name"]},
        )
    }
    return quants, locations


def aggregate(quants, locations):
    """One row per (location, product): a product can have several quants in a location (lots)."""
    rows = {}
    for q in quants:
        if not q["location_id"] or not q["product_id"]:
            continue
        loc = locations.get(q["location_id"][0])
        if not loc or loc["usage"] not in KEPT_USAGES:
            continue
        key = (q["location_id"][0], q["product_id"][0])
        row = rows.get(key)
        if row is None:
            company_name = q["company_id"][1] if q["company_id"] else None
            code, name = split_code(q["product_id"][1])
            row = rows[key] = {
                "odoo_location_id": key[0],
                "odoo_product_id": key[1],
                "odoo_company_id": q["company_id"][0] if q["company_id"] else None,
                "odoo_company_name": company_name,
                "company_source_key": get_company_source_key(company_name) if company_name else None,
                "location_name": loc["complete_name"],
                "location_usage": loc["usage"],
                "product_code": code,
                "product_name": name,
                "quantity": 0.0,
                "reserved_quantity": 0.0,
                "quant_count": 0,
            }
        row["quantity"] += q["quantity"] or 0.0
        row["reserved_quantity"] += q["reserved_quantity"] or 0.0
        row["quant_count"] += 1
    return list(rows.values())


def save(conn, rows, stock_date, captured_at):
    cur = conn.cursor()
    cur.execute(DDL)
    cur.execute(f"DELETE FROM {TABLE} WHERE stock_date = %s", (stock_date,))
    replaced = cur.rowcount
    cur.executemany(
        f"""
        INSERT INTO {TABLE} (
            stock_date, odoo_location_id, odoo_product_id, captured_at,
            odoo_company_id, odoo_company_name, company_source_key,
            location_name, location_usage, product_code, product_name,
            quantity, reserved_quantity, quant_count
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        [
            (
                stock_date, r["odoo_location_id"], r["odoo_product_id"], captured_at,
                r["odoo_company_id"], r["odoo_company_name"], r["company_source_key"],
                r["location_name"], r["location_usage"], r["product_code"], r["product_name"],
                round(r["quantity"], 4), round(r["reserved_quantity"], 4), r["quant_count"],
            )
            for r in rows
        ],
    )
    conn.commit()
    cur.close()
    return replaced


def run(captured_at=None):
    captured_at = (captured_at or datetime.now()).replace(microsecond=0)
    stock_date = stock_date_for(captured_at)
    quants, locations = fetch_quants()
    rows = aggregate(quants, locations)

    conn = get_db_connection()
    try:
        replaced = save(conn, rows, stock_date, captured_at)
    finally:
        conn.close()

    by_company = defaultdict(int)
    for r in rows:
        by_company[r["company_source_key"] or r["odoo_company_name"] or "(sin empresa)"] += 1
    print(f"Odoo stock del {stock_date} (capturado {captured_at}): {len(quants)} quants leídos, "
          f"{len(rows)} filas guardadas (ubicaciones {'/'.join(KEPT_USAGES)}), {replaced} filas previas reemplazadas")
    for company, n in sorted(by_company.items()):
        print(f"  {company}: {n}")
    if not rows:
        raise RuntimeError("Odoo no devolvió existencias en ubicaciones internas: no se guardó nada")
    return len(rows)


if __name__ == "__main__":
    run()
