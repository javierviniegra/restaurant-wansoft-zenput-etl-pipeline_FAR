# Unified inventory tables: movements and daily stock (design)

Status: **design agreed with the owner on 2026-10-10; not built yet.** Build
starts on a working day, step by step, each step tested on dev and approved
before it reaches production.

## Goal (owner, 2026-10-08)

"I need inventories, sales, purchases, supplier invoices and inventory
movements, easily, regardless of the source system, with their old history
in the same table, all living together in harmony." Every branch, every day.

Where each domain stands:

| Domain | Unified table | State |
|---|---|---|
| Sales | `getallordenesbyday_new_*` | done: one source (Wansoft) for all 19 branches |
| Purchases | `analytics_purchase_order_lines` | done: the model the others follow |
| Supplier invoices | `analytics_expense_invoices` | designed (`docs/analytics-expense-invoices-design.md`), step 4 below |
| **Inventory movements** | **`analytics_inventory_movements`** | **this document** |
| **Stock per day** | **`analytics_inventory_stock_daily`** | **this document** |

## Rules shared with purchases

- One row per business fact, whatever system produced it; `source_system`
  says which.
- Per branch, Wansoft **before** its Odoo start date
  (`odoo_company_migration_policy.operational_start_date`) and Odoo **from**
  it. A branch-day is never counted from both systems.
- `final_source_status` explains each row: `wansoft_final` (branches on
  Wansoft), `wansoft_history_before_odoo`, `odoo_final`,
  `wansoft_parallel_after_odoo` (see below).
- `include_in_business_views = 1` for what counts; the rest stays for audit
  and comparison.
- Product: `wansoft_code` (Wansoft rows; Odoo rows through the approved
  dictionary mapping), `odoo_product_id`, `product_analytical_key`
  (`dim_product`). Branch: `company_source_key`.

## Owner's decisions (2026-10-10)

1. `analytics_inventory_movements` is a **physical table** (not a view over
   the Wansoft tables): about 27 M rows, roughly 7 GB more on the database
   server, fast queries and the rules in one place. The nightly run reloads
   only the recent window.
2. `analytics_inventory_stock_daily` is **complete daily stock**: one row per
   branch × product × day since the first movement (about 12 M rows, about
   1.5 GB). Any date is a plain `WHERE stock_date = ...`.
3. The **Wansoft inventory the 8 migrated branches keep capturing in
   parallel since 2026-10-01** is loaded again (checked live: Acoxpa,
   Antenas, Tepeyac, Oceanía, Coyoacán, Isabel, San Jerónimo and Vía Vallejo
   all recorded entries and exits on 2026-10-06), into **its own raw tables**
   so that consumers reading `getinputinventory_entrada` /
   `getoutgoinginventory_salida` directly (Power BI) do not count it twice.
   In the movements table it is `wansoft_parallel_after_odoo` with
   `include_in_business_views = 0`: visible to compare Wansoft vs Odoo, never
   in the totals.

## Table 1: `analytics_inventory_movements`

One row = one inventory movement of one product in one branch on one day.

| Column | Meaning |
|---|---|
| `movement_date` | business date (Wansoft: `FechaEntrada` / `COALESCE(NULLIF(Fecha,'0000-00-00'), FechaReal)`; Odoo: `stock.move.date` in Mexico City time) |
| `company_source_key` | branch |
| `source_system`, `source_movement_id` | `wansoft` + `IdEntrada`/`IdSalida`, or `odoo` + `stock.move` id |
| `direction` | `in` / `out` |
| `movement_type` | normalized: `purchase_receipt`, `sale_consumption`, `sale_cancellation`, `waste`, `consumption`, `production_in`, `production_out`, `transfer_in`, `transfer_out`, `adjustment`, `initial_inventory`, `other` |
| `source_movement_type` | the original: Wansoft `TipoEntrada`/`TipoSalida`; Odoo picking type and source/destination location usage |
| `wansoft_code`, `odoo_product_id`, `product_analytical_key`, `product_name` | product |
| `quantity` | signed (+ in, − out), in the product's unit |
| `unit_cost`, `total_cost` | Wansoft `CostoUnitario`; Odoo `stock.valuation.layer` (unit cost and value) |
| `location_name` | warehouse / kitchen when known |
| `counts_in_stock` | whether it moves the stock balance, with the rules already used by `analytics_inventory_balance` (Wansoft: purchase orders, transfers on both sides, capture errors and rejected invoices do not) |
| `final_source_status`, `include_in_business_views` | as above |

**Sources and sizes (2026-10-10):** Wansoft entries 1.26 M rows, exits
25.1 M (about 800 k a year per large branch); Odoo done `stock.move` about
1.04 M for the group's companies since June 2026 (1.64 M in the whole
database), with `stock.valuation.layer` (1.6 M layers) for the value.

**Odoo movement direction**, from the branch's point of view: `in` when the
destination location is an internal location of the branch, `out` when the
source is; typed by the other side's usage (supplier → `purchase_receipt`,
customer → `sale_consumption`, inventory → `adjustment`/`waste` (scrap),
production → `production_in/out`, internal or transit → `transfer_in/out`).
To be confirmed against real moves in step 1.

## Table 2: `analytics_inventory_stock_daily`

One row = branch × product × day, from the product's first movement in the
branch to yesterday: `stock_date`, `company_source_key`, `source_system`,
`wansoft_code`, `odoo_product_id`, `product_name`, `stock_qty` (cumulative
sum of `quantity` where `counts_in_stock`), `stock_value` (Odoo from the
valuation layers; Wansoft from the movement costs, approximate),
`final_source_status`, `include_in_business_views`.

At a branch's Odoo start date the series switches from the Wansoft balance
to the Odoo one (each system's own count; Odoo starts from its opening
balances). The nightly run recomputes only the days inside the reload window.

## Validation

- Wansoft stock on any date equals the formula in
  `docs/inventory-coverage-by-branch.md` (verified: Coca Cola Mini, Viaducto,
  3,096 / 2,939 / 3,170), and today's equals `analytics_inventory_balance`.
- Odoo stock rebuilt from the moves equals Odoo's own stock
  (`odoo_inventory_quant_daily`) per branch × product × day, from
  2026-10-08 on.
- Every branch has movements up to yesterday (completeness per branch, as in
  the coverage document).

## Build order

1. **Odoo stock moves and valuation** (part b): raw snapshot tables loaded
   incrementally by `write_date`, each company from its start date (Puebla
   and CentroMyJ from opening). Validate against `odoo_inventory_quant_daily`.
2. **Parallel Wansoft inventory** of the 8 migrated branches since
   2026-10-01, into its own raw tables (same loaders, different target).
3. **`analytics_inventory_movements`**: one-off backfill, then a nightly
   window; new nightly stage.
4. **`analytics_inventory_stock_daily`** from the movements.
5. **`analytics_expense_invoices`** (supplier invoices; needs a crosswalk from
   Odoo accounting accounts to Wansoft's `Cuenta`).

Before step 3, check free space on the database server (about 9 GB more for
tables 1 and 2), and grant the new tables to the read-only users.
