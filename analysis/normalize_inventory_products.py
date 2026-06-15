import pandas as pd


def normalize_wansoft_inventory_products(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza catálogo Wansoft de inventory a estructura estándar.
    """

    if df is None or df.empty:
        return pd.DataFrame(columns=[
            "source_system",
            "wansoft_code",
            "product_name",
            "unit",
            "department",
            "department_code"
        ])

    out = df.copy()

    out = out.rename(columns={
        "CodigoProducto": "wansoft_code",
        "Producto": "product_name",
        "UnidadDeMedida": "unit",
        "Departamento": "department",
        "CodigoDepartamento": "department_code"
    })

    out["wansoft_code"] = out["wansoft_code"].astype(str).str.strip()
    out["product_name"] = out["product_name"].astype(str).str.strip()

    out["source_system"] = "wansoft_inventory"

    return out[[
        "source_system",
        "wansoft_code",
        "product_name",
        "unit",
        "department",
        "department_code"
    ]]