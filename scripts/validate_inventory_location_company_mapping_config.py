"""
Validate inventory_location_company_mapping_config.

Validation goals:
- required tables exist
- mapping config grain is unique for active approved mappings
- active approved mappings point to existing dim_inventory_location rows
- active approved mappings point to existing dim_company_analytical rows
- active approved mappings are allowed only for internal_or_unknown locations
- dim_inventory_location company view eligibility reconciles after rebuild
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.database.mysql import get_db_connection


CONFIG_TABLE = "inventory_location_company_mapping_config"
DIM_LOCATION_TABLE = "dim_inventory_location"
DIM_COMPANY_TABLE = "dim_company_analytical"


def fetch_one_dict(conn: Any, query: str, params: Optional[tuple] = None) -> Dict[str, Any]:
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params or ())
    row = cursor.fetchone() or {}
    cursor.close()
    return row


def fetch_all_dict(conn: Any, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params or ())
    rows = cursor.fetchall()
    cursor.close()
    return rows


def table_exists(conn: Any, table_name: str) -> bool:
    query = """
        SELECT COUNT(1) AS total
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = %s
    """
    row = fetch_one_dict(conn, query, (table_name,))
    return bool(row.get("total", 0) > 0)


def validation_result(name: str, status: str, details: Any = None) -> Dict[str, Any]:
    return {
        "validation": name,
        "status": status,
        "details": details,
    }


def validate_table_exists(conn: Any, table_name: str, validation_name: str) -> Dict[str, Any]:
    exists = table_exists(conn, table_name)
    return validation_result(
        validation_name,
        "PASS" if exists else "FAIL",
        {
            "table_name": table_name,
            "exists": exists,
        },
    )


def validate_active_approved_grain_unique(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            source_system,
            source_location_id,
            COUNT(1) AS total_rows
        FROM {CONFIG_TABLE}
        WHERE is_active = TRUE
          AND mapping_status = 'approved'
        GROUP BY
            source_system,
            source_location_id
        HAVING COUNT(1) > 1
    """
    rows = fetch_all_dict(conn, query)

    return validation_result(
        "active_approved_mapping_grain_unique",
        "PASS" if not rows else "FAIL",
        rows[:50],
    )


def validate_active_approved_locations_exist(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            c.source_system,
            c.source_location_id,
            c.company_source_key
        FROM {CONFIG_TABLE} c
        LEFT JOIN {DIM_LOCATION_TABLE} d
            ON c.source_system = d.source_system
           AND c.source_location_id = d.source_location_id
        WHERE c.is_active = TRUE
          AND c.mapping_status = 'approved'
          AND d.source_location_id IS NULL
    """
    rows = fetch_all_dict(conn, query)

    return validation_result(
        "active_approved_locations_exist",
        "PASS" if not rows else "FAIL",
        rows[:50],
    )


def validate_active_approved_companies_exist(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            c.source_system,
            c.source_location_id,
            c.company_source_key
        FROM {CONFIG_TABLE} c
        LEFT JOIN {DIM_COMPANY_TABLE} d
            ON c.company_source_key = d.company_source_key
        WHERE c.is_active = TRUE
          AND c.mapping_status = 'approved'
          AND (
                c.company_source_key IS NULL
             OR c.company_source_key = ''
             OR d.company_source_key IS NULL
          )
    """
    rows = fetch_all_dict(conn, query)

    return validation_result(
        "active_approved_companies_exist",
        "PASS" if not rows else "FAIL",
        rows[:50],
    )


def validate_active_approved_are_internal(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            c.source_system,
            c.source_location_id,
            c.company_source_key,
            d.location_usage_type
        FROM {CONFIG_TABLE} c
        INNER JOIN {DIM_LOCATION_TABLE} d
            ON c.source_system = d.source_system
           AND c.source_location_id = d.source_location_id
        WHERE c.is_active = TRUE
          AND c.mapping_status = 'approved'
          AND d.location_usage_type <> 'internal_or_unknown'
    """
    rows = fetch_all_dict(conn, query)

    return validation_result(
        "active_approved_mappings_only_internal_or_unknown",
        "PASS" if not rows else "FAIL",
        rows[:50],
    )


def validate_no_partner_virtual_company_views(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            source_system,
            source_location_id,
            location_usage_type,
            include_in_company_inventory_views
        FROM {DIM_LOCATION_TABLE}
        WHERE location_usage_type IN ('partner', 'virtual')
          AND include_in_company_inventory_views = TRUE
    """
    rows = fetch_all_dict(conn, query)

    return validation_result(
        "partner_virtual_excluded_from_company_inventory_views",
        "PASS" if not rows else "FAIL",
        rows[:50],
    )


def validate_company_view_reconciles(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            (
                SELECT COUNT(1)
                FROM {CONFIG_TABLE} c
                INNER JOIN {DIM_LOCATION_TABLE} d
                    ON c.source_system = d.source_system
                   AND c.source_location_id = d.source_location_id
                WHERE c.is_active = TRUE
                  AND c.mapping_status = 'approved'
                  AND d.location_usage_type = 'internal_or_unknown'
            ) AS approved_internal_mappings,
            (
                SELECT COUNT(1)
                FROM {DIM_LOCATION_TABLE}
                WHERE include_in_company_inventory_views = TRUE
            ) AS company_view_locations
    """
    row = fetch_one_dict(conn, query)
    approved_internal_mappings = int(row.get("approved_internal_mappings", 0))
    company_view_locations = int(row.get("company_view_locations", 0))

    return validation_result(
        "company_view_eligibility_reconciles_after_rebuild",
        "PASS" if approved_internal_mappings == company_view_locations else "FAIL",
        {
            "approved_internal_mappings": approved_internal_mappings,
            "company_view_locations": company_view_locations,
        },
    )


def validate_mapping_status_distribution(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            mapping_status,
            is_active,
            COUNT(1) AS total_rows
        FROM {CONFIG_TABLE}
        GROUP BY
            mapping_status,
            is_active
        ORDER BY
            mapping_status,
            is_active
    """
    rows = fetch_all_dict(conn, query)

    return validation_result(
        "mapping_config_distribution_available",
        "PASS",
        rows,
    )


def print_result(result: Dict[str, Any]) -> None:
    print(f"{result['validation']}: {result['status']}")

    details = result.get("details")

    if details not in (None, [], {}):
        print(details)


def main() -> int:
    print("=====================================================")
    print("INVENTORY LOCATION COMPANY MAPPING VALIDATION START")
    print("=====================================================")

    conn = get_db_connection()
    results: List[Dict[str, Any]] = []

    try:
        results.append(validate_table_exists(conn, CONFIG_TABLE, "inventory_location_company_mapping_config_exists"))
        results.append(validate_table_exists(conn, DIM_LOCATION_TABLE, "dim_inventory_location_exists"))
        results.append(validate_table_exists(conn, DIM_COMPANY_TABLE, "dim_company_analytical_exists"))

        if all(result["status"] == "PASS" for result in results):
            results.extend(
                [
                    validate_active_approved_grain_unique(conn),
                    validate_active_approved_locations_exist(conn),
                    validate_active_approved_companies_exist(conn),
                    validate_active_approved_are_internal(conn),
                    validate_no_partner_virtual_company_views(conn),
                    validate_company_view_reconciles(conn),
                    validate_mapping_status_distribution(conn),
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
