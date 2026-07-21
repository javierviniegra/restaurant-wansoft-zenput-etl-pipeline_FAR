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
PURCHASE_DOMAIN = "purchases"


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

# =====================================================
# CANONICAL PURCHASE WANSOFT ETL
# =====================================================
# Source:
#   getinputinventory_entrada
#
# Business rule:
#   TipoEntrada = 'Factura'
#
# Purpose:
#   Load Wansoft purchase-like inventory inputs into the
#   canonical purchase layer with source_system = 'wansoft'.
#
# Important:
#   This block preserves existing source_system = 'odoo'
#   rows in canonical_purchase_* tables.
# =====================================================

import hashlib
import pandas as pd

from core.database.mysql import get_mysql_connection as get_db_connection
from core.config.companies import (
    get_company_source_key,
    get_domain_company_source,
    should_include_company_in_final_domain,
)

from extract.purchases.odoo_purchase_etl import (
    sql_safe,
    execute_many_in_batches,
)


try:
    from core.config.companies import WANSOFT_SUBSIDIARY_SOURCE_KEY
except ImportError:
    WANSOFT_SUBSIDIARY_SOURCE_KEY = {}


SOURCE_SYSTEM_WANSOFT = "wansoft"
PURCHASE_DOMAIN = "purchases"


def normalize_wansoft_text(value):
    """
    Normalizes text values coming from Wansoft.
    """
    if value is None:
        return None

    if pd.isna(value):
        return None

    text = str(value).strip()

    if not text:
        return None

    return text


def stable_wansoft_hash(*values):
    """
    Creates a stable hash for fallback source identifiers.
    """
    raw = "|".join([str(v) if v is not None else "" for v in values])
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def resolve_wansoft_company_source_key(subsidiary_name):
    """
    Resolves a Wansoft subsidiary identifier/name to COMPANY_SOURCE key.

    Priority:
    1. WANSOFT_SUBSIDIARY_SOURCE_KEY derived from CUENTAS_SUCURSALES
    2. get_company_source_key fallback

    Example:
        4960 -> Antenas
        6175 -> Cancun
    """
    normalized = normalize_wansoft_text(subsidiary_name)

    if normalized is None:
        return None

    if normalized in WANSOFT_SUBSIDIARY_SOURCE_KEY:
        return WANSOFT_SUBSIDIARY_SOURCE_KEY[normalized]

    return get_company_source_key(normalized)


def load_wansoft_operational_start_dates():
    """
    Loads operational_start_date by COMPANY_SOURCE key from
    odoo_company_migration_policy.

    This is only used to preserve Wansoft history before Odoo becomes
    the official source for a company.

    Example:
        Antenas is source = odoo.
        Wansoft rows before Antenas operational_start_date are preserved.
        Wansoft rows from operational_start_date onward are excluded.
    """
    conn = get_db_connection(target="wansoft")

    query = """
    SELECT
        company_name,
        operational_start_date
    FROM odoo_company_migration_policy
    WHERE is_active = 1
      AND operational_start_date IS NOT NULL
    """

    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        return {}

    df["company_source_key"] = df["company_name"].apply(get_company_source_key)
    df["operational_start_date"] = pd.to_datetime(
        df["operational_start_date"],
        errors="coerce"
    )

    result = {}

    for _, row in df.dropna(subset=["company_source_key", "operational_start_date"]).iterrows():
        key = row["company_source_key"]
        date_value = row["operational_start_date"]

        if key not in result:
            result[key] = date_value
        else:
            result[key] = min(result[key], date_value)

    return result


def load_wansoft_input_inventory_facturas():
    """
    Loads Wansoft purchase-like inventory inputs.

    Source table:
        getinputinventory_entrada

    Filter:
        TipoEntrada = 'Factura'

    FechaEntrada is used as the operational purchase/input date.
    FechaReal is preserved as reference date for Wansoft upload/capture timing.
    """
    conn = get_db_connection(target="wansoft")

    query = """
    SELECT
        id,
        subsidiary_name,
        IdEntrada,
        ClaveAlmacen,
        Almacen,
        IdAlmacen,
        CodigoDepartamento,
        Departamento,
        IdProducto,
        CodigoProducto,
        NombreProducto,
        CodigoUnidadDeMedida,
        IdUnidadDeMedida,
        UnidadDeMedida,
        TipoEntrada,
        Cantidad,
        CostoUnitario,
        ProductoConIVA,
        FechaEntrada,
        Factura,
        FechaFactura,
        RFCProveedor,
        ClaveProveedor,
        NombreProveedor,
        IdOrdenCompra,
        FolioOrdenCompra,
        RFCProveedorOrdenCompra,
        ProveedorOrdenCompra,
        IdDocumento,
        IdUsuario,
        NombreUsuario,
        FechaReal,
        created_at
    FROM getinputinventory_entrada
    WHERE TipoEntrada = 'Factura'
    """

    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        return df

    df["FechaEntrada"] = pd.to_datetime(df["FechaEntrada"], errors="coerce")
    df["FechaReal"] = pd.to_datetime(df["FechaReal"], errors="coerce")
    df["FechaFactura"] = pd.to_datetime(df["FechaFactura"], errors="coerce")

    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)
    df["CostoUnitario"] = pd.to_numeric(df["CostoUnitario"], errors="coerce").fillna(0)

    df["line_amount"] = df["Cantidad"] * df["CostoUnitario"]

    return df


def apply_wansoft_purchase_source_flags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies COMPANY_SOURCE governance to Wansoft rows.

    Rules:
    - If domain source = wansoft:
        include as final_wansoft_enabled

    - If domain source = odoo:
        include only before operational_start_date as wansoft_history_before_odoo

    - If company is internal provider:
        exclude as final company

    - If mapping cannot resolve the company:
        mark as unknown_source_review and exclude from final load
    """
    if df is None or df.empty:
        return df

    out = df.copy()

    operational_start_dates = load_wansoft_operational_start_dates()

    out["company_source_key"] = out["subsidiary_name"].apply(
        resolve_wansoft_company_source_key
    )

    out["company_name"] = out["company_source_key"]
    out.loc[out["company_name"].isna(), "company_name"] = out["subsidiary_name"]

    out["domain_source"] = out["company_source_key"].apply(
        lambda x: get_domain_company_source(x, PURCHASE_DOMAIN) if pd.notna(x) else "unknown"
    )

    out["include_final_company"] = out["company_source_key"].apply(
        lambda x: should_include_company_in_final_domain(x, PURCHASE_DOMAIN) if pd.notna(x) else False
    )

    out["operational_start_date"] = out["company_source_key"].apply(
        lambda x: operational_start_dates.get(x)
    )

    def classify(row):
        if not row.get("include_final_company"):
            return "exclude_internal_provider"

        if pd.isna(row.get("company_source_key")):
            return "unknown_source_review"

        if row.get("domain_source") == "wansoft":
            return "final_wansoft_enabled"

        if row.get("domain_source") == "odoo":
            start_date = row.get("operational_start_date")
            fecha_entrada = row.get("FechaEntrada")

            if pd.isna(start_date):
                return "odoo_source_missing_cutoff_review"

            if pd.isna(fecha_entrada):
                return "missing_date_review"

            if fecha_entrada < start_date:
                return "wansoft_history_before_odoo"

            return "exclude_after_odoo_start"

        return "unknown_source_review"

    out["final_purchase_source_status"] = out.apply(classify, axis=1)

    return out


def filter_wansoft_final_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Keeps only Wansoft rows that should feed the final canonical purchase layer.
    """
    if df is None or df.empty:
        return df

    keep_statuses = {
        "final_wansoft_enabled",
        "wansoft_history_before_odoo",
    }

    return df[df["final_purchase_source_status"].isin(keep_statuses)].copy()

def normalize_wansoft_key_part(value):
    """
    Normalizes values used to build technical Wansoft source keys.

    This avoids MySQL unique-key collisions caused by:
    - case-insensitive collations
    - trailing spaces
    - inconsistent invoice casing
    - long natural keys
    """
    text = normalize_wansoft_text(value)

    if text is None:
        return "na"

    return text.strip().lower()

def wansoft_source_document_id(row):
    """
    Builds a stable, short, MySQL-safe source_order_id for Wansoft documents.

    Important:
    We do NOT use the raw invoice/RFC/date directly as the full source_order_id
    because MySQL VARCHAR unique keys may compare values case-insensitively
    or ignore trailing spaces depending on collation.

    Natural business values remain available in:
    - purchase_order_name
    - vendor_id
    - vendor_name
    """

    company_key = normalize_wansoft_key_part(row.get("company_source_key"))
    factura = normalize_wansoft_key_part(row.get("Factura"))
    rfc = normalize_wansoft_key_part(row.get("RFCProveedor"))
    proveedor = normalize_wansoft_key_part(row.get("NombreProveedor"))
    fecha = row.get("FechaEntrada")

    if not pd.isna(fecha):
        fecha_key = pd.to_datetime(fecha).strftime("%Y-%m-%d")
    else:
        fecha_key = "no_date"

    natural_key = "|".join([
        company_key,
        factura,
        rfc,
        proveedor,
        fecha_key,
    ])

    digest = stable_wansoft_hash(natural_key)[:16]

    return f"wansoft_order:{company_key}:{fecha_key}:{digest}"


def wansoft_source_line_id(row):
    """
    Builds a stable source_order_line_id for Wansoft rows.
    """
    row_id = normalize_wansoft_text(row.get("id"))

    if row_id:
        return f"wansoft_line:{row_id}"

    fallback = stable_wansoft_hash(
        row.get("company_source_key"),
        row.get("Factura"),
        row.get("RFCProveedor"),
        row.get("CodigoProducto"),
        row.get("Cantidad"),
        row.get("CostoUnitario"),
        row.get("FechaEntrada"),
    )

    return f"wansoft_line:{fallback}"


def wansoft_source_receipt_id(row):
    """
    Builds a stable, short, MySQL-safe source_receipt_id for Wansoft receipts.

    This follows the same natural document identity as source_order_id,
    but uses a different prefix to keep receipt and order IDs distinct.
    """

    company_key = normalize_wansoft_key_part(row.get("company_source_key"))
    factura = normalize_wansoft_key_part(row.get("Factura"))
    rfc = normalize_wansoft_key_part(row.get("RFCProveedor"))
    proveedor = normalize_wansoft_key_part(row.get("NombreProveedor"))
    fecha = row.get("FechaEntrada")

    if not pd.isna(fecha):
        fecha_key = pd.to_datetime(fecha).strftime("%Y-%m-%d")
    else:
        fecha_key = "no_date"

    natural_key = "|".join([
        company_key,
        factura,
        rfc,
        proveedor,
        fecha_key,
    ])

    digest = stable_wansoft_hash(natural_key)[:16]

    return f"wansoft_receipt:{company_key}:{fecha_key}:{digest}"


def wansoft_source_move_id(row):
    """
    Builds a stable source_stock_move_id for Wansoft receipt movements.
    """
    row_id = normalize_wansoft_text(row.get("id"))

    if row_id:
        return f"wansoft_move:{row_id}"

    fallback = stable_wansoft_hash(
        row.get("company_source_key"),
        row.get("IdEntrada"),
        row.get("Factura"),
        row.get("RFCProveedor"),
        row.get("CodigoProducto"),
        row.get("Cantidad"),
        row.get("CostoUnitario"),
        row.get("FechaEntrada"),
    )

    return f"wansoft_move:{fallback}"


def build_wansoft_canonical_base():
    """
    Loads Wansoft Factura rows and applies final source governance.
    """
    df_raw = load_wansoft_input_inventory_facturas()
    df_flagged = apply_wansoft_purchase_source_flags(df_raw)
    df_final = filter_wansoft_final_rows(df_flagged)

    if df_final is None or df_final.empty:
        return df_final

    df_final["source_order_id"] = df_final.apply(
        wansoft_source_document_id,
        axis=1
    )

    df_final["source_order_line_id"] = df_final.apply(
        wansoft_source_line_id,
        axis=1
    )

    df_final["source_receipt_id"] = df_final.apply(
        wansoft_source_receipt_id,
        axis=1
    )

    df_final["source_stock_move_id"] = df_final.apply(
        wansoft_source_move_id,
        axis=1
    )

    return df_final


def build_wansoft_canonical_orders(df_base: pd.DataFrame) -> pd.DataFrame:
    """
    Builds derived purchase order headers from Wansoft input inventory invoices.

    Important:
    Wansoft input inventory has one row per product movement/line.
    Multiple rows can share the same factura/RFC/date combination.

    Therefore, canonical order headers must be grouped only by the stable
    source_order_id, not by FechaEntrada or FechaReal, otherwise duplicate
    source_order_id values can be created.
    """
    if df_base is None or df_base.empty:
        return pd.DataFrame()

    df = (
        df_base.groupby(
            ["source_order_id"],
            dropna=False
        )
        .agg(
            Factura=("Factura", "max"),
            RFCProveedor=("RFCProveedor", "max"),
            ClaveProveedor=("ClaveProveedor", "max"),
            NombreProveedor=("NombreProveedor", "max"),
            subsidiary_name=("subsidiary_name", "max"),
            company_name=("company_name", "max"),
            company_source_key=("company_source_key", "max"),
            final_purchase_source_status=("final_purchase_source_status", "max"),
            FechaEntrada=("FechaEntrada", "min"),
            FechaReal=("FechaReal", "max"),
            amount_total=("line_amount", "sum"),
            picking_count=("source_receipt_id", "nunique"),
            total_lines=("source_order_line_id", "nunique"),
        )
        .reset_index()
    )

    return df


def build_wansoft_canonical_receipts(df_base: pd.DataFrame) -> pd.DataFrame:
    """
    Builds derived receipt headers from Wansoft input inventory invoices.

    Receipt headers are grouped by source_receipt_id.

    Since source_receipt_id is derived from the same document identity as
    source_order_id, this prevents duplicate receipt headers while preserving
    all movement-level detail in canonical_purchase_receipt_move_snapshot.
    """
    if df_base is None or df_base.empty:
        return pd.DataFrame()

    df = (
        df_base.groupby(
            ["source_receipt_id"],
            dropna=False
        )
        .agg(
            source_order_id=("source_order_id", "max"),
            Factura=("Factura", "max"),
            RFCProveedor=("RFCProveedor", "max"),
            ClaveProveedor=("ClaveProveedor", "max"),
            NombreProveedor=("NombreProveedor", "max"),
            subsidiary_name=("subsidiary_name", "max"),
            company_name=("company_name", "max"),
            company_source_key=("company_source_key", "max"),
            final_purchase_source_status=("final_purchase_source_status", "max"),
            FechaEntrada=("FechaEntrada", "min"),
            FechaReal=("FechaReal", "max"),
            move_count=("source_stock_move_id", "nunique"),
            move_line_count=("source_stock_move_id", "nunique"),
        )
        .reset_index()
    )

    return df


def delete_existing_wansoft_rows(table_name: str):
    """
    Deletes only Wansoft rows from a canonical table.

    Existing source_system = 'odoo' rows are preserved.
    """
    conn = get_db_connection(target="wansoft")
    cursor = conn.cursor()

    cursor.execute(
        f"""
        DELETE FROM {table_name}
        WHERE source_system = %s
        """,
        (SOURCE_SYSTEM_WANSOFT,)
    )

    conn.commit()
    cursor.close()
    conn.close()

def ensure_unique_wansoft_orders_for_insert(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensures one row per source_order_id before inserting into
    canonical_purchase_order_snapshot.

    Uses a normalized MySQL comparison key to catch differences that
    Pandas may treat as unique but MySQL may treat as equal.
    """
    if df is None or df.empty:
        return df

    required_col = "source_order_id"

    if required_col not in df.columns:
        raise ValueError("source_order_id column is required for Wansoft order insert.")

    df = df.copy()

    df["source_order_id_mysql_key"] = (
        df["source_order_id"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    grouped = (
        df.groupby(["source_order_id_mysql_key"], dropna=False)
        .agg(
            source_order_id=("source_order_id_mysql_key", "max"),
            Factura=("Factura", "max"),
            RFCProveedor=("RFCProveedor", "max"),
            ClaveProveedor=("ClaveProveedor", "max"),
            NombreProveedor=("NombreProveedor", "max"),
            subsidiary_name=("subsidiary_name", "max"),
            company_name=("company_name", "max"),
            company_source_key=("company_source_key", "max"),
            final_purchase_source_status=("final_purchase_source_status", "max"),
            FechaEntrada=("FechaEntrada", "min"),
            FechaReal=("FechaReal", "max"),
            amount_total=("amount_total", "sum"),
            picking_count=("picking_count", "max"),
        )
        .reset_index(drop=True)
    )

    duplicated = grouped[grouped.duplicated(subset=["source_order_id"], keep=False)]

    if not duplicated.empty:
        print("\n--- DUPLICATED WANSOFT ORDER IDS BEFORE INSERT ---")
        print(duplicated.head(20).to_string(index=False))
        raise ValueError("Duplicated source_order_id values remain before canonical order insert.")

    return grouped

def save_wansoft_canonical_orders(df: pd.DataFrame):
    table_name = "canonical_purchase_order_snapshot"

    delete_existing_wansoft_rows(table_name)

    if df is None or df.empty:
        print("No hay órdenes Wansoft elegibles para capa canónica.")
        return 0

    df = ensure_unique_wansoft_orders_for_insert(df)

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
            SOURCE_SYSTEM_WANSOFT,
            "wansoft_input_inventory_derived_purchase_order",
            sql_safe(row.get("source_order_id")),
            sql_safe(row.get("Factura")),
            sql_safe(row.get("RFCProveedor") or row.get("ClaveProveedor")),
            sql_safe(row.get("NombreProveedor")),
            sql_safe(row.get("subsidiary_name")),
            sql_safe(row.get("company_name")),
            sql_safe(row.get("company_source_key")),
            sql_safe(row.get("final_purchase_source_status")),
            None,
            "wansoft",
            0,
            None,
            "company_source",
            sql_safe(row.get("FechaEntrada")),
            sql_safe(row.get("FechaReal")),
            "done",
            "invoiced",
            sql_safe(row.get("amount_total")),
            None,
            sql_safe(row.get("amount_total")),
            None,
            "MXN",
            sql_safe(row.get("picking_count")),
        ))

    execute_many_in_batches(cursor, insert_sql, rows)
    conn.commit()

    inserted = len(rows)

    cursor.close()
    conn.close()

    print(f"Insertados {inserted} registros Wansoft en {table_name}.")
    return inserted


def save_wansoft_canonical_lines(df: pd.DataFrame):
    table_name = "canonical_purchase_order_line_snapshot"
    delete_existing_wansoft_rows(table_name)

    if df is None or df.empty:
        print("No hay líneas Wansoft elegibles para capa canónica.")
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
            SOURCE_SYSTEM_WANSOFT,
            "wansoft_input_inventory_derived_purchase_line",
            sql_safe(row.get("source_order_line_id")),
            sql_safe(row.get("source_order_id")),
            sql_safe(row.get("Factura")),
            sql_safe(row.get("RFCProveedor") or row.get("ClaveProveedor")),
            sql_safe(row.get("NombreProveedor")),
            sql_safe(row.get("subsidiary_name")),
            sql_safe(row.get("company_name")),
            sql_safe(row.get("company_source_key")),
            sql_safe(row.get("final_purchase_source_status")),
            None,
            "wansoft",
            0,
            None,
            "company_source",
            sql_safe(row.get("IdProducto")),
            sql_safe(row.get("NombreProducto")),
            sql_safe(row.get("CodigoProducto")),
            sql_safe(row.get("NombreProducto")),
            sql_safe(row.get("Departamento")),
            1,
            "native_wansoft",
            "getinputinventory_entrada",
            "product_line",
            "mapped_wansoft_inventory",
            "mapped_wansoft_native",
            "wansoft_native_code",
            sql_safe(row.get("CodigoProducto")),
            sql_safe(row.get("Cantidad")),
            sql_safe(row.get("Cantidad")),
            None,
            sql_safe(row.get("CostoUnitario")),
            sql_safe(row.get("line_amount")),
            sql_safe(row.get("line_amount")),
            sql_safe(row.get("FechaEntrada")),
            "done",
        ))

    execute_many_in_batches(cursor, insert_sql, rows)
    conn.commit()

    inserted = len(rows)

    cursor.close()
    conn.close()

    print(f"Insertados {inserted} registros Wansoft en {table_name}.")
    return inserted

def ensure_unique_wansoft_receipts_for_insert(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensures one row per source_receipt_id before inserting into
    canonical_purchase_receipt_snapshot.

    Uses a normalized MySQL comparison key to avoid collation-related
    duplicate issues.
    """
    if df is None or df.empty:
        return df

    required_col = "source_receipt_id"

    if required_col not in df.columns:
        raise ValueError("source_receipt_id column is required for Wansoft receipt insert.")

    df = df.copy()

    df["source_receipt_id_mysql_key"] = (
        df["source_receipt_id"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    grouped = (
        df.groupby(["source_receipt_id_mysql_key"], dropna=False)
        .agg(
            source_receipt_id=("source_receipt_id_mysql_key", "max"),
            source_order_id=("source_order_id", "max"),
            Factura=("Factura", "max"),
            RFCProveedor=("RFCProveedor", "max"),
            ClaveProveedor=("ClaveProveedor", "max"),
            NombreProveedor=("NombreProveedor", "max"),
            subsidiary_name=("subsidiary_name", "max"),
            company_name=("company_name", "max"),
            company_source_key=("company_source_key", "max"),
            final_purchase_source_status=("final_purchase_source_status", "max"),
            FechaEntrada=("FechaEntrada", "min"),
            FechaReal=("FechaReal", "max"),
            move_count=("move_count", "max"),
            move_line_count=("move_line_count", "max"),
        )
        .reset_index(drop=True)
    )

    duplicated = grouped[grouped.duplicated(subset=["source_receipt_id"], keep=False)]

    if not duplicated.empty:
        print("\n--- DUPLICATED WANSOFT RECEIPT IDS BEFORE INSERT ---")
        print(duplicated.head(20).to_string(index=False))
        raise ValueError("Duplicated source_receipt_id values remain before canonical receipt insert.")

    return grouped

def save_wansoft_canonical_receipts(df: pd.DataFrame):
    table_name = "canonical_purchase_receipt_snapshot"

    delete_existing_wansoft_rows(table_name)

    if df is None or df.empty:
        print("No hay recepciones Wansoft elegibles para capa canónica.")
        return 0

    df = ensure_unique_wansoft_receipts_for_insert(df)

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
            SOURCE_SYSTEM_WANSOFT,
            "wansoft_input_inventory_receipt",
            sql_safe(row.get("source_receipt_id")),
            sql_safe(row.get("Factura")),
            sql_safe(row.get("source_order_id")),
            sql_safe(row.get("RFCProveedor") or row.get("ClaveProveedor")),
            sql_safe(row.get("NombreProveedor")),
            sql_safe(row.get("subsidiary_name")),
            sql_safe(row.get("company_name")),
            sql_safe(row.get("company_source_key")),
            sql_safe(row.get("final_purchase_source_status")),
            None,
            "wansoft",
            0,
            None,
            "company_source",
            None,
            "Wansoft Input Inventory",
            "incoming",
            sql_safe(row.get("FechaEntrada")),
            sql_safe(row.get("FechaReal")),
            "done",
            sql_safe(row.get("move_count")),
            sql_safe(row.get("move_line_count")),
        ))

    execute_many_in_batches(cursor, insert_sql, rows)
    conn.commit()

    inserted = len(rows)

    cursor.close()
    conn.close()

    print(f"Insertados {inserted} registros Wansoft en {table_name}.")
    return inserted


def save_wansoft_canonical_receipt_moves(df: pd.DataFrame):
    table_name = "canonical_purchase_receipt_move_snapshot"
    delete_existing_wansoft_rows(table_name)

    if df is None or df.empty:
        print("No hay movimientos Wansoft elegibles para capa canónica.")
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
            SOURCE_SYSTEM_WANSOFT,
            "wansoft_input_inventory_receipt_move",
            sql_safe(row.get("source_stock_move_id")),
            sql_safe(row.get("Factura")),
            sql_safe(row.get("source_order_id")),
            sql_safe(row.get("source_receipt_id")),
            sql_safe(row.get("Factura")),
            sql_safe(row.get("source_order_line_id")),
            sql_safe(row.get("NombreProducto")),
            sql_safe(row.get("IdProducto")),
            sql_safe(row.get("NombreProducto")),
            sql_safe(row.get("CodigoProducto")),
            sql_safe(row.get("NombreProducto")),
            sql_safe(row.get("Departamento")),
            sql_safe(row.get("Cantidad")),
            sql_safe(row.get("Cantidad")),
            sql_safe(row.get("IdUnidadDeMedida")),
            sql_safe(row.get("UnidadDeMedida")),
            sql_safe(row.get("subsidiary_name")),
            sql_safe(row.get("company_name")),
            sql_safe(row.get("company_source_key")),
            sql_safe(row.get("final_purchase_source_status")),
            None,
            "wansoft",
            0,
            None,
            "company_source",
            "done",
            sql_safe(row.get("FechaEntrada")),
            sql_safe(row.get("FechaReal")),
        ))

    execute_many_in_batches(cursor, insert_sql, rows)
    conn.commit()

    inserted = len(rows)

    cursor.close()
    conn.close()

    print(f"Insertados {inserted} registros Wansoft en {table_name}.")
    return inserted


def run_canonical_purchase_wansoft_etl():
    """
    Loads Wansoft purchase-like records from getinputinventory_entrada
    into the canonical purchase layer.

    This function preserves existing source_system = 'odoo' rows.
    """
    print("=== CANONICAL PURCHASE WANSOFT ETL START ===")

    df_base = build_wansoft_canonical_base()

    if df_base is None or df_base.empty:
        print("No hay filas Wansoft elegibles para capa canónica.")
        return {
            "orders_inserted": 0,
            "lines_inserted": 0,
            "receipts_inserted": 0,
            "receipt_moves_inserted": 0,
        }

    df_orders = build_wansoft_canonical_orders(df_base)
    df_receipts = build_wansoft_canonical_receipts(df_base)

    print("\n--- CANONICAL WANSOFT ELIGIBLE SUMMARY ---")
    print(f"base_lines_eligible: {len(df_base)}")
    print(f"orders_derived: {len(df_orders)}")
    print(f"receipts_derived: {len(df_receipts)}")
    print(f"receipt_moves_eligible: {len(df_base)}")

    print("\n--- WANSOFT FINAL STATUS SUMMARY ---")
    status_summary = (
        df_base["final_purchase_source_status"]
        .value_counts(dropna=False)
        .reset_index()
    )
    status_summary.columns = ["final_purchase_source_status", "count"]
    print(status_summary.to_string(index=False))

    print("\n--- WANSOFT COMPANY SUMMARY ---")
    company_summary = (
        df_base.groupby(
            ["company_source_key", "final_purchase_source_status"],
            dropna=False
        )
        .size()
        .reset_index(name="rows_count")
        .sort_values(["rows_count"], ascending=False)
    )
    print(company_summary.to_string(index=False))

    inserted_orders = save_wansoft_canonical_orders(df_orders)
    inserted_lines = save_wansoft_canonical_lines(df_base)
    inserted_receipts = save_wansoft_canonical_receipts(df_receipts)
    inserted_moves = save_wansoft_canonical_receipt_moves(df_base)

    print("\n--- CANONICAL WANSOFT LOAD COUNTS ---")
    print(f"orders_inserted: {inserted_orders}")
    print(f"lines_inserted: {inserted_lines}")
    print(f"receipts_inserted: {inserted_receipts}")
    print(f"receipt_moves_inserted: {inserted_moves}")

    print("=== CANONICAL PURCHASE WANSOFT ETL END ✅ ===")

    return {
        "orders_inserted": inserted_orders,
        "lines_inserted": inserted_lines,
        "receipts_inserted": inserted_receipts,
        "receipt_moves_inserted": inserted_moves,
    }