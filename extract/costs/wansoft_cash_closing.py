"""
Wansoft Cash Closing Extraction Wrapper
"""

from legacy.wansoft.getGlobalCashClosing_update import main as legacy_cash


def extract_cash_closing():
    print("Running Wansoft Cash Closing extraction...")
    return legacy_cash()