from extract.products.odoo_products import extract_odoo_products


if __name__ == "__main__":

    print("==== TEST ODOO PRODUCTS ====")

    df = extract_odoo_products()

    df_sale = df[df["sale_ok"] == True]

    print("\n--- STATS GENERALES ---")
    print("Total productos:", len(df))
    print("Productos de venta:", len(df_sale))

    print("\n--- CÓDIGOS ---")
    print("Con default_code:", df_sale["default_code"].notna().sum())
    print("Con x_wansoft_code:", df_sale["x_wansoft_code"].notna().sum())
    print("Con integration_code:", df_sale["integration_code"].notna().sum())

    print("\n--- SAMPLE ---")
    print(df_sale[[
        "product_name",
        "default_code",
        "x_wansoft_code",
        "integration_code"
    ]].head(20))

    print("\n==== DONE ✅ ====")