from extract.inventory.odoo_inventory_etl import run_odoo_inventory_etl


if __name__ == "__main__":
    print("==== TEST ODOO INVENTORY ETL ====\n")

    run_odoo_inventory_etl()

    print("\n==== DONE ✅ ====")