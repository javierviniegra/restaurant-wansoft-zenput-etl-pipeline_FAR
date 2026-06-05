import pandas as pd


def normalize_wansoft_sales_products(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza catálogo de productos de venta Wansoft.
    """

    if df is None or df.empty:
        return pd.DataFrame(columns=[
            "source_system",
            "wansoft_code",
            "product_name",
            "group_name",
            "group_code",
            "group_type",
            "group_type_code"
        ])

    out = df.copy()

    out = out.rename(columns={
        "CodigoPlatillo": "wansoft_code",
        "Platillo": "product_name",
        "Grupo": "group_name",
        "CodigoGrupo": "group_code",
        "TipoGrupo": "group_type",
        "CodigoTipoGrupo": "group_type_code"
    })

    out["wansoft_code"] = out["wansoft_code"].astype(str).str.strip()
    out["product_name"] = out["product_name"].astype(str).str.strip()

    out["source_system"] = "wansoft_sales"

    return out[[
        "source_system",
        "wansoft_code",
        "product_name",
        "group_name",
        "group_code",
        "group_type",
        "group_type_code"
    ]]