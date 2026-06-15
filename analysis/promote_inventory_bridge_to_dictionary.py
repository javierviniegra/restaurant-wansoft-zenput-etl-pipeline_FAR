import pandas as pd
from core.database.mysql import get_mysql_connection as get_db_connection


def sql_safe(value):
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip()
        return value if value else None
    return value


def action_priority(action: str) -> int:
    """
    Menor número = mayor prioridad.
    """
    priorities = {
        "assign_default_code": 1,
        "review_before_assigning_code": 2,
        "historical_with_remaining_stock_review": 3,
        "keep_as_historical": 4
    }
    return priorities.get(action, 99)


def map_status(action: str) -> str:
    if action == "assign_default_code":
        return "approved"
    if action == "review_before_assigning_code":
        return "pending_review"
    if action in ("historical_with_remaining_stock_review", "keep_as_historical"):
        return "historical_only"
    return "unresolved"


def promote_inventory_bridge_to_dictionary():
    conn = get_db_connection(target="wansoft")

    query = """
    SELECT
        odoo_product_id,
        odoo_product_name,
        odoo_category_name,
        raw_classification,
        wansoft_code,
        wansoft_product_name,
        wansoft_department,
        wansoft_lifecycle_candidate,
        similarity_score,
        suggested_action
    FROM inventory_bridge_report
    """

    df = pd.read_sql(query, conn)

    if df.empty:
        print("No hay bridge report para promover.")
        conn.close()
        return

    # -----------------------------
    # Limpieza / normalización
    # -----------------------------
    df["domain"] = "inventory"
    df["mapping_status"] = df["suggested_action"].apply(map_status)
    df["mapping_source"] = "bridge_report"

    df["similarity_score"] = pd.to_numeric(df["similarity_score"], errors="coerce")
    df["priority"] = df["suggested_action"].apply(action_priority)

    # -----------------------------
    # DEDUPE CRÍTICO
    # Mantener mejor fila por:
    # domain + odoo_product_name + wansoft_code
    # -----------------------------
    df = df.sort_values(
        by=["domain", "odoo_product_name", "wansoft_code", "priority", "similarity_score"],
        ascending=[True, True, True, True, False]
    )

    df = df.drop_duplicates(
        subset=["domain", "odoo_product_name", "wansoft_code"],
        keep="first"
    ).copy()

    cursor = conn.cursor()

    # Refrescar tabla completa
    cursor.execute("TRUNCATE TABLE inventory_mapping_dictionary")

    insert_sql = """
    INSERT INTO inventory_mapping_dictionary (
        domain,
        odoo_product_id,
        odoo_product_name,
        odoo_category_name,
        wansoft_code,
        wansoft_product_name,
        wansoft_department,
        mapping_source,
        mapping_status,
        lifecycle_candidate,
        similarity_score,
        notes
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    rows = []
    for _, row in df.iterrows():
        rows.append((
            "inventory",
            sql_safe(row.get("odoo_product_id")),
            sql_safe(row.get("odoo_product_name")),
            sql_safe(row.get("odoo_category_name")),
            sql_safe(row.get("wansoft_code")),
            sql_safe(row.get("wansoft_product_name")),
            sql_safe(row.get("wansoft_department")),
            "bridge_report",
            sql_safe(row.get("mapping_status")),
            sql_safe(row.get("wansoft_lifecycle_candidate")),
            sql_safe(row.get("similarity_score")),
            f"suggested_action={row.get('suggested_action')}; raw_classification={row.get('raw_classification')}"
        ))

    cursor.executemany(insert_sql, rows)
    conn.commit()

    print(f"Insertados {len(rows)} registros en inventory_mapping_dictionary.")

    cursor.close()
    conn.close()