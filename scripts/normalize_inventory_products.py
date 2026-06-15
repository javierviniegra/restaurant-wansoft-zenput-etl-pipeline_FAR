import pandas as pd


def normalize_wansoft_inventory(df):

    out = df.copy()

    out = out.rename(columns={
        "CodigoProducto": "wansoft_code",
        "Descripcion": "product_name"
    })

    out["wansoft_code"] = out["wansoft_code"].astype(str).str.strip()
    out["product_name"] = out["product_name"].astype(str).str.strip()

    return out[[
        "wansoft_code",
        "product_name"
    ]]