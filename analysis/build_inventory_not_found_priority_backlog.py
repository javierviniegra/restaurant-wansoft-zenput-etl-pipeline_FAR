import pandas as pd
from core.database.mysql import get_mysql_connection as get_db_connection


# =========================
# PRIORITY CATEGORIES
# =========================

P1_CATEGORIES = {
    "Frutas y Verduras",
    "Semillas, Especias y Condimentos",
    "Cafe y te",
    "Materia prima",
    "Lácteos",
    "Aceites",
    "Otros lácteos",
}

P2_CATEGORIES = {
    "Tequila",
    "Material de Empaque",
    "Endulcorantes y azucares",
    "Queso",
    "Pasteles",
    "Enlatados y Conservas",
    "Jugos",
}

P3_CATEGORIES = {
    "Loza",
    "Pasteleria Preparados",
    "Licores",
    "Carne de res",
    "Helados",
    "Pan",
    "Químicos",
    "Ron",
}


def load_not_found_rows():
    """
    Carga filas del backlog not_found y les une la clasificación de scope.
    Solo toma shared_cross_company porque ese es el backlog útil actual.
    """
    conn = get_db_connection(target="wansoft")

    query = """
    SELECT
        b.odoo_product_id,
        b.odoo_product_name,
        s.category_name,
        s.refined_inventory_scope,
        'dictionary_candidate_shared' AS not_found_classification,
        b.location_name,
        b.stock_qty
    FROM odoo_inventory_backlog b
    LEFT JOIN odoo_inventory_scope_classification s
        ON b.odoo_product_id = s.odoo_product_id
    WHERE b.backlog_bucket = 'not_found'
      AND s.refined_inventory_scope = 'shared_cross_company'
    """

    df = pd.read_sql(query, conn)
    conn.close()

    return df


def assign_priority(category_name: str):
    """
    Asigna bucket de prioridad por categoría.
    """
    if category_name in P1_CATEGORIES:
        return ("P1", "High-volume shared inventory category")

    if category_name in P2_CATEGORIES:
        return ("P2", "Medium-priority shared inventory category")

    if category_name in P3_CATEGORIES:
        return ("P3", "Lower-priority or more ambiguous category")

    return ("P4", "Manual review category outside current prioritization")


def build_inventory_not_found_priority_backlog():
    """
    Construye backlog priorizado de not_found a nivel producto único,
    no a nivel fila por ubicación.
    """
    df = load_not_found_rows()

    if df is None or df.empty:
        return pd.DataFrame(columns=[
            "odoo_product_id",
            "odoo_product_name",
            "category_name",
            "refined_inventory_scope",
            "not_found_classification",
            "row_count",
            "location_count",
            "total_abs_stock_qty",
            "priority_bucket",
            "priority_reason"
        ])

    df["stock_qty"] = pd.to_numeric(df["stock_qty"], errors="coerce").fillna(0)
    df["abs_stock_qty"] = df["stock_qty"].abs()

    out = (
        df.groupby(
            [
                "odoo_product_id",
                "odoo_product_name",
                "category_name",
                "refined_inventory_scope",
                "not_found_classification"
            ],
            dropna=False,
            as_index=False
        )
        .agg(
            row_count=("odoo_product_id", "size"),
            location_count=("location_name", "nunique"),
            total_abs_stock_qty=("abs_stock_qty", "sum")
        )
    )

    priorities = out["category_name"].apply(assign_priority)

    out["priority_bucket"] = priorities.apply(lambda x: x[0])
    out["priority_reason"] = priorities.apply(lambda x: x[1])

    # Orden sugerido
    bucket_order = {"P1": 1, "P2": 2, "P3": 3, "P4": 4}
    out["priority_order"] = out["priority_bucket"].map(bucket_order).fillna(99)

    out = out.sort_values(
        by=["priority_order", "row_count", "total_abs_stock_qty"],
        ascending=[True, False, False]
    ).drop(columns=["priority_order"])

    return out