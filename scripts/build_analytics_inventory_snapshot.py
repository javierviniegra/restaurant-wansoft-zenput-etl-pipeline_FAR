
"""
Build analytics_inventory_snapshot.

This script creates and refreshes the first analytical inventory snapshot table.

Main rules:
- Source table is odoo_inventory_snapshot.
- Grain is 1 row = 1 source inventory snapshot row.
- Preserve every source row.
- Join dim_time through DATE(etl_loaded_at).
- Join dim_product through governed references only: odoo_product_id and wansoft_code.
- Do not join products by name.
- Do not infer company_source_key from location_name.
- Classify Odoo locations only as helper flags.
- Exclude not-ready rows from business views with flags, not by deletion.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Tuple

from core.database.mysql import get_db_connection
from analysis.build_inventory_company_source_eligibility_report import (
    classify_inventory_company_source,
)


TARGET_TABLE = "analytics_inventory_snapshot"
SOURCE_TABLE = "odoo_inventory_snapshot"
PRODUCT_TABLE = "dim_product"
TIME_TABLE = "dim_time"
LOCATION_MASTER_TABLE = "stg_odoo_inventory_location_master"
BATCH_SIZE = 5000


COMPANY_SOURCE_EXCLUDE_REASONS = {
    "internal_provider_excluded": "internal_provider_company",
    "out_of_scope_excluded": "out_of_scope_company",
    "parallel_diagnostic_odoo": "wansoft_is_official_source",
    "unmapped_location_pending_review": "unmapped_company_pending_review",
    "unknown_source_review": "unmapped_company_pending_review",
}


APPROVED_MAPPING_STATUSES = {
    "approved",
    "mapped",
    "valid",
    "ok",
    "complete",
    "completed",
    "active",
    "usable",
}

MAPPED_PRODUCT_STATUSES = {
    "mapped",
    "ok",
    "valid",
    "approved",
}

REVIEW_PRODUCT_STATUSES = {
    "review_required",
    "pending_review",
    "open_backlog",
    "backlog",
    "unmapped",
}


def table_exists(conn: Any, table_name: str) -> bool:
    query = """
        SELECT COUNT(1) AS total
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = %s
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, (table_name,))
    row = cursor.fetchone()
    cursor.close()
    return bool(row and int(row["total"]) > 0)


def get_table_columns(conn: Any, table_name: str) -> set[str]:
    query = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = %s
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, (table_name,))
    rows = cursor.fetchall()
    cursor.close()
    return {str(row["column_name"]) for row in rows}


def fetch_all_dict(conn: Any, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params or ())
    rows = cursor.fetchall()
    cursor.close()
    return rows


def normalize_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def normalize_key(value: Any) -> Optional[str]:
    text = normalize_text(value)
    if text is None:
        return None
    return text.lower()


def as_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float, Decimal)):
        return bool(value)

    text = str(value).strip().lower()

    if text in {"1", "true", "t", "yes", "y", "si", "sí", "approved", "mapped", "ok"}:
        return True

    if text in {"0", "false", "f", "no", "n", "none", "null", ""}:
        return False

    return None


def bool_to_int(value: Optional[bool]) -> Optional[int]:
    if value is None:
        return None
    return 1 if value else 0


def append_reason(existing: Optional[str], reason: str) -> str:
    if not existing:
        return reason

    parts = [part.strip() for part in existing.split("|") if part.strip()]

    if reason not in parts:
        parts.append(reason)

    return " | ".join(parts)


def parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)

    text = str(value).strip()

    if not text:
        return None

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(text[:26], fmt)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def date_key_from_datetime(value: Optional[datetime]) -> Optional[int]:
    if value is None:
        return None
    return int(value.strftime("%Y%m%d"))


def normalize_location(location_name: Any) -> Optional[str]:
    text = normalize_text(location_name)
    if text is None:
        return None
    return " ".join(text.lower().split())


def classify_location(location_name: Any) -> Dict[str, Any]:
    text = normalize_text(location_name) or ""
    normalized = normalize_location(text)
    lower = text.lower()

    if lower.startswith("virtual locations/"):
        location_usage_type = "virtual"
    elif lower.startswith("partners/"):
        location_usage_type = "partner"
    else:
        location_usage_type = "internal_or_unknown"

    return {
        "normalized_location_name": normalized,
        "location_usage_type": location_usage_type,
        "is_virtual_location": location_usage_type == "virtual",
        "is_partner_location": location_usage_type == "partner",
        "is_internal_location": location_usage_type == "internal_or_unknown",
    }


def recreate_table(conn: Any) -> None:
    cursor = conn.cursor()
    cursor.execute(f"DROP TABLE IF EXISTS {TARGET_TABLE}")

    ddl = f"""
    CREATE TABLE {TARGET_TABLE} (
        inventory_snapshot_analytical_key BIGINT AUTO_INCREMENT PRIMARY KEY,

        source_inventory_snapshot_id BIGINT NOT NULL,

        odoo_product_id VARCHAR(100) NULL,
        odoo_product_name VARCHAR(500) NULL,
        product_code VARCHAR(255) NULL,

        source_location_id VARCHAR(100) NULL,
        location_name VARCHAR(500) NULL,
        normalized_location_name VARCHAR(500) NULL,
        location_usage_type VARCHAR(100) NULL,
        is_virtual_location BOOLEAN NOT NULL DEFAULT FALSE,
        is_partner_location BOOLEAN NOT NULL DEFAULT FALSE,
        is_internal_location BOOLEAN NOT NULL DEFAULT FALSE,
        location_mapping_status VARCHAR(100) NOT NULL DEFAULT 'pending_company_mapping',

        company_source_key VARCHAR(255) NULL,
        company_mapping_status VARCHAR(100) NOT NULL DEFAULT 'pending_location_mapping',

        snapshot_date DATE NULL,
        snapshot_date_key INT NULL,
        etl_loaded_at DATETIME NULL,

        product_analytical_key BIGINT NULL,
        wansoft_code VARCHAR(255) NULL,
        wansoft_product_name VARCHAR(500) NULL,
        wansoft_department VARCHAR(255) NULL,
        product_identity_status VARCHAR(100) NULL,
        dim_product_mapping_status VARCHAR(100) NULL,
        is_product_mapped BOOLEAN NOT NULL DEFAULT FALSE,
        is_product_review_required BOOLEAN NOT NULL DEFAULT FALSE,
        include_product_in_business_views BOOLEAN NOT NULL DEFAULT TRUE,

        stock_qty DECIMAL(18,4) NULL,

        mapping_found BOOLEAN NULL,
        lookup_method VARCHAR(255) NULL,
        mapping_status VARCHAR(100) NULL,
        usable_for_etl BOOLEAN NULL,
        lifecycle_candidate VARCHAR(255) NULL,
        similarity_score DECIMAL(18,6) NULL,
        mapping_notes TEXT NULL,

        include_in_business_views BOOLEAN NOT NULL DEFAULT TRUE,
        exclude_reason VARCHAR(500) NULL,
        inventory_review_status VARCHAR(100) NULL,

        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

        UNIQUE KEY uq_analytics_inventory_snapshot_source_id (
            source_inventory_snapshot_id
        ),

        KEY idx_inventory_snapshot_date (
            snapshot_date_key
        ),

        KEY idx_inventory_snapshot_product (
            product_analytical_key
        ),

        KEY idx_inventory_snapshot_odoo_product (
            odoo_product_id
        ),

        KEY idx_inventory_snapshot_wansoft_code (
            wansoft_code
        ),

        KEY idx_inventory_snapshot_location (
            source_location_id
        ),

        KEY idx_inventory_snapshot_business_views (
            include_in_business_views
        ),

        KEY idx_inventory_snapshot_review_status (
            inventory_review_status
        )
    )
    """

    cursor.execute(ddl)
    conn.commit()
    cursor.close()


def load_valid_date_keys(conn: Any) -> set[int]:
    if not table_exists(conn, TIME_TABLE):
        return set()

    rows = fetch_all_dict(conn, f"SELECT date_key FROM {TIME_TABLE}")
    return {int(row["date_key"]) for row in rows if row.get("date_key") is not None}


def product_priority(row: Dict[str, Any]) -> Tuple[int, int, int, int]:
    is_product_mapped = as_bool(row.get("is_product_mapped"))
    include_product = as_bool(row.get("include_product_in_business_views"))
    is_review_required = as_bool(row.get("is_product_review_required"))

    identity_status = normalize_key(row.get("product_identity_status")) or ""
    mapping_status = normalize_key(row.get("dim_product_mapping_status") or row.get("mapping_status")) or ""

    return (
        1 if is_product_mapped else 0,
        1 if identity_status in MAPPED_PRODUCT_STATUSES else 0,
        1 if mapping_status in APPROVED_MAPPING_STATUSES else 0,
        1 if include_product and not is_review_required else 0,
    )


def load_product_indexes(conn: Any) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    if not table_exists(conn, PRODUCT_TABLE):
        return {}, {}

    rows = fetch_all_dict(conn, f"SELECT * FROM {PRODUCT_TABLE}")

    by_odoo: Dict[str, Dict[str, Any]] = {}
    by_wansoft: Dict[str, Dict[str, Any]] = {}

    for row in rows:
        odoo_key = normalize_key(row.get("odoo_product_id"))
        wansoft_key = normalize_key(row.get("wansoft_code"))

        if odoo_key:
            current = by_odoo.get(odoo_key)
            if current is None or product_priority(row) > product_priority(current):
                by_odoo[odoo_key] = row

        if wansoft_key:
            current = by_wansoft.get(wansoft_key)
            if current is None or product_priority(row) > product_priority(current):
                by_wansoft[wansoft_key] = row

    return by_odoo, by_wansoft


def get_dim_value(product: Optional[Dict[str, Any]], *names: str) -> Any:
    if product is None:
        return None

    for name in names:
        if name in product:
            return product.get(name)

    return None


def find_product(
    source_row: Dict[str, Any],
    by_odoo: Dict[str, Dict[str, Any]],
    by_wansoft: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    odoo_key = normalize_key(source_row.get("odoo_product_id"))
    if odoo_key and odoo_key in by_odoo:
        return by_odoo[odoo_key]

    wansoft_key = normalize_key(source_row.get("wansoft_code"))
    if wansoft_key and wansoft_key in by_wansoft:
        return by_wansoft[wansoft_key]

    return None


def source_mapping_is_approved(value: Any) -> bool:
    key = normalize_key(value)
    if key is None:
        return False
    return key in APPROVED_MAPPING_STATUSES


def determine_review_status(reasons: Optional[str]) -> str:
    if not reasons:
        return "ok"

    reason_parts = [part.strip() for part in reasons.split("|") if part.strip()]

    for preferred in [
        "invalid_snapshot_date",
        "orphan_product",
        "not_usable_for_etl",
        "mapping_not_approved",
        "product_review_required",
        "product_excluded",
        "internal_provider_company",
        "out_of_scope_company",
        "wansoft_is_official_source",
        "unmapped_company_pending_review",
    ]:
        if preferred in reason_parts:
            return preferred

    return "review_required"


def load_location_company_map(conn: Any) -> Dict[str, Optional[str]]:
    """
    Loads source_location_id -> odoo_company_name from
    stg_odoo_inventory_location_master (Paso 18.18), which reads
    company_id/company_name directly from Odoo's stock.location
    configuration.

    Returns an empty map when the staging table does not exist yet,
    so this build can still run before that step, with every row falling
    back to unmapped_company_pending_review.
    """
    if not table_exists(conn, LOCATION_MASTER_TABLE):
        return {}

    rows = fetch_all_dict(
        conn,
        f"SELECT source_location_id, odoo_company_name FROM {LOCATION_MASTER_TABLE}"
    )

    return {
        row["source_location_id"]: row["odoo_company_name"]
        for row in rows
        if row.get("source_location_id") is not None
    }


def resolve_company_source(
    source_location_id: Optional[str],
    location_company_map: Dict[str, Optional[str]],
) -> Tuple[Optional[str], str, bool, Optional[str]]:
    """
    Resolves company_source_key, final_inventory_source_status,
    include_final_company and an exclude_reason for a single inventory
    row, reusing the same classification already validated in Paso 18.19
    (analysis/build_inventory_company_source_eligibility_report.py).
    """
    odoo_company_name = location_company_map.get(source_location_id)

    classified = classify_inventory_company_source(
        {"odoo_company_name": odoo_company_name}
    )

    status = classified["final_inventory_source_status"]
    exclude_reason = COMPANY_SOURCE_EXCLUDE_REASONS.get(status)

    return (
        classified["company_source_key"],
        status,
        bool(classified["include_final_company"]),
        exclude_reason,
    )


def build_row(
    source_row: Dict[str, Any],
    product: Optional[Dict[str, Any]],
    valid_date_keys: set[int],
    location_company_map: Dict[str, Optional[str]],
) -> Dict[str, Any]:
    loaded_at = parse_datetime(source_row.get("etl_loaded_at"))
    snapshot_date_key = date_key_from_datetime(loaded_at)
    snapshot_date_value = loaded_at.date() if loaded_at else None
    date_is_valid = bool(snapshot_date_key and snapshot_date_key in valid_date_keys)

    location = classify_location(source_row.get("location_name"))

    product_analytical_key = get_dim_value(product, "product_analytical_key")
    product_identity_status = get_dim_value(product, "product_identity_status")
    dim_product_mapping_status = get_dim_value(product, "dim_product_mapping_status", "mapping_status")
    is_product_mapped = as_bool(get_dim_value(product, "is_product_mapped", "is_mapped"))
    is_product_review_required = as_bool(get_dim_value(product, "is_product_review_required", "is_review_required"))
    include_product_in_business_views = as_bool(get_dim_value(product, "include_product_in_business_views"))

    if include_product_in_business_views is None:
        include_product_in_business_views = True if product else False

    if is_product_mapped is None:
        identity_key = normalize_key(product_identity_status)
        is_product_mapped = bool(identity_key in MAPPED_PRODUCT_STATUSES)

    if is_product_review_required is None:
        identity_key = normalize_key(product_identity_status)
        mapping_key = normalize_key(dim_product_mapping_status)
        is_product_review_required = bool(identity_key in REVIEW_PRODUCT_STATUSES or mapping_key in REVIEW_PRODUCT_STATUSES)

    usable_for_etl = as_bool(source_row.get("usable_for_etl"))
    mapping_status = source_row.get("mapping_status")

    include_in_business_views = True
    exclude_reason: Optional[str] = None

    if not date_is_valid:
        include_in_business_views = False
        exclude_reason = append_reason(exclude_reason, "invalid_snapshot_date")

    if product_analytical_key is None:
        include_in_business_views = False
        exclude_reason = append_reason(exclude_reason, "orphan_product")

    if is_product_review_required:
        include_in_business_views = False
        exclude_reason = append_reason(exclude_reason, "product_review_required")

    if not include_product_in_business_views:
        include_in_business_views = False
        exclude_reason = append_reason(exclude_reason, "product_excluded")

    if usable_for_etl is not True:
        include_in_business_views = False
        exclude_reason = append_reason(exclude_reason, "not_usable_for_etl")

    if not source_mapping_is_approved(mapping_status):
        include_in_business_views = False
        exclude_reason = append_reason(exclude_reason, "mapping_not_approved")

    # Virtual/partner locations (e.g. "Virtual Locations/Inventory
    # adjustment", "Virtual Locations/Production", or a vendor/customer
    # counterpart location) are Odoo's double-entry bookkeeping
    # counterparts, not real physical stock on hand. classify_location()
    # already flags them; this was never checked here, so
    # analytics_inventory_balance was summing them alongside real
    # warehouse stock. Confirmed on Acoxpa 2026-08-31: virtual-location
    # rows alone (1893.92) roughly tripled the real internal-location
    # total (596.71) versus live Odoo (566.96, internal locations only).
    if location.get("is_virtual_location") or location.get("is_partner_location"):
        include_in_business_views = False
        exclude_reason = append_reason(exclude_reason, "non_internal_location")

    normalized_source_location_id = normalize_text(source_row.get("source_location_id"))

    (
        company_source_key,
        company_mapping_status,
        include_final_company,
        company_exclude_reason,
    ) = resolve_company_source(normalized_source_location_id, location_company_map)

    if not include_final_company:
        include_in_business_views = False
        if company_exclude_reason:
            exclude_reason = append_reason(exclude_reason, company_exclude_reason)

    inventory_review_status = determine_review_status(exclude_reason)

    return {
        "source_inventory_snapshot_id": source_row.get("id"),
        "odoo_product_id": normalize_text(source_row.get("odoo_product_id")),
        "odoo_product_name": source_row.get("odoo_product_name"),
        "product_code": source_row.get("product_code"),
        "source_location_id": normalized_source_location_id,
        "location_name": source_row.get("location_name"),
        "normalized_location_name": location["normalized_location_name"],
        "location_usage_type": location["location_usage_type"],
        "is_virtual_location": bool_to_int(location["is_virtual_location"]),
        "is_partner_location": bool_to_int(location["is_partner_location"]),
        "is_internal_location": bool_to_int(location["is_internal_location"]),
        "location_mapping_status": "pending_company_mapping",
        "company_source_key": company_source_key,
        "company_mapping_status": company_mapping_status,
        "snapshot_date": snapshot_date_value,
        "snapshot_date_key": snapshot_date_key,
        "etl_loaded_at": loaded_at,
        "product_analytical_key": product_analytical_key,
        "wansoft_code": source_row.get("wansoft_code") or get_dim_value(product, "wansoft_code"),
        "wansoft_product_name": source_row.get("wansoft_product_name") or get_dim_value(product, "wansoft_product_name"),
        "wansoft_department": source_row.get("wansoft_department") or get_dim_value(product, "wansoft_department"),
        "product_identity_status": product_identity_status,
        "dim_product_mapping_status": dim_product_mapping_status,
        "is_product_mapped": bool_to_int(is_product_mapped),
        "is_product_review_required": bool_to_int(is_product_review_required),
        "include_product_in_business_views": bool_to_int(include_product_in_business_views),
        "stock_qty": source_row.get("stock_qty"),
        "mapping_found": bool_to_int(as_bool(source_row.get("mapping_found"))),
        "lookup_method": source_row.get("lookup_method"),
        "mapping_status": mapping_status,
        "usable_for_etl": bool_to_int(usable_for_etl),
        "lifecycle_candidate": source_row.get("lifecycle_candidate"),
        "similarity_score": source_row.get("similarity_score"),
        "mapping_notes": source_row.get("mapping_notes"),
        "include_in_business_views": bool_to_int(include_in_business_views),
        "exclude_reason": exclude_reason,
        "inventory_review_status": inventory_review_status,
    }


def insert_rows(conn: Any, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return

    sql = f"""
    INSERT INTO {TARGET_TABLE} (
        source_inventory_snapshot_id,
        odoo_product_id,
        odoo_product_name,
        product_code,
        source_location_id,
        location_name,
        normalized_location_name,
        location_usage_type,
        is_virtual_location,
        is_partner_location,
        is_internal_location,
        location_mapping_status,
        company_source_key,
        company_mapping_status,
        snapshot_date,
        snapshot_date_key,
        etl_loaded_at,
        product_analytical_key,
        wansoft_code,
        wansoft_product_name,
        wansoft_department,
        product_identity_status,
        dim_product_mapping_status,
        is_product_mapped,
        is_product_review_required,
        include_product_in_business_views,
        stock_qty,
        mapping_found,
        lookup_method,
        mapping_status,
        usable_for_etl,
        lifecycle_candidate,
        similarity_score,
        mapping_notes,
        include_in_business_views,
        exclude_reason,
        inventory_review_status
    )
    VALUES (
        %(source_inventory_snapshot_id)s,
        %(odoo_product_id)s,
        %(odoo_product_name)s,
        %(product_code)s,
        %(source_location_id)s,
        %(location_name)s,
        %(normalized_location_name)s,
        %(location_usage_type)s,
        %(is_virtual_location)s,
        %(is_partner_location)s,
        %(is_internal_location)s,
        %(location_mapping_status)s,
        %(company_source_key)s,
        %(company_mapping_status)s,
        %(snapshot_date)s,
        %(snapshot_date_key)s,
        %(etl_loaded_at)s,
        %(product_analytical_key)s,
        %(wansoft_code)s,
        %(wansoft_product_name)s,
        %(wansoft_department)s,
        %(product_identity_status)s,
        %(dim_product_mapping_status)s,
        %(is_product_mapped)s,
        %(is_product_review_required)s,
        %(include_product_in_business_views)s,
        %(stock_qty)s,
        %(mapping_found)s,
        %(lookup_method)s,
        %(mapping_status)s,
        %(usable_for_etl)s,
        %(lifecycle_candidate)s,
        %(similarity_score)s,
        %(mapping_notes)s,
        %(include_in_business_views)s,
        %(exclude_reason)s,
        %(inventory_review_status)s
    )
    """

    cursor = conn.cursor()
    for index in range(0, len(rows), BATCH_SIZE):
        batch = rows[index:index + BATCH_SIZE]
        cursor.executemany(sql, batch)
        conn.commit()
    cursor.close()


def get_summary(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            COUNT(1) AS total_rows,
            SUM(CASE WHEN include_in_business_views = TRUE THEN 1 ELSE 0 END) AS business_rows,
            SUM(CASE WHEN include_in_business_views = FALSE THEN 1 ELSE 0 END) AS excluded_rows,
            SUM(CASE WHEN product_analytical_key IS NULL THEN 1 ELSE 0 END) AS orphan_product_rows,
            SUM(CASE WHEN inventory_review_status = 'invalid_snapshot_date' THEN 1 ELSE 0 END) AS invalid_snapshot_date_rows,
            SUM(CASE WHEN inventory_review_status = 'not_usable_for_etl' THEN 1 ELSE 0 END) AS not_usable_for_etl_rows,
            SUM(CASE WHEN inventory_review_status = 'mapping_not_approved' THEN 1 ELSE 0 END) AS mapping_not_approved_rows,
            COALESCE(SUM(stock_qty), 0) AS total_stock_qty
        FROM {TARGET_TABLE}
    """
    rows = fetch_all_dict(conn, query)
    return rows[0] if rows else {}


def print_summary(summary: Dict[str, Any]) -> None:
    print("=====================================================")
    print("ANALYTICS INVENTORY SNAPSHOT BUILD SUMMARY")
    print("=====================================================")
    print(f"table: {TARGET_TABLE}")
    print(f"total_rows_prepared: {summary.get('total_rows')}")
    print(f"include_in_business_views: {summary.get('business_rows')}")
    print(f"excluded_from_business_views: {summary.get('excluded_rows')}")
    print(f"orphan_product_rows: {summary.get('orphan_product_rows')}")
    print(f"invalid_snapshot_date_rows: {summary.get('invalid_snapshot_date_rows')}")
    print(f"not_usable_for_etl_rows: {summary.get('not_usable_for_etl_rows')}")
    print(f"mapping_not_approved_rows: {summary.get('mapping_not_approved_rows')}")
    print(f"total_stock_qty: {summary.get('total_stock_qty')}")
    print("=====================================================")


def build_analytics_inventory_snapshot(conn: Any) -> Dict[str, Any]:
    if not table_exists(conn, SOURCE_TABLE):
        raise RuntimeError(f"Required source table does not exist: {SOURCE_TABLE}")

    recreate_table(conn)

    valid_date_keys = load_valid_date_keys(conn)
    by_odoo, by_wansoft = load_product_indexes(conn)
    location_company_map = load_location_company_map(conn)

    source_rows = fetch_all_dict(conn, f"SELECT * FROM {SOURCE_TABLE}")

    output_rows: List[Dict[str, Any]] = []

    for source_row in source_rows:
        product = find_product(source_row, by_odoo, by_wansoft)
        output_rows.append(
            build_row(source_row, product, valid_date_keys, location_company_map)
        )

    insert_rows(conn, output_rows)

    return get_summary(conn)


def main() -> int:
    print("=====================================================")
    print("ANALYTICS INVENTORY SNAPSHOT BUILD START")
    print("=====================================================")

    conn = get_db_connection()

    try:
        summary = build_analytics_inventory_snapshot(conn)
        print_summary(summary)
        print("BUILD RESULT: COMPLETED")
        return 0
    except Exception as exc:
        print("BUILD RESULT: FAILED")
        print(f"error: {exc}")
        return 1
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
