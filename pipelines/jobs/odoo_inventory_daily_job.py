"""
Nightly stage "Inventario Odoo - foto diaria" (owner, 2026-10-08).

Stores Odoo's stock of the day (stock.quant in internal and transit
locations, every company) in odoo_inventory_quant_daily, so the branches on
Odoo keep a day-by-day stock history. See extract/inventory/odoo_quant_daily.py.
"""
from extract.inventory.odoo_quant_daily import run as run_odoo_quant_daily


def run_odoo_inventory_daily_job():
    run_odoo_quant_daily()
