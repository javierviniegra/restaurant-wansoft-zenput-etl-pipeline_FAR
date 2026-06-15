import pandas as pd
from core.database.mysql import get_mysql_connection as get_db_connection
from analysis.build_inventory_bridge_report import build_inventory_bridge_report


def sql_safe(value):
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip()
        return value if value else None
    return value


def save_inventory_bridge_report():
    df = build_inventory_bridge_report(threshold=92)

    if df is None or df.empty:
        print("No hay bridge report para guardar.")
        return

    conn = get_db_connection(target="wansoft")
    cursor = conn.cursor()

    cursor.execute("TRUNCATE TABLE inventory_bridge_report")

    insert_sql = """
    INSERT INTO inventory_bridge_report (
        odoo_product_name,
        odoo_category_name,
        raw_classification,
        wansoft_code,
        wansoft_product_name,
        wansoft_department,
        wansoft_lifecycle_candidate,
        similarity_score,
        suggested_action
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    rows = []
    for _, row in df.iterrows():
        rows.append((
            sql_safe(row.get("odoo_product_name")),
            sql_safe(row.get("odoo_category_name")),
            sql_safe(row.get("raw_classification")),
            sql_safe(row.get("wansoft_code")),
            sql_safe(row.get("wansoft_product_name")),
            sql_safe(row.get("wansoft_department")),
            sql_safe(row.get("wansoft_lifecycle_candidate")),
            sql_safe(row.get("similarity_score")),
            sql_safe(row.get("suggested_action")),
        ))

    cursor.executemany(insert_sql, rows)
    conn.commit()

    print(f"Insertados {len(rows)} registros en inventory_bridge_report.")

    cursor.close()
    conn.close()