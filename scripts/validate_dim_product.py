"""
Validate dim_product.

Validation goals:
- table exists
- table has rows
- source identity is unique
- product names are not null
- source_system values are valid
- product_identity_status values are valid
- mapping_status values are valid
- mapped products have approved mapping_status
- review-required flags are consistent
"""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from core.database.mysql import get_db_connection


TABLE_NAME = "dim_product"

SOURCE_SYSTEM_VALUES = {
    "wansoft",
    "odoo",
    "both",
    "backlog",
    "unknown",
}

PRODUCT_IDENTITY_STATUS_VALUES = {
    "mapped",
    "wansoft_only",
    "odoo_only",
    "unmapped",
    "pending_review",
    "historical_only",
    "excluded_scope",
    "unknown",
}

MAPPING_STATUS_VALUES = {
    "approved",
    "pending_review",
    "historical_only",
    "unmapped",
    "open_backlog",
    "unknown",
}


def query_df(conn, query: str, params: tuple | None = None) -> pd.DataFrame:
    return pd.read_sql(query, conn, params=params)


def validation_result(name: str, status: str, details: Any = None) -> Dict[str, Any]:
    return {
        "validation": name,
        "status": status,
        "details": details,
    }


def table_exists(conn) -> bool:
    query = """
        SELECT COUNT(*) AS total
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = %s
    """
    df = query_df(conn, query, (TABLE_NAME,))
    return bool(df.iloc[0]["total"] > 0)


def validate_table_exists(conn) -> Dict[str, Any]:
    exists = table_exists(conn)

    return validation_result(
        "dim_product_exists",
        "PASS" if exists else "FAIL",
        {"table_name": TABLE_NAME, "exists": exists},
    )


def validate_row_count(conn) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(*) AS total_rows
        FROM {TABLE_NAME}
    """
    df = query_df(conn, query)
    total_rows = int(df.iloc[0]["total_rows"])

    return validation_result(
        "dim_product_has_rows",
        "PASS" if total_rows > 0 else "FAIL",
        {"total_rows": total_rows},
    )


def validate_unique_source_identity(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            source_system,
            source_product_key,
            COUNT(*) AS total_rows
        FROM {TABLE_NAME}
        GROUP BY source_system, source_product_key
        HAVING COUNT(*) > 1
    """
    df = query_df(conn, query)

    return validation_result(
        "source_identity_unique",
        "PASS" if df.empty else "FAIL",
        df.to_dict("records"),
    )


def validate_no_null_product_names(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            product_analytical_key,
            product_display_name,
            normalized_product_name
        FROM {TABLE_NAME}
        WHERE product_display_name IS NULL
           OR product_display_name = ''
           OR normalized_product_name IS NULL
           OR normalized_product_name = ''
    """
    df = query_df(conn, query)

    return validation_result(
        "product_names_not_null",
        "PASS" if df.empty else "FAIL",
        df.to_dict("records"),
    )


def validate_no_null_source_product_key(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            product_analytical_key,
            product_display_name,
            source_system,
            source_product_key
        FROM {TABLE_NAME}
        WHERE source_product_key IS NULL
           OR source_product_key = ''
    """
    df = query_df(conn, query)

    return validation_result(
        "source_product_key_not_null",
        "PASS" if df.empty else "FAIL",
        df.to_dict("records"),
    )


def validate_source_system_values(conn) -> Dict[str, Any]:
    placeholders = ", ".join(["%s"] * len(SOURCE_SYSTEM_VALUES))

    query = f"""
        SELECT DISTINCT source_system
        FROM {TABLE_NAME}
        WHERE source_system NOT IN ({placeholders})
    """
    df = query_df(conn, query, tuple(SOURCE_SYSTEM_VALUES))

    return validation_result(
        "source_system_values_valid",
        "PASS" if df.empty else "FAIL",
        df.to_dict("records"),
    )


def validate_product_identity_status_values(conn) -> Dict[str, Any]:
    placeholders = ", ".join(["%s"] * len(PRODUCT_IDENTITY_STATUS_VALUES))

    query = f"""
        SELECT DISTINCT product_identity_status
        FROM {TABLE_NAME}
        WHERE product_identity_status NOT IN ({placeholders})
    """
    df = query_df(conn, query, tuple(PRODUCT_IDENTITY_STATUS_VALUES))

    return validation_result(
        "product_identity_status_values_valid",
        "PASS" if df.empty else "FAIL",
        df.to_dict("records"),
    )


def validate_mapping_status_values(conn) -> Dict[str, Any]:
    placeholders = ", ".join(["%s"] * len(MAPPING_STATUS_VALUES))

    query = f"""
        SELECT DISTINCT mapping_status
        FROM {TABLE_NAME}
        WHERE mapping_status NOT IN ({placeholders})
    """
    df = query_df(conn, query, tuple(MAPPING_STATUS_VALUES))

    return validation_result(
        "mapping_status_values_valid",
        "PASS" if df.empty else "FAIL",
        df.to_dict("records"),
    )


def validate_mapped_products_have_approved_status(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            product_analytical_key,
            product_display_name,
            source_system,
            source_product_key,
            mapping_status,
            is_mapped
        FROM {TABLE_NAME}
        WHERE is_mapped = TRUE
          AND mapping_status <> 'approved'
    """
    df = query_df(conn, query)

    return validation_result(
        "mapped_products_have_approved_status",
        "PASS" if df.empty else "FAIL",
        df.to_dict("records"),
    )


def validate_review_required_consistency(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            product_analytical_key,
            product_display_name,
            product_identity_status,
            mapping_status,
            is_review_required,
            include_in_business_views
        FROM {TABLE_NAME}
        WHERE (
                product_identity_status IN ('pending_review', 'unmapped', 'unknown')
             OR mapping_status IN ('pending_review', 'open_backlog', 'unmapped')
          )
          AND is_review_required <> TRUE
    """
    df = query_df(conn, query)

    return validation_result(
        "review_required_consistency",
        "PASS" if df.empty else "FAIL",
        df.to_dict("records"),
    )


def validate_review_required_excluded_from_business_views(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            product_analytical_key,
            product_display_name,
            product_identity_status,
            mapping_status,
            is_review_required,
            include_in_business_views
        FROM {TABLE_NAME}
        WHERE is_review_required = TRUE
          AND include_in_business_views = TRUE
    """
    df = query_df(conn, query)

    return validation_result(
        "review_required_excluded_from_business_views",
        "PASS" if df.empty else "FAIL",
        df.to_dict("records"),
    )


def validate_no_name_based_unique_constraint(conn) -> Dict[str, Any]:
    query = """
        SELECT
            constraint_name,
            column_name
        FROM information_schema.key_column_usage
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND constraint_name <> 'PRIMARY'
          AND column_name = 'normalized_product_name'
    """
    df = query_df(conn, query, (TABLE_NAME,))

    return validation_result(
        "no_unique_identity_on_normalized_product_name",
        "PASS" if df.empty else "FAIL",
        df.to_dict("records"),
    )


def print_result(result: Dict[str, Any]) -> None:
    print(f"{result['validation']}: {result['status']}")

    details = result.get("details")

    if details not in (None, [], {}):
        print(details)


def main() -> int:
    print("=====================================================")
    print("DIM PRODUCT VALIDATION START")
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
                    validate_unique_source_identity(conn),
                    validate_no_null_product_names(conn),
                    validate_no_null_source_product_key(conn),
                    validate_source_system_values(conn),
                    validate_product_identity_status_values(conn),
                    validate_mapping_status_values(conn),
                    validate_mapped_products_have_approved_status(conn),
                    validate_review_required_consistency(conn),
                    validate_review_required_excluded_from_business_views(conn),
                    validate_no_name_based_unique_constraint(conn),
                ]
            )

        print()
        print("-----------------------------------------------------")
        print("VALIDATION DETAILS")
        print("-----------------------------------------------------")

        for result in results:
            print_result(result)

        total = len(results)
        passed = sum(1 for r in results if r["status"] == "PASS")
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