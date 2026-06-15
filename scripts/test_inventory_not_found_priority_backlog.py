from analysis.build_inventory_not_found_priority_backlog import (
    build_inventory_not_found_priority_backlog
)
from analysis.save_inventory_not_found_priority_backlog import (
    save_inventory_not_found_priority_backlog
)


if __name__ == "__main__":
    print("==== TEST INVENTORY NOT_FOUND PRIORITY BACKLOG ====\n")

    df = build_inventory_not_found_priority_backlog()

    if df.empty:
        print("No se generó backlog.")
    else:
        print("\n--- SUMMARY ---")
        summary = (
            df["priority_bucket"]
            .value_counts()
            .reset_index()
        )
        summary.columns = ["priority_bucket", "count"]
        print(summary.to_string(index=False))

        print("\n--- SAMPLE ---")
        print(df.head(40).to_string(index=False))

    print("\n--- SAVE ---")
    save_inventory_not_found_priority_backlog()

    print("\n==== DONE ✅ ====")