from analysis.inventory_not_found_analyzer import (
    build_inventory_not_found_analysis,
    summarize_inventory_not_found,
    export_inventory_not_found_analysis
)


if __name__ == "__main__":
    print("==== TEST INVENTORY NOT_FOUND ANALYZER ====\n")

    df = build_inventory_not_found_analysis()
    stats = summarize_inventory_not_found(df)

    print("\n--- SUMMARY ---")
    print(stats["summary"].to_string(index=False))

    print("\n--- BY SCOPE ---")
    print(stats["by_scope"].to_string(index=False))

    print("\n--- TOP CATEGORIES ---")
    print(stats["by_category"].to_string(index=False))

    print("\n--- SAMPLE ---")
    print(stats["sample"].to_string(index=False))

    print("\n--- EXPORT ---")
    export_inventory_not_found_analysis(df)

    print("\n==== DONE ✅ ====")