from analysis.build_purchase_inventory_mapping_backlog import (
    build_purchase_inventory_mapping_backlog,
    summarize_purchase_inventory_mapping_backlog
)
from analysis.save_purchase_inventory_mapping_backlog import (
    save_purchase_inventory_mapping_backlog
)


if __name__ == "__main__":
    print("==== TEST PURCHASE INVENTORY MAPPING BACKLOG ====\n")

    df = build_purchase_inventory_mapping_backlog()

    print("\n--- BACKLOG SUMMARY ---")
    print(summarize_purchase_inventory_mapping_backlog(df).to_string(index=False))

    if not df.empty:
        print("\n--- BACKLOG SAMPLE ---")
        print(df.head(50).to_string(index=False))

    print("\n--- SAVE ---")
    inserted = save_purchase_inventory_mapping_backlog()
    print(f"rows_inserted: {inserted}")

    print("\n==== DONE ✅ ====")