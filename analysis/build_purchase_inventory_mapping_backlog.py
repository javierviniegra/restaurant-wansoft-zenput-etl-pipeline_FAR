import pandas as pd

from core.database.mysql import get_mysql_connection as get_db_connection


def build_purchase_inventory_mapping_backlog():
    """
    Construye backlog deduplicado de productos de compras que:
    - son líneas reales de producto
    - no están mapeados al inventory_mapping_dictionary
    - fueron clasificados como inventory_candidate

    Este backlog sirve para decidir qué productos deben revisarse
    para posible alta/mapeo en inventory_mapping_dictionary.
    """

    conn = get_db_connection(target="wansoft")

    query = """
    SELECT
        product_id,
        MAX(product_name) AS product_name,
        MAX(purchase_product_scope) AS purchase_product_scope,
        MAX(purchase_mapping_bucket) AS purchase_mapping_bucket,
        COUNT(*) AS total_lines,
        COUNT(DISTINCT vendor_name) AS unique_vendors,
        COUNT(DISTINCT company_name) AS unique_companies,
        SUM(COALESCE(product_qty, 0)) AS total_qty,
        SUM(COALESCE(qty_received, 0)) AS total_received,
        SUM(COALESCE(price_total, 0)) AS total_amount,
        MIN(order_date) AS first_order_date,
        MAX(order_date) AS last_order_date,
        'review_for_inventory_mapping' AS suggested_action,
        'open' AS backlog_status
    FROM odoo_purchase_order_line_snapshot
    WHERE purchase_line_type = 'product_line'
      AND purchase_mapping_bucket = 'unmapped_inventory_candidate'
      AND product_id IS NOT NULL
    GROUP BY product_id
    ORDER BY total_amount DESC
    """

    df = pd.read_sql(query, conn)
    conn.close()

    return df


def summarize_purchase_inventory_mapping_backlog(df: pd.DataFrame) -> pd.DataFrame:
    """
    Resume el backlog por suggested_action y backlog_status.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=[
            "suggested_action",
            "backlog_status",
            "unique_products",
            "total_lines",
            "total_amount"
        ])

    summary = (
        df.groupby(["suggested_action", "backlog_status"], dropna=False)
        .agg(
            unique_products=("product_id", "nunique"),
            total_lines=("total_lines", "sum"),
            total_amount=("total_amount", "sum")
        )
        .reset_index()
        .sort_values(["total_amount"], ascending=False)
    )

    return summary