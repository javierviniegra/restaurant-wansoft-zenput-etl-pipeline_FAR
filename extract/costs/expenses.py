from extract.utils.legacy_runner import run_legacy_script


def extract_expenses(company=None):
    print(f"[EXPENSES][WANSOFT] {company}")
    return run_legacy_script(
        "legacy/wansoft/automaticos/getExpenses.py",
        company_name=company
    )