"""
Build analytics_company_domain_coverage.

This script creates and refreshes the first unified analytical coverage table.

The table answers:
- Which canonical companies have Purchases?
- Which canonical companies have Inventory?
- Which canonical companies have Zenput submissions?
- Which canonical companies have Zenput tasks?
- Which companies are Zenput-only?
- Which companies are future rollouts?
- Which companies are internal providers?

This is part of the MySQL analytical layer.
It does not implement BI logic.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, Optional, Set

from core.database.mysql import get_db_connection

from core.config.zenput import ZENPUT_LOCATION_SOURCE_KEY


ANALYTICS_TABLE = "analytics_company_domain_coverage"
DIM_TABLE = "dim_company_analytical"


@dataclass
class CoverageRow:
    company_source_key: str
    display_name: str

    is_active_branch: bool
    is_internal_provider: bool
    is_final_operating_branch: bool
    is_future_rollout: bool
    is_zenput_location: bool
    is_zenput_only: bool

    purchases_source_system: str
    inventory_source_system: str
    sales_source_system: str
    zenput_source_status: str
    rollout_type: Optional[str]
    rollout_status: Optional[str]
    operational_start_date: Optional[Any]

    has_purchases: bool = False
    has_purchase_orders: bool = False
    has_purchase_lines: bool = False
    has_inventory: bool = False
    has_zenput_submissions: bool = False
    has_zenput_tasks: bool = False
    has_sales_future_placeholder: bool = False

    purchase_order_count: int = 0
    purchase_line_count: int = 0
    inventory_snapshot_count: int = 0
    zenput_submission_count: int = 0
    zenput_task_count: int = 0

    coverage_status: str = "no_domain_activity"
    coverage_notes: Optional[str] = None


def bool_to_int(value: bool) -> int:
    return 1 if value else 0


def table_exists(conn, table_name: str) -> bool:
    query = """
        SELECT COUNT(*) AS total
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = %s
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, (table_name,))
    row = cursor.fetchone()
    cursor.close()
    return bool(row and row["total"] > 0)


def get_table_columns(conn, table_name: str) -> Set[str]:
    query = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = %s
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, (table_name,))
    rows = cursor.fetchall()
    cursor.close()
    return {r["column_name"] for r in rows}


def fetch_all_dict(conn, query: str, params: Optional[tuple] = None) -> list:
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params or ())
    rows = cursor.fetchall()
    cursor.close()
    return rows


def add_note(row: CoverageRow, note: str) -> None:
    if not note:
        return

    if row.coverage_notes:
        if note not in row.coverage_notes:
            row.coverage_notes = f"{row.coverage_notes} | {note}"
    else:
        row.coverage_notes = note


def create_table_if_missing(conn) -> None:
    ddl = f"""
    CREATE TABLE IF NOT EXISTS {ANALYTICS_TABLE} (
        company_source_key VARCHAR(255) NOT NULL PRIMARY KEY,
        display_name VARCHAR(255) NOT NULL,

        is_active_branch BOOLEAN NOT NULL DEFAULT FALSE,
        is_internal_provider BOOLEAN NOT NULL DEFAULT FALSE,
        is_final_operating_branch BOOLEAN NOT NULL DEFAULT FALSE,
        is_future_rollout BOOLEAN NOT NULL DEFAULT FALSE,
        is_zenput_location BOOLEAN NOT NULL DEFAULT FALSE,
        is_zenput_only BOOLEAN NOT NULL DEFAULT FALSE,

        purchases_source_system VARCHAR(100) NOT NULL DEFAULT 'none',
        inventory_source_system VARCHAR(100) NOT NULL DEFAULT 'none',
        sales_source_system VARCHAR(100) NOT NULL DEFAULT 'none',
        zenput_source_status VARCHAR(100) NOT NULL DEFAULT 'not_detected',
        rollout_type VARCHAR(100) NULL,
        rollout_status VARCHAR(100) NULL,
        operational_start_date DATE NULL,

        has_purchases BOOLEAN NOT NULL DEFAULT FALSE,
        has_purchase_orders BOOLEAN NOT NULL DEFAULT FALSE,
        has_purchase_lines BOOLEAN NOT NULL DEFAULT FALSE,
        has_inventory BOOLEAN NOT NULL DEFAULT FALSE,
        has_zenput_submissions BOOLEAN NOT NULL DEFAULT FALSE,
        has_zenput_tasks BOOLEAN NOT NULL DEFAULT FALSE,
        has_sales_future_placeholder BOOLEAN NOT NULL DEFAULT FALSE,

        purchase_order_count BIGINT NOT NULL DEFAULT 0,
        purchase_line_count BIGINT NOT NULL DEFAULT 0,
        inventory_snapshot_count BIGINT NOT NULL DEFAULT 0,
        zenput_submission_count BIGINT NOT NULL DEFAULT 0,
        zenput_task_count BIGINT NOT NULL DEFAULT 0,

        coverage_status VARCHAR(100) NOT NULL DEFAULT 'no_domain_activity',
        coverage_notes TEXT NULL,

        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

        KEY idx_analytics_company_domain_coverage_status (coverage_status),
        KEY idx_analytics_company_domain_coverage_flags (
            has_purchases,
            has_inventory,
            has_zenput_submissions,
            has_zenput_tasks
        ),
        KEY idx_analytics_company_domain_coverage_rollout (
            rollout_type,
            rollout_status
        )
    )
    """
    cursor = conn.cursor()
    cursor.execute(ddl)
    conn.commit()
    cursor.close()


def load_base_rows(conn) -> Dict[str, CoverageRow]:
    if not table_exists(conn, DIM_TABLE):
        raise RuntimeError(f"Required table does not exist: {DIM_TABLE}")

    query = f"""
        SELECT
            company_source_key,
            display_name,
            is_active_branch,
            is_internal_provider,
            is_final_operating_branch,
            is_future_rollout,
            is_zenput_location,
            is_zenput_only,
            purchases_source_system,
            inventory_source_system,
            sales_source_system,
            zenput_source_status,
            rollout_type,
            rollout_status,
            operational_start_date
        FROM {DIM_TABLE}
    """

    rows: Dict[str, CoverageRow] = {}

    for item in fetch_all_dict(conn, query):
        key = item["company_source_key"]

        rows[key] = CoverageRow(
            company_source_key=key,
            display_name=item["display_name"],
            is_active_branch=bool(item["is_active_branch"]),
            is_internal_provider=bool(item["is_internal_provider"]),
            is_final_operating_branch=bool(item["is_final_operating_branch"]),
            is_future_rollout=bool(item["is_future_rollout"]),
            is_zenput_location=bool(item["is_zenput_location"]),
            is_zenput_only=bool(item["is_zenput_only"]),
            purchases_source_system=item["purchases_source_system"],
            inventory_source_system=item["inventory_source_system"],
            sales_source_system=item["sales_source_system"],
            zenput_source_status=item["zenput_source_status"],
            rollout_type=item["rollout_type"],
            rollout_status=item["rollout_status"],
            operational_start_date=item["operational_start_date"],
        )

    return rows


def apply_purchase_counts(conn, rows: Dict[str, CoverageRow]) -> None:
    if table_exists(conn, "canonical_purchase_order_snapshot"):
        query = """
            SELECT
                company_source_key,
                COUNT(*) AS total_rows
            FROM canonical_purchase_order_snapshot
            GROUP BY company_source_key
        """
        for item in fetch_all_dict(conn, query):
            key = item["company_source_key"]
            if key in rows:
                rows[key].purchase_order_count = int(item["total_rows"])
                rows[key].has_purchase_orders = rows[key].purchase_order_count > 0
            else:
                # Coverage table should stay anchored on dim_company_analytical.
                # Unknown keys are intentionally not inserted here.
                pass

    if table_exists(conn, "canonical_purchase_order_line_snapshot"):
        query = """
            SELECT
                company_source_key,
                COUNT(*) AS total_rows
            FROM canonical_purchase_order_line_snapshot
            GROUP BY company_source_key
        """
        for item in fetch_all_dict(conn, query):
            key = item["company_source_key"]
            if key in rows:
                rows[key].purchase_line_count = int(item["total_rows"])
                rows[key].has_purchase_lines = rows[key].purchase_line_count > 0

    for row in rows.values():
        row.has_purchases = row.has_purchase_orders or row.has_purchase_lines


def find_first_existing_column(columns: Set[str], candidates: list[str]) -> Optional:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def apply_inventory_counts(conn, rows: Dict[str, CoverageRow]) -> None:
    table_name = "odoo_inventory_snapshot"

    if not table_exists(conn, table_name):
        return

    columns = get_table_columns(conn, table_name)

    company_col = find_first_existing_column(
        columns,
        [
            "company_source_key",
            "company_key",
            "company_name",
            "source_company_key",
        ],
    )

    if company_col is None:
        for row in rows.values():
            add_note(row, "Inventory snapshot exists but no company key column was detected.")
        return

    query = f"""
        SELECT
            {company_col} AS company_source_key,
            COUNT(*) AS total_rows
        FROM {table_name}
        GROUP BY {company_col}
    """

    for item in fetch_all_dict(conn, query):
        key = item["company_source_key"]

        if key in rows:
            rows[key].inventory_snapshot_count = int(item["total_rows"])
            rows[key].has_inventory = rows[key].inventory_snapshot_count > 0


def apply_zenput_submission_counts(rows: Dict[str, CoverageRow]) -> None:
    try:
        zenput_conn = get_db_connection(target="zenput")
    except Exception:
        for row in rows.values():
            add_note(row, "Zenput connection unavailable for submission coverage.")
        return

    try:
        if not table_exists(zenput_conn, "submissions"):
            return

        columns = get_table_columns(zenput_conn, "submissions")

        if "location_name" not in columns:
            for row in rows.values():
                add_note(row, "Zenput submissions table has no location_name column.")
            return

        query = """
            SELECT
                location_name,
                COUNT(*) AS total_rows
            FROM submissions
            WHERE location_name IS NOT NULL
            GROUP BY location_name
        """

        for item in fetch_all_dict(zenput_conn, query):
            location_name = item["location_name"]
            mapped_key = ZENPUT_LOCATION_SOURCE_KEY.get(location_name)

            if mapped_key and mapped_key in rows:
                rows[mapped_key].zenput_submission_count += int(item["total_rows"])
                rows[mapped_key].has_zenput_submissions = rows[mapped_key].zenput_submission_count > 0
            elif mapped_key is None:
                # Unknown locations should already be caught by Zenput validators.
                pass

    finally:
        try:
            zenput_conn.close()
        except Exception:
            pass


def apply_zenput_task_counts(rows: Dict[str, CoverageRow]) -> None:
    try:
        zenput_conn = get_db_connection(target="zenput")
    except Exception:
        for row in rows.values():
            add_note(row, "Zenput connection unavailable for task coverage.")
        return

    try:
        if not table_exists(zenput_conn, "zenput_tasks"):
            return

        columns = get_table_columns(zenput_conn, "zenput_tasks")

        location_col = find_first_existing_column(
            columns,
            [
                "location_name",
                "account_name",
                "store_name",
                "location",
                "branch_name",
                "restaurant_name",
                "site_name",
            ],
        )

        if location_col is None:
            for row in rows.values():
                add_note(row, "Zenput tasks table has no detected location column; task coverage not mapped by company.")
            return

        if location_col == "account_name":
            for row in rows.values():
                add_note(row, "Zenput task coverage mapped using zenput_tasks.account_name.")

        query = f"""
            SELECT
                {location_col} AS location_name,
                COUNT(*) AS total_rows
            FROM zenput_tasks
            WHERE {location_col} IS NOT NULL
            GROUP BY {location_col}
        """

        for item in fetch_all_dict(zenput_conn, query):
            location_name = item["location_name"]
            mapped_key = ZENPUT_LOCATION_SOURCE_KEY.get(location_name)

            if mapped_key and mapped_key in rows:
                rows[mapped_key].zenput_task_count += int(item["total_rows"])
                rows[mapped_key].has_zenput_tasks = rows[mapped_key].zenput_task_count > 0

    finally:
        try:
            zenput_conn.close()
        except Exception:
            pass


def derive_coverage_status(rows: Dict[str, CoverageRow]) -> None:
    for row in rows.values():
        domain_count = sum(
            [
                bool(row.has_purchases),
                bool(row.has_inventory),
                bool(row.has_zenput_submissions or row.has_zenput_tasks),
            ]
        )

        if row.is_internal_provider:
            row.coverage_status = "internal_provider"
            continue

        if row.is_zenput_only:
            row.coverage_status = "zenput_only_location"
            continue

        if row.company_source_key == "Puebla" and (row.has_zenput_submissions or row.has_zenput_tasks):
            row.coverage_status = "future_with_zenput_activity"
            continue

        if row.company_source_key == "Puebla":
            row.coverage_status = "future_no_activity"
            continue

        if domain_count >= 2:
            row.coverage_status = "multi_domain"
            continue

        if row.has_purchases:
            row.coverage_status = "purchases_only"
            continue

        if row.has_inventory:
            row.coverage_status = "inventory_only"
            continue

        if row.has_zenput_submissions or row.has_zenput_tasks:
            row.coverage_status = "zenput_activity_only"
            continue

        if row.is_future_rollout:
            row.coverage_status = "future_no_activity"
            continue

        row.coverage_status = "no_domain_activity"


def upsert_rows(conn, rows: Dict[str, CoverageRow]) -> None:
    sql = f"""
    INSERT INTO {ANALYTICS_TABLE} (
        company_source_key,
        display_name,
        is_active_branch,
        is_internal_provider,
        is_final_operating_branch,
        is_future_rollout,
        is_zenput_location,
        is_zenput_only,
        purchases_source_system,
        inventory_source_system,
        sales_source_system,
        zenput_source_status,
        rollout_type,
        rollout_status,
        operational_start_date,
        has_purchases,
        has_purchase_orders,
        has_purchase_lines,
        has_inventory,
        has_zenput_submissions,
        has_zenput_tasks,
        has_sales_future_placeholder,
        purchase_order_count,
        purchase_line_count,
        inventory_snapshot_count,
        zenput_submission_count,
        zenput_task_count,
        coverage_status,
        coverage_notes
    )
    VALUES (
        %(company_source_key)s,
        %(display_name)s,
        %(is_active_branch)s,
        %(is_internal_provider)s,
        %(is_final_operating_branch)s,
        %(is_future_rollout)s,
        %(is_zenput_location)s,
        %(is_zenput_only)s,
        %(purchases_source_system)s,
        %(inventory_source_system)s,
        %(sales_source_system)s,
        %(zenput_source_status)s,
        %(rollout_type)s,
        %(rollout_status)s,
        %(operational_start_date)s,
        %(has_purchases)s,
        %(has_purchase_orders)s,
        %(has_purchase_lines)s,
        %(has_inventory)s,
        %(has_zenput_submissions)s,
        %(has_zenput_tasks)s,
        %(has_sales_future_placeholder)s,
        %(purchase_order_count)s,
        %(purchase_line_count)s,
        %(inventory_snapshot_count)s,
        %(zenput_submission_count)s,
        %(zenput_task_count)s,
        %(coverage_status)s,
        %(coverage_notes)s
    )
    ON DUPLICATE KEY UPDATE
        display_name = VALUES(display_name),
        is_active_branch = VALUES(is_active_branch),
        is_internal_provider = VALUES(is_internal_provider),
        is_final_operating_branch = VALUES(is_final_operating_branch),
        is_future_rollout = VALUES(is_future_rollout),
        is_zenput_location = VALUES(is_zenput_location),
        is_zenput_only = VALUES(is_zenput_only),
        purchases_source_system = VALUES(purchases_source_system),
        inventory_source_system = VALUES(inventory_source_system),
        sales_source_system = VALUES(sales_source_system),
        zenput_source_status = VALUES(zenput_source_status),
        rollout_type = VALUES(rollout_type),
        rollout_status = VALUES(rollout_status),
        operational_start_date = VALUES(operational_start_date),
        has_purchases = VALUES(has_purchases),
        has_purchase_orders = VALUES(has_purchase_orders),
        has_purchase_lines = VALUES(has_purchase_lines),
        has_inventory = VALUES(has_inventory),
        has_zenput_submissions = VALUES(has_zenput_submissions),
        has_zenput_tasks = VALUES(has_zenput_tasks),
        has_sales_future_placeholder = VALUES(has_sales_future_placeholder),
        purchase_order_count = VALUES(purchase_order_count),
        purchase_line_count = VALUES(purchase_line_count),
        inventory_snapshot_count = VALUES(inventory_snapshot_count),
        zenput_submission_count = VALUES(zenput_submission_count),
        zenput_task_count = VALUES(zenput_task_count),
        coverage_status = VALUES(coverage_status),
        coverage_notes = VALUES(coverage_notes),
        updated_at = CURRENT_TIMESTAMP
    """

    payload = []

    for row in rows.values():
        item = asdict(row)
        item["is_active_branch"] = bool_to_int(row.is_active_branch)
        item["is_internal_provider"] = bool_to_int(row.is_internal_provider)
        item["is_final_operating_branch"] = bool_to_int(row.is_final_operating_branch)
        item["is_future_rollout"] = bool_to_int(row.is_future_rollout)
        item["is_zenput_location"] = bool_to_int(row.is_zenput_location)
        item["is_zenput_only"] = bool_to_int(row.is_zenput_only)
        item["has_purchases"] = bool_to_int(row.has_purchases)
        item["has_purchase_orders"] = bool_to_int(row.has_purchase_orders)
        item["has_purchase_lines"] = bool_to_int(row.has_purchase_lines)
        item["has_inventory"] = bool_to_int(row.has_inventory)
        item["has_zenput_submissions"] = bool_to_int(row.has_zenput_submissions)
        item["has_zenput_tasks"] = bool_to_int(row.has_zenput_tasks)
        item["has_sales_future_placeholder"] = bool_to_int(row.has_sales_future_placeholder)
        payload.append(item)

    cursor = conn.cursor()

    # Exact rebuild is safe at this stage because no downstream facts depend on this table yet.
    cursor.execute(f"DELETE FROM {ANALYTICS_TABLE}")

    cursor.executemany(sql, payload)
    conn.commit()
    cursor.close()


def print_summary(rows: Dict[str, CoverageRow]) -> None:
    total = len(rows)
    has_purchases = sum(1 for r in rows.values() if r.has_purchases)
    has_inventory = sum(1 for r in rows.values() if r.has_inventory)
    has_zenput_submissions = sum(1 for r in rows.values() if r.has_zenput_submissions)
    has_zenput_tasks = sum(1 for r in rows.values() if r.has_zenput_tasks)

    status_counts: Dict[str, int] = {}

    for row in rows.values():
        status_counts[row.coverage_status] = status_counts.get(row.coverage_status, 0) + 1

    print("=====================================================")
    print("ANALYTICS COMPANY DOMAIN COVERAGE BUILD SUMMARY")
    print("=====================================================")
    print(f"table: {ANALYTICS_TABLE}")
    print(f"total_rows_prepared: {total}")
    print(f"has_purchases: {has_purchases}")
    print(f"has_inventory: {has_inventory}")
    print(f"has_zenput_submissions: {has_zenput_submissions}")
    print(f"has_zenput_tasks: {has_zenput_tasks}")
    print("coverage_status_counts:")

    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")

    print("=====================================================")


def main() -> int:
    print("=====================================================")
    print("ANALYTICS COMPANY DOMAIN COVERAGE BUILD START")
    print("=====================================================")

    conn = get_db_connection()

    try:
        create_table_if_missing(conn)

        rows = load_base_rows(conn)

        apply_purchase_counts(conn, rows)
        apply_inventory_counts(conn, rows)
        apply_zenput_submission_counts(rows)
        apply_zenput_task_counts(rows)
        derive_coverage_status(rows)

        upsert_rows(conn, rows)
        print_summary(rows)

        print("BUILD RESULT: COMPLETED")
        return 0

    except Exception as exc:
        print("BUILD RESULT: FAILED")
        print(f"error: {exc}")
        return 1

    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())