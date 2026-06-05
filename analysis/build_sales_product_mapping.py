import pandas as pd
from difflib import SequenceMatcher

from extract.db.wansoft_sales_products_db import get_wansoft_sales_products_from_db
from extract.products.odoo_products import extract_odoo_products
from analysis.normalize_sales_products import normalize_wansoft_sales_products


def similarity(a, b):
    if not a or not b:
        return 0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio() * 100


def build_sales_product_mapping(threshold=95):
    """
    Homologa SOLO productos de venta / platillos.
    Regla:
    - match exacto por wansoft_code == integration_code
    - fuzzy solo como sugerencia sobre NO matcheados
    - Odoo sin integration_code queda pending
    """

    df_w_raw = get_wansoft_sales_products_from_db()
    df_o = extract_odoo_products()

    df_w = normalize_wansoft_sales_products(df_w_raw)

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

    # Solo productos de venta en Odoo
    df_o_sale = df_o[df_o["sale_ok"] == True].copy()

    df_o_with_code = df_o_sale[df_o_sale["integration_code"].notna()].copy()
    df_o_no_code = df_o_sale[df_o_sale["integration_code"].isna()].copy()

    df_w["wansoft_code"] = df_w["wansoft_code"].astype(str).str.strip()
    df_o_with_code["integration_code"] = df_o_with_code["integration_code"].astype(str).str.strip()

    # EXACT MATCH
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
            "domain": "sales",
            "wansoft_code": r["wansoft_code"],
            "odoo_code": r["integration_code"],
            "canonical_code": r["wansoft_code"],
            "canonical_name": r["product_name_w"],
            "match_type": "exact_code",
            "confidence_score": 100.0,
            "status": "approved",
            "notes": f"Exact sales match. default_code={r['default_code']} x_wansoft_code={r['x_wansoft_code']}"
        })

    matched_w = set(df_exact["wansoft_code"])
    matched_o = set(df_exact["integration_code"])

    # Odoo de venta sin código
    no_code_rows = []
    for _, r in df_o_no_code.iterrows():
        no_code_rows.append({
            "source_system": "odoo",
            "domain": "sales",
            "wansoft_code": None,
            "odoo_code": None,
            "canonical_code": None,
            "canonical_name": r["product_name"],
            "match_type": "odoo_no_code",
            "confidence_score": None,
            "status": "pending",
            "notes": f"Odoo saleable product without integration code. category={r['category_name']}"
        })

    # FUZZY sobre no matcheados
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
                "domain": "sales",
                "wansoft_code": w["wansoft_code"],
                "odoo_code": best_match["integration_code"],
                "canonical_code": w["wansoft_code"],
                "canonical_name": w["product_name"],
                "match_type": "fuzzy_name",
                "confidence_score": round(best_score, 2),
                "status": "suggested",
                "notes": f"Suggested fuzzy sales match. Odoo product={best_match['product_name']}"
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