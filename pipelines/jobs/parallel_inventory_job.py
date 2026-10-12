"""
Nightly stages "Inventario paralelo Wansoft - entradas/salidas" (owner, 2026-10-10).

The branches already on Odoo keep capturing inventory in Wansoft (checked
live for 2026-10-06: entries and exits of all 8 migrated branches). Since the
cutover the main Wansoft tables only load the branches on Wansoft, so this
runs the same legacy loaders in parallel mode (WANSOFT_INVENTORY_PARALLEL=1)
for the Odoo branches, into wansoft_parallel_inputinventory_entrada and
wansoft_parallel_outgoinginventory_salida. The unified movements table marks
these rows 'wansoft_parallel_after_odoo', never in the business totals.
Same reload window as the main loaders (WANSOFT_LOOKBACK_DAYS).
"""
import os

from extract.utils.legacy_runner import run_legacy_script


def _run_parallel(script):
    os.environ["WANSOFT_INVENTORY_PARALLEL"] = "1"
    try:
        run_legacy_script(script)
    finally:
        os.environ.pop("WANSOFT_INVENTORY_PARALLEL", None)


def run_parallel_input_inventory_job():
    _run_parallel("legacy/wansoft/automaticos/getInputInventory.py")


def run_parallel_outgoing_inventory_job():
    _run_parallel("legacy/wansoft/automaticos/getOutgoingInventory.py")
