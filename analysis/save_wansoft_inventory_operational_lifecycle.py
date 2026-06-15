import pandas as pd
from core.database.mysql import get_mysql_connection as get_db_connection
from analysis.wansoft_inventory_operational_lifecycle import build_wansoft_inventory_operational_lifecycle


def sql_safe(value):
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip()
        return value if value else None
    return value


def save_wansoft_inventory_operational_lifecycle():
    df = build_wansoft_inventory_operational_lifecycle()

    if df is None or df.empty:
        print("No hay lifecycle para guardar.")
        return

    # 🔥 Defensa extra: dejar 1 fila por CodigoProducto
    df = df.sort_values(
        by=["CodigoProducto", "current_stock_qty"],
        ascending=[True, False]
    ).drop_duplicates(subset=["CodigoProducto"], keep="first")

    conn = get_db_connection(target="wansoft")
    cursor = conn.cursor()

    cursor.execute("TRUNCATE TABLE inventory_product_lifecycle")

    insert_sql = """
    INSERT INTO inventory_product_lifecycle (
        CodigoProducto,
        Producto,
        Departamento,
        CodigoDepartamento,
        UnidadDeMedida,
        current_stock_qty,
        last_activity_date,
        days_since_last_activity,
        lifecycle_candidate,
        source_logic
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    rows = []
    for _, row in df.iterrows():
        rows.append((
            sql_safe(row.get("CodigoProducto")),
            sql_safe(row.get("Producto")),
            sql_safe(row.get("Departamento")),
            sql_safe(row.get("CodigoDepartamento")),
            sql_safe(row.get("UnidadDeMedida")),
            sql_safe(row.get("current_stock_qty")),
            sql_safe(row.get("last_activity_date")),
            sql_safe(row.get("days_since_last_activity")),
            sql_safe(row.get("lifecycle_candidate")),
            "operational_lifecycle"
        ))

    cursor.executemany(insert_sql, rows)
    conn.commit()

    print(f"Insertados {len(rows)} registros en inventory_product_lifecycle.")

    cursor.close()
    conn.close()
