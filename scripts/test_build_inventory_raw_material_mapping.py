from analysis.build_sales_product_mapping import build_sales_product_mapping
from analysis.build_inventory_raw_material_mapping import build_inventory_raw_material_mapping
from analysis.product_mapping_stats import build_mapping_stats, print_mapping_stats


if __name__ == "__main__":
    print("==== TEST BUILD INVENTORY RAW MATERIAL MAPPING ====\n")

    # usamos sales mapping ya homologado como referencia
    df_sales_mapping = build_sales_product_mapping(threshold=95)

    df_mapping = build_inventory_raw_material_mapping(
        df_sales_mapping=df_sales_mapping,
        threshold=95
    )

    stats = build_mapping_stats(df_mapping)
    print_mapping_stats(stats)

    print("\n==== DONE ✅ ====")
