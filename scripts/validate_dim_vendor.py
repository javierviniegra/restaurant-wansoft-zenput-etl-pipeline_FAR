"""
Validate dim_vendor.

Validation goals:
- table exists
- table has rows
- normalized_vendor_name is unique
- vendor names are not null
- internal vendors are present and correctly classified
- vendor_source_system values are valid
- internal vendor business view flags are correct
"""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from core.database.mysql import get_db_connection


TABLE_NAME = "dim_vendor"

VALID_VENDOR_SOURCE_SYSTEMS = {
    "wansoft",
    "odoo",
    "both",
    "unknown",
}

REQUIRED_INTERNAL_VENDORS = {
    "EL BODEGON DE FITO": "Bodegón",
    "LAS EMPANADAS DE MARIA EVA": "Empanadas",
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
        "dim_vendor_exists",
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
        "dim_vendor_has_rows",
        "PASS" if total_rows > 0 else "FAIL",
        {"total_rows": total_rows},
    )


def validate_unique_normalized_vendor_name(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            normalized_vendor_name,
            COUNT(*) AS total_rows
        FROM {TABLE_NAME}
        GROUP BY normalized_vendor_name
        HAVING COUNT(*) > 1
    """
    df = query_df(conn, query)

    return validation_result(
        "normalized_vendor_name_unique",
        "PASS" if df.empty else "FAIL",
        df.to_dict("records"),
    )


def validate_no_null_vendor_names(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            vendor_analytical_key,
            vendor_display_name,
            normalized_vendor_name
        FROM {TABLE_NAME}
        WHERE vendor_display_name IS NULL
           OR vendor_display_name = ''
           OR normalized_vendor_name IS NULL
           OR normalized_vendor_name = ''
    """
    df = query_df(conn, query)

    return validation_result(
        "vendor_names_not_null",
        "PASS" if df.empty else "FAIL",
        df.to_dict("records"),
    )


def validate_source_system_values(conn) -> Dict[str, Any]:
    placeholders = ", ".join(["%s"] * len(VALID_VENDOR_SOURCE_SYSTEMS))

    query = f"""
        SELECT DISTINCT vendor_source_system
        FROM {TABLE_NAME}
        WHERE vendor_source_system NOT IN ({placeholders})
    """
    df = query_df(conn, query, tuple(VALID_VENDOR_SOURCE_SYSTEMS))

    return validation_result(
        "vendor_source_system_values_valid",
        "PASS" if df.empty else "FAIL",
        df.to_dict("records"),
    )


def validate_internal_vendors(conn) -> Dict[str, Any]:
    problems = []

    for legal_name, canonical_name in REQUIRED_INTERNAL_VENDORS.items():
        query = f"""
            SELECT
                vendor_analytical_key,
                vendor_display_name,
                vendor_canonical_name,
                normalized_vendor_name,
                is_internal_vendor,
                is_external_vendor,
                include_in_business_views,
                exclude_reason
            FROM {TABLE_NAME}
            WHERE vendor_display_name = %s
               OR vendor_canonical_name = %s
               OR normalized_vendor_name = UPPER(%s)
        """
        df = query_df(conn, query, (legal_name, canonical_name, legal_name))

        if df.empty:
            problems.append(
                {
                    "vendor": legal_name,
                    "issue": "missing internal vendor",
                }
            )
            continue

        row = df.iloc[0]

        if int(row["is_internal_vendor"]) != 1:
            problems.append(
                {
                    "vendor": legal_name,
                    "issue": "is_internal_vendor != true",
                }
            )

        if int(row["is_external_vendor"]) != 0:
            problems.append(
                {
                    "vendor": legal_name,
                    "issue": "is_external_vendor != false",
                }
            )

        if int(row["include_in_business_views"]) != 0:
            problems.append(
                {
                    "vendor": legal_name,
                    "issue": "include_in_business_views != false",
                }
            )

        if row["exclude_reason"] != "internal_vendor":
            problems.append(
                {
                    "vendor": legal_name,
                    "issue": "exclude_reason != internal_vendor",
                }
            )

    return validation_result(
        "internal_vendors_classified",
        "PASS" if not problems else "FAIL",
        problems,
    )


def validate_internal_vendor_business_flags(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            vendor_analytical_key,
            vendor_display_name,
            vendor_canonical_name,
            is_internal_vendor,
            is_external_vendor,
            include_in_business_views,
            exclude_reason
        FROM {TABLE_NAME}
        WHERE is_internal_vendor = TRUE
          AND (
                is_external_vendor <> FALSE
             OR include_in_business_views <> FALSE
             OR exclude_reason <> 'internal_vendor'
          )
    """
    df = query_df(conn, query)

    return validation_result(
        "internal_vendor_business_flags_valid",
        "PASS" if df.empty else "FAIL",
        df.to_dict("records"),
    )


def validate_boolean_consistency(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            vendor_analytical_key,
            vendor_display_name,
            is_internal_vendor,
            is_external_vendor
        FROM {TABLE_NAME}
        WHERE is_internal_vendor = TRUE
          AND is_external_vendor = TRUE
    """
    df = query_df(conn, query)

    return validation_result(
        "vendor_boolean_consistency",
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
    print("DIM VENDOR VALIDATION START")
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
                    validate_unique_normalized_vendor_name(conn),
                    validate_no_null_vendor_names(conn),
                    validate_source_system_values(conn),
                    validate_internal_vendors(conn),
                    validate_internal_vendor_business_flags(conn),
                    validate_boolean_consistency(conn),
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