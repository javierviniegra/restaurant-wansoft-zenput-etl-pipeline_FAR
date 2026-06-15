from analysis.inventory_raw_no_code_classifier import (
    classify_inventory_raw_no_code,
    summarize_inventory_raw_no_code
)


if __name__ == "__main__":

    print("==== TEST INVENTORY RAW NO CODE CLASSIFIER ====\n")

    df = classify_inventory_raw_no_code()

    print("\n--- SUMMARY ---")
    print(summarize_inventory_raw_no_code(df).to_string(index=False))

    print("\n--- SAMPLE ---")
    print(df[[
        "product_name",
        "category_name",
        "sale_ok",
        "purchase_ok",
        "raw_classification"
    ]].head(30).to_string(index=False))

    print("\n==== DONE ✅ ====")