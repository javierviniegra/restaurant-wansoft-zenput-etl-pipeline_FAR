from extract.utils.legacy_runner import run_legacy_script


def extract_input_inventory(company=None):
    print(f"[INPUT INVENTORY][WANSOFT] {company}")
    return run_legacy_script(
        "legacy/wansoft/automaticos/getInputInventory.py",
        company_name=company
    )