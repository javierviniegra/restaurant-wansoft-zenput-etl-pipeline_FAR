import pandas as pd
from core.database.mysql import get_mysql_connection as get_db_connection


def normalize(text):
    if pd.isna(text) or text is None:
        return ""
    return str(text).strip().lower()


def refine_scope_row(row):
    base_scope = normalize(row.get("inventory_scope"))
    original_scope_source = normalize(row.get("scope_source"))
    product_name = normalize(row.get("product_name"))
    category_name = normalize(row.get("category_name"))

    # Respetar scopes explícitos ya aprobados
    # IMPORTANTE: si viene de sales_reference, conservarlo
    if base_scope in ["bodegon", "empanadas", "restaurantes"]:
        return {
            "refined_inventory_scope": base_scope,
            "refined_scope_source": row.get("scope_source"),   # <- preserva fuente real
            "refined_scope_status": "approved"
        }

    # Solo refinamos shared_or_open
    if base_scope != "shared_or_open":
        return {
            "refined_inventory_scope": "review_scope",
            "refined_scope_source": "fallback",
            "refined_scope_status": "pending_review"
        }

    # Empanadas candidate
    if "empanad" in product_name or "canastita" in product_name or "empanad" in category_name:
        return {
            "refined_inventory_scope": "empanadas_candidate",
            "refined_scope_source": "heuristic_name_category",
            "refined_scope_status": "pending_review"
        }

    # Bodegón candidate
    if any(k in product_name for k in ["chorizo", "morcilla", "embutido", "salchicha"]) or \
       any(k in category_name for k in ["embutidos", "reventa", "bodegon"]):
        return {
            "refined_inventory_scope": "bodegon_candidate",
            "refined_scope_source": "heuristic_name_category",
            "refined_scope_status": "pending_review"
        }

    # Compartido / restaurantes probables
    if any(k in category_name for k in [
        "aceites", "frutas y verduras", "condimentos", "lacteos",
        "quesos", "carne", "pescados", "mariscos", "material de empaque",
        "agua", "cafe", "te", "conservas", "higienicos desechables"
    ]):
        return {
            "refined_inventory_scope": "shared_cross_company",
            "refined_scope_source": "heuristic_category",
            "refined_scope_status": "pending_review"
        }

    return {
        "refined_inventory_scope": "review_scope",
        "refined_scope_source": "heuristic_fallback",
        "refined_scope_status": "pending_review"
    }

def refine_odoo_inventory_scope():
    conn = get_db_connection(target="wansoft")

    query = """
    SELECT
        id,
        odoo_product_id,
        product_name,
        category_name,
        inventory_scope,
        scope_source,
        scope_status
    FROM odoo_inventory_scope_classification
    """

    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        return pd.DataFrame()

    refined = df.apply(refine_scope_row, axis=1, result_type="expand")
    result = pd.concat([df.reset_index(drop=True), refined.reset_index(drop=True)], axis=1)

    return result