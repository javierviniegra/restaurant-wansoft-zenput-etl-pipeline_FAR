import pandas as pd
from core.database.mysql import get_mysql_connection as get_db_connection
from analysis.odoo_inventory_scope_classifier import classify_odoo_inventory_scope


def sql_safe(value):
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip()
        return value if value else None
    if isinstance(value, bool):
        return int(value)
    return value


def ensure_odoo_inventory_scope_classification_table(conn):
    """
    Creates odoo_inventory_scope_classification when it does not exist yet.

    Columns match exactly what this module inserts plus the refined_*
    columns updated later by analysis/save_refined_odoo_inventory_scope.py.
    id is a plain AUTO_INCREMENT column because the refinement UPDATE
    targets it directly by name.
    """
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS odoo_inventory_scope_classification (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,

                odoo_product_id VARCHAR(100) NULL,
                product_name VARCHAR(500) NULL,
                category_name VARCHAR(255) NULL,
                company_id_only VARCHAR(100) NULL,
                company_name VARCHAR(500) NULL,
                sale_ok VARCHAR(10) NULL,
                purchase_ok VARCHAR(10) NULL,
                inventory_scope VARCHAR(100) NULL,
                scope_source VARCHAR(100) NULL,
                scope_status VARCHAR(100) NULL,
                notes TEXT NULL,

                refined_inventory_scope VARCHAR(100) NULL,
                refined_scope_source VARCHAR(100) NULL,
                refined_scope_status VARCHAR(100) NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """)
        conn.commit()
    finally:
        cursor.close()


def save_odoo_inventory_scope_classification():
    df = classify_odoo_inventory_scope()

    if df is None or df.empty:
        print("No hay clasificación de inventory scope para guardar.")
        return

    conn = get_db_connection(target="wansoft")
    ensure_odoo_inventory_scope_classification_table(conn)
    cursor = conn.cursor()

    cursor.execute("TRUNCATE TABLE odoo_inventory_scope_classification")

    insert_sql = """
    INSERT INTO odoo_inventory_scope_classification (
        odoo_product_id,
        product_name,
        category_name,
        company_id_only,
        company_name,
        sale_ok,
        purchase_ok,
        inventory_scope,
        scope_source,
        scope_status,
        notes
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    rows = []
    for _, row in df.iterrows():
        rows.append((
            sql_safe(row.get("odoo_product_id")),
            sql_safe(row.get("product_name")),
            sql_safe(row.get("category_name")),
            sql_safe(row.get("company_id_only")),
            sql_safe(row.get("company_name")),
            sql_safe(row.get("sale_ok")),
            sql_safe(row.get("purchase_ok")),
            sql_safe(row.get("inventory_scope")),
            sql_safe(row.get("scope_source")),
            sql_safe(row.get("scope_status")),
            sql_safe(row.get("notes"))
        ))

    cursor.executemany(insert_sql, rows)
    conn.commit()

    print(f"Insertados {len(rows)} registros en odoo_inventory_scope_classification.")

    cursor.close()
    conn.close()