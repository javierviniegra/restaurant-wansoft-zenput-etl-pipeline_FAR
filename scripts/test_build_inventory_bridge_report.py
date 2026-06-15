from analysis.build_inventory_bridge_report import (
    build_inventory_bridge_report,
    summarize_inventory_bridge_report
)


if __name__ == "__main__":
    print("==== TEST BUILD INVENTORY BRIDGE REPORT ====\n")

    df = build_inventory_bridge_report(threshold=92)

    if df.empty:
        print("No se encontraron coincidencias suficientes.")
    else:
        print("\n--- SUMMARY ---")
        print(summarize_inventory_bridge_report(df).to_string(index=False))

        print("\n--- SAMPLE ---")
        print(df.head(30).to_string(index=False))

    print("\n==== DONE ✅ ====")