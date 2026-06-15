import pandas as pd
from core.database.mysql import get_mysql_connection as get_db_connection


def normalize(text):
    if pd.isna(text) or text is None:
        return ""
    return str(text).strip().lower()


def refine_review_scope_row(row):
    """
    Refinador de segundo nivel SOLO para filas actualmente en review_scope.

    Objetivo:
    - reclasificar parte de review_scope como shared_cross_company
    - detectar algunos candidatos para bodegon / empanadas / restaurantes
    - dejar el resto en review_scope
    """

    product_name = normalize(row.get("product_name"))
    category_name = normalize(row.get("category_name"))

    # -----------------------------
    # 1) Empanadas candidate
    # -----------------------------
    if "empanad" in product_name or "canastita" in product_name or "empanad" in category_name:
        return {
            "refined_inventory_scope_v2": "empanadas_candidate",
            "refined_scope_source_v2": "review_scope_name_category",
            "refined_scope_status_v2": "pending_review",
            "refined_notes_v2": "Review-scope item matched empanadas naming heuristic"
        }

    # -----------------------------
    # 2) Bodegón candidate
    # -----------------------------
    if any(k in product_name for k in [
        "chorizo", "morcilla", "embutido", "salchicha",
        "back rib", "costillar", "top sirloin", "retazo"
    ]) or any(k in category_name for k in [
        "embutidos", "reventa", "bodegon", "manufacturas"
    ]):
        return {
            "refined_inventory_scope_v2": "bodegon_candidate",
            "refined_scope_source_v2": "review_scope_name_category",
            "refined_scope_status_v2": "pending_review",
            "refined_notes_v2": "Review-scope item matched bodegon heuristic"
        }

    # -----------------------------
    # 3) Shared cross company
    # Productos que razonablemente pueden ser comunes
    # a varias empresas / operaciones
    # -----------------------------
    shared_category_keywords = [
        "aceites",
        "frutas y verduras",
        "condimentos",
        "semillas",
        "especias",
        "lacteos",
        "quesos",
        "carne",
        "pescados",
        "mariscos",
        "material de empaque",
        "higienicos desechables",
        "jarceria",
        "quimicos",
        "limpieza",
        "agua",
        "cafe",
        "te",
        "conservas",
        "enlatados",
        "proveeduría",
    ]

    shared_name_keywords = [
        "aceite",
        "achiote",
        "almendra",
        "anis",
        "ajo",
        "pimienta",
        "canela",
        "clavo",
        "servilleta",
        "bobina",
        "bolsa",
        "charola",
        "contenedor",
        "caja",
        "limpiador",
        "cofia",
        "guante",
        "quimico",
        "jabon",
        "detergente",
        "agua",
        "cafe",
        "te",
        "crema",
        "queso",
        "leche",
        "yogurt",
        "jitomate",
        "cebolla",
        "limon",
        "cilantro",
        "arrachera",
        "suadero",
        "cabrito",
        "pulpo",
        "camaron",
        "atun",
        "bolillo",
    ]

    if any(k in category_name for k in shared_category_keywords) or \
       any(k in product_name for k in shared_name_keywords):
        return {
            "refined_inventory_scope_v2": "shared_cross_company",
            "refined_scope_source_v2": "review_scope_shared_heuristic",
            "refined_scope_status_v2": "pending_review",
            "refined_notes_v2": "Review-scope item matched shared cross-company heuristic"
        }

    # -----------------------------
    # 4) Restaurantes candidate
    # -----------------------------
    if any(k in category_name for k in [
        "refrescos",
        "pv bebidas sin alcohol",
        "pv carne",
        "pv postres",
        "pv quesos",
        "tortillas"
    ]) or any(k in product_name for k in [
        "coca cola", "fanta", "fresca", "ginger ale", "mineral"
    ]):
        return {
            "refined_inventory_scope_v2": "restaurantes_candidate",
            "refined_scope_source_v2": "review_scope_name_category",
            "refined_scope_status_v2": "pending_review",
            "refined_notes_v2": "Review-scope item matched restaurantes heuristic"
        }

    # -----------------------------
    # 5) Sigue ambiguo
    # -----------------------------
    return {
        "refined_inventory_scope_v2": "review_scope",
        "refined_scope_source_v2": "review_scope_fallback",
        "refined_scope_status_v2": "pending_review",
        "refined_notes_v2": "Still ambiguous after second refinement layer"
    }


def build_review_scope_refinement():
    """
    Toma SOLO las filas con refined_inventory_scope = review_scope
    y les aplica una segunda capa de refinamiento.
    """

    conn = get_db_connection(target="wansoft")

    query = """
    SELECT
        id,
        odoo_product_id,
        product_name,
        category_name,
        inventory_scope,
        scope_source,
        scope_status,
        refined_inventory_scope,
        refined_scope_source,
        refined_scope_status
    FROM odoo_inventory_scope_classification
    WHERE refined_inventory_scope = 'review_scope'
    """

    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        return pd.DataFrame()

    refined = df.apply(refine_review_scope_row, axis=1, result_type="expand")

    result = pd.concat([df.reset_index(drop=True), refined.reset_index(drop=True)], axis=1)

    return result


def summarize_review_scope_refinement(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["refined_inventory_scope_v2", "count", "pct"])

    total = len(df)

    summary = (
        df["refined_inventory_scope_v2"]
        .value_counts()
        .reset_index()
    )
    summary.columns = ["refined_inventory_scope_v2", "count"]
    summary["pct"] = (summary["count"] / total * 100).round(2)

    return summary