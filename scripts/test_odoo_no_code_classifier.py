from analysis.odoo_no_code_classifier import classify_odoo_no_code, summarize


if __name__ == "__main__":

    print("==== TEST ODOO CLASSIFIER ====\n")

    df = classify_odoo_no_code()

    print("\n--- SUMMARY ---")
    print(summarize(df))

    print("\n--- SAMPLE ---")
    print(df[[
        "product_name",
        "category_name",
        "sale_ok",
        "purchase_ok",
        "classification"
    ]].head(20))

    print("\n==== DONE ✅ ====")
