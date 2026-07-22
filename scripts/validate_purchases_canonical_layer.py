"""
Purchases Canonical Layer Validator.

Purpose:
    Validate the canonical purchase layer after running the purchases pipeline.

This script is read-only.

It validates:
    - source_system coexistence
    - Antenas Odoo/Wansoft split
    - Wansoft final-source companies
    - internal providers as vendors
    - internal providers not as final companies
    - canonical table row counts
    - purchase mapping status distribution

Execution:
    python -m scripts.validate_purchases_canonical_layer
"""

from __future__ import annotations

import sys
from datetime import datetime
from typing import Dict, List

import pandas as pd

from core.database.mysql import get_mysql_connection as get_db_connection


INTERNAL_PROVIDERS = [
    "EL BODEGON DE FITO",
    "LAS EMPANADAS DE MARIA EVA",
]

ROLLOUT_COMPANY_EXPECTATIONS = [
    {
        "company_source_key": "Antenas",
        "rollout_type": "migrated_from_wansoft",
        "active": True,
        "description": "Reference branch for migrated Fonda pattern.",
    },
    {
        "company_source_key": "La Esquina Coyoacán",
        "rollout_type": "migrated_from_wansoft",
        "active": True,
        "description": "Migrated Fonda branch. Should behave like Antenas.",
    },
    {
        "company_source_key": "CentroMyJ",
        "rollout_type": "new_odoo_branch",
        "active": True,
        "description": "New Odoo branch. Should be Odoo final without Wansoft final history.",
    },
    {
        "company_source_key": "Puebla",
        "rollout_type": "new_odoo_branch",
        "active": False,
        "description": "Future Odoo rollout branch. Documented but not enforced yet.",
    },
]


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def read_sql(query: str) -> pd.DataFrame:
    """
    Executes a read-only SQL query against MySQL.
    """
    conn = get_db_connection(target="wansoft")

    try:
        df = pd.read_sql(query, conn)
    finally:
        conn.close()

    return df


def print_section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def print_df(df: pd.DataFrame, empty_message: str = "No rows returned.") -> None:
    if df is None or df.empty:
        print(empty_message)
        return

    print(df.to_string(index=False))


def validate_source_system_coexistence(results: Dict[str, bool]) -> None:
    print_section("1. SOURCE SYSTEM COEXISTENCE")

    query = """
    SELECT
        'orders' AS canonical_table,
        source_system,
        company_source_key,
        final_purchase_source_status,
        COUNT(*) AS total_rows
    FROM canonical_purchase_order_snapshot
    GROUP BY
        source_system,
        company_source_key,
        final_purchase_source_status

    UNION ALL

    SELECT
        'lines' AS canonical_table,
        source_system,
        company_source_key,
        final_purchase_source_status,
        COUNT(*) AS total_rows
    FROM canonical_purchase_order_line_snapshot
    GROUP BY
        source_system,
        company_source_key,
        final_purchase_source_status

    UNION ALL

    SELECT
        'receipts' AS canonical_table,
        source_system,
        company_source_key,
        final_purchase_source_status,
        COUNT(*) AS total_rows
    FROM canonical_purchase_receipt_snapshot
    GROUP BY
        source_system,
        company_source_key,
        final_purchase_source_status

    UNION ALL

    SELECT
        'receipt_moves' AS canonical_table,
        source_system,
        company_source_key,
        final_purchase_source_status,
        COUNT(*) AS total_rows
    FROM canonical_purchase_receipt_move_snapshot
    GROUP BY
        source_system,
        company_source_key,
        final_purchase_source_status
    ORDER BY
        canonical_table,
        source_system,
        company_source_key
    """

    df = read_sql(query)
    print_df(df)

    source_systems = set(df["source_system"].dropna().unique()) if not df.empty else set()

    passed = {"odoo", "wansoft"}.issubset(source_systems)

    results["source_system_coexistence"] = passed

    print("\nValidation:")
    print(f"source_systems_found: {sorted(source_systems)}")
    print(f"status: {'PASS' if passed else 'FAIL'}")


def validate_antenas_split(results: Dict[str, bool]) -> None:
    print_section("2. ANTENAS SOURCE SPLIT")

    query = """
    SELECT
        source_system,
        company_source_key,
        final_purchase_source_status,
        MIN(order_date) AS min_order_date,
        MAX(order_date) AS max_order_date,
        COUNT(*) AS total_lines,
        SUM(COALESCE(price_total, 0)) AS total_amount
    FROM canonical_purchase_order_line_snapshot
    WHERE company_source_key = 'Antenas'
    GROUP BY
        source_system,
        company_source_key,
        final_purchase_source_status
    ORDER BY
        source_system,
        final_purchase_source_status
    """

    df = read_sql(query)
    print_df(df)

    if df.empty:
        passed = False
    else:
        statuses = set(df["final_purchase_source_status"].dropna().unique())
        systems = set(df["source_system"].dropna().unique())

        passed = (
            "odoo" in systems
            and "wansoft" in systems
            and "final_odoo_enabled" in statuses
            and "wansoft_history_before_odoo" in statuses
        )

    results["antenas_source_split"] = passed

    print("\nValidation:")
    print(f"status: {'PASS' if passed else 'FAIL'}")


def validate_wansoft_final_source_companies(results: Dict[str, bool]) -> None:
    print_section("3. WANSOFT FINAL-SOURCE COMPANIES")

    query = """
    SELECT
        source_system,
        company_source_key,
        final_purchase_source_status,
        COUNT(*) AS total_lines,
        SUM(COALESCE(price_total, 0)) AS total_amount
    FROM canonical_purchase_order_line_snapshot
    WHERE source_system = 'wansoft'
    GROUP BY
        source_system,
        company_source_key,
        final_purchase_source_status
    ORDER BY
        total_lines DESC
    """

    df = read_sql(query)
    print_df(df)

    if df.empty:
        passed = False
    else:
        valid_statuses = {
            "final_wansoft_enabled",
            "wansoft_history_before_odoo",
        }

        statuses = set(df["final_purchase_source_status"].dropna().unique())
        passed = statuses.issubset(valid_statuses)

    results["wansoft_final_source_companies"] = passed

    print("\nValidation:")
    print(f"status: {'PASS' if passed else 'FAIL'}")


def validate_internal_providers_as_vendors(results: Dict[str, bool]) -> None:
    print_section("4. INTERNAL PROVIDERS AS VENDORS")

    provider_list = "', '".join(INTERNAL_PROVIDERS)

    query = f"""
    SELECT
        source_system,
        vendor_name,
        company_name,
        company_source_key,
        COUNT(*) AS total_lines,
        SUM(COALESCE(price_total, 0)) AS total_amount
    FROM canonical_purchase_order_line_snapshot
    WHERE vendor_name IN ('{provider_list}')
    GROUP BY
        source_system,
        vendor_name,
        company_name,
        company_source_key
    ORDER BY
        total_lines DESC
    """

    df = read_sql(query)
    print_df(df, empty_message="No internal providers found as vendors.")

    # This validation is informational. Rows are allowed.
    passed = True
    results["internal_providers_as_vendors"] = passed

    print("\nValidation:")
    print("status: PASS")
    print("note: internal providers are allowed as vendor_name.")


def validate_internal_providers_not_as_companies(results: Dict[str, bool]) -> None:
    print_section("5. INTERNAL PROVIDERS NOT AS FINAL COMPANIES")

    provider_list = "', '".join(INTERNAL_PROVIDERS)

    query = f"""
    SELECT
        source_system,
        company_name,
        COUNT(*) AS total_lines
    FROM canonical_purchase_order_line_snapshot
    WHERE company_name IN ('{provider_list}')
    GROUP BY
        source_system,
        company_name
    """

    df = read_sql(query)
    print_df(df, empty_message="No internal providers found as final companies.")

    passed = df.empty
    results["internal_providers_not_as_companies"] = passed

    print("\nValidation:")
    print(f"status: {'PASS' if passed else 'FAIL'}")


def validate_mapping_distribution(results: Dict[str, bool]) -> None:
    print_section("6. CANONICAL PRODUCT MAPPING DISTRIBUTION")

    query = """
    SELECT
        source_system,
        product_mapping_status,
        product_mapping_source,
        purchase_mapping_bucket,
        COUNT(*) AS total_lines,
        COUNT(DISTINCT product_id) AS unique_product_ids,
        COUNT(DISTINCT wansoft_code) AS unique_wansoft_codes,
        SUM(COALESCE(price_total, 0)) AS total_amount
    FROM canonical_purchase_order_line_snapshot
    GROUP BY
        source_system,
        product_mapping_status,
        product_mapping_source,
        purchase_mapping_bucket
    ORDER BY
        source_system,
        total_lines DESC
    """

    df = read_sql(query)
    print_df(df)

    # Informational for now.
    passed = not df.empty
    results["mapping_distribution_available"] = passed

    print("\nValidation:")
    print(f"status: {'PASS' if passed else 'FAIL'}")


def validate_table_counts(results: Dict[str, bool]) -> None:
    print_section("7. CANONICAL TABLE COUNTS")

    query = """
    SELECT
        'canonical_purchase_order_snapshot' AS table_name,
        source_system,
        COUNT(*) AS total_rows
    FROM canonical_purchase_order_snapshot
    GROUP BY source_system

    UNION ALL

    SELECT
        'canonical_purchase_order_line_snapshot' AS table_name,
        source_system,
        COUNT(*) AS total_rows
    FROM canonical_purchase_order_line_snapshot
    GROUP BY source_system

    UNION ALL

    SELECT
        'canonical_purchase_receipt_snapshot' AS table_name,
        source_system,
        COUNT(*) AS total_rows
    FROM canonical_purchase_receipt_snapshot
    GROUP BY source_system

    UNION ALL

    SELECT
        'canonical_purchase_receipt_move_snapshot' AS table_name,
        source_system,
        COUNT(*) AS total_rows
    FROM canonical_purchase_receipt_move_snapshot
    GROUP BY source_system
    ORDER BY
        table_name,
        source_system
    """

    df = read_sql(query)
    print_df(df)

    passed = not df.empty
    results["table_counts_available"] = passed

    print("\nValidation:")
    print(f"status: {'PASS' if passed else 'FAIL'}")


def validate_rollout_company_patterns(results: Dict[str, bool]) -> None:
    print_section("8. ROLLOUT COMPANY PATTERN VALIDATION")

    company_keys = "', '".join(
        item["company_source_key"] for item in ROLLOUT_COMPANY_EXPECTATIONS
    )

    query = f"""
    SELECT
        source_system,
        company_source_key,
        final_purchase_source_status,
        COUNT(*) AS total_lines,
        MIN(order_date) AS min_order_date,
        MAX(order_date) AS max_order_date
    FROM canonical_purchase_order_line_snapshot
    WHERE company_source_key IN ('{company_keys}')
    GROUP BY
        source_system,
        company_source_key,
        final_purchase_source_status
    ORDER BY
        company_source_key,
        source_system,
        final_purchase_source_status
    """

    df = read_sql(query)
    print_df(df)

    failed = []

    for expectation in ROLLOUT_COMPANY_EXPECTATIONS:
        company_key = expectation["company_source_key"]
        rollout_type = expectation["rollout_type"]
        active = expectation.get("active", True)

        if not active:
            print(
                f"\nSkipping inactive rollout expectation: {company_key} "
                f"({rollout_type})"
            )
            continue

        company_df = df[df["company_source_key"] == company_key]

        statuses = set(company_df["final_purchase_source_status"].dropna().unique())
        systems = set(company_df["source_system"].dropna().unique())

        if rollout_type == "migrated_from_wansoft":
            has_odoo_final = (
                "odoo" in systems
                and "final_odoo_enabled" in statuses
            )
            has_wansoft_history = (
                "wansoft" in systems
                and "wansoft_history_before_odoo" in statuses
            )
            has_bad_wansoft_final = (
                "wansoft" in systems
                and "final_wansoft_enabled" in statuses
            )

            passed = (
                has_odoo_final
                and has_wansoft_history
                and not has_bad_wansoft_final
            )

            if not passed:
                failed.append(
                    f"{company_key}: expected migrated_from_wansoft pattern "
                    "with odoo/final_odoo_enabled and "
                    "wansoft/wansoft_history_before_odoo only."
                )

        elif rollout_type == "new_odoo_branch":
            has_odoo_final = (
                "odoo" in systems
                and "final_odoo_enabled" in statuses
            )
            has_bad_wansoft_final = (
                "wansoft" in systems
                and "final_wansoft_enabled" in statuses
            )

            passed = has_odoo_final and not has_bad_wansoft_final

            if not passed:
                failed.append(
                    f"{company_key}: expected new_odoo_branch pattern "
                    "with odoo/final_odoo_enabled and no wansoft/final_wansoft_enabled."
                )

        else:
            failed.append(f"{company_key}: unknown rollout_type {rollout_type}")

    passed = len(failed) == 0
    results["rollout_company_patterns"] = passed

    print("\nValidation:")
    print(f"status: {'PASS' if passed else 'FAIL'}")

    if failed:
        print("\nFailed rollout checks:")
        for item in failed:
            print(f"- {item}")


def print_final_summary(results: Dict[str, bool]) -> int:
    print_section("FINAL VALIDATION SUMMARY")

    failed: List[str] = []

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


def main() -> int:
    print("=====================================================")
    print("PURCHASES CANONICAL LAYER VALIDATION START")
    print("=====================================================")
    print(f"started_at: {now_iso()}")

    results: Dict[str, bool] = {}

    validate_source_system_coexistence(results)
    validate_antenas_split(results)
    validate_wansoft_final_source_companies(results)
    validate_internal_providers_as_vendors(results)
    validate_internal_providers_not_as_companies(results)
    validate_mapping_distribution(results)
    validate_table_counts(results)
    validate_rollout_company_patterns(results)

    exit_code = print_final_summary(results)

    print(f"\nfinished_at: {now_iso()}")
    print("=====================================================")
    print("PURCHASES CANONICAL LAYER VALIDATION END")
    print("=====================================================")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())