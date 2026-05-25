"""
Wansoft Inventory Extraction Wrapper
"""

from legacy.wansoft.getStockInventory import main as legacy_inventory


def extract_inventory():
    print("Running Wansoft Inventory extraction...")
    return legacy_inventory()
