"""
One-off backfill: dev's getallordenesbyday_new_venta only has Aug 28-31
for the 7 Odoo-migrated branches (root cause never found -- see
PROJECT_CONTEXT_REPORT.md 2026-09-15 session). Sales is always
Wansoft-sourced regardless of Purchases/Inventory migration status, so
this gap is purely a dev history gap, not a live pipeline issue.

Backfills Aug 1-28 for a given branch by calling the real Candado
(verificar_y_sincronizar) with a manual reference date, same
Cierre-Z-validated sync logic the daily job uses -- just pointed at
history instead of "today". Does NOT modify extractAllOrdersByDay.py's
own MODO/FECHA_MANUAL globals (those stay "hoy" for the real daily job);
this monkey-patches the branch list on the already-imported module for
the duration of this one call only.

Usage: python -m scripts.backfill_sales_august_acoxpa
"""

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legacy.wansoft.automaticos import extractAllOrdersByDay as candado  # noqa: E402

TARGET_BRANCH_IDS = {"5320"}  # Acoxpa -- cuentas_sucursales stores ids as strings

original_accounts = candado.cuentas_sucursales
candado.cuentas_sucursales = [
    c for c in original_accounts if c[0] in TARGET_BRANCH_IDS
]

print(f"Backfilling branches: {[c[1] for c in candado.cuentas_sucursales]}")

try:
    # fecha_referencia - N = the day being checked; want Aug 1..28, so
    # reference = Aug 29 (n=1 -> Aug 28, ... n=28 -> Aug 1).
    candado.verificar_y_sincronizar(
        fecha_referencia=datetime(2026, 8, 29),
        dias_atras=28,
        es_modo_hoy=False,  # always validate against Cierre Z -- all history, no open day
    )
finally:
    candado.cuentas_sucursales = original_accounts

print("\n==== BACKFILL DONE ====")
