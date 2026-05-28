from extract.utils.legacy_runner import run_legacy_script


def extract_cost_report_semana_pyq(company=None):
    print(f"[COST REPORT SEMANA PYQ][WANSOFT] {company}")
    return run_legacy_script(
        "legacy/wansoft/automaticos/getCostReport_SemanaPyQ.py",
        company_name=company
    )