from analysis.review_scope_refiner import (
    build_review_scope_refinement,
    summarize_review_scope_refinement
)
from analysis.save_review_scope_refiner import save_review_scope_refinement


if __name__ == "__main__":
    print("==== TEST REVIEW_SCOPE REFINER ====\n")

    df = build_review_scope_refinement()

    print("\n--- SUMMARY ---")
    print(summarize_review_scope_refinement(df).to_string(index=False))

    print("\n--- SAMPLE ---")
    print(df[[
        "odoo_product_id",
        "product_name",
        "category_name",
        "refined_inventory_scope",
        "refined_inventory_scope_v2",
        "refined_scope_source_v2",
        "refined_scope_status_v2"
    ]].head(50).to_string(index=False))

    print("\n--- SAVE ---")
    save_review_scope_refinement()

    print("\n==== DONE ✅ ====")