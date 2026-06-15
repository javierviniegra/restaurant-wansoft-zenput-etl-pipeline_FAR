from analysis.wansoft_inventory_lifecycle_candidates import (
    build_wansoft_inventory_lifecycle_candidates,
    summarize_wansoft_inventory_lifecycle
)


if __name__ == "__main__":

    print("==== TEST WANSOFT INVENTORY LIFECYCLE ====\n")

    df = build_wansoft_inventory_lifecycle_candidates()

    print("\n--- SUMMARY ---")
    print(summarize_wansoft_inventory_lifecycle(df).to_string(index=False))

    print("\n--- SAMPLE HISTORICAL CANDIDATES ---")
    historical = df[df["lifecycle_candidate"] == "historical_candidate"]
    print(historical[[
        "CodigoProducto",
        "Producto",
        "Departamento",
        "current_stock_qty",
        "last_purchase_date",
        "days_since_last_purchase",
        "lifecycle_candidate"
    ]].head(30).to_string(index=False))

    print("\n--- SAMPLE HISTORICAL WITH STOCK REVIEW ---")
    history_stock = df[df["lifecycle_candidate"] == "historical_with_stock_review"]
    print(history_stock[[
        "CodigoProducto",
        "Producto",
        "Departamento",
        "current_stock_qty",
        "last_purchase_date",
        "days_since_last_purchase",
        "lifecycle_candidate"
    ]].head(30).to_string(index=False))

    print("\n==== DONE ✅ ====")