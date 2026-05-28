from extract.utils.legacy_runner import run_legacy_script


def extract_outgoing_inventory(company=None):
    print(f"[OUTGOING INVENTORY][WANSOFT] {company}")
    return run_legacy_script(
        "legacy/wansoft/automaticos/getOutgoingInventory.py",
        company_name=company
    )