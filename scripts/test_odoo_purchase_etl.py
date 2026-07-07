from extract.purchases.odoo_purchase_etl import run_odoo_purchase_etl


if __name__ == "__main__":
    print("==== TEST ODOO PURCHASE ETL ====\n")

    run_odoo_purchase_etl()

    print("\n==== DONE ✅ ====")