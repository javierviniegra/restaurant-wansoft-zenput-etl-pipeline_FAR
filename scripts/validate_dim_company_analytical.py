"""
Validate dim_company_analytical.

This script validates the shared analytical company dimension for the unified
analytical layer.

Validation goals:
- table exists
- company_source_key is unique
- required key companies exist
- Zenput-only locations are correctly classified
- Puebla is mapped and not Zenput-only
- internal providers are flagged
- migrated branches have operational_start_date
- controlled source-system values are valid
"""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from core.database.mysql import get_db_connection


TABLE_NAME = "dim_company_analytical"

REQUIRED_COMPANIES = {
    "Antenas",
    "La Esquina Coyoacán",
    "CentroMyJ",
    "Puebla",
    "León",
    "Lindavista",
    "Perisur",
}

ZENPUT_ONLY_COMPANIES = {
    "León",
    "Lindavista",
    "Perisur",
}

VALID_SOURCE_VALUES = {
    "purchases_source_system": {
        "wansoft",
        "odoo",
        "mixed_by_operational_start_date",
        "none",
        "pending",
        "not_applicable",
    },
    "inventory_source_system": {
        "wansoft",
        "odoo",
        "mixed_by_operational_start_date",
        "none",
        "pending",
        "not_applicable",
    },
    "sales_source_system": {
        "wansoft",
        "none",
        "pending",
        "not_applicable",
    },
    "zenput_source_status": {
        "mapped",
        "zenput_only",
        "not_detected",
        "pending",
        "not_applicable",
    },
}


def query_df(conn, query: str, params: tuple | None = None) -> pd.DataFrame:
    return pd.read_sql(query, conn, params=params)


def table_exists(conn) -> bool:
    query = """
        SELECT COUNT(*) AS total
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = %s
    """
    df = query_df(conn, query, (TABLE_NAME,))
    return bool(df.iloc[0]["total"] > 0)


def validation_result(name: str, status: str, details: Any = None) -> Dict[str, Any]:
    return {
        "validation": name,
        "status": status,
        "details": details,
    }


def validate_table_exists(conn) -> Dict[str, Any]:
    exists = table_exists(conn)
    return validation_result(
        "dim_company_analytical_exists",
        "PASS" if exists else "FAIL",
        {"table_name": TABLE_NAME, "exists": exists},
    )


def validate_row_count(conn) -> Dict[str, Any]:
    df = query_df(conn, f"SELECT COUNT(*) AS total_rows FROM {TABLE_NAME}")
    total = int(df.iloc[0]["total_rows"])

    return validation_result(
        "dim_company_analytical_has_rows",
        "PASS" if total > 0 else "FAIL",
        {"total_rows": total},
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


def validate_no_null_company_source_key(conn) -> Dict[str, Any]:
    query = f"""
        SELECT *
        FROM {TABLE_NAME}
        WHERE company_source_key IS NULL
           OR company_source_key = ''
    """
    df = query_df(conn, query)

    return validation_result(
        "company_source_key_not_null",
        "PASS" if df.empty else "FAIL",
        {"bad_rows": len(df)},
    )


def validate_required_companies(conn) -> Dict[str, Any]:
    placeholders = ", ".join(["%s"] * len(REQUIRED_COMPANIES))
    query = f"""
        SELECT company_source_key
        FROM {TABLE_NAME}
        WHERE company_source_key IN ({placeholders})
    """
    df = query_df(conn, query, tuple(REQUIRED_COMPANIES))

    found = set(df["company_source_key"].tolist())
    missing = sorted(REQUIRED_COMPANIES - found)

    return validation_result(
        "required_companies_exist",
        "PASS" if not missing else "FAIL",
        {
            "required": sorted(REQUIRED_COMPANIES),
            "found": sorted(found),
            "missing": missing,
        },
    )


def validate_zenput_only_classification(conn) -> Dict[str, Any]:
    placeholders = ", ".join(["%s"] * len(ZENPUT_ONLY_COMPANIES))
    query = f"""
        SELECT
            company_source_key,
            is_zenput_location,
            is_zenput_only,
            zenput_source_status
        FROM {TABLE_NAME}
        WHERE company_source_key IN ({placeholders})
    """
    df = query_df(conn, query, tuple(ZENPUT_ONLY_COMPANIES))

    bad = []

    for company in ZENPUT_ONLY_COMPANIES:
        subset = df[df["company_source_key"] == company]

        if subset.empty:
            bad.append({"company_source_key": company, "issue": "missing"})
            continue

        row = subset.iloc[0]

        if int(row["is_zenput_location"]) != 1:
            bad.append({"company_source_key": company, "issue": "is_zenput_location != true"})

        if int(row["is_zenput_only"]) != 1:
            bad.append({"company_source_key": company, "issue": "is_zenput_only != true"})

        if row["zenput_source_status"] != "zenput_only":
            bad.append({"company_source_key": company, "issue": "zenput_source_status != zenput_only"})

    return validation_result(
        "zenput_only_companies_classified",
        "PASS" if not bad else "FAIL",
        bad,
    )


def validate_puebla_classification(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            company_source_key,
            is_zenput_location,
            is_zenput_only,
            zenput_source_status,
            rollout_type,
            rollout_status
        FROM {TABLE_NAME}
        WHERE company_source_key = 'Puebla'
    """
    df = query_df(conn, query)

    if df.empty:
        return validation_result(
            "puebla_classification",
            "FAIL",
            {"issue": "Puebla row missing"},
        )

    row = df.iloc[0]
    problems = []

    if int(row["is_zenput_location"]) != 1:
        problems.append("is_zenput_location != true")

    if int(row["is_zenput_only"]) != 0:
        problems.append("is_zenput_only != false")

    if row["zenput_source_status"] != "mapped":
        problems.append("zenput_source_status != mapped")

    if row["rollout_status"] not in {"future", "pending", "inactive"}:
        problems.append("rollout_status should be future/pending/inactive")

    return validation_result(
        "puebla_classification",
        "PASS" if not problems else "FAIL",
        {
            "row": row.to_dict(),
            "problems": problems,
        },
    )


def validate_internal_providers(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            company_source_key,
            display_name,
            is_internal_provider,
            include_in_business_views,
            exclude_reason
        FROM {TABLE_NAME}
        WHERE is_internal_provider = TRUE
           OR display_name IN ('EL BODEGON DE FITO', 'LAS EMPANADAS DE MARIA EVA')
           OR company_source_key IN ('Bodegón', 'Empanadas')
    """
    df = query_df(conn, query)

    required_display_names = {
        "EL BODEGON DE FITO",
        "LAS EMPANADAS DE MARIA EVA",
    }

    found_display_names = set(df["display_name"].tolist()) if not df.empty else set()
    missing = sorted(required_display_names - found_display_names)

    bad = []

    for _, row in df.iterrows():
        if int(row["is_internal_provider"]) != 1:
            bad.append({"company_source_key": row["company_source_key"], "issue": "is_internal_provider != true"})

        if int(row["include_in_business_views"]) != 0:
            bad.append({"company_source_key": row["company_source_key"], "issue": "include_in_business_views != false"})

        if row["exclude_reason"] != "internal_provider":
            bad.append({"company_source_key": row["company_source_key"], "issue": "exclude_reason != internal_provider"})

    status = "PASS" if not missing and not bad else "FAIL"

    return validation_result(
        "internal_providers_classified",
        status,
        {
            "missing_display_names": missing,
            "bad_rows": bad,
        },
    )


def validate_migrated_branches_operational_start_date(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            company_source_key,
            rollout_type,
            rollout_status,
            operational_start_date,
            purchases_source_system
        FROM {TABLE_NAME}
        WHERE company_source_key IN ('Antenas', 'La Esquina Coyoacán')
    """
    df = query_df(conn, query)

    bad = []

    for company in ["Antenas", "La Esquina Coyoacán"]:
        subset = df[df["company_source_key"] == company]

        if subset.empty:
            bad.append({"company_source_key": company, "issue": "missing"})
            continue

        row = subset.iloc[0]

        if row["rollout_type"] != "migrated_from_wansoft":
            bad.append({"company_source_key": company, "issue": "rollout_type != migrated_from_wansoft"})

        if pd.isna(row["operational_start_date"]):
            bad.append({"company_source_key": company, "issue": "operational_start_date is null"})

        if row["purchases_source_system"] != "mixed_by_operational_start_date":
            bad.append({"company_source_key": company, "issue": "purchases_source_system != mixed_by_operational_start_date"})

    return validation_result(
        "migrated_branches_operational_start_date",
        "PASS" if not bad else "FAIL",
        bad,
    )


def validate_source_value_domains(conn) -> Dict[str, Any]:
    bad = []

    for column_name, valid_values in VALID_SOURCE_VALUES.items():
        query = f"""
            SELECT DISTINCT {column_name} AS value
            FROM {TABLE_NAME}
        """
        df = query_df(conn, query)

        values = set(df["value"].dropna().tolist())
        invalid = sorted(values - valid_values)

        if invalid:
            bad.append(
                {
                    "column": column_name,
                    "invalid_values": invalid,
                    "valid_values": sorted(valid_values),
                }
            )

    return validation_result(
        "source_value_domains_valid",
        "PASS" if not bad else "FAIL",
        bad,
    )


def print_result(result: Dict[str, Any]) -> None:
    print(f"{result['validation']}: {result['status']}")

    details = result.get("details")

    if details not in (None, [], {}):
        print(details)


def main() -> int:
    print("=====================================================")
    print("DIM COMPANY ANALYTICAL VALIDATION START")
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
                    validate_unique_company_source_key(conn),
                    validate_no_null_company_source_key(conn),
                    validate_required_companies(conn),
                    validate_zenput_only_classification(conn),
                    validate_puebla_classification(conn),
                    validate_internal_providers(conn),
                    validate_migrated_branches_operational_start_date(conn),
                    validate_source_value_domains(conn),
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