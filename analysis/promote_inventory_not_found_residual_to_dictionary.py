import pandas as pd
from core.database.mysql import get_mysql_connection as get_db_connection


def sql_safe(value):
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip()
        return value if value else None
    return value


def map_status(action: str) -> str:
    if action == "approved_candidate":
        return "approved"
    if action == "review_candidate":
        return "pending_review"
    if action == "historical_candidate":
        return "historical_only"
    if action == "historical_stock_review":
        return "historical_only"
    return "unresolved"


def promote_inventory_not_found_residual_to_dictionary():
    """
    Promueve el bridge residual al diccionario de inventory.
    - NO trunca inventory_mapping_dictionary
    - Hace UPSERT
    """

    conn = get_db_connection(target="wansoft")

    query = """
    SELECT
        r.odoo_product_id,
        r.odoo_product_name,
        r.category_name,
        r.wansoft_code,
        r.wansoft_product_name,
        r.wansoft_department,
        r.lifecycle_candidate,
        r.similarity_score,
        r.suggested_action
    FROM inventory_not_found_residual_bridge r
    """

    df = pd.read_sql(query, conn)

    if df.empty:
        print("No hay registros residuales para promover.")
        conn.close()
        return

    df["mapping_status"] = df["suggested_action"].apply(map_status)
    df["mapping_source"] = "residual_bridge"

    cursor = conn.cursor()

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
        notes,
        inventory_scope,
        scope_source,
        scope_status
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        odoo_product_id = VALUES(odoo_product_id),
        odoo_category_name = VALUES(odoo_category_name),
        wansoft_product_name = VALUES(wansoft_product_name),
        wansoft_department = VALUES(wansoft_department),
        mapping_source = VALUES(mapping_source),
        mapping_status = VALUES(mapping_status),
        lifecycle_candidate = VALUES(lifecycle_candidate),
        similarity_score = VALUES(similarity_score),
        notes = VALUES(notes),
        inventory_scope = VALUES(inventory_scope),
        scope_source = VALUES(scope_source),
        scope_status = VALUES(scope_status),
        updated_at = CURRENT_TIMESTAMP
    """

    rows = []
    for _, row in df.iterrows():
        rows.append((
            "inventory",
            sql_safe(row.get("odoo_product_id")),
            sql_safe(row.get("odoo_product_name")),
            sql_safe(row.get("category_name")),
            sql_safe(row.get("wansoft_code")),
            sql_safe(row.get("wansoft_product_name")),
            sql_safe(row.get("wansoft_department")),
            "residual_bridge",
            sql_safe(row.get("mapping_status")),
            sql_safe(row.get("lifecycle_candidate")),
            sql_safe(row.get("similarity_score")),
            f"suggested_action={row.get('suggested_action')}; promoted_from=inventory_not_found_residual_bridge",
            "shared_cross_company",
            "residual_bridge",
            "approved" if row.get("suggested_action") == "approved_candidate" else "pending_review"
        ))

    cursor.executemany(insert_sql, rows)
    conn.commit()

    print(f"Promovidos {len(rows)} registros residuales a inventory_mapping_dictionary.")

    cursor.close()
    conn.close()