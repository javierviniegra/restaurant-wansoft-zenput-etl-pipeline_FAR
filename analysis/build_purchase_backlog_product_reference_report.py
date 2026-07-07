import pandas as pd

from core.database.mysql import get_mysql_connection as get_db_connection
from core.database.odoo import get_odoo_connection


def safe_many2one_id(value):
    if isinstance(value, list) and len(value) >= 1:
        return value[0]
    return None


def safe_many2one_name(value):
    if isinstance(value, list) and len(value) >= 2:
        return value[1]
    return None


def normalize_odoo_reference(value):
    """
    Normaliza referencias Odoo.

    Odoo suele devolver False cuando default_code está vacío.
    Para nuestra política, False no es una referencia válida.
    """
    if value is None:
        return None

    if value is False:
        return None

    if pd.isna(value):
        return None

    text = str(value).strip()

    if text == "":
        return None

    if text.lower() in {"false", "none", "nan", "null"}:
        return None

    return text


def has_valid_odoo_reference(value):
    """
    Determina si el producto tiene una referencia Odoo usable.
    """
    return normalize_odoo_reference(value) is not None


def get_available_fields(models, db, uid, password, model_name):
    fields_meta = models.execute_kw(
        db,
        uid,
        password,
        model_name,
        "fields_get",
        [],
        {"attributes": ["type"]}
    )
    return set(fields_meta.keys())


def load_purchase_inventory_mapping_backlog():
    """
    Loads the deduplicated purchase inventory mapping backlog from MySQL.
    """
    conn = get_db_connection(target="wansoft")

    query = """
    SELECT
        product_id,
        product_name,
        total_lines,
        unique_vendors,
        unique_companies,
        total_qty,
        total_received,
        total_amount,
        first_order_date,
        last_order_date,
        suggested_action,
        backlog_status
    FROM odoo_purchase_inventory_mapping_backlog
    WHERE backlog_status = 'open'
    ORDER BY total_amount DESC
    """

    df = pd.read_sql(query, conn)
    conn.close()

    return df


def extract_odoo_product_reference_metadata(product_ids, batch_size=500):
    """
    Extracts product reference metadata from Odoo product.product.

    Fields:
    - default_code: Odoo internal reference
    - barcode: barcode if available
    - display_name: Odoo display name
    - categ_id: Odoo category
    """
    if not product_ids:
        return pd.DataFrame(columns=[
            "product_id",
            "odoo_product_name",
            "odoo_display_name",
            "odoo_default_code",
            "odoo_barcode",
            "odoo_category_id",
            "odoo_category_name",
        ])

    uid, models, db, password = get_odoo_connection()

    model_name = "product.product"
    available_fields = get_available_fields(models, db, uid, password, model_name)

    desired_fields = [
        "id",
        "name",
        "display_name",
        "default_code",
        "barcode",
        "categ_id",
    ]

    fields = [f for f in desired_fields if f in available_fields]

    rows = []

    product_ids = [int(x) for x in product_ids if pd.notna(x)]

    for start in range(0, len(product_ids), batch_size):
        batch_ids = product_ids[start:start + batch_size]

        batch_rows = models.execute_kw(
            db,
            uid,
            password,
            model_name,
            "search_read",
            [[["id", "in", batch_ids]]],
            {"fields": fields}
        )

        rows.extend(batch_rows)

    df = pd.DataFrame(rows)

    output_columns = [
        "product_id",
        "odoo_product_name",
        "odoo_display_name",
        "odoo_default_code",
        "odoo_barcode",
        "odoo_category_id",
        "odoo_category_name",
    ]

    if df.empty:
        return pd.DataFrame(columns=output_columns)

    for col in desired_fields:
        if col not in df.columns:
            df[col] = None

    result = pd.DataFrame()

    result["product_id"] = df["id"]
    result["odoo_product_name"] = df["name"]
    result["odoo_display_name"] = df["display_name"]

    result["odoo_default_code"] = df["default_code"].apply(normalize_odoo_reference)
    result["odoo_barcode"] = df["barcode"].apply(normalize_odoo_reference)

    result["odoo_category_id"] = df["categ_id"].apply(safe_many2one_id)
    result["odoo_category_name"] = df["categ_id"].apply(safe_many2one_name)

    return result[output_columns]


def build_purchase_backlog_product_reference_report():
    """
    Builds a report joining purchase inventory backlog with Odoo product references.
    """
    df_backlog = load_purchase_inventory_mapping_backlog()

    if df_backlog.empty:
        return pd.DataFrame()

    product_ids = df_backlog["product_id"].dropna().astype(int).unique().tolist()

    df_refs = extract_odoo_product_reference_metadata(product_ids)

    df = df_backlog.merge(
        df_refs,
        on="product_id",
        how="left"
    )

    df["has_odoo_default_code"] = df["odoo_default_code"].apply(has_valid_odoo_reference)

    df["reference_review_bucket"] = df["has_odoo_default_code"].apply(
        lambda x: "has_reference_candidate" if x else "new_product_no_reference"
    )

    return df


def summarize_purchase_backlog_product_reference_report(df: pd.DataFrame):
    """
    Summarizes backlog products by reference availability.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=[
            "reference_review_bucket",
            "unique_products",
            "total_lines",
            "total_amount"
        ])

    summary = (
        df.groupby("reference_review_bucket", dropna=False)
        .agg(
            unique_products=("product_id", "nunique"),
            total_lines=("total_lines", "sum"),
            total_amount=("total_amount", "sum")
        )
        .reset_index()
        .sort_values("total_amount", ascending=False)
    )

    return summary