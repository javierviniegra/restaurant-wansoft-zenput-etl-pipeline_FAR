from extract.utils.legacy_runner import run_legacy_script


def extract_global_cash_closing(company=None):
    print(f"[GLOBAL CASH CLOSING][WANSOFT] {company}")
    return run_legacy_script(
        "legacy/wansoft/descargarCostoWansoft/getGlobalCashClosing.py",
        company_name=company
    )