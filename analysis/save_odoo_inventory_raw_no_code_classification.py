import pandas as pd
from core.database.mysql import get_mysql_connection as get_db_connection
from analysis.inventory_raw_no_code_classifier_v2 import classify_inventory_raw_no_code_v2


def sql_safe(value):
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip()
        return value if value else None
    if isinstance(value, bool):
        return int(value)
    return value


def save_odoo_inventory_raw_no_code_classification():
    df = classify_inventory_raw_no_code_v2()

    if df is None or df.empty:
        print("No hay clasificación de inventory raw no code para guardar.")
        return

    conn = get_db_connection(target="wansoft")
    cursor = conn.cursor()

    cursor.execute("TRUNCATE TABLE odoo_inventory_raw_no_code_classification")

    insert_sql = """
    INSERT INTO odoo_inventory_raw_no_code_classification (
        product_name,
        category_name,
        sale_ok,
        purchase_ok,
        raw_classification
    )
    VALUES (%s, %s, %s, %s, %s)
    """

    rows = []
    for _, row in df.iterrows():
        rows.append((
            sql_safe(row.get("product_name")),
            sql_safe(row.get("category_name")),
            sql_safe(row.get("sale_ok")),
            sql_safe(row.get("purchase_ok")),
            sql_safe(row.get("raw_classification")),
        ))

    cursor.executemany(insert_sql, rows)
    conn.commit()

    print(f"Insertados {len(rows)} registros en odoo_inventory_raw_no_code_classification.")

    cursor.close()
    conn.close()
