from extract.purchases.odoo_purchase_receipts import (
    extract_odoo_purchase_receipts,
    extract_odoo_purchase_receipt_moves
)


def print_state_summary(df, column_name="state"):
    summary = (
        df[column_name]
        .value_counts(dropna=False)
        .reset_index()
    )
    summary.columns = [column_name, "count"]
    print(summary.to_string(index=False))


if __name__ == "__main__":
    print("==== TEST EXTRACT ODOO PURCHASE RECEIPTS ====\n")

    df_receipts = extract_odoo_purchase_receipts()
    df_moves = extract_odoo_purchase_receipt_moves()

    print("\n--- PURCHASE RECEIPTS SUMMARY ---")
    print(f"purchase_receipts_rows: {len(df_receipts)}")

    if not df_receipts.empty:
        print("\n--- PURCHASE RECEIPTS COLUMNS ---")
        print(list(df_receipts.columns))

        print("\n--- PURCHASE RECEIPTS SAMPLE ---")
        print(df_receipts.head(20).to_string(index=False))

        print("\n--- PURCHASE RECEIPTS BY STATE ---")
        print_state_summary(df_receipts, "state")

    print("\n--- PURCHASE RECEIPT MOVES SUMMARY ---")
    print(f"purchase_receipt_moves_rows: {len(df_moves)}")

    if not df_moves.empty:
        print("\n--- PURCHASE RECEIPT MOVES COLUMNS ---")
        print(list(df_moves.columns))

        print("\n--- PURCHASE RECEIPT MOVES SAMPLE ---")
        print(df_moves.head(20).to_string(index=False))

        print("\n--- PURCHASE RECEIPT MOVES BY STATE ---")
        print_state_summary(df_moves, "state")

    print("\n==== DONE ✅ ====")