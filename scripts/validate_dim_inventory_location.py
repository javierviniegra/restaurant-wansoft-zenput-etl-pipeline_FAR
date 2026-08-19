"""
Validate dim_inventory_location.

Run:
    python -m scripts.validate_dim_inventory_location
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.database.mysql import get_db_connection


SOURCE_TABLE = "analytics_inventory_snapshot"
DIM_TABLE = "dim_inventory_location"
MAPPING_TABLE = "inventory_location_company_mapping_config"
SOURCE_SYSTEM = "odoo"


def fetch_all_dict(conn: Any, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params or ())
    rows = cursor.fetchall()
    cursor.close()
    return rows


def fetch_one_dict(conn: Any, query: str, params: Optional[tuple] = None) -> Dict[str, Any]:
    rows = fetch_all_dict(conn, query, params)
    return rows[0] if rows else {}


def object_exists(conn: Any, object_name: str) -> bool:
    query = """
        SELECT COUNT(1) AS total
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = %s
    """
    row = fetch_one_dict(conn, query, (object_name,))
    return bool(row and int(row["total"]) > 0)


def validation_result(name: str, status: str, details: Any = None) -> Dict[str, Any]:
    return {
        "validation": name,
        "status": status,
        "details": details,
    }


def validate_object_exists(conn: Any, object_name: str) -> Dict[str, Any]:
    exists = object_exists(conn, object_name)
    return validation_result(
        f"{object_name}_exists",
        "PASS" if exists else "FAIL",
        {"object_name": object_name, "exists": exists},
    )


def validate_source_location_count_reconciles(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            (SELECT COUNT(DISTINCT CAST(source_location_id AS CHAR))
             FROM {SOURCE_TABLE}
             WHERE source_location_id IS NOT NULL) AS source_location_count,
            (SELECT COUNT(1)
             FROM {DIM_TABLE}) AS dim_location_count
    """
    row = fetch_one_dict(conn, query)
    source_count = int(row["source_location_count"])
    dim_count = int(row["dim_location_count"])
    return validation_result(
        "source_location_count_reconciles",
        "PASS" if source_count == dim_count else "FAIL",
        {"source_location_count": source_count, "dim_location_count": dim_count},
    )


def validate_unique_grain(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            source_system,
            source_location_id,
            COUNT(1) AS total_rows
        FROM {DIM_TABLE}
        GROUP BY
            source_system,
            source_location_id
        HAVING COUNT(1) > 1
    """
    rows = fetch_all_dict(conn, query)
    return validation_result(
        "dim_inventory_location_grain_unique",
        "PASS" if not rows else "FAIL",
        rows[:20],
    )


def validate_no_null_source_location_id(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS bad_rows
        FROM {DIM_TABLE}
        WHERE source_location_id IS NULL
           OR TRIM(source_location_id) = ''
    """
    row = fetch_one_dict(conn, query)
    total = int(row["bad_rows"])
    return validation_result(
        "no_null_source_location_id",
        "PASS" if total == 0 else "FAIL",
        {"bad_rows": total},
    )


def validate_no_null_location_usage_type(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS bad_rows
        FROM {DIM_TABLE}
        WHERE location_usage_type IS NULL
           OR TRIM(location_usage_type) = ''
    """
    row = fetch_one_dict(conn, query)
    total = int(row["bad_rows"])
    return validation_result(
        "no_null_location_usage_type",
        "PASS" if total == 0 else "FAIL",
        {"bad_rows": total},
    )


def validate_all_source_locations_present(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS missing_rows
        FROM (
            SELECT DISTINCT CAST(source_location_id AS CHAR) AS source_location_id
            FROM {SOURCE_TABLE}
            WHERE source_location_id IS NOT NULL
        ) s
        LEFT JOIN {DIM_TABLE} d
            ON d.source_system = %s
           AND d.source_location_id = s.source_location_id
        WHERE d.source_location_id IS NULL
    """
    row = fetch_one_dict(conn, query, (SOURCE_SYSTEM,))
    total = int(row["missing_rows"])
    return validation_result(
        "all_source_locations_present",
        "PASS" if total == 0 else "FAIL",
        {"missing_rows": total},
    )


def validate_no_company_key_without_approved_mapping(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS bad_rows
        FROM {DIM_TABLE}
        WHERE company_source_key IS NOT NULL
          AND company_mapping_status NOT IN ('approved', 'approved_from_source')
    """
    row = fetch_one_dict(conn, query)
    total = int(row["bad_rows"])
    return validation_result(
        "no_company_key_without_approved_mapping",
        "PASS" if total == 0 else "FAIL",
        {"bad_rows": total},
    )


def validate_company_view_requires_approved_mapping(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS bad_rows
        FROM {DIM_TABLE}
        WHERE include_in_company_inventory_views = TRUE
          AND (
                company_source_key IS NULL
             OR company_mapping_status <> 'approved'
             OR location_usage_type <> 'internal_or_unknown'
          )
    """
    row = fetch_one_dict(conn, query)
    total = int(row["bad_rows"])
    return validation_result(
        "company_view_requires_approved_mapping",
        "PASS" if total == 0 else "FAIL",
        {"bad_rows": total},
    )


def validate_partner_virtual_excluded_from_company_views(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS bad_rows
        FROM {DIM_TABLE}
        WHERE location_usage_type IN ('partner', 'virtual')
          AND include_in_company_inventory_views = TRUE
    """
    row = fetch_one_dict(conn, query)
    total = int(row["bad_rows"])
    return validation_result(
        "partner_virtual_excluded_from_company_views",
        "PASS" if total == 0 else "FAIL",
        {"bad_rows": total},
    )


def validate_physical_eligibility_logic(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS bad_rows
        FROM {DIM_TABLE}
        WHERE (location_usage_type = 'internal_or_unknown' AND include_in_inventory_physical_views <> TRUE)
           OR (location_usage_type <> 'internal_or_unknown' AND include_in_inventory_physical_views = TRUE)
    """
    row = fetch_one_dict(conn, query)
    total = int(row["bad_rows"])
    return validation_result(
        "physical_eligibility_logic_valid",
        "PASS" if total == 0 else "FAIL",
        {"bad_rows": total},
    )


def validate_mapping_config_grain(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            source_system,
            source_location_id,
            company_source_key,
            is_active,
            COUNT(1) AS total_rows
        FROM {MAPPING_TABLE}
        GROUP BY
            source_system,
            source_location_id,
            company_source_key,
            is_active
        HAVING COUNT(1) > 1
    """
    rows = fetch_all_dict(conn, query)
    return validation_result(
        "mapping_config_grain_unique",
        "PASS" if not rows else "FAIL",
        rows[:20],
    )


def validate_physical_eligibility_distribution(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            location_usage_type,
            include_in_inventory_physical_views,
            include_in_company_inventory_views,
            COUNT(1) AS total_locations
        FROM {DIM_TABLE}
        GROUP BY
            location_usage_type,
            include_in_inventory_physical_views,
            include_in_company_inventory_views
        ORDER BY
            location_usage_type,
            include_in_inventory_physical_views,
            include_in_company_inventory_views
    """
    rows = fetch_all_dict(conn, query)
    return validation_result(
        "physical_eligibility_distribution_available",
        "PASS" if rows else "FAIL",
        rows,
    )


def validate_company_mapping_status_distribution(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            company_mapping_status,
            COUNT(1) AS total_locations
        FROM {DIM_TABLE}
        GROUP BY company_mapping_status
        ORDER BY company_mapping_status
    """
    rows = fetch_all_dict(conn, query)
    return validation_result(
        "company_mapping_status_distribution_available",
        "PASS" if rows else "FAIL",
        rows,
    )


def validate_location_review_status_distribution(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            location_review_status,
            COUNT(1) AS total_locations
        FROM {DIM_TABLE}
        GROUP BY location_review_status
        ORDER BY location_review_status
    """
    rows = fetch_all_dict(conn, query)
    return validation_result(
        "location_review_status_distribution_available",
        "PASS" if rows else "FAIL",
        rows,
    )


def validate_current_usage_reconciles(conn: Any) -> Dict[str, Any]:
    if not object_exists(conn, "analytics_inventory_current_product_location"):
        return validation_result(
            "current_usage_reconciles",
            "PASS",
            {"note": "analytics_inventory_current_product_location does not exist; skipped."},
        )

    query = f"""
        SELECT
            (SELECT COALESCE(SUM(source_row_count), 0)
             FROM analytics_inventory_current_product_location) AS source_current_rows,
            (SELECT COALESCE(SUM(current_source_row_count), 0)
             FROM {DIM_TABLE}) AS dim_current_rows,
            (SELECT COALESCE(SUM(current_stock_qty), 0)
             FROM analytics_inventory_current_product_location) AS source_current_stock_qty,
            (SELECT COALESCE(SUM(current_stock_qty), 0)
             FROM {DIM_TABLE}) AS dim_current_stock_qty
    """
    row = fetch_one_dict(conn, query)
    source_rows = int(row["source_current_rows"])
    dim_rows = int(row["dim_current_rows"])
    source_qty = str(row["source_current_stock_qty"])
    dim_qty = str(row["dim_current_stock_qty"])
    qty_ok = float(source_qty) == float(dim_qty)

    return validation_result(
        "current_usage_reconciles",
        "PASS" if source_rows == dim_rows and qty_ok else "FAIL",
        {
            "source_current_rows": source_rows,
            "dim_current_rows": dim_rows,
            "source_current_stock_qty": source_qty,
            "dim_current_stock_qty": dim_qty,
        },
    )


def print_result(result: Dict[str, Any]) -> None:
    print(f"{result['validation']}: {result['status']}")
    details = result.get("details")
    if details not in (None, [], {}):
        print(details)


def main() -> int:
    print("=====================================================")
    print("DIM INVENTORY LOCATION VALIDATION START")
    print("=====================================================")

    conn = get_db_connection()
    results: List[Dict[str, Any]] = []

    try:
        dim_exists = validate_object_exists(conn, DIM_TABLE)
        mapping_exists = validate_object_exists(conn, MAPPING_TABLE)
        source_exists = validate_object_exists(conn, SOURCE_TABLE)
        results.extend([source_exists, dim_exists, mapping_exists])

        if all(result["status"] == "PASS" for result in [source_exists, dim_exists, mapping_exists]):
            results.extend([
                validate_source_location_count_reconciles(conn),
                validate_unique_grain(conn),
                validate_no_null_source_location_id(conn),
                validate_no_null_location_usage_type(conn),
                validate_all_source_locations_present(conn),
                validate_no_company_key_without_approved_mapping(conn),
                validate_company_view_requires_approved_mapping(conn),
                validate_partner_virtual_excluded_from_company_views(conn),
                validate_physical_eligibility_logic(conn),
                validate_mapping_config_grain(conn),
                validate_current_usage_reconciles(conn),
                validate_physical_eligibility_distribution(conn),
                validate_company_mapping_status_distribution(conn),
                validate_location_review_status_distribution(conn),
            ])

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
