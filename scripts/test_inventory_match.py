from extract.db.wansoft_inventory_db import get_wansoft_inventory_from_db
from extract.inventory.odoo_inventory import extract_odoo_inventory
from analysis.normalize_inventory import normalize_wansoft_inventory
from analysis.inventory_match import match_inventory_by_product


if __name__ == "__main__":
    print("==== TEST INVENTORY MATCH ====\n")

    # WANSOFT
    df_w_raw = get_wansoft_inventory_from_db()
    df_w = normalize_wansoft_inventory(df_w_raw)

    # ODOO
    df_o = extract_odoo_inventory()

    # MATCH
    df_match = match_inventory_by_product(df_w, df_o)

    print(df_match.head(20))

    print("\n==== DONE ✅ ====")