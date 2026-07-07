import os
import pandas as pd

from core.config.env_loader import load_environment
from core.database.mysql import get_mysql_connection as get_db_connection
from extract.purchases.odoo_purchase_orders import extract_odoo_purchase_orders
from extract.purchases.odoo_purchase_order_lines import extract_odoo_purchase_order_lines


BATCH_SIZE = 500


def sql_safe(value):
    """
    Normaliza valores antes de insertar en MySQL.
    """
    if pd.isna(value):
        return None

    if value is False:
        return None

    if isinstance(value, str):
        value = value.strip()
        return value if value else None

    return value


def parse_csv_env(value: str):
    if value is None:
        return []
    value = str(value).strip()
    if value == "":
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


def get_purchase_etl_config():
    """
    Configuración operativa del dominio compras.
    """
    load_environment()

    return {
        "min_order_date": os.getenv("PURCHASE_ETL_MIN_ORDER_DATE", "").strip(),

        "min_receipt_date": os.getenv("PURCHASE_ETL_MIN_RECEIPT_DATE", "").strip(),

        "apply_product_mapping": os.getenv(
            "PURCHASE_ETL_APPLY_PRODUCT_MAPPING",
            "true"
        ).strip().lower() == "true",

        "allowed_mapping_status": parse_csv_env(
            os.getenv("PURCHASE_ETL_ALLOWED_MAPPING_STATUS", "approved")
        ),
    }


def execute_many_in_batches(cursor, insert_sql, rows, batch_size=BATCH_SIZE):
    """
    Ejecuta inserts en lotes para evitar errores de max_allowed_packet.
    """
    total = len(rows)

    for start in range(0, total, batch_size):
        batch = rows[start:start + batch_size]
        cursor.executemany(insert_sql, batch)


def classify_purchase_line_type(row):
    """
    Clasifica líneas reales de producto vs líneas vacías/administrativas.
    """
    product_id = row.get("product_id")
    product_qty = row.get("product_qty")
    price_total = row.get("price_total")

    product_qty = 0 if pd.isna(product_qty) else product_qty
    price_total = 0 if pd.isna(price_total) else price_total

    if product_id is not None and not pd.isna(product_id):
        return "product_line"

    if (product_id is None or pd.isna(product_id)) and product_qty == 0 and price_total == 0:
        return "empty_line"

    return "review_line"


def load_inventory_mapping_dictionary_for_purchases(allowed_status=None):
    """
    Carga el diccionario de inventory para enriquecer líneas de compra.

    Solo se usan mappings del dominio inventory.
    Por defecto, solo mapping_status = approved.
    """
    if allowed_status is None:
        allowed_status = ["approved"]

    conn = get_db_connection(target="wansoft")

    placeholders = ", ".join(["%s"] * len(allowed_status))

    query = f"""
    SELECT
        odoo_product_id,
        mapping_status,
        wansoft_code,
        wansoft_product_name,
        wansoft_department,
        mapping_source
    FROM inventory_mapping_dictionary
    WHERE domain = 'inventory'
      AND odoo_product_id IS NOT NULL
      AND mapping_status IN ({placeholders})
    """

    df = pd.read_sql(query, conn, params=allowed_status)
    conn.close()

    if df.empty:
        return pd.DataFrame(columns=[
            "product_id",
            "product_mapping_status",
            "wansoft_code",
            "wansoft_product_name",
            "wansoft_department",
            "product_mapping_source",
        ])

    df["product_id"] = pd.to_numeric(df["odoo_product_id"], errors="coerce")

    df = df.rename(columns={
        "mapping_status": "product_mapping_status",
        "mapping_source": "product_mapping_source",
    })

    return df[[
        "product_id",
        "product_mapping_status",
        "wansoft_code",
        "wansoft_product_name",
        "wansoft_department",
        "product_mapping_source",
    ]]


def apply_purchase_product_mapping(df_lines: pd.DataFrame, allowed_status=None):
    """
    Aplica el inventory_mapping_dictionary a las líneas de compra.

    Reglas:
    - Solo las product_line son elegibles para mapping.
    - empty_line y review_line no se mapean.
    - El mapping se hace por product_id de Odoo.
    """
    if df_lines is None or df_lines.empty:
        return df_lines

    df = df_lines.copy()

    if "purchase_line_type" not in df.columns:
        df["purchase_line_type"] = df.apply(classify_purchase_line_type, axis=1)

    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce")

    df_mapping = load_inventory_mapping_dictionary_for_purchases(
        allowed_status=allowed_status
    )

    if df_mapping.empty:
        df["product_mapping_found"] = False
        df["product_mapping_status"] = None
        df["wansoft_code"] = None
        df["wansoft_product_name"] = None
        df["wansoft_department"] = None
        df["product_mapping_source"] = None
        return df

    df = df.merge(
        df_mapping,
        on="product_id",
        how="left"
    )

    df["product_mapping_found"] = (
        (df["purchase_line_type"] == "product_line") &
        (df["wansoft_code"].notna())
    )

    # Si no es product_line, limpiamos mapping aunque hubiera cruce accidental
    non_product_mask = df["purchase_line_type"] != "product_line"

    df.loc[non_product_mask, "product_mapping_found"] = False
    df.loc[non_product_mask, "product_mapping_status"] = None
    df.loc[non_product_mask, "wansoft_code"] = None
    df.loc[non_product_mask, "wansoft_product_name"] = None
    df.loc[non_product_mask, "wansoft_department"] = None
    df.loc[non_product_mask, "product_mapping_source"] = None

    return df


def save_purchase_orders(df: pd.DataFrame):
    """
    Guarda cabeceras de órdenes de compra en MySQL.
    """
    if df is None or df.empty:
        print("No hay órdenes de compra para guardar.")
        return 0

    conn = get_db_connection(target="wansoft")
    cursor = conn.cursor()

    cursor.execute("TRUNCATE TABLE odoo_purchase_order_snapshot")

    insert_sql = """
    INSERT INTO odoo_purchase_order_snapshot (
        odoo_purchase_order_id,
        purchase_order_name,
        vendor_id,
        vendor_name,
        company_id,
        company_name,
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
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    rows = []

    for _, row in df.iterrows():
        rows.append((
            sql_safe(row.get("odoo_purchase_order_id")),
            sql_safe(row.get("purchase_order_name")),
            sql_safe(row.get("vendor_id")),
            sql_safe(row.get("vendor_name")),
            sql_safe(row.get("company_id")),
            sql_safe(row.get("company_name")),
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

    print(f"Insertados {inserted} registros en odoo_purchase_order_snapshot.")
    return inserted


def save_purchase_order_lines(df: pd.DataFrame):
    """
    Guarda líneas de órdenes de compra en MySQL.
    """
    if df is None or df.empty:
        print("No hay líneas de compra para guardar.")
        return 0

    conn = get_db_connection(target="wansoft")
    cursor = conn.cursor()

    cursor.execute("TRUNCATE TABLE odoo_purchase_order_line_snapshot")

    insert_sql = """
    INSERT INTO odoo_purchase_order_line_snapshot (
        odoo_purchase_order_line_id,
        odoo_purchase_order_id,
        purchase_order_name,
        vendor_id,
        vendor_name,
        product_id,
        product_name,
        product_qty,
        qty_received,
        qty_invoiced,
        price_unit,
        price_subtotal,
        price_total,
        company_id,
        company_name,
        order_date,
        state,
        purchase_line_type,
        product_mapping_found,
        product_mapping_status,
        wansoft_code,
        wansoft_product_name,
        wansoft_department,
        product_mapping_source
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    rows = []

    for _, row in df.iterrows():
        rows.append((
            sql_safe(row.get("odoo_purchase_order_line_id")),
            sql_safe(row.get("odoo_purchase_order_id")),
            sql_safe(row.get("purchase_order_name")),
            sql_safe(row.get("vendor_id")),
            sql_safe(row.get("vendor_name")),
            sql_safe(row.get("product_id")),
            sql_safe(row.get("product_name")),
            sql_safe(row.get("product_qty")),
            sql_safe(row.get("qty_received")),
            sql_safe(row.get("qty_invoiced")),
            sql_safe(row.get("price_unit")),
            sql_safe(row.get("price_subtotal")),
            sql_safe(row.get("price_total")),
            sql_safe(row.get("company_id")),
            sql_safe(row.get("company_name")),
            sql_safe(row.get("order_date")),
            sql_safe(row.get("state")),
            sql_safe(row.get("purchase_line_type")),
            int(bool(row.get("product_mapping_found"))),
            sql_safe(row.get("product_mapping_status")),
            sql_safe(row.get("wansoft_code")),
            sql_safe(row.get("wansoft_product_name")),
            sql_safe(row.get("wansoft_department")),
            sql_safe(row.get("product_mapping_source")),
        ))

    execute_many_in_batches(cursor, insert_sql, rows)
    conn.commit()

    inserted = len(rows)

    cursor.close()
    conn.close()

    print(f"Insertados {inserted} registros en odoo_purchase_order_line_snapshot.")
    return inserted


def run_odoo_purchase_etl():
    """
    ETL base del dominio compras.

    Flujo:
    1. Extrae purchase.order
    2. Extrae purchase.order.line
    3. Clasifica líneas
    4. Aplica mapping contra inventory_mapping_dictionary
    5. Carga snapshots en MySQL
    """

    print("=== ODOO PURCHASE ETL START ===")

    cfg = get_purchase_etl_config()

    print("\n--- PURCHASE ETL CONFIG ---")
    print(f"min_order_date: {cfg['min_order_date']}")
    print(f"min_receipt_date: {cfg['min_receipt_date']}")
    print(f"apply_product_mapping: {cfg['apply_product_mapping']}")
    print(f"allowed_mapping_status: {cfg['allowed_mapping_status']}")

    df_orders_raw = extract_odoo_purchase_orders()
    df_lines_raw = extract_odoo_purchase_order_lines()

    df_orders = filter_purchase_by_min_order_date(
        df_orders_raw,
        cfg["min_order_date"],
        date_col="order_date"
    )

    df_lines = filter_purchase_by_min_order_date(
        df_lines_raw,
        cfg["min_order_date"],
        date_col="order_date"
    )

    df_lines["purchase_line_type"] = df_lines.apply(classify_purchase_line_type, axis=1)

    if cfg["apply_product_mapping"]:
        df_lines = apply_purchase_product_mapping(
            df_lines,
            allowed_status=cfg["allowed_mapping_status"]
        )
    else:
        df_lines["product_mapping_found"] = False
        df_lines["product_mapping_status"] = None
        df_lines["wansoft_code"] = None
        df_lines["wansoft_product_name"] = None
        df_lines["wansoft_department"] = None
        df_lines["product_mapping_source"] = None

    print("\n--- PURCHASE EXTRACT SUMMARY ---")
    print(f"purchase_orders_raw_rows: {len(df_orders_raw)}")
    print(f"purchase_orders_filtered_rows: {len(df_orders)}")
    print(f"purchase_order_lines_raw_rows: {len(df_lines_raw)}")
    print(f"purchase_order_lines_filtered_rows: {len(df_lines)}")

    print("\n--- PURCHASE LINE TYPE SUMMARY ---")
    print(
        df_lines["purchase_line_type"]
        .value_counts(dropna=False)
        .reset_index()
        .rename(columns={"index": "purchase_line_type", "purchase_line_type": "count"})
        .to_string(index=False)
    )

    print("\n--- PURCHASE PRODUCT MAPPING SUMMARY ---")
    print(
        df_lines["product_mapping_found"]
        .value_counts(dropna=False)
        .reset_index()
        .rename(columns={"index": "product_mapping_found", "product_mapping_found": "count"})
        .to_string(index=False)
    )

    inserted_orders = save_purchase_orders(df_orders)
    inserted_lines = save_purchase_order_lines(df_lines)

    print("\n--- PURCHASE LOAD COUNTS ---")
    print(f"orders_inserted: {inserted_orders}")
    print(f"lines_inserted: {inserted_lines}")

    print("=== ODOO PURCHASE ETL END ✅ ===")

    return {
        "orders_inserted": inserted_orders,
        "lines_inserted": inserted_lines,
        "orders_df": df_orders,
        "lines_df": df_lines,
    }

def filter_purchase_by_min_order_date(df: pd.DataFrame, min_order_date: str, date_col: str = "order_date") -> pd.DataFrame:
    """
    Filtra órdenes o líneas de compra por fecha mínima de migración.

    La intención es evitar cargar históricos de Odoo que todavía no forman parte
    del pipeline operativo principal, ya que el histórico sigue siendo leído desde Wansoft.
    """
    if df is None or df.empty:
        return df

    if not min_order_date:
        return df

    out = df.copy()

    out[date_col] = pd.to_datetime(out[date_col], errors="coerce")
    cutoff = pd.to_datetime(min_order_date)

    out = out[out[date_col] >= cutoff].copy()

    return out