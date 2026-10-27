# Unified inventory tables: movements and daily stock (design)

Status: **steps 1-3 live in production since 2026-10-14** (`analytics_inventory_movements`,
40.6 M rows, validator PASS); step 4 next. Design agreed with the owner on 2026-10-10. Build
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

One row = one inventory movement of one product in one branch. **Structure
approved by the owner on 2026-10-13 (block 3b):**

```sql
CREATE TABLE analytics_inventory_movements (
  movement_key              BIGINT AUTO_INCREMENT PRIMARY KEY,
  movement_date             DATE NOT NULL,
  company_source_key        VARCHAR(100) NOT NULL,
  source_system             VARCHAR(10)  NOT NULL,   -- wansoft / odoo
  source_record             VARCHAR(20)  NOT NULL,   -- wansoft_entrada / wansoft_salida / odoo_move
  source_movement_id        VARCHAR(80)  NOT NULL,
  captured_date             DATE NULL,
  direction                 CHAR(3)      NOT NULL,   -- in / out
  movement_type             VARCHAR(20)  NOT NULL,
  source_movement_type      VARCHAR(100) NULL,
  wansoft_code              VARCHAR(50)  NULL,
  odoo_product_id           INT          NULL,
  product_name              VARCHAR(255) NULL,
  unit_name                 VARCHAR(50)  NULL,
  quantity                  DECIMAL(18,6) NOT NULL,  -- signed: + in, - out
  unit_cost                 DECIMAL(18,6) NULL,
  total_cost                DECIMAL(18,4) NULL,      -- signed
  location_name             VARCHAR(255) NULL,
  counts_in_stock           TINYINT(1)   NOT NULL,
  final_source_status       VARCHAR(40)  NOT NULL,
  include_in_business_views TINYINT(1)   NOT NULL,
  loaded_at                 DATETIME     NOT NULL,
  UNIQUE KEY uq_movement (source_record, company_source_key, source_movement_id),
  KEY idx_company_date (company_source_key, movement_date),
  KEY idx_product_date (wansoft_code, movement_date),
  KEY idx_captured (source_system, captured_date)
);
```

| Column | Meaning |
|---|---|
| `movement_date` | business date (Wansoft: `FechaEntrada` / `COALESCE(NULLIF(Fecha,'0000-00-00'), FechaReal)`; Odoo: `stock.move.date` in Mexico City time) |
| `company_source_key` | branch |
| `source_record`, `source_movement_id` | the source row, with the same identity the loaders use: Wansoft entries `IdEntrada` (unique per branch), Wansoft exits `Fecha` + `IdSalida` (the exits table's unique key), Odoo `stock.move` id |
| `captured_date` | when the source captured it (Wansoft `FechaEntrada`/`FechaSalida`, Odoo `write_date`); drives the nightly window |
| `direction` | `in` / `out` |
| `movement_type` | normalized: `purchase_receipt`, `sale_consumption`, `sale_cancellation`, `waste`, `theft`, `consumption`, `production_in`, `production_out`, `transfer_in`, `transfer_out`, `adjustment`, `initial_inventory`, `other` (Wansoft catalog below) |
| `source_movement_type` | the original: Wansoft `TipoEntrada`/`TipoSalida`; Odoo operation type and source/destination location usage |
| `wansoft_code`, `odoo_product_id`, `product_name`, `unit_name` | product; Odoo rows get `wansoft_code` from the approved `inventory_mapping_dictionary` rows |
| `quantity` | signed (+ in, − out), in the product's unit (Odoo `done_qty`) |
| `unit_cost`, `total_cost` | Wansoft `CostoUnitario`; Odoo `stock.valuation.layer` (unit cost and value) |
| `location_name` | warehouse / kitchen when known |
| `counts_in_stock` | whether it moves the stock balance, with the rules already used by `analytics_inventory_balance` (Wansoft catalog below; Odoo: storable products only) |
| `final_source_status`, `include_in_business_views` | as above |

**Decisions of 2026-10-13 (owner):**

1. **No `product_analytical_key` per row** (written down only, no change to
   other tables): `dim_product` has repeated Wansoft codes and would fan out
   rows, as the balance builder already warns. Consumers join the dimensions
   by `wansoft_code` / `odoo_product_id`. Also saves space on ~41 M rows.
2. **Odoo moves between two locations of the same branch (Almacén →
   Cocina) are not stored.** In Odoo such a transfer is one `stock.move`; it
   generates no separate entry or exit, and it does not change the branch's
   stock. What the kitchen then consumes are other moves, which are stored.
   The raw move stays in `odoo_stock_move_snapshot`. Moves between branches
   (or through transit) are stored as `transfer_out` / `transfer_in` of each
   branch. Wansoft "Transferencia" rows are already separate entries and
   exits and stay, with `counts_in_stock` = 0.
3. **Odoo moves of a migrated branch before its Odoo start date** (they
   captured in Odoo in parallel since June) are kept as
   `odoo_parallel_before_start`, `include_in_business_views` = 0; the
   mirror of `wansoft_parallel_after_odoo`.
4. **Nightly reload:** Wansoft rows are deleted and reinserted by
   `captured_date` over the last 10 days (an adjustment captured today with a
   business date weeks ago is not missed); Odoo and the parallel Wansoft
   inventory (small) are rebuilt in full. The September rows that exist only
   in the parallel tables enter once, through the unique key.

**Sources and sizes (2026-10-13, production):** Wansoft entries 1.85 M rows,
exits 37.5 M; Odoo done `stock.move` about 1.6 M for the group's companies,
with `stock.valuation.layer` for the value. About 41 M rows, ~10 GB on the
database server (243 GB free on 2026-10-13).

**Odoo movement direction**, from the branch's point of view: `in` when the
destination location is an internal location of the branch, `out` when the
source is; typed by the other side's usage (supplier → `purchase_receipt`,
customer → `sale_consumption`, inventory → `adjustment`/`waste` (scrap),
production → `production_in/out`, another branch or transit →
`transfer_in/out`). To be confirmed against real moves when building.

## Product code for both systems (owner, 2026-10-14)

`product_code` = the Wansoft code, or a temporary `ODOO-<odoo_product_id>`
while the Odoo product has no approved mapping; `product_code_status` =
`wansoft`, `temporal_odoo` or `sin_codigo` (a Wansoft row without code).
Both are generated columns, so an approved mapping reaches every row of the
product on the next rebuild of the Odoo side. `wansoft_code` keeps only real
Wansoft codes. The product index is on `product_code`.

**Weekly name matcher** (`scripts/match_odoo_products_by_name.py`, run on
Sundays by the product-mapping job after its own step): Odoo products with a
temporary code are compared with the live Wansoft catalog (`dim_product` +
`getinputinventory_entrada`) by normalized name (lower case, no accents,
punctuation, Odoo code in brackets or "(copia)"). Equal name and exactly one
Wansoft code -> `approved`; shared words (score >= 0.5) -> `pending_review`
in the workbook `reports/inventory_mapping_review/emparejamiento_odoo_wansoft_<date>.xlsx`;
the rest are listed. It never adds a second approved code to an Odoo
product (bug #44), fills the Odoo id of old approved rows that lacked it, and
re-points a row rejected on 2026-10-13 for its wrong Odoo id when the names
are equal (history kept in `notes`). The old weekly job only looks at Odoo
products that are sold (`sale_ok`) and uses a Wansoft catalog frozen in
2024, which is why supplies such as Lomo or Jitomate were never proposed.

Dev result (2026-10-14): before, 205,234 of the counting Odoo rows (521
products) had no Wansoft code; after one run, 48,398 (319 products): 84%
coded. 289 approved, 26 re-pointed, 147 for review. Purchase lines
identical before and after (46,529 lines, same total to the cent).

## Wansoft movement-type catalog (block 3a, owner approved 2026-10-13)

Measured in production on 2026-10-13 (full history, read-only). `counts_in_stock`
replicates `analytics_inventory_balance` exactly, so today's stock still
matches it; only the `movement_type` labels were new decisions.

Entries (`getinputinventory_entrada.TipoEntrada`, 1.85 M rows):

| TipoEntrada | Rows | `movement_type` | `counts_in_stock` |
|---|---|---|---|
| Factura | 797,522 | `purchase_receipt` | 1 |
| Transferencia | 443,126 | `transfer_in` | 0 |
| Entrada con canal | 307,180 | `production_in` | 1 |
| Ajuste de inventario | 157,276 | `adjustment` | 1 |
| Producto procesado | 87,372 | `production_in` | 1 |
| Orden de compra a proveedor | 46,588 | `other` | 0 |
| Inventario inicial | 8,200 | `initial_inventory` | 1 |
| Eliminado por ajuste de lote | 2,513 | `adjustment` | 1 |
| Anulación | 73 | `other` | 1 |
| Ajuste por lote | 57 | `adjustment` | 1 |
| Cancelación de transferencia | 7 | `other` | 1 |
| Devolución | 2 | `other` | 1 |

Exits (`getoutgoinginventory_salida.TipoSalida`, 37.5 M rows):

| TipoSalida | Rows | `movement_type` | `counts_in_stock` |
|---|---|---|---|
| Venta | 35,559,459 | `sale_consumption` | 1 |
| Transferencia | 566,572 | `transfer_out` | 0 |
| Producción de subproducto | 534,511 | `production_out` | 1 |
| Merma | 224,056 | `waste` | 1 |
| Producción de subproducto con canal | 221,763 | `production_out` | 1 |
| Consumo | 178,858 | `consumption` | 1 |
| Ajuste de inventario | 174,200 | `adjustment` | 1 |
| Venta cancelada | 24,239 | `sale_cancellation` | 1 |
| Ajuste por lote | 2,867 | `adjustment` | 1 |
| Error de captura | 1,977 | `other` | 0 |
| Desperdicio | 1,394 | `waste` | 1 |
| Devolución de producto | 699 | `other` | 1 |
| Registro de nota de crédito | 618 | `other` | 1 |
| Factura de egresos rechazada | 349 | `other` | 0 |
| Robo | 40 | `theft` | 1 |

Owner's decisions: **"Venta cancelada" subtracts stock** (confirmed again; first
decided 2026-08-21: the ingredients were cooked and lost; 24,239 rows, all
positive, $973 k of cost in five years, 0.1% of Venta) with its own type
`sale_cancellation`; **Robo gets its own type `theft`**; the rest as
proposed. "Entrada con canal" and "Producto procesado" are the entry side of
production: their cost matches their paired exits ($526 M vs $528 M, $43.6 M
vs $43.7 M). A `TipoEntrada`/`TipoSalida` not in these tables maps to `other`
with `counts_in_stock` = 1 (the balance's default) and is reported by the
build.

**September gap found (2026-10-13):** the parallel tables hold 12,290 exits
and 329 entries of the 8 migrated branches dated before 2026-10-01 that are
not in the main tables (captured in Wansoft after the main load stopped for
those branches). `wansoft_history_before_odoo` must read both tables,
deduplicated by branch + date + `IdSalida` (exits) / `IdEntrada` + product
(entries).

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

**Size measured in production (2026-10-26, read-only):** 14,280 branch ×
product pairs; **18.1 M rows** keeping every day from each product's first
movement to yesterday (the 2026-10-10 estimate was about 12 M), 13.6 M keeping
only days with stock or a movement, 4.6 M change days. **Owner, 2026-10-26:
keep every day, zero-stock days included** (option A): a missing row never means
zero, so averages and counts over days cannot silently go wrong; about 1 GB more
than skipping zeros, and WansoftServer has well over 200 GB free.
Build: `scripts/build_analytics_inventory_stock_daily.py` (`KEEP_ZERO_DAYS = True`).
Columns as built: `stock_date`, `company_source_key`, `product_code` (the same
common code as the movements), `source_system`, `product_name`, `stock_qty`,
`stock_value`, `moved_qty` (net movement of that day), `final_source_status`,
`include_in_business_views`, `built_at`.

## Odoo stock rebuilt from moves: findings and rule (2026-10-12)

Step 1 loaded every done `stock.move` of the 19 group companies (1,616,098)
into `odoo_stock_move_snapshot` and rebuilt Odoo's stock from them against
the production capture of stock date 2026-10-11. What it takes to match
Odoo's own stock:

1. **Only storable products** (`product.product.is_storable`; this Odoo has
   `type` `consu` for both). Consumables (paper napkins...) are received and
   delivered but never stocked.
2. **The quantity done in the product's unit**: `stock.move.quantity` is in
   the move's unit (recipes consume grams of an onion bought in kg) and
   `product_qty` is the demand; `done_qty` = quantity converted with Odoo's
   unit factors.
3. **Compare per branch × product**, summing every internal location of the
   branch: a move names the branch's general location (`FAACX/Existencias`)
   while the stock sits in sub-locations (Almacén, Cocina...), which only the
   move lines carry.

4. **Only the moves that existed at the capture**: Odoo moves are often
   registered later with an earlier effective date (on 2026-10-12, 1,020
   Acoxpa moves, 60 Oceanía, 41 CentroMyJ were dated before the 01:52
   capture but written after it). They belong to their day, but the capture
   could not include them.

Result (reload of 2026-10-12 with `done_qty` and `product_is_storable`,
1,616,472 moves): **exact (0 differences) for 9 of the 10 branches**:
Isabel, San Jerónimo, Vía Vallejo, Oceanía, Tepeyac, Coyoacán, Puebla,
Acoxpa and CentroMyJ. Only **Antenas** (the 2024 prototype, 336 of 374
products) carries stock values in Odoo that are not the sum of its own move
lines (for example "Moneda Ovalada Leyenda Fonda": move lines −480, Odoo
stock +119); Odoo itself is inconsistent there, the extraction is complete.
The internal providers (El Bodegón 32, Las Empanadas 10 products) also
differ; they are not branches.

**Rule (owner, 2026-10-12): Odoo daily stock is rebuilt BACKWARDS from
Odoo's latest daily capture.** Stock on day D = the latest capture
(`odoo_inventory_quant_daily`, from stock date 2026-10-08 on) minus the net
`done_qty` of the moves dated after D up to that capture. Every night the
recent days are recomputed from the new capture, so moves registered late
with an earlier date land on their day, today's stock is always exactly
Odoo's, and Antenas' inconsistency stays out of the daily series. For the
nine consistent branches it equals the forward sum.

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
   **Built 2026-10-12:** `WANSOFT_INVENTORY_PARALLEL=1` makes
   `getInputInventory.py` / `getOutgoingInventory.py` load the branches on
   Odoo into `wansoft_parallel_inputinventory_entrada` /
   `wansoft_parallel_outgoinginventory_salida` (the exits table carries the
   unique key `uq_subsidiary_fecha_idsalida` the upsert needs); nightly
   stages "Inventario paralelo Wansoft - entradas/salidas"
   (`pipelines/jobs/parallel_inventory_job.py`). Dev test from 2026-09-29:
   5,327 entries and 134,656 exits of the 8 branches, a second run changed
   nothing, the main tables got no row of them.
3. **`analytics_inventory_movements`**: one-off backfill, then a nightly
   window; new nightly stage. **Live 2026-10-14**: backfill 40.6 M rows in
   about 2.5 h on the VM; stages "Inventario Odoo - movimientos" and
   "Inventario - movimientos unificados"; capture-date indexes on the Wansoft
   tables (`sql/migrations/inventory_capture_date_indexes.sql`, 2026-10-16).
   The build also publishes `analytics_odoo_product_code`, the Odoo product ->
   Wansoft code equivalence it uses (consumers' table, 2026-10-16). Next
   improvement: an incremental Odoo side (the full nightly rebuild of 1.15 M
   rows takes about 12 min in production).
4. **`analytics_inventory_stock_daily`** from the movements. **Built on dev
   2026-10-26** (`scripts/build_analytics_inventory_stock_daily.py`): `--full`
   builds a new table by branch and swaps it in (a grid product x calendar day
   plus a running sum; Napoles 1.3 M rows in about 4.5 minutes on dev, so about one
   hour for all 18 M); the nightly mode updates the live table in place: per
   branch, the Wansoft days from the oldest day the movements' nightly window
   touched (seeded with the stored stock of the day before) and the whole Odoo
   series, 5-12 s per branch. Stage "Inventario - existencias diarias" after
   "movimientos unificados". Validated with full history copied from production
   (Napoles, La Esquina Coyoacan, CentroMyJ): no gaps; Napoles' last day = the
   balance for 862/862 products; latest Odoo capture = sum of Odoo's own moves
   (200/200, 331/332), older captures differ only by moves registered later; the
   nightly mode reproduces the full build with 0 differences (also after deleting
   30 days). Production: one-off `--full` load on the VM in the daytime, then the
   stage, grant to tukanmx, data guide 1.9. **Live 2026-10-26** (18.05 M rows; validator
   `scripts/validate_analytics_inventory_stock_daily.py`; nightly stage ~4 min); granted to tukanmx (part I);
   data guide 1.9. History coverage per branch and the query cost of the big inventory tables:
   `docs/history-coverage-by-branch.md`.
5. **`analytics_expense_invoices`** (supplier invoices; needs a crosswalk from
   Odoo accounting accounts to Wansoft's `Cuenta`).

Before step 3, check free space on the database server (about 9 GB more for
tables 1 and 2), and grant the new tables to the read-only users.
