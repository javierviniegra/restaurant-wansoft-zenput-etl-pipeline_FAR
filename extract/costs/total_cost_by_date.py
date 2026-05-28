from extract.utils.legacy_runner import run_legacy_script


def extract_total_cost_by_date(company=None):
    print(f"[TOTAL COST BY DATE][WANSOFT] {company}")
    return run_legacy_script(
        "legacy/wansoft/automaticos/getTotalCostByDate.py",
        company_name=company
    )