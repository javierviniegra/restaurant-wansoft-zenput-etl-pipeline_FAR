import pandas as pd
from extract.utils.inventory_dictionary_wrapper import (
    apply_inventory_dictionary,
    summarize_inventory_dictionary_application,
    split_inventory_dictionary_result
)


if __name__ == "__main__":
    print("==== TEST APPLY INVENTORY DICTIONARY ====\n")

    # dataframe de prueba simulando salida del ETL de Odoo
    df_test = pd.DataFrame([
        {"odoo_product_id": None, "product_name": "Aceite Vegetal"},
        {"odoo_product_id": None, "product_name": "Achiote"},
        {"odoo_product_id": None, "product_name": "Atun en Conserva"},
        {"odoo_product_id": None, "product_name": "Producto Inexistente XYZ"},
    ])

    df_result = apply_inventory_dictionary(
        df_odoo_inventory=df_test,
        product_name_col="product_name",
        odoo_product_id_col="odoo_product_id",
        allow_pending=False,
        allow_historical=False
    )

    print("\n--- RESULT ---")
    print(df_result.to_string(index=False))

    print("\n--- SUMMARY ---")
    print(summarize_inventory_dictionary_application(df_result).to_string(index=False))

    parts = split_inventory_dictionary_result(df_result)

    print("\n--- COUNTS BY PART ---")
    print(f"approved_rows: {len(parts['approved_rows'])}")
    print(f"pending_rows: {len(parts['pending_rows'])}")
    print(f"historical_rows: {len(parts['historical_rows'])}")
    print(f"not_found_rows: {len(parts['not_found_rows'])}")

    print("\n==== DONE ✅ ====")
