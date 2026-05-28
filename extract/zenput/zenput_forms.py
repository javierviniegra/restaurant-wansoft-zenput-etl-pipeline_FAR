"""
Zenput Forms Extraction Wrapper
"""

from extract.utils.legacy_runner import run_legacy_script

def extract_zenput_forms():
    print("[ZENPUT FORMS]")
    return run_legacy_script(
        "legacy/zenput/zenput_mysql_forms.py"
    )