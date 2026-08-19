
"""
Validate analytics_inventory_snapshot.

Validation goals:
- table exists
- row count equals odoo_inventory_snapshot
- source_inventory_snapshot_id is unique
- stock_qty reconciles to source
- snapshot_date_key is valid when populated
- product FK is valid when populated
- business inclusion distribution is available
- excluded rows have exclusion reason
- review status and location classification distributions are available
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

import pandas as pd

from core.database.mysql import get_db_connection


TARGET_TABLE = "analytics_inventory_snapshot"
SOURCE_TABLE = "odoo_inventory_snapshot"
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


def validate_table_exists(conn: Any) -> Dict[str, Any]:
    exists = table_exists(conn, TARGET_TABLE)
    return validation_result(
        "analytics_inventory_snapshot_exists",
        "PASS" if exists else "FAIL",
        {"table_name": TARGET_TABLE, "exists": exists},
    )


def validate_row_count(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            (SELECT COUNT(1) FROM {SOURCE_TABLE}) AS source_rows,
            (SELECT COUNT(1) FROM {TARGET_TABLE}) AS analytics_rows
    """
    df = query_df(conn, query)
    row = df.iloc[0]
    source_rows = int(row["source_rows"])
    analytics_rows = int(row["analytics_rows"])
    return validation_result(
        "row_count_matches_source",
        "PASS" if source_rows == analytics_rows else "FAIL",
        {"source_rows": source_rows, "analytics_rows": analytics_rows},
    )


def validate_source_id_unique(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            source_inventory_snapshot_id,
            COUNT(1) AS total_rows
        FROM {TARGET_TABLE}
        GROUP BY source_inventory_snapshot_id
        HAVING COUNT(1) > 1
    """
    df = query_df(conn, query)
    return validation_result(
        "source_inventory_snapshot_id_unique",
        "PASS" if df.empty else "FAIL",
        df.head(20).to_dict("records"),
    )


def validate_stock_qty_reconciles(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            (SELECT COALESCE(SUM(stock_qty), 0) FROM {SOURCE_TABLE}) AS source_stock_qty,
            (SELECT COALESCE(SUM(stock_qty), 0) FROM {TARGET_TABLE}) AS analytics_stock_qty
    """
    df = query_df(conn, query)
    row = df.iloc[0]

    source_total = Decimal(str(row["source_stock_qty"]))
    analytics_total = Decimal(str(row["analytics_stock_qty"]))
    difference = abs(source_total - analytics_total)
    tolerance = source_total.copy_abs().__mul__(AMOUNT_TOLERANCE_RATE)

    return validation_result(
        "stock_qty_reconciles",
        "PASS" if difference <= tolerance else "FAIL",
        {
            "source_stock_qty": str(source_total),
            "analytics_stock_qty": str(analytics_total),
            "difference": str(difference),
            "tolerance": str(tolerance),
        },
    )


def validate_date_fk(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS orphan_date_rows
        FROM {TARGET_TABLE} a
        LEFT JOIN dim_time d
            ON a.snapshot_date_key = d.date_key
        WHERE a.snapshot_date_key IS NOT NULL
          AND d.date_key IS NULL
    """
    df = query_df(conn, query)
    total = int(df.iloc[0]["orphan_date_rows"])
    return validation_result("date_fk_valid", "PASS" if total == 0 else "FAIL", {"orphan_date_rows": total})


def validate_product_fk(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS orphan_product_rows
        FROM {TARGET_TABLE} a
        LEFT JOIN dim_product d
            ON a.product_analytical_key = d.product_analytical_key
        WHERE a.product_analytical_key IS NOT NULL
          AND d.product_analytical_key IS NULL
    """
    df = query_df(conn, query)
    total = int(df.iloc[0]["orphan_product_rows"])
    return validation_result("product_fk_valid", "PASS" if total == 0 else "FAIL", {"orphan_product_rows": total})


def validate_excluded_rows_have_reason(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS bad_rows
        FROM {TARGET_TABLE}
        WHERE include_in_business_views = FALSE
          AND (exclude_reason IS NULL OR TRIM(exclude_reason) = '')
    """
    df = query_df(conn, query)
    total = int(df.iloc[0]["bad_rows"])
    return validation_result("excluded_rows_have_reason", "PASS" if total == 0 else "FAIL", {"bad_rows": total})


def validate_business_inclusion_distribution(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            include_in_business_views,
            COUNT(1) AS total_rows
        FROM {TARGET_TABLE}
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
            inventory_review_status,
            COUNT(1) AS total_rows
        FROM {TARGET_TABLE}
        GROUP BY inventory_review_status
        ORDER BY inventory_review_status
    """
    df = query_df(conn, query)
    return validation_result(
        "inventory_review_status_distribution_available",
        "PASS" if not df.empty else "FAIL",
        df.to_dict("records"),
    )


def validate_location_classification_distribution(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            location_usage_type,
            COUNT(1) AS total_rows
        FROM {TARGET_TABLE}
        GROUP BY location_usage_type
        ORDER BY location_usage_type
    """
    df = query_df(conn, query)
    return validation_result(
        "location_classification_distribution_available",
        "PASS" if not df.empty else "FAIL",
        df.to_dict("records"),
    )


def validate_company_not_forced(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS populated_company_rows
        FROM {TARGET_TABLE}
        WHERE company_source_key IS NOT NULL
    """
    df = query_df(conn, query)
    total = int(df.iloc[0]["populated_company_rows"])
    return validation_result(
        "company_mapping_not_forced",
        "PASS" if total == 0 else "FAIL",
        {"populated_company_rows": total},
    )


def print_result(result: Dict[str, Any]) -> None:
    print(f"{result['validation']}: {result['status']}")
    details = result.get("details")
    if details not in (None, [], {}):
        print(details)


def main() -> int:
    print("=====================================================")
    print("ANALYTICS INVENTORY SNAPSHOT VALIDATION START")
    print("=====================================================")

    conn = get_db_connection()
    results: List[Dict[str, Any]] = []

    try:
        exists_result = validate_table_exists(conn)
        results.append(exists_result)

        if exists_result["status"] == "PASS":
            results.extend(
                [
                    validate_row_count(conn),
                    validate_source_id_unique(conn),
                    validate_stock_qty_reconciles(conn),
                    validate_date_fk(conn),
                    validate_product_fk(conn),
                    validate_excluded_rows_have_reason(conn),
                    validate_business_inclusion_distribution(conn),
                    validate_review_status_distribution(conn),
                    validate_location_classification_distribution(conn),
                    validate_company_not_forced(conn),
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
