from core.config.companies import COMPANY_SOURCE


def is_wansoft_company(nombre_corto: str) -> bool:
    return COMPANY_SOURCE.get(nombre_corto, "wansoft") == "wansoft"