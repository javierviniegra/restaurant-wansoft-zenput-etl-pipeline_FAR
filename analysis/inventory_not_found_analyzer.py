import os
import pandas as pd

from core.config.env_loader import load_environment
from core.config.inventory_env import get_inventory_not_found_config
from core.database.mysql import get_mysql_connection as get_db_connection


def normalize(text):
    if pd.isna(text) or text is None:
        return ""
    return str(text).strip().lower()


def parse_csv_env(value: str):
    if value is None:
        return []
    value = str(value).strip()
    if value == "":
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


def get_env_config():
    load_environment()
    return get_inventory_not_found_config()


def load_not_found_backlog():
    """
    Carga backlog not_found + scope refinado desde MySQL.
    """
    conn = get_db_connection(target="wansoft")

    query = """
    SELECT
        b.id,
        b.odoo_product_id,
        b.odoo_product_name,
        b.product_code,
        b.location_name,
        b.stock_qty,
        b.backlog_bucket,
        s.category_name,
        s.inventory_scope,
        s.refined_inventory_scope,
        s.refined_scope_source,
        s.refined_scope_status
    FROM odoo_inventory_backlog b
    LEFT JOIN odoo_inventory_scope_classification s
        ON b.odoo_product_id = s.odoo_product_id
    """

    df = pd.read_sql(query, conn)
    conn.close()

    return df


def classify_not_found_row(row):
    """
    Clasifica el not_found para orientar el siguiente paso.
    """
    product_name = normalize(row.get("odoo_product_name"))
    category_name = normalize(row.get("category_name"))
    refined_scope = normalize(row.get("refined_inventory_scope"))

    # 1) Si sigue claramente fuera de scope principal
    if refined_scope in ["bodegon", "empanadas", "bodegon_candidate", "empanadas_candidate"]:
        return {
            "not_found_classification": "excluded_by_scope",
            "suggested_next_action": "keep_outside_restaurants_etl"
        }

    # 2) Shared cross company -> mejor candidato a ampliar diccionario
    if refined_scope == "shared_cross_company":
        return {
            "not_found_classification": "dictionary_candidate_shared",
            "suggested_next_action": "review_for_dictionary_mapping"
        }

    # 3) Review scope -> primero refinar scope
    if refined_scope == "review_scope":
        return {
            "not_found_classification": "needs_scope_refinement",
            "suggested_next_action": "refine_scope_before_mapping"
        }

    # 4) Categorías que parecen inventory comunes pero aún no mapeados
    if any(k in category_name for k in [
        "aceites", "frutas y verduras", "condimentos", "lacteos",
        "quesos", "carne", "pescados", "mariscos", "material de empaque",
        "agua", "cafe", "te", "conservas", "higienicos desechables",
        "quimicos", "jarceria", "botiquin", "aderezos", "salsas"
    ]):
        return {
            "not_found_classification": "likely_inventory_mapping_gap",
            "suggested_next_action": "review_name_and_add_to_dictionary"
        }

    # 5) Productos que parecen gastos/servicios/equipo
    if any(k in category_name for k in [
        "servicio", "equipo para salon", "otros ingresos", "gastos salon", "cristaleria"
    ]) or any(k in product_name for k in [
        "atril", "banderin", "base de metal", "atomizador", "aplicadores", "cofia", "guante"
    ]):
        return {
            "not_found_classification": "non_inventory_operational_item",
            "suggested_next_action": "exclude_from_inventory_mapping"
        }

    # 6) Fallback
    return {
        "not_found_classification": "manual_review",
        "suggested_next_action": "manual_review"
    }


def build_inventory_not_found_analysis():
    config = get_env_config()
    df = load_not_found_backlog()

    if df is None or df.empty:
        return pd.DataFrame()

    # filtrar por bucket
    df = df[df["backlog_bucket"] == config["bucket"]].copy()

    # include scopes
    if config["scope_include"]:
        df = df[df["refined_inventory_scope"].isin(config["scope_include"])].copy()

    # exclude scopes
    if config["scope_exclude"]:
        df = df[~df["refined_inventory_scope"].isin(config["scope_exclude"])].copy()

    if df.empty:
        return pd.DataFrame()

    classified = df.apply(classify_not_found_row, axis=1, result_type="expand")
    result = pd.concat([df.reset_index(drop=True), classified.reset_index(drop=True)], axis=1)

    return result


def summarize_inventory_not_found(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return {
            "summary": pd.DataFrame(),
            "by_scope": pd.DataFrame(),
            "by_category": pd.DataFrame(),
            "sample": pd.DataFrame()
        }

    total = len(df)

    summary = (
        df["not_found_classification"]
        .value_counts()
        .reset_index()
    )
    summary.columns = ["not_found_classification", "count"]
    summary["pct"] = (summary["count"] / total * 100).round(2)

    by_scope = (
        df.groupby(["refined_inventory_scope", "not_found_classification"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(by="count", ascending=False)
    )

    by_category = (
        df.groupby(["category_name", "not_found_classification"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(by="count", ascending=False)
        .head(50)
    )

    sample = df[[
        "odoo_product_id",
        "odoo_product_name",
        "category_name",
        "refined_inventory_scope",
        "not_found_classification",
        "suggested_next_action",
        "stock_qty",
        "location_name"
    ]].head(50)

    return {
        "summary": summary,
        "by_scope": by_scope,
        "by_category": by_category,
        "sample": sample
    }


def export_inventory_not_found_analysis(df: pd.DataFrame):
    config = get_env_config()

    if df is None or df.empty:
        print("No hay not_found para exportar.")
        return

    if not config["export_enabled"]:
        print("Export deshabilitado por configuración.")
        return

    file_name = config["export_file"]
    df.to_csv(file_name, index=False, encoding="utf-8-sig")

    print(f"Archivo exportado: {file_name}")
    print(f"Total registros exportados: {len(df)}")