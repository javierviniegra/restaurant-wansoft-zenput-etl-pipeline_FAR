"""
Validate analytics_purchase_orders.

Validation goals:
- table exists
- row count matches distinct source order groups from analytics_purchase_order_lines
- source order identity is unique
- line counts reconcile to analytics_purchase_order_lines
- amount totals reconcile to analytics_purchase_order_lines
- business and excluded line counts reconcile
- company, date and vendor references are valid when populated
- excluded orders have exclusion reason
- source system distribution reconciles
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

import pandas as pd

from core.database.mysql import get_db_connection


TABLE_NAME = "analytics_purchase_orders"
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
        "analytics_purchase_orders_exists",
        "PASS" if exists else "FAIL",
        {
            "table_name": TABLE_NAME,
            "exists": exists,
        },
    )


def validate_row_count_matches_order_groups(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            (
                SELECT COUNT(1)
                FROM (
                    SELECT
                        source_system,
                        COALESCE(source_order_id, CONCAT('__missing__:', canonical_purchase_order_line_id)) AS source_order_id
                    FROM {SOURCE_TABLE}
                    GROUP BY
                        source_system,
                        COALESCE(source_order_id, CONCAT('__missing__:', canonical_purchase_order_line_id))
                ) x
            ) AS expected_orders,
            (SELECT COUNT(1) FROM {TABLE_NAME}) AS analytics_orders
    """
    df = query_df(conn, query)
    row = df.iloc[0]

    expected_orders = int(row["expected_orders"])
    analytics_orders = int(row["analytics_orders"])

    return validation_result(
        "row_count_matches_order_groups",
        "PASS" if expected_orders == analytics_orders else "FAIL",
        {
            "expected_orders": expected_orders,
            "analytics_orders": analytics_orders,
        },
    )


def validate_unique_source_order(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            source_system,
            source_order_id,
            COUNT(1) AS total_rows
        FROM {TABLE_NAME}
        GROUP BY
            source_system,
            source_order_id
        HAVING COUNT(1) > 1
    """
    df = query_df(conn, query)

    return validation_result(
        "source_order_identity_unique",
        "PASS" if df.empty else "FAIL",
        df.head(20).to_dict("records"),
    )


def validate_line_count_reconciliation(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            (SELECT COUNT(1) FROM {SOURCE_TABLE}) AS line_fact_rows,
            (SELECT COALESCE(SUM(line_count), 0) FROM {TABLE_NAME}) AS order_fact_line_count
    """
    df = query_df(conn, query)
    row = df.iloc[0]

    line_fact_rows = int(row["line_fact_rows"])
    order_fact_line_count = int(row["order_fact_line_count"])

    return validation_result(
        "line_count_reconciles",
        "PASS" if line_fact_rows == order_fact_line_count else "FAIL",
        {
            "line_fact_rows": line_fact_rows,
            "order_fact_line_count": order_fact_line_count,
        },
    )


def validate_business_line_count_reconciliation(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            (
                SELECT COUNT(1)
                FROM {SOURCE_TABLE}
                WHERE include_in_business_views = TRUE
            ) AS business_line_rows,
            (SELECT COALESCE(SUM(business_line_count), 0) FROM {TABLE_NAME}) AS order_business_line_count
    """
    df = query_df(conn, query)
    row = df.iloc[0]

    business_line_rows = int(row["business_line_rows"])
    order_business_line_count = int(row["order_business_line_count"])

    return validation_result(
        "business_line_count_reconciles",
        "PASS" if business_line_rows == order_business_line_count else "FAIL",
        {
            "business_line_rows": business_line_rows,
            "order_business_line_count": order_business_line_count,
        },
    )


def validate_excluded_line_count_reconciliation(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            (
                SELECT COUNT(1)
                FROM {SOURCE_TABLE}
                WHERE include_in_business_views = FALSE
            ) AS excluded_line_rows,
            (SELECT COALESCE(SUM(excluded_line_count), 0) FROM {TABLE_NAME}) AS order_excluded_line_count
    """
    df = query_df(conn, query)
    row = df.iloc[0]

    excluded_line_rows = int(row["excluded_line_rows"])
    order_excluded_line_count = int(row["order_excluded_line_count"])

    return validation_result(
        "excluded_line_count_reconciles",
        "PASS" if excluded_line_rows == order_excluded_line_count else "FAIL",
        {
            "excluded_line_rows": excluded_line_rows,
            "order_excluded_line_count": order_excluded_line_count,
        },
    )


def validate_price_total_reconciliation(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            (SELECT COALESCE(SUM(price_total), 0) FROM {SOURCE_TABLE}) AS line_price_total,
            (SELECT COALESCE(SUM(price_total_total), 0) FROM {TABLE_NAME}) AS order_price_total
    """
    df = query_df(conn, query)
    row = df.iloc[0]

    line_price_total = Decimal(str(row["line_price_total"]))
    order_price_total = Decimal(str(row["order_price_total"]))
    difference = abs(line_price_total - order_price_total)
    tolerance = line_price_total.copy_abs().__mul__(AMOUNT_TOLERANCE_RATE)

    status = "PASS" if difference <= tolerance else "FAIL"

    return validation_result(
        "price_total_reconciles_with_lines",
        status,
        {
            "line_price_total": str(line_price_total),
            "order_price_total": str(order_price_total),
            "difference": str(difference),
            "tolerance": str(tolerance),
        },
    )


def validate_company_fk(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS orphan_company_orders
        FROM {TABLE_NAME} a
        LEFT JOIN dim_company_analytical d
            ON a.company_source_key = d.company_source_key
        WHERE a.company_source_key IS NOT NULL
          AND d.company_source_key IS NULL
    """
    df = query_df(conn, query)
    total = int(df.iloc[0]["orphan_company_orders"])

    return validation_result(
        "company_fk_valid",
        "PASS" if total == 0 else "FAIL",
        {
            "orphan_company_orders": total,
        },
    )


def validate_date_fk(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS orphan_date_orders
        FROM {TABLE_NAME} a
        LEFT JOIN dim_time d
            ON a.order_date_key = d.date_key
        WHERE a.order_date_key IS NOT NULL
          AND d.date_key IS NULL
    """
    df = query_df(conn, query)
    total = int(df.iloc[0]["orphan_date_orders"])

    return validation_result(
        "date_fk_valid",
        "PASS" if total == 0 else "FAIL",
        {
            "orphan_date_orders": total,
        },
    )


def validate_vendor_fk(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS orphan_vendor_orders
        FROM {TABLE_NAME} a
        LEFT JOIN dim_vendor d
            ON a.vendor_analytical_key = d.vendor_analytical_key
        WHERE a.vendor_analytical_key IS NOT NULL
          AND d.vendor_analytical_key IS NULL
    """
    df = query_df(conn, query)
    total = int(df.iloc[0]["orphan_vendor_orders"])

    return validation_result(
        "vendor_fk_valid",
        "PASS" if total == 0 else "FAIL",
        {
            "orphan_vendor_orders": total,
        },
    )


def validate_excluded_orders_have_reason(conn: Any) -> Dict[str, Any]:
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
        "excluded_orders_have_reason",
        "PASS" if total == 0 else "FAIL",
        {
            "bad_rows": total,
        },
    )


def validate_source_system_distribution(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            c.source_system,
            c.expected_orders,
            COALESCE(a.analytics_orders, 0) AS analytics_orders
        FROM (
            SELECT
                source_system,
                COUNT(1) AS expected_orders
            FROM (
                SELECT
                    source_system,
                    COALESCE(source_order_id, CONCAT('__missing__:', canonical_purchase_order_line_id)) AS source_order_id
                FROM {SOURCE_TABLE}
                GROUP BY
                    source_system,
                    COALESCE(source_order_id, CONCAT('__missing__:', canonical_purchase_order_line_id))
            ) x
            GROUP BY source_system
        ) c
        LEFT JOIN (
            SELECT
                source_system,
                COUNT(1) AS analytics_orders
            FROM {TABLE_NAME}
            GROUP BY source_system
        ) a
            ON a.source_system = c.source_system
    """
    df = query_df(conn, query)
    bad = df[df["expected_orders"] != df["analytics_orders"]]

    return validation_result(
        "source_system_distribution_reconciles",
        "PASS" if bad.empty else "FAIL",
        bad.to_dict("records"),
    )


def validate_business_inclusion_distribution(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            include_in_business_views,
            COUNT(1) AS total_orders
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


def validate_order_review_status_distribution(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            order_review_status,
            COUNT(1) AS total_orders
        FROM {TABLE_NAME}
        GROUP BY order_review_status
        ORDER BY order_review_status
    """
    df = query_df(conn, query)

    return validation_result(
        "order_review_status_distribution_available",
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
    print("ANALYTICS PURCHASE ORDERS VALIDATION START")
    print("=====================================================")

    conn = get_db_connection()
    results: List[Dict[str, Any]] = []

    try:
        exists_result = validate_table_exists(conn)
        results.append(exists_result)

        if exists_result["status"] == "PASS":
            results.extend(
                [
                    validate_row_count_matches_order_groups(conn),
                    validate_unique_source_order(conn),
                    validate_line_count_reconciliation(conn),
                    validate_business_line_count_reconciliation(conn),
                    validate_excluded_line_count_reconciliation(conn),
                    validate_price_total_reconciliation(conn),
                    validate_company_fk(conn),
                    validate_date_fk(conn),
                    validate_vendor_fk(conn),
                    validate_excluded_orders_have_reason(conn),
                    validate_source_system_distribution(conn),
                    validate_business_inclusion_distribution(conn),
                    validate_order_review_status_distribution(conn),
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
