"""
Zenput company and location configuration.

Purpose:
    Centralize Zenput location mapping and avoid duplicating branch lists
    inside legacy Zenput ETL scripts.

Zenput is an operational source independent from the Wansoft/Odoo source
selection used by Purchases and Inventory.

Important:
    - Do not use COMPANY_SOURCE as the inclusion filter for Zenput.
    - Do not use is_wansoft_company as the inclusion filter for Zenput.
    - Zenput locations should map from Zenput location_name to the canonical
      company_source_key used by the analytical layer.
    - Some Zenput locations do not have Wansoft as an operational source.
      These are still valid Zenput-only operational locations.
"""

from __future__ import annotations

from typing import Dict, Optional, Set


# =====================================================
# ZENPUT LOCATION TO CANONICAL COMPANY SOURCE KEY
# =====================================================
#
# Source field:
#     submissions.location_name
#
# Target:
#     canonical company_source_key used by the analytical layer.
#
# Notes:
#     - Zenput location names do not always match Wansoft or Odoo names.
#     - This map should be used instead of is_wansoft_company.
#     - WansoftID can be retained as auxiliary metadata, but should not
#       decide whether Zenput extracts or includes a location.
# =====================================================

ZENPUT_LOCATION_SOURCE_KEY: Dict[str, str] = {
    "Fonda Argentina Acoxpa": "Acoxpa",
    "Fonda Argentina Aeropuerto": "Aeropuerto",
    "Fonda Argentina Antenas": "Antenas",
    "Fonda Argentina Cancun": "Cancun",
    "Fonda Argentina Coyoacán": "La Esquina Coyoacán",
    "Fonda Argentina Isabel": "Isabel La Católica",
    "Fonda Argentina León": "León",
    "Fonda Argentina Lindavista": "Lindavista",
    "Fonda Argentina Napoles": "Napoles",
    "Fonda Argentina Oceania": "Oceanía",
    "Fonda Argentina Perisur": "Perisur",
    "Fonda Argentina Playa": "Playa del Carmen",
    "Fonda Argentina San Jerónimo": "San Jeronimo",
    "Fonda Argentina San Jeronimo": "San Jeronimo",
    "Fonda Argentina Tepeyac": "Tepeyac",
    "Fonda Argentina Tollocan": "Metepec",
    "Fonda Argentina Vallejo": "Vía Vallejo",
    "Fonda Argentina Viaducto": "Viaducto",
    "Taqueria Exhibimex": "Versalles",
    "Taqueria Parroquia": "Taquería parroquia",
    "Taqueria Viaducto": "Taquería Viaducto",
}


# =====================================================
# ZENPUT-ONLY LOCATIONS
# =====================================================
#
# These locations exist in Zenput operational data but do not have Wansoft
# as an operational source.
#
# Purchases and Inventory pipelines may skip them because those domains
# are governed by Wansoft/Odoo operational source rules.
#
# Zenput should still preserve them for Zenput operational reporting.
# =====================================================

ZENPUT_ONLY_LOCATIONS: Set[str] = {
    "León",
    "Lindavista",
    "Perisur",
}


# =====================================================
# CONFIRMED SPECIAL MAPPINGS
# =====================================================
#
# These mappings were explicitly confirmed during the Zenput assessment.
# =====================================================

ZENPUT_CONFIRMED_SPECIAL_MAPPINGS: Dict[str, str] = {
    "Fonda Argentina Coyoacán": "La Esquina Coyoacán",
    "Fonda Argentina Tollocan": "Metepec",
    "Taqueria Exhibimex": "Versalles",
}


# =====================================================
# OPTIONAL WANSOFT ID METADATA
# =====================================================
#
# WansoftID is kept as auxiliary metadata where available.
#
# Important:
#     WansoftID should not be used as the only inclusion rule for Zenput.
#
# Zenput-only locations may have no real WansoftID.
# =====================================================

ZENPUT_COMPANY_WANSOFT_ID: Dict[str, Optional[str]] = {
    "Acoxpa": "5320",
    "Aeropuerto": "4959",
    "Isabel La Católica": "4958",
    "Antenas": "4960",
    "Taquería parroquia": "5321",
    "Vía Vallejo": "5318",
    "Taquería Viaducto": "4962",
    "San Jeronimo": "5319",
    "Tepeyac": "6560",
    "Playa del Carmen": "6174",
    "Oceanía": "5943",
    "Cancun": "6175",
    "Napoles": "4433",
    "Metepec": "4752",
    "Versalles": "5396",
    "Viaducto": "4961",
    "La Esquina Coyoacán": "12057",
    "CentroMyJ": "12802",
    "Puebla": "12806",

    # Zenput-only operational locations.
    "León": None,
    "Lindavista": None,
    "Perisur": None,
}


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def normalize_zenput_location_name(location_name: Optional[str]) -> Optional:
    """
    Normalizes a Zenput location name for lookup.

    This function intentionally performs only conservative normalization:
        - trims surrounding whitespace
        - preserves accents
        - preserves original casing except whitespace cleanup

    More aggressive normalization should be added only if real Zenput values
    require it.
    """

    if location_name is None:
        return None

    normalized = str(location_name).strip()

    if not normalized:
        return None

    return normalized


def get_zenput_company_source_key(location_name: Optional[str]) -> Optional:
    """
    Returns the canonical company_source_key for a Zenput location_name.

    Example:
        Fonda Argentina Coyoacán -> La Esquina Coyoacán
        Fonda Argentina Tollocan -> Metepec
        Taqueria Exhibimex -> Versalles

    Returns:
        company_source_key when mapped.
        None when the location is unknown or blank.
    """

    normalized_location = normalize_zenput_location_name(location_name)

    if normalized_location is None:
        return None

    return ZENPUT_LOCATION_SOURCE_KEY.get(normalized_location)


def is_known_zenput_location(location_name: Optional[str]) -> bool:
    """
    Returns True when a Zenput location_name is configured.
    """

    return get_zenput_company_source_key(location_name) is not None


def is_zenput_only_company_source_key(company_source_key: Optional[str]) -> bool:
    """
    Returns True when the canonical company_source_key is a Zenput-only location.

    Zenput-only locations are valid for Zenput operational reporting but are not
    expected to participate in Purchases or Inventory Wansoft/Odoo pipelines.
    """

    if company_source_key is None:
        return False

    return company_source_key in ZENPUT_ONLY_LOCATIONS


def is_zenput_only_location(location_name: Optional[str]) -> bool:
    """
    Returns True when a Zenput location_name maps to a Zenput-only location.
    """

    company_source_key = get_zenput_company_source_key(location_name)

    return is_zenput_only_company_source_key(company_source_key)


def get_zenput_wansoft_id_from_location(
    location_name: Optional[str],
) -> Optional:
    """
    Returns WansoftID metadata for a Zenput location when available.

    Returns:
        WansoftID as string when available.
        None for Zenput-only locations or unknown locations.
    """

    company_source_key = get_zenput_company_source_key(location_name)

    if company_source_key is None:
        return None

    return ZENPUT_COMPANY_WANSOFT_ID.get(company_source_key)


def get_unmapped_zenput_locations(location_names: Set[str]) -> Set:
    """
    Returns location names that are not configured in ZENPUT_LOCATION_SOURCE_KEY.

    Useful for validators and diagnostics.
    """

    unmapped = set()

    for location_name in location_names:
        normalized_location = normalize_zenput_location_name(location_name)

        if normalized_location is None:
            continue

        if normalized_location not in ZENPUT_LOCATION_SOURCE_KEY:
            unmapped.add(normalized_location)

    return unmapped


def get_all_configured_zenput_locations() -> Set:
    """
    Returns all configured Zenput location_name values.
    """

    return set(ZENPUT_LOCATION_SOURCE_KEY.keys())


def get_all_zenput_company_source_keys() -> Set:
    """
    Returns all canonical company_source_key values mapped from Zenput locations.
    """

    return set(ZENPUT_LOCATION_SOURCE_KEY.values())