from extract.purchases.odoo_purchase_receipt_etl import run_odoo_purchase_receipt_etl


if __name__ == "__main__":
    print("==== TEST ODOO PURCHASE RECEIPT ETL ====\n")

    run_odoo_purchase_receipt_etl()

    print("\n==== DONE ✅ ====")