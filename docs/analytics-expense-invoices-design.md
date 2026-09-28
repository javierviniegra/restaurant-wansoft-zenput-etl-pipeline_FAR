# analytics_expense_invoices — design (to build after the 2026-10-01 cutover)

Status: design agreed with the owner on 2026-09-28; not built yet.

## Goal

One analytical table that **replicates the content of `getexpenses_factura`**
(every supplier invoice, classified by accounting `Cuenta` / `Subcuenta`) for
**all** branches, whatever system they buy in:

- Branch buying in Wansoft: rows from `getexpenses_factura`.
- Branch migrated to Odoo: `getexpenses_factura` **before** its Odoo start date
  (`odoo_company_migration_policy.operational_start_date`), Odoo vendor bills
  from that date on.
- Branch born on Odoo (Puebla, CentroMyJ, every future one): Odoo only.

Why: today only goods (purchase orders) and cost of sales come from Odoo. Non-goods
spend (rent, advertising, services, software, maintenance, payroll, freight) of
branches on Odoo exists nowhere in the warehouse after their start date, and from
the cutover the pipeline no longer downloads Wansoft invoices for them at all.

## Owner decisions (2026-09-28)

| Topic | Decision |
|---|---|
| Which Odoo bills | Every posted vendor bill (`move_type = 'in_invoice'`, `state = 'posted'`), paid **and** unpaid, like Wansoft's "Por pagar" + "Pagada". Cancelled bills excluded (Wansoft: `Rechazada` excluded) |
| Payment status | Kept current: when a bill becomes paid, its row must change |
| Date | Invoice date (`invoice_date` in Odoo = `FechaDeExpedicion` in Wansoft), as in the owner's "Compras Mensuales" report |
| Scope | Everything, goods included (flagged), so the table mirrors `getexpenses_factura`; product-level goods stay in `analytics_purchase_*` |
| When | After the cutover (from Friday 2026-10-02); not part of the Thursday migration |

## Findings that shape the design

**Wansoft (`getexpenses_factura`, production, invoices since 2019-02-18).** One row
per invoice with a single `Cuenta` / `Subcuenta`. Since 2025: `Costo operativo`
405 MDP (Costo de alimentos 333, Costo de bebidas 65, Costo de operación 7);
everything else about 190 MDP: Gastos Directos 78 (Management Administrativo 43,
Mantenimiento del Local 9, Energía Eléctrica 7...), Sueldos y Salarios 38, Renta de
Local 36 (Arrendamiento PM 30, PF 6), Gastos de venta 29 (Carbón, Gastos de Salón,
Hielo, Gas...), Gastos por servicios 6, and smaller buckets; 516 rows with an empty
`Cuenta`. `TipoDeEgreso` is `Costo de producción` (= Costo operativo) or `Gasto`.
Amounts and dates are text.

**Wansoft status is not a payment signal.** `Estatus` is `Por pagar` / `Pagada` /
`Rechazada`, but invoices are rarely marked paid in Wansoft: for Aeropuerto all
5,867 rows stored as "Por pagar" (4,646 older than June 2026, some from 2023) are
still in Wansoft's live pending list (`GetPendingExpenses_Xml`, 13,219 pending
documents). The warehouse mirrors Wansoft correctly; the guide must say that
"Por pagar" in Wansoft does not mean unpaid. Today `getExpenses.py` only refreshes
invoices dated in the last `WANSOFT_LOOKBACK_DAYS` (5).

**Odoo vendor bills (Acoxpa, August 2026, read-only check).** 297 bills: 245 paid,
11 in payment, 20 not paid, 1 reversed, 20 cancelled. Posted lines by account:
goods lines use the clearing account "Goods Received - No Invoices" (1.82 M, all
linked to purchase orders); direct expenses carry their own account: Publicidad y
Propaganda 645 K, Arrendamiento PM 507 K, Management Administrativo 380 K, Mtto
del Local 259 K, Asesorías 170 K, Gastos de Salón, Carbón, Mat. de Empaque, Art. de
Limpieza, Energía Eléctrica, Gas, Teléfono... Many Odoo account names equal Wansoft
`Subcuenta` names. `payment_state` is reliable.

**Reusable code.** `ControlPresupuestos_AP/scripts/scheduler.py` already reads
Odoo vendor bills (`account.move` in_invoice, lines from `account.move.line`,
payment dates via `reconciled_payment_ids`, incremental by `write_date` with a
monthly full run). For goods lines it resolves the real expense account through
the product category; `extract/purchases/odoo_purchase_category_totals.py`
documents the gotcha: `property_account_expense_categ_id` is company-dependent and
must be read with an explicit company context. Reuse the approach, not the
project (read-only; never touch ControlPresupuestos_AP).

## Proposed shape

Grain: one row per invoice × `Cuenta` / `Subcuenta`. A Wansoft invoice is one row;
an Odoo bill whose lines map to several buckets becomes one row per bucket (header
fields repeated, amounts summed from its lines).

Columns (mirroring `getexpenses_factura`, typed properly):
`company_source_key`, `source_system` (`wansoft`/`odoo`), `source_document_id`
(IdDocumento / account.move id), `folio` (Folio / bill reference), `uuid` (CFDI UUID;
Odoo field to confirm), `vendor_rfc`, `vendor_name`, `vendor_key`,
`invoice_date`, `due_date`, `payment_terms`, `cuenta`, `subcuenta`,
`tipo_de_egreso`, `source_account_name` (Odoo account or Wansoft Cuenta),
`subtotal`, `iva`, `ieps`, `total`, `status` (normalised: Por pagar / Pagada),
`source_status` (raw), `payment_date` (Odoo), `purchase_order_ref` (IdOrdenCompra /
invoice_origin), `is_goods`, `final_expense_source_status`,
`include_in_business_views`, `exclude_reason`, `loaded_at`, `updated_at`.

Rules: routing by `odoo_company_migration_policy` exactly as purchases; exclude
`Rechazada` / cancelled; internal providers as the buying company excluded (same as
purchases); rows with an empty Wansoft `Cuenta` kept, flagged for review.

Classification: new table `expense_account_mapping` (Odoo account name →
`cuenta`, `subcuenta`, `tipo_de_egreso`, `mapping_status`), seeded by normalised
name match against Wansoft `Subcuenta` values, the rest reviewed by the owner
(same governance as the product mapping dictionary: a re-run never overwrites a
human decision).

Status refresh:
- Odoo: daily incremental read of bills with recent `write_date` (catches bills
  paid later), plus a periodic full pass.
- Wansoft: daily `GetPendingExpenses_Xml` per Wansoft branch; stored "Por pagar"
  rows no longer in the pending list become "Pagada". About 10 MB per branch.
  **Never call** `MarkExpenseAsPaid_*` or `UpdateExpensesDownloadStatus_*`: they
  write to Wansoft.

## Validation plan

Reproduce the owner's Power BI "Compras Mensuales" by `Cuenta` for one Wansoft
branch (exact), then for a migrated branch across its Odoo start month (Wansoft
before, Odoo after), then a born-on-Odoo branch. Spot-check Odoo status changes
over a few days.

## Open points

- Odoo field holding the CFDI UUID and supplier reference.
- IEPS on Odoo lines (tax breakdown).
- Whether some Odoo accounts have no Wansoft equivalent (e.g. Publicidad y
  Propaganda, Asesorías, No deducibles) and need new buckets agreed with the owner.
- Credit notes (`in_refund`) in Odoo: probably include as negatives.
- Update `docs/data-access-guide/` (both languages, PDFs) and the tukanmx grants
  when the table exists.
