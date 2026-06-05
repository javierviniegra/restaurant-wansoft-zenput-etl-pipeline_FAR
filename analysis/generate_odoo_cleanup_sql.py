from analysis.odoo_no_code_classifier import classify_odoo_no_code


def generate_cleanup_sql():

    df = classify_odoo_no_code()

    # Solo los que NO deben ser venta
    df_clean = df[df["classification"].isin([
        "inventory_purchase",
        "utensilio_equipo",
        "botiquin",
        "mantenimiento"
    ])].copy()

    if df_clean.empty:
        print("No hay productos a limpiar")
        return

    file_path = "odoo_cleanup_sale_ok.sql"

    with open(file_path, "w", encoding="utf-8") as f:

        f.write("-- SCRIPT LIMPIEZA ODOO SALE_OK\n\n")

        for _, row in df_clean.iterrows():

            product_name = row["product_name"].replace("'", "''")

            sql = f"""
-- {row['classification']}
UPDATE product_product
SET sale_ok = FALSE
WHERE name = '{product_name}';
"""

            f.write(sql)

    print(f"Archivo generado: {file_path}")
    print(f"Productos a limpiar: {len(df_clean)}")


if __name__ == "__main__":
    generate_cleanup_sql()