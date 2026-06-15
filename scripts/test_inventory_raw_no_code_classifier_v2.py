from analysis.inventory_raw_no_code_classifier_v2 import (
    classify_inventory_raw_no_code_v2,
    summarize_inventory_raw_no_code_v2
)


if __name__ == "__main__":

    print("==== TEST INVENTORY RAW NO CODE CLASSIFIER V2 ====\n")

    df = classify_inventory_raw_no_code_v2()

    print("\n--- SUMMARY ---")
    print(summarize_inventory_raw_no_code_v2(df).to_string(index=False))

    print("\n--- SAMPLE ---")
    print(df[[
        "product_name",
        "category_name",
        "sale_ok",
        "purchase_ok",
        "raw_classification"
    ]].head(30).to_string(index=False))

    print("\n==== DONE ✅ ====")