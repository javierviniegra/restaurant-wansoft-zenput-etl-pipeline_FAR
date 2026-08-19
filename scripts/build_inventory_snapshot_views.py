
"""
Build inventory analytical views.

Creates:
- vw_inventory_physical_snapshot
- vw_inventory_non_physical_snapshot

Policy:
- analytics_inventory_snapshot remains complete evidence.
- Physical inventory views include only rows where:
    include_in_business_views = TRUE
    and location_usage_type = 'internal_or_unknown'
- Partner and virtual locations remain available in diagnostic views.
- No company_source_key is inferred from location_name.

Run:
    python -m scripts.build_inventory_snapshot_views
"""

from __future__ import annotations

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


def object_exists(conn: Any, object_name: str) -> bool:
    query = """
        SELECT COUNT(1) AS total
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = %s
    """
    rows = fetch_all_dict(conn, query, (object_name,))
    return bool(rows and int(rows[0]["total"]) > 0)


def create_physical_view(conn: Any) -> None:
    sql = f"""
    CREATE OR REPLACE VIEW {PHYSICAL_VIEW} AS
    SELECT
        a.*,
        TRUE AS include_in_inventory_physical_views,
        CAST(NULL AS CHAR(100)) AS inventory_physical_exclude_reason
    FROM {SOURCE_TABLE} a
    WHERE a.include_in_business_views = TRUE
      AND a.location_usage_type = 'internal_or_unknown'
    """
    cursor = conn.cursor()
    cursor.execute(sql)
    conn.commit()
    cursor.close()


def create_non_physical_view(conn: Any) -> None:
    sql = f"""
    CREATE OR REPLACE VIEW {NON_PHYSICAL_VIEW} AS
    SELECT
        a.*,
        FALSE AS include_in_inventory_physical_views,
        CASE
            WHEN a.include_in_business_views = FALSE THEN 'not_business_ready'
            WHEN a.location_usage_type = 'partner' THEN 'non_physical_partner_location'
            WHEN a.location_usage_type = 'virtual' THEN 'non_physical_virtual_location'
            ELSE 'unknown_location_usage_type'
        END AS inventory_physical_exclude_reason
    FROM {SOURCE_TABLE} a
    WHERE a.include_in_business_views = FALSE
       OR a.location_usage_type <> 'internal_or_unknown'
    """
    cursor = conn.cursor()
    cursor.execute(sql)
    conn.commit()
    cursor.close()


def summarize_view(conn: Any, view_name: str) -> Dict[str, Any]:
    query = f"""
        SELECT
            COUNT(1) AS total_rows,
            SUM(CASE WHEN stock_qty < 0 THEN 1 ELSE 0 END) AS negative_rows,
            SUM(CASE WHEN stock_qty = 0 THEN 1 ELSE 0 END) AS zero_rows,
            SUM(CASE WHEN stock_qty > 0 THEN 1 ELSE 0 END) AS positive_rows,
            COALESCE(SUM(stock_qty), 0) AS total_stock_qty,
            COALESCE(SUM(CASE WHEN stock_qty < 0 THEN stock_qty ELSE 0 END), 0) AS negative_stock_qty,
            COALESCE(SUM(CASE WHEN stock_qty > 0 THEN stock_qty ELSE 0 END), 0) AS positive_stock_qty
        FROM {view_name}
    """
    rows = fetch_all_dict(conn, query)
    return rows[0] if rows else {}


def summarize_non_physical_distribution(conn: Any) -> List[Dict[str, Any]]:
    query = f"""
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
    """
    return fetch_all_dict(conn, query)


def print_summary(name: str, summary: Dict[str, Any]) -> None:
    print("-----------------------------------------------------")
    print(name)
    print("-----------------------------------------------------")
    for key, value in summary.items():
        print(f"{key}: {value}")


def print_distribution(rows: List[Dict[str, Any]]) -> None:
    print("-----------------------------------------------------")
    print("vw_inventory_non_physical_snapshot distribution")
    print("-----------------------------------------------------")
    if not rows:
        print("<no rows>")
        return
    for row in rows:
        print(row)


def build_views(conn: Any) -> None:
    if not object_exists(conn, SOURCE_TABLE):
        raise RuntimeError(f"Required source table does not exist: {SOURCE_TABLE}")

    create_physical_view(conn)
    create_non_physical_view(conn)


def main() -> int:
    print("=====================================================")
    print("INVENTORY SNAPSHOT VIEWS BUILD START")
    print("=====================================================")

    conn = get_db_connection()

    try:
        build_views(conn)

        physical_summary = summarize_view(conn, PHYSICAL_VIEW)
        non_physical_summary = summarize_view(conn, NON_PHYSICAL_VIEW)
        non_physical_distribution = summarize_non_physical_distribution(conn)

        print_summary(PHYSICAL_VIEW, physical_summary)
        print_summary(NON_PHYSICAL_VIEW, non_physical_summary)
        print_distribution(non_physical_distribution)

        print("=====================================================")
        print("BUILD RESULT: COMPLETED")
        print("=====================================================")
        return 0
    except Exception as exc:
        print("=====================================================")
        print("BUILD RESULT: FAILED")
        print("=====================================================")
        print(f"error: {exc}")
        return 1
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
