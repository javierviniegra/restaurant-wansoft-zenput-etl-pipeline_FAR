from extract.utils.legacy_runner import run_legacy_script


def extract_all_orders_xml(company=None):
    print(f"[EXTRACT ALL ORDERS XML][WANSOFT] {company}")
    return run_legacy_script(
        "legacy/wansoft/automaticos/extractAllOrdersByDay.py",
        company_name=company
    )