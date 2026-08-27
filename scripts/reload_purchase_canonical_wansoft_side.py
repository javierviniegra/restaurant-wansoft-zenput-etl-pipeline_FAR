"""
Rollout maintenance step: clear the Wansoft side of the canonical purchase
snapshot tables so the next run of test_canonical_purchase_wansoft_etl
reloads it with the current COMPANY_SOURCE / odoo_company_migration_policy
classification.

Needed whenever a company's COMPANY_SOURCE flips from "wansoft" to "odoo"
for Purchases: existing canonical Wansoft rows for that company were
classified before the flip (final_wansoft_enabled) and must be reclassified
(wansoft_history_before_odoo / exclude_after_odoo_start) by a fresh ETL run.
See docs/purchases-company-migration-policy.md, "Rollout Update Sequence",
step 10.

Usage: python -m scripts.reload_purchase_canonical_wansoft_side
"""

from core.database.mysql import get_db_connection

TABLES = [
    "canonical_purchase_order_snapshot",
    "canonical_purchase_order_line_snapshot",
    "canonical_purchase_receipt_snapshot",
    "canonical_purchase_receipt_move_snapshot",
]


def main():
    conn = get_db_connection(target="wansoft")
    cursor = conn.cursor()

    for table in TABLES:
        cursor.execute(f"DELETE FROM {table} WHERE source_system = 'wansoft'")
        print(f"{table}: deleted {cursor.rowcount} rows")

    conn.commit()
    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
