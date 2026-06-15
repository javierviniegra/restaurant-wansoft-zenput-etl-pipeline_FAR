from analysis.build_inventory_not_found_p2_bridge import build_inventory_not_found_p2_bridge
from analysis.save_inventory_not_found_p2_bridge import save_inventory_not_found_p2_bridge


if __name__ == "__main__":
    print("==== TEST INVENTORY NOT_FOUND P2 BRIDGE ====\n")

    df = build_inventory_not_found_p2_bridge()

    if df.empty:
        print("No se generó bridge P2.")
    else:
        print("\n--- SUMMARY ---")
        summary = (
            df["suggested_action"]
            .value_counts()
            .reset_index()
        )
        summary.columns = ["suggested_action", "count"]
        print(summary.to_string(index=False))

        print("\n--- SAMPLE ---")
        print(df.head(40).to_string(index=False))

    print("\n--- SAVE ---")
    save_inventory_not_found_p2_bridge()

    print("\n==== DONE ✅ ====")
