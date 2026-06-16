import pandas as pd
from core.database.mysql import get_mysql_connection as get_db_connection
from analysis.review_scope_refiner_v2 import build_review_scope_refinement_v2


def sql_safe(value):
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip()
        return value if value else None
    return value


def save_review_scope_refinement_v2():
    df = build_review_scope_refinement_v2()

    if df is None or df.empty:
        print("No hay registros de review_scope para refinar en v2.")
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
            sql_safe(row.get("refined_inventory_scope_v2")),
            sql_safe(row.get("refined_scope_source_v2")),
            sql_safe(row.get("refined_scope_status_v2")),
            sql_safe(row.get("id"))
        ))

    cursor.executemany(update_sql, rows)
    conn.commit()

    print(f"Actualizados {len(rows)} registros de review_scope en odoo_inventory_scope_classification (v2).")

    cursor.close()
    conn.close()