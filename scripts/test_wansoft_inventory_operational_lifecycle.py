from analysis.wansoft_inventory_operational_lifecycle import (
    build_wansoft_inventory_operational_lifecycle,
    summarize_wansoft_inventory_operational_lifecycle
)


if __name__ == "__main__":
    print("==== TEST WANSOFT INVENTORY OPERATIONAL LIFECYCLE ====\n")

    df = build_wansoft_inventory_operational_lifecycle()

    print("\n--- SUMMARY ---")
    print(summarize_wansoft_inventory_operational_lifecycle(df).to_string(index=False))

    print("\n--- SAMPLE HISTORICAL CANDIDATES ---")
    historical = df[df["lifecycle_candidate"] == "historical_candidate"]
    print(historical[[
        "CodigoProducto",
        "Producto",
        "Departamento",
        "current_stock_qty",
        "last_activity_date",
        "days_since_last_activity",
        "lifecycle_candidate"
    ]].head(30).to_string(index=False))

    print("\n--- SAMPLE NEVER OPERATED ---")
    never_ops = df[df["lifecycle_candidate"] == "never_operated"]
    print(never_ops[[
        "CodigoProducto",
        "Producto",
        "Departamento",
        "current_stock_qty",
        "last_activity_date",
        "lifecycle_candidate"
    ]].head(30).to_string(index=False))

    print("\n==== DONE ✅ ====")