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


def ensure_inventory_not_found_priority_backlog_table(conn):
    """
    Creates inventory_not_found_priority_backlog when it does not exist yet.
    Columns match exactly what this module inserts.
    """
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_not_found_priority_backlog (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,

                odoo_product_id VARCHAR(100) NULL,
                odoo_product_name VARCHAR(500) NULL,
                category_name VARCHAR(255) NULL,
                refined_inventory_scope VARCHAR(100) NULL,
                not_found_classification VARCHAR(100) NULL,
                row_count INT NULL,
                location_count INT NULL,
                total_abs_stock_qty DECIMAL(18,4) NULL,
                priority_bucket VARCHAR(100) NULL,
                priority_reason VARCHAR(500) NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """)
        conn.commit()
    finally:
        cursor.close()


def save_inventory_not_found_priority_backlog():
    """
    Guarda en MySQL el backlog priorizado de not_found.
    """
    df = build_inventory_not_found_priority_backlog()

    if df is None or df.empty:
        print("No hay backlog priorizado de not_found para guardar.")
        return

    conn = get_db_connection(target="wansoft")
    ensure_inventory_not_found_priority_backlog_table(conn)
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