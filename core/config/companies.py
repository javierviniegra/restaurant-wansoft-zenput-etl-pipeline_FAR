"""
Company Data Source Configuration
"""


import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)


# Lista base (la que ya tienes)
CUENTAS_SUCURSALES = [
    ("5320", "Acoxpa", os.getenv("WANSOFT_PWD_5320")),
    ("4959", "Aeropuerto", os.getenv("WANSOFT_PWD_4959")),
    ("4958", "Isabel La Católica", os.getenv("WANSOFT_PWD_4958")),
    ("4960", "Antenas", os.getenv("WANSOFT_PWD_4960")),
    ("5321", "Taquería parroquia", os.getenv("WANSOFT_PWD_5321")),
    ("5318", "Vía Vallejo", os.getenv("WANSOFT_PWD_5318")),
    ("4961", "Viaducto", os.getenv("WANSOFT_PWD_4961")),
    ("4962", "Taquería Viaducto", os.getenv("WANSOFT_PWD_4962")),
    ("5319", "San Jeronimo", os.getenv("WANSOFT_PWD_5319")),
    ("6560", "Tepeyac", os.getenv("WANSOFT_PWD_6560")),
    ("6174", "Playa del Carmen", os.getenv("WANSOFT_PWD_6174")),
    ("5943", "Oceanía", os.getenv("WANSOFT_PWD_5943")),
    ("6175", "Cancun", os.getenv("WANSOFT_PWD_6175")),
    ("4433", "Napoles", os.getenv("WANSOFT_PWD_4433")),
    ("4752", "Metepec", os.getenv("WANSOFT_PWD_4752")),
    ("5396", "Versalles", os.getenv("WANSOFT_PWD_5396")),
    ("12057", "La Esquina Coyoacán", os.getenv("WANSOFT_PWD_12057")),
    ("12802", "CentroMyJ", os.getenv("WANSOFT_PWD_12802")),
    ("12806", "Puebla", os.getenv("WANSOFT_PWD_12806"))
]

# =====================================================
# WANSOFT SUBSIDIARY TO OPERATIONAL SOURCE KEY
# =====================================================
# Derived from CUENTAS_SUCURSALES.
#
# Maps Wansoft subsidiary identifiers to COMPANY_SOURCE keys.
#
# Example:
# "4960" -> "Antenas"
# =====================================================

WANSOFT_SUBSIDIARY_SOURCE_KEY = {
    str(subsidiary_id): company_name
    for subsidiary_id, company_name, _password in CUENTAS_SUCURSALES
}

# 🔥 CONFIGURACIÓN DE FUENTE POR EMPRESA
COMPANY_SOURCE = {
    "Acoxpa": "wansoft",
    "Aeropuerto": "wansoft",
    "Isabel La Católica": "wansoft",
    "Antenas": "odoo",
    "Taquería parroquia": "wansoft",
    "Vía Vallejo": "wansoft",
    "Viaducto": "wansoft",
    "Taquería Viaducto": "wansoft",
    "San Jeronimo": "wansoft",
    "Tepeyac": "wansoft",
    "Playa del Carmen": "wansoft",
    "Oceanía": "wansoft",
    "Cancun": "wansoft",
    "Napoles": "wansoft",
    "Metepec": "wansoft",
    "Versalles": "wansoft",
    "La Esquina Coyoacán": "wansoft",
    "CentroMyJ": "wansoft",
    "Puebla": "wansoft"
}

# =====================================================
# COMPANY SOURCE GOVERNANCE
# =====================================================
# This configuration defines the official source system
# by operational company/sucursal.
#
# Rules:
# - sales always remain Wansoft
# - purchases follow COMPANY_SOURCE
# - inventory follows COMPANY_SOURCE
# - operational_start_date applies only when source = odoo
# =====================================================


# Domains controlled by COMPANY_SOURCE
COMPANY_SOURCE_CONTROLLED_DOMAINS = {
    "purchases",
    "inventory",
}


# Domains that must always use Wansoft
ALWAYS_WANSOFT_DOMAINS = {
    "sales",
}



# =====================================================
# ODOO COMPANY NAME TO OPERATIONAL SOURCE KEY
# =====================================================
# Maps Odoo company names to the operational keys used in COMPANY_SOURCE.
#
# Important:
# - Bodegón and Empanadas may exist as Odoo companies because they are part
#   of the intercompany/provider flow.
# - For Grupo Fonda Argentina final BI tables, they are treated as suppliers,
#   not as operating restaurant branches.
# =====================================================

ODOO_COMPANY_SOURCE_KEY = {
    "FONDA ARGENTINA LAS ANTENAS": "Antenas",
    "FONDA ARGENTINA ENCUENTRO OCEANIA": "Oceanía",
    "FONDA ARGENTINA SAN JERONIMO": "San Jeronimo",
    "FONDA ARGENTINA PUEBLA": "Puebla",
    "FONDA ARGENTINA COYOACAN": "La Esquina Coyoacán",
    "FONDA ARGENTINA MAQ": "Tepeyac",
    "FONDA COSTA NERA": "Acoxpa",
    "FONDA ARGENTINA": "Isabel La Católica",
    "MARIO Y JULY": "CentroMyJ",
}


# =====================================================
# INTERNAL PROVIDER COMPANIES
# =====================================================
# These companies may exist in Odoo for intercompany operations,
# purchases, sales orders, receipts, or supplier flows.
#
# They should NOT be treated as final operating branches for
# Grupo Fonda Argentina BI canonical tables.
# =====================================================

ODOO_INTERNAL_PROVIDER_COMPANIES = {
    "EL BODEGON DE FITO",
    "LAS EMPANADAS DE MARIA EVA",
}



def normalize_company_name(value):
    """
    Normalizes company names for source-system lookup.
    """
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    return text


def is_internal_provider_company(company_name):
    """
    Returns True when an Odoo company should be treated as an internal provider
    instead of an operating branch for final BI tables.
    """
    normalized_name = normalize_company_name(company_name)

    if normalized_name is None:
        return False

    return normalized_name in ODOO_INTERNAL_PROVIDER_COMPANIES


def get_company_source_key(company_name):
    """
    Resolves the operational COMPANY_SOURCE key from an Odoo/Wansoft company name.

    Examples:
    FONDA ARGENTINA LAS ANTENAS -> Antenas
    FONDA ARGENTINA MAQ -> Tepeyac
    FONDA COSTA NERA -> Acoxpa

    Internal provider companies return None because they should not be treated
    as operating branches in final Grupo Fonda Argentina BI tables.
    """
    normalized_name = normalize_company_name(company_name)

    if normalized_name is None:
        return None

    if is_internal_provider_company(normalized_name):
        return None

    if normalized_name in ODOO_COMPANY_SOURCE_KEY:
        return ODOO_COMPANY_SOURCE_KEY[normalized_name]

    return normalized_name


def get_company_source(company_name, default="wansoft"):
    """
    Returns the configured source system for a company.

    Returns:
    - "wansoft"
    - "odoo"
    - "internal_provider"
    """
    if is_internal_provider_company(company_name):
        return "internal_provider"

    source_key = get_company_source_key(company_name)

    if source_key is None:
        return default

    return COMPANY_SOURCE.get(source_key, default)


def get_domain_company_source(company_name, domain, default="wansoft"):
    """
    Returns the official source system for a company and domain.

    Rules:
    - internal providers return internal_provider for purchases/inventory
    - sales always returns wansoft for operating companies
    - purchases and inventory use COMPANY_SOURCE
    - unknown domains default to Wansoft unless explicitly handled
    """
    domain_normalized = str(domain).strip().lower()

    if is_internal_provider_company(company_name):
        if domain_normalized in COMPANY_SOURCE_CONTROLLED_DOMAINS:
            return "internal_provider"

        # Sales always remains Wansoft as source system,
        # but final inclusion is controlled separately.
        if domain_normalized in ALWAYS_WANSOFT_DOMAINS:
            return "wansoft"

    if domain_normalized in ALWAYS_WANSOFT_DOMAINS:
        return "wansoft"

    if domain_normalized in COMPANY_SOURCE_CONTROLLED_DOMAINS:
        return get_company_source(company_name, default=default)

    return default


def is_company_odoo_source(company_name, domain):
    """
    Returns True only if the company is configured as Odoo source
    for the requested domain.
    """
    return get_domain_company_source(company_name, domain) == "odoo"


def is_company_wansoft_source(company_name, domain):
    """
    Returns True if the company is configured as Wansoft source
    for the requested domain.
    """
    return get_domain_company_source(company_name, domain) == "wansoft"


def is_company_internal_provider(company_name, domain=None):
    """
    Returns True when the company is an internal provider.

    The domain parameter is optional because provider classification is
    company-level, not domain-level.
    """
    return is_internal_provider_company(company_name)


def should_include_company_in_final_domain(company_name, domain):
    """
    Determines whether a company should be included as an operating company
    in final canonical BI tables for a given domain.

    Internal providers are excluded from final branch-level BI facts.
    """
    if is_internal_provider_company(company_name):
        return False

    return True