"""
Validate stg_odoo_inventory_location_master.

Run:
    python -m scripts.validate_odoo_inventory_location_master
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.database.mysql import get_db_connection


STAGING_TABLE = "stg_odoo_inventory_location_master"
DIM_TABLE = "dim_inventory_location"
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


def table_exists(conn: Any, table_name: str) -> bool:
    query = """
        SELECT COUNT(1) AS total
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = %s
    """
    row = fetch_one_dict(conn, query, (table_name,))
    return bool(row and int(row["total"]) > 0)


def validation_result(name: str, status: str, details: Any = None) -> Dict[str, Any]:
    return {"validation": name, "status": status, "details": details}


def validate_table_exists(conn: Any, table_name: str, name: str) -> Dict[str, Any]:
    exists = table_exists(conn, table_name)
    return validation_result(name, "PASS" if exists else "FAIL", {"table_name": table_name, "exists": exists})


def validate_has_rows(conn: Any) -> Dict[str, Any]:
    row = fetch_one_dict(conn, f"SELECT COUNT(1) AS total_rows FROM {STAGING_TABLE}")
    total = int(row.get("total_rows", 0))
    return validation_result("stg_odoo_inventory_location_master_has_rows", "PASS" if total > 0 else "FAIL", {"total_rows": total})


def validate_grain_unique(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT source_system, odoo_location_id, COUNT(1) AS total_rows
        FROM {STAGING_TABLE}
        GROUP BY source_system, odoo_location_id
        HAVING COUNT(1) > 1
    """
    rows = fetch_all_dict(conn, query)
    return validation_result("odoo_location_master_grain_unique", "PASS" if not rows else "FAIL", rows[:50])


def validate_no_null_odoo_location_id(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS bad_rows
        FROM {STAGING_TABLE}
        WHERE odoo_location_id IS NULL OR TRIM(odoo_location_id) = ''
    """
    row = fetch_one_dict(conn, query)
    total = int(row.get("bad_rows", 0))
    return validation_result("no_null_odoo_location_id", "PASS" if total == 0 else "FAIL", {"bad_rows": total})


def validate_no_null_source_location_id(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS bad_rows
        FROM {STAGING_TABLE}
        WHERE source_location_id IS NULL OR TRIM(source_location_id) = ''
    """
    row = fetch_one_dict(conn, query)
    total = int(row.get("bad_rows", 0))
    return validation_result("no_null_source_location_id", "PASS" if total == 0 else "FAIL", {"bad_rows": total})


def validate_dim_locations_match_staging(conn: Any) -> Dict[str, Any]:
    if not table_exists(conn, DIM_TABLE):
        return validation_result(
            "dim_locations_match_odoo_master",
            "PASS",
            {"note": f"{DIM_TABLE} does not exist; skipped."},
        )

    query = f"""
        SELECT
            d.source_system,
            d.source_location_id,
            d.location_name,
            d.location_usage_type
        FROM {DIM_TABLE} d
        LEFT JOIN {STAGING_TABLE} s
            ON s.source_system = d.source_system
           AND s.source_location_id = d.source_location_id
        WHERE d.source_system = %s
          AND s.source_location_id IS NULL
        ORDER BY d.source_location_id
    """
    rows = fetch_all_dict(conn, query, (SOURCE_SYSTEM,))
    return validation_result("dim_locations_match_odoo_master", "PASS" if not rows else "FAIL", rows[:50])


def validate_company_distribution(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            CASE
                WHEN odoo_company_id IS NULL OR odoo_company_id = '' THEN 'blank_company'
                ELSE 'company_available'
            END AS odoo_company_availability,
            COUNT(1) AS total_locations
        FROM {STAGING_TABLE}
        GROUP BY
            CASE
                WHEN odoo_company_id IS NULL OR odoo_company_id = '' THEN 'blank_company'
                ELSE 'company_available'
            END
        ORDER BY odoo_company_availability
    """
    rows = fetch_all_dict(conn, query)
    return validation_result("odoo_company_availability_distribution_available", "PASS" if rows else "FAIL", rows)


def validate_usage_distribution(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            odoo_usage,
            COUNT(1) AS total_locations
        FROM {STAGING_TABLE}
        GROUP BY odoo_usage
        ORDER BY odoo_usage
    """
    rows = fetch_all_dict(conn, query)
    return validation_result("odoo_usage_distribution_available", "PASS" if rows else "FAIL", rows)


def validate_internal_dim_locations_have_staging(conn: Any) -> Dict[str, Any]:
    if not table_exists(conn, DIM_TABLE):
        return validation_result(
            "internal_dim_locations_have_staging_match",
            "PASS",
            {"note": f"{DIM_TABLE} does not exist; skipped."},
        )

    query = f"""
        SELECT
            d.source_system,
            d.source_location_id,
            d.location_name,
            d.location_usage_type
        FROM {DIM_TABLE} d
        LEFT JOIN {STAGING_TABLE} s
            ON s.source_system = d.source_system
           AND s.source_location_id = d.source_location_id
        WHERE d.location_usage_type = 'internal_or_unknown'
          AND s.source_location_id IS NULL
        ORDER BY d.source_location_id
    """
    rows = fetch_all_dict(conn, query)
    return validation_result("internal_dim_locations_have_staging_match", "PASS" if not rows else "FAIL", rows[:50])


def print_result(result: Dict[str, Any]) -> None:
    print(f"{result['validation']}: {result['status']}")
    details = result.get("details")
    if details not in (None, [], {}):
        print(details)


def main() -> int:
    print("=====================================================")
    print("ODOO INVENTORY LOCATION MASTER VALIDATION START")
    print("=====================================================")

    conn = get_db_connection()
    results: List[Dict[str, Any]] = []

    try:
        staging_exists = validate_table_exists(conn, STAGING_TABLE, "stg_odoo_inventory_location_master_exists")
        dim_exists = validate_table_exists(conn, DIM_TABLE, "dim_inventory_location_exists")
        results.extend([staging_exists, dim_exists])

        if staging_exists["status"] == "PASS":
            results.extend(
                [
                    validate_has_rows(conn),
                    validate_grain_unique(conn),
                    validate_no_null_odoo_location_id(conn),
                    validate_no_null_source_location_id(conn),
                    validate_dim_locations_match_staging(conn),
                    validate_internal_dim_locations_have_staging(conn),
                    validate_company_distribution(conn),
                    validate_usage_distribution(conn),
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
