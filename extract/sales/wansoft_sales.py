"""
Sales Extraction Module (Wansoft ONLY)

IMPORTANT:
Sales data is exclusively sourced from Wansoft.
Odoo is NOT used for sales as it is not the system of record.
"""

from legacy.wansoft.automaticos.getAllOrdersByDay import main as legacy_sales

def extract_sales():
    print("Running Wansoft sales extraction...")
    legacy_sales()