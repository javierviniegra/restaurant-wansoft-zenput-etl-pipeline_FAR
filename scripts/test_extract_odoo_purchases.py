from extract.purchases.odoo_purchase_orders import extract_odoo_purchase_orders
from extract.purchases.odoo_purchase_order_lines import extract_odoo_purchase_order_lines


def print_state_summary(df, column_name="state"):
    summary = (
        df[column_name]
        .value_counts(dropna=False)
        .reset_index()
    )
    summary.columns = [column_name, "count"]
    print(summary.to_string(index=False))


if __name__ == "__main__":
    print("==== TEST EXTRACT ODOO PURCHASES ====\n")

    df_orders = extract_odoo_purchase_orders()
    df_lines = extract_odoo_purchase_order_lines()

    print("\n--- PURCHASE ORDERS SUMMARY ---")
    print(f"purchase_orders_rows: {len(df_orders)}")

    if not df_orders.empty:
        print("\n--- PURCHASE ORDERS COLUMNS ---")
        print(list(df_orders.columns))

        print("\n--- PURCHASE ORDERS SAMPLE ---")
        print(df_orders.head(20).to_string(index=False))

        print("\n--- PURCHASE ORDERS BY STATE ---")
        print_state_summary(df_orders, "state")

        print("\n--- PURCHASE ORDERS BY INVOICE STATUS ---")
        print_state_summary(df_orders, "invoice_status")

    print("\n--- PURCHASE ORDER LINES SUMMARY ---")
    print(f"purchase_order_lines_rows: {len(df_lines)}")

    if not df_lines.empty:
        print("\n--- PURCHASE ORDER LINES COLUMNS ---")
        print(list(df_lines.columns))

        print("\n--- PURCHASE ORDER LINES SAMPLE ---")
        print(df_lines.head(20).to_string(index=False))

        print("\n--- PURCHASE ORDER LINES BY STATE ---")
        print_state_summary(df_lines, "state")

    print("\n==== DONE ✅ ====")