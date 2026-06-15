from extract.products.odoo_products import extract_odoo_products
from analysis.build_sales_product_mapping import build_sales_product_mapping


def classify_inventory_bucket(row, sales_codes):
    """
    Clasifica productos Odoo dentro del universo inventory.
    """

    default_code = row.get("default_code")
    sale_ok = bool(row.get("sale_ok"))
    purchase_ok = bool(row.get("purchase_ok"))

    # si no es comprable, no entra a inventory
    if not purchase_ok:
        return "not_inventory"

    # tiene código de ventas homologado y además se compra:
    # probable producto terminado inventariable
    if default_code in sales_codes and sale_ok and purchase_ok:
        return "inventory_finished_goods"

    # se compra pero no está homologado en ventas
    if purchase_ok and not sale_ok:
        return "inventory_raw_materials"

    # se compra, se vende, pero no está homologado aún
    if purchase_ok and sale_ok and default_code not in sales_codes:
        return "inventory_mixed_review"

    return "inventory_review"


if __name__ == "__main__":

    print("==== INVENTORY UNIVERSE CLASSIFICATION TEST ====\n")

    df = extract_odoo_products()

    # mapping de ventas ya homologado
    df_sales_mapping = build_sales_product_mapping(threshold=95)

    sales_codes = set(
        df_sales_mapping["odoo_code"].dropna().astype(str).str.strip().tolist()
    )

    # limpiar default_code
    df["default_code"] = df["default_code"].apply(
        lambda x: None if x in [None, False, "", "False"] else str(x).strip()
    )

    # clasificar
    df["inventory_bucket"] = df.apply(
        lambda row: classify_inventory_bucket(row, sales_codes),
        axis=1
    )

    # universo inventory real
    df_inventory = df[df["inventory_bucket"] != "not_inventory"].copy()

    print(f"Total productos Odoo: {len(df)}")
    print(f"Productos con purchase_ok=True (universo inventory ampliado): {len(df_inventory)}")

    print("\n--- RESUMEN POR BUCKET ---")
    summary = df_inventory["inventory_bucket"].value_counts().reset_index()
    summary.columns = ["inventory_bucket", "count"]
    summary["pct"] = (summary["count"] / len(df_inventory) * 100).round(2)
    print(summary.to_string(index=False))

    print("\n--- SAMPLE FINISHED GOODS ---")
    fg = df_inventory[df_inventory["inventory_bucket"] == "inventory_finished_goods"]
    print(fg[[
        "product_name",
        "default_code",
        "sale_ok",
        "purchase_ok",
        "category_name",
        "inventory_bucket"
    ]].head(20).to_string(index=False))

    print("\n--- SAMPLE RAW MATERIALS ---")
    rm = df_inventory[df_inventory["inventory_bucket"] == "inventory_raw_materials"]
    print(rm[[
        "product_name",
        "default_code",
        "sale_ok",
        "purchase_ok",
        "category_name",
        "inventory_bucket"
    ]].head(20).to_string(index=False))

    print("\n--- SAMPLE MIXED REVIEW ---")
    mixed = df_inventory[df_inventory["inventory_bucket"] == "inventory_mixed_review"]
    print(mixed[[
        "product_name",
        "default_code",
        "sale_ok",
        "purchase_ok",
        "category_name",
        "inventory_bucket"
    ]].head(20).to_string(index=False))

    print("\n==== DONE ✅ ====")