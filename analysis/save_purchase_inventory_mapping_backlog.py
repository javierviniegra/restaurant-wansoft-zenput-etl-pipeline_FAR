import pandas as pd

from core.database.mysql import get_mysql_connection as get_db_connection
from analysis.build_purchase_inventory_mapping_backlog import (
    build_purchase_inventory_mapping_backlog
)


def sql_safe(value):
    """
    Normaliza valores antes de insertar en MySQL.
    """
    if pd.isna(value):
        return None

    if value is False:
        return None

    if isinstance(value, str):
        value = value.strip()
        return value if value else None

    return value


def save_purchase_inventory_mapping_backlog():
    """
    Guarda el backlog deduplicado de inventory candidates de compras.

    Importante:
    - Trunca la tabla porque es un snapshot derivado del ETL actual.
    - No modifica inventory_mapping_dictionary.
    - No promueve mappings automáticamente.
    """

    df = build_purchase_inventory_mapping_backlog()

    if df is None or df.empty:
        print("No hay backlog de inventory mapping de compras para guardar.")
        return 0

    conn = get_db_connection(target="wansoft")
    cursor = conn.cursor()

    cursor.execute("TRUNCATE TABLE odoo_purchase_inventory_mapping_backlog")

    insert_sql = """
    INSERT INTO odoo_purchase_inventory_mapping_backlog (
        product_id,
        product_name,
        purchase_product_scope,
        purchase_mapping_bucket,
        total_lines,
        unique_vendors,
        unique_companies,
        total_qty,
        total_received,
        total_amount,
        first_order_date,
        last_order_date,
        suggested_action,
        backlog_status
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    rows = []

    for _, row in df.iterrows():
        rows.append((
            sql_safe(row.get("product_id")),
            sql_safe(row.get("product_name")),
            sql_safe(row.get("purchase_product_scope")),
            sql_safe(row.get("purchase_mapping_bucket")),
            sql_safe(row.get("total_lines")),
            sql_safe(row.get("unique_vendors")),
            sql_safe(row.get("unique_companies")),
            sql_safe(row.get("total_qty")),
            sql_safe(row.get("total_received")),
            sql_safe(row.get("total_amount")),
            sql_safe(row.get("first_order_date")),
            sql_safe(row.get("last_order_date")),
            sql_safe(row.get("suggested_action")),
            sql_safe(row.get("backlog_status")),
        ))

    cursor.executemany(insert_sql, rows)
    conn.commit()

    inserted = len(rows)

    cursor.close()
    conn.close()

    print(f"Insertados {inserted} registros en odoo_purchase_inventory_mapping_backlog.")

    return inserted