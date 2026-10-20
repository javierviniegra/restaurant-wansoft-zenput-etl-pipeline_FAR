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

## Block 2: classification tables (built on dev 2026-10-20)

`scripts/seed_expense_mappings.py` (dry run by default, `--apply` writes) creates
and fills two governed tables from `seeds/expense_account_mapping_seed.csv` (93
account names decided by the owner) and `seeds/expense_vendor_rule_seed.csv` (72
vendors). The `analysis/*_20261019.csv` files are the review worksheets they came
from.

- **`expense_account_mapping`**, one row per Odoo account (`odoo_account_id`
  unique). Odoo keeps one account per company: Carnes is 16 accounts with 16 ids.
  Odoo **branches have no chart of their own**: Aeropuerto and Taquería Viaducto
  post to FONDA ARGENTINA AEROPUERTO's 305 accounts (same for Parroquia /
  Exhibimex under PERALTA Y LEON and Cancún under LA PARRILLADA ORIGINAL DEL SUR).
  So the seed reads the chart of each branch's root company; `company_source_key`
  is NULL for a shared holding chart, and the branch of a line comes from its
  bill's company. The November wave is classified from day 1.
- `mapping_status`: `approved` (cuenta / subcuenta / tipo_de_egreso),
  `product_category` (the goods clearing account: classify each line through its
  product category's expense account, company context), `vendor_rule` (use
  `expense_vendor_rule`), `excluded` (`exclude_reason`, here `advance`),
  `unclassified` (owner decided "Por clasificar"), `pending_review` (added
  automatically, waiting for the owner).
- **`expense_vendor_rule`**, one row per Odoo partner (`odoo_partner_id`
  unique), with RFC, `rule_status` (`approved` / `unclassified` /
  `pending_review`), `rule_source` (`owner_agreed` / `wansoft_vendor_history`) and
  the evidence.
- **Governance:** a re-run inserts new rows and updates only rows still in
  `pending_review`; owner decisions are never overwritten (second run on dev:
  0 inserted, 1,105 + 72 kept).

Dev result: 16 charts read, 4,982 accounts, **1,105 rows** matching all 93
decided names (approved 1,052, excluded 17, product_category 16, vendor_rule 16,
unclassified 4); 72 vendor rules (65 approved, 7 unclassified).

**Coverage check** (every posted bill line of the 10 operating branches since
2026-06-01, goods resolved through their category): approved 75.93 MDP,
vendor_rule 4.32 MDP, excluded -3.60 MDP (advance credit notes), unclassified
45 k; **not in the table: 6,330 MXN**, goods lines with no product. The owner
decided those are Costo de alimentos (block 1, F); that is a build rule for
block 5 ("goods line without product -> Costo operativo / Costo de alimentos"),
not an account row.

Production: not applied yet. Running the script on the tasks VM writes to the
live `wansoft` database (it creates the two tables; Odoo is only read).

## Block 3: Odoo vendor-bill extraction (built on dev 2026-10-20)

`extract/expenses/odoo_vendor_bills.py` (incremental by default, `--full` reads
everything again), same pattern as `extract/inventory/odoo_stock_moves.py`.
Companies: the group's (branches and internal providers, `group_companies`);
whole history, any state. Two raw tables:

- **`odoo_vendor_bill_snapshot`**, one row per `in_invoice` / `in_refund`
  (`odoo_move_id`): state, payment_state, `cfdi_uuid` + `cfdi_uuid_source`
  (`edi_field` / `ref`), `ref`, `payment_reference` (supplier folio), dates,
  vendor (commercial partner) name and RFC, amounts in company currency and
  **expense sign** (bills positive, credit notes negative), payment term,
  `reversed_entry_id`, `payment_count` and `last_payment_date` (from
  `matched_payment_ids`).
- **`odoo_vendor_bill_line_snapshot`**, its `product` and `tax` lines
  (`odoo_line_id`): account, product, product category and the category's
  expense account (company context), label, quantity, price, `amount` = balance
  (expense sign; IVA positive, withholdings negative), tax name / rate / group.

Incremental: bills written since the last load minus 3 days, **plus every
stored posted bill not settled yet** (`not_paid` / `partial` / `in_payment`),
because a payment does not always move the bill's `write_date`. A bill's lines
are deleted and rewritten each time it is read. `--full` also removes stored
bills that no longer exist in Odoo.

Dev results: full load **19,180 bills, 81,434 lines in 69 s**; incremental
2,681 bills (2,530 of them stored open bills) in 18 s. Checks:
- Acoxpa, September 2026, posted: 288 bills 4,110,155.44 and 4 credit notes
  -9,573.79, identical to the block 1 exploration.
- Every posted bill: product lines = `amount_untaxed` and tax lines =
  `amount_tax`, **0 differences**.
- Posted bills: UUID from `ref` 17,141, from the EDI field 434, none 841; 473
  without vendor RFC.
- Goods lines with no category account: 82 lines, all **without product**
  (the block 5 rule "Costo de alimentos"); most are Bodegón de Fito (internal
  provider, excluded) or Antenas in December 2025 (before its Odoo start).
- `last_payment_date` is missing on part of the paid bills (10,959 of 15,737):
  bills settled without an `account.payment` (statement reconciliation,
  compensation). `payment_state` stays the status signal; the date is
  informative.
- 9,307 bills belong to internal providers (`company_source_key` NULL); the
  analytics table excludes them as buying companies.

Not in production yet; it becomes a nightly stage in block 6.

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
    **Verified 2026-10-20 (Puebla, all dates):** an advance is a bill on the
    advance account (Amigo del Chef 2.29 MDP in March-May and July, Bodegón 1.44
    MDP in April, Situsmex 2.35 MDP in March, Nova SM, Wansoft) that is later
    cancelled by a credit note on the same account (July-August); the final
    supplier bill carries the full amount on its real account. Over all dates the
    advance account nets to 71 k (small items posted there and never reversed:
    lodging, Bodega Prissa, a cancelled Brownie bill). The -3.7 MDP seen since June
    is only the credit notes falling inside the window while their advance bills
    were earlier. So excluding **every line on the advance account, bills and
    credit notes alike**, is correct: the final bill counts once.
    "Liquidity Transfer" is **not** an advance: it is Nova SM's final oven bill
    (2026-06-15, 57,536, the same day its advance was cancelled) posted to a wrong
    account; excluding it would lose the oven. Owner, 2026-10-20: map it to
    `Inversión inicial / Equipo de restaurante`, the account where the opening
    ovens, ranges, dishwashers, fryers, griddles and fridges are booked. Only
    "Advance to national suppliers" and "Banorte 0144" stay `excluded_advance`.
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
- **2026-10-20:** the owner approved the 23 `suggested` rows and the automatic
  name matches; every mapped row is now `owner_confirmed`. "Other taxes and
  duties" (301 k at CentroMyJ) was checked: two payments to the Mexico City
  government, so `Otros Impuestos o Derechos` is right.
- **Mappings stay adjustable (owner, 2026-10-20).** Decisions live in the
  `expense_account_mapping` table (and the vendor-rule table), not in code; an
  edited row reclassifies the whole history at the next build of
  `analytics_expense_invoices`. Automatic runs only add new accounts as pending
  and never overwrite a human decision.
- Duplicate UUIDs: flag rule.
- Update `docs/data-access-guide/` (both languages, PDFs) and the tukanmx grants
  when the table exists.
