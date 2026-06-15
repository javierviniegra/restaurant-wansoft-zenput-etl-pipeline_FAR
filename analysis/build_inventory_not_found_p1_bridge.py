import pandas as pd
from difflib import SequenceMatcher
from core.database.mysql import get_mysql_connection as get_db_connection


def similarity(a, b):
    if not a or not b:
        return 0
    return SequenceMatcher(None, str(a).lower().strip(), str(b).lower().strip()).ratio() * 100


def load_p1_backlog():
    conn = get_db_connection(target="wansoft")

    query = """
    SELECT
        odoo_product_id,
        odoo_product_name,
        category_name,
        refined_inventory_scope,
        priority_bucket
    FROM inventory_not_found_priority_backlog
    WHERE priority_bucket = 'P1'
    """

    df = pd.read_sql(query, conn)
    conn.close()

    return df


def load_wansoft_inventory_lifecycle():
    conn = get_db_connection(target="wansoft")

    query = """
    SELECT
        CodigoProducto,
        Producto,
        Departamento,
        lifecycle_candidate
    FROM inventory_product_lifecycle
    """

    df = pd.read_sql(query, conn)
    conn.close()

    return df


def build_inventory_not_found_p1_bridge(threshold=90):
    df_p1 = load_p1_backlog()
    df_w = load_wansoft_inventory_lifecycle()

    if df_p1.empty or df_w.empty:
        return pd.DataFrame()

    # Solo lifecycle útil
    valid_lifecycle = {
        "active_operational",
        "dormant_operational",
        "historical_candidate",
        "historical_with_stock_review"
    }
    df_w = df_w[df_w["lifecycle_candidate"].isin(valid_lifecycle)].copy()

    rows = []

    for _, p1 in df_p1.iterrows():
        best_score = 0
        best_match = None

        for _, w in df_w.iterrows():
            score = similarity(p1["odoo_product_name"], w["Producto"])
            if score > best_score:
                best_score = score
                best_match = w

        if best_match is not None and best_score >= threshold:
            lifecycle = best_match["lifecycle_candidate"]

            if lifecycle == "active_operational":
                suggested_action = "approved_candidate"
            elif lifecycle == "dormant_operational":
                suggested_action = "review_candidate"
            elif lifecycle == "historical_candidate":
                suggested_action = "historical_candidate"
            elif lifecycle == "historical_with_stock_review":
                suggested_action = "historical_stock_review"
            else:
                suggested_action = "manual_review"

            rows.append({
                "odoo_product_id": p1["odoo_product_id"],
                "odoo_product_name": p1["odoo_product_name"],
                "category_name": p1["category_name"],
                "wansoft_code": best_match["CodigoProducto"],
                "wansoft_product_name": best_match["Producto"],
                "wansoft_department": best_match["Departamento"],
                "lifecycle_candidate": best_match["lifecycle_candidate"],
                "similarity_score": round(best_score, 2),
                "suggested_action": suggested_action
            })

    return pd.DataFrame(rows)