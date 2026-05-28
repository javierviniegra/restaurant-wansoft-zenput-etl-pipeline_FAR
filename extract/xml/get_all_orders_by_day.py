"""
Wansoft XML Orders Extraction Wrapper
"""

from extract.utils.legacy_runner import run_legacy_script


def extract_orders_by_day(company=None):
    print(f"[GET ALL ORDERS BY DAY][WANSOFT] {company}")
    return run_legacy_script(
        "legacy/wansoft/automaticos/getAllOrdersByDay.py",
