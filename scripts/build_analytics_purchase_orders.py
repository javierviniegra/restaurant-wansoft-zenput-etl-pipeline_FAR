"""
Build analytics_purchase_orders.

This version performs the aggregation inside MySQL with INSERT SELECT.
It avoids fetching the full grouped result set into Python.

Main rules:
- 1 row = 1 source purchase order group.
- Source is analytics_purchase_order_lines.
- Preserve all orders derived from lines.
- Aggregate line metrics and amounts from the validated line fact.
- Propagate business inclusion from line-level business flags.
- Flag inconsistent order-level company, vendor or date values.
- Do not recalculate amounts from quantity and unit price.

This script does not implement BI logic.
"""

from __future__ import annotations

from typing import Any, Dict

from core.database.mysql import get_db_connection


ANALYTICS_TABLE = "analytics_purchase_orders"
SOURCE_TABLE = "analytics_purchase_order_lines"


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


def fetch_one_dict(conn: Any, query: str) -> Dict[str, Any]:
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query)
    row = cursor.fetchone() or {}
    cursor.close()
    return row


def apply_session_settings(conn: Any) -> None:
    cursor = conn.cursor()
    statements = [
        "SET SESSION net_read_timeout = 600",
        "SET SESSION net_write_timeout = 600",
        "SET SESSION wait_timeout = 600",
        "SET SESSION interactive_timeout = 600",
        "SET SESSION group_concat_max_len = 1000000",
    ]

    for statement in statements:
        try:
            cursor.execute(statement)
        except Exception:
            pass

    conn.commit()
    cursor.close()


def create_table_if_missing(conn: Any) -> None:
    ddl = f"""
    CREATE TABLE IF NOT EXISTS {ANALYTICS_TABLE} (
        purchase_order_analytical_key BIGINT AUTO_INCREMENT PRIMARY KEY,

        source_system VARCHAR(50) NOT NULL,
        source_domain VARCHAR(100) NULL,
        source_order_id VARCHAR(100) NOT NULL,
        purchase_order_name VARCHAR(255) NULL,

        company_source_key VARCHAR(255) NULL,
        company_analytical_key BIGINT NULL,
        company_id VARCHAR(100) NULL,
        company_name VARCHAR(255) NULL,
        final_purchase_source_status VARCHAR(100) NULL,
        company_migration_type VARCHAR(100) NULL,
        history_source VARCHAR(100) NULL,
        include_odoo_history BOOLEAN NULL,
        operational_start_date DATE NULL,
        migration_policy_source VARCHAR(100) NULL,

        order_date DATETIME NULL,
        order_date_key INT NULL,

        vendor_analytical_key BIGINT NULL,
        vendor_id VARCHAR(100) NULL,
        vendor_name VARCHAR(255) NULL,
        normalized_vendor_name VARCHAR(255) NULL,
        is_internal_vendor BOOLEAN NOT NULL DEFAULT FALSE,
        include_vendor_in_business_views BOOLEAN NOT NULL DEFAULT TRUE,

        line_count BIGINT NOT NULL DEFAULT 0,
        business_line_count BIGINT NOT NULL DEFAULT 0,
        excluded_line_count BIGINT NOT NULL DEFAULT 0,
        review_required_line_count BIGINT NOT NULL DEFAULT 0,
        internal_vendor_line_count BIGINT NOT NULL DEFAULT 0,
        review_required_product_line_count BIGINT NOT NULL DEFAULT 0,
        orphan_product_line_count BIGINT NOT NULL DEFAULT 0,

        product_qty_total DECIMAL(18,4) NULL,
        qty_received_total DECIMAL(18,4) NULL,
        qty_invoiced_total DECIMAL(18,4) NULL,
        price_subtotal_total DECIMAL(18,4) NULL,
        price_total_total DECIMAL(18,4) NULL,

        state_values TEXT NULL,
        canonical_loaded_at_min TIMESTAMP NULL,
        canonical_loaded_at_max TIMESTAMP NULL,

        include_in_business_views BOOLEAN NOT NULL DEFAULT TRUE,
        exclude_reason VARCHAR(500) NULL,
        order_review_status VARCHAR(100) NULL,

        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

        UNIQUE KEY uq_analytics_purchase_orders_source_order (
            source_system,
            source_order_id
        ),

        KEY idx_analytics_purchase_orders_company_date (
            company_source_key,
            order_date_key
        ),

        KEY idx_analytics_purchase_orders_vendor (
            vendor_analytical_key
        ),

        KEY idx_analytics_purchase_orders_source_system (
            source_system
        ),

        KEY idx_analytics_purchase_orders_business_views (
            include_in_business_views
        )
    )
    """
    cursor = conn.cursor()
    cursor.execute(ddl)
    conn.commit()
    cursor.close()


def refresh_orders(conn: Any) -> None:
    delete_sql = f"DELETE FROM {ANALYTICS_TABLE}"

    insert_sql = f"""
    INSERT INTO {ANALYTICS_TABLE} (
        source_system,
        source_domain,
        source_order_id,
        purchase_order_name,
        company_source_key,
        company_analytical_key,
        company_id,
        company_name,
        final_purchase_source_status,
        company_migration_type,
        history_source,
        include_odoo_history,
        operational_start_date,
        migration_policy_source,
        order_date,
        order_date_key,
        vendor_analytical_key,
        vendor_id,
        vendor_name,
        normalized_vendor_name,
        is_internal_vendor,
        include_vendor_in_business_views,
        line_count,
        business_line_count,
        excluded_line_count,
        review_required_line_count,
        internal_vendor_line_count,
        review_required_product_line_count,
        orphan_product_line_count,
        product_qty_total,
        qty_received_total,
        qty_invoiced_total,
        price_subtotal_total,
        price_total_total,
        state_values,
        canonical_loaded_at_min,
        canonical_loaded_at_max,
        include_in_business_views,
        exclude_reason,
        order_review_status
    )
    SELECT
        g.source_system,
        g.source_domain,
        g.source_order_key,
        g.purchase_order_name,
        g.company_source_key,
        g.company_analytical_key,
        g.company_id,
        g.company_name,
        g.final_purchase_source_status,
        g.company_migration_type,
        g.history_source,
        g.include_odoo_history,
        g.operational_start_date,
        g.migration_policy_source,
        g.order_date,
        g.order_date_key,
        g.vendor_analytical_key,
        g.vendor_id,
        g.vendor_name,
        g.normalized_vendor_name,
        g.is_internal_vendor,
        g.include_vendor_in_business_views,
        g.line_count,
        g.business_line_count,
        g.excluded_line_count,
        g.review_required_line_count,
        g.internal_vendor_line_count,
        g.review_required_product_line_count,
        g.orphan_product_line_count,
        g.product_qty_total,
        g.qty_received_total,
        g.qty_invoiced_total,
        g.price_subtotal_total,
        g.price_total_total,
        g.state_values,
        g.canonical_loaded_at_min,
        g.canonical_loaded_at_max,
        CASE
            WHEN g.business_line_count > 0
             AND g.distinct_company_count <= 1
             AND g.distinct_order_date_key_count <= 1
             AND g.distinct_vendor_count <= 1
             AND g.missing_source_order_id_lines = 0
            THEN TRUE
            ELSE FALSE
        END AS include_in_business_views,
        NULLIF(
            CONCAT_WS(
                ' | ',
                CASE WHEN g.business_line_count = 0 THEN 'no_business_lines' ELSE NULL END,
                CASE WHEN g.internal_vendor_line_count > 0 AND g.business_line_count = 0 THEN 'internal_vendor' ELSE NULL END,
                CASE WHEN g.review_required_product_line_count > 0 AND g.business_line_count = 0 THEN 'review_required_product' ELSE NULL END,
                CASE WHEN g.orphan_product_line_count > 0 AND g.business_line_count = 0 THEN 'orphan_product' ELSE NULL END,
                CASE WHEN g.distinct_company_count > 1 THEN 'inconsistent_company_on_order' ELSE NULL END,
                CASE WHEN g.distinct_order_date_key_count > 1 THEN 'inconsistent_order_date_on_order' ELSE NULL END,
                CASE WHEN g.distinct_vendor_count > 1 THEN 'inconsistent_vendor_on_order' ELSE NULL END,
                CASE WHEN g.missing_source_order_id_lines > 0 THEN 'missing_source_order_id' ELSE NULL END
            ),
            ''
        ) AS exclude_reason,
        CASE
            WHEN g.distinct_company_count > 1
              OR g.distinct_order_date_key_count > 1
              OR g.distinct_vendor_count > 1
              OR g.missing_source_order_id_lines > 0
            THEN 'review_required'
            WHEN g.review_required_line_count > 0 THEN 'has_review_required_lines'
            ELSE 'ok'
        END AS order_review_status
    FROM (
        SELECT
            source_system,
            COALESCE(NULLIF(TRIM(source_order_id), ''), CONCAT('__missing__:', canonical_purchase_order_line_id)) AS source_order_key,
            MIN(source_domain) AS source_domain,
            MIN(purchase_order_name) AS purchase_order_name,

            MIN(company_source_key) AS company_source_key,
            MIN(company_analytical_key) AS company_analytical_key,
            MIN(company_id) AS company_id,
            MIN(company_name) AS company_name,
            MIN(final_purchase_source_status) AS final_purchase_source_status,
            MIN(company_migration_type) AS company_migration_type,
            MIN(history_source) AS history_source,
            MAX(include_odoo_history) AS include_odoo_history,
            MIN(operational_start_date) AS operational_start_date,
            MIN(migration_policy_source) AS migration_policy_source,

            MIN(order_date) AS order_date,
            MIN(order_date_key) AS order_date_key,

            MIN(vendor_analytical_key) AS vendor_analytical_key,
            MIN(vendor_id) AS vendor_id,
            MIN(vendor_name) AS vendor_name,
            MIN(normalized_vendor_name) AS normalized_vendor_name,
            MAX(is_internal_vendor) AS is_internal_vendor,
            MIN(include_vendor_in_business_views) AS include_vendor_in_business_views,

            COUNT(1) AS line_count,
            SUM(CASE WHEN include_in_business_views = TRUE THEN 1 ELSE 0 END) AS business_line_count,
            SUM(CASE WHEN include_in_business_views = FALSE THEN 1 ELSE 0 END) AS excluded_line_count,
            SUM(CASE WHEN line_review_status = 'review_required' THEN 1 ELSE 0 END) AS review_required_line_count,
            SUM(CASE WHEN is_internal_vendor = TRUE THEN 1 ELSE 0 END) AS internal_vendor_line_count,
            SUM(CASE WHEN is_product_review_required = TRUE THEN 1 ELSE 0 END) AS review_required_product_line_count,
            SUM(CASE WHEN exclude_reason LIKE '%orphan_product%' THEN 1 ELSE 0 END) AS orphan_product_line_count,

            COALESCE(SUM(product_qty), 0) AS product_qty_total,
            COALESCE(SUM(qty_received), 0) AS qty_received_total,
            COALESCE(SUM(qty_invoiced), 0) AS qty_invoiced_total,
            COALESCE(SUM(price_subtotal), 0) AS price_subtotal_total,
            COALESCE(SUM(price_total), 0) AS price_total_total,

            GROUP_CONCAT(DISTINCT state ORDER BY state SEPARATOR ' | ') AS state_values,
            MIN(canonical_loaded_at) AS canonical_loaded_at_min,
            MAX(canonical_loaded_at) AS canonical_loaded_at_max,

            COUNT(DISTINCT NULLIF(TRIM(company_source_key), '')) AS distinct_company_count,
            COUNT(DISTINCT order_date_key) AS distinct_order_date_key_count,
            COUNT(DISTINCT vendor_analytical_key) AS distinct_vendor_count,
            SUM(CASE WHEN source_order_id IS NULL OR TRIM(source_order_id) = '' THEN 1 ELSE 0 END) AS missing_source_order_id_lines
        FROM {SOURCE_TABLE}
        GROUP BY
            source_system,
            COALESCE(NULLIF(TRIM(source_order_id), ''), CONCAT('__missing__:', canonical_purchase_order_line_id))
    ) g
    """

    cursor = conn.cursor()
    cursor.execute(delete_sql)
    conn.commit()
    cursor.execute(insert_sql)
    conn.commit()
    cursor.close()


def build_summary(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            COUNT(1) AS total_orders,
            SUM(CASE WHEN include_in_business_views = TRUE THEN 1 ELSE 0 END) AS included_orders,
            SUM(CASE WHEN include_in_business_views = FALSE THEN 1 ELSE 0 END) AS excluded_orders,
            SUM(CASE WHEN order_review_status IN ('review_required', 'has_review_required_lines') THEN 1 ELSE 0 END) AS review_required_orders,
            SUM(CASE WHEN exclude_reason LIKE '%no_business_lines%' THEN 1 ELSE 0 END) AS no_business_line_orders,
            SUM(CASE WHEN exclude_reason LIKE '%inconsistent_company_on_order%' THEN 1 ELSE 0 END) AS inconsistent_company_orders,
            SUM(CASE WHEN exclude_reason LIKE '%inconsistent_order_date_on_order%' THEN 1 ELSE 0 END) AS inconsistent_date_orders,
            SUM(CASE WHEN exclude_reason LIKE '%inconsistent_vendor_on_order%' THEN 1 ELSE 0 END) AS inconsistent_vendor_orders,
            COALESCE(SUM(line_count), 0) AS total_line_count,
            COALESCE(SUM(business_line_count), 0) AS total_business_line_count,
            COALESCE(SUM(excluded_line_count), 0) AS total_excluded_line_count
        FROM {ANALYTICS_TABLE}
    """
    return fetch_one_dict(conn, query)


def print_summary(summary: Dict[str, Any]) -> None:
    print("=====================================================")
    print("ANALYTICS PURCHASE ORDERS BUILD SUMMARY")
    print("=====================================================")
    print(f"table: {ANALYTICS_TABLE}")
    print(f"total_orders_prepared: {int(summary.get('total_orders') or 0)}")
    print(f"include_in_business_views: {int(summary.get('included_orders') or 0)}")
    print(f"excluded_from_business_views: {int(summary.get('excluded_orders') or 0)}")
    print(f"review_required_orders: {int(summary.get('review_required_orders') or 0)}")
    print(f"no_business_line_orders: {int(summary.get('no_business_line_orders') or 0)}")
    print(f"inconsistent_company_orders: {int(summary.get('inconsistent_company_orders') or 0)}")
    print(f"inconsistent_date_orders: {int(summary.get('inconsistent_date_orders') or 0)}")
    print(f"inconsistent_vendor_orders: {int(summary.get('inconsistent_vendor_orders') or 0)}")
    print(f"total_line_count: {int(summary.get('total_line_count') or 0)}")
    print(f"total_business_line_count: {int(summary.get('total_business_line_count') or 0)}")
    print(f"total_excluded_line_count: {int(summary.get('total_excluded_line_count') or 0)}")
    print("=====================================================")


def main() -> int:
    print("=====================================================")
    print("ANALYTICS PURCHASE ORDERS BUILD START")
    print("=====================================================")

    conn = get_db_connection()

    try:
        apply_session_settings(conn)
        create_table_if_missing(conn)
        refresh_orders(conn)
        summary = build_summary(conn)
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
