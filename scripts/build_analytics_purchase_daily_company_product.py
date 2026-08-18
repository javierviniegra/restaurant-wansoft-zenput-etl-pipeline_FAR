"""
Build analytics_purchase_daily_company_product.

This script creates and refreshes the daily company-product purchase aggregate
for the unified MySQL analytical layer.

Main rules:
- Source table is analytics_purchase_order_lines.
- Grain is company_source_key + order_date_key + product_analytical_group_key + source_system.
- product_analytical_group_key = product_analytical_key when available, otherwise 0.
- Preserve all line activity, including excluded and review-required lines.
- Do not rejoin products by name.
- Reconcile back to analytics_purchase_order_lines.

This script does not implement BI logic.
"""

from __future__ import annotations

from typing import Any, Dict

from core.database.mysql import get_db_connection


TABLE_NAME = "analytics_purchase_daily_company_product"
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
        daily_company_product_key BIGINT AUTO_INCREMENT PRIMARY KEY,

        company_source_key VARCHAR(255) NOT NULL,
        company_analytical_key BIGINT NULL,
        order_date DATE NULL,
        order_date_key INT NOT NULL,
        product_analytical_key BIGINT NULL,
        product_analytical_group_key BIGINT NOT NULL,
        source_system VARCHAR(50) NOT NULL,

        product_identity_status VARCHAR(100) NULL,
        dim_product_mapping_status VARCHAR(100) NULL,
        is_product_mapped BOOLEAN NOT NULL DEFAULT FALSE,
        is_product_review_required BOOLEAN NOT NULL DEFAULT FALSE,
        include_product_in_business_views BOOLEAN NOT NULL DEFAULT TRUE,

        line_count BIGINT NOT NULL DEFAULT 0,
        business_line_count BIGINT NOT NULL DEFAULT 0,
        excluded_line_count BIGINT NOT NULL DEFAULT 0,
        review_required_line_count BIGINT NOT NULL DEFAULT 0,
        internal_vendor_line_count BIGINT NOT NULL DEFAULT 0,
        review_required_product_line_count BIGINT NOT NULL DEFAULT 0,
        orphan_product_line_count BIGINT NOT NULL DEFAULT 0,

        purchase_order_count BIGINT NOT NULL DEFAULT 0,
        vendor_count BIGINT NOT NULL DEFAULT 0,

        product_qty_total DECIMAL(18,4) NULL,
        qty_received_total DECIMAL(18,4) NULL,
        qty_invoiced_total DECIMAL(18,4) NULL,

        business_product_qty_total DECIMAL(18,4) NULL,
        business_qty_received_total DECIMAL(18,4) NULL,
        business_qty_invoiced_total DECIMAL(18,4) NULL,

        excluded_product_qty_total DECIMAL(18,4) NULL,
        excluded_qty_received_total DECIMAL(18,4) NULL,
        excluded_qty_invoiced_total DECIMAL(18,4) NULL,

        price_subtotal_total DECIMAL(18,4) NULL,
        price_total_total DECIMAL(18,4) NULL,
        business_price_subtotal_total DECIMAL(18,4) NULL,
        business_price_total_total DECIMAL(18,4) NULL,
        excluded_price_subtotal_total DECIMAL(18,4) NULL,
        excluded_price_total_total DECIMAL(18,4) NULL,

        include_in_business_views BOOLEAN NOT NULL DEFAULT TRUE,
        exclude_reason VARCHAR(500) NULL,
        aggregate_review_status VARCHAR(100) NULL,

        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

        UNIQUE KEY uq_purchase_daily_company_product (
            company_source_key,
            order_date_key,
            product_analytical_group_key,
            source_system
        ),

        KEY idx_purchase_daily_company_date (
            company_source_key,
            order_date_key
        ),

        KEY idx_purchase_daily_product (
            product_analytical_key
        ),

        KEY idx_purchase_daily_product_group (
            product_analytical_group_key
        ),

        KEY idx_purchase_daily_source_system (
            source_system
        ),

        KEY idx_purchase_daily_business_views (
            include_in_business_views
        ),

        KEY idx_purchase_daily_review_status (
            aggregate_review_status
        )
    )
    """

    cursor.execute(ddl)
    conn.commit()
    cursor.close()


def build_aggregate(conn: Any) -> None:
    if not table_exists(conn, SOURCE_TABLE):
        raise RuntimeError(f"Required source table does not exist: {SOURCE_TABLE}")

    sql = f"""
    INSERT INTO {TABLE_NAME} (
        company_source_key,
        company_analytical_key,
        order_date,
        order_date_key,
        product_analytical_key,
        product_analytical_group_key,
        source_system,
        product_identity_status,
        dim_product_mapping_status,
        is_product_mapped,
        is_product_review_required,
        include_product_in_business_views,
        line_count,
        business_line_count,
        excluded_line_count,
        review_required_line_count,
        internal_vendor_line_count,
        review_required_product_line_count,
        orphan_product_line_count,
        purchase_order_count,
        vendor_count,
        product_qty_total,
        qty_received_total,
        qty_invoiced_total,
        business_product_qty_total,
        business_qty_received_total,
        business_qty_invoiced_total,
        excluded_product_qty_total,
        excluded_qty_received_total,
        excluded_qty_invoiced_total,
        price_subtotal_total,
        price_total_total,
        business_price_subtotal_total,
        business_price_total_total,
        excluded_price_subtotal_total,
        excluded_price_total_total,
        include_in_business_views,
        exclude_reason,
        aggregate_review_status
    )
    SELECT
        grouped.company_source_key,
        grouped.company_analytical_key,
        grouped.order_date,
        grouped.order_date_key,
        grouped.product_analytical_key,
        grouped.product_analytical_group_key,
        grouped.source_system,
        grouped.product_identity_status,
        grouped.dim_product_mapping_status,
        grouped.is_product_mapped,
        grouped.is_product_review_required,
        grouped.include_product_in_business_views,
        grouped.line_count,
        grouped.business_line_count,
        grouped.excluded_line_count,
        grouped.review_required_line_count,
        grouped.internal_vendor_line_count,
        grouped.review_required_product_line_count,
        grouped.orphan_product_line_count,
        grouped.purchase_order_count,
        grouped.vendor_count,
        grouped.product_qty_total,
        grouped.qty_received_total,
        grouped.qty_invoiced_total,
        grouped.business_product_qty_total,
        grouped.business_qty_received_total,
        grouped.business_qty_invoiced_total,
        grouped.excluded_product_qty_total,
        grouped.excluded_qty_received_total,
        grouped.excluded_qty_invoiced_total,
        grouped.price_subtotal_total,
        grouped.price_total_total,
        grouped.business_price_subtotal_total,
        grouped.business_price_total_total,
        grouped.excluded_price_subtotal_total,
        grouped.excluded_price_total_total,
        CASE
            WHEN grouped.business_line_count > 0
             AND grouped.include_product_in_business_views = TRUE
            THEN TRUE
            ELSE FALSE
        END AS include_in_business_views,
        NULLIF(
            CONCAT_WS(
                ' | ',
                CASE WHEN grouped.business_line_count = 0 THEN 'no_business_lines' END,
                CASE WHEN grouped.orphan_product_line_count > 0 THEN 'orphan_product' END,
                CASE WHEN grouped.review_required_product_line_count > 0 THEN 'review_required_product' END,
                CASE WHEN grouped.include_product_in_business_views = FALSE THEN 'product_excluded' END
            ),
            ''
        ) AS exclude_reason,
        CASE
            WHEN grouped.orphan_product_line_count > 0 THEN 'orphan_product'
            WHEN grouped.review_required_line_count > 0 THEN 'has_review_required_lines'
            WHEN grouped.business_line_count = 0 THEN 'no_business_lines'
            ELSE 'ok'
        END AS aggregate_review_status
    FROM (
        SELECT
            company_source_key,
            MAX(company_analytical_key) AS company_analytical_key,
            DATE(order_date) AS order_date,
            order_date_key,
            product_analytical_key,
            COALESCE(product_analytical_key, 0) AS product_analytical_group_key,
            source_system,
            product_identity_status,
            dim_product_mapping_status,
            MAX(is_product_mapped) AS is_product_mapped,
            MAX(is_product_review_required) AS is_product_review_required,
            MAX(include_product_in_business_views) AS include_product_in_business_views,

            COUNT(1) AS line_count,

            SUM(
                CASE
                    WHEN include_in_business_views = TRUE THEN 1
                    ELSE 0
                END
            ) AS business_line_count,

            SUM(
                CASE
                    WHEN include_in_business_views = FALSE THEN 1
                    ELSE 0
                END
            ) AS excluded_line_count,

            SUM(
                CASE
                    WHEN line_review_status = 'review_required' THEN 1
                    ELSE 0
                END
            ) AS review_required_line_count,

            SUM(
                CASE
                    WHEN is_internal_vendor = TRUE THEN 1
                    ELSE 0
                END
            ) AS internal_vendor_line_count,

            SUM(
                CASE
                    WHEN is_product_review_required = TRUE THEN 1
                    ELSE 0
                END
            ) AS review_required_product_line_count,

            SUM(
                CASE
                    WHEN product_analytical_key IS NULL THEN 1
                    ELSE 0
                END
            ) AS orphan_product_line_count,

            COUNT(
                DISTINCT CONCAT(
                    source_system,
                    '|',
                    COALESCE(
                        source_order_id,
                        CONCAT('__missing__:', canonical_purchase_order_line_id)
                    )
                )
            ) AS purchase_order_count,

            COUNT(DISTINCT vendor_analytical_key) AS vendor_count,

            COALESCE(SUM(product_qty), 0) AS product_qty_total,
            COALESCE(SUM(qty_received), 0) AS qty_received_total,
            COALESCE(SUM(qty_invoiced), 0) AS qty_invoiced_total,

            COALESCE(
                SUM(
                    CASE
                        WHEN include_in_business_views = TRUE THEN product_qty
                        ELSE 0
                    END
                ),
                0
            ) AS business_product_qty_total,

            COALESCE(
                SUM(
                    CASE
                        WHEN include_in_business_views = TRUE THEN qty_received
                        ELSE 0
                    END
                ),
                0
            ) AS business_qty_received_total,

            COALESCE(
                SUM(
                    CASE
                        WHEN include_in_business_views = TRUE THEN qty_invoiced
                        ELSE 0
                    END
                ),
                0
            ) AS business_qty_invoiced_total,

            COALESCE(
                SUM(
                    CASE
                        WHEN include_in_business_views = FALSE THEN product_qty
                        ELSE 0
                    END
                ),
                0
            ) AS excluded_product_qty_total,

            COALESCE(
                SUM(
                    CASE
                        WHEN include_in_business_views = FALSE THEN qty_received
                        ELSE 0
                    END
                ),
                0
            ) AS excluded_qty_received_total,

            COALESCE(
                SUM(
                    CASE
                        WHEN include_in_business_views = FALSE THEN qty_invoiced
                        ELSE 0
                    END
                ),
                0
            ) AS excluded_qty_invoiced_total,

            COALESCE(SUM(price_subtotal), 0) AS price_subtotal_total,
            COALESCE(SUM(price_total), 0) AS price_total_total,

            COALESCE(
                SUM(
                    CASE
                        WHEN include_in_business_views = TRUE THEN price_subtotal
                        ELSE 0
                    END
                ),
                0
            ) AS business_price_subtotal_total,

            COALESCE(
                SUM(
                    CASE
                        WHEN include_in_business_views = TRUE THEN price_total
                        ELSE 0
                    END
                ),
                0
            ) AS business_price_total_total,

            COALESCE(
                SUM(
                    CASE
                        WHEN include_in_business_views = FALSE THEN price_subtotal
                        ELSE 0
                    END
                ),
                0
            ) AS excluded_price_subtotal_total,

            COALESCE(
                SUM(
                    CASE
                        WHEN include_in_business_views = FALSE THEN price_total
                        ELSE 0
                    END
                ),
                0
            ) AS excluded_price_total_total

        FROM {SOURCE_TABLE}
        GROUP BY
            company_source_key,
            order_date_key,
            DATE(order_date),
            product_analytical_key,
            COALESCE(product_analytical_key, 0),
            source_system,
            product_identity_status,
            dim_product_mapping_status
    ) grouped
    """

    cursor = conn.cursor()
    cursor.execute(sql)
    conn.commit()
    cursor.close()


def get_summary(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            COUNT(1) AS total_rows,
            SUM(CASE WHEN include_in_business_views = TRUE THEN 1 ELSE 0 END) AS business_rows,
            SUM(CASE WHEN include_in_business_views = FALSE THEN 1 ELSE 0 END) AS excluded_rows,
            COALESCE(SUM(line_count), 0) AS total_line_count,
            COALESCE(SUM(business_line_count), 0) AS total_business_line_count,
            COALESCE(SUM(excluded_line_count), 0) AS total_excluded_line_count,
            COALESCE(SUM(review_required_line_count), 0) AS total_review_required_line_count,
            COALESCE(SUM(internal_vendor_line_count), 0) AS total_internal_vendor_line_count,
            COALESCE(SUM(review_required_product_line_count), 0) AS total_review_required_product_line_count,
            COALESCE(SUM(orphan_product_line_count), 0) AS total_orphan_product_line_count,
            COALESCE(SUM(price_total_total), 0) AS total_price_total,
            COALESCE(SUM(business_price_total_total), 0) AS total_business_price_total,
            COALESCE(SUM(excluded_price_total_total), 0) AS total_excluded_price_total
        FROM {TABLE_NAME}
    """
    return fetch_one_dict(conn, query)


def print_summary(summary: Dict[str, Any]) -> None:
    print("=====================================================")
    print("ANALYTICS PURCHASE DAILY COMPANY PRODUCT BUILD SUMMARY")
    print("=====================================================")
    print(f"table: {TABLE_NAME}")
    print(f"total_rows_prepared: {summary.get('total_rows')}")
    print(f"include_in_business_views: {summary.get('business_rows')}")
    print(f"excluded_from_business_views: {summary.get('excluded_rows')}")
    print(f"total_line_count: {summary.get('total_line_count')}")
    print(f"total_business_line_count: {summary.get('total_business_line_count')}")
    print(f"total_excluded_line_count: {summary.get('total_excluded_line_count')}")
    print(f"total_review_required_line_count: {summary.get('total_review_required_line_count')}")
    print(f"total_internal_vendor_line_count: {summary.get('total_internal_vendor_line_count')}")
    print(f"total_review_required_product_line_count: {summary.get('total_review_required_product_line_count')}")
    print(f"total_orphan_product_line_count: {summary.get('total_orphan_product_line_count')}")
    print(f"total_price_total: {summary.get('total_price_total')}")
    print(f"total_business_price_total: {summary.get('total_business_price_total')}")
    print(f"total_excluded_price_total: {summary.get('total_excluded_price_total')}")
    print("=====================================================")


def main() -> int:
    print("=====================================================")
    print("ANALYTICS PURCHASE DAILY COMPANY PRODUCT BUILD START")
    print("=====================================================")

    conn = get_db_connection()

    try:
        apply_session_settings(conn)
        recreate_table(conn)
        build_aggregate(conn)
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