
"""
Analyze negative stock and location_usage_type in analytics_inventory_snapshot.

Purpose:
- Diagnose how negative stock_qty is distributed across location_usage_type.
- Identify whether negative stock is concentrated in virtual, partner, or internal_or_unknown locations.
- Preserve the current design rule: location classification is diagnostic and does not imply company mapping.
- Produce terminal summaries and optional CSV outputs under reports/analytics_inventory_negative_stock.

Run:
    python -m scripts.analyze_analytics_inventory_negative_stock
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from core.database.mysql import get_db_connection


TABLE_NAME = "analytics_inventory_snapshot"
OUTPUT_DIR = Path("reports") / "analytics_inventory_negative_stock"
LIMIT_TOP_ROWS = 100


def fetch_all_dict(conn: Any, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params or ())
    rows = cursor.fetchall()
    cursor.close()
    return rows


def table_exists(conn: Any, table_name: str) -> bool:
    query = """
        SELECT COUNT(1) AS total
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = %s
    """
    rows = fetch_all_dict(conn, query, (table_name,))
    return bool(rows and int(rows[0]["total"]) > 0)


def write_csv(filename: str, rows: List[Dict[str, Any]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename

    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].keys())

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def print_section(title: str) -> None:
    print()
    print("=====================================================")
    print(title)
    print("=====================================================")


def print_rows(rows: List[Dict[str, Any]], max_rows: int = 20) -> None:
    if not rows:
        print("<no rows>")
        return

    columns = list(rows[0].keys())
    widths = {column: len(column) for column in columns}

    preview_rows = rows[:max_rows]

    for row in preview_rows:
        for column in columns:
            widths[column] = max(widths[column], len(str(row.get(column, ""))))

    header = " | ".join(column.ljust(widths[column]) for column in columns)
    divider = "-+-".join("-" * widths[column] for column in columns)
    print(header)
    print(divider)

    for row in preview_rows:
        print(" | ".join(str(row.get(column, "")).ljust(widths[column]) for column in columns))

    if len(rows) > max_rows:
        print(f"... showing {max_rows} of {len(rows)} rows")


def run_query_block(conn: Any, title: str, query: str, filename: str, max_rows: int = 20) -> List[Dict[str, Any]]:
    rows = fetch_all_dict(conn, query)
    print_section(title)
    print_rows(rows, max_rows=max_rows)
    write_csv(filename, rows)
    return rows


def analyze(conn: Any) -> None:
    if not table_exists(conn, TABLE_NAME):
        raise RuntimeError(f"Required table does not exist: {TABLE_NAME}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    run_query_block(
        conn,
        "1. Overall inventory snapshot summary",
        f"""
        SELECT
            COUNT(1) AS total_rows,
            SUM(CASE WHEN stock_qty < 0 THEN 1 ELSE 0 END) AS negative_rows,
            SUM(CASE WHEN stock_qty = 0 THEN 1 ELSE 0 END) AS zero_rows,
            SUM(CASE WHEN stock_qty > 0 THEN 1 ELSE 0 END) AS positive_rows,
            COALESCE(SUM(stock_qty), 0) AS total_stock_qty,
            COALESCE(SUM(CASE WHEN stock_qty < 0 THEN stock_qty ELSE 0 END), 0) AS negative_stock_qty,
            COALESCE(SUM(CASE WHEN stock_qty > 0 THEN stock_qty ELSE 0 END), 0) AS positive_stock_qty,
            SUM(CASE WHEN include_in_business_views = TRUE THEN 1 ELSE 0 END) AS business_rows,
            SUM(CASE WHEN include_in_business_views = FALSE THEN 1 ELSE 0 END) AS excluded_rows
        FROM {TABLE_NAME}
        """,
        "01_overall_summary.csv",
    )

    run_query_block(
        conn,
        "2. Stock distribution by location_usage_type",
        f"""
        SELECT
            location_usage_type,
            COUNT(1) AS total_rows,
            SUM(CASE WHEN stock_qty < 0 THEN 1 ELSE 0 END) AS negative_rows,
            SUM(CASE WHEN stock_qty = 0 THEN 1 ELSE 0 END) AS zero_rows,
            SUM(CASE WHEN stock_qty > 0 THEN 1 ELSE 0 END) AS positive_rows,
            COALESCE(SUM(stock_qty), 0) AS total_stock_qty,
            COALESCE(SUM(CASE WHEN stock_qty < 0 THEN stock_qty ELSE 0 END), 0) AS negative_stock_qty,
            COALESCE(SUM(CASE WHEN stock_qty > 0 THEN stock_qty ELSE 0 END), 0) AS positive_stock_qty,
            SUM(CASE WHEN include_in_business_views = TRUE THEN 1 ELSE 0 END) AS business_rows,
            SUM(CASE WHEN include_in_business_views = FALSE THEN 1 ELSE 0 END) AS excluded_rows
        FROM {TABLE_NAME}
        GROUP BY location_usage_type
        ORDER BY total_stock_qty ASC
        """,
        "02_by_location_usage_type.csv",
    )

    run_query_block(
        conn,
        "3. Stock distribution by inventory_review_status",
        f"""
        SELECT
            inventory_review_status,
            COUNT(1) AS total_rows,
            SUM(CASE WHEN stock_qty < 0 THEN 1 ELSE 0 END) AS negative_rows,
            SUM(CASE WHEN stock_qty = 0 THEN 1 ELSE 0 END) AS zero_rows,
            SUM(CASE WHEN stock_qty > 0 THEN 1 ELSE 0 END) AS positive_rows,
            COALESCE(SUM(stock_qty), 0) AS total_stock_qty,
            COALESCE(SUM(CASE WHEN stock_qty < 0 THEN stock_qty ELSE 0 END), 0) AS negative_stock_qty,
            COALESCE(SUM(CASE WHEN stock_qty > 0 THEN stock_qty ELSE 0 END), 0) AS positive_stock_qty
        FROM {TABLE_NAME}
        GROUP BY inventory_review_status
        ORDER BY total_stock_qty ASC
        """,
        "03_by_inventory_review_status.csv",
    )

    run_query_block(
        conn,
        "4. Stock distribution by location_usage_type and inventory_review_status",
        f"""
        SELECT
            location_usage_type,
            inventory_review_status,
            COUNT(1) AS total_rows,
            SUM(CASE WHEN stock_qty < 0 THEN 1 ELSE 0 END) AS negative_rows,
            SUM(CASE WHEN stock_qty = 0 THEN 1 ELSE 0 END) AS zero_rows,
            SUM(CASE WHEN stock_qty > 0 THEN 1 ELSE 0 END) AS positive_rows,
            COALESCE(SUM(stock_qty), 0) AS total_stock_qty,
            COALESCE(SUM(CASE WHEN stock_qty < 0 THEN stock_qty ELSE 0 END), 0) AS negative_stock_qty,
            COALESCE(SUM(CASE WHEN stock_qty > 0 THEN stock_qty ELSE 0 END), 0) AS positive_stock_qty
        FROM {TABLE_NAME}
        GROUP BY
            location_usage_type,
            inventory_review_status
        ORDER BY total_stock_qty ASC
        """,
        "04_by_location_and_review_status.csv",
        max_rows=50,
    )

    run_query_block(
        conn,
        "5. Most negative source locations",
        f"""
        SELECT
            location_usage_type,
            source_location_id,
            location_name,
            COUNT(1) AS total_rows,
            SUM(CASE WHEN stock_qty < 0 THEN 1 ELSE 0 END) AS negative_rows,
            COALESCE(SUM(stock_qty), 0) AS total_stock_qty,
            COALESCE(SUM(CASE WHEN stock_qty < 0 THEN stock_qty ELSE 0 END), 0) AS negative_stock_qty,
            COALESCE(SUM(CASE WHEN stock_qty > 0 THEN stock_qty ELSE 0 END), 0) AS positive_stock_qty
        FROM {TABLE_NAME}
        GROUP BY
            location_usage_type,
            source_location_id,
            location_name
        HAVING COALESCE(SUM(stock_qty), 0) < 0
        ORDER BY total_stock_qty ASC
        LIMIT {LIMIT_TOP_ROWS}
        """,
        "05_most_negative_locations.csv",
        max_rows=30,
    )

    run_query_block(
        conn,
        "6. Most negative products",
        f"""
        SELECT
            product_analytical_key,
            odoo_product_id,
            odoo_product_name,
            wansoft_code,
            wansoft_product_name,
            product_identity_status,
            dim_product_mapping_status,
            inventory_review_status,
            COUNT(1) AS total_rows,
            SUM(CASE WHEN stock_qty < 0 THEN 1 ELSE 0 END) AS negative_rows,
            COALESCE(SUM(stock_qty), 0) AS total_stock_qty,
            COALESCE(SUM(CASE WHEN stock_qty < 0 THEN stock_qty ELSE 0 END), 0) AS negative_stock_qty,
            COALESCE(SUM(CASE WHEN stock_qty > 0 THEN stock_qty ELSE 0 END), 0) AS positive_stock_qty
        FROM {TABLE_NAME}
        GROUP BY
            product_analytical_key,
            odoo_product_id,
            odoo_product_name,
            wansoft_code,
            wansoft_product_name,
            product_identity_status,
            dim_product_mapping_status,
            inventory_review_status
        HAVING COALESCE(SUM(stock_qty), 0) < 0
        ORDER BY total_stock_qty ASC
        LIMIT {LIMIT_TOP_ROWS}
        """,
        "06_most_negative_products.csv",
        max_rows=30,
    )

    run_query_block(
        conn,
        "7. Most negative product-location combinations",
        f"""
        SELECT
            location_usage_type,
            source_location_id,
            location_name,
            product_analytical_key,
            odoo_product_id,
            odoo_product_name,
            wansoft_code,
            wansoft_product_name,
            inventory_review_status,
            COUNT(1) AS total_rows,
            COALESCE(SUM(stock_qty), 0) AS total_stock_qty
        FROM {TABLE_NAME}
        GROUP BY
            location_usage_type,
            source_location_id,
            location_name,
            product_analytical_key,
            odoo_product_id,
            odoo_product_name,
            wansoft_code,
            wansoft_product_name,
            inventory_review_status
        HAVING COALESCE(SUM(stock_qty), 0) < 0
        ORDER BY total_stock_qty ASC
        LIMIT {LIMIT_TOP_ROWS}
        """,
        "07_most_negative_product_location.csv",
        max_rows=30,
    )

    run_query_block(
        conn,
        "8. Negative rows detail",
        f"""
        SELECT
            source_inventory_snapshot_id,
            location_usage_type,
            source_location_id,
            location_name,
            product_analytical_key,
            odoo_product_id,
            odoo_product_name,
            wansoft_code,
            wansoft_product_name,
            stock_qty,
            include_in_business_views,
            inventory_review_status,
            exclude_reason
        FROM {TABLE_NAME}
        WHERE stock_qty < 0
        ORDER BY stock_qty ASC
        LIMIT {LIMIT_TOP_ROWS}
        """,
        "08_negative_rows_detail.csv",
        max_rows=30,
    )

    run_query_block(
        conn,
        "9. Business vs excluded negative stock",
        f"""
        SELECT
            include_in_business_views,
            location_usage_type,
            inventory_review_status,
            COUNT(1) AS total_rows,
            SUM(CASE WHEN stock_qty < 0 THEN 1 ELSE 0 END) AS negative_rows,
            COALESCE(SUM(stock_qty), 0) AS total_stock_qty,
            COALESCE(SUM(CASE WHEN stock_qty < 0 THEN stock_qty ELSE 0 END), 0) AS negative_stock_qty,
            COALESCE(SUM(CASE WHEN stock_qty > 0 THEN stock_qty ELSE 0 END), 0) AS positive_stock_qty
        FROM {TABLE_NAME}
        GROUP BY
            include_in_business_views,
            location_usage_type,
            inventory_review_status
        ORDER BY total_stock_qty ASC
        """,
        "09_business_vs_excluded_negative_stock.csv",
        max_rows=50,
    )

    print()
    print("=====================================================")
    print("OUTPUT FILES")
    print("=====================================================")
    print(f"CSV output folder: {OUTPUT_DIR}")
    print("Analysis complete.")


def main() -> int:
    print("=====================================================")
    print("ANALYTICS INVENTORY NEGATIVE STOCK ANALYSIS START")
    print("=====================================================")

    conn = get_db_connection()

    try:
        analyze(conn)
        print()
        print("ANALYSIS RESULT: COMPLETED")
        return 0
    except Exception as exc:
        print()
        print("ANALYSIS RESULT: FAILED")
        print(f"error: {exc}")
        return 1
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
