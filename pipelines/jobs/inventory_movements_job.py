"""
Nightly stages of the unified inventory movements (owner, 2026-10-14):

- "Inventario Odoo - movimientos": done Odoo stock moves with their valuation
  into odoo_stock_move_snapshot, incremental by write_date
  (extract/inventory/odoo_stock_moves.py).
- "Inventario - movimientos unificados": analytics_inventory_movements,
  Wansoft rows captured in the last days plus the Odoo side rebuilt in full
  (scripts/build_analytics_inventory_movements.py).

- "Inventario - existencias diarias" (owner, 2026-10-26):
  analytics_inventory_stock_daily, stock per branch x product x day, updated in
  place from the movements just built (scripts/build_analytics_inventory_stock_daily.py;
  needs one --full load first).

They run after "Inventario Odoo - foto diaria", when the Wansoft main and
parallel inventory and Odoo's stock of the night are loaded. A non-zero exit
fails the stage.
"""
from extract.inventory.odoo_stock_moves import main as odoo_stock_moves_main
from scripts.build_analytics_inventory_movements import main as build_movements_main
from scripts.build_analytics_inventory_stock_daily import main as build_stock_daily_main


def run_odoo_stock_moves_job():
    code = odoo_stock_moves_main([])
    if code:
        raise SystemExit(code)


def run_inventory_movements_job():
    code = build_movements_main([])
    if code:
        raise SystemExit(code)


def run_inventory_stock_daily_job():
    code = build_stock_daily_main([])
    if code:
        raise SystemExit(code)
