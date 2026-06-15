import pandas as pd
from difflib import SequenceMatcher
from core.database.mysql import get_mysql_connection as get_db_connection


def similarity(a, b):
    if not a or not b:
        return 0
    return SequenceMatcher(None, str(a).lower().strip(), str(b).lower().strip()).ratio() * 100


def get_wansoft_inventory_lifecycle():
    conn = get_db_connection(target="wansoft")

    query = """
    SELECT
        CodigoProducto,
        Producto,
        Departamento,
        CodigoDepartamento,
        UnidadDeMedida,
        current_stock_qty,
        last_activity_date,
        days_since_last_activity,
        lifecycle_candidate
    FROM inventory_product_lifecycle
    """

    df = pd.read_sql(query, conn)
    conn.close()

    return df


def get_odoo_inventory_raw_no_code():
    conn = get_db_connection(target="wansoft")

    query = """
    SELECT
        product_name,
        category_name,
        sale_ok,
        purchase_ok,
        raw_classification
    FROM odoo_inventory_raw_no_code_classification
    """

    df = pd.read_sql(query, conn)
    conn.close()

    return df


def build_inventory_bridge_report(threshold=92):
    df_w = get_wansoft_inventory_lifecycle()
    df_o = get_odoo_inventory_raw_no_code()

    if df_w.empty or df_o.empty:
        return pd.DataFrame()

    rows = []

    # Solo comparar contra Wansoft que sea útil:
    # activos, dormidos o históricos
    valid_lifecycle = {
        "active_operational",
        "dormant_operational",
        "historical_candidate",
        "historical_with_stock_review"
    }
    df_w = df_w[df_w["lifecycle_candidate"].isin(valid_lifecycle)].copy()

    for _, o in df_o.iterrows():
        best_score = 0
        best_match = None

        for _, w in df_w.iterrows():
            score = similarity(o["product_name"], w["Producto"])

            if score > best_score:
                best_score = score
                best_match = w

        if best_match is not None and best_score >= threshold:
            # sugerencia de acción en función del lifecycle
            lifecycle = best_match["lifecycle_candidate"]

            if lifecycle == "active_operational":
                suggested_action = "assign_default_code"
            elif lifecycle == "dormant_operational":
                suggested_action = "review_before_assigning_code"
            elif lifecycle == "historical_candidate":
                suggested_action = "keep_as_historical"
            elif lifecycle == "historical_with_stock_review":
                suggested_action = "historical_with_remaining_stock_review"
            else:
                suggested_action = "manual_review"

            rows.append({
                "odoo_product_name": o["product_name"],
                "odoo_category_name": o["category_name"],
                "raw_classification": o["raw_classification"],
                "wansoft_code": best_match["CodigoProducto"],
                "wansoft_product_name": best_match["Producto"],
                "wansoft_department": best_match["Departamento"],
                "wansoft_lifecycle_candidate": best_match["lifecycle_candidate"],
                "similarity_score": round(best_score, 2),
                "suggested_action": suggested_action
            })

    return pd.DataFrame(rows)


def summarize_inventory_bridge_report(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=["suggested_action", "count", "pct"])

    total = len(df)

    summary = (
        df["suggested_action"]
        .value_counts()
        .reset_index()
    )
    summary.columns = ["suggested_action", "count"]
    summary["pct"] = (summary["count"] / total * 100).round(2)

    return summary