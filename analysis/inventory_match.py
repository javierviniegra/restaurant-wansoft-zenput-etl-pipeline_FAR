import pandas as pd


def match_inventory_by_product(df_wansoft: pd.DataFrame, df_odoo: pd.DataFrame) -> pd.DataFrame:
    """
    Hace un primer match de inventario por código de producto.

    Este match:
    - Agrega Wansoft por product_code
    - Agrega Odoo por product_code
    - Compara cantidades totales
    - Calcula diferencia

    NOTA:
    Aún NO se compara por sucursal / location.
    Este es un primer cruce global por producto.
    """

    w = df_wansoft.copy()
    o = df_odoo.copy()

    # -----------------------------
    # Validaciones mínimas
    # -----------------------------
    required_wansoft_cols = ["product_code", "product_name", "unit", "stock_qty", "stock_value"]
    required_odoo_cols = ["product_code", "product_name", "stock_qty"]

    missing_w = [col for col in required_wansoft_cols if col not in w.columns]
    missing_o = [col for col in required_odoo_cols if col not in o.columns]

    if missing_w:
        raise ValueError(f"Faltan columnas en df_wansoft: {missing_w}")

    if missing_o:
        raise ValueError(f"Faltan columnas en df_odoo: {missing_o}")

    # -----------------------------
    # Normalización ligera
    # -----------------------------
    w["product_code"] = w["product_code"].astype(str).str.strip()
    o["product_code"] = o["product_code"].astype(str).str.strip()

    w["product_name"] = w["product_name"].astype(str).str.strip()
    o["product_name"] = o["product_name"].astype(str).str.strip()

    # Convertir cantidades a numérico por seguridad
    w["stock_qty"] = pd.to_numeric(w["stock_qty"], errors="coerce")
    w["stock_value"] = pd.to_numeric(w["stock_value"], errors="coerce")
    o["stock_qty"] = pd.to_numeric(o["stock_qty"], errors="coerce")

    # -----------------------------
    # Agregación WANSOFT
    # -----------------------------
    w_agg = (
        w.groupby(["product_code", "product_name", "unit"], dropna=False, as_index=False)
         .agg(
             wansoft_stock_qty=("stock_qty", "sum"),
             wansoft_stock_value=("stock_value", "sum")
         )
    )

    w_agg = w_agg.rename(columns={
        "product_name": "product_name_wansoft"
    })

    # -----------------------------
    # Agregación ODOO
    # -----------------------------
    o_agg = (
        o.groupby(["product_code", "product_name"], dropna=False, as_index=False)
         .agg(
             odoo_stock_qty=("stock_qty", "sum")
         )
    )

    o_agg = o_agg.rename(columns={
        "product_name": "product_name_odoo"
    })

    # -----------------------------
    # Merge principal
    # -----------------------------
    result = pd.merge(
        w_agg,
        o_agg,
        on="product_code",
        how="outer"
    )

    # -----------------------------
    # Resolver nombre final
    # -----------------------------
    result["product_name_final"] = result["product_name_wansoft"].combine_first(result["product_name_odoo"])

    # -----------------------------
    # Calcular diferencia
    # -----------------------------
    result["wansoft_stock_qty"] = result["wansoft_stock_qty"].fillna(0)
    result["odoo_stock_qty"] = result["odoo_stock_qty"].fillna(0)
    result["wansoft_stock_value"] = result["wansoft_stock_value"].fillna(0)

    result["diff_qty"] = result["wansoft_stock_qty"] - result["odoo_stock_qty"]

    # -----------------------------
    # Flags útiles
    # -----------------------------
    result["exists_in_wansoft"] = result["wansoft_stock_qty"] != 0
    result["exists_in_odoo"] = result["odoo_stock_qty"] != 0

    result["match_status"] = result.apply(
        lambda row: (
            "match"
            if row["exists_in_wansoft"] and row["exists_in_odoo"]
            else "only_wansoft"
            if row["exists_in_wansoft"] and not row["exists_in_odoo"]
            else "only_odoo"
            if row["exists_in_odoo"] and not row["exists_in_wansoft"]
            else "empty"
        ),
        axis=1
    )

    # -----------------------------
    # Orden final de columnas
    # -----------------------------
    final_cols = [
        "product_code",
        "product_name_final",
        "unit",
        "wansoft_stock_qty",
        "odoo_stock_qty",
        "diff_qty",
        "wansoft_stock_value",
        "match_status",
        "product_name_wansoft",
        "product_name_odoo"
    ]

    result = result[final_cols]

    # -----------------------------
    # Ordenar por diferencia absoluta
    # -----------------------------
    result["abs_diff_qty"] = result["diff_qty"].abs()
    result = result.sort_values(by=["abs_diff_qty", "product_code"], ascending=[False, True])

    # Si no quieres dejar la columna auxiliar, la quitamos
    result = result.drop(columns=["abs_diff_qty"])

    return result
