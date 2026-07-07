import pandas as pd

from core.database.mysql import get_mysql_connection as get_db_connection
from extract.purchases.odoo_purchase_receipts import (
    extract_odoo_purchase_receipts,
    extract_odoo_purchase_receipt_moves
)
from extract.purchases.odoo_purchase_etl import (
    get_purchase_etl_config,
    apply_company_migration_policy,
    execute_many_in_batches,
    sql_safe,
    format_value_counts
)


def save_purchase_receipts(df: pd.DataFrame):
    """
    Guarda recepciones de compra en MySQL.

    Tabla destino:
    - odoo_purchase_receipt_snapshot
    """

    if df is None or df.empty:
        print("No hay recepciones de compra para guardar.")
        return 0

    conn = get_db_connection(target="wansoft")
    cursor = conn.cursor()

    cursor.execute("TRUNCATE TABLE odoo_purchase_receipt_snapshot")

    insert_sql = """
    INSERT INTO odoo_purchase_receipt_snapshot (
        odoo_receipt_id,
        receipt_name,
        origin,
        vendor_id,
        vendor_name,
        company_id,
        company_name,
        company_migration_type,
        history_source,
        include_odoo_history,
        operational_start_date,
        migration_policy_source,
        picking_type_id,
        picking_type_name,
        picking_type_code,
        scheduled_date,
        date_done,
        state,
        move_count,
        move_line_count
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    rows = []

    for _, row in df.iterrows():
        rows.append((
            sql_safe(row.get("odoo_receipt_id")),
            sql_safe(row.get("receipt_name")),
            sql_safe(row.get("origin")),
            sql_safe(row.get("vendor_id")),
            sql_safe(row.get("vendor_name")),
            sql_safe(row.get("company_id")),
            sql_safe(row.get("company_name")),
            sql_safe(row.get("company_migration_type")),
            sql_safe(row.get("history_source")),
            int(row.get("include_odoo_history")) if not pd.isna(row.get("include_odoo_history")) else None,
            sql_safe(row.get("operational_start_date")),
            sql_safe(row.get("migration_policy_source")),
            sql_safe(row.get("picking_type_id")),
            sql_safe(row.get("picking_type_name")),
            sql_safe(row.get("picking_type_code")),
            sql_safe(row.get("scheduled_date")),
            sql_safe(row.get("date_done")),
            sql_safe(row.get("state")),
            sql_safe(row.get("move_count")),
            sql_safe(row.get("move_line_count")),
        ))

    execute_many_in_batches(cursor, insert_sql, rows)
    conn.commit()

    inserted = len(rows)

    cursor.close()
    conn.close()

    print(f"Insertados {inserted} registros en odoo_purchase_receipt_snapshot.")
    return inserted


def save_purchase_receipt_moves(df: pd.DataFrame):
    """
    Guarda movimientos de recepción de compra en MySQL.

    Tabla destino:
    - odoo_purchase_receipt_move_snapshot
    """

    if df is None or df.empty:
        print("No hay movimientos de recepción para guardar.")
        return 0

    conn = get_db_connection(target="wansoft")
    cursor = conn.cursor()

    cursor.execute("TRUNCATE TABLE odoo_purchase_receipt_move_snapshot")

    insert_sql = """
    INSERT INTO odoo_purchase_receipt_move_snapshot (
        odoo_stock_move_id,
        reference,
        origin,
        odoo_receipt_id,
        receipt_name,
        odoo_purchase_order_line_id,
        purchase_line_name,
        product_id,
        product_name,
        product_uom_qty,
        quantity,
        product_uom_id,
        product_uom_name,
        company_id,
        company_name,
        company_migration_type,
        history_source,
        include_odoo_history,
        operational_start_date,
        migration_policy_source,
        state,
        move_date,
        date_deadline
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    rows = []

    for _, row in df.iterrows():
        rows.append((
            sql_safe(row.get("odoo_stock_move_id")),
            sql_safe(row.get("reference")),
            sql_safe(row.get("origin")),
            sql_safe(row.get("odoo_receipt_id")),
            sql_safe(row.get("receipt_name")),
            sql_safe(row.get("odoo_purchase_order_line_id")),
            sql_safe(row.get("purchase_line_name")),
            sql_safe(row.get("product_id")),
            sql_safe(row.get("product_name")),
            sql_safe(row.get("product_uom_qty")),
            sql_safe(row.get("quantity")),
            sql_safe(row.get("product_uom_id")),
            sql_safe(row.get("product_uom_name")),
            sql_safe(row.get("company_id")),
            sql_safe(row.get("company_name")),
            sql_safe(row.get("company_migration_type")),
            sql_safe(row.get("history_source")),
            int(row.get("include_odoo_history")) if not pd.isna(row.get("include_odoo_history")) else None,
            sql_safe(row.get("operational_start_date")),
            sql_safe(row.get("migration_policy_source")),
            sql_safe(row.get("state")),
            sql_safe(row.get("move_date")),
            sql_safe(row.get("date_deadline")),
        ))

    execute_many_in_batches(cursor, insert_sql, rows)
    conn.commit()

    inserted = len(rows)

    cursor.close()
    conn.close()

    print(f"Insertados {inserted} registros en odoo_purchase_receipt_move_snapshot.")
    return inserted


def run_odoo_purchase_receipt_etl():
    """
    ETL de recepciones del dominio compras.

    Flujo:
    1. Extrae stock.picking incoming
    2. Extrae stock.move con purchase_line_id
    3. Aplica política de migración por empresa
    4. Guarda snapshots en MySQL
    """

    print("=== ODOO PURCHASE RECEIPT ETL START ===")

    cfg = get_purchase_etl_config()

    print("\n--- PURCHASE RECEIPT ETL CONFIG ---")
    print(f"min_receipt_date_fallback: {cfg['min_receipt_date']}")

    df_receipts_raw = extract_odoo_purchase_receipts()
    df_moves_raw = extract_odoo_purchase_receipt_moves()

    df_receipts = apply_company_migration_policy(
        df_receipts_raw,
        cfg["min_receipt_date"],
        date_col="scheduled_date",
        company_col="company_id"
    )

    df_moves = apply_company_migration_policy(
        df_moves_raw,
        cfg["min_receipt_date"],
        date_col="move_date",
        company_col="company_id"
    )

    print("\n--- PURCHASE RECEIPT EXTRACT SUMMARY ---")
    print(f"purchase_receipts_raw_rows: {len(df_receipts_raw)}")
    print(f"purchase_receipts_filtered_rows: {len(df_receipts)}")
    print(f"purchase_receipt_moves_raw_rows: {len(df_moves_raw)}")
    print(f"purchase_receipt_moves_filtered_rows: {len(df_moves)}")

    if not df_receipts.empty:
        print("\n--- PURCHASE RECEIPT POLICY SOURCE SUMMARY ---")
        print(format_value_counts(df_receipts, "migration_policy_source"))

        print("\n--- PURCHASE RECEIPTS BY STATE ---")
        print(format_value_counts(df_receipts, "state"))

    if not df_moves.empty:
        print("\n--- PURCHASE RECEIPT MOVES POLICY SOURCE SUMMARY ---")
        print(format_value_counts(df_moves, "migration_policy_source"))

        print("\n--- PURCHASE RECEIPT MOVES BY STATE ---")
        print(format_value_counts(df_moves, "state"))

    inserted_receipts = save_purchase_receipts(df_receipts)
    inserted_moves = save_purchase_receipt_moves(df_moves)

    print("\n--- PURCHASE RECEIPT LOAD COUNTS ---")
    print(f"receipts_inserted: {inserted_receipts}")
    print(f"receipt_moves_inserted: {inserted_moves}")

    print("=== ODOO PURCHASE RECEIPT ETL END ✅ ===")

    return {
        "receipts_inserted": inserted_receipts,
        "receipt_moves_inserted": inserted_moves,
        "receipts_df": df_receipts,
        "moves_df": df_moves,
    }