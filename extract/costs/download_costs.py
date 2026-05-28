from extract.utils.legacy_runner import run_legacy_script


def extract_download_costs(company=None):
    print(f"[DOWNLOAD COSTS][WANSOFT] {company}")
    return run_legacy_script(
        "legacy/wansoft/descargarCostoWansoft/descargarCostoWansoft.py",
        company_name=company
    )