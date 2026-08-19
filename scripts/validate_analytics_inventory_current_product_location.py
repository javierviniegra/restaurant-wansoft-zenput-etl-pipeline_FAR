"""
Validate analytics_inventory_current_product_location.

Validation goals:
- table exists
- table has rows
- grain is unique
- source row count reconciles to vw_inventory_physical_snapshot for current snapshot
- stock quantity reconciles to vw_inventory_physical_snapshot for current snapshot
- date and product references are valid when populated
- all rows come from physical inventory policy
- no negative current stock rows are included in business views
- excluded rows have an exclusion reason
- business inclusion and review status distributions are available
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

import pandas as pd

from core.database.mysql import get_db_connection


TABLE_NAME = "analytics_inventory_current_product_location"
SOURCE_VIEW = "vw_inventory_physical_snapshot"
AMOUNT_TOLERANCE_RATE = Decimal("0.0001")


def query_df(conn: Any, query: str, params: Optional[tuple] = None) -> pd.DataFrame:
    return pd.read_sql(query, conn, params=params)


def validation_result(name: str, status: str, details: Any = None) -> Dict[str, Any]:
    return {
        "validation": name,
        "status": status,
        "details": details,
    }


def table_exists(conn: Any, table_name: str) -> bool:
    query = """
        SELECT COUNT(1) AS total
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = %s
    """
    df = query_df(conn, query, (table_name,))
    return bool(df.iloc[0]["total"] > 0)


def view_exists(conn: Any, view_name: str) -> bool:
    query = """
        SELECT COUNT(1) AS total
        FROM information_schema.views
        WHERE table_schema = DATABASE()
          AND table_name = %s
    """
    df = query_df(conn, query, (view_name,))
    return bool(df.iloc[0]["total"] > 0)


def validate_table_exists(conn: Any) -> Dict[str, Any]:
    exists = table_exists(conn, TABLE_NAME)

    return validation_result(
        "analytics_inventory_current_product_location_exists",
        "PASS" if exists else "FAIL",
        {
            "table_name": TABLE_NAME,
            "exists": exists,
        },
    )


def validate_source_view_exists(conn: Any) -> Dict[str, Any]:
    exists = view_exists(conn, SOURCE_VIEW)

    return validation_result(
        "source_physical_view_exists",
        "PASS" if exists else "FAIL",
        {
            "view_name": SOURCE_VIEW,
            "exists": exists,
        },
    )


def validate_row_count(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS total_rows
        FROM {TABLE_NAME}
    """
    df = query_df(conn, query)
    total_rows = int(df.iloc[0]["total_rows"])

    return validation_result(
        "analytics_inventory_current_product_location_has_rows",
        "PASS" if total_rows > 0 else "FAIL",
        {
            "total_rows": total_rows,
        },
    )


def validate_unique_grain(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            snapshot_date_key,
            product_analytical_key,
            source_location_id,
            COUNT(1) AS total_rows
        FROM {TABLE_NAME}
        GROUP BY
            snapshot_date_key,
            product_analytical_key,
            source_location_id
        HAVING COUNT(1) > 1
    """
    df = query_df(conn, query)

    return validation_result(
        "current_product_location_grain_unique",
        "PASS" if df.empty else "FAIL",
        df.head(20).to_dict("records"),
    )


def validate_current_snapshot_loaded_at_single(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(DISTINCT current_snapshot_loaded_at) AS distinct_loaded_at
        FROM {TABLE_NAME}
    """
    df = query_df(conn, query)
    total = int(df.iloc[0]["distinct_loaded_at"])

    return validation_result(
        "single_current_snapshot_loaded_at",
        "PASS" if total == 1 else "FAIL",
        {
            "distinct_loaded_at": total,
        },
    )


def validate_source_row_count_reconciles(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            (SELECT COUNT(1)
             FROM {SOURCE_VIEW}
             WHERE etl_loaded_at = (SELECT MAX(etl_loaded_at) FROM {SOURCE_VIEW})
            ) AS source_current_rows,
            (SELECT COALESCE(SUM(source_row_count), 0)
             FROM {TABLE_NAME}
            ) AS aggregate_source_rows
    """
    df = query_df(conn, query)
    row = df.iloc[0]

    source_total = int(row["source_current_rows"])
    aggregate_total = int(row["aggregate_source_rows"])

    return validation_result(
        "source_row_count_reconciles",
        "PASS" if source_total == aggregate_total else "FAIL",
        {
            "source_current_rows": source_total,
            "aggregate_source_rows": aggregate_total,
        },
    )


def validate_stock_qty_reconciles(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            (SELECT COALESCE(SUM(stock_qty), 0)
             FROM {SOURCE_VIEW}
             WHERE etl_loaded_at = (SELECT MAX(etl_loaded_at) FROM {SOURCE_VIEW})
            ) AS source_current_stock_qty,
            (SELECT COALESCE(SUM(current_stock_qty), 0)
             FROM {TABLE_NAME}
            ) AS aggregate_current_stock_qty
    """
    df = query_df(conn, query)
    row = df.iloc[0]

    source_total = Decimal(str(row["source_current_stock_qty"]))
    aggregate_total = Decimal(str(row["aggregate_current_stock_qty"]))
    difference = abs(source_total - aggregate_total)
    tolerance = source_total.copy_abs().__mul__(AMOUNT_TOLERANCE_RATE)

    return validation_result(
        "current_stock_qty_reconciles",
        "PASS" if difference <= tolerance else "FAIL",
        {
            "source_current_stock_qty": str(source_total),
            "aggregate_current_stock_qty": str(aggregate_total),
            "difference": str(difference),
            "tolerance": str(tolerance),
        },
    )


def validate_date_fk(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS orphan_date_rows
        FROM {TABLE_NAME} a
        LEFT JOIN dim_time d
            ON a.snapshot_date_key = d.date_key
        WHERE a.snapshot_date_key IS NOT NULL
          AND d.date_key IS NULL
    """
    df = query_df(conn, query)
    total = int(df.iloc[0]["orphan_date_rows"])

    return validation_result(
        "date_fk_valid",
        "PASS" if total == 0 else "FAIL",
        {
            "orphan_date_rows": total,
        },
    )


def validate_product_fk(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS orphan_product_rows
        FROM {TABLE_NAME} a
        LEFT JOIN dim_product d
            ON a.product_analytical_key = d.product_analytical_key
        WHERE a.product_analytical_key IS NOT NULL
          AND d.product_analytical_key IS NULL
    """
    df = query_df(conn, query)
    total = int(df.iloc[0]["orphan_product_rows"])

    return validation_result(
        "product_fk_valid",
        "PASS" if total == 0 else "FAIL",
        {
            "orphan_product_rows": total,
        },
    )


def validate_only_physical_location_type(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS bad_rows
        FROM {TABLE_NAME}
        WHERE location_usage_type <> 'internal_or_unknown'
           OR location_usage_type IS NULL
    """
    df = query_df(conn, query)
    total = int(df.iloc[0]["bad_rows"])

    return validation_result(
        "only_physical_location_type",
        "PASS" if total == 0 else "FAIL",
        {
            "bad_rows": total,
        },
    )


def validate_negative_business_rows_excluded(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS bad_rows
        FROM {TABLE_NAME}
        WHERE current_stock_qty < 0
          AND include_in_business_views = TRUE
    """
    df = query_df(conn, query)
    total = int(df.iloc[0]["bad_rows"])

    return validation_result(
        "negative_current_stock_excluded_from_business_views",
        "PASS" if total == 0 else "FAIL",
        {
            "bad_rows": total,
        },
    )


def validate_excluded_rows_have_reason(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS bad_rows
        FROM {TABLE_NAME}
        WHERE include_in_business_views = FALSE
          AND (
                exclude_reason IS NULL
             OR TRIM(exclude_reason) = ''
          )
    """
    df = query_df(conn, query)
    total = int(df.iloc[0]["bad_rows"])

    return validation_result(
        "excluded_rows_have_reason",
        "PASS" if total == 0 else "FAIL",
        {
            "bad_rows": total,
        },
    )


def validate_business_inclusion_distribution(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            include_in_business_views,
            COUNT(1) AS total_rows
        FROM {TABLE_NAME}
        GROUP BY include_in_business_views
        ORDER BY include_in_business_views
    """
    df = query_df(conn, query)

    return validation_result(
        "business_inclusion_distribution_available",
        "PASS" if not df.empty else "FAIL",
        df.to_dict("records"),
    )


def validate_review_status_distribution(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            aggregate_review_status,
            COUNT(1) AS total_rows
        FROM {TABLE_NAME}
        GROUP BY aggregate_review_status
        ORDER BY aggregate_review_status
    """
    df = query_df(conn, query)

    return validation_result(
        "aggregate_review_status_distribution_available",
        "PASS" if not df.empty else "FAIL",
        df.to_dict("records"),
    )


def print_result(result: Dict[str, Any]) -> None:
    print(f"{result['validation']}: {result['status']}")

    details = result.get("details")

    if details not in (None, [], {}):
        print(details)


def main() -> int:
    print("=====================================================")
    print("ANALYTICS INVENTORY CURRENT PRODUCT LOCATION VALIDATION START")
    print("=====================================================")

    conn = get_db_connection()
    results: List[Dict[str, Any]] = []

    try:
        source_result = validate_source_view_exists(conn)
        exists_result = validate_table_exists(conn)
        results.append(source_result)
        results.append(exists_result)

        if source_result["status"] == "PASS" and exists_result["status"] == "PASS":
            results.extend(
                [
                    validate_row_count(conn),
                    validate_unique_grain(conn),
                    validate_current_snapshot_loaded_at_single(conn),
                    validate_source_row_count_reconciles(conn),
                    validate_stock_qty_reconciles(conn),
                    validate_date_fk(conn),
                    validate_product_fk(conn),
                    validate_only_physical_location_type(conn),
                    validate_negative_business_rows_excluded(conn),
                    validate_excluded_rows_have_reason(conn),
                    validate_business_inclusion_distribution(conn),
                    validate_review_status_distribution(conn),
                ]
            )

        print()
        print("-----------------------------------------------------")
        print("VALIDATION DETAILS")
        print("-----------------------------------------------------")

        for result in results:
            print_result(result)

        total = len(results)
        passed = sum(1 for result in results if result["status"] == "PASS")
        failed = total - passed

        print()
        print("-----------------------------------------------------")
        print("SUMMARY COUNTS")
        print("-----------------------------------------------------")
        print(f"total_validations: {total}")
        print(f"passed: {passed}")
        print(f"failed: {failed}")

        if failed == 0:
            print()
            print("VALIDATION RESULT: PASSED")
            return 0

        print()
        print("VALIDATION RESULT: FAILED")
        print("Failed validations:")

        for result in results:
            if result["status"] != "PASS":
                print(f"- {result['validation']}")

        return 1

    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
