# Wansoft Automated Core ETL (`/automaticos`)

This directory contains the primary automated scripts scheduled to run daily. Their main goal is to extract operational data, sales, inventory movements, and expenses from all Fonda Argentina branches using the Wansoft SOAP API.

In production they run inside the nightly cycle `Wansoft_Pipeline_Diario` (01:30 on the tasks VM, `scripts/run_daily_cycle.py`, stage list in `pipelines/scheduler.py`), never as separate scheduled tasks.

## 🔐 Security & Installation
This module strictly requires the centralized `.env` and `database.py` files located in the root of the project to run safely without exposing hardcoded passwords or paths.
1. Ensure the `python-dotenv`, `mysql-connector-python`, and `zeep` packages are installed.
2. Ensure the `XML_DOWNLOAD_DIR` is correctly set in your root `.env` file to handle large payloads locally.

## 📄 File Structure & Documentation

Here is a detailed breakdown of what each script does and what data it brings to the MySQL database:

*   **`extractAllOrdersByDay.py`**: The Sales "Candado" (Lock): downloads the daily orders XML of each branch, compares the database total against Wansoft's official Z-Closing and rewrites a day only when they differ. It populates `getallordenesbyday_new_venta`, `_new_detalleventa`, `_new_modificador` and `_new_pago`. Exits non-zero when not a single XML could be obtained.
*   **`getAllOrdersByDay.py`**: Older full-range Sales loader; not part of the nightly cycle.
*   **`getCostReport_SemanaPyQ.py`**: Week-to-date cost (Monday through the day before `created_at`) into `costeomensual_semanapyq`. Wansoft or Odoo per branch and day, see "Cost routing" below.
*   **`getExpenses.py`**: Downloads Wansoft supplier invoices (`Facturas`) with tax details (IVA, IEPS), subtotals and supplier RFCs into `getexpenses_factura`. Only branches still on Wansoft (`COMPANY_SOURCE`).
*   **`getInputInventory.py`**: Inventory entries (purchases, transfers) with unit costs, expiration dates and quantities into `getinputinventory_entrada` (upsert by `IdEntrada` + branch). Only branches still on Wansoft.
*   **`getOutgoingInventory.py`**: Inventory exits by department and warehouse into `getoutgoinginventory_salida` (upsert against the unique key `uq_subsidiary_fecha_idsalida`, added at the 2026-10-01 cutover). Only branches still on Wansoft.
*   **`getTablajeriaReport.py`**: Butchery yields (base product into generated products, shrinkage, costs) into `gettablajeriareport`. Being phased out as branches move purchases/inventory to Odoo.
*   **`getTotalCostByDate.py`**: Single-day cost of sales (`CostoTotalVenta`) into `gettotalcostbydate`. Wansoft or Odoo per branch and day, see below.

## 💰 Cost routing: Wansoft or Odoo, per branch and per day

The three cost scripts (`getCostReport_SemanaPyQ.py`, `getTotalCostByDate.py` and `../descargarCostoWansoft/descargarCostoWansoft.py`) decide the source of every (branch, day) with `extract/costs/cost_routing.py`:

1. **Branches on Wansoft** (`COMPANY_SOURCE = "wansoft"` in `core/config/companies.py`): always Wansoft's cost report.
2. **Branches on Odoo**: Odoo's cost of sales (`extract/costs/odoo_cost_report.py`) from their start date (`odoo_company_migration_policy.operational_start_date`), Wansoft before it. Production since the 2026-10-01 cutover: Acoxpa, Tepeyac, Oceanía, La Esquina Coyoacán from 2026-10-01; Puebla and CentroMyJ since they opened (June 2026).
3. **Temporary exceptions** (`COSTS_WANSOFT_TEMPORARY_EXCEPTIONS`): stay on Wansoft regardless. Today only **Antenas** (its Odoo cost data is broken by pilot-era tests); remove it when the owner confirms the repair.
4. **Automatic switch** (`COSTS_AUTO_SWITCH_TO_ODOO`, since 2026-10-02): **Isabel La Católica, San Jerónimo and Vía Vallejo** run on Odoo for purchases but cannot post cost of sales there until their opening inventory balances are loaded, so they stay on Wansoft until Odoo really has cost data for each one. The nightly stage **"Costos - cambio automático a Odoo"** (`pipelines/jobs/costs_switch_job.py`, rule in `extract/costs/cost_switch.py`) switches each branch by itself:
    - rule: the first of **two consecutive days** on which Odoo's daily cost is > 0 and between **0.5x and 2x** Wansoft's cost stored for that day (a test entry or a stray adjustment cannot trigger it);
    - the switch date is recorded in the table **`costs_odoo_switch`** (branch, date, evidence, backfilled/validated timestamps) and announced with an `[AVISO]` line in the night's log;
    - the same night it recomputes that branch's three cost tables from the switch date (whatever the 10-day window), then validates them;
    - days before the switch stay on Wansoft; it never switches back by itself. To undo a switch, delete the branch's row from `costs_odoo_switch`.
    - Check what the rule decides today, read-only: `python -m extract.costs.cost_switch --prod`.

**Month/week to date across a switch in the middle of a period** (owner, 2026-10-02): on Odoo days, `costeomensual` and `costeomensual_semanapyq` add Wansoft's accumulation of the same month/week up to the day before the switch (`wansoft_period_base`), so the period stays whole and every day counts exactly once. Before this, the five branches migrated on Thursday 2026-10-01 lost Monday-Wednesday of that week.

**Columns on Odoo rows:** only `CostoTotal`, `CostoDeProductosVendidos` and `CostoDeMerma` come from Odoo (monthly cortesías/cancelaciones come from the cash closing). The Wansoft-only columns (`CostoDeConsumo`, `CostoDeDesperdicio`, `CostoDeRobo`, `AjustePorSobrantes`, `UtilidadMarginal`, `CostoIdealDeProductosPendientesDeRebaja`; weekly also cortesías/cancelaciones) are set to **NULL**, also when a row that was Wansoft is recomputed from Odoo, so a stale Wansoft consumo is never subtracted from an Odoo `CostoTotal`. On Odoo rows the accumulated `CostoTotal` already excludes consumo. SQL consumers use `COALESCE`.

**Validation every night:** the same stage checks every branch costed from Odoo over the nightly window: no duplicate (branch, day) rows in the three tables, and on every Odoo day the month/week accumulation grows by exactly that day's cost (`gettotalcostbydate`). Any problem prints `[AVISO]` lines and fails the stage, so it appears in the cycle summary.

**Windows and backfills:** the cost scripts re-check the last `COSTS_LOOKBACK_DAYS` (10 by default, Wansoft recalculates costs after the fact). **The Odoo side re-reads longer** (`odoo_costs_window_start` in `extract/costs/cost_routing.py`, 2026-10-05): the whole current month, and during the first 10 days of a month the whole previous month too. Odoo's cost of a day comes from that day's customer invoices (the Wansoft sales passed to Odoo), which keep being created for up to ~2 weeks and the rest at the month-end closing (September 2026: 40-70% invoiced one day later, 70-100% after 7 days, 92-100% after 14, all by the close); with only 10 days the first days of each month would stay incomplete forever. Recent days of Odoo branches are therefore partial by construction: compare Odoo's invoiced amount with Wansoft's net sales of the day before reading their cost (`docs/production-cutover-runbook.md`, Section 7b). For a one-off backfill of some branches use `COSTS_ONLY_BRANCHES` with a long `COSTS_LOOKBACK_DAYS` (`docs/production-cutover-runbook.md`, step 3d and Section 7b).

**Published routing table `costs_source_by_company`** (2026-10-05, rewritten every night by the stage "Costos - cambio automático a Odoo"): one row per branch with `company_source_key`, `wansoft_subsidiary_id`, `odoo_company_id`, `odoo_cost_start_date` (first day on Odoo costs; NULL = always Wansoft) and `reason` (`wansoft`, `policy`, `exception`, `auto_switch_pending`, `switched`, `no_policy`), `updated_at`. Consumers (Central de Reportes) read it instead of copying the constants.

**Completeness of Wansoft costs:** Wansoft's cost of recent days grows while it processes the inventory deductions of the sales; `CostoIdealDeProductosPendientesDeRebaja` (in `costeomensual` and `costeomensual_semanapyq`) is the ideal cost still pending deduction, and it is 0 once the period is complete (all of September 2026 by 10-05; October month-to-date on 10-04 still 1-24% pending depending on the branch, highest on weekends). `CostoTotal` excludes the pending part; a consumer can show it as incomplete, or estimate with the pending part added. Odoo-sourced rows carry it NULL (their completeness is the invoiced share, see "Windows and backfills").

**Date convention:** `costeomensual` and `gettotalcostbydate` rows are dated with the day they cover; `costeomensual_semanapyq` rows are dated **one day after** the last day they cover.
