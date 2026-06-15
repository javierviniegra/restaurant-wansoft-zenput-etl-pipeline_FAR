from extract.db.wansoft_inventory_products_db import get_wansoft_inventory_products_from_db


if __name__ == "__main__":

    print("==== WANSOFT INVENTORY PRODUCTS TEST ====\n")

    df = get_wansoft_inventory_products_from_db()

    print(f"Total filas: {len(df)}")
    print(f"Productos únicos Wansoft inventory: {df['CodigoProducto'].nunique()}")

    print("\n--- SAMPLE ---")
    print(df.head(20).to_string(index=False))

    print("\n==== DONE ✅ ====")