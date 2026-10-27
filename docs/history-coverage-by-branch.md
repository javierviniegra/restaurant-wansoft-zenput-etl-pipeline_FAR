# History coverage per branch (2026-10-27)

What history each reference table holds per branch and source system, how to
measure it, and why the obvious query is too slow on the inventory tables.

- Query: `sql/maintenance/history_coverage_by_branch.sql` (read-only, about 1
  minute in production; never between 01:30 and 03:00 or on Thursday at 18:00).
- Owner-facing result: page 2 of `reports/referencias/tablas_de_referencia_mysql.pdf`
  ("Desde cuándo hay datos, por sucursal"), generated from the query's output.

## Reference tables covered

| Topic | Table | Source |
|---|---|---|
| Sales | `getallordenesbyday_new_venta` | Wansoft only (every branch) |
| Cash closing | `getglobalcashclosing` | Wansoft only |
| Costs (day / month / week) | `gettotalcostbydate`, `costeomensual`, `costeomensual_semanapyq` | Wansoft, Odoo from `costs_source_by_company.odoo_cost_start_date` |
| Purchases | `analytics_purchase_order_lines` | Wansoft + Odoo |
| Supplier invoices | `analytics_expense_invoices` | Wansoft + Odoo |
| Inventory movements | `analytics_inventory_movements` | Wansoft + Odoo |
| Daily stock | `analytics_inventory_stock_daily` | Wansoft + Odoo |

Branch keys differ per table: sales and the analytic tables use the short key
(`company_source_key`); costs and cash closing carry the Wansoft ID
(`subsidiary_id`), translated with `costs_source_by_company` (19 rows, one per
branch; 7697 Taqueria San Fernando is not in it and keeps its long name).

## The bottleneck (measured in production, 2026-10-27)

The first version grouped every table by branch and source with `COUNT(*)`
and the `include_in_business_views = 1` filter. It ran for more than 10
minutes and never returned; the connection dropped. Timing each part:

| Part | Rows | Time |
|---|---|---|
| Sales (`getallordenesbyday_new_venta`, 1.2 M rows) | 20 | 3.3 s |
| Cash closing, the three cost tables | 20-26 each | 0.1 s each |
| Purchases (`analytics_purchase_order_lines`, 0.75 M) | 26 | 4.6 s |
| Supplier invoices | 28 | 1.0 s |
| **Movements (`analytics_inventory_movements`, 40.2 M rows, 11.7 GB)** | — | **> 9 min, killed** |

Why: the movements table's only branch index is `idx_company_date
(company_source_key, movement_date)`. Grouping by `source_system`, filtering
on `include_in_business_views` or counting rows makes MariaDB read all
40 M rows. Rewriting it as correlated `ORDER BY movement_date LIMIT 1`
subqueries per branch and source did not help either (over 5 minutes): when a
branch has no rows of a source (Odoo for a Wansoft branch), the subquery walks
the branch's whole history looking for one.

What works:
- **Movements: per branch only, no filter, no count**: `MIN/MAX(movement_date)
  ... GROUP BY company_source_key` is a loose index scan over
  `idx_company_date`, **0.0 s**. The per-source dates are the same as the daily
  stock's, so nothing is lost.
- **Daily stock: per branch and source, no count**: 38.9 s (an index scan of
  the 16-18 M rows; `idx_stock_daily_date` starts with `stock_date`, so it does
  not help a per-branch group).
- Whole query: 218 rows in 49 s.

If a per-source split of the movements is ever needed often, an index
`(company_source_key, source_system, movement_date)` would make it instant.
Not created: it is a production schema change (about 1-2 GB more on an 11.7 GB
table) and nothing needs it today.

The same applies to anyone querying the big tables (tukanmx included): always
filter `analytics_inventory_movements` by `company_source_key` and a
`movement_date` range, and `analytics_inventory_stock_daily` by
`company_source_key` and a `stock_date` range. A count or group over the whole
movements table takes more than 10 minutes, a third of tukanmx's 30-minute
statement limit (data guide 1.9, sections 5.4 and 8).

## Findings (production, 2026-10-27)

- Every branch reaches yesterday (2026-10-26) in every table, except where
  nobody captured: purchases of Metepec until 10-23 and Playa del Carmen until
  10-22; recent invoices lag a few days in several branches (normal: invoices
  arrive later).
- Odoo appears in purchases, supplier invoices and daily stock of the 10 Odoo
  branches, and in costs of 6 (Puebla, CentroMyJ, Acoxpa, Coyoacán, Oceanía,
  Tepeyac). Isabel, San Jerónimo, Vía Vallejo and Antenas stay on Wansoft costs
  by rule (complete Odoo month required; Antenas' Odoo is being repaired).
- Typical starts: sales 2021-09-01, cash closing 2022-01-01, daily cost
  2021-07-31, monthly 2022-01-01, weekly 2024-01-02, purchases 2021-09.
  Inventory is the oldest (Taquería Viaducto 2020-09-29, Metepec 2020-11-30,
  Oceanía 2021-04-27). Branches opened later start later (Cancún and Playa del
  Carmen 2022-08, Tepeyac 2022-11, Coyoacán 2026-01, CentroMyJ and Puebla 2026).
- Supplier invoices: complete from 2023-01-01 (2,292 invoices in January 2023
  vs fewer than 100 a month in 2022); earlier dates are scattered invoices back
  to 2019-02-18. Data guide 1.8 said "since 2019-02-18"; corrected in 1.9.
- Versalles has no purchases in the analytic layer and only 7 supplier invoices.
- Taqueria San Fernando (7697, left the group 2025-02-28) carries a different
  name in each table: `Taq San Fernando` in sales, `Fonda Argentina - Taqueria
  San Fernando` in costs and cash closing, `Taqueria San Fernando` in supplier
  invoices.
- San Jerónimo and Vía Vallejo have Odoo movements dated today (2026-10-27):
  moves registered early in the morning; the daily stock stops at yesterday.
- Born-on-Odoo branches (Puebla, CentroMyJ) have Wansoft cost rows from
  2026-05-29, before their Odoo cost start (2026-06-10 / 2026-06-01).
