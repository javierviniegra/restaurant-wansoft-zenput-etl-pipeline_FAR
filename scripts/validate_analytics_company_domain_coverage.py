"""
Validate analytics_company_domain_coverage.

Validation goals:
- table exists
- row count matches dim_company_analytical
- one row per company_source_key
- no missing dim rows
- key examples behave as expected
- coverage_status values are valid
- count fields are non-negative
"""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from core.database.mysql import get_db_connection


TABLE_NAME = "analytics_company_domain_coverage"
DIM_TABLE = "dim_company_analytical"

VALID_COVERAGE_STATUS = {
    "multi_domain",
    "purchases_only",
    "inventory_only",
    "zenput_only_location",
    "zenput_activity_only",
    "future_with_zenput_activity",
    "future_no_activity",
    "internal_provider",
    "no_domain_activity",
    "pending_review",
}


def query_df(conn, query: str, params: tuple | None = None) -> pd.DataFrame:
    return pd.read_sql(query, conn, params=params)


def table_exists(conn, table_name: str) -> bool:
    query = """
        SELECT COUNT(*) AS total
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = %s
    """
    df = query_df(conn, query, (table_name,))
    return bool(df.iloc[0]["total"] > 0)


def validation_result(name: str, status: str, details: Any = None) -> Dict[str, Any]:
    return {
        "validation": name,
        "status": status,
        "details": details,
    }


def validate_table_exists(conn) -> Dict[str, Any]:
    exists = table_exists(conn, TABLE_NAME)

    return validation_result(
        "analytics_company_domain_coverage_exists",
        "PASS" if exists else "FAIL",
        {"table_name": TABLE_NAME, "exists": exists},
    )


def validate_row_count_matches_dim(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            (SELECT COUNT(*) FROM {TABLE_NAME}) AS analytics_rows,
            (SELECT COUNT(*) FROM {DIM_TABLE}) AS dim_rows
    """
    df = query_df(conn, query)
    row = df.iloc[0]

    analytics_rows = int(row["analytics_rows"])
    dim_rows = int(row["dim_rows"])

    return validation_result(
        "row_count_matches_dim_company_analytical",
        "PASS" if analytics_rows == dim_rows else "FAIL",
        {
            "analytics_rows": analytics_rows,
            "dim_rows": dim_rows,
        },
    )


def validate_unique_company_source_key(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            company_source_key,
            COUNT(*) AS total_rows
        FROM {TABLE_NAME}
        GROUP BY company_source_key
        HAVING COUNT(*) > 1
    """
    df = query_df(conn, query)

    return validation_result(
        "company_source_key_unique",
        "PASS" if df.empty else "FAIL",
        df.to_dict("records"),
    )


def validate_no_missing_dim_rows(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            d.company_source_key
        FROM {DIM_TABLE} d
        LEFT JOIN {TABLE_NAME} a
            ON a.company_source_key = d.company_source_key
        WHERE a.company_source_key IS NULL
    """
    df = query_df(conn, query)

    return validation_result(
        "all_dim_companies_represented",
        "PASS" if df.empty else "FAIL",
        df.to_dict("records"),
    )


def validate_valid_coverage_status(conn) -> Dict[str, Any]:
    query = f"""
        SELECT DISTINCT coverage_status
        FROM {TABLE_NAME}
    """
    df = query_df(conn, query)

    values = set(df["coverage_status"].dropna().tolist())
    invalid = sorted(values - VALID_COVERAGE_STATUS)

    return validation_result(
        "coverage_status_values_valid",
        "PASS" if not invalid else "FAIL",
        {
            "invalid_values": invalid,
            "valid_values": sorted(VALID_COVERAGE_STATUS),
        },
    )


def validate_non_negative_counts(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            company_source_key,
            purchase_order_count,
            purchase_line_count,
            inventory_snapshot_count,
            zenput_submission_count,
            zenput_task_count
        FROM {TABLE_NAME}
        WHERE purchase_order_count < 0
           OR purchase_line_count < 0
           OR inventory_snapshot_count < 0
           OR zenput_submission_count < 0
           OR zenput_task_count < 0
    """
    df = query_df(conn, query)

    return validation_result(
        "coverage_counts_non_negative",
        "PASS" if df.empty else "FAIL",
        df.to_dict("records"),
    )


def validate_required_examples(conn) -> Dict[str, Any]:
    required = [
        "Acoxpa",
        "Antenas",
        "CentroMyJ",
        "Puebla",
        "León",
        "Lindavista",
        "Perisur",
        "Bodegón",
        "Empanadas",
    ]

    placeholders = ", ".join(["%s"] * len(required))

    query = f"""
        SELECT
            company_source_key,
            coverage_status,
            is_internal_provider,
            is_zenput_only,
            has_zenput_submissions,
            has_purchases,
            has_inventory
        FROM {TABLE_NAME}
        WHERE company_source_key IN ({placeholders})
    """
    df = query_df(conn, query, tuple(required))

    found = set(df["company_source_key"].tolist())
    missing = sorted(set(required) - found)

    problems = []

    if missing:
        problems.append({"issue": "missing_required_examples", "missing": missing})

    by_key = {row["company_source_key"]: row for _, row in df.iterrows()}

    for key in ["León", "Lindavista", "Perisur"]:
        row = by_key.get(key)
        if row is None:
            continue

        if int(row["is_zenput_only"]) != 1:
            problems.append({"company_source_key": key, "issue": "is_zenput_only != true"})

        if row["coverage_status"] != "zenput_only_location":
            problems.append({"company_source_key": key, "issue": "coverage_status != zenput_only_location"})


    for key in ["Bodegón", "Empanadas"]:
        row = by_key.get(key)
        if row is None:
            continue

        if int(row["is_internal_provider"]) != 1:
            problems.append({"company_source_key": key, "issue": "is_internal_provider != true"})

        if row["coverage_status"] != "internal_provider":
            problems.append({"company_source_key": key, "issue": "coverage_status != internal_provider"})

    puebla = by_key.get("Puebla")
    if puebla is not None:
        if puebla["coverage_status"] not in {"future_with_zenput_activity", "future_no_activity"}:
            problems.append(
                {
                    "company_source_key": "Puebla",
                    "issue": "coverage_status should be future_with_zenput_activity or future_no_activity",
                    "actual": puebla["coverage_status"],
                }
            )

    return validation_result(
        "required_examples_valid",
        "PASS" if not problems else "FAIL",
        problems,
    )


def validate_purchase_flags_consistent(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            company_source_key,
            has_purchases,
            has_purchase_orders,
            has_purchase_lines,
            purchase_order_count,
            purchase_line_count
        FROM {TABLE_NAME}
        WHERE has_purchases <> (has_purchase_orders OR has_purchase_lines)
           OR has_purchase_orders <> (purchase_order_count > 0)
           OR has_purchase_lines <> (purchase_line_count > 0)
    """
    df = query_df(conn, query)

    return validation_result(
        "purchase_flags_consistent",
        "PASS" if df.empty else "FAIL",
        df.to_dict("records"),
    )


def validate_inventory_flags_consistent(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            company_source_key,
            has_inventory,
            inventory_snapshot_count
        FROM {TABLE_NAME}
        WHERE has_inventory <> (inventory_snapshot_count > 0)
    """
    df = query_df(conn, query)

    return validation_result(
        "inventory_flags_consistent",
        "PASS" if df.empty else "FAIL",
        df.to_dict("records"),
    )


def validate_zenput_flags_consistent(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            company_source_key,
            has_zenput_submissions,
            has_zenput_tasks,
            zenput_submission_count,
            zenput_task_count
        FROM {TABLE_NAME}
        WHERE has_zenput_submissions <> (zenput_submission_count > 0)
           OR has_zenput_tasks <> (zenput_task_count > 0)
    """
    df = query_df(conn, query)

    return validation_result(
        "zenput_flags_consistent",
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
    print("ANALYTICS COMPANY DOMAIN COVERAGE VALIDATION START")
    print("=====================================================")

    conn = get_db_connection()
    results: List[Dict[str, Any]] = []

    try:
        exists_result = validate_table_exists(conn)
        results.append(exists_result)

        if exists_result["status"] == "PASS":
            results.extend(
                [
                    validate_row_count_matches_dim(conn),
                    validate_unique_company_source_key(conn),
                    validate_no_missing_dim_rows(conn),
                    validate_valid_coverage_status(conn),
                    validate_non_negative_counts(conn),
                    validate_required_examples(conn),
                    validate_purchase_flags_consistent(conn),
                    validate_inventory_flags_consistent(conn),
                    validate_zenput_flags_consistent(conn),
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