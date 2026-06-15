import pandas as pd
from core.database.mysql import get_mysql_connection as get_db_connection
from analysis.build_inventory_not_found_priority_backlog import (
    build_inventory_not_found_priority_backlog
)


def sql_safe(value):
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip()
        return value if value else None
    return value


def save_inventory_not_found_priority_backlog():
    """
    Guarda en MySQL el backlog priorizado de not_found.
    """
    df = build_inventory_not_found_priority_backlog()

    if df is None or df.empty:
        print("No hay backlog priorizado de not_found para guardar.")
        return

    conn = get_db_connection(target="wansoft")
    cursor = conn.cursor()

    cursor.execute("TRUNCATE TABLE inventory_not_found_priority_backlog")

    insert_sql = """
    INSERT INTO inventory_not_found_priority_backlog (
        odoo_product_id,
        odoo_product_name,
        category_name,
        refined_inventory_scope,
        not_found_classification,
        row_count,
        location_count,
        total_abs_stock_qty,
        priority_bucket,
        priority_reason
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    rows = []
    for _, row in df.iterrows():
        rows.append((
            sql_safe(row.get("odoo_product_id")),
            sql_safe(row.get("odoo_product_name")),
            sql_safe(row.get("category_name")),
            sql_safe(row.get("refined_inventory_scope")),
            sql_safe(row.get("not_found_classification")),
            sql_safe(row.get("row_count")),
            sql_safe(row.get("location_count")),
            sql_safe(row.get("total_abs_stock_qty")),
            sql_safe(row.get("priority_bucket")),
            sql_safe(row.get("priority_reason")),
        ))

    cursor.executemany(insert_sql, rows)
    conn.commit()

    print(f"Insertados {len(rows)} registros en inventory_not_found_priority_backlog.")

    cursor.close()
    conn.close()