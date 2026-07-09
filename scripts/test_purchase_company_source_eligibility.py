from analysis.build_purchase_company_source_eligibility_report import (
    build_combined_purchase_company_source_eligibility_summary,
    build_final_odoo_candidate_samples,
)


def print_sample(label, df):
    print(f"\n--- FINAL ODOO SAMPLE: {label.upper()} ---")

    if df is None or df.empty:
        print("No rows.")
        return

    columns_to_show = [
        col for col in [
            "company_name",
            "company_source_key",
            "domain_source",
            "include_final_company",
            "final_purchase_source_status",
            "purchase_order_name",
            "receipt_name",
            "origin",
            "product_id",
            "product_name",
            "state",
            "order_date",
            "scheduled_date",
            "move_date",
        ]
        if col in df.columns
    ]

    print(df[columns_to_show].head(30).to_string(index=False))


if __name__ == "__main__":
    print("==== TEST PURCHASE COMPANY SOURCE ELIGIBILITY ====\n")

    summary = build_combined_purchase_company_source_eligibility_summary()

    print("\n--- COMPANY SOURCE ELIGIBILITY SUMMARY ---")
    print(summary.to_string(index=False))

    samples = build_final_odoo_candidate_samples(limit=30)

    for label, df in samples.items():
        print_sample(label, df)

    print("\n==== DONE ✅ ====")