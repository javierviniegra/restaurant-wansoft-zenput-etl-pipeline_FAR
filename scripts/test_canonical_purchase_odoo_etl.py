from extract.purchases.canonical_purchase_etl import run_canonical_purchase_odoo_etl


if __name__ == "__main__":
    print("==== TEST CANONICAL PURCHASE ODOO ETL ====\n")

    run_canonical_purchase_odoo_etl()

    print("\n==== DONE ✅ ====")