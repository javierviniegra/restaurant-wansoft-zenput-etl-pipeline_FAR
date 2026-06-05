import pandas as pd
import re


def normalize_wansoft_inventory(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza el inventario Wansoft a un modelo canónico.
    """

    out = df.copy()

    out = out.rename(columns={
        "Sucursal": "branch",
        "Fecha": "snapshot_date",
        "IdProducto": "source_product_id",
        "CodigoProducto": "product_code",
        "Producto": "product_name",
        "UnidadDeMedida": "unit",
        "Disponibilidad": "stock_qty",
        "Balance": "stock_value",
        "Critico": "is_critical",
        "Departamento": "department",
        "CodigoDepartamento": "department_code",
    })

    out["source"] = "wansoft"

    cols = [
        "source",
        "branch",
        "snapshot_date",
        "source_product_id",
        "product_code",
        "product_name",
        "department_code",
        "department",
        "unit",
        "stock_qty",
        "stock_value",
        "is_critical",
    ]

    return out[cols]