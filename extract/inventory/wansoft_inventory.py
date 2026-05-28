"""
Wansoft Inventory Extraction Wrapper
"""

from extract.utils.legacy_runner import run_legacy_script


def extract_inventory(company=None):
    print(f"[INVENTORY][WANSOFT] {company}")
    return run_legacy_script(
        "legacy/wansoft/getStockInventory.py",
        company_name=company
    )