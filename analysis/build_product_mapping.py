import pandas as pd
from difflib import SequenceMatcher

from extract.db.wansoft_products_db import get_wansoft_products_from_db
from extract.products.odoo_products import extract_odoo_products
from analysis.normalize_products import normalize_wansoft_products
from analysis.normalize_odoo_products import normalize_odoo_products


def similarity(a, b):
    if not a or not b:
        return 0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() * 100


def build_product_mapping(threshold=95):

    # --------------------------------
    # EXTRAER
    # --------------------------------
    df_w_raw = get_wansoft_products_from_db()
    df_o_raw = extract_odoo_products()

    df_w = normalize_wansoft_products(df_w_raw)
    df_o = normalize_odoo_products(df_o_raw)

    # --------------------------------
    # FILTRAR ODOO SOLO PRODUCTOS DE VENTA
    # --------------------------------
    df_o = df_o[df_o["sale_ok"] == True].copy()

    # separar con / sin código
    df_o_with_code = df_o[df_o["odoo_code"].notna()].copy()
    df_o_no_code = df_o[df_o["odoo_code"].isna()].copy()

    # limpieza clave
    df_w["wansoft_code"] = df_w["wansoft_code"].astype(str).str.strip()
    df_o_with_code["odoo_code"] = df_o_with_code["odoo_code"].astype(str).str.strip()

    # --------------------------------
    # MATCH EXACTO
    # --------------------------------
    df_exact = pd.merge(
        df_w,
        df_o_with_code,
        left_on="wansoft_code",
        right_on="odoo_code",
        how="inner",
        suffixes=("_w", "_o")
    )

    exact_rows = []
    for _, r in df_exact.iterrows():
        exact_rows.append({
            "source_system": "both",
            "wansoft_code": r["wansoft_code"],
            "odoo_code": r["odoo_code"],
            "canonical_code": r["wansoft_code"],
            "canonical_name": r["product_name_w"],
            "match_type": "exact_code",
            "confidence_score": 100,
            "status": "approved",
            "notes": "Exact match"
        })

    matched_w = set(df_exact["wansoft_code"])
    matched_o = set(df_exact["odoo_code"])

    # --------------------------------
    # ODOO SIN CÓDIGO
    # --------------------------------
    no_code_rows = []
    for _, r in df_o_no_code.iterrows():
        no_code_rows.append({
            "source_system": "odoo",
            "wansoft_code": None,
            "odoo_code": None,
            "canonical_code": None,
            "canonical_name": r["product_name"],
            "match_type": "odoo_no_code",
            "confidence_score": None,
            "status": "pending",
            "notes": "Odoo sin referencia interna"
        })

    # --------------------------------
    # FUZZY MATCH
    # --------------------------------
    fuzzy_rows = []

    df_w_unmatched = df_w[~df_w["wansoft_code"].isin(matched_w)]
    df_o_unmatched = df_o_with_code[~df_o_with_code["odoo_code"].isin(matched_o)]

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
                "wansoft_code": w["wansoft_code"],
                "odoo_code": best_match["odoo_code"],
                "canonical_code": w["wansoft_code"],
                "canonical_name": w["product_name"],
                "match_type": "fuzzy_name",
                "confidence_score": round(best_score, 2),
                "status": "suggested",
                "notes": f"Fuzzy match {best_score}%"
            })

    # --------------------------------
    # RESULTADO FINAL
    # --------------------------------
    df = pd.DataFrame(exact_rows + no_code_rows + fuzzy_rows)

    return df


def extract_base_code(code):

    if not code:
        return None

    parts = str(code).split("-")

    if len(parts) >= 4:
        return "-".join(parts[1:])  # quita el prefijo

    return code