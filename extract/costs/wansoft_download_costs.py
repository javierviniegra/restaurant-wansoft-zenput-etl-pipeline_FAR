"""
Wansoft Download Cost Module Wrapper
"""

from legacy.wansoft.descargarCostoWansoft.descargarCostoWansoft import main as legacy_download_costs


def extract_download_costs():
    print("Running Wansoft Download Cost extraction...")
    return legacy_download_costs()