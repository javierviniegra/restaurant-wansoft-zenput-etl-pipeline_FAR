from analysis.build_product_mapping import build_product_mapping
from analysis.product_mapping_stats import build_mapping_stats, print_mapping_stats


if __name__ == "__main__":
    print("==== TEST BUILD PRODUCT MAPPING ====\n")

    df_mapping = build_product_mapping(threshold=95)

    stats = build_mapping_stats(df_mapping)
    print_mapping_stats(stats)

    print("\n==== DONE ✅ ====")