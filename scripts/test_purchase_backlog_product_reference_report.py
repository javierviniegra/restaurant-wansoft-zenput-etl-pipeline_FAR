from analysis.build_purchase_backlog_product_reference_report import (
    build_purchase_backlog_product_reference_report,
    summarize_purchase_backlog_product_reference_report
)


if __name__ == "__main__":
    print("==== TEST PURCHASE BACKLOG PRODUCT REFERENCES ====\n")

    df = build_purchase_backlog_product_reference_report()

    if df.empty:
        print("No purchase inventory mapping backlog found.")
    else:
        print("\n--- REFERENCE SUMMARY ---")
        print(
            summarize_purchase_backlog_product_reference_report(df)
            .to_string(index=False)
        )

        print("\n--- SAMPLE WITH REFERENCE ---")
        print(
            df[df["has_odoo_default_code"] == True][[
                "product_id",
                "product_name",
                "odoo_default_code",
                "odoo_category_name",
                "total_lines",
                "unique_vendors",
                "unique_companies",
                "total_amount",
                "reference_review_bucket"
            ]]
            .head(40)
            .to_string(index=False)
        )

        print("\n--- SAMPLE WITHOUT REFERENCE ---")
        print(
            df[df["has_odoo_default_code"] == False][[
                "product_id",
                "product_name",
                "odoo_default_code",
                "odoo_category_name",
                "total_lines",
                "unique_vendors",
                "unique_companies",
                "total_amount",
                "reference_review_bucket"
            ]]
            .head(40)
            .to_string(index=False)
        )

    print("\n==== DONE ✅ ====")