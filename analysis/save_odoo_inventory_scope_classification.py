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


def save_odoo_inventory_scope_classification():
    df = classify_odoo_inventory_scope()

    if df is None or df.empty:
        print("No hay clasificación de inventory scope para guardar.")
        return

    conn = get_db_connection(target="wansoft")
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