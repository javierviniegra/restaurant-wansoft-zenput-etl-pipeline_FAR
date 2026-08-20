"""
Paso 18.21 - Purchases reconciliation gate.

Compares the governed dev pipeline output (canonical_purchase_order_snapshot /
canonical_purchase_order_line_snapshot) against Odoo purchase.order /
purchase.order.line queried directly and independently, with no reuse of
any project ETL, dictionary or mapping code.

This is intentionally standalone. It does not import
extract/purchases/canonical_purchase_etl.py or any other project ETL module,
so a bug shared between the pipeline and this script cannot hide a real
discrepancy.

First run parameters (2026-08-20):
    company_source_key = Antenas
    odoo company_id     = 9 (FONDA ARGENTINA LAS ANTENAS)
    period              = 2026-07-01 to 2026-07-31 (closed month)

Run:
    python -m scripts.reconcile_purchases_dev_vs_odoo
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict

from core.database.mysql import get_db_connection
from core.database.odoo import get_odoo_connection


COMPANY_SOURCE_KEY = "Antenas"
ODOO_COMPANY_ID = 9
PERIOD_START = "2026-07-01"
PERIOD_END = "2026-08-01"  # exclusive

AMOUNT_TOLERANCE = Decimal("1.00")
COUNT_TOLERANCE = 0


def fetch_dev_orders() -> Dict[str, Any]:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(1), SUM(amount_total)
        FROM canonical_purchase_order_snapshot
        WHERE company_source_key = %s
          AND source_system = 'odoo'
          AND order_date >= %s
          AND order_date < %s
        """,
        (COMPANY_SOURCE_KEY, PERIOD_START, PERIOD_END),
    )
    count, total = cur.fetchone()
    cur.close()
    conn.close()
    return {"orders": int(count or 0), "amount_total": total or Decimal("0")}


def fetch_dev_lines() -> Dict[str, Any]:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(1), SUM(price_total)
        FROM canonical_purchase_order_line_snapshot
        WHERE company_source_key = %s
          AND source_system = 'odoo'
          AND order_date >= %s
          AND order_date < %s
        """,
        (COMPANY_SOURCE_KEY, PERIOD_START, PERIOD_END),
    )
    count, total = cur.fetchone()
    cur.close()
    conn.close()
    return {"lines": int(count or 0), "price_total": total or Decimal("0")}


def fetch_odoo_orders_live() -> Dict[str, Any]:
    """
    Queries purchase.order directly. Does not use extract/purchases/*.
    """
    uid, models, db, password = get_odoo_connection()

    domain = [
        ["company_id", "=", ODOO_COMPANY_ID],
        ["date_order", ">=", PERIOD_START],
        ["date_order", "<", PERIOD_END],
    ]

    order_ids = models.execute_kw(
        db, uid, password,
        "purchase.order", "search",
        [domain],
    )

    if not order_ids:
        return {"orders": 0, "amount_total": Decimal("0"), "order_ids": []}

    orders = models.execute_kw(
        db, uid, password,
        "purchase.order", "read",
        [order_ids],
        {"fields": ["id", "amount_total", "date_order", "state"]},
    )

    amount_total = sum(Decimal(str(o["amount_total"])) for o in orders)

    return {
        "orders": len(orders),
        "amount_total": amount_total,
        "order_ids": order_ids,
    }


def fetch_odoo_lines_live(order_ids: list) -> Dict[str, Any]:
    """
    Queries purchase.order.line directly for the same order_ids resolved
    above. Does not use extract/purchases/*.
    """
    if not order_ids:
        return {"lines": 0, "price_total": Decimal("0")}

    uid, models, db, password = get_odoo_connection()

    domain = [["order_id", "in", order_ids]]

    line_ids = models.execute_kw(
        db, uid, password,
        "purchase.order.line", "search",
        [domain],
    )

    if not line_ids:
        return {"lines": 0, "price_total": Decimal("0")}

    lines = models.execute_kw(
        db, uid, password,
        "purchase.order.line", "read",
        [line_ids],
        {"fields": ["id", "price_total"]},
    )

    price_total = sum(Decimal(str(l["price_total"])) for l in lines)

    return {"lines": len(lines), "price_total": price_total}


def compare(label: str, dev_value, odoo_value, tolerance) -> bool:
    diff = abs(Decimal(str(dev_value)) - Decimal(str(odoo_value)))
    passed = diff <= Decimal(str(tolerance))
    status = "PASS" if passed else "FAIL"
    print(f"{label}: dev={dev_value} odoo={odoo_value} diff={diff} tolerance={tolerance} -> {status}")
    return passed


def main() -> int:
    print("=====================================================")
    print("PASO 18.21 - PURCHASES RECONCILIATION: DEV VS LIVE ODOO")
    print("=====================================================")
    print(f"company_source_key: {COMPANY_SOURCE_KEY}")
    print(f"odoo_company_id: {ODOO_COMPANY_ID}")
    print(f"period: {PERIOD_START} to {PERIOD_END} (exclusive)")
    print()

    dev_orders = fetch_dev_orders()
    dev_lines = fetch_dev_lines()

    print("--- DEV (canonical_purchase_order_snapshot / _line_snapshot) ---")
    print(dev_orders)
    print(dev_lines)
    print()

    print("--- LIVE ODOO (direct query, no project ETL code) ---")
    odoo_orders = fetch_odoo_orders_live()
    odoo_lines = fetch_odoo_lines_live(odoo_orders["order_ids"])
    print({"orders": odoo_orders["orders"], "amount_total": odoo_orders["amount_total"]})
    print(odoo_lines)
    print()

    print("--- COMPARISON ---")
    results = [
        compare("orders_count", dev_orders["orders"], odoo_orders["orders"], COUNT_TOLERANCE),
        compare("orders_amount_total", dev_orders["amount_total"], odoo_orders["amount_total"], AMOUNT_TOLERANCE),
        compare("lines_count", dev_lines["lines"], odoo_lines["lines"], COUNT_TOLERANCE),
        compare("lines_price_total", dev_lines["price_total"], odoo_lines["price_total"], AMOUNT_TOLERANCE),
    ]

    print()
    if all(results):
        print("RECONCILIATION RESULT: PASSED")
        return 0

    print("RECONCILIATION RESULT: FAILED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
