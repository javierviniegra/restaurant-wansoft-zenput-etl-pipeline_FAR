import pandas as pd
from core.database.mysql import get_mysql_connection as get_db_connection


def normalize(text):
    if pd.isna(text) or text is None:
        return ""
    return str(text).strip().lower()


def refine_review_scope_row_v2(row):
    """
    Segunda iteración de refinamiento SOLO para filas que
    siguen en refined_inventory_scope = 'review_scope'.

    Objetivo:
    - mover alcoholes/aderezos/preparados a shared_cross_company
    - mover químicos/botiquín/equipo salón/etc a operational_non_inventory
    - dejar el residuo ambiguo en review_scope
    """

    product_name = normalize(row.get("product_name"))
    category_name = normalize(row.get("category_name"))

    # =============================
    # 1) ALCOHOL / DESTILADOS / LICORES
    # -> shared_cross_company
    # =============================
    alcohol_category_keywords = [
        "ron", "mezcal", "vodka", "licores", "aperitivos",
        "whisky", "brandy", "tequila", "vino", "cerveza"
    ]

    alcohol_name_keywords = [
        "bacardi", "absolut", "conejos", "amaretto", "anis",
        "aperol", "appleton", "bitter", "jose cuervo",
        "1800", "whisky", "brandy", "vodka", "mezcal", "ron",
        "ginebra", "tequila", "chandon", "moet"
    ]

    if any(k in category_name for k in alcohol_category_keywords) or \
       any(k in product_name for k in alcohol_name_keywords):
        return {
            "refined_inventory_scope_v2": "shared_cross_company",
            "refined_scope_source_v2": "review_scope_alcohol_heuristic",
            "refined_scope_status_v2": "pending_review",
            "refined_notes_v2": "Alcohol/destilados heuristic"
        }

    # =============================
    # 2) ADEREZOS / SALSAS / PREPARADOS
    # -> shared_cross_company
    # =============================
    prepared_category_keywords = [
        "aderezos",
        "salsas preparados",
        "pasteleria preparados",
        "materia prima",
        "all"
    ]

    prepared_name_keywords = [
        "aderezo",
        "pasta para mole",
        "mole",
        "salsa",
        "consome",
        "consomé",
        "base",
        "saborizante",
        "vinagre",
        "dulce de leche"
    ]

    if any(k in category_name for k in prepared_category_keywords) or \
       any(k in product_name for k in prepared_name_keywords):
        return {
            "refined_inventory_scope_v2": "shared_cross_company",
            "refined_scope_source_v2": "review_scope_prepared_heuristic",
            "refined_scope_status_v2": "pending_review",
            "refined_notes_v2": "Prepared ingredients / bases heuristic"
        }

    # =============================
    # 3) QUÍMICOS / BOTIQUÍN / JARCERÍA / EQUIPO SALÓN / OPERATIVOS
    # -> operational_non_inventory
    # =============================
    non_inventory_category_keywords = [
        "quimicos",
        "articulos para botiquin",
        "equipo para salón",
        "equipo para salon",
        "jarcería",
        "jarceria",
        "servicio",
        "cristalería",
        "cristaleria",
        "otros ingresos",
        "gastos salon",
        "loza"
    ]

    non_inventory_name_keywords = [
        "acido muriatico",
        "alcohol 96",
        "alcohol solido",
        "algodon",
        "algodón",
        "aplicadores",
        "apósito",
        "aposito",
        "abatelenguas",
        "atomizador",
        "atril",
        "banderin",
        "banderín",
        "base de metal",
        "cofia",
        "guante",
        "crayolas",
        "baunometro",
        "baunómetro",
        "papel higienico",
        "papel higiénico",
    ]

    if any(k in category_name for k in non_inventory_category_keywords) or \
       any(k in product_name for k in non_inventory_name_keywords):
        return {
            "refined_inventory_scope_v2": "operational_non_inventory",
            "refined_scope_source_v2": "review_scope_non_inventory_heuristic",
            "refined_scope_status_v2": "pending_review",
            "refined_notes_v2": "Operational/non-inventory heuristic"
        }

    # =============================
    # 4) RESTAURANTES candidate
    # -> restaurantes_candidate
    # =============================
    restaurantes_category_keywords = [
        "refrescos",
        "pv bebidas sin alcohol",
        "pv carne",
        "pv postres",
        "pv quesos",
        "tortillas"
    ]

    restaurantes_name_keywords = [
        "coca cola",
        "fanta",
        "fresca",
        "ginger ale",
        "mineral",
        "sprite",
        "mundet"
    ]

    if any(k in category_name for k in restaurantes_category_keywords) or \
       any(k in product_name for k in restaurantes_name_keywords):
        return {
            "refined_inventory_scope_v2": "restaurantes_candidate",
            "refined_scope_source_v2": "review_scope_restaurantes_heuristic",
            "refined_scope_status_v2": "pending_review",
            "refined_notes_v2": "Restaurantes heuristic"
        }

    # =============================
    # 5) Sigue ambiguo
    # =============================
    return {
        "refined_inventory_scope_v2": "review_scope",
        "refined_scope_source_v2": "review_scope_v2_fallback",
        "refined_scope_status_v2": "pending_review",
        "refined_notes_v2": "Still ambiguous after second refinement layer"
    }


def build_review_scope_refinement_v2():
    """
    Toma SOLO filas que siguen en review_scope y aplica segunda capa.
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

    refined = df.apply(refine_review_scope_row_v2, axis=1, result_type="expand")

    result = pd.concat([df.reset_index(drop=True), refined.reset_index(drop=True)], axis=1)

    return result


def summarize_review_scope_refinement_v2(df: pd.DataFrame) -> pd.DataFrame:
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