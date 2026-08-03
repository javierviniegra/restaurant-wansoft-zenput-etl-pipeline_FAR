"""
Zenput Location Mapping Validator.

Purpose:
    Validate that Zenput location_name values found in MySQL are mapped
    through the centralized Zenput configuration.

This script is read-only.

It validates:
    - submissions table exists
    - submissions.location_name values are available
    - every location_name is mapped in core.config.zenput
    - Zenput-only locations are identified correctly
    - WansoftID metadata is available when applicable

Execution:
    python -m scripts.validate_zenput_location_mapping

Important:
    This script does not call the Zenput API.
    This script does not modify MySQL.
    This script does not update last_run_timestamp.txt.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

try:
    from core.database.mysql import get_db_connection
except ImportError:
    from core.database.mysql import get_mysql_connection as get_db_connection

from core.config.zenput import (
    get_zenput_company_source_key,
    get_zenput_wansoft_id_from_location,
    is_zenput_only_location,
    get_unmapped_zenput_locations,
)


DATABASE_TARGET = "zenput"


def now_iso():
    """
    Returns current local timestamp as string.
    """

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def print_section(title):
    """
    Prints a section header.
    """

    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def read_sql(query):
    """
    Executes a read-only SQL query against the Zenput MySQL target.
    """

    conn = get_db_connection(target=DATABASE_TARGET)

    try:
        df = pd.read_sql(query, conn)
    finally:
        conn.close()

    return df


def table_exists(table_name):
    """
    Returns True when the table exists in the current database.
    """

    query = f"""
    SELECT
        COUNT(*) AS table_count
    FROM information_schema.tables
    WHERE table_schema = DATABASE()
      AND table_name = '{table_name}'
    """

    df = read_sql(query)

    if df.empty:
        return False

    return int(df.iloc[0]["table_count"]) > 0


def print_df(df, empty_message="No rows returned."):
    """
    Prints a dataframe safely.
    """

    if df is None or df.empty:
        print(empty_message)
        return

    print(df.to_string(index=False))


def load_zenput_locations():
    """
    Loads distinct Zenput location_name values from submissions.
    """

    query = """
    SELECT
        location_name,
        COUNT(*) AS total_submissions,
        MIN(date_submitted) AS first_submission,
        MAX(date_submitted) AS last_submission
    FROM submissions
    WHERE location_name IS NOT NULL
    GROUP BY location_name
    ORDER BY location_name
    """

    return read_sql(query)


def validate_submissions_table(results):
    """
    Validates that the submissions table exists.
    """

    print_section("1. ZENPUT SUBMISSIONS TABLE")

    exists = table_exists("submissions")

    print(f"table_name: submissions")
    print(f"exists: {exists}")

    results["submissions_table_exists"] = exists

    print("\nValidation:")
    print(f"status: {'PASS' if exists else 'FAIL'}")


def validate_location_mapping(results):
    """
    Validates location_name values against core.config.zenput.
    """

    print_section("2. ZENPUT LOCATION MAPPING")

    if not table_exists("submissions"):
        print("Table not found: submissions")
        results["zenput_location_mapping_available"] = False
        print("\nValidation:")
        print("status: FAIL")
        return

    df = load_zenput_locations()

    if df.empty:
        print("No location_name values found in submissions.")
        results["zenput_location_mapping_available"] = False
        print("\nValidation:")
        print("status: FAIL")
        return

    rows = []

    for _, row in df.iterrows():
        location_name = row["location_name"]
        company_source_key = get_zenput_company_source_key(location_name)
        is_mapped = company_source_key is not None
        is_zenput_only = is_zenput_only_location(location_name)
        wansoft_id = get_zenput_wansoft_id_from_location(location_name)

        rows.append(
            {
                "location_name": location_name,
                "company_source_key": company_source_key,
                "is_mapped": is_mapped,
                "is_zenput_only": is_zenput_only,
                "wansoft_id": wansoft_id,
                "total_submissions": row["total_submissions"],
                "first_submission": row["first_submission"],
                "last_submission": row["last_submission"],
            }
        )

    output_df = pd.DataFrame(rows)

    print_df(output_df)

    location_names = set(df["location_name"].dropna().astype(str).tolist())
    unmapped_locations = get_unmapped_zenput_locations(location_names)

    passed = len(unmapped_locations) == 0

    results["zenput_location_mapping_available"] = passed

    print("\nValidation:")
    print(f"total_locations: {len(location_names)}")
    print(f"unmapped_locations: {sorted(unmapped_locations)}")
    print(f"status: {'PASS' if passed else 'FAIL'}")


def validate_zenput_only_locations(results):
    """
    Validates that Zenput-only locations are visible and classified.
    """

    print_section("3. ZENPUT-ONLY LOCATION CLASSIFICATION")

    if not table_exists("submissions"):
        print("Table not found: submissions")
        results["zenput_only_locations_classified"] = False
        print("\nValidation:")
        print("status: FAIL")
        return

    df = load_zenput_locations()

    if df.empty:
        print("No location_name values found in submissions.")
        results["zenput_only_locations_classified"] = False
        print("\nValidation:")
        print("status: FAIL")
        return

    rows = []

    for _, row in df.iterrows():
        location_name = row["location_name"]
        company_source_key = get_zenput_company_source_key(location_name)

        if is_zenput_only_location(location_name):
            rows.append(
                {
                    "location_name": location_name,
                    "company_source_key": company_source_key,
                    "classification": "zenput_only",
                    "total_submissions": row["total_submissions"],
                    "first_submission": row["first_submission"],
                    "last_submission": row["last_submission"],
                }
            )

    output_df = pd.DataFrame(rows)

    print_df(output_df, empty_message="No Zenput-only locations found in current submissions.")

    expected_zenput_only = {
        "León",
        "Lindavista",
        "Perisur",
    }

    found_zenput_only = set(output_df["company_source_key"].tolist()) if not output_df.empty else set()

    missing_expected = expected_zenput_only - found_zenput_only

    passed = len(missing_expected) == 0

    results["zenput_only_locations_classified"] = passed

    print("\nValidation:")
    print(f"expected_zenput_only: {sorted(expected_zenput_only)}")
    print(f"found_zenput_only: {sorted(found_zenput_only)}")
    print(f"missing_expected: {sorted(missing_expected)}")
    print(f"status: {'PASS' if passed else 'FAIL'}")


def validate_no_wansoft_filter_dependency(results):
    """
    Documents that Zenput mapping should not depend on is_wansoft_company.

    This is a governance validation by design.
    """

    print_section("4. ZENPUT GOVERNANCE RULE")

    rows = [
        {
            "rule": "Zenput location mapping must not depend on is_wansoft_company",
            "status": "required",
        },
        {
            "rule": "Zenput location_name must map to company_source_key through core.config.zenput",
            "status": "required",
        },
        {
            "rule": "Zenput-only locations must remain valid for Zenput operational reporting",
            "status": "required",
        },
    ]

    df = pd.DataFrame(rows)
    print_df(df)

    results["zenput_governance_rule_documented"] = True

    print("\nValidation:")
    print("status: PASS")


def print_final_summary(results):
    """
    Prints final validation summary.
    """

    print_section("FINAL ZENPUT LOCATION MAPPING VALIDATION SUMMARY")

    failed = []

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


def main():
    """
    Main validation entrypoint.
    """

    print("=====================================================")
    print("ZENPUT LOCATION MAPPING VALIDATION START")
    print("=====================================================")
    print(f"started_at: {now_iso()}")

    results = {}

    validate_submissions_table(results)
    validate_location_mapping(results)
    validate_zenput_only_locations(results)
    validate_no_wansoft_filter_dependency(results)

    exit_code = print_final_summary(results)

    print(f"\nfinished_at: {now_iso()}")
    print("=====================================================")
    print("ZENPUT LOCATION MAPPING VALIDATION END")
    print("=====================================================")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())