import pandas as pd
from extract.products.odoo_products import extract_odoo_products
from analysis.build_sales_product_mapping import build_sales_product_mapping


def normalize(text):
    if pd.isna(text):
        return ""
    return str(text).strip().lower()


def classify_inventory_bucket(row, sales_codes):
    default_code = row.get("default_code")
    sale_ok = bool(row.get("sale_ok"))
    purchase_ok = bool(row.get("purchase_ok"))

    if not purchase_ok:
        return "not_inventory"

    if default_code in sales_codes and sale_ok and purchase_ok:
        return "inventory_finished_goods"

    if purchase_ok and not sale_ok:
        return "inventory_raw_materials"

    if purchase_ok and sale_ok and default_code not in sales_codes:
        return "inventory_mixed_review"

    return "inventory_review"


def classify_raw_row(row):
    category = normalize(row.get("category_name"))
    name = normalize(row.get("product_name"))

    # por categoría
    if "material de empaque" in category:
        return "packaging_supply"

    if "ron" in category or "tequila" in category or "mezcal" in category or "vodka" in category or "vino" in category or "cerveza" in category:
        return "alcoholic_inventory"

    if "aceite" in category:
        return "ingredient_oil"

    if "frutas y verduras" in category:
        return "ingredient_fresh"

    if "enlatados y conservas" in category:
        return "ingredient_conserved"

    if "semillas" in category or "condimentos" in category or "especias" in category:
        return "ingredient_condiment"

    if "agua" in category:
        return "liquid_inventory"

    if "servicio" in category:
        return "service_non_inventory"

    # por nombre
    if "charola" in name or "contenedor" in name:
        return "packaging_supply"

    if "aceite" in name:
        return "ingredient_oil"

    if "agua" in name:
        return "liquid_inventory"

    if "absolut" in name or "bacardi" in name or "conejos" in name or "1800" in name:
        return "alcoholic_inventory"

    return "raw_review_manual"


def classify_inventory_raw_no_code():
    """
    Clasifica SOLO inventory_raw_materials sin integration_code.
    """
    df = extract_odoo_products()

    if df.empty:
        return pd.DataFrame()

    if "integration_code" not in df.columns:
        df["integration_code"] = df["x_wansoft_code"].combine_first(df["default_code"])

    df["default_code"] = df["default_code"].apply(
        lambda x: None if x in [None, False, "", "False"] else str(x).strip()
    )
    df["integration_code"] = df["integration_code"].apply(
        lambda x: None if x in [None, False, "", "False"] else str(x).strip()
    )

    df_sales_mapping = build_sales_product_mapping(threshold=95)
    sales_codes = set(df_sales_mapping["odoo_code"].dropna().astype(str).str.strip().tolist())

    df["inventory_bucket"] = df.apply(
        lambda row: classify_inventory_bucket(row, sales_codes),
        axis=1
    )

    pending = df[
        (df["inventory_bucket"] == "inventory_raw_materials") &
        (df["integration_code"].isna())
    ].copy()

    if pending.empty:
        return pd.DataFrame()

    pending["raw_classification"] = pending.apply(classify_raw_row, axis=1)

    return pending


def summarize_inventory_raw_no_code(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=["raw_classification", "count", "pct"])

    total = len(df)

    summary = (
        df["raw_classification"]
        .value_counts()
        .reset_index()
    )
    summary.columns = ["raw_classification", "count"]
    summary["pct"] = (summary["count"] / total * 100).round(2)

    return summary