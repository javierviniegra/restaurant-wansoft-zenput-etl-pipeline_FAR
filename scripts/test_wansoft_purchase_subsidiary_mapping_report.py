from analysis.build_wansoft_purchase_subsidiary_mapping_report import (
    build_wansoft_purchase_subsidiary_mapping_report,
    summarize_wansoft_purchase_subsidiary_mapping_report,
)


if __name__ == "__main__":
    print("==== TEST WANSOFT PURCHASE SUBSIDIARY MAPPING REPORT ====\n")

    df = build_wansoft_purchase_subsidiary_mapping_report()

    print("\n--- SUBSIDIARY MAPPING SUMMARY ---")
    print(
        summarize_wansoft_purchase_subsidiary_mapping_report(df)
        .to_string(index=False)
    )

    print("\n--- SUBSIDIARY MAPPING DETAIL ---")
    print(df.to_string(index=False))

    print("\n==== DONE ✅ ====")