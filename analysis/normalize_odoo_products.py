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

    # limpiar códigos -- integration_code ya prioriza x_wansoft_code (referencia
    # explícita) sobre default_code, per docs/purchases-product-mapping-policy.md.
    # extract_odoo_products() dejó de emitir una columna "odoo_code" cuando se
    # agregó soporte a x_wansoft_code; este normalizador nunca se actualizó,
    # por lo que build_product_mapping() truena con KeyError en cualquier
    # corrida actual (confirmado 2026-09-15).
    source_col = "integration_code" if "integration_code" in out.columns else "odoo_code"
    out["odoo_code"] = out[source_col].apply(
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