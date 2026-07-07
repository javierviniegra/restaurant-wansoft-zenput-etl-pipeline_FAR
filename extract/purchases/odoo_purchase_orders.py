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


def extract_odoo_purchase_orders():
    """
    Extracts purchase.order headers from Odoo.

    This extractor is read-only.
    It does not modify Odoo.
    """

    uid, models, db, password = get_odoo_connection()

    model_name = "purchase.order"
    available_fields = get_available_fields(models, db, uid, password, model_name)

    desired_fields = [
        "id",
        "name",
        "partner_id",
        "company_id",
        "date_order",
        "date_approve",
        "state",
        "invoice_status",
        "amount_untaxed",
        "amount_tax",
        "amount_total",
        "currency_id",
        "picking_count",
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
        "odoo_purchase_order_id",
        "purchase_order_name",
        "vendor_id",
        "vendor_name",
        "company_id",
        "company_name",
        "order_date",
        "approval_date",
        "state",
        "invoice_status",
        "amount_untaxed",
        "amount_tax",
        "amount_total",
        "currency_id",
        "currency_name",
        "picking_count",
    ]

    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(columns=output_columns)

    for col in desired_fields:
        if col not in df.columns:
            df[col] = None

    result = pd.DataFrame()

    result["odoo_purchase_order_id"] = df["id"]
    result["purchase_order_name"] = df["name"]

    result["vendor_id"] = df["partner_id"].apply(safe_many2one_id)
    result["vendor_name"] = df["partner_id"].apply(safe_many2one_name)

    result["company_id"] = df["company_id"].apply(safe_many2one_id)
    result["company_name"] = df["company_id"].apply(safe_many2one_name)

    result["order_date"] = df["date_order"]
    result["approval_date"] = df["date_approve"]

    result["state"] = df["state"]
    result["invoice_status"] = df["invoice_status"]

    result["amount_untaxed"] = df["amount_untaxed"]
    result["amount_tax"] = df["amount_tax"]
    result["amount_total"] = df["amount_total"]

    result["currency_id"] = df["currency_id"].apply(safe_many2one_id)
    result["currency_name"] = df["currency_id"].apply(safe_many2one_name)

    result["picking_count"] = df["picking_count"]

    return result[output_columns]