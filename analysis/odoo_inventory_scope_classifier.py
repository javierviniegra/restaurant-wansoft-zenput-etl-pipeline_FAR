import pandas as pd
from extract.products.odoo_products import extract_odoo_products


def normalize(text):
    if pd.isna(text) or text is None:
        return ""
    return str(text).strip().lower()


def has_internal_reference(row):
    """
    Consideramos referencia interna usable si existe integration_code
    o, en su defecto, default_code.
    """
    integration_code = row.get("integration_code")
    default_code = row.get("default_code")

    if integration_code not in [None, False, "", "False"]:
        return True

    if default_code not in [None, False, "", "False"]:
        return True

    return False


def classify_inventory_scope(row):
    """
    Clasificación inicial de scope para inventory.

    NUEVA REGLA PRIORITARIA:
    Si el producto se puede vender y tiene referencia interna,
    lo tratamos como producto de venta de sucursales/restaurantes
    aunque la categoría diga "Empanadas" o similar.
    """

    company_name = normalize(row.get("company_name"))
    product_name = normalize(row.get("product_name"))
    category_name = normalize(row.get("category_name"))
    purchase_ok = bool(row.get("purchase_ok"))
    sale_ok = bool(row.get("sale_ok"))
    has_ref = has_internal_reference(row)

    # -----------------------------
    # 0) Fuera del universo inventory
    # -----------------------------
    if not purchase_ok:
        return {
            "inventory_scope": "not_inventory",
            "scope_source": "rule",
            "scope_status": "approved",
            "notes": "purchase_ok=False"
        }

    # -----------------------------
    # 1) REGLA MÁS FUERTE:
    # producto de venta con referencia interna
    # => producto de sucursales / restaurantes
    # -----------------------------
    if sale_ok and has_ref:
        return {
            "inventory_scope": "restaurantes",
            "scope_source": "sales_reference",
            "scope_status": "approved",
            "notes": "sale_ok=True and internal reference present"
        }

    # -----------------------------
    # 2) Clasificación explícita por empresa asignada
    # -----------------------------
    if "bodeg" in company_name:
        return {
            "inventory_scope": "bodegon",
            "scope_source": "company_assignment",
            "scope_status": "approved",
            "notes": f"company_name={row.get('company_name')}"
        }

    if "empanad" in company_name:
        return {
            "inventory_scope": "empanadas",
            "scope_source": "company_assignment",
            "scope_status": "approved",
            "notes": f"company_name={row.get('company_name')}"
        }

    # Si tiene empresa asignada y no es bodegón/empanadas, por ahora restaurantes
    if company_name != "":
        return {
            "inventory_scope": "restaurantes",
            "scope_source": "company_assignment",
            "scope_status": "approved",
            "notes": f"company_name={row.get('company_name')}"
        }

    # -----------------------------
    # 3) Productos abiertos/sin empresa asignada
    # heurísticas SOLO si no tienen referencia interna
    # -----------------------------
    if "empanad" in product_name or "canastita" in product_name or "empanad" in category_name:
        return {
            "inventory_scope": "empanadas",
            "scope_source": "heuristic_name_category",
            "scope_status": "pending_review",
            "notes": "Open/shared product with empanadas naming heuristic"
        }

    if any(k in product_name for k in ["chorizo", "morcilla", "embutido", "salchicha"]) or \
       any(k in category_name for k in ["embutidos", "reventa", "bodegon"]):
        return {
            "inventory_scope": "bodegon",
            "scope_source": "heuristic_name_category",
            "scope_status": "pending_review",
            "notes": "Open/shared product with bodegon naming heuristic"
        }

    # -----------------------------
    # 4) Abierto y sin evidencia
    # -----------------------------
    return {
        "inventory_scope": "shared_or_open",
        "scope_source": "company_assignment",
        "scope_status": "pending_review",
        "notes": "No company assigned and no internal reference-based override"
    }


def classify_odoo_inventory_scope():
    df = extract_odoo_products()

    if df is None or df.empty:
        return pd.DataFrame()

    # Solo universo inventory
    df = df[df["purchase_ok"] == True].copy()

    if df.empty:
        return pd.DataFrame()

    scope_df = df.apply(classify_inventory_scope, axis=1, result_type="expand")

    result = pd.concat([df.reset_index(drop=True), scope_df.reset_index(drop=True)], axis=1)

    return result


def summarize_inventory_scope(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["inventory_scope", "count", "pct"])

    total = len(df)

    summary = (
        df["inventory_scope"]
        .value_counts()
        .reset_index()
    )
    summary.columns = ["inventory_scope", "count"]
    summary["pct"] = (summary["count"] / total * 100).round(2)

    return summary