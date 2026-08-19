"""
Build analytics_inventory_current_product_location.

This script creates and refreshes the current physical inventory aggregate by
product and source location.

Main rules:
- Source view is vw_inventory_physical_snapshot.
- Grain is snapshot_date_key + product_analytical_key + source_location_id.
- Current snapshot is selected with MAX(etl_loaded_at) from the physical view.
- Preserve only physical, business-ready inventory rows from the validated view.
- Do not infer company_source_key from location_name.
- Do not join products by name.
- Reconcile current_stock_qty back to vw_inventory_physical_snapshot for the
  current snapshot timestamp.

This script does not implement BI logic.
"""

from __future__ import annotations

from typing import Any, Dict

from core.database.mysql import get_db_connection


TABLE_NAME = "analytics_inventory_current_product_location"
SOURCE_VIEW = "vw_inventory_physical_snapshot"


def table_exists(conn: Any, table_name: str) -> bool:
    query = """
        SELECT COUNT(1) AS total
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = %s
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, (table_name,))
    row = cursor.fetchone()
    cursor.close()
    return bool(row and row["total"] > 0)


def view_exists(conn: Any, view_name: str) -> bool:
    query = """
        SELECT COUNT(1) AS total
        FROM information_schema.views
        WHERE table_schema = DATABASE()
          AND table_name = %s
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, (view_name,))
    row = cursor.fetchone()
    cursor.close()
    return bool(row and row["total"] > 0)


def fetch_one_dict(conn: Any, query: str) -> Dict[str, Any]:
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query)
    row = cursor.fetchone() or {}
    cursor.close()
    return row


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


def recreate_table(conn: Any) -> None:
    cursor = conn.cursor()
    cursor.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")

    ddl = f"""
    CREATE TABLE {TABLE_NAME} (
        inventory_current_product_location_key BIGINT AUTO_INCREMENT PRIMARY KEY,

        current_snapshot_loaded_at DATETIME NOT NULL,
        snapshot_date DATE NULL,
        snapshot_date_key INT NOT NULL,

        product_analytical_key BIGINT NOT NULL,
        odoo_product_id VARCHAR(100) NULL,
        odoo_product_name VARCHAR(500) NULL,
        product_code VARCHAR(255) NULL,
        wansoft_code VARCHAR(255) NULL,
        wansoft_product_name VARCHAR(500) NULL,
        wansoft_department VARCHAR(255) NULL,
        product_identity_status VARCHAR(100) NULL,
        dim_product_mapping_status VARCHAR(100) NULL,
        is_product_mapped BOOLEAN NOT NULL DEFAULT FALSE,
        is_product_review_required BOOLEAN NOT NULL DEFAULT FALSE,
        include_product_in_business_views BOOLEAN NOT NULL DEFAULT TRUE,

        source_location_id VARCHAR(100) NOT NULL,
        location_name VARCHAR(500) NULL,
        normalized_location_name VARCHAR(500) NULL,
        location_usage_type VARCHAR(100) NULL,
        is_virtual_location BOOLEAN NOT NULL DEFAULT FALSE,
        is_partner_location BOOLEAN NOT NULL DEFAULT FALSE,
        is_internal_location BOOLEAN NOT NULL DEFAULT TRUE,
        location_mapping_status VARCHAR(100) NULL,

        company_source_key VARCHAR(255) NULL,
        company_mapping_status VARCHAR(100) NULL,

        source_row_count BIGINT NOT NULL DEFAULT 0,
        current_stock_qty DECIMAL(18,4) NOT NULL DEFAULT 0,
        positive_stock_qty DECIMAL(18,4) NOT NULL DEFAULT 0,
        zero_stock_row_count BIGINT NOT NULL DEFAULT 0,
        negative_stock_qty DECIMAL(18,4) NOT NULL DEFAULT 0,
        negative_row_count BIGINT NOT NULL DEFAULT 0,

        include_in_business_views BOOLEAN NOT NULL DEFAULT TRUE,
        exclude_reason VARCHAR(500) NULL,
        aggregate_review_status VARCHAR(100) NOT NULL DEFAULT 'ok',

        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

        UNIQUE KEY uq_inventory_current_product_location (
            snapshot_date_key,
            product_analytical_key,
            source_location_id
        ),

        KEY idx_inventory_current_snapshot_loaded_at (
            current_snapshot_loaded_at
        ),

        KEY idx_inventory_current_date (
            snapshot_date_key
        ),

        KEY idx_inventory_current_product (
            product_analytical_key
        ),

        KEY idx_inventory_current_location (
            source_location_id
        ),

        KEY idx_inventory_current_business_views (
            include_in_business_views
        ),

        KEY idx_inventory_current_review_status (
            aggregate_review_status
        )
    )
    """

    cursor.execute(ddl)
    conn.commit()
    cursor.close()


def get_current_snapshot_loaded_at(conn: Any) -> Any:
    query = f"""
        SELECT MAX(etl_loaded_at) AS current_snapshot_loaded_at
        FROM {SOURCE_VIEW}
    """
    row = fetch_one_dict(conn, query)
    return row.get("current_snapshot_loaded_at")


def build_aggregate(conn: Any, current_snapshot_loaded_at: Any) -> None:
    if current_snapshot_loaded_at is None:
        raise RuntimeError("No current snapshot timestamp found in physical inventory view")

    sql = f"""
    INSERT INTO {TABLE_NAME} (
        current_snapshot_loaded_at,
        snapshot_date,
        snapshot_date_key,
        product_analytical_key,
        odoo_product_id,
        odoo_product_name,
        product_code,
        wansoft_code,
        wansoft_product_name,
        wansoft_department,
        product_identity_status,
        dim_product_mapping_status,
        is_product_mapped,
        is_product_review_required,
        include_product_in_business_views,
        source_location_id,
        location_name,
        normalized_location_name,
        location_usage_type,
        is_virtual_location,
        is_partner_location,
        is_internal_location,
        location_mapping_status,
        company_source_key,
        company_mapping_status,
        source_row_count,
        current_stock_qty,
        positive_stock_qty,
        zero_stock_row_count,
        negative_stock_qty,
        negative_row_count,
        include_in_business_views,
        exclude_reason,
        aggregate_review_status
    )
    SELECT
        MAX(etl_loaded_at) AS current_snapshot_loaded_at,
        MAX(snapshot_date) AS snapshot_date,
        snapshot_date_key,
        product_analytical_key,
        MAX(odoo_product_id) AS odoo_product_id,
        MAX(odoo_product_name) AS odoo_product_name,
        MAX(product_code) AS product_code,
        MAX(wansoft_code) AS wansoft_code,
        MAX(wansoft_product_name) AS wansoft_product_name,
        MAX(wansoft_department) AS wansoft_department,
        MAX(product_identity_status) AS product_identity_status,
        MAX(dim_product_mapping_status) AS dim_product_mapping_status,
        MAX(is_product_mapped) AS is_product_mapped,
        MAX(is_product_review_required) AS is_product_review_required,
        MAX(include_product_in_business_views) AS include_product_in_business_views,
        source_location_id,
        MAX(location_name) AS location_name,
        MAX(normalized_location_name) AS normalized_location_name,
        MAX(location_usage_type) AS location_usage_type,
        MAX(is_virtual_location) AS is_virtual_location,
        MAX(is_partner_location) AS is_partner_location,
        MAX(is_internal_location) AS is_internal_location,
        MAX(location_mapping_status) AS location_mapping_status,
        MAX(company_source_key) AS company_source_key,
        MAX(company_mapping_status) AS company_mapping_status,
        COUNT(1) AS source_row_count,
        COALESCE(SUM(stock_qty), 0) AS current_stock_qty,
        COALESCE(SUM(CASE WHEN stock_qty > 0 THEN stock_qty ELSE 0 END), 0) AS positive_stock_qty,
        SUM(CASE WHEN stock_qty = 0 THEN 1 ELSE 0 END) AS zero_stock_row_count,
        COALESCE(SUM(CASE WHEN stock_qty < 0 THEN stock_qty ELSE 0 END), 0) AS negative_stock_qty,
        SUM(CASE WHEN stock_qty < 0 THEN 1 ELSE 0 END) AS negative_row_count,
        CASE
            WHEN COALESCE(SUM(stock_qty), 0) >= 0
             AND SUM(CASE WHEN stock_qty < 0 THEN 1 ELSE 0 END) = 0
            THEN TRUE
            ELSE FALSE
        END AS include_in_business_views,
        NULLIF(
            CONCAT_WS(
                ' | ',
                CASE WHEN COALESCE(SUM(stock_qty), 0) < 0 THEN 'negative_current_stock' END,
                CASE WHEN SUM(CASE WHEN stock_qty < 0 THEN 1 ELSE 0 END) > 0 THEN 'contains_negative_source_rows' END
            ),
            ''
        ) AS exclude_reason,
        CASE
            WHEN COALESCE(SUM(stock_qty), 0) < 0 THEN 'negative_current_stock'
            WHEN SUM(CASE WHEN stock_qty < 0 THEN 1 ELSE 0 END) > 0 THEN 'contains_negative_source_rows'
            ELSE 'ok'
        END AS aggregate_review_status
    FROM {SOURCE_VIEW}
    WHERE etl_loaded_at = %s
    GROUP BY
        snapshot_date_key,
        product_analytical_key,
        source_location_id
    """

    cursor = conn.cursor()
    cursor.execute(sql, (current_snapshot_loaded_at,))
    conn.commit()
    cursor.close()


def get_summary(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            COUNT(1) AS total_rows,
            SUM(CASE WHEN include_in_business_views = TRUE THEN 1 ELSE 0 END) AS business_rows,
            SUM(CASE WHEN include_in_business_views = FALSE THEN 1 ELSE 0 END) AS excluded_rows,
            COALESCE(SUM(source_row_count), 0) AS total_source_row_count,
            COALESCE(SUM(current_stock_qty), 0) AS total_current_stock_qty,
            COALESCE(SUM(positive_stock_qty), 0) AS total_positive_stock_qty,
            COALESCE(SUM(negative_stock_qty), 0) AS total_negative_stock_qty,
            COALESCE(SUM(negative_row_count), 0) AS total_negative_row_count,
            MIN(current_snapshot_loaded_at) AS min_snapshot_loaded_at,
            MAX(current_snapshot_loaded_at) AS max_snapshot_loaded_at
        FROM {TABLE_NAME}
    """
    return fetch_one_dict(conn, query)


def print_summary(summary: Dict[str, Any]) -> None:
    print("=====================================================")
    print("ANALYTICS INVENTORY CURRENT PRODUCT LOCATION BUILD SUMMARY")
    print("=====================================================")
    print(f"table: {TABLE_NAME}")
    print(f"total_rows_prepared: {summary.get('total_rows')}")
    print(f"include_in_business_views: {summary.get('business_rows')}")
    print(f"excluded_from_business_views: {summary.get('excluded_rows')}")
    print(f"total_source_row_count: {summary.get('total_source_row_count')}")
    print(f"total_current_stock_qty: {summary.get('total_current_stock_qty')}")
    print(f"total_positive_stock_qty: {summary.get('total_positive_stock_qty')}")
    print(f"total_negative_stock_qty: {summary.get('total_negative_stock_qty')}")
    print(f"total_negative_row_count: {summary.get('total_negative_row_count')}")
    print(f"min_snapshot_loaded_at: {summary.get('min_snapshot_loaded_at')}")
    print(f"max_snapshot_loaded_at: {summary.get('max_snapshot_loaded_at')}")
    print("=====================================================")


def main() -> int:
    print("=====================================================")
    print("ANALYTICS INVENTORY CURRENT PRODUCT LOCATION BUILD START")
    print("=====================================================")

    conn = get_db_connection()

    try:
        apply_session_settings(conn)

        if not view_exists(conn, SOURCE_VIEW):
            raise RuntimeError(f"Required source view does not exist: {SOURCE_VIEW}")

        current_snapshot_loaded_at = get_current_snapshot_loaded_at(conn)
        recreate_table(conn)
        build_aggregate(conn, current_snapshot_loaded_at)
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
