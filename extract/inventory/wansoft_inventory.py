"""
Inventory Extraction Module (Wansoft - Legacy Wrapper)

This module wraps the existing Wansoft inventory extraction logic
without modifying the original implementation.
"""

from getStockInventory import main as legacy_inventory

def extract_inventory():
    print("Running Wansoft inventory extraction...")
    legacy_inventory()
