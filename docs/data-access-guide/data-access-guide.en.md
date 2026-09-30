# Data Access Guide — Fonda Argentina analytical databases

*Spanish version: [data-access-guide.es.md](data-access-guide.es.md)*

Audience: external teams building their own ETL on top of these databases (for
example, a question-and-answer / chatbot layer). It tells you **which table to
use for each business question, which fields matter, how tables join, and the
traps to avoid**. Every rule here was checked against the live schema and data
on 2026-09-28. PDF version: [data-access-guide.en.pdf](data-access-guide.en.pdf).

## Contents

1. [What is where](#1-what-is-where)
2. [Golden rules](#2-golden-rules-read-before-writing-any-query)
3. [Branch crosswalk](#3-branch-crosswalk)
4. [Which table answers which question](#4-which-table-answers-which-question)
   - [4.1 Available history](#41-available-history)
5. [Domains](#5-domains)
   - [5.1 Sales](#51-sales-wansoft-all-branches)
   - [5.2 Costs](#52-costs-wansoft-or-odoo-by-branch)
   - [5.3 Purchases](#53-purchases-wansoft-history--odoo-merged)
   - [5.4 Inventory](#54-inventory)
   - [5.5 Zenput](#55-zenput-zenput-database)
   - [5.6 Governance tables](#56-governance-tables)
6. [Do not use](#6-do-not-use)
7. [Freshness and schedule](#7-freshness-and-schedule)
8. [Access](#8-access)

---

## 1. What is where

Two MySQL (MariaDB 10.4) databases on the same server:

| Database | Content |
|---|---|
| `wansoft` | Sales, costs, purchases, inventory and the unified analytical layer |
| `zenput` | Operational checklists (forms, answers) and tasks from Zenput |

Source systems behind them:

| Source | What it provides | How it arrives |
|---|---|---|
| **Wansoft** (POS/ERP) | Sales for all branches, costs, cash closing, and purchases/inventory for branches not yet on Odoo | Daily download via its SOAP API |
| **Odoo** | Purchases and inventory for the branches migrated to Odoo | Daily read-only extraction |
| **Zenput** | Checklists and tasks | Daily API download |

Layers inside `wansoft`:

| Layer | Tables | Use it for |
|---|---|---|
| Raw Wansoft copies | `get*`, `costeomensual*` | Sales, costs, cash closing, Wansoft-side detail |
| Canonical | `canonical_purchase_*` | Internal: Odoo and Wansoft purchases merged into one shape. Prefer the analytics layer |
| **Analytics (business-ready)** | `analytics_*` | Purchases and inventory for all branches, both sources merged |
| Dimensions | `dim_company_analytical`, `dim_product`, `dim_vendor`, `dim_time` | Descriptions and attributes for the analytics layer |

---

## 2. Golden rules (read before writing any query)

1. **A branch is identified three different ways** depending on the table. Use
   the crosswalk in Section 3; never join tables on branch names blindly.
   - Short key (`Acoxpa`, `Oceanía`): sales tables (`Sucursal`) and the
     analytics layer (`company_source_key`).
   - **Numeric Wansoft id** (`5320`): costs (`subsidiary_id`) and the inventory
     tables — where the id is stored in a column confusingly named
     `subsidiary_name`.
   - Long Wansoft name (`Fonda Argentina - Acoxpa`): costs (`subsidiary_name`)
     and invoices (`getexpenses_factura.Sucursal`).
2. **`getexpenses_factura.Sucursal` contains the same branch spelled two ways**
   because of historical encoding damage (`Cancún` and `Canc??n`,
   `Oceanía` and `Ocean??a`). Map it to the crosswalk before grouping.
3. **Sales tables store amounts and dates as text** (`varchar`). Cast them:
   `CAST(Total AS DECIMAL(14,2))`, `DATE(Fecha)` (format `2026-09-01T00:00:00`).
4. **Analytics tables carry `include_in_business_views`.** Filter
   `include_in_business_views = 1` for business numbers; the other rows are kept
   for audit (internal providers, unmapped products, review cases) and carry an
   `exclude_reason`.
5. **Purchases and inventory come from two systems; the analytics layer already
   merges them without overlap** (Section 5.3). Do not rebuild the merge from raw
   tables.
6. **Data is loaded once a day, at about 01:30, through the previous day.** Each
   run also re-checks recent days (sales 10 days, Wansoft costs/inventory 5,
   purchases 35), so the last few days can still change.
7. Costs tables are **cumulative snapshots**, not daily amounts (Section 5.2).

---

## 3. Branch crosswalk

| Wansoft id | Short key (`Sucursal`, `company_source_key`) | Wansoft long name (costs) | Odoo company | Purchases & inventory source | Odoo start date |
|---|---|---|---|---|---|
| 5320 | Acoxpa | Fonda Argentina - Acoxpa | FONDA COSTA NERA | Wansoft → **Odoo from 2026-10-01** | 2026-10-01 |
| 4959 | Aeropuerto | Fonda Argentina - Aeropuerto | FONDA ARGENTINA AEROPUERTO | Wansoft | — |
| 4960 | Antenas | Fonda Argentina - Antenas | FONDA ARGENTINA LAS ANTENAS | Wansoft → **Odoo from 2026-10-01** | 2026-10-01 |
| 6175 | Cancun | Fonda Argentina - Cancún | — | Wansoft | — |
| 12802 | CentroMyJ | Fonda Argentina - Centro Mario y July | MARIO Y JULY | Odoo (born on Odoo) | 2026-06-01 |
| 4958 | Isabel La Católica | Fonda Argentina - Isabel La Católica | FONDA ARGENTINA | Wansoft → **Odoo from 2026-10-01** | 2026-10-01 |
| 12057 | La Esquina Coyoacán | Fonda Argentina - Coyoacan | FONDA ARGENTINA COYOACAN | Wansoft → **Odoo from 2026-10-01** | 2026-10-01 |
| 4752 | Metepec | Fonda Argentina - Tollocan | FONDA ARGENTINA TOLLOCAN | Wansoft | — |
| 4433 | Napoles | Fonda Argentina - Nápoles | FONDA ARGENTINA POLYFORUM | Wansoft | — |
| 5943 | Oceanía | Fonda Argentina - Oceanía | FONDA ARGENTINA ENCUENTRO OCEANIA | Wansoft → **Odoo from 2026-10-01** | 2026-10-01 |
| 6174 | Playa del Carmen | Fonda Argentina - Playa del Carmen | — | Wansoft | — |
| 12806 | Puebla | Fonda Argentina - Puebla | FONDA ARGENTINA PUEBLA | Odoo (born on Odoo) | 2026-06-10 |
| 5319 | San Jeronimo | Fonda Argentina – San Jerónimo | FONDA ARGENTINA SAN JERONIMO | Wansoft → **Odoo from 2026-10-01** | 2026-10-01 |
| 5321 | Taquería parroquia | Fonda Argentina – Taquería Parroquía | — | Wansoft | — |
| 4962 | Taquería Viaducto | Fonda Argentina - Taqueria Viaducto | — | Wansoft | — |
| 6560 | Tepeyac | Fonda Argentina - Tepeyac | FONDA ARGENTINA MAQ | Wansoft → **Odoo from 2026-10-01** | 2026-10-01 |
| 5396 | Versalles | Fonda Argentina - Taquería Exhibimex | — | Wansoft | — |
| 5318 | Vía Vallejo | Fonda Argentina – Vía Vallejo | FONDA ARGENTINA VALLEJO | Wansoft → **Odoo from 2026-10-01** | 2026-10-01 |
| 4961 | Viaducto | Fonda Argentina - Viaducto | FONDA ARGENTINA VIADUCTO | Wansoft | — |

Notes:
- Names differ between systems for the same branch: Metepec = "Tollocan",
  Napoles = "Polyforum", Versalles = "Taquería Exhibimex", Acoxpa = "Costa Nera"
  in Odoo. Long names use either a hyphen (`-`) or an en dash (`–`).
- `7697` "Taqueria San Fernando" appears in historical costs only; it is not one
  of the 19 current branches.
- **Sales always come from Wansoft for every branch**, whatever the purchases
  source.
- **New branches** (today Puebla and CentroMyJ, and every branch opened from
  now on) are born on Odoo: purchases, inventory and costs come from Odoo; in
  Wansoft they only record sales and daily closings.
- **Costs:** every branch operating on Odoo, migrated or new, takes its cost
  from Odoo **from its start date on**, and from Wansoft before that date.
  **Temporary exception: Antenas** keeps Wansoft costs while its Odoo database
  is repaired (it was the prototype). See Section 5.2.
- Internal providers **El Bodegón de Fito** and **Las Empanadas de María Eva**
  (central kitchens) are excluded as buying companies from business views.
- The same information, as data: `dim_company_analytical` and
  `analytics_company_domain_coverage` (Section 5.6). They use the short key and
  do not carry the Wansoft id; use this table for that link.

---

## 4. Which table answers which question

| Question | Table | Filter / note |
|---|---|---|
| Sales, tickets, covers per day/branch | `getallordenesbyday_new_venta` | one row per ticket |
| What was sold (dishes, groups) | `getallordenesbyday_new_detalleventa` | one row per line |
| Payment methods, tips | `getallordenesbyday_new_pago` | one row per payment |
| Official daily close (Z report), cancellations, courtesies, discounts | `getglobalcashclosing` | one row per branch per closing |
| Monthly cost of sales, waste, margin | `costeomensual` | month-to-date snapshot; take the last day |
| Weekly cost | `costeomensual_semanapyq` | week-to-date snapshot |
| Daily cost of sales | `gettotalcostbydate` | one row per branch per day |
| Butchery yields | `gettablajeriareport` | history of Wansoft branches only; being phased out (see 5.2) |
| Purchases (goods) for any branch, any period | `analytics_purchase_order_lines` / `analytics_purchase_orders` / `analytics_purchase_daily_company_product` | `include_in_business_views = 1` |
| Spend by accounting account (Costo operativo, Gastos directos, ...) | `getexpenses_factura` | Wansoft only (see 5.3) |
| Inventory entries/exits detail (Wansoft) | `getinputinventory_entrada`, `getoutgoinginventory_salida` | Wansoft branches |
| Current stock | `analytics_inventory_current_product_location`, `analytics_inventory_balance` | `include_in_business_views = 1` |
| Checklist results | `zenput.submissions` + `zenput.submission_answers` | |
| Tasks | `zenput.zenput_tasks` | |
| Which source feeds each branch | `analytics_company_domain_coverage` | |

### 4.1 Available history

Dates measured in production on 2026-09-28. Tables keep filling daily through the previous day.

| Data | Table | Source | Since | Notes |
|---|---|---|---|---|
| Sales: tickets, lines, modifiers | `getallordenesbyday_new_venta`, `_new_detalleventa`, `_new_modificador` | Wansoft | 2021-09-01 | 2021-12-14 to 2021-12-31 has almost no tickets (a gap in the source history, accepted) |
| Sales: payments per ticket | `getallordenesbyday_new_pago` | Wansoft | 2025-01-01 | No payments per ticket before 2025; use the cash closing |
| Daily cash closing | `getglobalcashclosing` | Wansoft | 2022-01-01 |  |
| Daily cost of sales | `gettotalcostbydate` | Wansoft or Odoo (5.2) | 2021-07-31 |  |
| Month-to-date cost | `costeomensual` | Wansoft or Odoo (5.2) | 2022-01-01 |  |
| Week-to-date cost | `costeomensual_semanapyq` | Wansoft or Odoo (5.2) | 2024-01-02 |  |
| Butchery yields | `gettablajeriareport` | Wansoft | 2022-01-01 | Being phased out (Section 5.2) |
| Supplier invoices by accounting account | `getexpenses_factura` | Wansoft | 2019-02-18 | The oldest history; only while a branch enters purchases in Wansoft |
| Inventory entries | `getinputinventory_entrada` | Wansoft | 2021-09-01 |  |
| Inventory exits | `getoutgoinginventory_salida` | Wansoft | 2020-11-30 | About 1.15 million rows have an empty date (`0000-00-00`); exclude them |
| **Unified purchases** | `analytics_purchase_order_lines`, `analytics_purchase_orders`, `analytics_purchase_daily_company_product` | **Wansoft + Odoo** | **2021-09-01** | Wansoft until each branch's Odoo start date, Odoo from then on (2026-10-01 for the migrated branches; Puebla and CentroMyJ since they opened in June). Checked year by year: same rows and amounts as production's Wansoft invoices |
| **Unified stock** | `analytics_inventory_current_product_location`, `analytics_inventory_balance` | **Wansoft + Odoo** | Current snapshot | No history by design; the Wansoft balance is recomputed nightly from every movement since 2020-11-30 |
| Checklists | `zenput.submissions`, `zenput.submission_answers` | Zenput | 2025-06-11 |  |
| Tasks | `zenput.zenput_tasks` | Zenput | 2025-06-03 |  |
| Calendar | `dim_time` | — | 2020-01-01 | Until 2035-12-31 |

---

## 5. Domains

### 5.1 Sales (Wansoft, all branches)

`getallordenesbyday_new_venta` — ticket header.

| Field | Meaning |
|---|---|
| `Sucursal` | Branch short key |
| `Movimento` | Ticket id within the branch (sic, no "i"); join key |
| `Fecha` | Business date, text `YYYY-MM-DDT00:00:00` |
| `Total`, `Subtotal`, `IVA`, `IEPS`, `Descuento` | Amounts, text |
| `Personas` | Covers |
| `Mesa`, `Mesero`, `Orden`, `Terminal` | Table, waiter, order number, terminal |
| `TipoOrden` | `Restaurant`, `Para llevar`, `eCommerce` |
| `HoraApertura`, `HoraCierre` | Open / close time |
| `Estatus` | Always `0` in current data |

Joins (both columns needed, the ticket id repeats across branches):
`venta.Sucursal = detalle.Sucursal AND venta.Movimento = detalle.Movimiento_Id`;
same for `getallordenesbyday_new_pago` and `getallordenesbyday_new_modificador`.

`getallordenesbyday_new_detalleventa` — lines: `Platillo`, `CodigoPlatillo`,
`Grupo`, `TipoGrupo` (e.g. food / drinks), `Cantidad`, `PrecioUnitario`,
`Total`, `Costo`, `Cortesia`, `Hora`.

`getallordenesbyday_new_pago` — `MetodoDePago`, `Total`, `Propina`, `Terminal`.

Waiters: delivery and app orders are attributed to a **placeholder waiter**
whose name varies by branch (`APLICACIONES`, `Apps Llevar`). Exclude it when
ranking real waiters.

```sql
SELECT Sucursal, DATE(Fecha) AS dia,
       COUNT(*) AS tickets,
       SUM(CAST(Personas AS UNSIGNED)) AS comensales,
       SUM(CAST(Total AS DECIMAL(14,2))) AS venta
FROM getallordenesbyday_new_venta
WHERE Fecha >= '2026-09-01' AND Fecha < '2026-10-01'
GROUP BY Sucursal, DATE(Fecha);
```

`getglobalcashclosing` — the official close per branch (`subsidiary_id`,
`fecha_corte`): `total_ventas`, `no_ordenes`, `total_personas`, averages, and
counts/amounts of courtesies, cancellations, discounts, voids, promotions.
Amounts here are **sale value**. Use it to reconcile daily totals.

### 5.2 Costs (Wansoft or Odoo, by branch)

Where each branch's cost comes from:

| Branch type | Cost source today |
|---|---|
| Wansoft only | Wansoft cost report |
| Migrated to Odoo (Acoxpa, Tepeyac, Oceanía, La Esquina Coyoacán; from 2026-10-01 also Isabel La Católica, San Jeronimo, Vía Vallejo) | Odoo from its start date (Section 3); Wansoft before |
| New, born on Odoo (Puebla, CentroMyJ and any branch opened later) | Odoo |
| **Antenas (temporary exception)** | Wansoft, while its Odoo database is repaired |

Odoo cost is computed from Odoo accounting (direct-cost accounts) and stored in
the same tables. It fills `CostoTotal`, `CostoDeProductosVendidos` and
`CostoDeMerma`; `CostoDeCortesías` and `CostoDeCancelaciones` come from the
cash closing; the other columns stay empty (no Odoo equivalent). **In Odoo rows the columns with no equivalent are NULL**: use `COALESCE(column, 0)`
when adding or subtracting, or the result is NULL (e.g. `CostoTotal - CostoDeConsumo`
is NULL for Puebla). The switch is
per day: days before the start date keep Wansoft's cost.

Keyed by `subsidiary_id` (Wansoft id). All three are **snapshots**:

| Table | One row = | How to read it |
|---|---|---|
| `costeomensual` | Month-to-date cumulative, from the 1st through `created_date` | Month total = the row with the latest `created_date` of that month |
| `costeomensual_semanapyq` | Week-to-date cumulative, Monday through the day **before** `created_date` | Week total = latest row of the week |
| `gettotalcostbydate` | Cost of sales of the single day `created_date` | Sum over days |

`mes_ano` is text `MM-YYYY`. Unique per (`subsidiary_id`, `created_date`).

Fields in `costeomensual` and how the owner's reports use them:

| Report figure | Formula |
|---|---|
| Costo Total | `CostoTotal - COALESCE(CostoDeConsumo, 0)` |
| Costo Teórico | `CostoDeProductosVendidos` |
| Gasto de Venta | `CostoDeConsumo` |
| Costo de Mermas | `CostoDeMerma` |
| Cortesías / Cancelaciones | `CostoDeCortesías`, `CostoDeCancelaciones` (sale value, from the cash closing) |

```sql
-- Month cost per branch: last snapshot of the month
SELECT c.subsidiary_id, c.subsidiary_name, c.created_date,
       c.CostoTotal - COALESCE(c.CostoDeConsumo, 0) AS costo_total,
       c.CostoDeProductosVendidos AS costo_teorico
FROM costeomensual c
JOIN (SELECT subsidiary_id, MAX(created_date) AS d
      FROM costeomensual
      WHERE created_date >= '2026-08-01' AND created_date < '2026-09-01'
      GROUP BY subsidiary_id) last ON last.subsidiary_id = c.subsidiary_id AND last.d = c.created_date;
```

**Butchery yields (`gettablajeriareport`) are being phased out.** They only exist for branches that enter purchases and inventory in Wansoft: new branches (Puebla, CentroMyJ) have none, and migrated branches will stop having them once they stop entering purchases in Wansoft. Odoo does not record butchery this way: it applies calculated yields, and at month end the real inventory is checked against the calculated one. Use this table only as history for Wansoft branches.

### 5.3 Purchases (Wansoft history + Odoo, merged)

**Use the analytics layer.** It already merges both sources with this rule per
branch:

- Branch purchasing in Wansoft: Wansoft invoices-type entries
  (`getinputinventory_entrada` with `TipoEntrada = 'Factura'`).
- Branch migrated to Odoo: Wansoft history **before** its Odoo start date
  (Section 3), then confirmed Odoo purchase orders (`state` purchase/done) from
  that date on. No overlap, no gap.
- Internal providers as buying company are excluded; a branch buying *from* an
  internal provider is kept.

`source_system` (`wansoft`/`odoo`) tells where each row came from;
`final_purchase_source_status` explains why it was kept (for example
`wansoft_history_before_odoo`).

| Table | Grain | Key fields |
|---|---|---|
| `analytics_purchase_order_lines` | purchase line | `company_source_key`, `order_date`, `vendor_name`, `product_name`, `wansoft_code`, `wansoft_department`, `product_qty`, `price_unit`, `price_subtotal` (before tax), `price_total` (with tax), `source_system` |
| `analytics_purchase_orders` | purchase order / invoice | same header fields plus totals |
| `analytics_purchase_daily_company_product` | branch × day × product | `business_price_subtotal_total`, `business_product_qty_total` (already business-filtered) |

Join to dimensions with `product_analytical_key` → `dim_product`,
`vendor_analytical_key` → `dim_vendor`, `company_analytical_key` →
`dim_company_analytical`, `order_date_key` → `dim_time.date_key`.

```sql
SELECT company_source_key, DATE_FORMAT(order_date, '%Y-%m') AS mes,
       source_system, SUM(price_subtotal) AS compras_sin_iva
FROM analytics_purchase_order_lines
WHERE include_in_business_views = 1
  AND order_date >= '2026-01-01'
GROUP BY company_source_key, mes, source_system;
```

Example: the migrated branches (Acoxpa, Antenas, Tepeyac, Oceanía, Coyoacán)
come back with `source_system = 'wansoft'` through September 2026 and with
`'odoo'` from October, with no month repeated or missing; Puebla and
CentroMyJ, born on Odoo, come back with `'odoo'` since they opened in June 2026.

**`getexpenses_factura` is a different thing:** every Wansoft supplier invoice
classified by accounting account (`Cuenta`: Costo operativo, Gastos de venta,
Gastos directos, Sueldos y salarios, Fletes, ...), including services, software
and payroll that are not goods. Odoo purchase orders only cover goods. So:
- For goods purchases across both systems, use the analytics layer.
- To compare with Wansoft's "Compras" reports, use only `Cuenta = 'Costo operativo'`.
- **Non-goods spend** (rent, services, software, payroll, freight...) of
  branches already operating on Odoo is **not** extracted from Odoo today. In
  `getexpenses_factura` those branches only have invoices up to their Odoo start
  date. From Odoo accounting only the cost of sales is taken (Section 5.2).

Some Wansoft invoices have an empty `Cuenta`. Amounts and dates in this table
are text. **`Estatus = 'Por pagar'` does not mean unpaid:** invoices are rarely
marked paid in Wansoft (payment is recorded elsewhere), so do not use that field
for accounts payable.

### 5.4 Inventory

- **Wansoft movements** (Wansoft branches, and history of migrated ones):
  `getinputinventory_entrada` (entries; `TipoEntrada`: `Factura`, `Transferencia`,
  `Entrada con canal`, `Producto procesado`, `Ajuste de inventario`) and
  `getoutgoinginventory_salida` (exits, ~37 million rows: always filter by
  `Fecha` and `subsidiary_name`). Branch = Wansoft id in `subsidiary_name`.
  Quantity `Cantidad`, cost `CostoUnitario`.
- **Current stock, unified:** `analytics_inventory_current_product_location`
  (Odoo stock by product and location) and `analytics_inventory_balance`
  (Wansoft balance = entries − exits by product). Filter
  `include_in_business_views = 1`.
- There is **no inventory valuation** (money) for Odoo branches yet, only
  quantities.

### 5.5 Zenput (`zenput` database)

| Table | Grain | Key fields |
|---|---|---|
| `form_templates` | checklist template | `form_id`, `title`, `category_name` |
| `submissions` | one filled checklist | `submission_id`, `form_template_id` → `form_templates.form_id`, `location_name`, `user_display_name`, `date_submitted` |
| `submission_answers` | one answer | `submission_id`, `title` (question), `field_type`, `value_as_string` |
| `zenput_tasks` | task | `task_id`, `title`, `account_name` (location), `status_name`, `assignee_display_name`, `date_due`, `is_closed`, `is_completed_late` |

`location_name` / `account_name` are Zenput's own location names, not the short
key; some Zenput locations have no POS branch.

### 5.6 Governance tables

- `dim_company_analytical`: one row per company, flags (`is_active_branch`,
  `is_internal_provider`, `is_final_operating_branch`), source per domain,
  `operational_start_date`.
- `analytics_company_domain_coverage`: which source feeds each domain per
  branch, with counts and a `coverage_status`.
- `dim_time`: calendar (`date_key` = `YYYYMMDD`), weeks, months, ISO weeks.

---

## 6. Do not use

| Tables | Why |
|---|---|
| `canonical_purchase_*`, `odoo_purchase_*`, `odoo_inventory_*` | Intermediate layers; the analytics tables are the business-ready result |
| `inventory_*`, `product_catalog_mapping`, `backup_product_catalog_mapping`, `product_replacement_candidates`, `stg_*` | Mapping and review workbench |
| `odoo_company_migration_policy`, `odoo_cutover_validation_log` | Pipeline control |
| `getinventorybydepartment`, `getstockinventory_inventario`, `getinventorybyday_*` | Old snapshots, not refreshed daily |
| `vw_inventory_*` | Diagnostic views |
| `tmp_*` | Temporary |

---

## 7. Freshness and schedule

- Daily pipeline at **01:30** (Mexico City time); data through the previous day.
- Rolling re-checks: sales 10 days (reconciled against Wansoft's own daily close),
  Wansoft costs/inventory/cash closing 5 days, purchases 35 days.
- Costs in Wansoft can be recalculated by Wansoft after the fact; the latest
  snapshot wins.
- Weekly backup Thursdays 18:00. Avoid heavy queries at 01:30–03:00.

## 8. Access

Access is through a dedicated **read-only** database user limited to the tables
in Sections 4–5, provided separately (credentials are never written in this
document). Query `getoutgoinginventory_salida` and the sales detail tables with
date filters: they hold tens of millions of rows. Each user is limited to 4
simultaneous connections and 30 minutes per query.
