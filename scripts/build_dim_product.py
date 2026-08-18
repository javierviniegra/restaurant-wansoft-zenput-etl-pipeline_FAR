"""
Build dim_product.

This script creates and refreshes the shared analytical product dimension used
by the unified MySQL analytical layer.

Main rules:
- No automatic product aliasing.
- Do not merge products by similar names.
- Explicit governed mapping beats name similarity.
- inventory_mapping_dictionary is the primary governance source.
- Unmapped / backlog products remain visible.
- Product identity is based on source_system + source_product_key, not product name.
- normalized_product_name is for search/diagnostics, not uniqueness.

This script does not implement BI logic.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Tuple

from core.database.mysql import get_db_connection


TABLE_NAME = "dim_product"

SOURCE_SYSTEM_VALUES = {
    "wansoft",
    "odoo",
    "both",
    "backlog",
    "unknown",
}

PRODUCT_IDENTITY_STATUS_VALUES = {
    "mapped",
    "wansoft_only",
    "odoo_only",
    "unmapped",
    "pending_review",
    "historical_only",
    "excluded_scope",
    "unknown",
}

MAPPING_STATUS_VALUES = {
    "approved",
    "pending_review",
    "historical_only",
    "unmapped",
    "open_backlog",
    "unknown",
}


@dataclass
class ProductRow:
    product_display_name: str
    normalized_product_name: str
    product_canonical_name: Optional[str]
    product_identity_status: str

    wansoft_code: Optional[str] = None
    wansoft_product_name: Optional[str] = None
    wansoft_department: Optional[str] = None
    wansoft_family: Optional[str] = None
    wansoft_group: Optional[str] = None

    odoo_product_id: Optional[str] = None
    odoo_product_name: Optional[str] = None
    odoo_default_code: Optional[str] = None
    odoo_category: Optional[str] = None
    odoo_uom: Optional[str] = None

    mapping_status: str = "unknown"
    mapping_source: Optional[str] = None
    mapping_confidence: Optional[str] = None

    is_mapped: bool = False
    is_unmapped: bool = False
    is_review_required: bool = False
    is_excluded: bool = False
    exclude_reason: Optional[str] = None

    company_scope: Optional[str] = None
    scope_bucket: Optional[str] = None
    product_business_domain: Optional[str] = None

    is_restaurant_product: bool = False
    is_bodegon_product: bool = False
    is_empanadas_product: bool = False
    is_shared_cross_company: bool = False

    source_system: str = "unknown"
    source_table: Optional[str] = None
    source_product_key: Optional[str] = None
    source_product_name: Optional[str] = None

    include_in_business_views: bool = True
    notes: Optional[str] = None


def remove_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def clean_text(value: Any) -> Optional:
    if value is None:
        return None

    text = " ".join(str(value).strip().split())

    if not text:
        return None

    return text


def normalize_product_name(value: Any) -> Optional:
    text = clean_text(value)

    if text is None:
        return None

    text = remove_accents(text)
    text = text.upper()

    return text


def bool_to_int(value: bool) -> int:
    return 1 if value else 0


def append_unique(existing: Optional[str], value: Optional[Any]) -> Optional:
    if value is None:
        return existing

    text = str(value).strip()

    if not text:
        return existing

    if not existing:
        return text

    parts = [p.strip() for p in existing.split("|") if p.strip()]

    if text not in parts:
        parts.append(text)

    return " | ".join(parts)


def add_note(row: ProductRow, note: str) -> None:
    if not note:
        return

    if row.notes:
        if note not in row.notes:
            row.notes = f"{row.notes} | {note}"
    else:
        row.notes = note


def table_exists(conn, table_name: str) -> bool:
    query = """
        SELECT COUNT(*) AS total
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = %s
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, (table_name,))
    row = cursor.fetchone()
    cursor.close()
    return bool(row and row["total"] > 0)


def get_table_columns(conn, table_name: str) -> set:
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
    return {r["column_name"] for r in rows}


def fetch_all_dict(conn, query: str, params: Optional[tuple] = None) -> list:
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params or ())
    rows = cursor.fetchall()
    cursor.close()
    return rows


def create_table_if_missing(conn) -> None:
    ddl = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        product_analytical_key BIGINT AUTO_INCREMENT PRIMARY KEY,

        product_display_name VARCHAR(500) NOT NULL,
        normalized_product_name VARCHAR(500) NOT NULL,
        product_canonical_name VARCHAR(500) NULL,
        product_identity_status VARCHAR(100) NOT NULL DEFAULT 'unknown',

        wansoft_code VARCHAR(255) NULL,
        wansoft_product_name VARCHAR(500) NULL,
        wansoft_department VARCHAR(255) NULL,
        wansoft_family VARCHAR(255) NULL,
        wansoft_group VARCHAR(255) NULL,

        odoo_product_id VARCHAR(255) NULL,
        odoo_product_name VARCHAR(500) NULL,
        odoo_default_code VARCHAR(255) NULL,
        odoo_category VARCHAR(255) NULL,
        odoo_uom VARCHAR(100) NULL,

        mapping_status VARCHAR(100) NOT NULL DEFAULT 'unknown',
        mapping_source VARCHAR(255) NULL,
        mapping_confidence VARCHAR(100) NULL,

        is_mapped BOOLEAN NOT NULL DEFAULT FALSE,
        is_unmapped BOOLEAN NOT NULL DEFAULT FALSE,
        is_review_required BOOLEAN NOT NULL DEFAULT FALSE,
        is_excluded BOOLEAN NOT NULL DEFAULT FALSE,
        exclude_reason VARCHAR(255) NULL,

        company_scope VARCHAR(255) NULL,
        scope_bucket VARCHAR(255) NULL,
        product_business_domain VARCHAR(255) NULL,

        is_restaurant_product BOOLEAN NOT NULL DEFAULT FALSE,
        is_bodegon_product BOOLEAN NOT NULL DEFAULT FALSE,
        is_empanadas_product BOOLEAN NOT NULL DEFAULT FALSE,
        is_shared_cross_company BOOLEAN NOT NULL DEFAULT FALSE,

        source_system VARCHAR(100) NOT NULL DEFAULT 'unknown',
        source_table VARCHAR(255) NULL,
        source_product_key VARCHAR(255) NOT NULL,
        source_product_name VARCHAR(500) NULL,

        include_in_business_views BOOLEAN NOT NULL DEFAULT TRUE,
        notes TEXT NULL,

        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

        UNIQUE KEY uq_dim_product_source_identity (
            source_system,
            source_product_key
        ),

        KEY idx_dim_product_normalized_name (normalized_product_name),
        KEY idx_dim_product_wansoft_code (wansoft_code),
        KEY idx_dim_product_odoo_product_id (odoo_product_id),
        KEY idx_dim_product_identity_status (product_identity_status),
        KEY idx_dim_product_mapping_status (mapping_status),
        KEY idx_dim_product_scope_bucket (scope_bucket),
        KEY idx_dim_product_business_views (include_in_business_views)
    )
    """
    cursor = conn.cursor()
    cursor.execute(ddl)
    conn.commit()
    cursor.close()


def product_key(source_system: str, source_product_key: str) -> Tuple[str, str]:
    return source_system, source_product_key


def choose_display_name(
    wansoft_product_name: Optional[Any] = None,
    odoo_product_name: Optional[Any] = None,
    product_name: Optional[Any] = None,
) -> str:
    for candidate in [wansoft_product_name, odoo_product_name, product_name]:
        cleaned = clean_text(candidate)
        if cleaned:
            return cleaned

    return "UNKNOWN PRODUCT"


def make_row(
    source_system: str,
    source_product_key: str,
    product_display_name: str,
    source_table: str,
) -> ProductRow:
    normalized = normalize_product_name(product_display_name) or "UNKNOWN PRODUCT"

    return ProductRow(
        product_display_name=product_display_name,
        normalized_product_name=normalized,
        product_canonical_name=None,
        product_identity_status="unknown",
        source_system=source_system,
        source_product_key=source_product_key,
        source_product_name=product_display_name,
        source_table=source_table,
    )


def ensure_row(
    rows: Dict[Tuple[str, str], ProductRow],
    source_system: str,
    source_product_key: str,
    product_display_name: str,
    source_table: str,
) -> ProductRow:
    key = product_key(source_system, source_product_key)

    if key not in rows:
        rows[key] = make_row(
            source_system=source_system,
            source_product_key=source_product_key,
            product_display_name=product_display_name,
            source_table=source_table,
        )

    row = rows[key]
    row.source_table = append_unique(row.source_table, source_table)
    row.source_product_name = append_unique(row.source_product_name, product_display_name)

    return row


def apply_scope_flags(row: ProductRow, scope_value: Optional[Any]) -> None:
    scope = clean_text(scope_value)

    if not scope:
        return

    row.company_scope = row.company_scope or scope
    row.scope_bucket = row.scope_bucket or scope

    normalized = normalize_product_name(scope) or ""

    if "RESTAURANTE" in normalized or "RESTAURANTES" in normalized:
        row.is_restaurant_product = True

    if "BODEGON" in normalized:
        row.is_bodegon_product = True

    if "EMPANADAS" in normalized:
        row.is_empanadas_product = True

    if "SHARED" in normalized or "CROSS" in normalized:
        row.is_shared_cross_company = True


def apply_mapping_status(row: ProductRow, raw_status: Optional[Any]) -> None:
    status = clean_text(raw_status)

    if not status:
        return

    status = status.lower()

    if status == "approved":
        row.mapping_status = "approved"
        row.product_identity_status = "mapped"
        row.is_mapped = True
        row.is_unmapped = False
        row.is_review_required = False
        row.include_in_business_views = True

    elif status == "pending_review":
        if row.mapping_status != "approved":
            row.mapping_status = "pending_review"
            row.product_identity_status = "pending_review"
            row.is_mapped = False
            row.is_unmapped = True
            row.is_review_required = True

    elif status == "historical_only":
        if row.mapping_status != "approved":
            row.mapping_status = "historical_only"
            row.product_identity_status = "historical_only"
            row.is_mapped = False
            row.is_unmapped = False
            row.is_review_required = False
            row.include_in_business_views = False
            row.is_excluded = True
            row.exclude_reason = "historical_only"

    else:
        if row.mapping_status == "unknown":
            row.mapping_status = "unknown"
            add_note(row, f"Unrecognised mapping_status: {status}")


def collect_from_inventory_mapping_dictionary(
    conn,
    rows: Dict[Tuple[str, str], ProductRow],
    odoo_index: Dict[str, ProductRow],
    wansoft_index: Dict[str, ProductRow],
) -> None:
    table_name = "inventory_mapping_dictionary"

    if not table_exists(conn, table_name):
        return

    query = """
        SELECT
            id,
            domain,
            odoo_product_id,
            odoo_product_name,
            odoo_category_name,
            wansoft_code,
            wansoft_product_name,
            wansoft_department,
            mapping_source,
            mapping_status,
            inventory_scope,
            scope_source,
            scope_status,
            lifecycle_candidate,
            similarity_score,
            notes
        FROM inventory_mapping_dictionary
    """

    for item in fetch_all_dict(conn, query):
        mapping_id = item.get("id")
        source_product_key = f"dict:{mapping_id}"

        display_name = choose_display_name(
            wansoft_product_name=item.get("wansoft_product_name"),
            odoo_product_name=item.get("odoo_product_name"),
        )

        has_wansoft = bool(clean_text(item.get("wansoft_code")))
        has_odoo = item.get("odoo_product_id") is not None

        if has_wansoft and has_odoo:
            source_system = "both"
        elif has_wansoft:
            source_system = "wansoft"
        elif has_odoo:
            source_system = "odoo"
        else:
            source_system = "unknown"

        row = ensure_row(
            rows=rows,
            source_system=source_system,
            source_product_key=source_product_key,
            product_display_name=display_name,
            source_table=table_name,
        )

        row.product_canonical_name = display_name
        row.wansoft_code = clean_text(item.get("wansoft_code")) or row.wansoft_code
        row.wansoft_product_name = clean_text(item.get("wansoft_product_name")) or row.wansoft_product_name
        row.wansoft_department = clean_text(item.get("wansoft_department")) or row.wansoft_department

        if item.get("odoo_product_id") is not None:
            row.odoo_product_id = str(item.get("odoo_product_id"))

        row.odoo_product_name = clean_text(item.get("odoo_product_name")) or row.odoo_product_name
        row.odoo_category = clean_text(item.get("odoo_category_name")) or row.odoo_category

        row.mapping_source = clean_text(item.get("mapping_source")) or row.mapping_source
        row.mapping_confidence = str(item.get("similarity_score")) if item.get("similarity_score") is not None else row.mapping_confidence

        apply_mapping_status(row, item.get("mapping_status"))
        apply_scope_flags(row, item.get("inventory_scope"))

        if clean_text(item.get("lifecycle_candidate")):
            row.product_business_domain = clean_text(item.get("lifecycle_candidate"))

        if clean_text(item.get("notes")):
            add_note(row, f"dictionary_notes: {clean_text(item.get('notes'))}")

        if row.odoo_product_id:
            odoo_index[row.odoo_product_id] = row

        if row.wansoft_code:
            wansoft_index[row.wansoft_code] = row


def collect_from_canonical_purchase_lines(
    conn,
    rows: Dict[Tuple[str, str], ProductRow],
    odoo_index: Dict[str, ProductRow],
    wansoft_index: Dict[str, ProductRow],
) -> None:
    table_name = "canonical_purchase_order_line_snapshot"

    if not table_exists(conn, table_name):
        return

    query = """
        SELECT DISTINCT
            source_system,
            product_id,
            product_name,
            wansoft_code,
            wansoft_product_name,
            wansoft_department,
            product_mapping_found,
            product_mapping_status,
            product_mapping_source,
            purchase_product_scope,
            purchase_mapping_bucket,
            extracted_product_code
        FROM canonical_purchase_order_line_snapshot
        WHERE (
                product_id IS NOT NULL
             OR wansoft_code IS NOT NULL
             OR product_name IS NOT NULL
             OR wansoft_product_name IS NOT NULL
        )
    """

    for item in fetch_all_dict(conn, query):
        source_system = clean_text(item.get("source_system"))
        product_id = item.get("product_id")
        wansoft_code = clean_text(item.get("wansoft_code"))

        row: Optional[ProductRow] = None

        if product_id is not None and str(product_id) in odoo_index:
            row = odoo_index[str(product_id)]

        elif wansoft_code and wansoft_code in wansoft_index:
            row = wansoft_index[wansoft_code]

        else:
            if source_system == "odoo" and product_id is not None:
                source_product_key = f"odoo:{product_id}"
                display_name = choose_display_name(
                    odoo_product_name=item.get("product_name"),
                    wansoft_product_name=item.get("wansoft_product_name"),
                )
                row = ensure_row(rows, "odoo", source_product_key, display_name, table_name)
                row.odoo_product_id = str(product_id)
                row.odoo_product_name = clean_text(item.get("product_name")) or row.odoo_product_name
                row.product_identity_status = "odoo_only"

            elif source_system == "wansoft" and wansoft_code:
                source_product_key = f"wansoft:{wansoft_code}"
                display_name = choose_display_name(
                    wansoft_product_name=item.get("wansoft_product_name"),
                    product_name=item.get("product_name"),
                )
                row = ensure_row(rows, "wansoft", source_product_key, display_name, table_name)
                row.wansoft_code = wansoft_code
                row.wansoft_product_name = clean_text(item.get("wansoft_product_name")) or row.wansoft_product_name
                row.product_identity_status = "wansoft_only"

            else:
                fallback_key = normalize_product_name(
                    item.get("product_name") or item.get("wansoft_product_name") or item.get("extracted_product_code")
                )

                if not fallback_key:
                    continue

                source_product_key = f"unknown:{fallback_key}"
                display_name = choose_display_name(
                    product_name=item.get("product_name"),
                    wansoft_product_name=item.get("wansoft_product_name"),
                )
                row = ensure_row(rows, "unknown", source_product_key, display_name, table_name)
                row.product_identity_status = "unknown"
                row.is_review_required = True

        row.source_table = append_unique(row.source_table, table_name)
        row.wansoft_code = clean_text(item.get("wansoft_code")) or row.wansoft_code
        row.wansoft_product_name = clean_text(item.get("wansoft_product_name")) or row.wansoft_product_name
        row.wansoft_department = clean_text(item.get("wansoft_department")) or row.wansoft_department
        row.mapping_source = clean_text(item.get("product_mapping_source")) or row.mapping_source

        if clean_text(item.get("product_mapping_status")):
            apply_mapping_status(row, item.get("product_mapping_status"))

        if item.get("product_mapping_found") == 1 and row.mapping_status == "approved":
            row.is_mapped = True
            row.product_identity_status = "mapped"

        apply_scope_flags(row, item.get("purchase_product_scope"))

        if clean_text(item.get("purchase_mapping_bucket")):
            row.scope_bucket = clean_text(item.get("purchase_mapping_bucket"))

        add_note(row, "Detected in canonical_purchase_order_line_snapshot")


def collect_from_odoo_inventory_snapshot(
    conn,
    rows: Dict[Tuple[str, str], ProductRow],
    odoo_index: Dict[str, ProductRow],
    wansoft_index: Dict[str, ProductRow],
) -> None:
    table_name = "odoo_inventory_snapshot"

    if not table_exists(conn, table_name):
        return

    query = """
        SELECT DISTINCT
            odoo_product_id,
            odoo_product_name,
            product_code,
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
        FROM odoo_inventory_snapshot
        WHERE odoo_product_id IS NOT NULL
           OR odoo_product_name IS NOT NULL
    """

    for item in fetch_all_dict(conn, query):
        odoo_product_id = item.get("odoo_product_id")
        wansoft_code = clean_text(item.get("wansoft_code"))

        row: Optional[ProductRow] = None

        if odoo_product_id is not None and str(odoo_product_id) in odoo_index:
            row = odoo_index[str(odoo_product_id)]

        elif wansoft_code and wansoft_code in wansoft_index:
            row = wansoft_index[wansoft_code]

        else:
            if odoo_product_id is None:
                continue

            source_product_key = f"odoo:{odoo_product_id}"
            display_name = choose_display_name(
                odoo_product_name=item.get("odoo_product_name"),
                wansoft_product_name=item.get("wansoft_product_name"),
            )

            row = ensure_row(rows, "odoo", source_product_key, display_name, table_name)
            row.odoo_product_id = str(odoo_product_id)
            row.odoo_product_name = clean_text(item.get("odoo_product_name")) or row.odoo_product_name
            row.product_identity_status = "odoo_only"

            odoo_index[str(odoo_product_id)] = row

        row.source_table = append_unique(row.source_table, table_name)
        row.odoo_product_id = str(odoo_product_id) if odoo_product_id is not None else row.odoo_product_id
        row.odoo_product_name = clean_text(item.get("odoo_product_name")) or row.odoo_product_name
        row.odoo_default_code = clean_text(item.get("product_code")) or row.odoo_default_code
        row.wansoft_code = clean_text(item.get("wansoft_code")) or row.wansoft_code
        row.wansoft_product_name = clean_text(item.get("wansoft_product_name")) or row.wansoft_product_name
        row.wansoft_department = clean_text(item.get("wansoft_department")) or row.wansoft_department
        row.mapping_source = clean_text(item.get("lookup_method")) or row.mapping_source
        row.mapping_confidence = str(item.get("similarity_score")) if item.get("similarity_score") is not None else row.mapping_confidence

        apply_mapping_status(row, item.get("mapping_status"))

        if item.get("mapping_found") == 1 and row.mapping_status == "approved":
            row.is_mapped = True
            row.product_identity_status = "mapped"

        if item.get("usable_for_etl") == 0:
            row.include_in_business_views = False
            add_note(row, "Inventory snapshot usable_for_etl = 0")

        if clean_text(item.get("lifecycle_candidate")):
            row.product_business_domain = clean_text(item.get("lifecycle_candidate"))

        if clean_text(item.get("mapping_notes")):
            add_note(row, f"inventory_mapping_notes: {clean_text(item.get('mapping_notes'))}")

        add_note(row, "Detected in odoo_inventory_snapshot")


def collect_from_purchase_inventory_backlog(
    conn,
    rows: Dict[Tuple[str, str], ProductRow],
    odoo_index: Dict[str, ProductRow],
) -> None:
    table_name = "odoo_purchase_inventory_mapping_backlog"

    if not table_exists(conn, table_name):
        return

    query = """
        SELECT
            product_id,
            product_name,
            purchase_product_scope,
            purchase_mapping_bucket,
            total_lines,
            unique_vendors,
            unique_companies,
            total_qty,
            total_received,
            total_amount,
            first_order_date,
            last_order_date,
            suggested_action,
            backlog_status
        FROM odoo_purchase_inventory_mapping_backlog
    """

    for item in fetch_all_dict(conn, query):
        product_id = item.get("product_id")

        if product_id is None:
            continue

        if str(product_id) in odoo_index:
            row = odoo_index[str(product_id)]
        else:
            source_product_key = f"odoo:{product_id}"
            display_name = choose_display_name(product_name=item.get("product_name"))
            row = ensure_row(rows, "odoo", source_product_key, display_name, table_name)
            row.odoo_product_id = str(product_id)
            row.odoo_product_name = clean_text(item.get("product_name")) or row.odoo_product_name
            odoo_index[str(product_id)] = row

        row.source_table = append_unique(row.source_table, table_name)
        row.product_identity_status = "pending_review"
        row.mapping_status = "open_backlog"
        row.is_mapped = False
        row.is_unmapped = True
        row.is_review_required = True
        row.include_in_business_views = False
        row.exclude_reason = "open_backlog"

        apply_scope_flags(row, item.get("purchase_product_scope"))

        if clean_text(item.get("purchase_mapping_bucket")):
            row.scope_bucket = clean_text(item.get("purchase_mapping_bucket"))

        add_note(row, f"backlog_status: {clean_text(item.get('backlog_status'))}")
        add_note(row, f"suggested_action: {clean_text(item.get('suggested_action'))}")
        add_note(row, "Detected in odoo_purchase_inventory_mapping_backlog")


def finalize_rows(rows: Dict[Tuple[str, str], ProductRow]) -> None:
    for row in rows.values():
        row.product_display_name = clean_text(row.product_display_name) or "UNKNOWN PRODUCT"
        row.normalized_product_name = normalize_product_name(row.product_display_name) or "UNKNOWN PRODUCT"

        if row.source_system not in SOURCE_SYSTEM_VALUES:
            row.source_system = "unknown"

        if row.product_identity_status not in PRODUCT_IDENTITY_STATUS_VALUES:
            row.product_identity_status = "unknown"

        if row.mapping_status not in MAPPING_STATUS_VALUES:
            row.mapping_status = "unknown"

        if row.is_mapped:
            row.is_unmapped = False
            row.is_review_required = False
            row.product_identity_status = "mapped"
            row.mapping_status = "approved"

        if row.product_identity_status in {"pending_review", "unmapped", "unknown"}:
            row.is_review_required = True

        if row.mapping_status in {"pending_review", "open_backlog", "unmapped"}:
            row.is_unmapped = True
            row.is_review_required = True

        if row.is_excluded:
            row.include_in_business_views = False

        if row.is_review_required:
            row.include_in_business_views = False

        if row.source_product_key is None:
            row.source_product_key = f"unknown:{row.normalized_product_name}"
            row.source_system = "unknown"
            row.is_review_required = True
            row.include_in_business_views = False
            add_note(row, "Generated fallback source_product_key")

        if not row.source_product_name:
            row.source_product_name = row.product_display_name


def build_rows(conn) -> Dict[Tuple[str, str], ProductRow]:
    rows: Dict[Tuple[str, str], ProductRow] = {}
    odoo_index: Dict[str, ProductRow] = {}
    wansoft_index: Dict[str, ProductRow] = {}

    collect_from_inventory_mapping_dictionary(conn, rows, odoo_index, wansoft_index)
    collect_from_canonical_purchase_lines(conn, rows, odoo_index, wansoft_index)
    collect_from_odoo_inventory_snapshot(conn, rows, odoo_index, wansoft_index)
    collect_from_purchase_inventory_backlog(conn, rows, odoo_index)

    finalize_rows(rows)

    return rows


def insert_rows(conn, rows: Dict[Tuple[str, str], ProductRow]) -> None:
    sql = f"""
    INSERT INTO {TABLE_NAME} (
        product_display_name,
        normalized_product_name,
        product_canonical_name,
        product_identity_status,
        wansoft_code,
        wansoft_product_name,
        wansoft_department,
        wansoft_family,
        wansoft_group,
        odoo_product_id,
        odoo_product_name,
        odoo_default_code,
        odoo_category,
        odoo_uom,
        mapping_status,
        mapping_source,
        mapping_confidence,
        is_mapped,
        is_unmapped,
        is_review_required,
        is_excluded,
        exclude_reason,
        company_scope,
        scope_bucket,
        product_business_domain,
        is_restaurant_product,
        is_bodegon_product,
        is_empanadas_product,
        is_shared_cross_company,
        source_system,
        source_table,
        source_product_key,
        source_product_name,
        include_in_business_views,
        notes
    )
    VALUES (
        %(product_display_name)s,
        %(normalized_product_name)s,
        %(product_canonical_name)s,
        %(product_identity_status)s,
        %(wansoft_code)s,
        %(wansoft_product_name)s,
        %(wansoft_department)s,
        %(wansoft_family)s,
        %(wansoft_group)s,
        %(odoo_product_id)s,
        %(odoo_product_name)s,
        %(odoo_default_code)s,
        %(odoo_category)s,
        %(odoo_uom)s,
        %(mapping_status)s,
        %(mapping_source)s,
        %(mapping_confidence)s,
        %(is_mapped)s,
        %(is_unmapped)s,
        %(is_review_required)s,
        %(is_excluded)s,
        %(exclude_reason)s,
        %(company_scope)s,
        %(scope_bucket)s,
        %(product_business_domain)s,
        %(is_restaurant_product)s,
        %(is_bodegon_product)s,
        %(is_empanadas_product)s,
        %(is_shared_cross_company)s,
        %(source_system)s,
        %(source_table)s,
        %(source_product_key)s,
        %(source_product_name)s,
        %(include_in_business_views)s,
        %(notes)s
    )
    """

    payload = []

    for row in rows.values():
        item = asdict(row)
        item["is_mapped"] = bool_to_int(row.is_mapped)
        item["is_unmapped"] = bool_to_int(row.is_unmapped)
        item["is_review_required"] = bool_to_int(row.is_review_required)
        item["is_excluded"] = bool_to_int(row.is_excluded)
        item["is_restaurant_product"] = bool_to_int(row.is_restaurant_product)
        item["is_bodegon_product"] = bool_to_int(row.is_bodegon_product)
        item["is_empanadas_product"] = bool_to_int(row.is_empanadas_product)
        item["is_shared_cross_company"] = bool_to_int(row.is_shared_cross_company)
        item["include_in_business_views"] = bool_to_int(row.include_in_business_views)
        payload.append(item)

    cursor = conn.cursor()

    # Deterministic rebuild for initial Section 17 implementation.
    cursor.execute(f"DELETE FROM {TABLE_NAME}")

    if payload:
        cursor.executemany(sql, payload)

    conn.commit()
    cursor.close()


def print_summary(rows: Dict[Tuple[str, str], ProductRow]) -> None:
    total = len(rows)
    mapped = sum(1 for row in rows.values() if row.is_mapped)
    unmapped = sum(1 for row in rows.values() if row.is_unmapped)
    review_required = sum(1 for row in rows.values() if row.is_review_required)
    included_business = sum(1 for row in rows.values() if row.include_in_business_views)

    status_counts: Dict[str, int] = {}
    source_counts: Dict[str, int] = {}
    mapping_counts: Dict[str, int] = {}

    for row in rows.values():
        status_counts[row.product_identity_status] = status_counts.get(row.product_identity_status, 0) + 1
        source_counts[row.source_system] = source_counts.get(row.source_system, 0) + 1
        mapping_counts[row.mapping_status] = mapping_counts.get(row.mapping_status, 0) + 1

    print("=====================================================")
    print("DIM PRODUCT BUILD SUMMARY")
    print("=====================================================")
    print(f"table: {TABLE_NAME}")
    print(f"total_rows_prepared: {total}")
    print(f"mapped: {mapped}")
    print(f"unmapped: {unmapped}")
    print(f"review_required: {review_required}")
    print(f"include_in_business_views: {included_business}")

    print("product_identity_status_counts:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")

    print("source_system_counts:")
    for source_system, count in sorted(source_counts.items()):
        print(f"  {source_system}: {count}")

    print("mapping_status_counts:")
    for mapping_status, count in sorted(mapping_counts.items()):
        print(f"  {mapping_status}: {count}")

    print("=====================================================")


def main() -> int:
    print("=====================================================")
    print("DIM PRODUCT BUILD START")
    print("=====================================================")

    conn = get_db_connection()

    try:
        create_table_if_missing(conn)
        rows = build_rows(conn)
        insert_rows(conn, rows)
        print_summary(rows)

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