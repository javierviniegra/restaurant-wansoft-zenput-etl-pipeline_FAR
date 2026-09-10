# Power BI Source Migration — Raw Tables to Unified Analytics Tables

## Purpose

This document maps each raw/legacy table currently used in Power BI to its
replacement in the unified analytical layer (all 19 branches combined,
Wansoft + Odoo, one table per domain). Use it to repoint Power BI data
sources.

**Status as of 2026-09-08: do not switch yet.** The Purchases analytics
tables below are confirmed stale (see "Known gap" section) — they need a
fresh rebuild and to be added to the daily scheduler before they can be
trusted as a Power BI source. Inventory is already scheduled daily and
safe to use today.

---

## Purchases

| Today (Power BI reads this) | Replace with | Covers |
|---|---|---|
| `getexpenses_factura` (Wansoft only) | `analytics_purchase_orders` (order/invoice level) | All 19 branches, Wansoft + Odoo combined |
| — (no line-level equivalent today) | `analytics_purchase_order_lines` (line level, if you need product detail) | Same |
| — | `analytics_purchase_daily_company_product` (daily company+product aggregate, if you need a pre-aggregated fact for performance) | Same |

**Recommended filter for both:** `include_in_business_views = 1` — this
already excludes internal-provider vendors (El Bodegón de Fito, Las
Empanadas de María Eva), review-required rows, and orphan product lines.
Without this filter you'll double-count or include rows that shouldn't
appear in a branch-level report.

**Key columns on `analytics_purchase_orders`:**
```
company_source_key       -- branch name, use this to filter/group by branch
source_system             -- 'wansoft' or 'odoo' (which system this row came from — informational, not needed for filtering once include_in_business_views is applied)
order_date                -- date
vendor_name                -- normalized vendor
price_total_total          -- order total amount
price_subtotal_total       -- order subtotal (pre-tax)
line_count / business_line_count  -- how many lines, and how many after business-view exclusions
include_in_business_views  -- filter to 1
```

**Key columns on `analytics_purchase_order_lines`** (same governance
columns as above, plus):
```
product_name / wansoft_code / wansoft_product_name / wansoft_department
product_qty / price_unit / price_subtotal / price_total
include_product_in_business_views  -- also filter to 1 if using line-level product detail
```

**How a branch's Purchases total is assembled internally** (for context,
you don't need to replicate this in Power BI — the analytics tables
already resolve it): for a branch still on Wansoft, all rows come from
Wansoft (`final_wansoft_enabled`). For a branch migrated to Odoo, rows
before its cutover date stay Wansoft-sourced (`wansoft_history_before_odoo`)
and rows from the cutover date onward are Odoo-sourced
(`final_odoo_enabled`) — no double-counting, `include_in_business_views`
already resolves which one wins per date.

### Known gap (2026-09-08)

`analytics_purchase_orders` and `analytics_purchase_order_lines` are built
by standalone scripts (`scripts/build_analytics_purchase_order_lines.py`
→ `scripts/build_analytics_purchase_orders.py` →
`scripts/build_analytics_purchase_daily_company_product.py`) that are
**not** part of the automated daily pipeline or scheduler. Confirmed stale
today: Puebla has real canonical data (62 orders, ~$480K in the last 10
days) but zero rows in `analytics_purchase_orders`. These three scripts
need to be run manually (in that order) to refresh, and should be added
to `pipelines/scheduler.py` right after the Purchases canonical refresh
(currently at 13:30) before this is safe to use as a live Power BI source.

---

## Inventory

| Today (Power BI reads this) | Replace with | Covers |
|---|---|---|
| `getstockinventory_inventario` / raw entrada+salida tables | `analytics_inventory_balance` (current stock balance per product per branch) | All 19 branches, confirmed present for every branch as of 2026-09-08 |
| — | `analytics_inventory_snapshot` (point-in-time snapshot with location detail, if you need warehouse/location breakdown) | Odoo-sourced branches (location-level detail is an Odoo concept; Wansoft branches don't have this granularity) |

**Recommended filter:** `include_in_business_views = 1` — excludes
virtual/partner locations (Odoo adjustment and production accounts, not
real physical stock) and unmapped products pending manual review.

**Key columns on `analytics_inventory_balance`:**
```
company_source_key    -- branch name
wansoft_code / product_name
entrada_qty / salida_qty / current_balance_qty
source_system          -- informational
include_in_business_views  -- filter to 1
```

**Status:** this table IS already scheduled daily (`inventory_pipeline_job`,
1pm) as part of last week's work — safe to use as a Power BI source
today, no known gap.

---

## Sales

**No change needed.** Sales is always Wansoft-sourced for all 19 branches
(there is no Odoo sales source in this project — see
`core/config/companies.py`, `ALWAYS_WANSOFT_DOMAINS = {"sales"}`). Keep
reading from `getallordenesbyday_new_venta` (and
`getglobalcashclosing`/`costeomensual_semanapyq` for cash-close and
cost-linked sales figures) as you do today. There is nothing to unify
here since only one source system is ever involved.

---

## Costs

**No unified analytics table exists yet for Costs.** Keep reading from
the existing raw tables (`costeomensual_semanapyq`, `costeoMensual`,
`getglobalcashclosing`, `gettablajeriareport`, `getTotalCostByDate`) as
you do today. Costs combines Wansoft and Odoo differently per sub-metric
(see `docs/production-orchestration-plan.md`, "Costs architecture") and
was out of scope for this round of work. If you want a single unified
Costs table later, that would be a new project (mirroring the Purchases
canonical-layer pattern), not something that already exists.

---

## Summary — what to actually do

1. **Inventory:** safe to repoint Power BI to `analytics_inventory_balance`
   now.
2. **Purchases:** wait. Ask to have the three `analytics_purchase_*`
   build scripts run once manually and added to the scheduler first,
   then repoint to `analytics_purchase_orders` (or
   `analytics_purchase_order_lines` for product-level detail).
3. **Sales and Costs:** no change, keep current sources.
