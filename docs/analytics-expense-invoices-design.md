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

## Block 1 findings: read-only Odoo exploration (2026-10-19)

Scope: `account.move` with `move_type in (in_invoice, in_refund)`, every company,
`invoice_date >= 2026-01-01` (12,989 moves); line analysis on the 10 branch
companies since 2026-06-01. Scripts were run from the dev PC against Odoo
(XML-RPC, read-only) and dev MySQL; nothing was written anywhere.

**Volumes (posted bills since each branch's real Odoo activity).** Born on Odoo:
Puebla from 2026-03 (opening capex; policy start 2026-06-10), CentroMyJ from
2026-01/03. Migrated in the June wave (Acoxpa, Antenas, Tepeyac, Oceanía,
Coyoacán): real bills from 2026-05/06, about 200-350 per month each; Antenas has
real bills since January. October wave (Isabel, San Jerónimo, Vía Vallejo): about
50 bills each in **September 2026** (Isabel 1.0 MDP, San Jerónimo 0.9 MDP) before
the 2026-10-01 start, then 90-120 in October. Routing by
`operational_start_date` keeps Wansoft before the start date, so these September
Odoo bills are not loaded (same rule as purchases). Other Odoo companies (Bodegón
de Fito, Empanadas de María Eva, Grupo Hospitalario Rodiva) are internal or out of
scope.

**Status.** Posted bills: `payment_state` in `paid`, `in_payment`, `not_paid`,
`partial`, `reversed`. `reversed` bills (≈70 since January) have a posted
`in_refund` that cancels them: loading both (refund as negative) nets to zero.
Cancelled bills (`state = cancel`) are a few per month per branch; drafts are rare.
Credit notes are material for some branches (Puebla: 2.35 MDP in April, 3.1 MDP in
August), so **`in_refund` is included as negative amounts**.

**CFDI UUID and supplier reference.** `l10n_mx_edi_cfdi_uuid` is almost always
empty (only part of Oceanía and Tepeyac). The team types the **UUID in `ref`**:
95-100% of posted bills per branch have a UUID-shaped `ref`. The supplier's folio
is in `payment_reference`. No CFDI XML is attached. Rule: `uuid =
COALESCE(l10n_mx_edi_cfdi_uuid, ref if it looks like a UUID)`; `folio =
payment_reference`. 19 UUIDs appear on more than one posted move (39 moves):
flag them (possible duplicate capture), do not drop them silently.

**Taxes.** Tax lines are only IVA 16% and withholdings (IVA and ISR retained on
rent, professional services, freight). **There is no IEPS tax in Odoo**: IEPS,
when present, is inside the line amount, so `ieps` is NULL for Odoo rows. New
column needed: `retentions` (Wansoft already has `Retentions`), so that
`total = subtotal + iva - retentions`.

**Accounts on lines.** Goods lines (≈22,000 lines, 29 MDP since June) post to the
clearing account "Goods Received - No Invoices"; resolving them through the
product category's expense account with company context (as in
`extract/purchases/odoo_purchase_category_totals.py`) classifies 99.98%
(6,330 MXN unresolved): 501.01.xx (Carnes 15.7 MDP, Con Alcohol 3.0, Frutas y
Verduras 2.0, Sin Alcohol 1.8, ...) and 504.01.xx (Gastos de Salón, Mat. de
Empaque, Art. de Limpieza, ...). Direct-expense lines carry their own account.

**Account names are not a key.** The same code has different names in different
companies (601.84.02 = "Renta de Equipo" and "Cash Difference Loss"; 601.84.24 =
"Soporte técnico" and "Finiquito (copia)..."; 601.56.05 = "Mantenimiento ABR" and
"Mtto Eq. De Restaurante (copia) (copia)"). `expense_account_mapping` must be
keyed by the **Odoo account id** (per company if needed), with name and code kept
for review.

**"Other overheads" (601.84.01), 4.3 MDP since June.** 271 lines without a
product: food from Sigma and Bodegón de Fito, rent, legal services, CFE, armoured
transport. The account says nothing about the expense; it cannot be mapped by
account. Owner decision needed (vendor-based rule, or a "por clasificar" bucket).

**Crosswalk proposal.** `analysis/expense_account_mapping_proposal_20261019.csv`
(93 account names): 37 automatic name matches (27.6 MDP), 26 suggested (32.8 MDP,
mostly the 501.01 cost accounts -> Costo operativo / Costo de alimentos or
bebidas), 30 for the owner (15.0 MDP: capex such as Equipo de restaurante 8.4 MDP
and Gastos de Instalación 4.7 MDP, Other overheads, Advance to national suppliers
-3.7 MDP, bank/transfer accounts, Mantenimiento ABR, Soporte técnico, Servicios
de Logística, ...). A Wansoft `Subcuenta` used under two `Cuenta` values is
proposed with its most used `Cuenta` since 2025; the other uses are listed.

## Open points

- Owner decisions on the crosswalk (`owner_decision` rows and every `suggested`
  row). **Decided 2026-10-19:** every 504.01 account (Gastos de Salón, Carbón,
  Art. de Limpieza, Mat. de Empaque, Hielo, Gas, Cristalería y Loza, Manteletas,
  Utensilios, Equipo de Salón, Equipo de Protección) is `Gasto / Gastos de
  venta`, also for goods bought through purchase orders (Art. de Limpieza ->
  `Gastos de venta / Articulos de Limpieza`, not `Gastos Directos`). Rows marked
  `owner_confirmed` in the proposal CSV. Servicios de Logística (504.01.14) is a
  service and stays open.
- **Owner decisions on the 30 open accounts (2026-10-19)**, applied in the
  proposal CSV (`owner_confirmed` unless said otherwise):
  - A. Opening investment: Equipo de restaurante, Gastos de Instalación y/o
    remodelación, Equipo de cómputo, Mobiliario y equipo de oficina, Equipo de
    comunicación -> new bucket `TipoDeEgreso = Inversión`, `Cuenta = Inversión
    inicial`, `Subcuenta` = the Odoo account name (13.2 MDP since June, almost all
    Puebla and CentroMyJ). "Dep eq de restaurante" (one 7.5 k bill, Tepeyac) ->
    `Gastos Directos / Mantto. Eq. de Restaurante`.
  - B. Advances: "Advance to national suppliers", "Banorte 0144" (applied April
    advances) and "Liquidity Transfer" (the counterpart of a Nova SM advance) are
    `excluded_advance`: advance-application lines are left out so the final bill
    counts once. **To verify while building:** the advance bills themselves
    (Puebla, March-May 2026, about 3.9 MDP in 4 bills) must not also be loaded as
    expenses.
  - C. "Other overheads" is `vendor_rule`: classified per vendor,
    `analysis/expense_vendor_rules_other_overheads_20261019.csv`. Agreed by the
    owner: Sigma -> Costo de alimentos, Inmobiliaria Gocos -> Arrendamiento PM,
    Gerila -> Honorarios PM. Every other vendor takes its most used Wansoft
    `Cuenta` / `Subcuenta` by RFC since 2025 (Bodegón de Fito -> Costo de alimentos,
    12,461 of 16,462 invoices); vendors with no Wansoft history (CFE 21 k, La Cava
    de James 13 k, a few at zero) stay "Por clasificar" with an alert. Known
    imperfection: Bodegón's imported chairs (208 k) land in Costo de alimentos.
    Accounting should be told that bills are being captured without product or
    account.
  - D. Mantenimiento ABR (it is the vendor ABR Servicio y Hospitalidad) and
    Materiales para Mantenimiento -> `Gastos Directos / Mantenimiento del Local`;
    Servicios de Logística (both spellings) -> `Fletes / Flete PM`; Soporte técnico
    (three spellings), "Finiquito (copia)..." (Vía Vallejo, same IT vendor) and Mtto
    Eq. de Oficina y Cómputo -> `Gastos por servicios / Otros`; Peaje, transporte,
    taxi -> `Viáticos / Viáticos`.
  - E. Cash Difference Loss (really refrigerated storage) -> `Gastos por servicios
    / Otros` (Wansoft has no `Gastos Directos / Otros`); Foreign exchange loss and
    Comisiones Bancarias -> `Gastos financieros / Otros`; the three "Recibos
    Pendientes" bank accounts -> `por_clasificar`.
  - F. Discounts and returns on purchases (mostly wine vendors) -> `Costo
    operativo / Costo de bebidas` as negatives; Variaciones de Inventario and the
    goods lines with no category -> `Costo operativo / Costo de alimentos`.
- Still to review by the owner: the 23 `suggested` rows (mostly 501.01 cost
  accounts to Costo de alimentos / bebidas).
- Duplicate UUIDs: flag rule.
- Update `docs/data-access-guide/` (both languages, PDFs) and the tukanmx grants
  when the table exists.
