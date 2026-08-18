"""
Build analytics_purchase_order_lines.

This script creates and refreshes the first detailed analytical purchase fact
 table in the unified MySQL analytical layer.

Main rules:
- 1 row = 1 canonical purchase order line.
- Preserve all canonical rows.
- Do not drop rows with missing dimensions.
- Join company by company_source_key.
- Join time by order_date_key.
- Join vendor by normalized vendor name.
- Join product by source identity and governed mapping fallback.
- Do not join product by product name.
- Internal vendor lines remain visible but excluded from business views.
- Review-required products remain visible but excluded from business views.

This script does not implement BI logic.
"""

from __future__ import annotations

import unicodedata
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from core.database.mysql import get_db_connection


ANALYTICS_TABLE = "analytics_purchase_order_lines"
SOURCE_TABLE = "canonical_purchase_order_line_snapshot"
BATCH_SIZE = 5000


def remove_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None

    text = " ".join(str(value).strip().split())

    if not text:
        return None

    return text


def normalize_name(value: Any) -> Optional[str]:
    text = clean_text(value)

    if text is None:
        return None

    text = remove_accents(text)
    text = text.upper()

    return text


def bool_to_int(value: bool) -> int:
    return 1 if value else 0


def append_reason(existing: Optional[str], reason: str) -> str:
    if not existing:
        return reason

    parts = [p.strip() for p in existing.split("|") if p.strip()]

    if reason not in parts:
        parts.append(reason)

    return " | ".join(parts)


def parse_date(value: Any) -> Optional[date]:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    text = str(value).strip()

    if not text:
        return None

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:19], fmt).date()
        except ValueError:
            pass

    try:
        return datetime.fromisoformat(text).date()
    except Exception:
        return None


def date_key_from_date(value: Optional[date]) -> Optional[int]:
    if value is None:
        return None

    return int(value.strftime("%Y%m%d"))


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

    return bool(row and row["total"] > 0)


def fetch_all_dict(conn: Any, query: str, params: Optional[tuple] = None) -> list:
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params or ())
    rows = cursor.fetchall()
    cursor.close()
    return rows


def create_table_if_missing(conn: Any) -> None:
    ddl = f"""
    CREATE TABLE IF NOT EXISTS {ANALYTICS_TABLE} (
        purchase_order_line_analytical_key BIGINT AUTO_INCREMENT PRIMARY KEY,

        canonical_purchase_order_line_id BIGINT NOT NULL,
        source_system VARCHAR(50) NOT NULL,
        source_domain VARCHAR(100) NULL,
        source_order_line_id VARCHAR(100) NULL,
        source_order_id VARCHAR(100) NULL,
        purchase_order_name VARCHAR(255) NULL,

        company_source_key VARCHAR(255) NULL,
        company_analytical_key BIGINT NULL,
        company_id VARCHAR(100) NULL,
        company_name VARCHAR(255) NULL,
        final_purchase_source_status VARCHAR(100) NULL,
        company_migration_type VARCHAR(100) NULL,
        history_source VARCHAR(100) NULL,
        include_odoo_history BOOLEAN NULL,
        operational_start_date DATE NULL,
        migration_policy_source VARCHAR(100) NULL,

        order_date DATETIME NULL,
        order_date_key INT NULL,

        vendor_analytical_key BIGINT NULL,
        vendor_id VARCHAR(100) NULL,
        vendor_name VARCHAR(255) NULL,
        normalized_vendor_name VARCHAR(255) NULL,
        is_internal_vendor BOOLEAN NOT NULL DEFAULT FALSE,
        include_vendor_in_business_views BOOLEAN NOT NULL DEFAULT TRUE,

        product_analytical_key BIGINT NULL,
        product_id VARCHAR(100) NULL,
        product_name VARCHAR(255) NULL,
        wansoft_code VARCHAR(100) NULL,
        wansoft_product_name VARCHAR(255) NULL,
        wansoft_department VARCHAR(255) NULL,
        product_mapping_found BOOLEAN NULL,
        product_mapping_status VARCHAR(100) NULL,
        product_mapping_source VARCHAR(100) NULL,
        purchase_line_type VARCHAR(100) NULL,
        purchase_product_scope VARCHAR(100) NULL,
        purchase_mapping_bucket VARCHAR(100) NULL,
        purchase_classification_source VARCHAR(100) NULL,
        extracted_product_code VARCHAR(100) NULL,

        product_identity_status VARCHAR(100) NULL,
        dim_product_mapping_status VARCHAR(100) NULL,
        is_product_mapped BOOLEAN NOT NULL DEFAULT FALSE,
        is_product_review_required BOOLEAN NOT NULL DEFAULT FALSE,
        include_product_in_business_views BOOLEAN NOT NULL DEFAULT TRUE,

        product_qty DECIMAL(18,4) NULL,
        qty_received DECIMAL(18,4) NULL,
        qty_invoiced DECIMAL(18,4) NULL,
        price_unit DECIMAL(18,4) NULL,
        price_subtotal DECIMAL(18,4) NULL,
        price_total DECIMAL(18,4) NULL,

        state VARCHAR(100) NULL,
        canonical_loaded_at TIMESTAMP NULL,

        include_in_business_views BOOLEAN NOT NULL DEFAULT TRUE,
        exclude_reason VARCHAR(500) NULL,
        line_review_status VARCHAR(100) NULL,

        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

        UNIQUE KEY uq_analytics_purchase_order_lines_canonical_id (
            canonical_purchase_order_line_id
        ),

        KEY idx_analytics_purchase_lines_company_date (
            company_source_key,
            order_date_key
        ),

        KEY idx_analytics_purchase_lines_vendor (
            vendor_analytical_key
        ),

        KEY idx_analytics_purchase_lines_product (
            product_analytical_key
        ),

        KEY idx_analytics_purchase_lines_source_system (
            source_system
        ),

        KEY idx_analytics_purchase_lines_business_views (
            include_in_business_views
        )
    )
    """
    cursor = conn.cursor()
    cursor.execute(ddl)
    conn.commit()
    cursor.close()


def load_company_dimension(conn: Any) -> Dict[str, Dict[str, Any]]:
    query = """
        SELECT
            company_analytical_key,
            company_source_key,
            is_internal_provider,
            is_final_operating_branch,
            rollout_type,
            rollout_status
        FROM dim_company_analytical
    """

    result: Dict[str, Dict[str, Any]] = {}

    for row in fetch_all_dict(conn, query):
        result[row["company_source_key"]] = row

    return result


def load_time_dimension(conn: Any) -> set[int]:
    query = """
        SELECT date_key
        FROM dim_time
    """
    return {int(row["date_key"]) for row in fetch_all_dict(conn, query)}


def load_vendor_dimension(conn: Any) -> Dict[str, Dict[str, Any]]:
    query = """
        SELECT
            vendor_analytical_key,
            vendor_display_name,
            normalized_vendor_name,
            is_internal_vendor,
            include_in_business_views
        FROM dim_vendor
    """

    result: Dict[str, Dict[str, Any]] = {}

    for row in fetch_all_dict(conn, query):
        result[row["normalized_vendor_name"]] = row

    return result


def product_priority(row: Dict[str, Any]) -> int:
    if row.get("is_mapped"):
        return 1

    if row.get("product_identity_status") == "mapped":
        return 2

    if row.get("include_in_business_views"):
        return 3

    return 9


def assign_product_if_better(
    reference: Dict[str, Dict[str, Any]],
    key: Optional[str],
    product_row: Dict[str, Any],
) -> None:
    if not key:
        return

    existing = reference.get(key)

    if existing is None or product_priority(product_row) < product_priority(existing):
        reference[key] = product_row


def load_product_dimension(conn: Any) -> Dict[str, Dict[Any, Dict[str, Any]]]:
    query = """
        SELECT
            product_analytical_key,
            product_display_name,
            product_identity_status,
            mapping_status,
            is_mapped,
            is_review_required,
            include_in_business_views,
            source_system,
            source_product_key,
            wansoft_code,
            odoo_product_id
        FROM dim_product
    """

    source_identity: Dict[Tuple[str, str], Dict[str, Any]] = {}
    odoo_by_product_id: Dict[str, Dict[str, Any]] = {}
    wansoft_by_code: Dict[str, Dict[str, Any]] = {}

    for row in fetch_all_dict(conn, query):
        source_system = row.get("source_system")
        source_product_key = row.get("source_product_key")

        if source_system and source_product_key:
            source_identity[(source_system, source_product_key)] = row

        odoo_product_id = clean_text(row.get("odoo_product_id"))
        wansoft_code = clean_text(row.get("wansoft_code"))

        assign_product_if_better(odoo_by_product_id, odoo_product_id, row)
        assign_product_if_better(wansoft_by_code, wansoft_code, row)

    return {
        "source_identity": source_identity,
        "odoo_by_product_id": odoo_by_product_id,
        "wansoft_by_code": wansoft_by_code,
    }


def lookup_product(
    source_row: Dict[str, Any],
    product_dimension: Dict[str, Dict[Any, Dict[str, Any]]],
) -> Optional[Dict[str, Any]]:
    source_system = clean_text(source_row.get("source_system"))
    product_id = source_row.get("product_id")
    wansoft_code = clean_text(source_row.get("wansoft_code"))

    source_identity = product_dimension["source_identity"]
    odoo_by_product_id = product_dimension["odoo_by_product_id"]
    wansoft_by_code = product_dimension["wansoft_by_code"]

    if source_system == "odoo" and product_id is not None:
        key = ("odoo", f"odoo:{product_id}")

        if key in source_identity:
            return source_identity[key]

        product = odoo_by_product_id.get(str(product_id))

        if product:
            return product

    if source_system == "wansoft" and wansoft_code:
        key = ("wansoft", f"wansoft:{wansoft_code}")

        if key in source_identity:
            return source_identity[key]

        product = wansoft_by_code.get(wansoft_code)

        if product:
            return product

    if product_id is not None:
        product = odoo_by_product_id.get(str(product_id))

        if product:
            return product

    if wansoft_code:
        product = wansoft_by_code.get(wansoft_code)

        if product:
            return product

    return None


def build_analytics_row(
    source_row: Dict[str, Any],
    company_dimension: Dict[str, Dict[str, Any]],
    time_keys: set[int],
    vendor_dimension: Dict[str, Dict[str, Any]],
    product_dimension: Dict[str, Dict[Any, Dict[str, Any]]],
) -> Dict[str, Any]:
    include_in_business_views = True
    exclude_reason: Optional[str] = None
    line_review_status = "ok"

    company_source_key = source_row.get("company_source_key")
    company_row = company_dimension.get(company_source_key)

    company_analytical_key = None

    if company_row:
        company_analytical_key = company_row.get("company_analytical_key")

        if bool(company_row.get("is_internal_provider")):
            include_in_business_views = False
            exclude_reason = append_reason(exclude_reason, "internal_provider_company")
    else:
        include_in_business_views = False
        exclude_reason = append_reason(exclude_reason, "orphan_company")
        line_review_status = "review_required"

    parsed_order_date = parse_date(source_row.get("order_date"))
    order_date_key = date_key_from_date(parsed_order_date)

    if order_date_key is None or order_date_key not in time_keys:
        include_in_business_views = False
        exclude_reason = append_reason(exclude_reason, "invalid_order_date")
        line_review_status = "review_required"

    vendor_name = source_row.get("vendor_name")
    normalized_vendor_name = normalize_name(vendor_name)
    vendor_row = vendor_dimension.get(normalized_vendor_name) if normalized_vendor_name else None

    vendor_analytical_key = None
    is_internal_vendor = False
    include_vendor_in_business_views = True

    if vendor_row:
        vendor_analytical_key = vendor_row.get("vendor_analytical_key")
        is_internal_vendor = bool(vendor_row.get("is_internal_vendor"))
        include_vendor_in_business_views = bool(vendor_row.get("include_in_business_views"))

        if is_internal_vendor:
            include_in_business_views = False
            exclude_reason = append_reason(exclude_reason, "internal_vendor")

        if not include_vendor_in_business_views:
            include_in_business_views = False
            exclude_reason = append_reason(exclude_reason, "vendor_excluded")
    else:
        include_in_business_views = False
        exclude_reason = append_reason(exclude_reason, "orphan_vendor")
        line_review_status = "review_required"

    product_row = lookup_product(source_row, product_dimension)

    product_analytical_key = None
    product_identity_status = None
    dim_product_mapping_status = None
    is_product_mapped = False
    is_product_review_required = False
    include_product_in_business_views = True

    if product_row:
        product_analytical_key = product_row.get("product_analytical_key")
        product_identity_status = product_row.get("product_identity_status")
        dim_product_mapping_status = product_row.get("mapping_status")
        is_product_mapped = bool(product_row.get("is_mapped"))
        is_product_review_required = bool(product_row.get("is_review_required"))
        include_product_in_business_views = bool(product_row.get("include_in_business_views"))

        if is_product_review_required:
            include_in_business_views = False
            exclude_reason = append_reason(exclude_reason, "review_required_product")
            line_review_status = "review_required"

        if not include_product_in_business_views:
            include_in_business_views = False
            exclude_reason = append_reason(exclude_reason, "product_excluded")
    else:
        include_in_business_views = False
        exclude_reason = append_reason(exclude_reason, "orphan_product")
        line_review_status = "review_required"

    return {
        "canonical_purchase_order_line_id": source_row.get("id"),
        "source_system": source_row.get("source_system"),
        "source_domain": source_row.get("source_domain"),
        "source_order_line_id": source_row.get("source_order_line_id"),
        "source_order_id": source_row.get("source_order_id"),
        "purchase_order_name": source_row.get("purchase_order_name"),
        "company_source_key": company_source_key,
        "company_analytical_key": company_analytical_key,
        "company_id": source_row.get("company_id"),
        "company_name": source_row.get("company_name"),
        "final_purchase_source_status": source_row.get("final_purchase_source_status"),
        "company_migration_type": source_row.get("company_migration_type"),
        "history_source": source_row.get("history_source"),
        "include_odoo_history": source_row.get("include_odoo_history"),
        "operational_start_date": source_row.get("operational_start_date"),
        "migration_policy_source": source_row.get("migration_policy_source"),
        "order_date": source_row.get("order_date"),
        "order_date_key": order_date_key,
        "vendor_analytical_key": vendor_analytical_key,
        "vendor_id": source_row.get("vendor_id"),
        "vendor_name": vendor_name,
        "normalized_vendor_name": normalized_vendor_name,
        "is_internal_vendor": bool_to_int(is_internal_vendor),
        "include_vendor_in_business_views": bool_to_int(include_vendor_in_business_views),
        "product_analytical_key": product_analytical_key,
        "product_id": source_row.get("product_id"),
        "product_name": source_row.get("product_name"),
        "wansoft_code": source_row.get("wansoft_code"),
        "wansoft_product_name": source_row.get("wansoft_product_name"),
        "wansoft_department": source_row.get("wansoft_department"),
        "product_mapping_found": source_row.get("product_mapping_found"),
        "product_mapping_status": source_row.get("product_mapping_status"),
        "product_mapping_source": source_row.get("product_mapping_source"),
        "purchase_line_type": source_row.get("purchase_line_type"),
        "purchase_product_scope": source_row.get("purchase_product_scope"),
        "purchase_mapping_bucket": source_row.get("purchase_mapping_bucket"),
        "purchase_classification_source": source_row.get("purchase_classification_source"),
        "extracted_product_code": source_row.get("extracted_product_code"),
        "product_identity_status": product_identity_status,
        "dim_product_mapping_status": dim_product_mapping_status,
        "is_product_mapped": bool_to_int(is_product_mapped),
        "is_product_review_required": bool_to_int(is_product_review_required),
        "include_product_in_business_views": bool_to_int(include_product_in_business_views),
        "product_qty": source_row.get("product_qty"),
        "qty_received": source_row.get("qty_received"),
        "qty_invoiced": source_row.get("qty_invoiced"),
        "price_unit": source_row.get("price_unit"),
        "price_subtotal": source_row.get("price_subtotal"),
        "price_total": source_row.get("price_total"),
        "state": source_row.get("state"),
        "canonical_loaded_at": source_row.get("canonical_loaded_at"),
        "include_in_business_views": bool_to_int(include_in_business_views),
        "exclude_reason": exclude_reason,
        "line_review_status": line_review_status,
    }


def insert_batch(conn: Any, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return

    sql = f"""
    INSERT INTO {ANALYTICS_TABLE} (
        canonical_purchase_order_line_id,
        source_system,
        source_domain,
        source_order_line_id,
        source_order_id,
        purchase_order_name,
        company_source_key,
        company_analytical_key,
        company_id,
        company_name,
        final_purchase_source_status,
        company_migration_type,
        history_source,
        include_odoo_history,
        operational_start_date,
        migration_policy_source,
        order_date,
        order_date_key,
        vendor_analytical_key,
        vendor_id,
        vendor_name,
        normalized_vendor_name,
        is_internal_vendor,
        include_vendor_in_business_views,
        product_analytical_key,
        product_id,
        product_name,
        wansoft_code,
        wansoft_product_name,
        wansoft_department,
        product_mapping_found,
        product_mapping_status,
        product_mapping_source,
        purchase_line_type,
        purchase_product_scope,
        purchase_mapping_bucket,
        purchase_classification_source,
        extracted_product_code,
        product_identity_status,
        dim_product_mapping_status,
        is_product_mapped,
        is_product_review_required,
        include_product_in_business_views,
        product_qty,
        qty_received,
        qty_invoiced,
        price_unit,
        price_subtotal,
        price_total,
        state,
        canonical_loaded_at,
        include_in_business_views,
        exclude_reason,
        line_review_status
    )
    VALUES (
        %(canonical_purchase_order_line_id)s,
        %(source_system)s,
        %(source_domain)s,
        %(source_order_line_id)s,
        %(source_order_id)s,
        %(purchase_order_name)s,
        %(company_source_key)s,
        %(company_analytical_key)s,
        %(company_id)s,
        %(company_name)s,
        %(final_purchase_source_status)s,
        %(company_migration_type)s,
        %(history_source)s,
        %(include_odoo_history)s,
        %(operational_start_date)s,
        %(migration_policy_source)s,
        %(order_date)s,
        %(order_date_key)s,
        %(vendor_analytical_key)s,
        %(vendor_id)s,
        %(vendor_name)s,
        %(normalized_vendor_name)s,
        %(is_internal_vendor)s,
        %(include_vendor_in_business_views)s,
        %(product_analytical_key)s,
        %(product_id)s,
        %(product_name)s,
        %(wansoft_code)s,
        %(wansoft_product_name)s,
        %(wansoft_department)s,
        %(product_mapping_found)s,
        %(product_mapping_status)s,
        %(product_mapping_source)s,
        %(purchase_line_type)s,
        %(purchase_product_scope)s,
        %(purchase_mapping_bucket)s,
        %(purchase_classification_source)s,
        %(extracted_product_code)s,
        %(product_identity_status)s,
        %(dim_product_mapping_status)s,
        %(is_product_mapped)s,
        %(is_product_review_required)s,
        %(include_product_in_business_views)s,
        %(product_qty)s,
        %(qty_received)s,
        %(qty_invoiced)s,
        %(price_unit)s,
        %(price_subtotal)s,
        %(price_total)s,
        %(state)s,
        %(canonical_loaded_at)s,
        %(include_in_business_views)s,
        %(exclude_reason)s,
        %(line_review_status)s
    )
    """

    cursor = conn.cursor()
    cursor.executemany(sql, rows)
    conn.commit()
    cursor.close()


def build_analytics_purchase_order_lines(conn: Any) -> Dict[str, Any]:
    if not table_exists(conn, SOURCE_TABLE):
        raise RuntimeError(f"Required source table does not exist: {SOURCE_TABLE}")

    company_dimension = load_company_dimension(conn)
    time_keys = load_time_dimension(conn)
    vendor_dimension = load_vendor_dimension(conn)
    product_dimension = load_product_dimension(conn)

    source_query = f"""
        SELECT
            id,
            source_system,
            source_domain,
            source_order_line_id,
            source_order_id,
            purchase_order_name,
            vendor_id,
            vendor_name,
            company_id,
            company_name,
            company_source_key,
            final_purchase_source_status,
            company_migration_type,
            history_source,
            include_odoo_history,
            operational_start_date,
            migration_policy_source,
            product_id,
            product_name,
            wansoft_code,
            wansoft_product_name,
            wansoft_department,
            product_mapping_found,
            product_mapping_status,
            product_mapping_source,
            purchase_line_type,
            purchase_product_scope,
            purchase_mapping_bucket,
            purchase_classification_source,
            extracted_product_code,
            product_qty,
            qty_received,
            qty_invoiced,
            price_unit,
            price_subtotal,
            price_total,
            order_date,
            state,
            canonical_loaded_at
        FROM {SOURCE_TABLE}
    """

    # Read all source rows and close the cursor before any write on the same connection.
    # This avoids mysql-connector "Unread result found" errors.
    source_rows = fetch_all_dict(conn, source_query)

    write_cursor = conn.cursor()
    write_cursor.execute(f"DELETE FROM {ANALYTICS_TABLE}")
    conn.commit()
    write_cursor.close()

    total_rows = 0
    included_rows = 0
    excluded_rows = 0
    internal_vendor_rows = 0
    review_required_product_rows = 0
    orphan_company_rows = 0
    orphan_vendor_rows = 0
    orphan_product_rows = 0
    invalid_order_date_rows = 0

    analytics_batch: List[Dict[str, Any]] = []

    for source_row in source_rows:
        analytics_row = build_analytics_row(
            source_row=source_row,
            company_dimension=company_dimension,
            time_keys=time_keys,
            vendor_dimension=vendor_dimension,
            product_dimension=product_dimension,
        )

        total_rows += 1

        if analytics_row["include_in_business_views"] == 1:
            included_rows += 1
        else:
            excluded_rows += 1

        reason = analytics_row.get("exclude_reason") or ""

        if "internal_vendor" in reason:
            internal_vendor_rows += 1

        if "review_required_product" in reason:
            review_required_product_rows += 1

        if "orphan_company" in reason:
            orphan_company_rows += 1

        if "orphan_vendor" in reason:
            orphan_vendor_rows += 1

        if "orphan_product" in reason:
            orphan_product_rows += 1

        if "invalid_order_date" in reason:
            invalid_order_date_rows += 1

        analytics_batch.append(analytics_row)

        if len(analytics_batch) >= BATCH_SIZE:
            insert_batch(conn, analytics_batch)
            analytics_batch = []

    if analytics_batch:
        insert_batch(conn, analytics_batch)

    return {
        "total_rows": total_rows,
        "included_rows": included_rows,
        "excluded_rows": excluded_rows,
        "internal_vendor_rows": internal_vendor_rows,
        "review_required_product_rows": review_required_product_rows,
        "orphan_company_rows": orphan_company_rows,
        "orphan_vendor_rows": orphan_vendor_rows,
        "orphan_product_rows": orphan_product_rows,
        "invalid_order_date_rows": invalid_order_date_rows,
    }


def print_summary(summary: Dict[str, Any]) -> None:
    print("=====================================================")
    print("ANALYTICS PURCHASE ORDER LINES BUILD SUMMARY")
    print("=====================================================")
    print(f"table: {ANALYTICS_TABLE}")
    print(f"total_rows_prepared: {summary['total_rows']}")
    print(f"include_in_business_views: {summary['included_rows']}")
    print(f"excluded_from_business_views: {summary['excluded_rows']}")
    print(f"internal_vendor_rows: {summary['internal_vendor_rows']}")
    print(f"review_required_product_rows: {summary['review_required_product_rows']}")
    print(f"orphan_company_rows: {summary['orphan_company_rows']}")
    print(f"orphan_vendor_rows: {summary['orphan_vendor_rows']}")
    print(f"orphan_product_rows: {summary['orphan_product_rows']}")
    print(f"invalid_order_date_rows: {summary['invalid_order_date_rows']}")
    print("=====================================================")


def main() -> int:
    print("=====================================================")
    print("ANALYTICS PURCHASE ORDER LINES BUILD START")
    print("=====================================================")

    conn = get_db_connection()

    try:
        create_table_if_missing(conn)
        summary = build_analytics_purchase_order_lines(conn)
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
