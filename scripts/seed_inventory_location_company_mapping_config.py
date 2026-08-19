"""
Seed inventory_location_company_mapping_config.

This script loads governed inventory location to company mappings from a CSV file.

Main rules:
- Dry run is the default behavior.
- Apply requires the explicit --apply flag.
- Mappings are data governance inputs, not inferred rules.
- source_system + source_location_id must exist in dim_inventory_location.
- Approved active mappings are allowed only for internal_or_unknown locations.
- Approved active mappings require a valid company_source_key in dim_company_analytical.
- Only one active approved mapping is allowed per source location.

Default seed file:
seeds/inventory_location_company_mapping_config_seed.csv
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.database.mysql import get_db_connection


TABLE_NAME = "inventory_location_company_mapping_config"
DIM_LOCATION_TABLE = "dim_inventory_location"
DIM_COMPANY_TABLE = "dim_company_analytical"
DEFAULT_SEED_PATH = "seeds/inventory_location_company_mapping_config_seed.csv"

REQUIRED_COLUMNS = [
    "source_system",
    "source_location_id",
    "location_name_snapshot",
    "company_source_key",
    "mapped_company_name",
    "mapping_status",
    "mapping_method",
    "mapping_notes",
    "effective_from_date",
    "effective_to_date",
    "is_active",
]

VALID_MAPPING_STATUSES = {
    "approved",
    "pending_review",
    "rejected",
    "inactive",
}


@dataclass
class SeedRow:
    source_system: str
    source_location_id: str
    location_name_snapshot: Optional[str]
    company_source_key: Optional[str]
    mapped_company_name: Optional[str]
    mapping_status: str
    mapping_method: Optional[str]
    mapping_notes: Optional[str]
    effective_from_date: Optional[date]
    effective_to_date: Optional[date]
    is_active: bool


def clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None

    text = " ".join(str(value).strip().split())

    if not text:
        return None

    return text


def parse_bool(value: Any, default: bool = True) -> bool:
    text = clean_text(value)

    if text is None:
        return default

    text = text.lower()

    if text in {"1", "true", "yes", "y", "si", "sí"}:
        return True

    if text in {"0", "false", "no", "n"}:
        return False

    return default


def bool_to_int(value: bool) -> int:
    return 1 if value else 0


def parse_date(value: Any) -> Optional[date]:
    text = clean_text(value)

    if text is None:
        return None

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass

    raise ValueError(f"Invalid date value: {value}")


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


def get_columns(conn: Any, table_name: str) -> set[str]:
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
    return {row["column_name"] for row in rows}


def fetch_all_dict(conn: Any, query: str, params: Optional[tuple] = None) -> list[dict[str, Any]]:
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params or ())
    rows = cursor.fetchall()
    cursor.close()
    return rows


def create_or_upgrade_config_table(conn: Any) -> None:
    ddl = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        source_system VARCHAR(100) NOT NULL,
        source_location_id VARCHAR(100) NOT NULL,
        location_name_snapshot VARCHAR(500) NULL,
        company_source_key VARCHAR(255) NULL,
        mapped_company_name VARCHAR(255) NULL,
        mapping_status VARCHAR(100) NOT NULL DEFAULT 'pending_review',
        mapping_method VARCHAR(255) NULL,
        mapping_notes TEXT NULL,
        effective_from_date DATE NULL,
        effective_to_date DATE NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        KEY idx_inventory_location_mapping_source (source_system, source_location_id),
        KEY idx_inventory_location_mapping_company (company_source_key),
        KEY idx_inventory_location_mapping_status (mapping_status),
        KEY idx_inventory_location_mapping_active (is_active)
    )
    """
    cursor = conn.cursor()
    cursor.execute(ddl)
    conn.commit()
    cursor.close()

    required_defs = {
        "location_name_snapshot": "VARCHAR(500) NULL",
        "company_source_key": "VARCHAR(255) NULL",
        "mapped_company_name": "VARCHAR(255) NULL",
        "mapping_status": "VARCHAR(100) NOT NULL DEFAULT 'pending_review'",
        "mapping_method": "VARCHAR(255) NULL",
        "mapping_notes": "TEXT NULL",
        "effective_from_date": "DATE NULL",
        "effective_to_date": "DATE NULL",
        "is_active": "BOOLEAN NOT NULL DEFAULT TRUE",
    }

    current_columns = get_columns(conn, TABLE_NAME)
    cursor = conn.cursor()

    for column_name, column_def in required_defs.items():
        if column_name not in current_columns:
            cursor.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN {column_name} {column_def}")

    conn.commit()
    cursor.close()


def read_seed_file(seed_path: Path) -> List[SeedRow]:
    if not seed_path.exists():
        raise FileNotFoundError(f"Seed file not found: {seed_path}")

    rows: List[SeedRow] = []

    with seed_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing_columns = [column for column in REQUIRED_COLUMNS if column not in fieldnames]

        if missing_columns:
            raise ValueError(f"Seed file is missing required columns: {missing_columns}")

        for line_number, raw in enumerate(reader, start=2):
            source_system = clean_text(raw.get("source_system")) or "odoo"
            source_location_id = clean_text(raw.get("source_location_id"))
            mapping_status = (clean_text(raw.get("mapping_status")) or "pending_review").lower()

            if not source_location_id:
                raise ValueError(f"Line {line_number}: source_location_id is required")

            if mapping_status not in VALID_MAPPING_STATUSES:
                raise ValueError(f"Line {line_number}: invalid mapping_status: {mapping_status}")

            rows.append(
                SeedRow(
                    source_system=source_system,
                    source_location_id=source_location_id,
                    location_name_snapshot=clean_text(raw.get("location_name_snapshot")),
                    company_source_key=clean_text(raw.get("company_source_key")),
                    mapped_company_name=clean_text(raw.get("mapped_company_name")),
                    mapping_status=mapping_status,
                    mapping_method=clean_text(raw.get("mapping_method")) or "manual_governance",
                    mapping_notes=clean_text(raw.get("mapping_notes")),
                    effective_from_date=parse_date(raw.get("effective_from_date")),
                    effective_to_date=parse_date(raw.get("effective_to_date")),
                    is_active=parse_bool(raw.get("is_active"), default=True),
                )
            )

    return rows


def load_dim_locations(conn: Any) -> Dict[Tuple[str, str], Dict[str, Any]]:
    query = f"""
        SELECT
            source_system,
            source_location_id,
            location_name,
            location_usage_type
        FROM {DIM_LOCATION_TABLE}
    """
    result: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for row in fetch_all_dict(conn, query):
        key = (str(row["source_system"]), str(row["source_location_id"]))
        result[key] = row

    return result


def load_companies(conn: Any) -> set[str]:
    query = f"""
        SELECT company_source_key
        FROM {DIM_COMPANY_TABLE}
    """
    return {str(row["company_source_key"]) for row in fetch_all_dict(conn, query)}


def validate_seed_rows(
    rows: List[SeedRow],
    dim_locations: Dict[Tuple[str, str], Dict[str, Any]],
    companies: set[str],
) -> List[Dict[str, Any]]:
    problems: List[Dict[str, Any]] = []
    active_approved_locations: Dict[Tuple[str, str], int] = {}

    for index, row in enumerate(rows, start=1):
        key = (row.source_system, row.source_location_id)
        dim_location = dim_locations.get(key)

        if dim_location is None:
            problems.append(
                {
                    "row_number": index,
                    "source_system": row.source_system,
                    "source_location_id": row.source_location_id,
                    "issue": "source location does not exist in dim_inventory_location",
                }
            )
            continue

        location_usage_type = dim_location.get("location_usage_type")

        if row.is_active and row.mapping_status == "approved":
            active_approved_locations[key] = active_approved_locations.get(key, 0) + 1

            if location_usage_type != "internal_or_unknown":
                problems.append(
                    {
                        "row_number": index,
                        "source_system": row.source_system,
                        "source_location_id": row.source_location_id,
                        "location_usage_type": location_usage_type,
                        "issue": "approved active mappings are allowed only for internal_or_unknown locations",
                    }
                )

            if not row.company_source_key:
                problems.append(
                    {
                        "row_number": index,
                        "source_system": row.source_system,
                        "source_location_id": row.source_location_id,
                        "issue": "approved active mapping requires company_source_key",
                    }
                )

            elif row.company_source_key not in companies:
                problems.append(
                    {
                        "row_number": index,
                        "source_system": row.source_system,
                        "source_location_id": row.source_location_id,
                        "company_source_key": row.company_source_key,
                        "issue": "company_source_key does not exist in dim_company_analytical",
                    }
                )

        if row.effective_to_date and row.effective_from_date:
            if row.effective_to_date < row.effective_from_date:
                problems.append(
                    {
                        "row_number": index,
                        "source_system": row.source_system,
                        "source_location_id": row.source_location_id,
                        "issue": "effective_to_date is before effective_from_date",
                    }
                )

    for key, count in active_approved_locations.items():
        if count > 1:
            problems.append(
                {
                    "source_system": key[0],
                    "source_location_id": key[1],
                    "active_approved_count": count,
                    "issue": "more than one active approved mapping in seed for source location",
                }
            )

    return problems


def insert_seed_rows(conn: Any, rows: List[SeedRow]) -> None:
    sql = f"""
        INSERT INTO {TABLE_NAME} (
            source_system,
            source_location_id,
            location_name_snapshot,
            company_source_key,
            mapped_company_name,
            mapping_status,
            mapping_method,
            mapping_notes,
            effective_from_date,
            effective_to_date,
            is_active
        )
        VALUES (
            %(source_system)s,
            %(source_location_id)s,
            %(location_name_snapshot)s,
            %(company_source_key)s,
            %(mapped_company_name)s,
            %(mapping_status)s,
            %(mapping_method)s,
            %(mapping_notes)s,
            %(effective_from_date)s,
            %(effective_to_date)s,
            %(is_active)s
        )
    """

    payload = []

    for row in rows:
        payload.append(
            {
                "source_system": row.source_system,
                "source_location_id": row.source_location_id,
                "location_name_snapshot": row.location_name_snapshot,
                "company_source_key": row.company_source_key,
                "mapped_company_name": row.mapped_company_name,
                "mapping_status": row.mapping_status,
                "mapping_method": row.mapping_method,
                "mapping_notes": row.mapping_notes,
                "effective_from_date": row.effective_from_date,
                "effective_to_date": row.effective_to_date,
                "is_active": bool_to_int(row.is_active),
            }
        )

    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {TABLE_NAME}")

    if payload:
        cursor.executemany(sql, payload)

    conn.commit()
    cursor.close()


def print_summary(seed_path: Path, rows: List[SeedRow], problems: List[Dict[str, Any]], applied: bool) -> None:
    approved_active = sum(1 for row in rows if row.is_active and row.mapping_status == "approved")
    pending_review = sum(1 for row in rows if row.mapping_status == "pending_review")
    rejected = sum(1 for row in rows if row.mapping_status == "rejected")
    inactive = sum(1 for row in rows if not row.is_active or row.mapping_status == "inactive")

    print("=====================================================")
    print("INVENTORY LOCATION COMPANY MAPPING SEED SUMMARY")
    print("=====================================================")
    print(f"seed_file: {seed_path}")
    print(f"rows_read: {len(rows)}")
    print(f"approved_active_rows: {approved_active}")
    print(f"pending_review_rows: {pending_review}")
    print(f"rejected_rows: {rejected}")
    print(f"inactive_rows: {inactive}")
    print(f"validation_problems: {len(problems)}")
    print(f"applied: {applied}")

    if problems:
        print("-----------------------------------------------------")
        print("VALIDATION PROBLEMS")
        print("-----------------------------------------------------")
        for problem in problems[:50]:
            print(problem)

        if len(problems) > 50:
            print(f"... showing 50 of {len(problems)} problems")

    print("=====================================================")


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed inventory location company mapping config")
    parser.add_argument(
        "--seed-file",
        default=DEFAULT_SEED_PATH,
        help="CSV seed file path",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the seed to the database. Without this flag the script runs as dry-run.",
    )

    args = parser.parse_args()
    seed_path = Path(args.seed_file)

    print("=====================================================")
    print("INVENTORY LOCATION COMPANY MAPPING SEED START")
    print("=====================================================")
    print(f"mode: {'apply' if args.apply else 'dry-run'}")

    conn = get_db_connection()

    try:
        if not table_exists(conn, DIM_LOCATION_TABLE):
            raise RuntimeError(f"Required table does not exist: {DIM_LOCATION_TABLE}")

        if not table_exists(conn, DIM_COMPANY_TABLE):
            raise RuntimeError(f"Required table does not exist: {DIM_COMPANY_TABLE}")

        create_or_upgrade_config_table(conn)

        rows = read_seed_file(seed_path)
        dim_locations = load_dim_locations(conn)
        companies = load_companies(conn)
        problems = validate_seed_rows(rows, dim_locations, companies)

        if problems:
            print_summary(seed_path, rows, problems, applied=False)
            print("SEED RESULT: FAILED")
            return 1

        if args.apply:
            insert_seed_rows(conn, rows)
            print_summary(seed_path, rows, problems, applied=True)
            print("SEED RESULT: APPLIED")
            return 0

        print_summary(seed_path, rows, problems, applied=False)
        print("SEED RESULT: DRY RUN PASSED")
        return 0

    except Exception as exc:
        print("SEED RESULT: FAILED")
        print(f"error: {exc}")
        return 1

    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
