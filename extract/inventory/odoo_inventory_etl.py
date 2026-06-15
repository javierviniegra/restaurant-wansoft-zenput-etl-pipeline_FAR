import pandas as pd

from core.database.mysql import get_mysql_connection as get_db_connection
from extract.inventory.odoo_inventory import extract_odoo_inventory
from extract.utils.inventory_dictionary_wrapper import (
    apply_inventory_dictionary,
    split_inventory_dictionary_result,
    summarize_inventory_dictionary_application
)
from extract.utils.inventory_scope_lookup import load_inventory_scope_classification


def sql_safe(value):
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip()
        return value if value else None
    if isinstance(value, bool):
        return int(value)
    return value


def _prepare_inventory_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ajusta columnas del extractor Odoo y consolida el snapshot
    para evitar duplicados por producto + ubicación.
    """

    out = df.copy()

    # Renombrar si viene del extractor actual
    if "source_product_id" in out.columns and "odoo_product_id" not in out.columns:
        out = out.rename(columns={"source_product_id": "odoo_product_id"})

    # Tipos seguros
    out["odoo_product_id"] = pd.to_numeric(out["odoo_product_id"], errors="coerce")
    out["source_location_id"] = pd.to_numeric(out["source_location_id"], errors="coerce")
    out["stock_qty"] = pd.to_numeric(out["stock_qty"], errors="coerce").fillna(0)

    # Consolidar por producto + ubicación
    group_cols = [
        "odoo_product_id",
        "product_name",
        "product_code",
        "source_location_id",
        "location_name"
    ]

    out = (
        out.groupby(group_cols, dropna=False, as_index=False)
           .agg(stock_qty=("stock_qty", "sum"))
    )

    return out


def _merge_inventory_scope(df: pd.DataFrame) -> pd.DataFrame:
    """
    Une el snapshot Odoo con la clasificación de scope.
    """
    df_scope = load_inventory_scope_classification()

    if df_scope is None or df_scope.empty:
        df["inventory_scope"] = None
        df["scope_source"] = None
        df["scope_status"] = None
        df["refined_inventory_scope"] = None
        df["refined_scope_source"] = None
        df["refined_scope_status"] = None
        return df

    out = df.merge(
        df_scope[[
            "odoo_product_id",
            "inventory_scope",
            "scope_source",
            "scope_status",
            "refined_inventory_scope",
            "refined_scope_source",
            "refined_scope_status"
        ]],
        on="odoo_product_id",
        how="left"
    )

    return out


def _ensure_backlog_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rellena columnas de mapping cuando el DataFrame aún no pasó por el wrapper.
    Evita fillna(None), que rompe en pandas.
    """
    out = df.copy()

    default_columns = {
        "mapping_found": False,
        "lookup_method": None,
        "mapping_status": None,
        "usable_for_etl": False,
        "wansoft_code": None,
        "wansoft_product_name": None,
        "wansoft_department": None,
        "lifecycle_candidate": None,
        "similarity_score": None,
        "mapping_notes": None,
    }

    for col, default_value in default_columns.items():
        if col not in out.columns:
            out[col] = default_value
        else:
            # Solo rellenar si hay un valor real por defecto distinto de None
            if default_value is not None:
                out[col] = out[col].fillna(default_value)

    return out


def _save_snapshot(df: pd.DataFrame):
    if df is None or df.empty:
        print("No hay filas aprobadas para guardar en odoo_inventory_snapshot.")
        return 0

    # Defensa extra por si algo llega duplicado todavía
    df = df.copy()

    df["odoo_product_id"] = pd.to_numeric(df["odoo_product_id"], errors="coerce")
    df["source_location_id"] = pd.to_numeric(df["source_location_id"], errors="coerce")
    df["stock_qty"] = pd.to_numeric(df["stock_qty"], errors="coerce").fillna(0)

    group_cols = [
        "odoo_product_id",
        "product_name",
        "product_code",
        "source_location_id",
        "location_name",
        "mapping_found",
        "lookup_method",
        "mapping_status",
        "usable_for_etl",
        "wansoft_code",
        "wansoft_product_name",
        "wansoft_department",
        "lifecycle_candidate",
        "similarity_score",
        "mapping_notes"
    ]

    df = (
        df.groupby(group_cols, dropna=False, as_index=False)
          .agg(stock_qty=("stock_qty", "sum"))
    )

    conn = get_db_connection(target="wansoft")
    cursor = conn.cursor()

    cursor.execute("TRUNCATE TABLE odoo_inventory_snapshot")

    insert_sql = """
    INSERT INTO odoo_inventory_snapshot (
        odoo_product_id,
        odoo_product_name,
        product_code,
        source_location_id,
        location_name,
        stock_qty,
        mapping_found,
        lookup_method,
        mapping_status,
        usable_for_etl,
        wansoft_code,
        wansoft_product_name,
        wansoft_department,
        lifecycle_candidate,
        similarity_score,
        mapping_notes
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    rows = []
    for _, row in df.iterrows():
        rows.append((
            sql_safe(row.get("odoo_product_id")),
            sql_safe(row.get("product_name")),
            sql_safe(row.get("product_code")),
            sql_safe(row.get("source_location_id")),
            sql_safe(row.get("location_name")),
            sql_safe(row.get("stock_qty")),
            sql_safe(row.get("mapping_found")),
            sql_safe(row.get("lookup_method")),
            sql_safe(row.get("mapping_status")),
            sql_safe(row.get("usable_for_etl")),
            sql_safe(row.get("wansoft_code")),
            sql_safe(row.get("wansoft_product_name")),
            sql_safe(row.get("wansoft_department")),
            sql_safe(row.get("lifecycle_candidate")),
            sql_safe(row.get("similarity_score")),
            sql_safe(row.get("mapping_notes")),
        ))

    cursor.executemany(insert_sql, rows)
    conn.commit()
    inserted = len(rows)

    cursor.close()
    conn.close()

    print(f"Insertados {inserted} registros en odoo_inventory_snapshot.")
    return inserted


def _save_backlog(df: pd.DataFrame, backlog_bucket: str):
    if df is None or df.empty:
        return 0

    df = _ensure_backlog_columns(df)

    conn = get_db_connection(target="wansoft")
    cursor = conn.cursor()

    insert_sql = """
    INSERT INTO odoo_inventory_backlog (
        odoo_product_id,
        odoo_product_name,
        product_code,
        source_location_id,
        location_name,
        stock_qty,
        mapping_found,
        lookup_method,
        mapping_status,
        usable_for_etl,
        wansoft_code,
        wansoft_product_name,
        wansoft_department,
        lifecycle_candidate,
        similarity_score,
        mapping_notes,
        backlog_bucket
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    rows = []
    for _, row in df.iterrows():
        rows.append((
            sql_safe(row.get("odoo_product_id")),
            sql_safe(row.get("product_name")),
            sql_safe(row.get("product_code")),
            sql_safe(row.get("source_location_id")),
            sql_safe(row.get("location_name")),
            sql_safe(row.get("stock_qty")),
            sql_safe(row.get("mapping_found")),
            sql_safe(row.get("lookup_method")),
            sql_safe(row.get("mapping_status")),
            sql_safe(row.get("usable_for_etl")),
            sql_safe(row.get("wansoft_code")),
            sql_safe(row.get("wansoft_product_name")),
            sql_safe(row.get("wansoft_department")),
            sql_safe(row.get("lifecycle_candidate")),
            sql_safe(row.get("similarity_score")),
            sql_safe(row.get("mapping_notes")),
            backlog_bucket
        ))

    cursor.executemany(insert_sql, rows)
    conn.commit()
    inserted = len(rows)

    cursor.close()
    conn.close()

    print(f"Insertados {inserted} registros en odoo_inventory_backlog [{backlog_bucket}].")
    return inserted


def run_odoo_inventory_etl():
    """
    ETL real de inventory Odoo -> MySQL usando inventory_mapping_dictionary
    y clasificación de scope.
    """

    print("=== ODOO INVENTORY ETL START ===")

    # 1. Extract
    df_odoo = extract_odoo_inventory()
    df_odoo = _prepare_inventory_dataframe(df_odoo)

    # 2. Merge refined scope
    df_odoo = _merge_inventory_scope(df_odoo)

    # 3. Separar universos
    # A) Productos de restaurantes provenientes del universo de ventas:
    #    NO pasan por inventory dictionary
    df_sales_reference = df_odoo[
        (df_odoo["refined_inventory_scope"] == "restaurantes") &
        (df_odoo["scope_source"] == "sales_reference")
    ].copy()

    # B) Candidatos reales para inventory dictionary:
    #    SOLO shared_cross_company
    df_inventory_candidates = df_odoo[
        df_odoo["refined_inventory_scope"].isin(["shared_cross_company"])
    ].copy()

    # C) Scope backlog explícito:
    #    bodegon, empanadas y review_scope
    df_scope_backlog = df_odoo[
        df_odoo["refined_inventory_scope"].isin([
            "bodegon",
            "empanadas",
            "bodegon_candidate",
            "empanadas_candidate",
            "review_scope"
        ])
    ].copy()

    print("\n--- SCOPE COUNTS ---")
    print(f"sales_reference_rows: {len(df_sales_reference)}")
    print(f"inventory_candidates_rows: {len(df_inventory_candidates)}")
    print(f"scope_backlog_rows: {len(df_scope_backlog)}")

    # 4. Apply dictionary SOLO a shared_cross_company
    df_mapped = apply_inventory_dictionary(
        df_odoo_inventory=df_inventory_candidates,
        product_name_col="product_name",
        odoo_product_id_col="odoo_product_id",
        allow_pending=False,
        allow_historical=False
    )

    # 5. Summary
    summary = summarize_inventory_dictionary_application(df_mapped)
    print("\n--- ETL SUMMARY ---")
    print(summary.to_string(index=False))

    # 6. Partition
    parts = split_inventory_dictionary_result(df_mapped)

    approved_rows = parts["approved_rows"].copy()
    pending_rows = parts["pending_rows"].copy()
    historical_rows = parts["historical_rows"].copy()
    not_found_rows = parts["not_found_rows"].copy()

    # 7. Refrescar backlog
    conn = get_db_connection(target="wansoft")
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE odoo_inventory_backlog")
    conn.commit()
    cursor.close()
    conn.close()

    # 8. Guardar backlog de scope primero
    if not df_sales_reference.empty:
        _save_backlog(df_sales_reference, "scope_restaurantes_sales_reference")

    if not df_scope_backlog.empty:
        for scope_name, df_scope_part in df_scope_backlog.groupby("refined_inventory_scope"):
            _save_backlog(df_scope_part, f"scope_{scope_name}")

    # 9. Guardar snapshot aprobado
    inserted_snapshot = _save_snapshot(approved_rows)

    # 10. Guardar backlog del diccionario
    inserted_pending = _save_backlog(pending_rows, "pending_review")
    inserted_historical = _save_backlog(historical_rows, "historical_only")
    inserted_not_found = _save_backlog(not_found_rows, "not_found")

    print("\n--- ETL COUNTS ---")
    print(f"approved_rows: {len(approved_rows)}")
    print(f"pending_rows: {len(pending_rows)}")
    print(f"historical_rows: {len(historical_rows)}")
    print(f"not_found_rows: {len(not_found_rows)}")

    print("=== ODOO INVENTORY ETL END ✅ ===")

    return {
        "summary": summary,
        "approved_rows": approved_rows,
        "pending_rows": pending_rows,
        "historical_rows": historical_rows,
        "not_found_rows": not_found_rows,
        "snapshot_inserted": inserted_snapshot,
        "pending_inserted": inserted_pending,
        "historical_inserted": inserted_historical,
        "not_found_inserted": inserted_not_found,
    }