from extract.utils.legacy_runner import run_legacy_script


def extract_tablajeria_report(company=None):
    print(f"[TABLAJERIA REPORT][WANSOFT] {company}")
    return run_legacy_script(
        "legacy/wansoft/automaticos/getTablajeriaReport.py",
        company_name=company
    )
