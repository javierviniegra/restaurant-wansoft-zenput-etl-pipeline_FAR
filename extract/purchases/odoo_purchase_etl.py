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


def format_value_counts(df: pd.DataFrame, column_name: str) -> str:
    """
    Devuelve un value_counts limpio para impresión.
    """
    summary = (
        df[column_name]
        .value_counts(dropna=False)
        .reset_index()
    )

    summary.columns = [column_name, "count"]

    return summary.to_string(index=False)


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


def load_company_migration_policy():
    """
    Carga la política activa de migración por empresa.

    Esta tabla define desde qué fecha debe entrar cada empresa
    al pipeline de compras.
    """
    conn = get_db_connection(target="wansoft")

    query = """
    SELECT
        odoo_company_id AS company_id,
        company_name AS policy_company_name,
        company_migration_type,
        history_source,
        include_odoo_history,
        operational_start_date,
        is_active
    FROM odoo_company_migration_policy
    WHERE is_active = 1
    """

    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        return pd.DataFrame(columns=[
            "company_id",
            "policy_company_name",
            "company_migration_type",
            "history_source",
            "include_odoo_history",
            "operational_start_date",
            "is_active",
        ])

    df["company_id"] = pd.to_numeric(df["company_id"], errors="coerce")
    df["operational_start_date"] = pd.to_datetime(
        df["operational_start_date"],
        errors="coerce"
    ).dt.date

    return df


def apply_company_migration_policy(
    df: pd.DataFrame,
    fallback_min_order_date: str,
    date_col: str = "order_date",
    company_col: str = "company_id"
) -> pd.DataFrame:
    """
    Aplica política de migración por empresa.

    Reglas:
    - Si la empresa tiene política activa, usa operational_start_date.
    - Si no tiene política activa, usa fallback_min_order_date de .env.
    - El resultado queda enriquecido con columnas de trazabilidad.
    """
    if df is None or df.empty:
        return df

    out = df.copy()

    out[company_col] = pd.to_numeric(out[company_col], errors="coerce")
    out[date_col] = pd.to_datetime(out[date_col], errors="coerce")

    fallback_date = pd.to_datetime(fallback_min_order_date, errors="coerce")

    policy = load_company_migration_policy()

    if policy.empty:
        out["company_migration_type"] = "env_fallback"
        out["history_source"] = "unknown"
        out["include_odoo_history"] = 0
        out["operational_start_date"] = fallback_date.date() if not pd.isna(fallback_date) else None
        out["migration_policy_source"] = "env_fallback"

        if not pd.isna(fallback_date):
            out = out[out[date_col] >= fallback_date].copy()

        return out

    out = out.merge(
        policy[[
            "company_id",
            "company_migration_type",
            "history_source",
            "include_odoo_history",
            "operational_start_date",
        ]],
        left_on=company_col,
        right_on="company_id",
        how="left",
        suffixes=("", "_policy")
    )

    # Si el merge genera una segunda company_id por construcción, la eliminamos.
    if "company_id_policy" in out.columns:
        out = out.drop(columns=["company_id_policy"])

    has_policy = out["operational_start_date"].notna()

    out["migration_policy_source"] = has_policy.map({
        True: "company_policy",
        False: "env_fallback"
    })

    out.loc[~has_policy, "company_migration_type"] = "env_fallback"
    out.loc[~has_policy, "history_source"] = "unknown"
    out.loc[~has_policy, "include_odoo_history"] = 0

    if not pd.isna(fallback_date):
        out.loc[~has_policy, "operational_start_date"] = fallback_date.date()

    out["effective_start_date"] = pd.to_datetime(
        out["operational_start_date"],
        errors="coerce"
    )

    out = out[
        out[date_col].notna() &
        out["effective_start_date"].notna() &
        (out[date_col] >= out["effective_start_date"])
    ].copy()

    out["operational_start_date"] = pd.to_datetime(
        out["operational_start_date"],
        errors="coerce"
    ).dt.date

    out = out.drop(columns=["effective_start_date"])

    return out


def load_inventory_mapping_dictionary_for_purchases(allowed_status=None):
    """
    Carga el diccionario de inventory para enriquecer líneas de compra.

    Sólo se usan mappings del dominio inventory.
    Por defecto, sólo mapping_status = approved.
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
    - Sólo las product_line son elegibles para mapping.
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
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        company_migration_type,
        history_source,
        include_odoo_history,
        operational_start_date,
        migration_policy_source,
        order_date,
        state,
        purchase_line_type,
        product_mapping_found,
        product_mapping_status,
        wansoft_code,
        wansoft_product_name,
        wansoft_department,
        product_mapping_source,
        purchase_product_scope,
        purchase_mapping_bucket,
        purchase_classification_source,
        extracted_product_code
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            sql_safe(row.get("company_migration_type")),
            sql_safe(row.get("history_source")),
            int(row.get("include_odoo_history")) if not pd.isna(row.get("include_odoo_history")) else None,
            sql_safe(row.get("operational_start_date")),
            sql_safe(row.get("migration_policy_source")),
            sql_safe(row.get("order_date")),
            sql_safe(row.get("state")),
            sql_safe(row.get("purchase_line_type")),
            int(bool(row.get("product_mapping_found"))),
            sql_safe(row.get("product_mapping_status")),
            sql_safe(row.get("wansoft_code")),
            sql_safe(row.get("wansoft_product_name")),
            sql_safe(row.get("wansoft_department")),
            sql_safe(row.get("product_mapping_source")),
            sql_safe(row.get("purchase_product_scope")),
            sql_safe(row.get("purchase_mapping_bucket")),
            sql_safe(row.get("purchase_classification_source")),
            sql_safe(row.get("extracted_product_code")),
        ))

    execute_many_in_batches(cursor, insert_sql, rows)
    conn.commit()

    inserted = len(rows)

    cursor.close()
    conn.close()

    print(f"Insertados {inserted} registros en odoo_purchase_order_line_snapshot.")
    return inserted


def initialize_purchase_line_classification_columns(df_lines: pd.DataFrame) -> pd.DataFrame:
    """
    Inicializa columnas de clasificación futura de líneas no mapeadas.

    La lógica específica se implementará en el siguiente paso.
    Por ahora se dejan listas para persistencia sin romper el ETL.
    """
    df = df_lines.copy()

    for col in [
        "purchase_product_scope",
        "purchase_mapping_bucket",
        "purchase_classification_source",
        "extracted_product_code",
    ]:
        if col not in df.columns:
            df[col] = None

    return df


def run_odoo_purchase_etl():
    """
    ETL base del dominio compras.

    Flujo:
    1. Extrae purchase.order
    2. Extrae purchase.order.line
    3. Aplica política de migración por empresa
    4. Clasifica líneas
    5. Aplica mapping contra inventory_mapping_dictionary
    6. Inicializa columnas de clasificación
    7. Carga snapshots en MySQL
    """

    print("=== ODOO PURCHASE ETL START ===")

    cfg = get_purchase_etl_config()

    print("\n--- PURCHASE ETL CONFIG ---")
    print(f"min_order_date_fallback: {cfg['min_order_date']}")
    print(f"min_receipt_date_fallback: {cfg['min_receipt_date']}")
    print(f"apply_product_mapping: {cfg['apply_product_mapping']}")
    print(f"allowed_mapping_status: {cfg['allowed_mapping_status']}")

    df_orders_raw = extract_odoo_purchase_orders()
    df_lines_raw = extract_odoo_purchase_order_lines()

    df_orders = apply_company_migration_policy(
        df_orders_raw,
        cfg["min_order_date"],
        date_col="order_date",
        company_col="company_id"
    )

    df_lines = apply_company_migration_policy(
        df_lines_raw,
        cfg["min_order_date"],
        date_col="order_date",
        company_col="company_id"
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

    df_lines = initialize_purchase_line_classification_columns(df_lines)

    print("\n--- PURCHASE EXTRACT SUMMARY ---")
    print(f"purchase_orders_raw_rows: {len(df_orders_raw)}")
    print(f"purchase_orders_filtered_rows: {len(df_orders)}")
    print(f"purchase_order_lines_raw_rows: {len(df_lines_raw)}")
    print(f"purchase_order_lines_filtered_rows: {len(df_lines)}")

    print("\n--- PURCHASE POLICY SOURCE SUMMARY ---")
    print(format_value_counts(df_orders, "migration_policy_source"))

    print("\n--- PURCHASE LINE TYPE SUMMARY ---")
    print(format_value_counts(df_lines, "purchase_line_type"))

    print("\n--- PURCHASE PRODUCT MAPPING SUMMARY ---")
    print(format_value_counts(df_lines, "product_mapping_found"))

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