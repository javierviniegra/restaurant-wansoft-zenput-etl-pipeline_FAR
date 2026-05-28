"""
Zenput Tasks Extraction Wrapper
"""

from extract.utils.legacy_runner import run_legacy_script

def extract_zenput_tasks():
    print("[ZENPUT TASKS]")
    return run_legacy_script(
        "legacy/zenput/zenput_mysql_tasks.py"
    )