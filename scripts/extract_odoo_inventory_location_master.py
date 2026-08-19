"""
Extract Odoo inventory location master into staging.

Target staging table:
    stg_odoo_inventory_location_master

Odoo environment variables expected:
    ODOO_URL
    ODOO_DB_NAME
    ODOO_USER
    ODOO_PASSWORD

Backward-compatible Odoo aliases accepted:
    ODOO_DB
    ODOO_USERNAME
    ODOO_API_KEY

Database environment variables accepted:
    Project standard:
        ENV=dev uses:
            WANSOFT_DB_HOST_DEV
            WANSOFT_DB_USER_DEV
            WANSOFT_DB_PASSWORD_DEV (can be empty in dev)
            WANSOFT_DB_NAME_DEV

        ENV=prod uses:
            WANSOFT_DB_HOST
            WANSOFT_DB_USER
            WANSOFT_DB_PASSWORD
            WANSOFT_DB_NAME

    Generic aliases are accepted as fallback.

Design notes:
    - Uses Odoo XML-RPC API.
    - Dynamically discovers available stock.location fields with fields_get.
    - Does not fail when optional Odoo fields are missing.
    - Dynamically detects staging table columns and inserts only matching fields.
    - Rebuilds only stg_odoo_inventory_location_master.
    - Does not modify dim_inventory_location.
"""

from __future__ import annotations

import json
import os
import sys
import xmlrpc.client
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from dotenv import find_dotenv, load_dotenv
except ImportError as exc:
    raise RuntimeError(
        "Missing dependency: python-dotenv. Install it with: pip install python-dotenv"
    ) from exc


STAGING_TABLE = "stg_odoo_inventory_location_master"
SOURCE_SYSTEM = "odoo"
BATCH_SIZE = 1000


# =====================================================
# ENVIRONMENT LOADING
# =====================================================

SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parents[1]


def load_project_env() -> Optional[Path]:
    """
    Load the project .env file from the most common project locations.

    Search order:
        1. core/config/.env from the current working directory.
        2. .env from the current working directory.
        3. core/config/.env from parent directories.
        4. .env from parent directories.
        5. core/config/.env relative to this script.
        6. .env relative to this script.
        7. python-dotenv find_dotenv(usecwd=True).

    This avoids failures when the script is executed with python -m scripts.<module>
    and the .env file is not exactly where __file__.parents[1] expects it.
    """
    candidates = []

    cwd = Path.cwd().resolve()

    # Project-specific convention for this repository:
    # credentials live under core/config/.env
    candidates.append(cwd / "core" / "config" / ".env")
    candidates.append(cwd / ".env")

    for parent in cwd.parents:
        candidates.append(parent / "core" / "config" / ".env")
        candidates.append(parent / ".env")

    candidates.append(PROJECT_ROOT / "core" / "config" / ".env")
    candidates.append(PROJECT_ROOT / ".env")

    for parent in SCRIPT_PATH.parents:
        candidates.append(parent / "core" / "config" / ".env")
        candidates.append(parent / ".env")

    seen = set()
    for candidate in candidates:
        candidate_str = str(candidate)
        if candidate_str in seen:
            continue
        seen.add(candidate_str)

        if candidate.exists() and candidate.is_file():
            load_dotenv(candidate, override=False)
            print(f"env_file_loaded: {candidate}")
            return candidate

    found = find_dotenv(filename=".env", usecwd=True)
    if found:
        found_path = Path(found).resolve()
        load_dotenv(found_path, override=False)
        print(f"env_file_loaded: {found_path}")
        return found_path

    print("WARNING: No .env file found by extractor")
    return None


ENV_PATH = load_project_env()


# =====================================================
# CONSOLE HELPERS
# =====================================================

def print_header() -> None:
    print("=====================================================")
    print("ODOO INVENTORY LOCATION MASTER EXTRACTION START")
    print("=====================================================")


def print_result_success(total_rows: int) -> None:
    print("EXTRACTION RESULT: SUCCESS")
    print(f"rows_inserted: {total_rows}")


def print_result_failed(error: Any) -> None:
    print("EXTRACTION RESULT: FAILED")
    print(f"error: {error}")


def print_warning(message: str) -> None:
    print(f"WARNING: {message}")


def print_info(message: str) -> None:
    print(message)


# =====================================================
# ENVIRONMENT HELPERS
# =====================================================

def getenv_first(*names: str) -> Optional[str]:
    for name in names:
        value = os.getenv(name)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return None


def getenv_first_allow_empty(*names: str) -> Optional[str]:
    """
    Return the first environment variable that exists, even if its value is empty.

    This is needed for DEV database connections where the password variable exists
    but intentionally has no value, for example:
        WANSOFT_DB_PASSWORD_DEV=
    """
    for name in names:
        value = os.getenv(name)
        if value is not None:
            return str(value).strip()
    return None


def require_config_value(config: Dict[str, Optional[str]], label_map: Dict[str, str]) -> None:
    missing = []
    for key, display_name in label_map.items():
        if not config.get(key):
            missing.append(display_name)

    if missing:
        raise RuntimeError("Missing environment variables: " + ", ".join(missing))


def get_odoo_config() -> Dict[str, str]:
    config = {
        "url": getenv_first("ODOO_URL"),
        "db": getenv_first("ODOO_DB_NAME", "ODOO_DB"),
        "user": getenv_first("ODOO_USER", "ODOO_USERNAME"),
        "password": getenv_first("ODOO_PASSWORD", "ODOO_API_KEY"),
    }

    require_config_value(
        config,
        {
            "url": "ODOO_URL",
            "db": "ODOO_DB_NAME",
            "user": "ODOO_USER",
            "password": "ODOO_PASSWORD",
        },
    )

    return {
        "url": str(config["url"]).rstrip("/"),
        "db": str(config["db"]),
        "user": str(config["user"]),
        "password": "" if config.get("password") is None else str(config["password"]),
    }


def get_mysql_config() -> Dict[str, Any]:
    """
    Resolve the target MySQL/MariaDB database using this project's .env convention.

    Project standard:
        ENV=dev  -> WANSOFT_DB_HOST_DEV, WANSOFT_DB_USER_DEV,
                    WANSOFT_DB_PASSWORD_DEV, WANSOFT_DB_NAME_DEV
        ENV=prod -> WANSOFT_DB_HOST, WANSOFT_DB_USER,
                    WANSOFT_DB_PASSWORD, WANSOFT_DB_NAME

    Generic aliases are still accepted as fallback for compatibility.
    """
    env = (getenv_first("ENV") or "prod").strip().lower()
    is_dev = env in {"dev", "development", "local", "test", "testing"}

    if is_dev:
        config = {
            "host": getenv_first("WANSOFT_DB_HOST_DEV", "MYSQL_HOST_DEV", "DB_HOST_DEV", "DWH_HOST_DEV"),
            "port": getenv_first("WANSOFT_DB_PORT_DEV", "MYSQL_PORT_DEV", "DB_PORT_DEV", "DWH_PORT_DEV") or "3306",
            "user": getenv_first("WANSOFT_DB_USER_DEV", "MYSQL_USER_DEV", "DB_USER_DEV", "DWH_USER_DEV"),
            "password": getenv_first_allow_empty(
                "WANSOFT_DB_PASSWORD_DEV",
                "MYSQL_PASSWORD_DEV",
                "DB_PASSWORD_DEV",
                "DWH_PASSWORD_DEV",
            ),
            "database": getenv_first("WANSOFT_DB_NAME_DEV", "MYSQL_DATABASE_DEV", "DB_NAME_DEV", "DWH_DATABASE_DEV"),
        }
        expected_labels = {
            "host": "WANSOFT_DB_HOST_DEV",
            "user": "WANSOFT_DB_USER_DEV",
            "database": "WANSOFT_DB_NAME_DEV",
        }
    else:
        config = {
            "host": getenv_first("WANSOFT_DB_HOST", "MYSQL_HOST", "DB_HOST", "DWH_HOST", "DW_HOST", "MARIADB_HOST"),
            "port": getenv_first("WANSOFT_DB_PORT", "MYSQL_PORT", "DB_PORT", "DWH_PORT", "DW_PORT", "MARIADB_PORT") or "3306",
            "user": getenv_first("WANSOFT_DB_USER", "MYSQL_USER", "DB_USER", "DWH_USER", "DW_USER", "MARIADB_USER"),
            "password": getenv_first_allow_empty(
                "WANSOFT_DB_PASSWORD",
                "MYSQL_PASSWORD",
                "DB_PASSWORD",
                "DWH_PASSWORD",
                "DW_PASSWORD",
                "MARIADB_PASSWORD",
            ),
            "database": getenv_first(
                "WANSOFT_DB_NAME",
                "MYSQL_DATABASE",
                "DB_NAME",
                "DWH_DATABASE",
                "DW_DATABASE",
                "DATABASE_NAME",
                "MARIADB_DATABASE",
            ),
        }
        expected_labels = {
            "host": "WANSOFT_DB_HOST",
            "user": "WANSOFT_DB_USER",
            "database": "WANSOFT_DB_NAME",
        }

    require_config_value(config, expected_labels)

    print_info(f"database_env: {env}")
    print_info("database_config_source: " + ("WANSOFT_DEV" if is_dev else "WANSOFT_PROD"))

    return {
        "host": str(config["host"]),
        "port": int(str(config["port"])),
        "user": str(config["user"]),
        "password": "" if config.get("password") is None else str(config["password"]),
        "database": str(config["database"]),
    }


# =====================================================
# MYSQL HELPERS
# =====================================================

def get_mysql_connection() -> Tuple[Any, str]:
    mysql_config = get_mysql_config()

    try:
        import pymysql

        connection = pymysql.connect(
            host=mysql_config["host"],
            port=mysql_config["port"],
            user=mysql_config["user"],
            password=mysql_config["password"],
            database=mysql_config["database"],
            charset="utf8mb4",
            autocommit=False,
            cursorclass=pymysql.cursors.DictCursor,
        )
        return connection, "pymysql"

    except ImportError:
        pass

    try:
        import mysql.connector

        connection = mysql.connector.connect(
            host=mysql_config["host"],
            port=mysql_config["port"],
            user=mysql_config["user"],
            password=mysql_config["password"],
            database=mysql_config["database"],
        )
        return connection, "mysql.connector"

    except ImportError as exc:
        raise RuntimeError(
            "Missing MySQL driver. Install one of these: pip install pymysql or pip install mysql-connector-python"
        ) from exc


def get_cursor(connection: Any, driver: str, dictionary: bool = False) -> Any:
    if driver == "mysql.connector" and dictionary:
        return connection.cursor(dictionary=True)
    return connection.cursor()


def get_table_columns(connection: Any, driver: str, table_name: str) -> List[str]:
    cursor = get_cursor(connection, driver, dictionary=True)
    try:
        cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
        rows = cursor.fetchall()

        columns = []
        for row in rows:
            if isinstance(row, dict):
                field_name = row.get("Field") or row.get("field")
            else:
                field_name = row[0]

            if field_name:
                columns.append(str(field_name))

        if not columns:
            raise RuntimeError(f"No columns found for table {table_name}")

        return columns

    finally:
        cursor.close()


def truncate_table(connection: Any, driver: str, table_name: str) -> None:
    cursor = get_cursor(connection, driver)
    try:
        cursor.execute(f"TRUNCATE TABLE `{table_name}`")
    finally:
        cursor.close()


def insert_rows_dynamic(
    connection: Any,
    driver: str,
    table_name: str,
    rows: List[Dict[str, Any]],
    available_columns: List[str],
) -> int:
    if not rows:
        return 0

    available_column_set = set(available_columns)

    candidate_columns = []
    for row in rows:
        for key in row.keys():
            if key in available_column_set and key not in candidate_columns:
                candidate_columns.append(key)

    if not candidate_columns:
        raise RuntimeError(f"No matching columns between generated rows and table {table_name}")

    placeholders = ", ".join(["%s"] * len(candidate_columns))
    quoted_columns = ", ".join(f"`{column}`" for column in candidate_columns)

    sql = f"INSERT INTO `{table_name}` ({quoted_columns}) VALUES ({placeholders})"

    values = []
    for row in rows:
        values.append(tuple(row.get(column) for column in candidate_columns))

    cursor = get_cursor(connection, driver)
    try:
        cursor.executemany(sql, values)
        return len(values)
    finally:
        cursor.close()


# =====================================================
# ODOO HELPERS
# =====================================================

def get_odoo_clients(odoo_config: Dict[str, str]) -> Tuple[Any, Any]:
    common = xmlrpc.client.ServerProxy(
        f"{odoo_config['url']}/xmlrpc/2/common",
        allow_none=True,
    )
    models = xmlrpc.client.ServerProxy(
        f"{odoo_config['url']}/xmlrpc/2/object",
        allow_none=True,
    )
    return common, models


def authenticate_odoo(common: Any, odoo_config: Dict[str, str]) -> int:
    uid = common.authenticate(
        odoo_config["db"],
        odoo_config["user"],
        odoo_config["password"],
        {},
    )

    if not uid:
        raise RuntimeError("Odoo authentication failed. Check ODOO_DB_NAME, ODOO_USER and ODOO_PASSWORD.")

    return int(uid)


def get_available_model_fields(
    models: Any,
    odoo_config: Dict[str, str],
    uid: int,
    model_name: str,
) -> Dict[str, Any]:
    return models.execute_kw(
        odoo_config["db"],
        uid,
        odoo_config["password"],
        model_name,
        "fields_get",
        [],
        {"attributes": ["string", "type"]},
    )


def choose_existing_fields(
    available_fields: Dict[str, Any],
    required_fields: Iterable[str],
    optional_fields: Iterable[str],
) -> List[str]:
    selected_fields: List[str] = []

    for field_name in required_fields:
        if field_name not in available_fields:
            raise RuntimeError(f"Required field {field_name!r} not found in Odoo model stock.location")
        selected_fields.append(field_name)

    missing_optional = []
    for field_name in optional_fields:
        if field_name in available_fields:
            selected_fields.append(field_name)
        else:
            missing_optional.append(field_name)

    if missing_optional:
        print_warning(
            "Optional stock.location fields not available in this Odoo database: "
            + ", ".join(missing_optional)
        )

    return selected_fields


def fetch_stock_locations_batch(
    models: Any,
    odoo_config: Dict[str, str],
    uid: int,
    fields: List[str],
    offset: int,
    limit: int,
) -> List[Dict[str, Any]]:
    return models.execute_kw(
        odoo_config["db"],
        uid,
        odoo_config["password"],
        "stock.location",
        "search_read",
        [[]],
        {
            "fields": fields,
            "order": "id asc",
            "offset": offset,
            "limit": limit,
            "context": {"active_test": False},
        },
    )


def extract_stock_locations(
    models: Any,
    odoo_config: Dict[str, str],
    uid: int,
) -> List[Dict[str, Any]]:
    required_fields = [
        "id",
        "name",
        "usage",
    ]

    optional_fields = [
        "complete_name",
        "display_name",
        "location_id",
        "company_id",
        "active",
        "scrap_location",
        "return_location",
        "barcode",
        "replenish_location",
    ]

    available_fields = get_available_model_fields(
        models=models,
        odoo_config=odoo_config,
        uid=uid,
        model_name="stock.location",
    )

    location_fields = choose_existing_fields(
        available_fields=available_fields,
        required_fields=required_fields,
        optional_fields=optional_fields,
    )

    all_locations: List[Dict[str, Any]] = []
    offset = 0

    while True:
        batch = fetch_stock_locations_batch(
            models=models,
            odoo_config=odoo_config,
            uid=uid,
            fields=location_fields,
            offset=offset,
            limit=BATCH_SIZE,
        )

        if not isinstance(batch, list):
            raise RuntimeError("Unexpected Odoo response for stock.location search_read")

        if not batch:
            break

        all_locations.extend(batch)

        if len(batch) < BATCH_SIZE:
            break

        offset += BATCH_SIZE

    return all_locations


# =====================================================
# TRANSFORMATION HELPERS
# =====================================================

def many2one_id(value: Any) -> Optional[int]:
    if isinstance(value, (list, tuple)) and len(value) >= 1:
        if value[0] is False or value[0] is None:
            return None
        return int(value[0])

    if isinstance(value, int):
        return value

    return None


def many2one_name(value: Any) -> Optional[str]:
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        if value[1] is False or value[1] is None:
            return None
        return str(value[1])

    return None


def bool_or_none(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if value is False:
        return False
    if value is True:
        return True
    return bool(value)


def normalize_usage_type(usage: Optional[str]) -> str:
    if not usage:
        return "internal_or_unknown"

    usage_norm = str(usage).strip().lower()

    if usage_norm in {"supplier", "customer"}:
        return "partner"

    if usage_norm in {"inventory", "production", "transit", "view"}:
        return "virtual"

    if usage_norm == "internal":
        return "internal_or_unknown"

    return "internal_or_unknown"


def company_availability(company_id: Optional[int]) -> str:
    if company_id is None:
        return "shared"
    return "company_specific"


def make_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def build_location_name(location: Dict[str, Any]) -> Optional[str]:
    for key in ("complete_name", "display_name", "name"):
        value = location.get(key)
        if value:
            return str(value)
    return None


def transform_location(location: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.now()

    odoo_location_id = location.get("id")
    source_location_id = str(odoo_location_id) if odoo_location_id is not None else None

    raw_usage = location.get("usage")
    normalized_usage = normalize_usage_type(raw_usage)

    parent_location_id = many2one_id(location.get("location_id"))
    parent_location_name = many2one_name(location.get("location_id"))

    odoo_company_id = many2one_id(location.get("company_id"))
    odoo_company_name = many2one_name(location.get("company_id"))

    location_name = build_location_name(location)

    row = {
        # Core source identifiers
        "source_system": SOURCE_SYSTEM,
        "source_location_id": source_location_id,
        "odoo_location_id": odoo_location_id,

        # Names
        "location_name": location_name,
        "odoo_location_name": location.get("name"),
        "odoo_complete_name": location.get("complete_name"),
        "odoo_display_name": location.get("display_name"),

        # Usage
        "location_usage_type": normalized_usage,
        "odoo_usage": raw_usage,
        "usage": raw_usage,

        # Parent
        "odoo_parent_location_id": parent_location_id,
        "parent_location_id": parent_location_id,
        "odoo_parent_location_name": parent_location_name,
        "parent_location_name": parent_location_name,

        # Company
        "odoo_company_id": odoo_company_id,
        "company_id": odoo_company_id,
        "odoo_company_name": odoo_company_name,
        "company_name": odoo_company_name,
        "company_availability": company_availability(odoo_company_id),

        # Flags
        "is_active": bool_or_none(location.get("active")),
        "active": bool_or_none(location.get("active")),
        "is_scrap_location": bool_or_none(location.get("scrap_location")),
        "scrap_location": bool_or_none(location.get("scrap_location")),
        "is_return_location": bool_or_none(location.get("return_location")),
        "return_location": bool_or_none(location.get("return_location")),
        "replenish_location": bool_or_none(location.get("replenish_location")),

        # Operational attributes
        "barcode": location.get("barcode"),

        # Raw metadata
        "raw_payload": make_json(location),
        "odoo_raw_payload": make_json(location),

        # Audit fields
        "extracted_at": now,
        "created_at": now,
        "updated_at": now,
    }

    return row


def transform_locations(locations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [transform_location(location) for location in locations]


# =====================================================
# MAIN EXTRACTION
# =====================================================

def run_extraction() -> int:
    print_header()
    print_info("mode: api")

    odoo_config = get_odoo_config()

    common, models = get_odoo_clients(odoo_config)
    uid = authenticate_odoo(common, odoo_config)

    locations = extract_stock_locations(
        models=models,
        odoo_config=odoo_config,
        uid=uid,
    )

    rows = transform_locations(locations)

    connection, driver = get_mysql_connection()

    try:
        table_columns = get_table_columns(connection, driver, STAGING_TABLE)
        truncate_table(connection, driver, STAGING_TABLE)

        inserted_rows = insert_rows_dynamic(
            connection=connection,
            driver=driver,
            table_name=STAGING_TABLE,
            rows=rows,
            available_columns=table_columns,
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    return inserted_rows


def main() -> int:
    try:
        inserted_rows = run_extraction()
        print_result_success(inserted_rows)
        return 0

    except Exception as exc:
        print_result_failed(exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
