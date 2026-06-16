import pandas as pd
from difflib import SequenceMatcher
from core.database.mysql import get_mysql_connection as get_db_connection


def similarity(a, b):
    if not a or not b:
        return 0
    return SequenceMatcher(None, str(a).lower().strip(), str(b).lower().strip()).ratio() * 100


def load_residual_not_found():
    """
    Carga únicamente el backlog real pendiente:
    not_found que NO está ya en snapshot ni en el diccionario.
    """
    conn = get_db_connection(target="wansoft")

    query = """
    SELECT
        b.odoo_product_id,
        MAX(b.odoo_product_name) AS odoo_product_name,
        MAX(s.category_name) AS category_name
    FROM odoo_inventory_backlog b
    LEFT JOIN odoo_inventory_scope_classification s
        ON b.odoo_product_id = s.odoo_product_id
    LEFT JOIN odoo_inventory_snapshot snap
        ON b.odoo_product_id = snap.odoo_product_id
    LEFT JOIN inventory_mapping_dictionary d
        ON b.odoo_product_id = d.odoo_product_id
       AND d.domain = 'inventory'
    WHERE b.backlog_bucket = 'not_found'
      AND snap.odoo_product_id IS NULL
      AND d.odoo_product_id IS NULL
    GROUP BY b.odoo_product_id
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


def build_inventory_not_found_residual_bridge(threshold=86):
    """
    Puente final del residual not_found contra inventory_product_lifecycle.

    Threshold ligeramente más flexible porque lo que queda ya es
    más heterogéneo que P1/P2.
    """
    df_residual = load_residual_not_found()
    df_w = load_wansoft_inventory_lifecycle()

    if df_residual.empty or df_w.empty:
        return pd.DataFrame()

    valid_lifecycle = {
        "active_operational",
        "dormant_operational",
        "historical_candidate",
        "historical_with_stock_review"
    }
    df_w = df_w[df_w["lifecycle_candidate"].isin(valid_lifecycle)].copy()

    rows = []

    for _, residual in df_residual.iterrows():
        best_score = 0
        best_match = None

        for _, w in df_w.iterrows():
            score = similarity(residual["odoo_product_name"], w["Producto"])
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
                "odoo_product_id": residual["odoo_product_id"],
                "odoo_product_name": residual["odoo_product_name"],
                "category_name": residual["category_name"],
                "wansoft_code": best_match["CodigoProducto"],
                "wansoft_product_name": best_match["Producto"],
                "wansoft_department": best_match["Departamento"],
                "lifecycle_candidate": best_match["lifecycle_candidate"],
                "similarity_score": round(best_score, 2),
                "suggested_action": suggested_action
            })

    return pd.DataFrame(rows)