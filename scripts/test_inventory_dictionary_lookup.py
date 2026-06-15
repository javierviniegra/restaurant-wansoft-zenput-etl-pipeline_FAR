from extract.utils.inventory_dictionary_lookup import load_inventory_mapping_dictionary


if __name__ == "__main__":
    print("==== TEST INVENTORY DICTIONARY LOOKUP ====\n")

    lookup_engine = load_inventory_mapping_dictionary()

    test_cases = [
        {"odoo_product_id": None, "product_name": "Aceite Vegetal"},
        {"odoo_product_id": None, "product_name": "Achiote"},
        {"odoo_product_id": None, "product_name": "Atun en Conserva"},
        {"odoo_product_id": None, "product_name": "Producto Inexistente XYZ"},
    ]

    for case in test_cases:
        result = lookup_engine.lookup(
            odoo_product_name=case["product_name"],
            odoo_product_id=case["odoo_product_id"],
            allow_pending=False,
            allow_historical=False
        )

        print(f"\n--- CASE: {case['product_name']} ---")
        for k, v in result.items():
            print(f"{k}: {v}")

    print("\n==== DONE ✅ ====")
