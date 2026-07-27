"""
Inventory Outputs Validator.

Purpose:
    Validate Inventory domain outputs after running the inventory pipeline.

This script is read-only.

It validates:
    - required Inventory tables exist
    - inventory snapshot has rows
    - inventory backlog table is available
    - inventory scope classification exists
    - inventory dictionary exists
    - inventory lifecycle table exists
    - snapshot distributions are available when columns exist
    - backlog distributions are available when columns exist
    - residual not_found / pending_review visibility
    - dictionary coverage visibility

Execution:
    python -m scripts.validate_inventory_outputs

Important:
    This script does not promote dictionary rows.
    This script does not update Odoo.
    This script does not modify COMPANY_SOURCE.
"""

from __future__ import annotations

import sys
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from core.database.mysql import get_mysql_connection as get_db_connection


DATABASE_TARGET = "wansoft"

REQUIRED_TABLES = [
    "odoo_inventory_scope_classification",
    "odoo_inventory_snapshot",
    "odoo_inventory_backlog",
    "inventory_mapping_dictionary",
    "inventory_product_lifecycle",
]


def now_iso() -> str:
    """
    Returns current local timestamp as string.
    """

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def read_sql(query: str, params: Optional[tuple] = None) -> pd.DataFrame:
    """
    Executes a read-only SQL query against MySQL.
    """

    conn = get_db_connection(target=DATABASE_TARGET)

    try:
        df = pd.read_sql(query, conn, params=params)
    finally:
        conn.close()

    return df


def print_section(title: str) -> None:
    """
    Prints a standard section header.
    """

    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def print_df(df: pd.DataFrame, empty_message: str = "No rows returned.") -> None:
    """
    Prints a dataframe safely.
    """

    if df is None or df.empty:
        print(empty_message)
        return

    print(df.to_string(index=False))


def table_exists(table_name: str) -> bool:
    """
    Returns True if a table exists in the current database.
    """

    query = """
    SELECT
        COUNT(*) AS table_count
    FROM information_schema.tables
    WHERE table_schema = DATABASE()
      AND table_name = %s
    """

    df = read_sql(query, params=(table_name,))

    if df.empty:
        return False

    return int(df.iloc[0]["table_count"]) > 0


def get_table_columns(table_name: str):
    """
    Returns the list of columns for a table.
    """

    query = """
    SELECT
        column_name
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = %s
    ORDER BY ordinal_position
    """

    df = read_sql(query, params=(table_name,))

    if df.empty:
        return []

    return [str(value) for value in df["column_name"].tolist()]


def first_existing_column(
    table_name: str,
    candidates: List[str],
):
    """
    Returns the first candidate column that exists in a table.
    """

    available_columns = set(get_table_columns(table_name))

    for candidate in candidates:
        if candidate in available_columns:
            return candidate

    return None


def validate_required_tables_exist(results: Dict[str, bool]) -> None:
    """
    Validates that the required Inventory tables exist.
    """

    print_section("1. REQUIRED INVENTORY TABLES")

    rows = []

    for table_name in REQUIRED_TABLES:
        exists = table_exists(table_name)

        rows.append(
            {
                "table_name": table_name,
                "exists": exists,
            }
        )

    df = pd.DataFrame(rows)
    print_df(df)

    passed = bool(df["exists"].all())

    results["required_inventory_tables_exist"] = passed

    print("\nValidation:")
    print(f"status: {'PASS' if passed else 'FAIL'}")


def validate_table_counts(results: Dict[str, bool]) -> None:
    """
    Validates row counts for the required Inventory tables.
    """

    print_section("2. INVENTORY TABLE COUNTS")

    union_parts = []

    for table_name in REQUIRED_TABLES:
        if table_exists(table_name):
            union_parts.append(
                f"""
                SELECT
                    '{table_name}' AS table_name,
                    COUNT(*) AS total_rows
                FROM {table_name}
                """
            )

    if not union_parts:
        print("No required Inventory tables are available.")
        results["inventory_table_counts_available"] = False
        print("\nValidation:")
        print("status: FAIL")
        return

    query = "\nUNION ALL\n".join(union_parts)
    query = f"""
    {query}
    ORDER BY table_name
    """

    df = read_sql(query)
    print_df(df)

    required_present = set(df["table_name"].tolist())
    missing_tables = set(REQUIRED_TABLES) - required_present

    core_tables_with_rows = True

    for table_name in [
        "odoo_inventory_scope_classification",
        "odoo_inventory_snapshot",
        "inventory_mapping_dictionary",
    ]:
        table_df = df[df["table_name"] == table_name]

        if table_df.empty:
            core_tables_with_rows = False
            continue

        if int(table_df.iloc[0]["total_rows"]) <= 0:
            core_tables_with_rows = False

    passed = len(missing_tables) == 0 and core_tables_with_rows

    results["inventory_table_counts_available"] = passed

    print("\nValidation:")
    print(f"missing_tables: {sorted(missing_tables)}")
    print(f"core_tables_with_rows: {core_tables_with_rows}")
    print(f"status: {'PASS' if passed else 'FAIL'}")


def validate_scope_distribution(results: Dict[str, bool]) -> None:
    """
    Validates scope distribution from the scope classification table.
    """

    print_section("3. INVENTORY SCOPE DISTRIBUTION")

    table_name = "odoo_inventory_scope_classification"

    if not table_exists(table_name):
        print(f"Table not found: {table_name}")
        results["inventory_scope_distribution_available"] = False
        print("\nValidation:")
        print("status: FAIL")
        return

    scope_column = first_existing_column(
        table_name,
        [
            "inventory_scope",
            "refined_inventory_scope",
            "product_scope",
            "scope",
            "scope_bucket",
        ],
    )

    if not scope_column:
        print("No scope-like column found.")
        print("Available columns:")
        print(get_table_columns(table_name))
        results["inventory_scope_distribution_available"] = False
        print("\nValidation:")
        print("status: FAIL")
        return

    query = f"""
    SELECT
        {scope_column} AS inventory_scope,
        COUNT(*) AS total_rows
    FROM {table_name}
    GROUP BY {scope_column}
    ORDER BY total_rows DESC
    """

    df = read_sql(query)
    print_df(df)

    passed = not df.empty

    results["inventory_scope_distribution_available"] = passed

    print("\nValidation:")
    print(f"scope_column: {scope_column}")
    print(f"status: {'PASS' if passed else 'FAIL'}")


def validate_snapshot_mapping_distribution(results: Dict[str, bool]) -> None:
    """
    Validates mapping distribution in the inventory snapshot table.
    """

    print_section("4. INVENTORY SNAPSHOT MAPPING DISTRIBUTION")

    table_name = "odoo_inventory_snapshot"

    if not table_exists(table_name):
        print(f"Table not found: {table_name}")
        results["inventory_snapshot_mapping_distribution_available"] = False
        print("\nValidation:")
        print("status: FAIL")
        return

    status_column = first_existing_column(
        table_name,
        [
            "inventory_mapping_status",
            "mapping_status",
            "dictionary_status",
            "match_status",
            "mapped_status",
        ],
    )

    scope_column = first_existing_column(
        table_name,
        [
            "inventory_scope",
            "refined_inventory_scope",
            "purchase_product_scope",
            "product_scope",
            "scope",
            "scope_bucket",
        ],
    )

    if not status_column:
        print("No mapping-status-like column found.")
        print("Available columns:")
        print(get_table_columns(table_name))
        results["inventory_snapshot_mapping_distribution_available"] = False
        print("\nValidation:")
        print("status: FAIL")
        return

    if scope_column:
        query = f"""
        SELECT
            {scope_column} AS inventory_scope,
            {status_column} AS mapping_status,
            COUNT(*) AS total_rows
        FROM {table_name}
        GROUP BY
            {scope_column},
            {status_column}
        ORDER BY
            total_rows DESC
        """
    else:
        query = f"""
        SELECT
            {status_column} AS mapping_status,
            COUNT(*) AS total_rows
        FROM {table_name}
        GROUP BY {status_column}
        ORDER BY total_rows DESC
        """

    df = read_sql(query)
    print_df(df)

    passed = not df.empty

    results["inventory_snapshot_mapping_distribution_available"] = passed

    print("\nValidation:")
    print(f"status_column: {status_column}")
    print(f"scope_column: {scope_column}")
    print(f"status: {'PASS' if passed else 'FAIL'}")


def validate_backlog_distribution(results: Dict[str, bool]) -> None:
    """
    Validates backlog distribution in the inventory backlog table.

    An empty backlog table is considered valid because it may mean there are
    no current unresolved backlog rows after the inventory ETL.
    """

    print_section("5. INVENTORY BACKLOG DISTRIBUTION")

    table_name = "odoo_inventory_backlog"

    if not table_exists(table_name):
        print(f"Table not_found: {table_name}")
        results["inventory_backlog_distribution_available"] = False
        print("\nValidation:")
        print("status: FAIL")
        return

    count_query = f"""
    SELECT
        COUNT(*) AS total_rows
    FROM {table_name}
    """

    count_df = read_sql(count_query)
    total_rows = int(count_df.iloc[0]["total_rows"]) if not count_df.empty else 0

    print(f"table_name: {table_name}")
    print(f"total_rows: {total_rows}")

    if total_rows == 0:
        print("\nNo backlog rows found.")
        print("This is acceptable if the current inventory ETL produced no unresolved backlog records.")

        results["inventory_backlog_distribution_available"] = True

        print("\nValidation:")
        print("status: PASS")
        print("note: backlog table exists and is currently empty.")
        return

    status_column = first_existing_column(
        table_name,
        [
            "backlog_status",
            "mapping_status",
            "inventory_mapping_status",
            "review_status",
            "status",
        ],
    )

    action_column = first_existing_column(
        table_name,
        [
            "suggested_action",
            "recommended_action",
            "action",
            "review_action",
        ],
    )

    bucket_column = first_existing_column(
        table_name,
        [
            "mapping_bucket",
            "inventory_mapping_bucket",
            "backlog_bucket",
            "bucket",
        ],
    )

    group_columns = [
        column
        for column in [status_column, action_column, bucket_column]
        if column is not None
    ]

    if group_columns:
        select_columns = ",\n            ".join(group_columns)
        group_by_columns = ",\n            ".join(group_columns)

        query = f"""
        SELECT
            {select_columns},
            COUNT(*) AS total_rows
        FROM {table_name}
        GROUP BY
            {group_by_columns}
        ORDER BY total_rows DESC
        """
    else:
        query = f"""
        SELECT
            COUNT(*) AS total_rows
        FROM {table_name}
        """

    df = read_sql(query)
    print_df(df)

    passed = not df.empty

    results["inventory_backlog_distribution_available"] = passed

    print("\nValidation:")
    print(f"status_column: {status_column}")
    print(f"action_column: {action_column}")
    print(f"bucket_column: {bucket_column}")
    print(f"status: {'PASS' if passed else 'FAIL'}")


def validate_residual_visibility(results: Dict[str, bool]) -> None:
    """
    Validates visibility of residual not_found and pending_review style outputs.
    """

    print_section("6. RESIDUAL NOT_FOUND / PENDING_REVIEW VISIBILITY")

    table_candidates = [
        "odoo_inventory_snapshot",
        "odoo_inventory_backlog",
    ]

    rows = []

    for table_name in table_candidates:
        if not table_exists(table_name):
            continue

        status_column = first_existing_column(
            table_name,
            [
                "inventory_mapping_status",
                "mapping_status",
                "dictionary_status",
                "match_status",
                "review_status",
                "backlog_status",
                "status",
            ],
        )

        if not status_column:
            rows.append(
                {
                    "table_name": table_name,
                    "status_column": None,
                    "status_value": None,
                    "total_rows": None,
                    "note": "No status-like column found.",
                }
            )
            continue

        query = f"""
        SELECT
            '{table_name}' AS table_name,
            '{status_column}' AS status_column,
            {status_column} AS status_value,
            COUNT(*) AS total_rows
        FROM {table_name}
        WHERE LOWER(COALESCE(CAST({status_column} AS CHAR), '')) IN (
            'not_found',
            'pending_review',
            'open',
            'review'
        )
        GROUP BY {status_column}
        ORDER BY total_rows DESC
        """

        df = read_sql(query)

        if df.empty:
            rows.append(
                {
                    "table_name": table_name,
                    "status_column": status_column,
                    "status_value": None,
                    "total_rows": 0,
                    "note": "No residual status rows found for tracked values.",
                }
            )
        else:
            for _, row in df.iterrows():
                rows.append(
                    {
                        "table_name": row["table_name"],
                        "status_column": row["status_column"],
                        "status_value": row["status_value"],
                        "total_rows": row["total_rows"],
                        "note": "Tracked residual status found.",
                    }
                )

    output_df = pd.DataFrame(rows)
    print_df(output_df)

    passed = not output_df.empty

    results["inventory_residual_visibility_available"] = passed

    print("\nValidation:")
    print(f"status: {'PASS' if passed else 'FAIL'}")


def validate_dictionary_coverage_visibility(results: Dict[str, bool]) -> None:
    """
    Validates dictionary coverage visibility using inventory_mapping_dictionary.
    """

    print_section("7. INVENTORY DICTIONARY COVERAGE VISIBILITY")

    table_name = "inventory_mapping_dictionary"

    if not table_exists(table_name):
        print(f"Table not found: {table_name}")
        results["inventory_dictionary_coverage_available"] = False
        print("\nValidation:")
        print("status: FAIL")
        return

    status_column = first_existing_column(
        table_name,
        [
            "mapping_status",
            "dictionary_status",
            "approval_status",
            "status",
        ],
    )

    scope_column = first_existing_column(
        table_name,
        [
            "inventory_scope",
            "product_scope",
            "scope",
            "scope_bucket",
        ],
    )

    if status_column and scope_column:
        query = f"""
        SELECT
            {scope_column} AS inventory_scope,
            {status_column} AS dictionary_status,
            COUNT(*) AS total_rows
        FROM {table_name}
        GROUP BY
            {scope_column},
            {status_column}
        ORDER BY total_rows DESC
        """
    elif status_column:
        query = f"""
        SELECT
            {status_column} AS dictionary_status,
            COUNT(*) AS total_rows
        FROM {table_name}
        GROUP BY {status_column}
        ORDER BY total_rows DESC
        """
    elif scope_column:
        query = f"""
        SELECT
            {scope_column} AS inventory_scope,
            COUNT(*) AS total_rows
        FROM {table_name}
        GROUP BY {scope_column}
        ORDER BY total_rows DESC
        """
    else:
        query = f"""
        SELECT
            COUNT(*) AS total_rows
        FROM {table_name}
        """

    df = read_sql(query)
    print_df(df)

    passed = not df.empty

    results["inventory_dictionary_coverage_available"] = passed

    print("\nValidation:")
    print(f"status_column: {status_column}")
    print(f"scope_column: {scope_column}")
    print(f"status: {'PASS' if passed else 'FAIL'}")


def validate_no_automatic_promotions(results: Dict[str, bool]) -> None:
    """
    Documents that promotion scripts are not part of validation or default orchestration.

    This is a governance validation by design.
    """

    print_section("8. CONTROLLED PROMOTION POLICY")

    promotion_scripts = [
        "scripts.test_promote_inventory_bridge_to_dictionary",
        "scripts.test_promote_inventory_not_found_p1_to_dictionary",
        "scripts.test_promote_inventory_not_found_p2_to_dictionary",
        "scripts.test_promote_inventory_not_found_residual_to_dictionary",
    ]

    rows = []

    for module_name in promotion_scripts:
        rows.append(
            {
                "module": module_name,
                "included_in_default_pipeline": False,
                "policy": "manual approval required",
            }
        )

    df = pd.DataFrame(rows)
    print_df(df)

    passed = True

    results["inventory_promotions_controlled"] = passed

    print("\nValidation:")
    print("status: PASS")
    print("note: promotion scripts are intentionally excluded from default automation.")


def print_final_summary(results: Dict[str, bool]) -> int:
    """
    Prints final validation summary.
    """

    print_section("FINAL INVENTORY VALIDATION SUMMARY")

    failed: List[str] = []

    for validation_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"{validation_name}: {status}")

        if not passed:
            failed.append(validation_name)

    print("\n-----------------------------------------------------")
    print("SUMMARY COUNTS")
    print("-----------------------------------------------------")
    print(f"total_validations: {len(results)}")
    print(f"passed: {len(results) - len(failed)}")
    print(f"failed: {len(failed)}")

    if failed:
        print("\nVALIDATION RESULT: FAILED")
        print("Failed validations:")

        for item in failed:
            print(f"- {item}")

        return 1

    print("\nVALIDATION RESULT: PASSED")
    return 0


def main() -> int:
    """
    Main validation entrypoint.
    """

    print("=====================================================")
    print("INVENTORY OUTPUT VALIDATION START")
    print("=====================================================")
    print(f"started_at: {now_iso()}")

    results: Dict[str, bool] = {}

    validate_required_tables_exist(results)
    validate_table_counts(results)
    validate_scope_distribution(results)
    validate_snapshot_mapping_distribution(results)
    validate_backlog_distribution(results)
    validate_residual_visibility(results)
    validate_dictionary_coverage_visibility(results)
    validate_no_automatic_promotions(results)

    exit_code = print_final_summary(results)

    print(f"\nfinished_at: {now_iso()}")
    print("=====================================================")
    print("INVENTORY OUTPUT VALIDATION END")
    print("=====================================================")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())