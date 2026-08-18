"""
Validate analytics_purchase_daily_company_product.

Validation goals:
- table exists
- table has rows
- grain is unique
- line counts reconcile to analytics_purchase_order_lines
- amount totals reconcile to analytics_purchase_order_lines
- company, date and product references are valid when populated
- excluded aggregate rows have exclusion reason
- business inclusion and review status distributions are available
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

import pandas as pd

from core.database.mysql import get_db_connection


TABLE_NAME = "analytics_purchase_daily_company_product"
SOURCE_TABLE = "analytics_purchase_order_lines"
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
    exists = table_exists(conn, TABLE_NAME)

    return validation_result(
        "analytics_purchase_daily_company_product_exists",
        "PASS" if exists else "FAIL",
        {
            "table_name": TABLE_NAME,
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
        "analytics_purchase_daily_company_product_has_rows",
        "PASS" if total_rows > 0 else "FAIL",
        {
            "total_rows": total_rows,
        },
    )


def validate_unique_grain(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            company_source_key,
            order_date_key,
            product_analytical_group_key,
            source_system,
            COUNT(1) AS total_rows
        FROM {TABLE_NAME}
        GROUP BY
            company_source_key,
            order_date_key,
            product_analytical_group_key,
            source_system
        HAVING COUNT(1) > 1
    """
    df = query_df(conn, query)

    return validation_result(
        "daily_company_product_grain_unique",
        "PASS" if df.empty else "FAIL",
        df.head(20).to_dict("records"),
    )


def validate_line_count_reconciles(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            (SELECT COUNT(1) FROM {SOURCE_TABLE}) AS source_line_count,
            (SELECT COALESCE(SUM(line_count), 0) FROM {TABLE_NAME}) AS aggregate_line_count
    """
    df = query_df(conn, query)
    row = df.iloc[0]

    source_line_count = int(row["source_line_count"])
    aggregate_line_count = int(row["aggregate_line_count"])

    return validation_result(
        "line_count_reconciles",
        "PASS" if source_line_count == aggregate_line_count else "FAIL",
        {
            "source_line_count": source_line_count,
            "aggregate_line_count": aggregate_line_count,
        },
    )


def validate_business_line_count_reconciles(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            (SELECT COUNT(1) FROM {SOURCE_TABLE} WHERE include_in_business_views = TRUE) AS source_business_line_count,
            (SELECT COALESCE(SUM(business_line_count), 0) FROM {TABLE_NAME}) AS aggregate_business_line_count
    """
    df = query_df(conn, query)
    row = df.iloc[0]

    source_total = int(row["source_business_line_count"])
    aggregate_total = int(row["aggregate_business_line_count"])

    return validation_result(
        "business_line_count_reconciles",
        "PASS" if source_total == aggregate_total else "FAIL",
        {
            "source_business_line_count": source_total,
            "aggregate_business_line_count": aggregate_total,
        },
    )


def validate_excluded_line_count_reconciles(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            (SELECT COUNT(1) FROM {SOURCE_TABLE} WHERE include_in_business_views = FALSE) AS source_excluded_line_count,
            (SELECT COALESCE(SUM(excluded_line_count), 0) FROM {TABLE_NAME}) AS aggregate_excluded_line_count
    """
    df = query_df(conn, query)
    row = df.iloc[0]

    source_total = int(row["source_excluded_line_count"])
    aggregate_total = int(row["aggregate_excluded_line_count"])

    return validation_result(
        "excluded_line_count_reconciles",
        "PASS" if source_total == aggregate_total else "FAIL",
        {
            "source_excluded_line_count": source_total,
            "aggregate_excluded_line_count": aggregate_total,
        },
    )


def amount_validation(
    conn: Any,
    source_expression: str,
    aggregate_column: str,
    name: str,
) -> Dict[str, Any]:
    query = f"""
        SELECT
            (SELECT COALESCE(SUM({source_expression}), 0) FROM {SOURCE_TABLE}) AS source_total,
            (SELECT COALESCE(SUM({aggregate_column}), 0) FROM {TABLE_NAME}) AS aggregate_total
    """
    df = query_df(conn, query)
    row = df.iloc[0]

    source_total = Decimal(str(row["source_total"]))
    aggregate_total = Decimal(str(row["aggregate_total"]))
    difference = abs(source_total - aggregate_total)
    tolerance = source_total.copy_abs().__mul__(AMOUNT_TOLERANCE_RATE)

    return validation_result(
        name,
        "PASS" if difference <= tolerance else "FAIL",
        {
            "source_total": str(source_total),
            "aggregate_total": str(aggregate_total),
            "difference": str(difference),
            "tolerance": str(tolerance),
        },
    )


def validate_price_total_reconciles(conn: Any) -> Dict[str, Any]:
    return amount_validation(
        conn,
        "price_total",
        "price_total_total",
        "price_total_reconciles",
    )


def validate_business_price_total_reconciles(conn: Any) -> Dict[str, Any]:
    return amount_validation(
        conn,
        "CASE WHEN include_in_business_views = TRUE THEN price_total ELSE 0 END",
        "business_price_total_total",
        "business_price_total_reconciles",
    )


def validate_excluded_price_total_reconciles(conn: Any) -> Dict[str, Any]:
    return amount_validation(
        conn,
        "CASE WHEN include_in_business_views = FALSE THEN price_total ELSE 0 END",
        "excluded_price_total_total",
        "excluded_price_total_reconciles",
    )


def validate_company_fk(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS orphan_company_rows
        FROM {TABLE_NAME} a
        LEFT JOIN dim_company_analytical d
            ON a.company_source_key = d.company_source_key
        WHERE a.company_source_key IS NOT NULL
          AND d.company_source_key IS NULL
    """
    df = query_df(conn, query)
    total = int(df.iloc[0]["orphan_company_rows"])

    return validation_result(
        "company_fk_valid",
        "PASS" if total == 0 else "FAIL",
        {
            "orphan_company_rows": total,
        },
    )


def validate_date_fk(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS orphan_date_rows
        FROM {TABLE_NAME} a
        LEFT JOIN dim_time d
            ON a.order_date_key = d.date_key
        WHERE a.order_date_key IS NOT NULL
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
    print("ANALYTICS PURCHASE DAILY COMPANY PRODUCT VALIDATION START")
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
                    validate_unique_grain(conn),
                    validate_line_count_reconciles(conn),
                    validate_business_line_count_reconciles(conn),
                    validate_excluded_line_count_reconciles(conn),
                    validate_price_total_reconciles(conn),
                    validate_business_price_total_reconciles(conn),
                    validate_excluded_price_total_reconciles(conn),
                    validate_company_fk(conn),
                    validate_date_fk(conn),
                    validate_product_fk(conn),
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