from extract.products.odoo_products import extract_odoo_products
from analysis.odoo_no_code_classifier import classify_odoo_no_code


if __name__ == "__main__":

    print("==== ODOO SALE_OK IMPACT TEST ====\n")

    df = extract_odoo_products()

    total_products = len(df)
    sale_products = df[df["sale_ok"] == True]

    print(f"Total productos Odoo: {total_products}")
    print(f"Productos con sale_ok = True (actual): {len(sale_products)}")

    # Clasificación de no_code
    df_no_code = classify_odoo_no_code()

    # Los que vamos a quitar
    df_to_remove = df_no_code[df_no_code["classification"].isin([
        "inventory_purchase",
        "utensilio_equipo",
        "botiquin",
        "mantenimiento"
    ])]

    print("\n--- LIMPIEZA PROPUESTA ---")
    print(f"Productos a quitar de venta: {len(df_to_remove)}")

    # Simulación AFTER
    final_sale = len(sale_products) - len(df_to_remove)

    print("\n--- RESULTADO FINAL ESTIMADO ---")
    print(f"Productos de venta después de limpieza: {final_sale}")

    print("\n==== DONE ✅ ====")