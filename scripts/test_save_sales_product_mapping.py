from analysis.save_sales_product_mapping import save_sales_product_mapping


if __name__ == "__main__":
    print("==== TEST SAVE SALES PRODUCT MAPPING ====\n")

    # Recomendación inicial:
    # guardar exact_code + odoo_no_code + fuzzy_name suggested
    save_sales_product_mapping(include_fuzzy=True)

    print("\n==== DONE ✅ ====")