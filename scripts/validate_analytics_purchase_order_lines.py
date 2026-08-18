"""
Validate analytics_purchase_order_lines.

Validation goals:
- Table exists.
- Row count matches canonical_purchase_order_line_snapshot.
- canonical_purchase_order_line_id is unique.
- Source system distribution matches canonical.
- price_total reconciles with canonical within tolerance.
- Company, date, vendor and product references are valid when populated.
- Review-required product lines are excluded from business views.
- Internal vendor lines are excluded from business views.
- Excluded rows have an exclusion reason.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

import pandas as pd

from core.database.mysql import get_db_connection


TABLE_NAME = "analytics_purchase_order_lines"
SOURCE_TABLE = "canonical_purchase_order_line_snapshot"
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
        "analytics_purchase_order_lines_exists",
        "PASS" if exists else "FAIL",
        {
            "table_name": TABLE_NAME,
            "exists": exists,
        },
    )


def validate_row_count_matches_canonical(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            (SELECT COUNT(1) FROM {SOURCE_TABLE}) AS canonical_rows,
            (SELECT COUNT(1) FROM {TABLE_NAME}) AS analytics_rows
    """
    df = query_df(conn, query)
    row = df.iloc[0]

    canonical_rows = int(row["canonical_rows"])
    analytics_rows = int(row["analytics_rows"])

    return validation_result(
        "row_count_matches_canonical",
        "PASS" if canonical_rows == analytics_rows else "FAIL",
        {
            "canonical_rows": canonical_rows,
            "analytics_rows": analytics_rows,
        },
    )


def validate_unique_canonical_line_id(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            canonical_purchase_order_line_id,
            COUNT(1) AS total_rows
        FROM {TABLE_NAME}
        GROUP BY canonical_purchase_order_line_id
        HAVING COUNT(1) > 1
    """
    df = query_df(conn, query)

    return validation_result(
        "canonical_purchase_order_line_id_unique",
        "PASS" if df.empty else "FAIL",
        df.head(20).to_dict("records"),
    )


def validate_source_system_distribution(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            c.source_system,
            c.total_rows AS canonical_rows,
            COALESCE(a.total_rows, 0) AS analytics_rows
        FROM (
            SELECT
                source_system,
                COUNT(1) AS total_rows
            FROM {SOURCE_TABLE}
            GROUP BY source_system
        ) c
        LEFT JOIN (
            SELECT
                source_system,
                COUNT(1) AS total_rows
            FROM {TABLE_NAME}
            GROUP BY source_system
        ) a
            ON a.source_system = c.source_system
    """
    df = query_df(conn, query)
    bad = df[df["canonical_rows"] != df["analytics_rows"]]

    return validation_result(
        "source_system_distribution_matches_canonical",
        "PASS" if bad.empty else "FAIL",
        bad.to_dict("records"),
    )


def validate_price_total_reconciliation(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            (SELECT COALESCE(SUM(price_total), 0) FROM {SOURCE_TABLE}) AS canonical_price_total,
            (SELECT COALESCE(SUM(price_total), 0) FROM {TABLE_NAME}) AS analytics_price_total
    """
    df = query_df(conn, query)
    row = df.iloc[0]

    canonical_total = Decimal(str(row["canonical_price_total"]))
    analytics_total = Decimal(str(row["analytics_price_total"]))
    difference = abs(canonical_total - analytics_total)
    tolerance = canonical_total.copy_abs() * AMOUNT_TOLERANCE_RATE

    status = "PASS" if difference <= tolerance else "FAIL"

    return validation_result(
        "price_total_reconciles_with_canonical",
        status,
        {
            "canonical_price_total": str(canonical_total),
            "analytics_price_total": str(analytics_total),
            "difference": str(difference),
            "tolerance": str(tolerance),
        },
    )


def validate_company_fk(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS orphan_company_lines
        FROM {TABLE_NAME} a
        LEFT JOIN dim_company_analytical d
            ON a.company_source_key = d.company_source_key
        WHERE a.company_source_key IS NOT NULL
          AND d.company_source_key IS NULL
    """
    df = query_df(conn, query)
    total = int(df.iloc[0]["orphan_company_lines"])

    return validation_result(
        "company_fk_valid",
        "PASS" if total == 0 else "FAIL",
        {
            "orphan_company_lines": total,
        },
    )


def validate_date_fk(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS orphan_date_lines
        FROM {TABLE_NAME} a
        LEFT JOIN dim_time d
            ON a.order_date_key = d.date_key
        WHERE a.order_date_key IS NOT NULL
          AND d.date_key IS NULL
    """
    df = query_df(conn, query)
    total = int(df.iloc[0]["orphan_date_lines"])

    return validation_result(
        "date_fk_valid",
        "PASS" if total == 0 else "FAIL",
        {
            "orphan_date_lines": total,
        },
    )


def validate_vendor_fk(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS orphan_vendor_lines
        FROM {TABLE_NAME} a
        LEFT JOIN dim_vendor d
            ON a.vendor_analytical_key = d.vendor_analytical_key
        WHERE a.vendor_analytical_key IS NOT NULL
          AND d.vendor_analytical_key IS NULL
    """
    df = query_df(conn, query)
    total = int(df.iloc[0]["orphan_vendor_lines"])

    return validation_result(
        "vendor_fk_valid",
        "PASS" if total == 0 else "FAIL",
        {
            "orphan_vendor_lines": total,
        },
    )


def validate_product_fk(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS orphan_product_lines
        FROM {TABLE_NAME} a
        LEFT JOIN dim_product d
            ON a.product_analytical_key = d.product_analytical_key
        WHERE a.product_analytical_key IS NOT NULL
          AND d.product_analytical_key IS NULL
    """
    df = query_df(conn, query)
    total = int(df.iloc[0]["orphan_product_lines"])

    return validation_result(
        "product_fk_valid",
        "PASS" if total == 0 else "FAIL",
        {
            "orphan_product_lines": total,
        },
    )


def validate_review_required_products_excluded(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS bad_rows
        FROM {TABLE_NAME}
        WHERE is_product_review_required = TRUE
          AND include_in_business_views = TRUE
    """
    df = query_df(conn, query)
    total = int(df.iloc[0]["bad_rows"])

    return validation_result(
        "review_required_products_excluded",
        "PASS" if total == 0 else "FAIL",
        {
            "bad_rows": total,
        },
    )


def validate_internal_vendor_lines_excluded(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS bad_rows
        FROM {TABLE_NAME}
        WHERE is_internal_vendor = TRUE
          AND include_in_business_views = TRUE
    """
    df = query_df(conn, query)
    total = int(df.iloc[0]["bad_rows"])

    return validation_result(
        "internal_vendor_lines_excluded",
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


def validate_review_status_available(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            line_review_status,
            COUNT(1) AS total_rows
        FROM {TABLE_NAME}
        GROUP BY line_review_status
        ORDER BY line_review_status
    """
    df = query_df(conn, query)

    return validation_result(
        "line_review_status_distribution_available",
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
    print("ANALYTICS PURCHASE ORDER LINES VALIDATION START")
    print("=====================================================")

    conn = get_db_connection()
    results: List[Dict[str, Any]] = []

    try:
        exists_result = validate_table_exists(conn)
        results.append(exists_result)

        if exists_result["status"] == "PASS":
            results.extend(
                [
                    validate_row_count_matches_canonical(conn),
                    validate_unique_canonical_line_id(conn),
                    validate_source_system_distribution(conn),
                    validate_price_total_reconciliation(conn),
                    validate_company_fk(conn),
                    validate_date_fk(conn),
                    validate_vendor_fk(conn),
                    validate_product_fk(conn),
                    validate_review_required_products_excluded(conn),
                    validate_internal_vendor_lines_excluded(conn),
                    validate_business_inclusion_distribution(conn),
                    validate_excluded_rows_have_reason(conn),
                    validate_review_status_available(conn),
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
