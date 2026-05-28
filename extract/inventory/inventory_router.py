from core.config.companies import COMPANY_SOURCE
from extract.inventory.wansoft_inventory import extract_inventory as wansoft_inventory
from extract.inventory.odoo_inventory import extract_inventory as odoo_inventory


def extract_inventory_by_company(company_name):

    source = COMPANY_SOURCE.get(company_name, "wansoft")

    if source == "odoo":
        return odoo_inventory(company_name)

    return wansoft_inventory(company_name)
