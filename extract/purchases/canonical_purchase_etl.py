import pandas as pd

from core.database.mysql import get_mysql_connection as get_db_connection
from extract.purchases.odoo_purchase_etl import (
    sql_safe,
    execute_many_in_batches,
)
from analysis.build_purchase_company_source_eligibility_report import (
    apply_purchase_company_source_flags,
)


FINAL_ODOO_STATUS = "final_odoo_enabled"
SOURCE_SYSTEM_ODOO = "odoo"
SOURCE_SYSTEM_WANSOFT = "wansoft"


def load_table(table_name: str) -> pd.DataFrame:
    """
    Loads a MySQL table into a DataFrame.
    """
    conn = get_db_connection(target="wansoft")

    query = f"""
    SELECT *
    FROM {table_name}
    """

    df = pd.read_sql(query, conn)
    conn.close()

    return df


def delete_existing_odoo_rows(table_name: str):
    """
    Deletes only Odoo rows from a canonical table.

    This preserves future Wansoft rows when the Wansoft canonical
    load is added.
    """
    conn = get_db_connection(target="wansoft")
    cursor = conn.cursor()

    cursor.execute(
        f"""
        DELETE FROM {table_name}
        WHERE source_system = %s
        """,
        (SOURCE_SYSTEM_ODOO,)
    )

    conn.commit()
    cursor.close()
    conn.close()


def filter_final_odoo_enabled(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies company source governance and keeps only rows eligible
    for the final Odoo purchase canonical layer.
    """
    if df is None or df.empty:
        return df

    flagged = apply_purchase_company_source_flags(df)

    out = flagged[
        flagged["final_purchase_source_status"] == FINAL_ODOO_STATUS
    ].copy()

    return out


def build_canonical_odoo_purchase_orders() -> pd.DataFrame:
    df = load_table("odoo_purchase_order_snapshot")
    return filter_final_odoo_enabled(df)


def build_canonical_odoo_purchase_lines() -> pd.DataFrame:
    df = load_table("odoo_purchase_order_line_snapshot")
    return filter_final_odoo_enabled(df)


def build_canonical_odoo_purchase_receipts() -> pd.DataFrame:
    df = load_table("odoo_purchase_receipt_snapshot")
    return filter_final_odoo_enabled(df)


def build_canonical_odoo_purchase_receipt_moves() -> pd.DataFrame:
    """
    Builds canonical receipt moves.

    Receipt moves are enriched with product mapping from purchase lines
    when a purchase line relationship exists.
    """
    df_moves = load_table("odoo_purchase_receipt_move_snapshot")
    df_lines = load_table("odoo_purchase_order_line_snapshot")

    df_moves = filter_final_odoo_enabled(df_moves)

    if df_moves is None or df_moves.empty:
        return df_moves

    mapping_cols = [
        "odoo_purchase_order_line_id",
        "wansoft_code",
        "wansoft_product_name",
        "wansoft_department",
    ]

    available_mapping_cols = [
        col for col in mapping_cols if col in df_lines.columns
    ]

    df_mapping = df_lines[available_mapping_cols].drop_duplicates(
        subset=["odoo_purchase_order_line_id"]
    )

    df = df_moves.merge(
        df_mapping,
        on="odoo_purchase_order_line_id",
        how="left"
    )

    return df


def save_canonical_odoo_purchase_orders(df: pd.DataFrame):
    table_name = "canonical_purchase_order_snapshot"
    delete_existing_odoo_rows(table_name)

    if df is None or df.empty:
        print("No hay órdenes Odoo elegibles para capa canónica.")
        return 0

    conn = get_db_connection(target="wansoft")
    cursor = conn.cursor()

    insert_sql = """
    INSERT INTO canonical_purchase_order_snapshot (
        source_system,
        source_domain,
        source_order_id,
        purchase_order_name,
        vendor_id,
        vendor_name,
        company_id,
        company_name,
        company_source_key,
        final_purchase_source_status,
        company_migration_type,
        history_source,
        include_odoo_history,
        operational_start_date,
        migration_policy_source,
        order_date,
        approval_date,
        state,
        invoice_status,
        amount_untaxed,
        amount_tax,
        amount_total,
        currency_id,
        currency_name,
        picking_count
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    rows = []

    for _, row in df.iterrows():
        rows.append((
            SOURCE_SYSTEM_ODOO,
            "purchase_order",
            sql_safe(row.get("odoo_purchase_order_id")),
            sql_safe(row.get("purchase_order_name")),
            sql_safe(row.get("vendor_id")),
            sql_safe(row.get("vendor_name")),
            sql_safe(row.get("company_id")),
            sql_safe(row.get("company_name")),
            sql_safe(row.get("company_source_key")),
            sql_safe(row.get("final_purchase_source_status")),
            sql_safe(row.get("company_migration_type")),
            sql_safe(row.get("history_source")),
            int(row.get("include_odoo_history")) if not pd.isna(row.get("include_odoo_history")) else None,
            sql_safe(row.get("operational_start_date")),
            sql_safe(row.get("migration_policy_source")),
            sql_safe(row.get("order_date")),
            sql_safe(row.get("approval_date")),
            sql_safe(row.get("state")),
            sql_safe(row.get("invoice_status")),
            sql_safe(row.get("amount_untaxed")),
            sql_safe(row.get("amount_tax")),
            sql_safe(row.get("amount_total")),
            sql_safe(row.get("currency_id")),
            sql_safe(row.get("currency_name")),
            sql_safe(row.get("picking_count")),
        ))

    execute_many_in_batches(cursor, insert_sql, rows)
    conn.commit()

    inserted = len(rows)

    cursor.close()
    conn.close()

    print(f"Insertados {inserted} registros Odoo en {table_name}.")
    return inserted


def save_canonical_odoo_purchase_lines(df: pd.DataFrame):
    table_name = "canonical_purchase_order_line_snapshot"
    delete_existing_odoo_rows(table_name)

    if df is None or df.empty:
        print("No hay líneas Odoo elegibles para capa canónica.")
        return 0

    conn = get_db_connection(target="wansoft")
    cursor = conn.cursor()

    insert_sql = """
    INSERT INTO canonical_purchase_order_line_snapshot (
        source_system,
        source_domain,
        source_order_line_id,
        source_order_id,
        purchase_order_name,
        vendor_id,
        vendor_name,
        company_id,
        company_name,
        company_source_key,
        final_purchase_source_status,
        company_migration_type,
        history_source,
        include_odoo_history,
        operational_start_date,
        migration_policy_source,
        product_id,
        product_name,
        wansoft_code,
        wansoft_product_name,
        wansoft_department,
        product_mapping_found,
        product_mapping_status,
        product_mapping_source,
        purchase_line_type,
        purchase_product_scope,
        purchase_mapping_bucket,
        purchase_classification_source,
        extracted_product_code,
        product_qty,
        qty_received,
        qty_invoiced,
        price_unit,
        price_subtotal,
        price_total,
        order_date,
        state
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    rows = []

    for _, row in df.iterrows():
        rows.append((
            SOURCE_SYSTEM_ODOO,
            "purchase_order_line",
            sql_safe(row.get("odoo_purchase_order_line_id")),
            sql_safe(row.get("odoo_purchase_order_id")),
            sql_safe(row.get("purchase_order_name")),
            sql_safe(row.get("vendor_id")),
            sql_safe(row.get("vendor_name")),
            sql_safe(row.get("company_id")),
            sql_safe(row.get("company_name")),
            sql_safe(row.get("company_source_key")),
            sql_safe(row.get("final_purchase_source_status")),
            sql_safe(row.get("company_migration_type")),
            sql_safe(row.get("history_source")),
            int(row.get("include_odoo_history")) if not pd.isna(row.get("include_odoo_history")) else None,
            sql_safe(row.get("operational_start_date")),
            sql_safe(row.get("migration_policy_source")),
            sql_safe(row.get("product_id")),
            sql_safe(row.get("product_name")),
            sql_safe(row.get("wansoft_code")),
            sql_safe(row.get("wansoft_product_name")),
            sql_safe(row.get("wansoft_department")),
            int(bool(row.get("product_mapping_found"))) if not pd.isna(row.get("product_mapping_found")) else None,
            sql_safe(row.get("product_mapping_status")),
            sql_safe(row.get("product_mapping_source")),
            sql_safe(row.get("purchase_line_type")),
            sql_safe(row.get("purchase_product_scope")),
            sql_safe(row.get("purchase_mapping_bucket")),
            sql_safe(row.get("purchase_classification_source")),
            sql_safe(row.get("extracted_product_code")),
            sql_safe(row.get("product_qty")),
            sql_safe(row.get("qty_received")),
            sql_safe(row.get("qty_invoiced")),
            sql_safe(row.get("price_unit")),
            sql_safe(row.get("price_subtotal")),
            sql_safe(row.get("price_total")),
            sql_safe(row.get("order_date")),
            sql_safe(row.get("state")),
        ))

    execute_many_in_batches(cursor, insert_sql, rows)
    conn.commit()

    inserted = len(rows)

    cursor.close()
    conn.close()

    print(f"Insertados {inserted} registros Odoo en {table_name}.")
    return inserted


def save_canonical_odoo_purchase_receipts(df: pd.DataFrame):
    table_name = "canonical_purchase_receipt_snapshot"
    delete_existing_odoo_rows(table_name)

    if df is None or df.empty:
        print("No hay recepciones Odoo elegibles para capa canónica.")
        return 0

    conn = get_db_connection(target="wansoft")
    cursor = conn.cursor()

    insert_sql = """
    INSERT INTO canonical_purchase_receipt_snapshot (
        source_system,
        source_domain,
        source_receipt_id,
        receipt_name,
        origin,
        vendor_id,
        vendor_name,
        company_id,
        company_name,
        company_source_key,
        final_purchase_source_status,
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
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    rows = []

    for _, row in df.iterrows():
        rows.append((
            SOURCE_SYSTEM_ODOO,
            "purchase_receipt",
            sql_safe(row.get("odoo_receipt_id")),
            sql_safe(row.get("receipt_name")),
            sql_safe(row.get("origin")),
            sql_safe(row.get("vendor_id")),
            sql_safe(row.get("vendor_name")),
            sql_safe(row.get("company_id")),
            sql_safe(row.get("company_name")),
            sql_safe(row.get("company_source_key")),
            sql_safe(row.get("final_purchase_source_status")),
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

    print(f"Insertados {inserted} registros Odoo en {table_name}.")
    return inserted


def save_canonical_odoo_purchase_receipt_moves(df: pd.DataFrame):
    table_name = "canonical_purchase_receipt_move_snapshot"
    delete_existing_odoo_rows(table_name)

    if df is None or df.empty:
        print("No hay movimientos Odoo elegibles para capa canónica.")
        return 0

    conn = get_db_connection(target="wansoft")
    cursor = conn.cursor()

    insert_sql = """
    INSERT INTO canonical_purchase_receipt_move_snapshot (
        source_system,
        source_domain,
        source_stock_move_id,
        reference,
        origin,
        source_receipt_id,
        receipt_name,
        source_order_line_id,
        purchase_line_name,
        product_id,
        product_name,
        wansoft_code,
        wansoft_product_name,
        wansoft_department,
        product_uom_qty,
        quantity,
        product_uom_id,
        product_uom_name,
        company_id,
        company_name,
        company_source_key,
        final_purchase_source_status,
        company_migration_type,
        history_source,
        include_odoo_history,
        operational_start_date,
        migration_policy_source,
        state,
        move_date,
        date_deadline
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    rows = []

    for _, row in df.iterrows():
        rows.append((
            SOURCE_SYSTEM_ODOO,
            "purchase_receipt_move",
            sql_safe(row.get("odoo_stock_move_id")),
            sql_safe(row.get("reference")),
            sql_safe(row.get("origin")),
            sql_safe(row.get("odoo_receipt_id")),
            sql_safe(row.get("receipt_name")),
            sql_safe(row.get("odoo_purchase_order_line_id")),
            sql_safe(row.get("purchase_line_name")),
            sql_safe(row.get("product_id")),
            sql_safe(row.get("product_name")),
            sql_safe(row.get("wansoft_code")),
            sql_safe(row.get("wansoft_product_name")),
            sql_safe(row.get("wansoft_department")),
            sql_safe(row.get("product_uom_qty")),
            sql_safe(row.get("quantity")),
            sql_safe(row.get("product_uom_id")),
            sql_safe(row.get("product_uom_name")),
            sql_safe(row.get("company_id")),
            sql_safe(row.get("company_name")),
            sql_safe(row.get("company_source_key")),
            sql_safe(row.get("final_purchase_source_status")),
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

    print(f"Insertados {inserted} registros Odoo en {table_name}.")
    return inserted


def run_canonical_purchase_odoo_etl():
    """
    Loads Odoo eligible purchase records into the canonical purchase layer.

    This step loads only source_system = 'odoo'.
    Future Wansoft canonical loading should preserve these rows and load
    source_system = 'wansoft' separately.
    """

    print("=== CANONICAL PURCHASE ODOO ETL START ===")

    df_orders = build_canonical_odoo_purchase_orders()
    df_lines = build_canonical_odoo_purchase_lines()
    df_receipts = build_canonical_odoo_purchase_receipts()
    df_moves = build_canonical_odoo_purchase_receipt_moves()

    print("\n--- CANONICAL ODOO ELIGIBLE SUMMARY ---")
    print(f"orders_eligible: {len(df_orders)}")
    print(f"lines_eligible: {len(df_lines)}")
    print(f"receipts_eligible: {len(df_receipts)}")
    print(f"receipt_moves_eligible: {len(df_moves)}")

    inserted_orders = save_canonical_odoo_purchase_orders(df_orders)
    inserted_lines = save_canonical_odoo_purchase_lines(df_lines)
    inserted_receipts = save_canonical_odoo_purchase_receipts(df_receipts)
    inserted_moves = save_canonical_odoo_purchase_receipt_moves(df_moves)

    print("\n--- CANONICAL ODOO LOAD COUNTS ---")
    print(f"orders_inserted: {inserted_orders}")
    print(f"lines_inserted: {inserted_lines}")
    print(f"receipts_inserted: {inserted_receipts}")
    print(f"receipt_moves_inserted: {inserted_moves}")

    print("=== CANONICAL PURCHASE ODOO ETL END ✅ ===")

    return {
        "orders_inserted": inserted_orders,
        "lines_inserted": inserted_lines,
        "receipts_inserted": inserted_receipts,
        "receipt_moves_inserted": inserted_moves,
    }

def run_canonical_purchase_wansoft_etl():
    print("canonical_purchase_wansoft_etl module loaded correctly.")
    return {
        "orders_inserted": 0,
        "lines_inserted": 0,
        "receipts_inserted": 0,
        "receipt_moves_inserted": 0,
    }