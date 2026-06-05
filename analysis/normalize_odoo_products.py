import pandas as pd


def normalize_odoo_products(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza catálogo Odoo a una estructura estándar.
    """

    if df is None or df.empty:
        return pd.DataFrame(columns=[
            "source_system",
            "odoo_product_id",
            "odoo_code",
            "product_name",
            "sale_ok",
            "purchase_ok",
            "category_id_only",
            "category_name"
        ])

    out = df.copy()

    out["source_system"] = "odoo"

    # limpiar nombres
    out["product_name"] = out["product_name"].astype(str).str.strip()

    # limpiar códigos
    out["odoo_code"] = out["odoo_code"].apply(
        lambda x: None if pd.isna(x) or x in [False, "", "False"] else str(x).strip()
    )

    cols = [
        "source_system",
        "odoo_product_id",
        "odoo_code",
        "product_name",
        "sale_ok",
        "purchase_ok",
        "category_id_only",
        "category_name"
    ]

    return out[cols]