"""
Build dim_vendor.

This script creates and refreshes the shared analytical vendor dimension used by
the unified MySQL analytical layer.

Main rules:
- 1 row = 1 analytical vendor identity.
- Vendor names are normalized deterministically.
- Internal vendors are preserved and flagged.
- Internal vendors are excluded from business views by default.
- Vendor equivalence is not inferred through fuzzy similarity.
- Source traceability is preserved where available.

This script does not implement BI logic.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Set
import unicodedata

from core.database.mysql import get_db_connection


TABLE_NAME = "dim_vendor"

SOURCE_TABLES = [
    "canonical_purchase_order_snapshot",
    "canonical_purchase_order_line_snapshot",
    "canonical_purchase_receipt_snapshot",
    "canonical_purchase_receipt_move_snapshot",
]

VENDOR_NAME_CANDIDATES = [
    "vendor_name",
    "source_vendor_name",
    "partner_name",
    "supplier_name",
    "provider_name",
    "proveedor",
    "proveedor_nombre",
    "nombre_proveedor",
]

VENDOR_ID_CANDIDATES = [
    "vendor_id",
    "source_vendor_id",
    "partner_id",
    "supplier_id",
    "provider_id",
    "proveedor_id",
    "id_proveedor",
]

SOURCE_SYSTEM_CANDIDATES = [
    "source_system",
    "source",
    "vendor_source_system",
]

INTERNAL_VENDOR_CANONICAL = {
    "Bodegón": "EL BODEGON DE FITO",
    "Empanadas": "LAS EMPANADAS DE MARIA EVA",
}

INTERNAL_VENDOR_ALIASES = {
    "BODEGÓN": "Bodegón",
    "BODEGON": "Bodegón",
    "EL BODEGON DE FITO": "Bodegón",
    "EMPANADAS": "Empanadas",
    "LAS EMPANADAS DE MARIA EVA": "Empanadas",
}

VALID_VENDOR_SOURCE_SYSTEMS = {
    "wansoft",
    "odoo",
    "both",
    "unknown",
}


@dataclass
class VendorRow:
    vendor_display_name: str
    normalized_vendor_name: str

    vendor_canonical_name: Optional[str] = None

    vendor_source_system: str = "unknown"
    wansoft_vendor_id: Optional[str] = None
    odoo_vendor_id: Optional[str] = None
    source_vendor_name: Optional[str] = None
    source_vendor_key: Optional[str] = None

    is_internal_vendor: bool = False
    is_external_vendor: bool = True
    is_active: bool = True
    is_review_required: bool = False

    include_in_business_views: bool = True
    exclude_reason: Optional[str] = None

    notes: Optional[str] = None


def normalize_vendor_name(value: Optional[str]) -> Optional:
    if value is None:
        return None

    text = " ".join(str(value).strip().split())

    if not text:
        return None

    text = remove_accents(text)
    text = text.upper()

    return text

def remove_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def clean_display_name(value: Any) -> Optional:
    if value is None:
        return None

    text = " ".join(str(value).strip().split())

    if not text:
        return None

    return text


def bool_to_int(value: bool) -> int:
    return 1 if value else 0


def add_note(row: VendorRow, note: str) -> None:
    if not note:
        return

    if row.notes:
        if note not in row.notes:
            row.notes = f"{row.notes} | {note}"
    else:
        row.notes = note


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


def canonicalize_internal_vendor(value: Optional[str]) -> Optional:
    normalized = normalize_vendor_name(value)

    if normalized is None:
        return None

    return INTERNAL_VENDOR_ALIASES.get(normalized)


def is_internal_vendor(value: Optional[str]) -> bool:
    return canonicalize_internal_vendor(value) is not None


def get_internal_display_name(canonical_name: str) -> str:
    return INTERNAL_VENDOR_CANONICAL[canonical_name]


def merge_source_system(existing: str, new_value: Optional[Any]) -> str:
    if new_value is None:
        return existing or "unknown"

    source = str(new_value).strip().lower()

    if source not in {"wansoft", "odoo"}:
        source = "unknown"

    if existing in (None, "", "unknown"):
        return source

    if source == "unknown":
        return existing

    if existing == source:
        return existing

    if existing in {"wansoft", "odoo"} and source in {"wansoft", "odoo"}:
        return "both"

    if existing == "both":
        return "both"

    return existing


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


def get_table_columns(conn, table_name: str) -> Set[str]:
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


def first_existing_column(columns: Set[str], candidates: list[str]) -> Optional[str]:
    for candidate in candidates:
        if candidate in columns:
            return candidate

    return None


def create_table_if_missing(conn) -> None:
    ddl = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        vendor_analytical_key BIGINT AUTO_INCREMENT PRIMARY KEY,

        vendor_display_name VARCHAR(255) NOT NULL,
        normalized_vendor_name VARCHAR(255) NOT NULL,
        vendor_canonical_name VARCHAR(255) NULL,

        vendor_source_system VARCHAR(100) NOT NULL DEFAULT 'unknown',
        wansoft_vendor_id VARCHAR(255) NULL,
        odoo_vendor_id VARCHAR(255) NULL,
        source_vendor_name TEXT NULL,
        source_vendor_key TEXT NULL,

        is_internal_vendor BOOLEAN NOT NULL DEFAULT FALSE,
        is_external_vendor BOOLEAN NOT NULL DEFAULT TRUE,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        is_review_required BOOLEAN NOT NULL DEFAULT FALSE,

        include_in_business_views BOOLEAN NOT NULL DEFAULT TRUE,
        exclude_reason VARCHAR(255) NULL,

        notes TEXT NULL,

        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

        UNIQUE KEY uq_dim_vendor_normalized_vendor_name (normalized_vendor_name),
        KEY idx_dim_vendor_display_name (vendor_display_name),
        KEY idx_dim_vendor_source_system (vendor_source_system),
        KEY idx_dim_vendor_internal (is_internal_vendor),
        KEY idx_dim_vendor_business_views (include_in_business_views)
    )
    """
    cursor = conn.cursor()
    cursor.execute(ddl)
    conn.commit()
    cursor.close()


def ensure_vendor_row(rows: Dict[str, VendorRow], vendor_name: str) -> VendorRow:
    internal_canonical = canonicalize_internal_vendor(vendor_name)

    if internal_canonical:
        display_name = get_internal_display_name(internal_canonical)
        normalized_name = normalize_vendor_name(display_name)

        if normalized_name is None:
            raise ValueError(f"Invalid internal vendor name: {vendor_name}")

        if normalized_name not in rows:
            rows[normalized_name] = VendorRow(
                vendor_display_name=display_name,
                normalized_vendor_name=normalized_name,
                vendor_canonical_name=internal_canonical,
                is_internal_vendor=True,
                is_external_vendor=False,
                include_in_business_views=False,
                exclude_reason="internal_vendor",
                source_vendor_name=clean_display_name(vendor_name),
            )

        row = rows[normalized_name]
        row.is_internal_vendor = True
        row.is_external_vendor = False
        row.include_in_business_views = False
        row.exclude_reason = "internal_vendor"
        row.vendor_canonical_name = internal_canonical
        row.vendor_display_name = display_name
        row.source_vendor_name = append_unique(row.source_vendor_name, clean_display_name(vendor_name))
        return row

    display_name = clean_display_name(vendor_name)

    if display_name is None:
        raise ValueError(f"Invalid vendor name: {vendor_name}")

    normalized_name = normalize_vendor_name(display_name)

    if normalized_name is None:
        raise ValueError(f"Invalid normalized vendor name: {vendor_name}")

    if normalized_name not in rows:
        rows[normalized_name] = VendorRow(
            vendor_display_name=display_name,
            normalized_vendor_name=normalized_name,
            vendor_canonical_name=None,
            source_vendor_name=display_name,
        )

    row = rows[normalized_name]
    row.source_vendor_name = append_unique(row.source_vendor_name, display_name)

    return row


def collect_vendor_candidates_from_table(
    conn,
    rows: Dict[str, VendorRow],
    table_name: str,
) -> None:
    if not table_exists(conn, table_name):
        return

    columns = get_table_columns(conn, table_name)

    vendor_name_col = first_existing_column(columns, VENDOR_NAME_CANDIDATES)

    if vendor_name_col is None:
        return

    vendor_id_col = first_existing_column(columns, VENDOR_ID_CANDIDATES)
    source_system_col = first_existing_column(columns, SOURCE_SYSTEM_CANDIDATES)

    select_exprs = [
        f"`{vendor_name_col}` AS vendor_name",
    ]

    if vendor_id_col:
        select_exprs.append(f"`{vendor_id_col}` AS vendor_id")
    else:
        select_exprs.append("NULL AS vendor_id")

    if source_system_col:
        select_exprs.append(f"`{source_system_col}` AS source_system")
    else:
        select_exprs.append("NULL AS source_system")

    query = f"""
        SELECT DISTINCT
            {", ".join(select_exprs)}
        FROM {table_name}
        WHERE `{vendor_name_col}` IS NOT NULL
          AND TRIM(`{vendor_name_col}`) <> ''
    """

    for item in fetch_all_dict(conn, query):
        vendor_name = item.get("vendor_name")
        vendor_id = item.get("vendor_id")
        source_system = item.get("source_system")

        display_name = clean_display_name(vendor_name)

        if display_name is None:
            continue

        row = ensure_vendor_row(rows, display_name)
        row.vendor_source_system = merge_source_system(row.vendor_source_system, source_system)

        source = str(source_system).strip().lower() if source_system is not None else "unknown"

        if source == "wansoft":
            row.wansoft_vendor_id = append_unique(row.wansoft_vendor_id, vendor_id)

        elif source == "odoo":
            row.odoo_vendor_id = append_unique(row.odoo_vendor_id, vendor_id)

        else:
            row.source_vendor_key = append_unique(row.source_vendor_key, vendor_id)

        add_note(row, f"Detected in {table_name}")


def ensure_internal_vendors(rows: Dict[str, VendorRow]) -> None:
    for canonical_name, legal_name in INTERNAL_VENDOR_CANONICAL.items():
        row = ensure_vendor_row(rows, legal_name)
        row.vendor_canonical_name = canonical_name
        row.is_internal_vendor = True
        row.is_external_vendor = False
        row.include_in_business_views = False
        row.exclude_reason = "internal_vendor"
        add_note(row, "Required internal vendor")


def finalize_rows(rows: Dict[str, VendorRow]) -> None:
    for row in rows.values():
        if row.vendor_source_system not in VALID_VENDOR_SOURCE_SYSTEMS:
            row.vendor_source_system = "unknown"

        if row.is_internal_vendor:
            row.is_external_vendor = False
            row.include_in_business_views = False
            row.exclude_reason = "internal_vendor"

        else:
            row.is_external_vendor = True

        if not row.vendor_display_name or not row.normalized_vendor_name:
            row.is_review_required = True
            add_note(row, "Missing vendor display or normalized name")

        if row.vendor_source_system == "unknown":
            add_note(row, "Vendor source system unknown")


def build_rows(conn) -> Dict[str, VendorRow]:
    rows: Dict[str, VendorRow] = {}

    for table_name in SOURCE_TABLES:
        collect_vendor_candidates_from_table(conn, rows, table_name)

    ensure_internal_vendors(rows)
    finalize_rows(rows)

    return rows


def insert_rows(conn, rows: Dict[str, VendorRow]) -> None:
    sql = f"""
    INSERT INTO {TABLE_NAME} (
        vendor_display_name,
        normalized_vendor_name,
        vendor_canonical_name,
        vendor_source_system,
        wansoft_vendor_id,
        odoo_vendor_id,
        source_vendor_name,
        source_vendor_key,
        is_internal_vendor,
        is_external_vendor,
        is_active,
        is_review_required,
        include_in_business_views,
        exclude_reason,
        notes
    )
    VALUES (
        %(vendor_display_name)s,
        %(normalized_vendor_name)s,
        %(vendor_canonical_name)s,
        %(vendor_source_system)s,
        %(wansoft_vendor_id)s,
        %(odoo_vendor_id)s,
        %(source_vendor_name)s,
        %(source_vendor_key)s,
        %(is_internal_vendor)s,
        %(is_external_vendor)s,
        %(is_active)s,
        %(is_review_required)s,
        %(include_in_business_views)s,
        %(exclude_reason)s,
        %(notes)s
    )
    """

    payload = []

    for row in rows.values():
        item = asdict(row)
        item["is_internal_vendor"] = bool_to_int(row.is_internal_vendor)
        item["is_external_vendor"] = bool_to_int(row.is_external_vendor)
        item["is_active"] = bool_to_int(row.is_active)
        item["is_review_required"] = bool_to_int(row.is_review_required)
        item["include_in_business_views"] = bool_to_int(row.include_in_business_views)
        payload.append(item)

    cursor = conn.cursor()

    # Deterministic rebuild for initial Section 17 implementation.
    cursor.execute(f"DELETE FROM {TABLE_NAME}")

    if payload:
        cursor.executemany(sql, payload)

    conn.commit()
    cursor.close()


def print_summary(rows: Dict[str, VendorRow]) -> None:
    total = len(rows)
    internal = sum(1 for r in rows.values() if r.is_internal_vendor)
    external = sum(1 for r in rows.values() if r.is_external_vendor)
    review_required = sum(1 for r in rows.values() if r.is_review_required)

    source_counts: Dict[str, int] = {}

    for row in rows.values():
        source_counts[row.vendor_source_system] = source_counts.get(row.vendor_source_system, 0) + 1

    print("=====================================================")
    print("DIM VENDOR BUILD SUMMARY")
    print("=====================================================")
    print(f"table: {TABLE_NAME}")
    print(f"total_rows_prepared: {total}")
    print(f"internal_vendors: {internal}")
    print(f"external_vendors: {external}")
    print(f"review_required: {review_required}")
    print("vendor_source_system_counts:")

    for source_system, count in sorted(source_counts.items()):
        print(f"  {source_system}: {count}")

    print("=====================================================")


def main() -> int:
    print("=====================================================")
    print("DIM VENDOR BUILD START")
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