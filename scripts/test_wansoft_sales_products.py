from extract.db.wansoft_sales_products_db import get_wansoft_sales_products_from_db


if __name__ == "__main__":

    print("==== TEST WANSOFT SALES PRODUCTS ====")

    df = get_wansoft_sales_products_from_db()

    print("\n--- SAMPLE ---")
    print(df.head(20))

    print("\n--- STATS ---")
    print("Total filas:", len(df))
    print("Productos únicos:", df["CodigoPlatillo"].nunique())

    print("\n==== DONE ✅ ====")