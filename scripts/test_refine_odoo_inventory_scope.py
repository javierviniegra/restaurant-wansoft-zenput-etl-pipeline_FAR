from analysis.refine_odoo_inventory_scope import refine_odoo_inventory_scope
from analysis.save_refined_odoo_inventory_scope import save_refined_odoo_inventory_scope


if __name__ == "__main__":
    print("==== TEST REFINE ODOO INVENTORY SCOPE ====\n")

    df = refine_odoo_inventory_scope()

    print("\n--- SUMMARY ---")
    summary = (
        df["refined_inventory_scope"]
        .value_counts()
        .reset_index()
    )
    summary.columns = ["refined_inventory_scope", "count"]
    print(summary.to_string(index=False))

    print("\n--- SAMPLE ---")
    print(df[[
        "product_name",
        "category_name",
        "inventory_scope",
        "refined_inventory_scope",
        "refined_scope_source",
        "refined_scope_status"
    ]].head(40).to_string(index=False))

    print("\n--- SAVE ---")
    save_refined_odoo_inventory_scope()

    print("\n==== DONE ✅ ====")
