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


def extract_odoo_purchase_receipts():
    """
    Extracts incoming stock pickings related to receipts.

    This extractor is read-only.
    It does not modify Odoo.

    Primary model:
    - stock.picking

    Initial scope:
    - incoming receipts
    """

    uid, models, db, password = get_odoo_connection()

    model_name = "stock.picking"
    available_fields = get_available_fields(models, db, uid, password, model_name)

    desired_fields = [
        "id",
        "name",
        "origin",
        "partner_id",
        "company_id",
        "picking_type_id",
        "picking_type_code",
        "scheduled_date",
        "date_done",
        "state",
        "move_ids",
        "move_line_ids",
    ]

    fields = [f for f in desired_fields if f in available_fields]

    domain = []

    if "picking_type_code" in available_fields:
        domain = [["picking_type_code", "=", "incoming"]]

    rows = models.execute_kw(
        db,
        uid,
        password,
        model_name,
        "search_read",
        [domain],
        {"fields": fields}
    )

    output_columns = [
        "odoo_receipt_id",
        "receipt_name",
        "origin",
        "vendor_id",
        "vendor_name",
        "company_id",
        "company_name",
        "picking_type_id",
        "picking_type_name",
        "picking_type_code",
        "scheduled_date",
        "date_done",
        "state",
        "move_count",
        "move_line_count",
    ]

    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(columns=output_columns)

    for col in desired_fields:
        if col not in df.columns:
            df[col] = None

    result = pd.DataFrame()

    result["odoo_receipt_id"] = df["id"]
    result["receipt_name"] = df["name"]
    result["origin"] = df["origin"]

    result["vendor_id"] = df["partner_id"].apply(safe_many2one_id)
    result["vendor_name"] = df["partner_id"].apply(safe_many2one_name)

    result["company_id"] = df["company_id"].apply(safe_many2one_id)
    result["company_name"] = df["company_id"].apply(safe_many2one_name)

    result["picking_type_id"] = df["picking_type_id"].apply(safe_many2one_id)
    result["picking_type_name"] = df["picking_type_id"].apply(safe_many2one_name)

    result["picking_type_code"] = df["picking_type_code"]
    result["scheduled_date"] = df["scheduled_date"]
    result["date_done"] = df["date_done"]
    result["state"] = df["state"]

    result["move_count"] = df["move_ids"].apply(lambda x: len(x) if isinstance(x, list) else 0)
    result["move_line_count"] = df["move_line_ids"].apply(lambda x: len(x) if isinstance(x, list) else 0)

    return result[output_columns]


def extract_odoo_purchase_receipt_moves():
    """
    Extracts stock moves for incoming receipts.

    Primary model:
    - stock.move

    Initial scope:
    - incoming receipt-related moves when available
    """

    uid, models, db, password = get_odoo_connection()

    model_name = "stock.move"
    available_fields = get_available_fields(models, db, uid, password, model_name)

    desired_fields = [
        "id",
        "reference",
        "origin",
        "picking_id",
        "purchase_line_id",
        "product_id",
        "product_uom_qty",
        "quantity",
        "product_uom",
        "company_id",
        "state",
        "date",
        "date_deadline",
    ]

    fields = [f for f in desired_fields if f in available_fields]

    domain = []

    # If purchase_line_id exists, this is the cleanest first pass
    if "purchase_line_id" in available_fields:
        domain = [["purchase_line_id", "!=", False]]

    rows = models.execute_kw(
        db,
        uid,
        password,
        model_name,
        "search_read",
        [domain],
        {"fields": fields}
    )

    output_columns = [
        "odoo_stock_move_id",
        "reference",
        "origin",
        "odoo_receipt_id",
        "receipt_name",
        "odoo_purchase_order_line_id",
        "purchase_line_name",
        "product_id",
        "product_name",
        "product_uom_qty",
        "quantity",
        "product_uom_id",
        "product_uom_name",
        "company_id",
        "company_name",
        "state",
        "move_date",
        "date_deadline",
    ]

    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(columns=output_columns)

    for col in desired_fields:
        if col not in df.columns:
            df[col] = None

    result = pd.DataFrame()

    result["odoo_stock_move_id"] = df["id"]
    result["reference"] = df["reference"]
    result["origin"] = df["origin"]

    result["odoo_receipt_id"] = df["picking_id"].apply(safe_many2one_id)
    result["receipt_name"] = df["picking_id"].apply(safe_many2one_name)

    result["odoo_purchase_order_line_id"] = df["purchase_line_id"].apply(safe_many2one_id)
    result["purchase_line_name"] = df["purchase_line_id"].apply(safe_many2one_name)

    result["product_id"] = df["product_id"].apply(safe_many2one_id)
    result["product_name"] = df["product_id"].apply(safe_many2one_name)

    result["product_uom_qty"] = df["product_uom_qty"]

    if "quantity" in df.columns:
        result["quantity"] = df["quantity"]
    else:
        result["quantity"] = None

    result["product_uom_id"] = df["product_uom"].apply(safe_many2one_id)
    result["product_uom_name"] = df["product_uom"].apply(safe_many2one_name)

    result["company_id"] = df["company_id"].apply(safe_many2one_id)
    result["company_name"] = df["company_id"].apply(safe_many2one_name)

    result["state"] = df["state"]
    result["move_date"] = df["date"]
    result["date_deadline"] = df["date_deadline"]

    return result[output_columns]