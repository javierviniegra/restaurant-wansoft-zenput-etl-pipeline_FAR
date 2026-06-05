import pandas as pd
from extract.products.odoo_products import extract_odoo_products


def normalize(text):
    if pd.isna(text):
        return ""
    return str(text).strip().lower()


def classify_row(row):

    category = normalize(row.get("category_name"))
    name = normalize(row.get("product_name"))
    sale_ok = bool(row.get("sale_ok"))
    purchase_ok = bool(row.get("purchase_ok"))

    # -----------------------------
    # REGLAS POR CATEGORÍA
    # -----------------------------
    if "utensilio" in category or "equipo" in category:
        return "utensilio_equipo"

    if "mantenimiento" in category:
        return "mantenimiento"

    if "botiquin" in category:
        return "botiquin"

    if "aceite" in category or "salsa" in category or "fruta" in category:
        return "inventory_purchase"

    # -----------------------------
    # REGLAS POR NOMBRE
    # -----------------------------
    if "copa" in name or "abrelatas" in name:
        return "utensilio_equipo"

    if "aceite" in name or "ajo" in name or "pasta" in name:
        return "inventory_purchase"

    # -----------------------------
    # REGLAS POR FLAGS
    # -----------------------------
    if sale_ok and not purchase_ok:
        return "venta_sin_codigo"

    if purchase_ok:
        return "inventory_purchase"

    return "revisar_manual"


def classify_odoo_no_code():

    df = extract_odoo_products()

    # crear integration_code si no existe
    if "integration_code" not in df.columns:
        df["integration_code"] = df["default_code"]

    pending = df[
        (df["sale_ok"] == True) &
        (df["integration_code"].isna())
    ].copy()

    if pending.empty:
        print("No hay productos pendientes")
        return pd.DataFrame()

    pending["classification"] = pending.apply(classify_row, axis=1)

    return pending


def summarize(df):

    total = len(df)

    summary = df["classification"].value_counts().reset_index()
    summary.columns = ["classification", "count"]
    summary["pct"] = (summary["count"] / total * 100).round(2)

    return summary