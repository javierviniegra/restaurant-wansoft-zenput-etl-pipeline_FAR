from analysis.odoo_inventory_scope_classifier import (
    classify_odoo_inventory_scope,
    summarize_inventory_scope
)
from analysis.save_odoo_inventory_scope_classification import (
    save_odoo_inventory_scope_classification
)


if __name__ == "__main__":
    print("==== TEST ODOO INVENTORY SCOPE CLASSIFICATION ====\n")

    df = classify_odoo_inventory_scope()

    print("\n--- SUMMARY ---")
    print(summarize_inventory_scope(df).to_string(index=False))

    print("\n--- SAMPLE ---")
    print(df[[
        "odoo_product_id",
        "product_name",
        "category_name",
        "company_name",
        "inventory_scope",
        "scope_source",
        "scope_status"
    ]].head(40).to_string(index=False))

    print("\n--- SAVE ---")
    save_odoo_inventory_scope_classification()

    print("\n==== DONE ✅ ====")