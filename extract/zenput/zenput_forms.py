"""
Zenput Forms Extraction Wrapper
"""

from legacy.zenput.zenput_mysql_forms import main as legacy_forms


def extract_zenput_forms():
    print("Running Zenput Forms extraction...")
    return legacy_forms()