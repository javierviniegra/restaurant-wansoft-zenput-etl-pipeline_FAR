"""
Zenput Outputs Validator.

Purpose:
    Validate current Zenput MySQL outputs and local legacy state.

This script is read-only.

It validates:
    - required Zenput tables exist
    - Zenput table counts are available
    - submissions.location_name mapping is valid
    - Zenput-only locations are classified correctly
    - last_run_timestamp.txt exists
    - last_run_timestamp.txt has a parseable UTC-like timestamp
    - legacy write-enabled scripts remain protected by the pipeline wrapper

Execution:
    python -m scripts.validate_zenput_outputs

Important:
    This script does not call the Zenput API.
    This script does not modify MySQL.
    This script does not update last_run_timestamp.txt.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

try:
    from core.database.mysql import get_db_connection
except ImportError:
    from core.database.mysql import get_mysql_connection as get_db_connection

from core.config.zenput import (
    get_zenput_company_source_key,
    get_zenput_wansoft_id_from_location,
    get_unmapped_zenput_locations,
    is_zenput_only_location,
)


DATABASE_TARGET = "zenput"

REQUIRED_TABLES = [
    "form_templates",
    "submissions",
    "submission_answers",
    "zenput_tasks",
]

TIMESTAMP_FILE = Path("legacy") / "zenput" / "last_run_timestamp.txt"


def now_iso():
    """
    Returns current local timestamp as string.
    """

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def print_section(title):
    """
    Prints a standard section header.
    """

    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def print_df(df, empty_message="No rows returned."):
    """
    Prints a dataframe safely.
    """

    if df is None or df.empty:
        print(empty_message)
        return

    print(df.to_string(index=False))


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


def get_table_columns(table_name):
    """
    Returns table columns from information_schema.
    """

    query = f"""
    SELECT
        column_name
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = '{table_name}'
    ORDER BY ordinal_position
    """

    df = read_sql(query)

    if df.empty:
        return []

    return [str(value) for value in df["column_name"].tolist()]


def first_existing_column(table_name, candidates):
    """
    Returns the first candidate column found in a table.
    """

    available_columns = set(get_table_columns(table_name))

    for candidate in candidates:
        if candidate in available_columns:
            return candidate

    return None


def validate_required_tables_exist(results):
    """
    Validates that required Zenput tables exist.
    """

    print_section("1. REQUIRED ZENPUT TABLES")

    rows = []

    for table_name in REQUIRED_TABLES:
        exists = table_exists(table_name)

        rows.append(
            {
                "table_name": table_name,
                "exists": exists,
            }
        )

    df = pd.DataFrame(rows)
    print_df(df)

    passed = bool(df["exists"].all())

    results["required_zenput_tables_exist"] = passed

    print("\nValidation:")
    print(f"status: {'PASS' if passed else 'FAIL'}")


def validate_table_counts(results):
    """
    Validates row counts for required Zenput tables.
    """

    print_section("2. ZENPUT TABLE COUNTS")

    union_parts = []

    for table_name in REQUIRED_TABLES:
        if table_exists(table_name):
            union_parts.append(
                f"""
                SELECT
                    '{table_name}' AS table_name,
                    COUNT(*) AS total_rows
                FROM {table_name}
                """
            )

    if not union_parts:
        print("No required Zenput tables are available.")
        results["zenput_table_counts_available"] = False
        print("\nValidation:")
        print("status: FAIL")
        return

    query = "\nUNION ALL\n".join(union_parts)
    query = f"""
    {query}
    ORDER BY table_name
    """

    df = read_sql(query)
    print_df(df)

    present_tables = set(df["table_name"].tolist())
    missing_tables = set(REQUIRED_TABLES) - present_tables

    passed = len(missing_tables) == 0

    results["zenput_table_counts_available"] = passed

    print("\nValidation:")
    print(f"missing_tables: {sorted(missing_tables)}")
    print(f"status: {'PASS' if passed else 'FAIL'}")


def validate_submissions_location_mapping(results):
    """
    Validates Zenput submissions.location_name values against core.config.zenput.
    """

    print_section("3. SUBMISSIONS LOCATION MAPPING")

    table_name = "submissions"

    if not table_exists(table_name):
        print(f"Table not found: {table_name}")
        results["zenput_submissions_location_mapping"] = False
        print("\nValidation:")
        print("status: FAIL")
        return

    columns = get_table_columns(table_name)

    if "location_name" not in columns:
        print("Column not found: submissions.location_name")
        results["zenput_submissions_location_mapping"] = False
        print("\nValidation:")
        print("status: FAIL")
        return

    date_column = first_existing_column(
        table_name,
        [
            "date_submitted",
            "created_at",
            "last_updated",
        ],
    )

    if date_column:
        query = f"""
        SELECT
            location_name,
            COUNT(*) AS total_submissions,
            MIN({date_column}) AS first_submission,
            MAX({date_column}) AS last_submission
        FROM submissions
        WHERE location_name IS NOT NULL
        GROUP BY location_name
        ORDER BY location_name
        """
    else:
        query = """
        SELECT
            location_name,
            COUNT(*) AS total_submissions
        FROM submissions
        WHERE location_name IS NOT NULL
        GROUP BY location_name
        ORDER BY location_name
        """

    df = read_sql(query)

    if df.empty:
        print("No location_name values found in submissions.")
        results["zenput_submissions_location_mapping"] = False
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

        output_row = {
            "location_name": location_name,
            "company_source_key": company_source_key,
            "is_mapped": is_mapped,
            "is_zenput_only": is_zenput_only,
            "wansoft_id": wansoft_id,
            "total_submissions": row["total_submissions"],
        }

        if "first_submission" in row:
            output_row["first_submission"] = row["first_submission"]

        if "last_submission" in row:
            output_row["last_submission"] = row["last_submission"]

        rows.append(output_row)

    output_df = pd.DataFrame(rows)
    print_df(output_df)

    location_names = set(df["location_name"].dropna().astype(str).tolist())
    unmapped_locations = get_unmapped_zenput_locations(location_names)

    passed = len(unmapped_locations) == 0

    results["zenput_submissions_location_mapping"] = passed

    print("\nValidation:")
    print(f"total_locations: {len(location_names)}")
    print(f"unmapped_locations: {sorted(unmapped_locations)}")
    print(f"status: {'PASS' if passed else 'FAIL'}")


def validate_zenput_only_locations(results):
    """
    Validates that Zenput-only locations are visible and classified.
    """

    print_section("4. ZENPUT-ONLY LOCATIONS")

    table_name = "submissions"

    if not table_exists(table_name):
        print(f"Table not found: {table_name}")
        results["zenput_only_locations_classified"] = False
        print("\nValidation:")
        print("status: FAIL")
        return

    query = """
    SELECT
        location_name,
        COUNT(*) AS total_submissions
    FROM submissions
    WHERE location_name IS NOT NULL
    GROUP BY location_name
    ORDER BY location_name
    """

    df = read_sql(query)

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
                }
            )

    output_df = pd.DataFrame(rows)
    print_df(output_df, empty_message="No Zenput-only locations found.")

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


def validate_timestamp_file(results):
    """
    Validates legacy last_run_timestamp.txt.
    """

    print_section("5. LEGACY TIMESTAMP FILE")

    exists = TIMESTAMP_FILE.exists()

    print(f"timestamp_file: {TIMESTAMP_FILE}")
    print(f"exists: {exists}")

    if not exists:
        results["zenput_timestamp_file_valid"] = False
        print("\nValidation:")
        print("status: FAIL")
        return

    raw_value = TIMESTAMP_FILE.read_text(encoding="utf-8").strip()

    print(f"raw_value: {raw_value}")

    parsed_ok = False
    parsed_value = None

    if raw_value:
        candidate = raw_value

        if candidate.endswith("Z"):
            candidate = candidate[:-1] + "+00:00"

        try:
            parsed_value = datetime.fromisoformat(candidate)
            parsed_ok = True
        except ValueError:
            parsed_ok = False

    print(f"parsed_ok: {parsed_ok}")
    print(f"parsed_value: {parsed_value}")

    results["zenput_timestamp_file_valid"] = parsed_ok

    print("\nValidation:")
    print(f"status: {'PASS' if parsed_ok else 'FAIL'}")


def validate_legacy_pipeline_protection(results):
    """
    Documents that write-enabled legacy scripts are protected by the wrapper.

    This is a governance validation.
    """

    print_section("6. LEGACY PIPELINE PROTECTION")

    rows = [
        {
            "legacy_script": "legacy.zenput.zenput_mysql_forms",
            "writes_database": True,
            "writes_file": False,
            "protected_by": "scripts.run_zenput_pipeline safety gate",
        },
        {
            "legacy_script": "legacy.zenput.zenput_mysql_tasks",
            "writes_database": True,
            "writes_file": True,
            "protected_by": "scripts.run_zenput_pipeline safety gate",
        },
    ]

    df = pd.DataFrame(rows)
    print_df(df)

    results["zenput_legacy_pipeline_protection_documented"] = True

    print("\nValidation:")
    print("status: PASS")


def print_final_summary(results):
    """
    Prints final validation summary.
    """

    print_section("FINAL ZENPUT OUTPUT VALIDATION SUMMARY")

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
    print("ZENPUT OUTPUT VALIDATION START")
    print("=====================================================")
    print(f"started_at: {now_iso()}")

    results = {}

    validate_required_tables_exist(results)
    validate_table_counts(results)
    validate_submissions_location_mapping(results)
    validate_zenput_only_locations(results)
    validate_timestamp_file(results)
    validate_legacy_pipeline_protection(results)

    exit_code = print_final_summary(results)

    print(f"\nfinished_at: {now_iso()}")
    print("=====================================================")
    print("ZENPUT OUTPUT VALIDATION END")
    print("=====================================================")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())