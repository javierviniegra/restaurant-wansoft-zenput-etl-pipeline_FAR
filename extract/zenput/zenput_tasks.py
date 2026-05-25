"""
Zenput Tasks Extraction Wrapper
"""

from legacy.zenput.zenput_mysql_tasks import main as legacy_tasks


def extract_zenput_tasks():
    print("Running Zenput Tasks extraction...")
    return legacy_tasks()