import pandas as pd
from core.database.odoo import get_odoo_connection


def extract_odoo_products():
    """
    Extrae catálogo de productos desde Odoo.
    Prioriza x_wansoft_code sobre default_code como llave de integración.
    """

    uid, models, db, password = get_odoo_connection()

    base_fields = [
        "id",
        "name",
        "default_code",
        "sale_ok",
        "purchase_ok",
        "categ_id"
    ]

    custom_fields = [
        "x_wansoft_code",
        "x_wansoft_platillo_id"
    ]

    try:
        rows = models.execute_kw(
            db,
            uid,
            password,
            "product.product",
            "search_read",
            [[]],
            {"fields": base_fields + custom_fields}
        )
    except Exception:
        rows = models.execute_kw(
            db,
            uid,
            password,
            "product.product",
            "search_read",
            [[]],
            {"fields": base_fields}
        )

    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(columns=[
            "odoo_product_id",
            "product_name",
            "default_code",
            "x_wansoft_code",
            "x_wansoft_platillo_id",
            "integration_code",
            "sale_ok",
            "purchase_ok",
            "category_id_only",
            "category_name"
        ])

    # categoría
    if "categ_id" in df.columns:
        df["category_id_only"] = df["categ_id"].apply(lambda x: x[0] if x else None)
        df["category_name"] = df["categ_id"].apply(lambda x: x[1] if x else None)
    else:
        df["category_id_only"] = None
        df["category_name"] = None

    df = df.rename(columns={
        "id": "odoo_product_id",
        "name": "product_name"
    })

    if "x_wansoft_code" not in df.columns:
        df["x_wansoft_code"] = None
    if "x_wansoft_platillo_id" not in df.columns:
        df["x_wansoft_platillo_id"] = None
    if "default_code" not in df.columns:
        df["default_code"] = None

    def clean_code(x):
        if x in [False, None, "", "False"]:
            return None
        return str(x).strip()

    df["default_code"] = df["default_code"].apply(clean_code)
    df["x_wansoft_code"] = df["x_wansoft_code"].apply(clean_code)

    # Llave oficial de integración
    df["integration_code"] = df["x_wansoft_code"].combine_first(df["default_code"])

    df["product_name"] = df["product_name"].astype(str).str.strip()
    df["sale_ok"] = df["sale_ok"].fillna(False).astype(bool)
    df["purchase_ok"] = df["purchase_ok"].fillna(False).astype(bool)

    return df[[
        "odoo_product_id",
        "product_name",
        "default_code",
        "x_wansoft_code",
        "x_wansoft_platillo_id",
        "integration_code",
        "sale_ok",
        "purchase_ok",
        "category_id_only",
        "category_name"
    ]]