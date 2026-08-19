
"""
Validate inventory analytical views.

Validates:
- vw_inventory_physical_snapshot exists
- vw_inventory_non_physical_snapshot exists
- physical view follows policy exactly
- non-physical view follows complement policy exactly
- physical and non-physical rows are complementary against analytics_inventory_snapshot
- physical view contains no partner or virtual locations
- physical view contains only business-ready rows
- non-physical rows have inventory_physical_exclude_reason

Run:
    python -m scripts.validate_inventory_snapshot_views
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.database.mysql import get_db_connection


SOURCE_TABLE = "analytics_inventory_snapshot"
PHYSICAL_VIEW = "vw_inventory_physical_snapshot"
NON_PHYSICAL_VIEW = "vw_inventory_non_physical_snapshot"


def fetch_all_dict(conn: Any, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params or ())
    rows = cursor.fetchall()
    cursor.close()
    return rows


def validation_result(name: str, status: str, details: Any = None) -> Dict[str, Any]:
    return {
        "validation": name,
        "status": status,
        "details": details,
    }


def object_exists(conn: Any, object_name: str) -> bool:
    query = """
        SELECT COUNT(1) AS total
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = %s
    """
    rows = fetch_all_dict(conn, query, (object_name,))
    return bool(rows and int(rows[0]["total"]) > 0)


def scalar(conn: Any, query: str) -> Any:
    rows = fetch_all_dict(conn, query)
    if not rows:
        return None
    first_row = rows[0]
    return next(iter(first_row.values()))


def validate_object_exists(conn: Any, object_name: str) -> Dict[str, Any]:
    exists = object_exists(conn, object_name)
    return validation_result(
        f"{object_name}_exists",
        "PASS" if exists else "FAIL",
        {"object_name": object_name, "exists": exists},
    )


def validate_physical_policy_count(conn: Any) -> Dict[str, Any]:
    expected = scalar(
        conn,
        f"""
        SELECT COUNT(1)
        FROM {SOURCE_TABLE}
        WHERE include_in_business_views = TRUE
          AND location_usage_type = 'internal_or_unknown'
        """,
    )
    actual = scalar(conn, f"SELECT COUNT(1) FROM {PHYSICAL_VIEW}")
    return validation_result(
        "physical_view_count_matches_policy",
        "PASS" if int(expected) == int(actual) else "FAIL",
        {"expected_rows": int(expected), "actual_rows": int(actual)},
    )


def validate_non_physical_policy_count(conn: Any) -> Dict[str, Any]:
    expected = scalar(
        conn,
        f"""
        SELECT COUNT(1)
        FROM {SOURCE_TABLE}
        WHERE include_in_business_views = FALSE
           OR location_usage_type <> 'internal_or_unknown'
        """,
    )
    actual = scalar(conn, f"SELECT COUNT(1) FROM {NON_PHYSICAL_VIEW}")
    return validation_result(
        "non_physical_view_count_matches_policy",
        "PASS" if int(expected) == int(actual) else "FAIL",
        {"expected_rows": int(expected), "actual_rows": int(actual)},
    )


def validate_views_are_complementary(conn: Any) -> Dict[str, Any]:
    source_rows = int(scalar(conn, f"SELECT COUNT(1) FROM {SOURCE_TABLE}"))
    physical_rows = int(scalar(conn, f"SELECT COUNT(1) FROM {PHYSICAL_VIEW}"))
    non_physical_rows = int(scalar(conn, f"SELECT COUNT(1) FROM {NON_PHYSICAL_VIEW}"))

    overlap_rows = int(
        scalar(
            conn,
            f"""
            SELECT COUNT(1)
            FROM {PHYSICAL_VIEW} p
            INNER JOIN {NON_PHYSICAL_VIEW} n
                ON p.inventory_snapshot_analytical_key = n.inventory_snapshot_analytical_key
            """,
        )
    )

    pass_status = (physical_rows + non_physical_rows == source_rows) and overlap_rows == 0

    return validation_result(
        "views_are_complementary",
        "PASS" if pass_status else "FAIL",
        {
            "source_rows": source_rows,
            "physical_rows": physical_rows,
            "non_physical_rows": non_physical_rows,
            "combined_rows": physical_rows + non_physical_rows,
            "overlap_rows": overlap_rows,
        },
    )


def validate_physical_only_internal(conn: Any) -> Dict[str, Any]:
    bad_rows = int(
        scalar(
            conn,
            f"""
            SELECT COUNT(1)
            FROM {PHYSICAL_VIEW}
            WHERE location_usage_type <> 'internal_or_unknown'
            """,
        )
    )
    return validation_result(
        "physical_view_only_internal_or_unknown",
        "PASS" if bad_rows == 0 else "FAIL",
        {"bad_rows": bad_rows},
    )


def validate_physical_only_business_ready(conn: Any) -> Dict[str, Any]:
    bad_rows = int(
        scalar(
            conn,
            f"""
            SELECT COUNT(1)
            FROM {PHYSICAL_VIEW}
            WHERE include_in_business_views <> TRUE
            """,
        )
    )
    return validation_result(
        "physical_view_only_business_ready",
        "PASS" if bad_rows == 0 else "FAIL",
        {"bad_rows": bad_rows},
    )


def validate_physical_no_negative_stock(conn: Any) -> Dict[str, Any]:
    negative_rows = int(
        scalar(
            conn,
            f"""
            SELECT COUNT(1)
            FROM {PHYSICAL_VIEW}
            WHERE stock_qty < 0
            """,
        )
    )
    total_stock_qty = scalar(conn, f"SELECT COALESCE(SUM(stock_qty), 0) FROM {PHYSICAL_VIEW}")
    return validation_result(
        "physical_view_has_no_negative_stock_rows",
        "PASS" if negative_rows == 0 else "FAIL",
        {"negative_rows": negative_rows, "total_stock_qty": str(total_stock_qty)},
    )


def validate_non_physical_has_exclude_reason(conn: Any) -> Dict[str, Any]:
    bad_rows = int(
        scalar(
            conn,
            f"""
            SELECT COUNT(1)
            FROM {NON_PHYSICAL_VIEW}
            WHERE inventory_physical_exclude_reason IS NULL
               OR TRIM(inventory_physical_exclude_reason) = ''
            """,
        )
    )
    return validation_result(
        "non_physical_view_has_exclude_reason",
        "PASS" if bad_rows == 0 else "FAIL",
        {"bad_rows": bad_rows},
    )


def validate_non_physical_distribution_available(conn: Any) -> Dict[str, Any]:
    rows = fetch_all_dict(
        conn,
        f"""
        SELECT
            location_usage_type,
            inventory_physical_exclude_reason,
            COUNT(1) AS total_rows,
            SUM(CASE WHEN stock_qty < 0 THEN 1 ELSE 0 END) AS negative_rows,
            COALESCE(SUM(stock_qty), 0) AS total_stock_qty
        FROM {NON_PHYSICAL_VIEW}
        GROUP BY
            location_usage_type,
            inventory_physical_exclude_reason
        ORDER BY total_stock_qty ASC
        """,
    )
    return validation_result(
        "non_physical_distribution_available",
        "PASS" if rows else "FAIL",
        rows,
    )


def validate_physical_summary_available(conn: Any) -> Dict[str, Any]:
    rows = fetch_all_dict(
        conn,
        f"""
        SELECT
            COUNT(1) AS total_rows,
            SUM(CASE WHEN stock_qty < 0 THEN 1 ELSE 0 END) AS negative_rows,
            SUM(CASE WHEN stock_qty = 0 THEN 1 ELSE 0 END) AS zero_rows,
            SUM(CASE WHEN stock_qty > 0 THEN 1 ELSE 0 END) AS positive_rows,
            COALESCE(SUM(stock_qty), 0) AS total_stock_qty
        FROM {PHYSICAL_VIEW}
        """,
    )
    return validation_result(
        "physical_summary_available",
        "PASS" if rows else "FAIL",
        rows[0] if rows else {},
    )


def print_result(result: Dict[str, Any]) -> None:
    print(f"{result['validation']}: {result['status']}")
    details = result.get("details")
    if details not in (None, [], {}):
        print(details)


def main() -> int:
    print("=====================================================")
    print("INVENTORY SNAPSHOT VIEWS VALIDATION START")
    print("=====================================================")

    conn = get_db_connection()
    results: List[Dict[str, Any]] = []

    try:
        results.append(validate_object_exists(conn, PHYSICAL_VIEW))
        results.append(validate_object_exists(conn, NON_PHYSICAL_VIEW))

        if all(result["status"] == "PASS" for result in results):
            results.extend(
                [
                    validate_physical_policy_count(conn),
                    validate_non_physical_policy_count(conn),
                    validate_views_are_complementary(conn),
                    validate_physical_only_internal(conn),
                    validate_physical_only_business_ready(conn),
                    validate_physical_no_negative_stock(conn),
                    validate_non_physical_has_exclude_reason(conn),
                    validate_physical_summary_available(conn),
                    validate_non_physical_distribution_available(conn),
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
