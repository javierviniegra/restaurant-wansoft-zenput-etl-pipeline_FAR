import pandas as pd
from core.database.odoo import get_odoo_connection


def safe_many2one_id(value):
    if isinstance(value, list) and len(value) >= 1:
        return value[0]
    return None


def safe_many2one_name(value):
    if isinstance(value, list) and len(value) >= 2:
        return value[1]
    return None


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


def extract_odoo_purchase_order_lines():
    """
    Extracts purchase.order.line records from Odoo.

    This extractor is read-only.
    It does not modify Odoo.
    """

    uid, models, db, password = get_odoo_connection()

    model_name = "purchase.order.line"
    available_fields = get_available_fields(models, db, uid, password, model_name)

    desired_fields = [
        "id",
        "order_id",
        "partner_id",
        "product_id",
        "product_qty",
        "qty_received",
        "qty_invoiced",
        "price_unit",
        "price_subtotal",
        "price_total",
        "company_id",
        "date_order",
        "state",
    ]

    fields = [f for f in desired_fields if f in available_fields]

    rows = models.execute_kw(
        db,
        uid,
        password,
        model_name,
        "search_read",
        [[]],
        {"fields": fields}
    )

    output_columns = [
        "odoo_purchase_order_line_id",
        "odoo_purchase_order_id",
        "purchase_order_name",
        "vendor_id",
        "vendor_name",
        "product_id",
        "product_name",
        "product_qty",
        "qty_received",
        "qty_invoiced",
        "price_unit",
        "price_subtotal",
        "price_total",
        "company_id",
        "company_name",
        "order_date",
        "state",
    ]

    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(columns=output_columns)

    for col in desired_fields:
        if col not in df.columns:
            df[col] = None

    result = pd.DataFrame()

    result["odoo_purchase_order_line_id"] = df["id"]

    result["odoo_purchase_order_id"] = df["order_id"].apply(safe_many2one_id)
    result["purchase_order_name"] = df["order_id"].apply(safe_many2one_name)

    result["vendor_id"] = df["partner_id"].apply(safe_many2one_id)
    result["vendor_name"] = df["partner_id"].apply(safe_many2one_name)

    result["product_id"] = df["product_id"].apply(safe_many2one_id)
    result["product_name"] = df["product_id"].apply(safe_many2one_name)

    result["product_qty"] = df["product_qty"]
    result["qty_received"] = df["qty_received"]
    result["qty_invoiced"] = df["qty_invoiced"]

    result["price_unit"] = df["price_unit"]
    result["price_subtotal"] = df["price_subtotal"]
    result["price_total"] = df["price_total"]

    result["company_id"] = df["company_id"].apply(safe_many2one_id)
    result["company_name"] = df["company_id"].apply(safe_many2one_name)

    result["order_date"] = df["date_order"]
    result["state"] = df["state"]

    return result[output_columns]