"""
Nightly stages of the unified supplier invoices, analytics_expense_invoices
(expenses domain, block 6: docs/analytics-expense-invoices-design.md):

- "Gastos - facturas de proveedor Odoo": Odoo vendor bills and credit notes
  into odoo_vendor_bill_snapshot / _line_snapshot, incremental by write_date
  plus every stored open bill; on Sundays a full pass that also drops bills
  deleted in Odoo (extract/expenses/odoo_vendor_bills.py).
- "Gastos - estatus Wansoft": current Estatus of every Wansoft invoice still
  listed by GetPendingExpenses_Xml into wansoft_expense_live_status
  (extract/expenses/wansoft_expense_status.py; read-only against Wansoft).
- "Gastos - tabla unificada": first the governed classification tables are
  topped up (scripts/seed_expense_mappings.py: only accounts of the decided
  names that appeared in an Odoo chart, never overwriting a decision), then
  analytics_expense_invoices is rebuilt and swapped in
  (scripts/build_analytics_expense_invoices.py).

They run after the legacy chain, so "Compras - facturas/gastos" has already
refreshed getexpenses_factura. A non-zero exit or an exception fails the stage.
"""
from datetime import date

from extract.expenses.odoo_vendor_bills import main as odoo_vendor_bills_main
from extract.expenses.wansoft_expense_status import main as wansoft_expense_status_main
from scripts.build_analytics_expense_invoices import main as build_expense_invoices_main
from scripts.seed_expense_mappings import main as seed_expense_mappings_main


def run_odoo_vendor_bills_job(today=None):
    full = (today or date.today()).weekday() == 6
    odoo_vendor_bills_main(["--full"] if full else [])


def run_wansoft_expense_status_job():
    code = wansoft_expense_status_main([])
    if code:
        raise SystemExit(code)


def run_expense_invoices_job():
    seed_expense_mappings_main(apply=True)
    build_expense_invoices_main()
