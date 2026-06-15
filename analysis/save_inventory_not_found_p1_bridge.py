import pandas as pd
from core.database.mysql import get_mysql_connection as get_db_connection
from analysis.build_inventory_not_found_p1_bridge import build_inventory_not_found_p1_bridge


def sql_safe(value):
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip()
        return value if value else None
    return value


def save_inventory_not_found_p1_bridge():
    df = build_inventory_not_found_p1_bridge()

    if df is None or df.empty:
        print("No hay bridge de P1 para guardar.")
        return

    conn = get_db_connection(target="wansoft")
    cursor = conn.cursor()

    cursor.execute("TRUNCATE TABLE inventory_not_found_p1_bridge")

    insert_sql = """
    INSERT INTO inventory_not_found_p1_bridge (
        odoo_product_id,
        odoo_product_name,
        category_name,
        wansoft_code,
        wansoft_product_name,
        wansoft_department,
        lifecycle_candidate,
        similarity_score,
        suggested_action
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    rows = []
    for _, row in df.iterrows():
        rows.append((
            sql_safe(row.get("odoo_product_id")),
            sql_safe(row.get("odoo_product_name")),
            sql_safe(row.get("category_name")),
            sql_safe(row.get("wansoft_code")),
            sql_safe(row.get("wansoft_product_name")),
            sql_safe(row.get("wansoft_department")),
            sql_safe(row.get("lifecycle_candidate")),
            sql_safe(row.get("similarity_score")),
            sql_safe(row.get("suggested_action")),
        ))

    cursor.executemany(insert_sql, rows)
    conn.commit()

    print(f"Insertados {len(rows)} registros en inventory_not_found_p1_bridge.")

    cursor.close()
    conn.close()
