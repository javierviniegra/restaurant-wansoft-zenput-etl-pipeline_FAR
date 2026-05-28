"""
Sales Extraction Module (Wansoft ONLY)

IMPORTANT:
Sales data is exclusively sourced from Wansoft.
Odoo is NOT used for sales as it is not the system of record.
"""

from extract.utils.legacy_runner import run_legacy_script


def extract_sales(company=None):
    print(f"[SALES][WANSOFT] {company}")
    return run_legacy_script(
        "legacy/wansoft/automaticos/getAllOrdersByDay.py",
        company_name=company
    )