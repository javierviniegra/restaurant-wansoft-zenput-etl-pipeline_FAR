"""
Wansoft XML Orders Extraction Wrapper
"""

from legacy.wansoft.automaticos.getAllOrdersByDay import main as legacy_xml_orders


def extract_xml_orders():
    print("Running Wansoft XML Orders extraction...")
    return legacy_xml_orders()