import pandas as pd

from core.database.mysql import get_mysql_connection as get_db_connection
from analysis.build_product_mapping import build_product_mapping


def sql_safe(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, str):
        value = value.strip()
        return value if value else None
    return value


def save_product_mapping(threshold=95):
    """
    Runs build_product_mapping() and upserts every row that has a wansoft_code
    (exact_code / exact_code_base / fuzzy_name -- i.e. everything except
    odoo_no_code, which has nothing to write) into inventory_mapping_dictionary.

    Per docs/purchases-product-mapping-policy.md, this NEVER auto-promotes a
    row to mapping_status='approved' on its own -- only a literal exact_code
    match (wansoft_code == odoo_code, the one case that already qualifies as
    an "explicit reference") keeps the 'approved' status build_product_mapping
    assigns it. Everything else (exact_code_base, fuzzy_name) is written as
    'pending_review' for a human to promote. If a row was already reviewed
    (mapping_status IN ('approved', 'rejected') from a previous run), that
    human decision is preserved -- a re-suggestion never downgrades it.
    """
    df = build_product_mapping(threshold=threshold)

    df = df[df["wansoft_code"].notna()].copy()

    if df.empty:
        print("No hay matches con wansoft_code para guardar.")
        return 0

    conn = get_db_connection(target="wansoft")
    cursor = conn.cursor()

    upsert_sql = """
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
        similarity_score,
        notes
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        -- A row a human already reviewed (approved/rejected) is left
        -- completely untouched, not just its mapping_status -- a bug fixed
        -- 2026-09-15 after the first run of this job overwrote
        -- mapping_source on 77 already-approved rows (their approval status
        -- and the actual mapping content were never at risk, only the
        -- "which review batch approved this" attribution).
        odoo_product_id = IF(mapping_status IN ('approved', 'rejected'), odoo_product_id, VALUES(odoo_product_id)),
        odoo_category_name = IF(mapping_status IN ('approved', 'rejected'), odoo_category_name, VALUES(odoo_category_name)),
        wansoft_product_name = IF(mapping_status IN ('approved', 'rejected'), wansoft_product_name, VALUES(wansoft_product_name)),
        wansoft_department = IF(mapping_status IN ('approved', 'rejected'), wansoft_department, VALUES(wansoft_department)),
        mapping_source = IF(mapping_status IN ('approved', 'rejected'), mapping_source, VALUES(mapping_source)),
        mapping_status = IF(mapping_status IN ('approved', 'rejected'), mapping_status, VALUES(mapping_status)),
        similarity_score = IF(mapping_status IN ('approved', 'rejected'), similarity_score, VALUES(similarity_score)),
        notes = IF(mapping_status IN ('approved', 'rejected'), notes, VALUES(notes)),
        updated_at = IF(mapping_status IN ('approved', 'rejected'), updated_at, CURRENT_TIMESTAMP)
    """

    rows = []
    for _, r in df.iterrows():
        status = r["status"] if r["match_type"] == "exact_code" else "pending_review"

        rows.append((
            sql_safe("inventory"),
            sql_safe(r.get("odoo_product_id")),
            sql_safe(r["canonical_name"]),
            sql_safe(r.get("odoo_category_name")),
            sql_safe(r["wansoft_code"]),
            sql_safe(r["canonical_name"]),
            sql_safe(r.get("wansoft_department")),
            sql_safe(f"weekly_auto_match:{r['match_type']}"),
            sql_safe(status),
            sql_safe(r.get("confidence_score")),
            sql_safe(r.get("notes")),
        ))

    cursor.executemany(upsert_sql, rows)
    conn.commit()

    written = len(rows)

    cursor.close()
    conn.close()

    print(f"Upserted {written} filas en inventory_mapping_dictionary (pending_review salvo exact_code literal).")
    return written
