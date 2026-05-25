"""
Wansoft Cost Extraction Wrapper
"""

from legacy.wansoft.getCostReport_update import main as legacy_costs


def extract_costs():
    print("Running Wansoft Cost extraction...")
    return legacy_costs()