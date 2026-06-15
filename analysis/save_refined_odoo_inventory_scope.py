import pandas as pd
from core.database.mysql import get_mysql_connection as get_db_connection
from analysis.refine_odoo_inventory_scope import refine_odoo_inventory_scope


def sql_safe(value):
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip()
        return value if value else None
    return value


def save_refined_odoo_inventory_scope():
    df = refine_odoo_inventory_scope()

    if df is None or df.empty:
        print("No hay refinamiento de scope para guardar.")
        return

    conn = get_db_connection(target="wansoft")
    cursor = conn.cursor()

    update_sql = """
    UPDATE odoo_inventory_scope_classification
    SET
        refined_inventory_scope = %s,
        refined_scope_source = %s,
        refined_scope_status = %s
    WHERE id = %s
    """

    rows = []
    for _, row in df.iterrows():
        rows.append((
            sql_safe(row.get("refined_inventory_scope")),
            sql_safe(row.get("refined_scope_source")),
            sql_safe(row.get("refined_scope_status")),
            sql_safe(row.get("id"))
        ))

    cursor.executemany(update_sql, rows)
    conn.commit()

    print(f"Actualizados {len(rows)} registros en odoo_inventory_scope_classification.")

    cursor.close()
    conn.close()