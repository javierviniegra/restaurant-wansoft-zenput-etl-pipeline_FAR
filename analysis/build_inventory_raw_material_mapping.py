import pandas as pd
from difflib import SequenceMatcher

from extract.db.wansoft_inventory_products_db import get_wansoft_inventory_products_from_db
from extract.products.odoo_products import extract_odoo_products
from analysis.normalize_inventory_products import normalize_wansoft_inventory_products


def similarity(a, b):
    if not a or not b:
        return 0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio() * 100


def classify_inventory_bucket(row, sales_codes):
    """
    Replica la lógica del test para clasificar el universo inventory.
    """

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


def build_inventory_raw_material_mapping(df_sales_mapping: pd.DataFrame, threshold=95):
    """
    Construye mapping SOLO para inventory_raw_materials.

    Reglas:
    - exact match por CodigoProducto (Wansoft) == default_code/integration_code (Odoo)
    - no_code -> pending
    - fuzzy -> solo sugerencia sobre no matcheados
    """

    # -----------------------------
    # WANSOFT INVENTORY
    # -----------------------------
    df_w_raw = get_wansoft_inventory_products_from_db()
    df_w = normalize_wansoft_inventory_products(df_w_raw)

    # -----------------------------
    # ODOO
    # -----------------------------
    df_o = extract_odoo_products()

    if df_o.empty:
        return pd.DataFrame(columns=[
            "source_system",
            "domain",
            "wansoft_code",
            "odoo_code",
            "canonical_code",
            "canonical_name",
            "match_type",
            "confidence_score",
            "status",
            "notes"
        ])

    # integration_code
    if "integration_code" not in df_o.columns:
        df_o["integration_code"] = df_o["x_wansoft_code"].combine_first(df_o["default_code"])

    df_o["default_code"] = df_o["default_code"].apply(
        lambda x: None if x in [None, False, "", "False"] else str(x).strip()
    )
    df_o["integration_code"] = df_o["integration_code"].apply(
        lambda x: None if x in [None, False, "", "False"] else str(x).strip()
    )

    # -----------------------------
    # SALES codes para excluir finished goods
    # -----------------------------
    sales_codes = set(df_sales_mapping["odoo_code"].dropna().astype(str).str.strip().tolist())

    # -----------------------------
    # CLASIFICAR inventory buckets
    # -----------------------------
    df_o["inventory_bucket"] = df_o.apply(
        lambda row: classify_inventory_bucket(row, sales_codes),
        axis=1
    )

    # Nos quedamos SOLO con raw materials
    df_o_raw = df_o[df_o["inventory_bucket"] == "inventory_raw_materials"].copy()

    # Odoo con / sin código
    df_o_with_code = df_o_raw[df_o_raw["integration_code"].notna()].copy()
    df_o_no_code = df_o_raw[df_o_raw["integration_code"].isna()].copy()

    # limpieza
    df_w["wansoft_code"] = df_w["wansoft_code"].astype(str).str.strip()
    df_o_with_code["integration_code"] = df_o_with_code["integration_code"].astype(str).str.strip()

    # -----------------------------
    # 1) EXACT MATCH
    # -----------------------------
    df_exact = pd.merge(
        df_w,
        df_o_with_code,
        left_on="wansoft_code",
        right_on="integration_code",
        how="inner",
        suffixes=("_w", "_o")
    )

    exact_rows = []
    for _, r in df_exact.iterrows():
        exact_rows.append({
            "source_system": "both",
            "domain": "inventory_raw_materials",
            "wansoft_code": r["wansoft_code"],
            "odoo_code": r["integration_code"],
            "canonical_code": r["integration_code"],
            "canonical_name": r["product_name_w"],
            "match_type": "exact_code",
            "confidence_score": 100.0,
            "status": "approved",
            "notes": f"Exact inventory raw material match. category={r['category_name']}"
        })

    matched_w = set(df_exact["wansoft_code"].dropna().astype(str).tolist())
    matched_o = set(df_exact["integration_code"].dropna().astype(str).tolist())

    # -----------------------------
    # 2) ODOO RAW MATERIALS SIN CÓDIGO
    # -----------------------------
    no_code_rows = []
    for _, r in df_o_no_code.iterrows():
        no_code_rows.append({
            "source_system": "odoo",
            "domain": "inventory_raw_materials",
            "wansoft_code": None,
            "odoo_code": None,
            "canonical_code": None,
            "canonical_name": r["product_name"],
            "match_type": "odoo_no_code",
            "confidence_score": None,
            "status": "pending",
            "notes": f"Odoo raw material without integration code. category={r['category_name']}"
        })

    # -----------------------------
    # 3) FUZZY SOLO PARA NO MATCHEADOS
    # -----------------------------
    fuzzy_rows = []

    df_w_unmatched = df_w[~df_w["wansoft_code"].isin(matched_w)].copy()
    df_o_unmatched = df_o_with_code[~df_o_with_code["integration_code"].isin(matched_o)].copy()

    for _, w in df_w_unmatched.iterrows():
        best_score = 0
        best_match = None

        for _, o in df_o_unmatched.iterrows():
            score = similarity(w["product_name"], o["product_name"])
            if score > best_score:
                best_score = score
                best_match = o

        if best_match is not None and best_score >= threshold:
            fuzzy_rows.append({
                "source_system": "both",
                "domain": "inventory_raw_materials",
                "wansoft_code": w["wansoft_code"],
                "odoo_code": best_match["integration_code"],
                "canonical_code": best_match["integration_code"],
                "canonical_name": w["product_name"],
                "match_type": "fuzzy_name",
                "confidence_score": round(best_score, 2),
                "status": "suggested",
                "notes": f"Suggested fuzzy raw material match. Odoo product={best_match['product_name']}"
            })

    df_mapping = pd.DataFrame(exact_rows + no_code_rows + fuzzy_rows)

    if df_mapping.empty:
        return pd.DataFrame(columns=[
            "source_system",
            "domain",
            "wansoft_code",
            "odoo_code",
            "canonical_code",
            "canonical_name",
            "match_type",
            "confidence_score",
            "status",
            "notes"
        ])

    return df_mapping