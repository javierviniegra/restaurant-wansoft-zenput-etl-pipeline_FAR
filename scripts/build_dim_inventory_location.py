"""
Build dim_inventory_location and inventory_location_company_mapping_config.

Purpose:
- Discover all inventory source locations from analytics_inventory_snapshot.
- Create a governed inventory location dimension.
- Preserve partner, virtual, and internal_or_unknown locations.
- Do not infer company_source_key from location names.
- Use inventory_location_company_mapping_config for explicit company mapping only.

Run:
    python -m scripts.build_dim_inventory_location
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.database.mysql import get_db_connection


SOURCE_TABLE = "analytics_inventory_snapshot"
CURRENT_PHYSICAL_TABLE = "analytics_inventory_current_product_location"
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


def table_has_column(conn: Any, table_name: str, column_name: str) -> bool:
    query = """
        SELECT COUNT(1) AS total
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND column_name = %s
    """
    row = fetch_one_dict(conn, query, (table_name, column_name))
    return bool(row and int(row["total"]) > 0)


def column_expr(conn: Any, table_name: str, column_name: str, fallback_sql: str) -> str:
    if table_has_column(conn, table_name, column_name):
        return column_name
    return fallback_sql


def apply_session_settings(conn: Any) -> None:
    statements = [
        "SET SESSION net_read_timeout = 600",
        "SET SESSION net_write_timeout = 600",
        "SET SESSION wait_timeout = 28800",
        "SET SESSION interactive_timeout = 28800",
        "SET SESSION group_concat_max_len = 1048576",
    ]
    cursor = conn.cursor()
    for statement in statements:
        try:
            cursor.execute(statement)
        except Exception:
            pass
    conn.commit()
    cursor.close()


def create_mapping_config_if_needed(conn: Any) -> None:
    ddl = f"""
    CREATE TABLE IF NOT EXISTS {MAPPING_TABLE} (
        mapping_config_key BIGINT AUTO_INCREMENT PRIMARY KEY,
        source_system VARCHAR(50) NOT NULL DEFAULT 'odoo',
        source_location_id VARCHAR(100) NOT NULL,
        location_name_snapshot VARCHAR(500) NULL,
        company_source_key VARCHAR(255) NOT NULL,
        mapped_company_name VARCHAR(500) NULL,
        mapping_status VARCHAR(100) NOT NULL DEFAULT 'approved',
        mapping_method VARCHAR(100) NOT NULL DEFAULT 'manual_governance',
        mapping_notes TEXT NULL,
        effective_from_date DATE NULL,
        effective_to_date DATE NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_inventory_location_company_mapping_config (
            source_system,
            source_location_id,
            company_source_key,
            is_active
        ),
        KEY idx_inventory_location_company_mapping_source_location (
            source_system,
            source_location_id
        ),
        KEY idx_inventory_location_company_mapping_status (
            mapping_status,
            is_active
        )
    )
    """
    cursor = conn.cursor()
    cursor.execute(ddl)
    conn.commit()
    cursor.close()


def recreate_dim_table(conn: Any) -> None:
    cursor = conn.cursor()
    cursor.execute(f"DROP TABLE IF EXISTS {DIM_TABLE}")

    ddl = f"""
    CREATE TABLE {DIM_TABLE} (
        inventory_location_key BIGINT AUTO_INCREMENT PRIMARY KEY,

        source_system VARCHAR(50) NOT NULL DEFAULT 'odoo',
        source_location_id VARCHAR(100) NOT NULL,
        location_name VARCHAR(500) NULL,
        normalized_location_name VARCHAR(500) NULL,
        location_usage_type VARCHAR(100) NOT NULL,

        is_virtual_location BOOLEAN NOT NULL DEFAULT FALSE,
        is_partner_location BOOLEAN NOT NULL DEFAULT FALSE,
        is_internal_location BOOLEAN NOT NULL DEFAULT FALSE,

        parent_source_location_id VARCHAR(100) NULL,
        parent_location_name VARCHAR(500) NULL,
        location_path VARCHAR(1000) NULL,
        location_depth INT NULL,

        odoo_location_type VARCHAR(100) NULL,
        odoo_warehouse_id VARCHAR(100) NULL,
        odoo_warehouse_name VARCHAR(500) NULL,
        odoo_company_id VARCHAR(100) NULL,
        odoo_company_name VARCHAR(500) NULL,

        company_source_key VARCHAR(255) NULL,
        mapped_company_name VARCHAR(500) NULL,
        company_mapping_status VARCHAR(100) NOT NULL DEFAULT 'pending_location_mapping',
        company_mapping_method VARCHAR(100) NULL,
        company_mapping_notes TEXT NULL,

        include_in_inventory_physical_views BOOLEAN NOT NULL DEFAULT FALSE,
        include_in_company_inventory_views BOOLEAN NOT NULL DEFAULT FALSE,

        location_identity_status VARCHAR(100) NOT NULL DEFAULT 'active_source_location',
        location_review_status VARCHAR(100) NOT NULL DEFAULT 'needs_governance_review',
        location_mapping_status VARCHAR(100) NULL,

        first_seen_snapshot_date_key INT NULL,
        last_seen_snapshot_date_key INT NULL,
        current_source_row_count BIGINT NOT NULL DEFAULT 0,
        historical_source_row_count BIGINT NOT NULL DEFAULT 0,
        current_stock_qty DECIMAL(18,4) NULL,

        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

        UNIQUE KEY uq_dim_inventory_location_source (
            source_system,
            source_location_id
        ),
        KEY idx_dim_inventory_location_usage_type (location_usage_type),
        KEY idx_dim_inventory_location_company_mapping_status (company_mapping_status),
        KEY idx_dim_inventory_location_company_source_key (company_source_key),
        KEY idx_dim_inventory_location_physical_views (include_in_inventory_physical_views),
        KEY idx_dim_inventory_location_company_views (include_in_company_inventory_views),
        KEY idx_dim_inventory_location_review_status (location_review_status)
    )
    """
    cursor.execute(ddl)
    conn.commit()
    cursor.close()


def insert_dim_rows(conn: Any) -> None:
    if not object_exists(conn, SOURCE_TABLE):
        raise RuntimeError(f"Required source table does not exist: {SOURCE_TABLE}")

    is_virtual_expr = column_expr(conn, SOURCE_TABLE, "is_virtual_location", "CASE WHEN location_usage_type = 'virtual' THEN TRUE ELSE FALSE END")
    is_partner_expr = column_expr(conn, SOURCE_TABLE, "is_partner_location", "CASE WHEN location_usage_type = 'partner' THEN TRUE ELSE FALSE END")
    is_internal_expr = column_expr(conn, SOURCE_TABLE, "is_internal_location", "CASE WHEN location_usage_type = 'internal_or_unknown' THEN TRUE ELSE FALSE END")
    location_mapping_status_expr = column_expr(conn, SOURCE_TABLE, "location_mapping_status", "NULL")
    company_source_key_expr = column_expr(conn, SOURCE_TABLE, "company_source_key", "NULL")
    company_mapping_status_expr = column_expr(conn, SOURCE_TABLE, "company_mapping_status", "NULL")

    current_join_sql = """
        SELECT
            source_location_id,
            SUM(source_row_count) AS current_source_row_count,
            COALESCE(SUM(current_stock_qty), 0) AS current_stock_qty
        FROM analytics_inventory_current_product_location
        GROUP BY source_location_id
    """ if object_exists(conn, CURRENT_PHYSICAL_TABLE) else """
        SELECT
            CAST(NULL AS CHAR(100)) AS source_location_id,
            CAST(0 AS SIGNED) AS current_source_row_count,
            CAST(NULL AS DECIMAL(18,4)) AS current_stock_qty
        WHERE 1 = 0
    """

    sql = f"""
    INSERT INTO {DIM_TABLE} (
        source_system,
        source_location_id,
        location_name,
        normalized_location_name,
        location_usage_type,
        is_virtual_location,
        is_partner_location,
        is_internal_location,
        company_source_key,
        mapped_company_name,
        company_mapping_status,
        company_mapping_method,
        company_mapping_notes,
        include_in_inventory_physical_views,
        include_in_company_inventory_views,
        location_identity_status,
        location_review_status,
        location_mapping_status,
        first_seen_snapshot_date_key,
        last_seen_snapshot_date_key,
        current_source_row_count,
        historical_source_row_count,
        current_stock_qty
    )
    WITH source_locations AS (
        SELECT
            CAST(source_location_id AS CHAR) AS source_location_id,
            MAX(location_name) AS location_name,
            MAX(normalized_location_name) AS normalized_location_name,
            CASE
                WHEN COUNT(DISTINCT location_usage_type) > 1 THEN 'mixed_usage_type_review_required'
                ELSE MAX(location_usage_type)
            END AS location_usage_type,
            MAX({is_virtual_expr}) AS is_virtual_location,
            MAX({is_partner_expr}) AS is_partner_location,
            MAX({is_internal_expr}) AS is_internal_location,
            MAX({location_mapping_status_expr}) AS location_mapping_status,
            MAX({company_source_key_expr}) AS source_company_source_key,
            MAX({company_mapping_status_expr}) AS source_company_mapping_status,
            MIN(snapshot_date_key) AS first_seen_snapshot_date_key,
            MAX(snapshot_date_key) AS last_seen_snapshot_date_key,
            COUNT(1) AS historical_source_row_count
        FROM {SOURCE_TABLE}
        WHERE source_location_id IS NOT NULL
        GROUP BY CAST(source_location_id AS CHAR)
    ),
    current_usage AS (
        {current_join_sql}
    ),
    active_mapping AS (
        SELECT
            source_system,
            CAST(source_location_id AS CHAR) AS source_location_id,
            COUNT(1) AS active_mapping_count,
            MAX(company_source_key) AS company_source_key,
            MAX(mapped_company_name) AS mapped_company_name,
            MAX(mapping_status) AS mapping_status,
            MAX(mapping_method) AS mapping_method,
            GROUP_CONCAT(mapping_notes SEPARATOR ' | ') AS mapping_notes
        FROM {MAPPING_TABLE}
        WHERE is_active = TRUE
        GROUP BY
            source_system,
            CAST(source_location_id AS CHAR)
    )
    SELECT
        %s AS source_system,
        s.source_location_id,
        s.location_name,
        s.normalized_location_name,
        s.location_usage_type,
        COALESCE(s.is_virtual_location, FALSE) AS is_virtual_location,
        COALESCE(s.is_partner_location, FALSE) AS is_partner_location,
        COALESCE(s.is_internal_location, FALSE) AS is_internal_location,
        CASE
            WHEN m.active_mapping_count = 1 AND m.mapping_status = 'approved'
            THEN m.company_source_key
            ELSE NULL
        END AS company_source_key,
        CASE
            WHEN m.active_mapping_count = 1 AND m.mapping_status = 'approved'
            THEN m.mapped_company_name
            ELSE NULL
        END AS mapped_company_name,
        CASE
            WHEN m.active_mapping_count > 1 THEN 'conflicting_mapping'
            WHEN m.active_mapping_count = 1 THEN m.mapping_status
            WHEN s.source_company_source_key IS NOT NULL AND s.source_company_mapping_status = 'approved' THEN 'approved_from_source'
            ELSE 'pending_location_mapping'
        END AS company_mapping_status,
        CASE
            WHEN m.active_mapping_count = 1 THEN m.mapping_method
            WHEN s.source_company_source_key IS NOT NULL AND s.source_company_mapping_status = 'approved' THEN 'source_field_preserved'
            ELSE NULL
        END AS company_mapping_method,
        CASE
            WHEN m.active_mapping_count = 1 THEN m.mapping_notes
            WHEN m.active_mapping_count > 1 THEN 'More than one active mapping exists for this source location.'
            ELSE NULL
        END AS company_mapping_notes,
        CASE
            WHEN s.location_usage_type = 'internal_or_unknown' THEN TRUE
            ELSE FALSE
        END AS include_in_inventory_physical_views,
        CASE
            WHEN s.location_usage_type = 'internal_or_unknown'
             AND m.active_mapping_count = 1
             AND m.mapping_status = 'approved'
             AND m.company_source_key IS NOT NULL
            THEN TRUE
            ELSE FALSE
        END AS include_in_company_inventory_views,
        'active_source_location' AS location_identity_status,
        CASE
            WHEN s.location_usage_type IN ('partner', 'virtual') THEN 'non_physical_location'
            WHEN s.location_usage_type = 'mixed_usage_type_review_required' THEN 'mapping_review_required'
            WHEN m.active_mapping_count > 1 THEN 'mapping_review_required'
            WHEN s.location_usage_type = 'internal_or_unknown'
             AND m.active_mapping_count = 1
             AND m.mapping_status = 'approved'
            THEN 'ok'
            WHEN s.location_usage_type = 'internal_or_unknown' THEN 'needs_governance_review'
            ELSE 'needs_governance_review'
        END AS location_review_status,
        s.location_mapping_status,
        s.first_seen_snapshot_date_key,
        s.last_seen_snapshot_date_key,
        COALESCE(c.current_source_row_count, 0) AS current_source_row_count,
        s.historical_source_row_count,
        c.current_stock_qty
    FROM source_locations s
    LEFT JOIN current_usage c
        ON c.source_location_id = s.source_location_id
    LEFT JOIN active_mapping m
        ON m.source_system = %s
       AND m.source_location_id = s.source_location_id
    """

    cursor = conn.cursor()
    cursor.execute(sql, (SOURCE_SYSTEM, SOURCE_SYSTEM))
    conn.commit()
    cursor.close()


def get_summary(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            COUNT(1) AS total_locations,
            SUM(CASE WHEN location_usage_type = 'internal_or_unknown' THEN 1 ELSE 0 END) AS internal_or_unknown_locations,
            SUM(CASE WHEN location_usage_type = 'partner' THEN 1 ELSE 0 END) AS partner_locations,
            SUM(CASE WHEN location_usage_type = 'virtual' THEN 1 ELSE 0 END) AS virtual_locations,
            SUM(CASE WHEN include_in_inventory_physical_views = TRUE THEN 1 ELSE 0 END) AS physical_view_eligible_locations,
            SUM(CASE WHEN include_in_company_inventory_views = TRUE THEN 1 ELSE 0 END) AS company_view_eligible_locations,
            SUM(CASE WHEN company_mapping_status = 'approved' THEN 1 ELSE 0 END) AS approved_company_mappings,
            SUM(CASE WHEN company_mapping_status = 'pending_location_mapping' THEN 1 ELSE 0 END) AS pending_company_mappings,
            SUM(CASE WHEN location_review_status = 'needs_governance_review' THEN 1 ELSE 0 END) AS needs_governance_review_locations,
            SUM(CASE WHEN location_review_status = 'non_physical_location' THEN 1 ELSE 0 END) AS non_physical_locations,
            COALESCE(SUM(current_source_row_count), 0) AS current_source_row_count,
            COALESCE(SUM(current_stock_qty), 0) AS current_stock_qty
        FROM {DIM_TABLE}
    """
    return fetch_one_dict(conn, query)


def print_summary(summary: Dict[str, Any]) -> None:
    print("=====================================================")
    print("DIM INVENTORY LOCATION BUILD SUMMARY")
    print("=====================================================")
    print(f"table: {DIM_TABLE}")
    for key, value in summary.items():
        print(f"{key}: {value}")
    print("=====================================================")


def main() -> int:
    print("=====================================================")
    print("DIM INVENTORY LOCATION BUILD START")
    print("=====================================================")

    conn = get_db_connection()

    try:
        apply_session_settings(conn)
        if not object_exists(conn, SOURCE_TABLE):
            raise RuntimeError(f"Required source table does not exist: {SOURCE_TABLE}")

        create_mapping_config_if_needed(conn)
        recreate_dim_table(conn)
        insert_dim_rows(conn)
        summary = get_summary(conn)
        print_summary(summary)
        print("BUILD RESULT: COMPLETED")
        return 0
    except Exception as exc:
        print("BUILD RESULT: FAILED")
        print(f"error: {exc}")
        return 1
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
