"""
Export inventory location company mapping worklist.

Purpose:
- Generate a CSV worklist of internal_or_unknown inventory locations that are
  pending company mapping governance.
- This worklist is for manual review only.
- It does not approve mappings and does not modify the database.

Default output:
    seeds/inventory_location_company_mapping_worklist.csv

Run:
    python -m scripts.export_inventory_location_company_mapping_worklist

Optional output path:
    python -m scripts.export_inventory_location_company_mapping_worklist --output-file seeds/my_worklist.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.database.mysql import get_db_connection


DIM_TABLE = "dim_inventory_location"
DEFAULT_OUTPUT_PATH = "seeds/inventory_location_company_mapping_worklist.csv"

OUTPUT_COLUMNS = [
    "source_system",
    "source_location_id",
    "location_name",
    "normalized_location_name",
    "location_usage_type",
    "include_in_inventory_physical_views",
    "include_in_company_inventory_views",
    "company_mapping_status",
    "location_review_status",
    "current_source_row_count",
    "current_stock_qty",
    "proposed_company_source_key",
    "proposed_mapped_company_name",
    "review_decision",
    "review_notes",
]


def fetch_all_dict(conn: Any, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params or ())
    rows = cursor.fetchall()
    cursor.close()
    return rows


def fetch_one_dict(conn: Any, query: str, params: Optional[tuple] = None) -> Dict[str, Any]:
    rows = fetch_all_dict(conn, query, params)
    return rows[0] if rows else {}


def table_exists(conn: Any, table_name: str) -> bool:
    query = """
        SELECT COUNT(1) AS total
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = %s
    """
    row = fetch_one_dict(conn, query, (table_name,))
    return bool(row and int(row["total"]) > 0)


def get_worklist_rows(conn: Any) -> List[Dict[str, Any]]:
    query = f"""
        SELECT
            source_system,
            source_location_id,
            location_name,
            normalized_location_name,
            location_usage_type,
            include_in_inventory_physical_views,
            include_in_company_inventory_views,
            company_mapping_status,
            location_review_status,
            current_source_row_count,
            current_stock_qty
        FROM {DIM_TABLE}
        WHERE location_usage_type = 'internal_or_unknown'
          AND company_mapping_status = 'pending_location_mapping'
        ORDER BY
            current_source_row_count DESC,
            current_stock_qty DESC,
            location_name
    """
    return fetch_all_dict(conn, query)


def format_value(value: Any) -> Any:
    if value is None:
        return ""
    return value


def export_worklist(rows: List[Dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()

        for row in rows:
            writer.writerow(
                {
                    "source_system": format_value(row.get("source_system")),
                    "source_location_id": format_value(row.get("source_location_id")),
                    "location_name": format_value(row.get("location_name")),
                    "normalized_location_name": format_value(row.get("normalized_location_name")),
                    "location_usage_type": format_value(row.get("location_usage_type")),
                    "include_in_inventory_physical_views": format_value(row.get("include_in_inventory_physical_views")),
                    "include_in_company_inventory_views": format_value(row.get("include_in_company_inventory_views")),
                    "company_mapping_status": format_value(row.get("company_mapping_status")),
                    "location_review_status": format_value(row.get("location_review_status")),
                    "current_source_row_count": format_value(row.get("current_source_row_count")),
                    "current_stock_qty": format_value(row.get("current_stock_qty")),
                    "proposed_company_source_key": "",
                    "proposed_mapped_company_name": "",
                    "review_decision": "pending_review",
                    "review_notes": "",
                }
            )


def print_summary(rows: List[Dict[str, Any]], output_path: Path) -> None:
    total_rows = len(rows)
    total_current_source_rows = sum(int(row.get("current_source_row_count") or 0) for row in rows)
    total_current_stock_qty = sum(float(row.get("current_stock_qty") or 0) for row in rows)

    print("=====================================================")
    print("INVENTORY LOCATION COMPANY MAPPING WORKLIST EXPORT SUMMARY")
    print("=====================================================")
    print(f"output_file: {output_path}")
    print(f"worklist_rows: {total_rows}")
    print(f"total_current_source_row_count: {total_current_source_rows}")
    print(f"total_current_stock_qty: {total_current_stock_qty:.4f}")
    print("review_columns_added: proposed_company_source_key, proposed_mapped_company_name, review_decision, review_notes")
    print("=====================================================")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export inventory location company mapping worklist")
    parser.add_argument(
        "--output-file",
        default=DEFAULT_OUTPUT_PATH,
        help="Output CSV file path",
    )
    args = parser.parse_args()

    output_path = Path(args.output_file)

    print("=====================================================")
    print("INVENTORY LOCATION COMPANY MAPPING WORKLIST EXPORT START")
    print("=====================================================")

    conn = get_db_connection()

    try:
        if not table_exists(conn, DIM_TABLE):
            raise RuntimeError(f"Required table does not exist: {DIM_TABLE}")

        rows = get_worklist_rows(conn)
        export_worklist(rows, output_path)
        print_summary(rows, output_path)
        print("EXPORT RESULT: COMPLETED")
        return 0

    except Exception as exc:
        print("EXPORT RESULT: FAILED")
        print(f"error: {exc}")
        return 1

    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
