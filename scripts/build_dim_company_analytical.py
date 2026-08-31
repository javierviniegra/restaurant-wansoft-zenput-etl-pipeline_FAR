"""
Build dim_company_analytical.

This script creates and refreshes the shared analytical company dimension used by
the unified analytical layer.

The table is part of the MySQL analytical layer.

It does not implement BI logic.
It does not build reports.
It does not replace existing canonical or legacy source tables.

Main rules:
- company_source_key is the central analytical company key.
- Purchases and Inventory follow COMPANY_SOURCE.
- Sales remains Wansoft by default where applicable.
- Zenput uses core/config/zenput.py location mapping.
- Zenput-only locations are valid analytical locations.
- Puebla is mapped from Zenput but is not Zenput-only.
- Internal providers are marked and excluded from business views by default.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import Any, Dict, Iterable, Optional, Set

import importlib

from core.database.mysql import get_db_connection


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ANALYTICAL_TABLE = "dim_company_analytical"

ZENPUT_ONLY_COMPANIES = {
    "León",
    "Lindavista",
    "Perisur",
}

INTERNAL_PROVIDER_NAMES = {
    "EL BODEGON DE FITO",
    "LAS EMPANADAS DE MARIA EVA",
}

INTERNAL_PROVIDER_KEYS = {
    "Bodegón": "EL BODEGON DE FITO",
    "Empanadas": "LAS EMPANADAS DE MARIA EVA",
}

KNOWN_FUTURE_ROLLOUTS = {
    "Puebla",
}

MIGRATED_FROM_WANSOFT_COMPANIES = {
    "Antenas",
    "La Esquina Coyoacán",
    "Acoxpa",
    "Tepeyac",
    "Oceanía",
}

NEW_ODOO_BRANCH_COMPANIES = {
    "CentroMyJ",
    "Puebla",
}


VALID_PURCHASES_SOURCE_SYSTEM = {
    "wansoft",
    "odoo",
    "mixed_by_operational_start_date",
    "none",
    "pending",
    "not_applicable",
}

VALID_INVENTORY_SOURCE_SYSTEM = {
    "wansoft",
    "odoo",
    "mixed_by_operational_start_date",
    "none",
    "pending",
    "not_applicable",
}

VALID_SALES_SOURCE_SYSTEM = {
    "wansoft",
    "none",
    "pending",
    "not_applicable",
}

VALID_ZENPUT_SOURCE_STATUS = {
    "mapped",
    "zenput_only",
    "not_detected",
    "pending",
    "not_applicable",
}


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

@dataclass
class CompanyAnalyticalRow:
    company_source_key: str
    display_name: str

    normalized_name: Optional[str] = None
    brand_group: Optional[str] = None

    is_active_branch: bool = False
    is_internal_provider: bool = False
    is_final_operating_branch: bool = False
    is_future_rollout: bool = False

    is_wansoft_company: bool = False
    is_odoo_company: bool = False
    is_zenput_location: bool = False
    is_zenput_only: bool = False

    purchases_source_system: str = "none"
    inventory_source_system: str = "none"
    sales_source_system: str = "none"
    zenput_source_status: str = "not_detected"

    rollout_type: Optional[str] = None
    rollout_status: Optional[str] = None
    operational_start_date: Optional[date] = None

    include_in_business_views: bool = True
    exclude_reason: Optional[str] = None

    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def normalize_name(value: Optional[str]) -> Optional:
    if value is None:
        return None
    return " ".join(str(value).strip().split()).upper()


def safe_import(module_name: str) -> Optional:
    try:
        return importlib.import_module(module_name)
    except Exception:
        return None


def get_attr_dict(module: Any, candidate_names: Iterable[str]) -> Dict[Any, Any]:
    if module is None:
        return {}

    for name in candidate_names:
        value = getattr(module, name, None)
        if isinstance(value, dict):
            return value

    return {}


def get_attr_set(module: Any, candidate_names: Iterable[str]) -> Set:
    if module is None:
        return set()

    for name in candidate_names:
        value = getattr(module, name, None)
        if isinstance(value, set):
            return value
        if isinstance(value, list):
            return set(value)
        if isinstance(value, tuple):
            return set(value)

    return set()


def ensure_row(rows: Dict[str, CompanyAnalyticalRow], company_source_key: str) -> CompanyAnalyticalRow:
    canonical_key = canonicalize_company_source_key(company_source_key)

    if canonical_key is None:
        raise ValueError(f"Invalid company_source_key: {company_source_key}")

    key = str(canonical_key).strip()

    if key not in rows:
        rows[key] = CompanyAnalyticalRow(
            company_source_key=key,
            display_name=key,
            normalized_name=normalize_name(key),
        )

    return rows[key]


def set_note(row: CompanyAnalyticalRow, note: str) -> None:
    if not note:
        return

    if row.notes:
        if note not in row.notes:
            row.notes = f"{row.notes} | {note}"
    else:
        row.notes = note

def is_internal_provider_identity(value: Optional[str]) -> bool:
    if value is None:
        return False

    normalized = normalize_name(value)

    internal_normalized_values = {
        normalize_name("Bodegón"),
        normalize_name("Empanadas"),
        normalize_name("EL BODEGON DE FITO"),
        normalize_name("LAS EMPANADAS DE MARIA EVA"),
    }

    return normalized in internal_normalized_values


def mark_internal_provider(row: CompanyAnalyticalRow, display_name: Optional[str] = None) -> None:
    if display_name:
        row.display_name = display_name

    row.normalized_name = normalize_name(row.display_name)
    row.is_internal_provider = True
    row.is_active_branch = False
    row.is_final_operating_branch = False
    row.is_future_rollout = False

    row.purchases_source_system = "not_applicable"
    row.inventory_source_system = "not_applicable"
    row.sales_source_system = "not_applicable"
    row.zenput_source_status = "not_applicable"

    row.rollout_type = "internal_provider"
    row.rollout_status = "not_applicable"

    row.include_in_business_views = False
    row.exclude_reason = "internal_provider"


def bool_to_int(value: bool) -> int:
    return 1 if value else 0


def parse_date(value: Any) -> Optional:
    if value is None:
        return None

    if isinstance(value, date) and not isinstance(value, datetime):
        return value

    if isinstance(value, datetime):
        return value.date()

    text = str(value).strip()
    if not text:
        return None

    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt).date()
        except ValueError:
            pass

    try:
        return datetime.fromisoformat(text).date()
    except Exception:
        return None


def canonicalize_company_source_key(value: Any) -> Optional:
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    normalized = normalize_name(text)

    aliases = {
        # Acoxpa / Costa Nera
        normalize_name("Acoxpa"): "Acoxpa",
        normalize_name("FONDA COSTA NERA"): "Acoxpa",
        normalize_name("COSTA NERA"): "Acoxpa",

        # Aeropuerto
        normalize_name("Aeropuerto"): "Aeropuerto",
        normalize_name("FONDA ARGENTINA AEROPUERTO"): "Aeropuerto",

        # Antenas
        normalize_name("Antenas"): "Antenas",
        normalize_name("FONDA ARGENTINA LAS ANTENAS"): "Antenas",
        normalize_name("LAS ANTENAS"): "Antenas",

        # Cancun
        normalize_name("Cancun"): "Cancun",
        normalize_name("Cancún"): "Cancun",
        normalize_name("FONDA ARGENTINA CANCUN"): "Cancun",
        normalize_name("FONDA ARGENTINA CANCÚN"): "Cancun",

        # CentroMyJ
        normalize_name("CentroMyJ"): "CentroMyJ",
        normalize_name("MARIO Y JULY"): "CentroMyJ",

        # Isabel La Católica
        normalize_name("Isabel La Católica"): "Isabel La Católica",
        normalize_name("Isabel La Catolica"): "Isabel La Católica",
        normalize_name("FONDA ARGENTINA"): "Isabel La Católica",
        normalize_name("FONDA ARGENTINA ISABEL"): "Isabel La Católica",

        # La Esquina Coyoacán
        normalize_name("La Esquina Coyoacán"): "La Esquina Coyoacán",
        normalize_name("La Esquina Coyoacan"): "La Esquina Coyoacán",
        normalize_name("FONDA ARGENTINA COYOACAN"): "La Esquina Coyoacán",
        normalize_name("FONDA ARGENTINA COYOACÁN"): "La Esquina Coyoacán",
        normalize_name("COYOACAN"): "La Esquina Coyoacán",
        normalize_name("COYOACÁN"): "La Esquina Coyoacán",

        # Metepec / Tollocan
        normalize_name("Metepec"): "Metepec",
        normalize_name("FONDA ARGENTINA TOLLOCAN"): "Metepec",
        normalize_name("TOLLOCAN"): "Metepec",

        # Napoles
        normalize_name("Napoles"): "Napoles",
        normalize_name("Nápoles"): "Napoles",
        normalize_name("FONDA ARGENTINA NAPOLES"): "Napoles",
        normalize_name("FONDA ARGENTINA NÁPOLES"): "Napoles",

        # Oceanía
        normalize_name("Oceanía"): "Oceanía",
        normalize_name("Oceania"): "Oceanía",
        normalize_name("FONDA ARGENTINA ENCUENTRO OCEANIA"): "Oceanía",
        normalize_name("FONDA ARGENTINA ENCUENTRO OCEANÍA"): "Oceanía",

        # Playa del Carmen
        normalize_name("Playa del Carmen"): "Playa del Carmen",
        normalize_name("FONDA ARGENTINA PLAYA"): "Playa del Carmen",

        # Puebla
        normalize_name("Puebla"): "Puebla",
        normalize_name("FONDA ARGENTINA PUEBLA"): "Puebla",

        # San Jeronimo
        normalize_name("San Jeronimo"): "San Jeronimo",
        normalize_name("San Jerónimo"): "San Jeronimo",
        normalize_name("FONDA ARGENTINA SAN JERONIMO"): "San Jeronimo",
        normalize_name("FONDA ARGENTINA SAN JERÓNIMO"): "San Jeronimo",

        # Tepeyac / MAQ
        normalize_name("Tepeyac"): "Tepeyac",
        normalize_name("FONDA ARGENTINA MAQ"): "Tepeyac",

        # Vallejo
        normalize_name("Vía Vallejo"): "Vía Vallejo",
        normalize_name("Via Vallejo"): "Vía Vallejo",
        normalize_name("FONDA ARGENTINA VALLEJO"): "Vía Vallejo",

        # Viaducto
        normalize_name("Viaducto"): "Viaducto",
        normalize_name("FONDA ARGENTINA VIADUCTO"): "Viaducto",

        # Taquerías
        normalize_name("Versalles"): "Versalles",
        normalize_name("Taqueria Exhibimex"): "Versalles",
        normalize_name("Taquería Exhibimex"): "Versalles",

        normalize_name("Taquería parroquia"): "Taquería parroquia",
        normalize_name("Taqueria Parroquia"): "Taquería parroquia",
        normalize_name("Taquería Parroquia"): "Taquería parroquia",

        normalize_name("Taquería Viaducto"): "Taquería Viaducto",
        normalize_name("Taqueria Viaducto"): "Taquería Viaducto",

        # Zenput-only
        normalize_name("León"): "León",
        normalize_name("Leon"): "León",
        normalize_name("FONDA ARGENTINA LEON"): "León",
        normalize_name("FONDA ARGENTINA LEÓN"): "León",

        normalize_name("Lindavista"): "Lindavista",
        normalize_name("FONDA ARGENTINA LINDAVISTA"): "Lindavista",

        normalize_name("Perisur"): "Perisur",
        normalize_name("FONDA ARGENTINA PERISUR"): "Perisur",

        # Internal providers
        normalize_name("Bodegón"): "Bodegón",
        normalize_name("Bodegon"): "Bodegón",
        normalize_name("EL BODEGON DE FITO"): "Bodegón",

        normalize_name("Empanadas"): "Empanadas",
        normalize_name("LAS EMPANADAS DE MARIA EVA"): "Empanadas",
    }

    return aliases.get(normalized, text)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

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


def get_table_columns(conn, table_name: str) -> Set:
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


# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

def create_table_if_missing(conn) -> None:
    ddl = f"""
    CREATE TABLE IF NOT EXISTS {ANALYTICAL_TABLE} (
        company_analytical_key BIGINT AUTO_INCREMENT PRIMARY KEY,

        company_source_key VARCHAR(255) NOT NULL,
        display_name VARCHAR(255) NOT NULL,
        normalized_name VARCHAR(255) NULL,
        brand_group VARCHAR(255) NULL,

        is_active_branch BOOLEAN NOT NULL DEFAULT FALSE,
        is_internal_provider BOOLEAN NOT NULL DEFAULT FALSE,
        is_final_operating_branch BOOLEAN NOT NULL DEFAULT FALSE,
        is_future_rollout BOOLEAN NOT NULL DEFAULT FALSE,

        is_wansoft_company BOOLEAN NOT NULL DEFAULT FALSE,
        is_odoo_company BOOLEAN NOT NULL DEFAULT FALSE,
        is_zenput_location BOOLEAN NOT NULL DEFAULT FALSE,
        is_zenput_only BOOLEAN NOT NULL DEFAULT FALSE,

        purchases_source_system VARCHAR(100) NOT NULL DEFAULT 'none',
        inventory_source_system VARCHAR(100) NOT NULL DEFAULT 'none',
        sales_source_system VARCHAR(100) NOT NULL DEFAULT 'none',
        zenput_source_status VARCHAR(100) NOT NULL DEFAULT 'not_detected',

        rollout_type VARCHAR(100) NULL,
        rollout_status VARCHAR(100) NULL,
        operational_start_date DATE NULL,

        include_in_business_views BOOLEAN NOT NULL DEFAULT TRUE,
        exclude_reason VARCHAR(255) NULL,

        notes TEXT NULL,

        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

        UNIQUE KEY uq_dim_company_analytical_source_key (company_source_key),
        KEY idx_dim_company_analytical_display_name (display_name),
        KEY idx_dim_company_analytical_rollout (rollout_type, rollout_status),
        KEY idx_dim_company_analytical_sources (
            purchases_source_system,
            inventory_source_system,
            sales_source_system,
            zenput_source_status
        )
    )
    """
    cursor = conn.cursor()
    cursor.execute(ddl)
    conn.commit()
    cursor.close()


# ---------------------------------------------------------------------------
# Source extraction from project configuration
# ---------------------------------------------------------------------------

def collect_from_companies_config(rows: Dict[str, CompanyAnalyticalRow]) -> None:
    companies = safe_import("core.config.companies")

    company_source = get_attr_dict(
        companies,
        [
            "COMPANY_SOURCE",
        ],
    )

    wansoft_subsidiary_source_key = get_attr_dict(
        companies,
        [
            "WANSOFT_SUBSIDIARY_SOURCE_KEY",
        ],
    )

    odoo_company_mappings = get_attr_dict(
        companies,
        [
            "ODOO_COMPANY_SOURCE_KEY",
            "ODOO_COMPANY_SOURCE_MAP",
            "ODOO_COMPANY_NAME_SOURCE_KEY",
            "ODOO_COMPANY_TO_SOURCE_KEY",
            "ODOO_COMPANY_MAPPING",
        ],
    )

    # COMPANY_SOURCE: domain source governance for Purchases / Inventory.
    for company_key, source_system in company_source.items():
        row = ensure_row(rows, str(company_key))

        source = str(source_system).strip().lower()

        if source == "odoo":
            row.is_odoo_company = True
            row.purchases_source_system = "odoo"
            row.inventory_source_system = "odoo"
            row.is_active_branch = True
            row.is_final_operating_branch = True
        elif source == "wansoft":
            row.is_wansoft_company = True
            row.purchases_source_system = "wansoft"
            row.inventory_source_system = "wansoft"
            row.sales_source_system = "wansoft"
            row.is_active_branch = True
            row.is_final_operating_branch = True
        else:
            set_note(row, f"Unknown COMPANY_SOURCE value: {source_system}")

    # Wansoft subsidiary mapping.
    for _subsidiary_id, company_key in wansoft_subsidiary_source_key.items():
        row = ensure_row(rows, str(company_key))
        row.is_wansoft_company = True

        if row.sales_source_system == "none":
            row.sales_source_system = "wansoft"

    # Odoo company mappings may appear in either direction depending on config shape.
    # Register both sides through canonicalization so raw Odoo names do not become
    # separate analytical companies.
    for left_value, right_value in odoo_company_mappings.items():
        for candidate in (left_value, right_value):
            canonical_key = canonicalize_company_source_key(candidate)

            if canonical_key:
                row = ensure_row(rows, canonical_key)
                row.is_odoo_company = True

    # Known migrated branches.
    for company_key in MIGRATED_FROM_WANSOFT_COMPANIES:
        row = ensure_row(rows, company_key)
        row.is_wansoft_company = True
        row.is_odoo_company = True
        row.is_active_branch = True
        row.is_final_operating_branch = True
        row.rollout_type = "migrated_from_wansoft"
        row.rollout_status = "active"
        row.purchases_source_system = "mixed_by_operational_start_date"

        # Inventory may or may not preserve Wansoft history the same way Purchases does.
        # Use mixed_by_operational_start_date for now if Odoo and Wansoft are both present.
        row.inventory_source_system = "mixed_by_operational_start_date"
        row.sales_source_system = "wansoft"

    # New Odoo branches.
    for company_key in NEW_ODOO_BRANCH_COMPANIES:
        row = ensure_row(rows, company_key)
        row.is_odoo_company = True

        if company_key in KNOWN_FUTURE_ROLLOUTS:
            row.is_future_rollout = True
            row.rollout_status = "future"
            row.purchases_source_system = "pending"
            row.inventory_source_system = "pending"
            row.sales_source_system = "pending"
            row.is_active_branch = False
            row.is_final_operating_branch = False
        else:
            row.is_active_branch = True
            row.is_final_operating_branch = True
            row.rollout_status = "active"
            row.purchases_source_system = "odoo"
            row.inventory_source_system = "odoo"
            row.sales_source_system = "pending"

        row.rollout_type = "new_odoo_branch"


def collect_from_zenput_config(rows: Dict[str, CompanyAnalyticalRow]) -> None:
    zenput = safe_import("core.config.zenput")

    location_mapping = get_attr_dict(
        zenput,
        [
            "ZENPUT_LOCATION_SOURCE_KEY",
        ],
    )

    zenput_only = get_attr_set(
        zenput,
        [
            "ZENPUT_ONLY_LOCATIONS",
        ],
    )

    company_wansoft_id = get_attr_dict(
        zenput,
        [
            "ZENPUT_COMPANY_WANSOFT_ID",
        ],
    )

    for _location_name, company_key in location_mapping.items():
        row = ensure_row(rows, str(company_key))
        row.is_zenput_location = True

        if str(company_key) in zenput_only:
            row.is_zenput_only = True
            row.zenput_source_status = "zenput_only"
            row.rollout_type = row.rollout_type or "zenput_only"
            row.rollout_status = row.rollout_status or "future"
            row.is_future_rollout = True
        else:
            row.zenput_source_status = "mapped"

    # Apply explicit Zenput-only set even if the location mapping changes.
    for company_key in zenput_only:
        row = ensure_row(rows, str(company_key))
        row.is_zenput_location = True
        row.is_zenput_only = True
        row.zenput_source_status = "zenput_only"
        row.rollout_type = row.rollout_type or "zenput_only"
        row.rollout_status = row.rollout_status or "future"
        row.is_future_rollout = True

    # If Zenput metadata knows Wansoft IDs, mark presence.
    for company_key, wansoft_id in company_wansoft_id.items():
        if wansoft_id:
            row = ensure_row(rows, str(company_key))
            row.is_wansoft_company = True

    # Puebla rule.
    if "Puebla" in rows:
        puebla = rows["Puebla"]
        puebla.is_zenput_location = True
        puebla.is_zenput_only = False
        puebla.zenput_source_status = "mapped"
        puebla.rollout_type = puebla.rollout_type or "new_odoo_branch"
        puebla.rollout_status = puebla.rollout_status or "future"
        puebla.is_future_rollout = True
        set_note(puebla, "Appears in Zenput as Fonda Argentina Puebla. Not Zenput-only.")


def collect_internal_providers(rows: Dict[str, CompanyAnalyticalRow]) -> None:
    # Only canonical internal provider keys should exist in dim_company_analytical.
    # Legal names are stored as display_name, not as separate company_source_key rows.
    for company_key, display_name in INTERNAL_PROVIDER_KEYS.items():
        row = ensure_row(rows, company_key)
        mark_internal_provider(row, display_name=display_name)


def collect_rollout_expectations(rows: Dict[str, CompanyAnalyticalRow]) -> None:
    module = safe_import("scripts.validate_purchases_canonical_layer")
    expectations = get_attr_dict(
        module,
        [
            "ROLLOUT_COMPANY_EXPECTATIONS",
        ],
    )

    for company_key, expectation in expectations.items():
        row = ensure_row(rows, str(company_key))

        if isinstance(expectation, dict):
            rollout_type = expectation.get("rollout_type") or expectation.get("type")
            active = expectation.get("active")
            operational_start_date = expectation.get("operational_start_date")

            if rollout_type:
                row.rollout_type = str(rollout_type)

            if active is True:
                row.rollout_status = "active"
                row.is_active_branch = True
                row.is_final_operating_branch = True
            elif active is False:
                row.rollout_status = "future"
                row.is_future_rollout = True

            parsed_date = parse_date(operational_start_date)
            if parsed_date:
                row.operational_start_date = parsed_date

        else:
            set_note(row, "Rollout expectation found but shape was not a dict.")


def collect_migration_policy_from_db(conn, rows: Dict[str, CompanyAnalyticalRow]) -> None:
    table_name = "odoo_company_migration_policy"

    if not table_exists(conn, table_name):
        return

    columns = get_table_columns(conn, table_name)

    company_col_candidates = [
        "company_source_key",
        "source_key",
        "company_key",
        "company",
        "company_name",
        "branch_name",
        "sucursal",
        "odoo_company_name",
        "final_company_name",
        "source_company_key",
    ]

    date_col_candidates = [
        "operational_start_date",
        "odoo_operational_start_date",
        "odoo_start_date",
        "migration_date",
        "go_live_date",
        "start_date",
        "effective_date",
        "valid_from",
    ]

    company_col = next((c for c in company_col_candidates if c in columns), None)
    date_col = next((c for c in date_col_candidates if c in columns), None)

    if company_col is None:
        return

    select_fields = [company_col]

    optional_fields = [
        "rollout_type",
        "rollout_status",
        "active",
        "is_active",
    ]

    if date_col:
        select_fields.append(date_col)

    for field in optional_fields:
        if field in columns:
            select_fields.append(field)

    query = f"""
        SELECT {", ".join(select_fields)}
        FROM {table_name}
    """

    for db_row in fetch_all_dict(conn, query):
        raw_company_key = db_row.get(company_col)
        company_key = canonicalize_company_source_key(raw_company_key)

        if not company_key:
            continue

        row = ensure_row(rows, str(company_key))

        rollout_type = db_row.get("rollout_type")
        rollout_status = db_row.get("rollout_status")
        active = db_row.get("active", db_row.get("is_active"))

        if rollout_type:
            row.rollout_type = str(rollout_type)

        if rollout_status:
            row.rollout_status = str(rollout_status)
        elif active is not None:
            row.rollout_status = "active" if bool(active) else "future"

        parsed_date = parse_date(db_row.get(date_col)) if date_col else None

        if parsed_date:
            row.operational_start_date = parsed_date

        if row.company_source_key in MIGRATED_FROM_WANSOFT_COMPANIES:
            row.rollout_type = "migrated_from_wansoft"
            row.rollout_status = row.rollout_status or "active"
            row.is_wansoft_company = True
            row.is_odoo_company = True
            row.is_active_branch = True
            row.is_final_operating_branch = True
            row.purchases_source_system = "mixed_by_operational_start_date"
            row.inventory_source_system = "mixed_by_operational_start_date"
            row.sales_source_system = "wansoft"

        if row.company_source_key in NEW_ODOO_BRANCH_COMPANIES:
            row.rollout_type = "new_odoo_branch"
            row.is_odoo_company = True

            if row.company_source_key in KNOWN_FUTURE_ROLLOUTS:
                row.rollout_status = row.rollout_status or "future"
                row.is_future_rollout = True
                row.purchases_source_system = "pending"
                row.inventory_source_system = "pending"
                row.sales_source_system = "pending"
            else:
                row.rollout_status = row.rollout_status or "active"
                row.is_active_branch = True
                row.is_final_operating_branch = True
                row.purchases_source_system = "odoo"
                row.inventory_source_system = "odoo"
                row.sales_source_system = "pending"


# ---------------------------------------------------------------------------
# Final normalization
# ---------------------------------------------------------------------------

def finalize_rows(rows: Dict[str, CompanyAnalyticalRow]) -> None:
    for row in rows.values():
        row.normalized_name = row.normalized_name or normalize_name(row.display_name)

        # Baseline brand group.
        if row.brand_group is None:
            if row.company_source_key in {"Taquería parroquia", "Taquería Viaducto", "Versalles"}:
                row.brand_group = "Taqueria"
            elif row.is_internal_provider:
                row.brand_group = "Internal Provider"
            else:
                row.brand_group = "Fonda Argentina"

        # Sales default.
        if row.sales_source_system == "none" and row.is_wansoft_company:
            row.sales_source_system = "wansoft"

        # Future rollouts.
        if row.company_source_key in KNOWN_FUTURE_ROLLOUTS:
            row.is_future_rollout = True
            row.rollout_status = row.rollout_status or "future"

        # Zenput-only companies should not be marked as final operating branches yet.
        if row.is_zenput_only:
            row.is_zenput_location = True
            row.zenput_source_status = "zenput_only"
            row.purchases_source_system = "none"
            row.inventory_source_system = "none"
            row.sales_source_system = "none"
            row.is_final_operating_branch = False
            row.is_active_branch = False
            row.is_future_rollout = True

        # Puebla explicit rule.
        if row.company_source_key == "Puebla":
            row.is_zenput_only = False
            if row.is_zenput_location:
                row.zenput_source_status = "mapped"

        # Internal providers.
        if (
            row.is_internal_provider
            or is_internal_provider_identity(row.company_source_key)
            or is_internal_provider_identity(row.display_name)
        ):
            mark_internal_provider(row, display_name=row.display_name)

        # Validate source values defensively.
        if row.purchases_source_system not in VALID_PURCHASES_SOURCE_SYSTEM:
            set_note(row, f"Invalid purchases_source_system normalized to pending: {row.purchases_source_system}")
            row.purchases_source_system = "pending"

        if row.inventory_source_system not in VALID_INVENTORY_SOURCE_SYSTEM:
            set_note(row, f"Invalid inventory_source_system normalized to pending: {row.inventory_source_system}")
            row.inventory_source_system = "pending"

        if row.sales_source_system not in VALID_SALES_SOURCE_SYSTEM:
            set_note(row, f"Invalid sales_source_system normalized to pending: {row.sales_source_system}")
            row.sales_source_system = "pending"

        if row.zenput_source_status not in VALID_ZENPUT_SOURCE_STATUS:
            set_note(row, f"Invalid zenput_source_status normalized to pending: {row.zenput_source_status}")
            row.zenput_source_status = "pending"


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def upsert_rows(conn, rows: Dict[str, CompanyAnalyticalRow]) -> None:
    sql = f"""
    INSERT INTO {ANALYTICAL_TABLE} (
        company_source_key,
        display_name,
        normalized_name,
        brand_group,
        is_active_branch,
        is_internal_provider,
        is_final_operating_branch,
        is_future_rollout,
        is_wansoft_company,
        is_odoo_company,
        is_zenput_location,
        is_zenput_only,
        purchases_source_system,
        inventory_source_system,
        sales_source_system,
        zenput_source_status,
        rollout_type,
        rollout_status,
        operational_start_date,
        include_in_business_views,
        exclude_reason,
        notes
    )
    VALUES (
        %(company_source_key)s,
        %(display_name)s,
        %(normalized_name)s,
        %(brand_group)s,
        %(is_active_branch)s,
        %(is_internal_provider)s,
        %(is_final_operating_branch)s,
        %(is_future_rollout)s,
        %(is_wansoft_company)s,
        %(is_odoo_company)s,
        %(is_zenput_location)s,
        %(is_zenput_only)s,
        %(purchases_source_system)s,
        %(inventory_source_system)s,
        %(sales_source_system)s,
        %(zenput_source_status)s,
        %(rollout_type)s,
        %(rollout_status)s,
        %(operational_start_date)s,
        %(include_in_business_views)s,
        %(exclude_reason)s,
        %(notes)s
    )
    ON DUPLICATE KEY UPDATE
        display_name = VALUES(display_name),
        normalized_name = VALUES(normalized_name),
        brand_group = VALUES(brand_group),
        is_active_branch = VALUES(is_active_branch),
        is_internal_provider = VALUES(is_internal_provider),
        is_final_operating_branch = VALUES(is_final_operating_branch),
        is_future_rollout = VALUES(is_future_rollout),
        is_wansoft_company = VALUES(is_wansoft_company),
        is_odoo_company = VALUES(is_odoo_company),
        is_zenput_location = VALUES(is_zenput_location),
        is_zenput_only = VALUES(is_zenput_only),
        purchases_source_system = VALUES(purchases_source_system),
        inventory_source_system = VALUES(inventory_source_system),
        sales_source_system = VALUES(sales_source_system),
        zenput_source_status = VALUES(zenput_source_status),
        rollout_type = VALUES(rollout_type),
        rollout_status = VALUES(rollout_status),
        operational_start_date = VALUES(operational_start_date),
        include_in_business_views = VALUES(include_in_business_views),
        exclude_reason = VALUES(exclude_reason),
        notes = VALUES(notes),
        updated_at = CURRENT_TIMESTAMP
    """

    payload = []

    for row in rows.values():
        item = asdict(row)
        item["is_active_branch"] = bool_to_int(row.is_active_branch)
        item["is_internal_provider"] = bool_to_int(row.is_internal_provider)
        item["is_final_operating_branch"] = bool_to_int(row.is_final_operating_branch)
        item["is_future_rollout"] = bool_to_int(row.is_future_rollout)
        item["is_wansoft_company"] = bool_to_int(row.is_wansoft_company)
        item["is_odoo_company"] = bool_to_int(row.is_odoo_company)
        item["is_zenput_location"] = bool_to_int(row.is_zenput_location)
        item["is_zenput_only"] = bool_to_int(row.is_zenput_only)
        item["include_in_business_views"] = bool_to_int(row.include_in_business_views)
        payload.append(item)

    cursor = conn.cursor()

    # Section 17 initial implementation uses exact rebuild semantics.
    # This prevents stale source aliases from remaining as separate analytical rows.
    # Future versions may switch to soft-deactivation once analytics facts depend on this dimension.
    cursor.execute(f"DELETE FROM {ANALYTICAL_TABLE}")

    cursor.executemany(sql, payload)
    conn.commit()
    cursor.close()


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build_rows(conn) -> Dict[str, CompanyAnalyticalRow]:
    rows: Dict[str, CompanyAnalyticalRow] = {}

    collect_from_companies_config(rows)
    collect_from_zenput_config(rows)
    collect_internal_providers(rows)
    collect_rollout_expectations(rows)
    collect_migration_policy_from_db(conn, rows)
    finalize_rows(rows)

    return rows


def print_summary(rows: Dict[str, CompanyAnalyticalRow]) -> None:
    total = len(rows)

    active = sum(1 for r in rows.values() if r.is_active_branch)
    internal = sum(1 for r in rows.values() if r.is_internal_provider)
    zenput_locations = sum(1 for r in rows.values() if r.is_zenput_location)
    zenput_only = sum(1 for r in rows.values() if r.is_zenput_only)
    future = sum(1 for r in rows.values() if r.is_future_rollout)

    print("=====================================================")
    print("DIM COMPANY ANALYTICAL BUILD SUMMARY")
    print("=====================================================")
    print(f"table: {ANALYTICAL_TABLE}")
    print(f"total_rows_prepared: {total}")
    print(f"active_branches: {active}")
    print(f"internal_providers: {internal}")
    print(f"zenput_locations: {zenput_locations}")
    print(f"zenput_only: {zenput_only}")
    print(f"future_rollouts: {future}")
    print("=====================================================")


def main() -> int:
    print("=====================================================")
    print("DIM COMPANY ANALYTICAL BUILD START")
    print("=====================================================")

    conn = get_db_connection()

    try:
        create_table_if_missing(conn)

        rows = build_rows(conn)
        upsert_rows(conn, rows)

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