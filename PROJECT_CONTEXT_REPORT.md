# PROJECT_CONTEXT_REPORT.md

Master continuity document. Generated/updated automatically at the close of major steps, on explicit request ("Generate project context report"), when the conversation gets very long, when consumed context exceeds ~70%, or when a new chat needs to be opened due to token limits. Always regenerated in full, never as an incremental patch.

Last generated: 2026-09-23, closing for the day — covers three sessions (2026-09-21, 2026-09-22, 2026-09-23). This round validated the data-warehouse methodology end to end against live Power BI for 4 representative branches, fixed a real Odoo extraction bug, and closes with a **major strategic pivot**: the delivery layer is no longer "repoint Power BI at the unified MySQL layer" — it is now "build a purpose-built Django web app," plus a full production infrastructure migration plan. **Read this before anything else if you're picking this up fresh, especially Section 0, Section 12 (bug log), Section 16 (the pivot), and Section 17 (infra migration plan).**

---

# 0. Critical environment note — READ FIRST

**The project's working directory moved.** OneDrive redirected the user's Desktop to the organization's OneDrive path around 2026-09-15 13:10-13:40. The old path (`C:\Users\JavierViniegra\Desktop\AnalisisRestaurantesBI\...`) is permanently empty and will stay that way — do not try to "restore" it.

**Current correct path:**
```
C:\Users\JavierViniegra\OneDrive - GRUPO FONDA ARGENTINA\Escritorio\AnalisisRestaurantesBI\Wansoft\Jupyter Notebooks\Python Files
```

The shell/harness's own default working directory still resets to the old (dead) path after every command in this environment — every command needs an explicit `cd` to the OneDrive path, or an absolute path. This is a session/tooling quirk, not a project issue.

**MySQL dev is not a Windows service (deliberate, prior decision — do not re-suggest making it one).** It does not auto-start with the machine. Confirmed again 2026-09-22: a fresh session hit `Can't connect to MySQL server on 'localhost:3306'` until the user started it manually. If a dev DB connection fails at the start of a session, ask the user to start MySQL rather than debugging further.

`core/config/.env`'s `XML_DOWNLOAD_DIR_DEV` was hardcoded to the old path and was corrected to the OneDrive path on 2026-09-17 — this was silently breaking XML downloads (Sales Candado) for **every branch, every day** since the move (bug log #21). This fix is **local-machine-only** — `.env` is gitignored. If this project is ever set up fresh on another machine, this path needs to be set correctly again from scratch.

Git and `.env` (credentials) both survived the OneDrive move intact.

---

# 1. Executive Summary

**Overall project goal:** build a unified analytical layer in MySQL that integrates Wansoft, Odoo, and Zenput, hiding from the end user which system originates each piece of data.

**Delivery layer goal — changed this round (see Section 16):** the plan is **no longer** to repoint the user's existing Power BI reports at the unified layer. As of 2026-09-23, the decision is to build a **new Django web application** that replicates the validated Power BI pages with interactive filters (date range, branch, month) and interactive charts, behind role-based access (Dirección, Gerente, CGI, Usuario básico, Administrador general). Power BI's role in this project going forward is as the **validation reference**, not the target platform.

**Current state:** the acceptance gate remains formally accepted (2026-08-31). This round's work was almost entirely validation-and-hardening, not new domain construction:
- Made the daily pipeline's re-check windows configurable via `.env` instead of hardcoded, and tuned them for a faster daily run (83 min → 27 min for the full cycle).
- Found and fixed a real bug: Odoo purchase extraction counted unconfirmed RFQs (quotations, `state='sent'`) as real purchases, inflating business-facing Compras totals for every Odoo-migrated branch.
- Ran a structured, branch-by-branch live validation against the user's Power BI (Acoxpa, La Esquina Coyoacán, San Jerónimo, Oceanía; September 2026 month-to-date) covering Ventas, Costos, Meseros, and Compras. **Ventas and Meseros matched exactly in all 4 branches with zero exceptions.** Costos matched exactly once same-day refresh timing was accounted for. Compras required real methodological correction (see below) before it made sense.
- Along the way, discovered and root-caused three things that looked like bugs but were actually either genuine PBI refresh-lag (dev is fresher than Power BI, not wrong) or a comparison-scope mistake (comparing Odoo purchase orders against Wansoft's *full* Compras total, which includes non-goods spend Odoo structurally never captures).
- **User confirmed the validation goal is met**: the methodology — which system to read from per domain/branch, and which exact Power BI figure it corresponds to — is proven correct and repeatable across 4 representative branches. Validating the remaining 15 branches individually is not required; one more can be pulled from Power BI if a doubt ever comes up.

**Scope:** unchanged since 2026-08-31 for the data warehouse itself (see prior sections for full branch list and routing rules). What changed is the *target* for the analytics-facing delivery layer (Section 16) and a new, explicit infrastructure migration plan (Section 17).

**Current block:** none on the data-warehouse side. The new blocking work is planning/scoping the Django app and the production server migration — both captured in this report as the next major step (informally, "Paso 24").

---

# 2. Session 2026-09-15 — Full recap

## 2.1 Full daily cycle simulation, MySQL crash, and 2 real bugs found

Ran the complete daily cycle manually (legacy chain → inventory → purchases → analytics-purchase → cutover) to simulate "a normal production day," per user request. Result: **not** clean end to end.

**MySQL crashed** during `analytics_purchase_daily_company_product`'s ~800K-row aggregation build (`Lost connection to MySQL server during query`). Root cause: `innodb_buffer_pool_size` was still 16M, a risk documented as unresolved since 2026-09-08. Raised to 1G. On restart, crash-recovery itself hit a corruption assertion (`log0recv.cc line 1541`) — same failure class as two prior incidents (2026-09-08, 2026-09-10). Recovery playbook (now well-established in this project): boot at `innodb_force_recovery=6` → confirm the corrupted table via crash-on-SELECT → stop → delete the table's `.frm`/`.ibd` directly from disk → boot at `innodb_force_recovery=1` → confirm clean rollback → remove the flag → rebuild the table from its normal build script. Hit an **orphaned InnoDB dictionary entry** afterward (`CREATE TABLE` failed with "already exists" despite the table being gone from `SHOW TABLES`) — fixed by copying a donor `.frm` from a same-shape table, letting `DROP TABLE` succeed cleanly, then rebuilding for real.

**Bug #1 — real duplicate-insert crash in Purchases:** `save_wansoft_canonical_receipts()` (`extract/purchases/canonical_purchase_etl.py`) deleted existing rows by `date_done` (mapped from `FechaReal`) before reinserting, but the eligibility query that builds the incoming rows filters by `FechaEntrada` (`scheduled_date`). These two dates can diverge per row — confirmed live: an Aeropuerto receipt with `scheduled_date` 2026-08-12 but `date_done` 2026-08-05 was never deleted (outside the delete's 35-day window measured from the wrong column) then crashed the reinsert on a real `Duplicate entry`. **Fixed:** delete by `scheduled_date` instead, matching the eligibility filter.

**Bug #2 — product mapping pipeline never worked:** `analysis/build_product_mapping.py` (exact + fuzzy Odoo↔Wansoft product code matching) crashed on every run with `KeyError: 'odoo_code'` — `extract/products/odoo_products.py` was upgraded at some point to emit `integration_code` (prioritizing the explicit `x_wansoft_code` custom field over `default_code`), but `analysis/normalize_odoo_products.py` was never updated to match. **Fixed** the column reference, and **added a code-base matching tier** (Wansoft/Odoo codes for the same product differ only by a leading prefix — e.g. Wansoft `1000-105-103-030` vs Odoo `5200-105-103-030` — an existing-but-unused `extract_base_code()` helper strips it). Result: 1,047 code-base matches at 99% confidence, up from 301 much-lower-confidence fuzzy-name matches. New `analysis/save_product_mapping.py` writes these to `inventory_mapping_dictionary` as `pending_review` (never auto-`approved` except a literal exact-code match, per `docs/purchases-product-mapping-policy.md`) — a row a human already reviewed is left completely untouched on re-run. Caught and fixed a bug this same day: the first version of the upsert correctly preserved `mapping_status` on already-approved rows but still overwrote `mapping_source`, clobbering provenance on 77 rows (relabeled `historical_approved_source_unknown` since the exact original batch couldn't be reconstructed — chose honesty over false precision). New weekly job (`pipelines/jobs/product_mapping_backlog_job.py` + `schedule_weekly_at()` in `pipelines/scheduler.py`), Sunday 11am, project owner's call.

## 2.2 Power BI validation — found a real internal-vendor exclusion bug

Validated Acoxpa and La Esquina Coyoacan against the user's live Power BI for August (closed month). Ventas matched exactly. Compras/"Entradas de Inventario" were off by ~23% for both branches. Root cause: `scripts/build_analytics_purchase_order_lines.py` excluded any purchase line whose **vendor** was an internal provider (El Bodegon de Fito, Las Empanadas de Maria Eva) from `include_in_business_views`, unconditionally — contradicting the documented policy (`docs/purchases-product-mapping-policy.md`, "Internal Provider Companies"): exclude when the internal provider is the **buying company**, keep when it's just the **vendor** and the buyer is a real branch. **Fixed** (also removed the identical bug baked into `dim_vendor`'s own `include_in_business_views`, which fed the same wrong signal). After the fix: Acoxpa 23%→1.8%, Coyoacan 23%→6.2% — the remaining gap is the still-open product-mapping backlog (expected, not a bug).

## 2.3 Discovered: Sales has a dev-only history gap for the 7 Odoo-migrated branches

August history for Acoxpa/Antenas/Tepeyac/Oceania/Coyoacan/Puebla/CentroMyJ only went back to Aug 28 in **dev** (root cause never found — some event around the 2026-08-27 Odoo-rollout commit session wiped Aug 1-27 for these 7 branches specifically, in dev only; **production is unaffected**, confirmed by the project owner from memory). Backfilled Acoxpa's Aug 1-28 via the real Candado (`verificar_y_sincronizar`, Cierre-Z-validated) — new reusable `scripts/backfill_sales_august.py <subsidiary_id> [<subsidiary_id> ...]`.

---

# 3. Session 2026-09-17 — Full recap

## 3.1 OneDrive move discovered and worked through (see Section 0)

## 3.2 Full daily cycle re-run — clean, confirmed the 09-15 fixes hold

All 5 stages OK, no failures. Confirmed the 2026-09-15 fixes (duplicate-insert, internal-vendor exclusion) held under a real full run.

## 3.3 Puebla exercise — the real payoff of the 09-15 work

User's request: use Puebla (zero Wansoft Purchases/Inventory activity — genuinely "already in the future state") to check whether **dev** has everything needed for a fully Odoo-sourced branch, without comparing to Power BI (since PBI isn't repointed to the unified layer yet).

**Found: Puebla's Sales in dev had the exact same Aug 1-27 gap as Acoxpa** — the user caught this by recalling Puebla's real August sales were "above 3.4 million pesos," while dev showed $631,943 (4 days only). Backfilled via the same `scripts/backfill_sales_august.py 12806` (one day, Aug 22, needed a retry after a transient Wansoft SOAP timeout). Confirmed: **$3,480,350.65**, exactly matching the user's recollection.

**Found: no inventory valuation exists for pure-Odoo branches.** Tried to compute a COGS% for Puebla two ways: (1) Wansoft's own cost report — genuinely returns `0.0` (confirmed in the raw SOAP response, not a bug — Puebla was never onboarded into Wansoft's costing catalog); (2) Purchases-as-COGS-proxy — nonsensical (145.9% of net sales for August, because Puebla was in ramp-up/stock-buildup that month). Checked `analytics_inventory_snapshot` and `canonical_purchase_receipt_move_snapshot` for any inventory valuation field — neither has one, only quantities. **Conclusion, confirmed by the user:** a real inventory-valuation build is genuinely needed for pure-Odoo branches; this is future work.

**Found and fixed: Costs was incorrectly routed to Wansoft for every branch (a same-day self-correction).** First pass put Costs in `ALWAYS_WANSOFT_DOMAINS`, which broke Puebla/CentroMyJ's *only* working cost source.

## 3.4 Costs domain — built out properly for the first time (3 iterations, self-corrected each time)

**Iteration 1:** Found that 4 cost scripts (`descargarCostoWansoft.py`, `getTotalCostByDate.py`, `getCostReport_SemanaPyQ.py`, `getTablajeriaReport.py`) routed branches via `is_wansoft_company()` — which reads `COMPANY_SOURCE`, the governance signal for Purchases/Inventory only. Costs was never migrated (`docs/power-bi-source-migration.md`: "No unified analytics table exists yet for Costs"), and the user confirmed live: their Power BI reads Costs entirely from Wansoft, for every branch, migrated or not. Added `"costs"` to `ALWAYS_WANSOFT_DOMAINS`.

**Iteration 2 (same-day correction):** This broke Puebla/CentroMyJ, which have **zero** real Wansoft cost data but **do** have a working, previously-built, already-audited Odoo-side calculation (`extract/costs/odoo_cost_report.py` — `account.move.line` on `expense_direct_cost` accounts). Real governance needed a 3-way split:
- 5 branches migrated **from** Wansoft (Acoxpa, Antenas, Tepeyac, Oceania, La Esquina Coyoacan): Wansoft still has real, complete cost data.
- 2 branches that started **on** Odoo (Puebla, CentroMyJ): use `extract/costs/odoo_cost_report.py`.

New: `core/config/companies.py` — removed `"costs"` from `ALWAYS_WANSOFT_DOMAINS`, added `COSTS_ODOO_SOURCE_COMPANIES = {"Puebla", "CentroMyJ"}` and `is_company_wansoft_source_for_costs()` as the real per-branch check.

**Iteration 3 — Cortesias/Cancelaciones, applied to all 19 uniformly:** User's proposal: pull them from `getglobalcashclosing` instead of Wansoft's own `CostoDeCortesias`/`CostoDeCancelaciones` — it's a Sales-domain value (sale price forfeited on the comped/cancelled item), and Sales is always Wansoft-sourced, same principle as `ALWAYS_WANSOFT_DOMAINS`. Cross-checked against Acoxpa: the sale-value figure is ~2x the previously-validated cost-basis figure. **User's explicit, informed decision:** use the sale-value figure anyway, uniformly, for all 19 branches. Applied to both the Wansoft-report path (overriding `GetCostReport_Xml`'s own values) and the Odoo path.

Two real bugs surfaced while building this, both fixed same-day: MySQL `SUM()` returning `decimal.Decimal` breaking pandas `cumsum()`; a cross-dataset date-merge silently resetting values to 0 on unmatched dates, fixed by querying month-to-date sums fresh per-date instead of a batch merge.

## 3.5 Confirmed a real, ongoing production duplication (left production untouched, per instruction)

Checked production directly (avoided the 25M-row `getoutgoinginventory_salida` table entirely):
- **Puebla, CentroMyJ:** zero Wansoft Purchases/Inventory activity — already in the target state.
- **Acoxpa, Antenas, Tepeyac, Oceania, La Esquina Coyoacan:** all 5 still had real, recent Wansoft Purchases **and** Inventory activity in production — genuine ongoing duplicate work, confirmed again this round (Section 5) still true as of 2026-09-21/22.

Confirmed dev's own code already correctly excludes all 7 Odoo-source branches. **Production is running something else** (an older deployment or separate process) — not touched, per explicit instruction. See Section 17 for how this gets resolved once the new server migration lands.

---

# 4. Session 2026-09-21 — Full recap

## 4.1 MySQL dev required a manual start

Session opened with dev DB unreachable (`Can't connect to MySQL server on 'localhost:3306'`) — expected, since MySQL dev is deliberately not a Windows service (Section 0). Resumed once the user started it.

## 4.2 Daily-run lookback windows made configurable

User's ask: the daily job should re-check a **configurable** number of past days for updates/corrections, not a hardcoded number — the existing legacy Wansoft scripts already did this (31-day windows), which was good, and the Sales Candado (`extractAllOrdersByDay.py`) already supported a configurable range/payments mode. What was missing: a single, `.env`-driven knob instead of literals scattered across scripts.

**Built:** `core/config/lookback.py` — reads and validates three integers from `.env`, with safe defaults matching prior hardcoded behavior:
- `SALES_LOOKBACK_DAYS` (default 10) — feeds `DIAS_A_REVISAR` in the Sales Candado.
- `WANSOFT_LOOKBACK_DAYS` (default 31) — feeds the re-check window in `getCostReport_SemanaPyQ.py`, `getExpenses.py`, `getInputInventory.py`, `getOutgoingInventory.py`, `getTablajeriaReport.py`, `getTotalCostByDate.py`, `getGlobalCashClosing.py`, `descargarCostoWansoft.py`.
- `PURCHASES_LOOKBACK_DAYS` (default 35) — feeds `WANSOFT_CANONICAL_INCREMENTAL_WINDOW_DAYS` in `extract/purchases/canonical_purchase_etl.py`.

Each edit was a 3-line diff (import + one hardcoded value replaced). Documented in `.env.example`. Committed and pushed (`9ed1cec`).

**Tuned same day, per user request:** `WANSOFT_LOOKBACK_DAYS` set from 31 → **5** in the working `.env` (and `.env.example` default), to keep the daily Wansoft leg fast while still catching same-week corrections. `SALES_LOOKBACK_DAYS` and `PURCHASES_LOOKBACK_DAYS` left at their defaults.

## 4.3 Full daily cycle re-run twice — confirmed correctness and measured the speedup

- **Run 1** (old 31-day window, before the .env tune landed): 83 minutes, 15/15 stages OK, no failures.
- **Run 2** (new 5-day window): **27 minutes**, 15/15 stages OK. Confirmed via before/after row-count baselines: no duplicate rows introduced anywhere, and the shorter window still correctly picked up new activity (cash closing +2, tablajería +16 late-registered rows, canonical purchases +25).

## 4.4 Dev-vs-prod comparison, and confirmed production loads are manual today

Compared dev against production (read-only, careful about the 25M-row `getoutgoinginventory_salida` table — checked `information_schema` sizes/indexes first). Production was frozen since 2026-09-18 for most tables — **confirmed by the user: production loads are run by hand today, there is no autonomous daily scheduler in production yet.** This is expected, not a bug — the goal for when the project reaches production is a fully autonomous daily run (Section 17 covers how that lands).

Established methodology for future dev-vs-prod checks: always find production's actual max loaded date per table first, and only compare through that date — don't treat a stale prod load as a data discrepancy.

After the user's manual production load caught up: Ventas, Caja Global, Facturas, and Costo Total matched dev exactly through 2026-09-20; Entradas/Salidas were still mid-load in production at comparison time.

---

# 5. Session 2026-09-22 — Full recap

## 5.1 Daily cycle re-run, methodology validation kickoff

Re-ran the full daily cycle fresh (MySQL started manually again). Then began a structured, per-branch live validation against the user's actual Power BI — first branch: **Acoxpa**, September 2026 month-to-date.

## 5.2 Acoxpa validation — Ventas and Costos exact, Compras led to a real bug fix

**Ventas:** dev vs Power BI matched exactly ($4,230,552.70 / 1,913 orders for the Sept 1-21 cut used that day).

**Costos:** traced Power BI's figures to production's `costeoMensual` table (Wansoft's raw `GetCostReport_Xml` report, month-to-date cumulative). Found Power BI's displayed "Costo Total" = `costeoMensual.CostoTotal` **minus** `CostoDeConsumo` (shown separately as "Gasto de Venta") — once that transformation was understood, Costo Total, Costo Teórico, and Gasto de Venta all matched dev exactly; small residual gaps (~0.2-8%) on Costo Total/Merma turned out to be capture-timing (Wansoft recalculates its own report between production's and dev's capture times that day) — confirmed the next day when the gap disappeared entirely. Costo de Cortesías/Cancelaciones differ from Power BI **by design** (dev correctly uses `getglobalcashclosing`'s sale-value figure per the 2026-09-17 decision; Power BI still shows Wansoft's raw cost-basis value until it's repointed).

**Compras — real bug found:** comparing Odoo's business-eligible purchase total for Acoxpa against Wansoft/Power BI's figure showed Odoo ~4.7% *higher*. Investigated the gap: **`extract/purchases/odoo_purchase_orders.py` and `odoo_purchase_order_lines.py` pulled `purchase.order`/`purchase.order.line` from Odoo with no `state` filter at all** — unconfirmed RFQs (`state='sent'`, quotations that were never approved into a real purchase commitment) were being counted as real business purchases. Confirmed: 46 lines, $108,113.33 (sin IVA) of Acoxpa's September total were unconfirmed quotations, about half the observed gap.

**Fixed:** added `domain = [["state", "in", ["purchase", "done"]]]` to both Odoo extractors (both tables are `TRUNCATE`+reload on every run, so a normal pipeline re-run purges the bad rows — no backfill needed). After the fix, the gap dropped from +4.7% to -2.0% (and flipped sign) — a normal, small cross-system residual, not chased further that day.

Committed and pushed (`0169140`).

---

# 6. Session 2026-09-23 — Full recap

## 6.1 Daily cycle re-run with both fixes live

27 minutes, no failures, confirmed by baseline diff (row counts moved forward with no duplication).

## 6.2 Extended validation: La Esquina Coyoacán, San Jerónimo, Oceanía (Sept 1-22 MTD)

### Ventas and Meseros — exact in every branch, and a real discovery about Power BI's own report

Ventas matched exactly in all 4 branches, no exceptions, across two separate days of comparison (Acoxpa twice, Coyoacán/San Jerónimo/Oceanía once each).

**Discovery (not a bug): Power BI's "Meseros" ranked table silently excludes a delivery/app placeholder "waiter."** Every sale in dev has a `Mesero` value, including delivery/app orders — attributed to a placeholder that Wansoft names differently per branch (`APLICACIONES` for Coyoacán/Acoxpa, `Apps Llevar` for San Jerónimo). Power BI's Top-Meseros table filters this placeholder out of its ranking (a report-design choice, not a data problem). Confirmed by summing dev's real, human waiters only (excluding the placeholder) and getting an **exact** match to Power BI's Meseros "Total" row in Coyoacán ($703,345.30), San Jerónimo ($3,015,847.00), and Oceanía ($1,817,226.00, which for that branch also equals the "Restaurant" dine-in total). This is now a repeatable validation pattern for any branch's Meseros page.

### Costos — exact once refresh timing is accounted for

Acoxpa and San Jerónimo matched exactly on every line (Costo Total, Costo Teórico, Gasto de Venta, Merma). Coyoacán had a small residual (~0.06-0.09%). **Oceanía's numbers did not match today's dev capture at all** — until compared against **yesterday's** dev capture (Sept 1-21 cumulative), which matched Power BI's figures **exactly** on all four fields. Conclusion: Power BI's Costos page for Oceanía specifically was still one day behind its own Wansoft source at the moment the screenshot was taken — dev was simply more current, not wrong.

### Compras — San Jerónimo (100% Wansoft): apparent near-doubling, root-caused to two separate, real, understandable causes

Dev's naive Entradas-de-Inventario total for San Jerónimo came out at $1,864,227 against Power BI's $1,040,150 — an alarming near-2x gap. Investigation found:
1. **Power BI's "Entradas de Inventario por Factura" report only counts `TipoEntrada='Factura'`** — dev's naive query had summed every entry type (`Entrada con canal`, `Transferencia`, `Producto procesado`, `Ajuste de inventario` too). Restricting to `Factura` alone brought the total to $1,211,378 — much closer, but still ~16% high.
2. **One single invoice** (Sigma Foodservice, Factura `8562652917`, $135,734.51, posted Sept 22 at ~1pm) was in dev's fresher capture but not yet in Power BI's refresh at screenshot time. Excluding just that one day's data made dev match Power BI **exactly**: $1,040,149.69 = $1,040,149.69.

Confirmed no duplicate `IdEntrada` rows anywhere — this was never a duplicate-insert bug, purely a scope/timing mismatch. Two smaller open items surfaced along the way and were **not** resolved today: a real, unexplained ~$5,915 gap in the "Gastos de venta" `Cuenta` bucket, and $49,937 in Wansoft invoices with a **blank** `Cuenta` (unclassified spend on the Wansoft side) — both flagged for later, not urgent.

### Compras — Acoxpa, Coyoacán, Oceanía (Odoo-migrated branches): a real comparison-scope correction

Comparing Odoo's business-eligible purchase total against Power BI's **full** "Compras Mensuales" total (all `Cuenta` buckets summed: Costo operativo + Gastos de venta + Gastos Directos + Sueldos y Salarios + Fletes, depending on branch) produced wildly inconsistent gaps: Acoxpa -3.2%, **Coyoacán -26.0%**, Oceanía +3.9%.

Root-caused Coyoacán's outlier via a proveedor-by-proveedor cross-check (Wansoft prod vs Odoo dev, normalized vendor names): **one vendor, GRUPO HOSPITALARIO RODIVA, billed $81,008.49 across 4 weekly invoices in September, classified under Wansoft's `Gastos Directos` account as "Licencias/Programas/Software" and "Management Administrativo."** This is a recurring administrative/software subscription, not a goods purchase — Odoo's `purchase.order` model structurally never creates a purchase order for this kind of spend (it belongs in vendor bills/accounting, not procurement), so its complete absence from Odoo was never a data gap. This single vendor accounted for ~79% of Coyoacán's apparent shortfall.

**Corrected methodology:** compare Odoo's business-eligible total only against Wansoft's `Cuenta='Costo operativo'` bucket (the actual raw-materials/COGS spend), never the full multi-account sum. After the correction, all three branches show a consistent, much smaller, believable pattern — **Odoo running above Wansoft's Costo operativo in every case**: Acoxpa +7.2%, Coyoacán +11.1%, Oceanía +18.5%. This residual gap is real and was **not** root-caused today (candidate explanation: Odoo purchase orders and Wansoft invoiced facturas cut off "when is this a purchase" on different criteria — order placed vs. invoice registered); documented as an open item in project memory, not chased further.

**Side note for future vendor-level reconciliations:** found multiple false-positive "missing vendor" entries caused purely by word-order differences between the two systems (e.g. Wansoft's "Barrera Amezcua Carlos" = Odoo's "Carlos Barrera Amezcua," identical amount) — normalize/reorder names before treating a vendor as genuinely missing.

## 6.3 User confirmed the validation goal is met

Explicitly stated: validating these 4 branches (Acoxpa, Coyoacán, San Jerónimo, Oceanía) is sufficient to demonstrate the process is correct and the data is consistent between systems — the point was proving *where to read each figure from and what it corresponds to in Power BI*, not exhaustively re-validating all 19 branches. If a doubt comes up later, one more branch can be pulled from Power BI on demand; no standing requirement to validate the rest.

## 6.4 Strategic pivot decided (see Section 16) and infrastructure migration plan requested (see Section 17)

---

# 7. Detailed Status by Domain

### Sales
No open issues in pipeline logic. Matches Power BI exactly in every branch checked to date (Acoxpa, Coyoacán, San Jerónimo, Oceanía; Puebla in the prior report round). **Open question, carried forward unchanged:** whether Antenas, Tepeyac, or CentroMyJ have the same Aug 1-27 dev-only history gap found on Acoxpa/Puebla — still not checked.

### Purchases
Both August-round bugs (duplicate-insert date-column mismatch, internal-vendor exclusion) remain fixed and validated. **New this round:** the unconfirmed-RFQ bug (Section 6.2) is fixed for all 7 Odoo-source branches, not just Acoxpa. **New methodology finding:** for Odoo-migrated branches, business-facing Compras must be compared against Wansoft's `Cuenta='Costo operativo'` specifically, not the full Compras Mensuales total — the full total includes non-goods spend (software, admin, payroll, freight-as-service) that Odoo's purchase-order model will never contain. After that correction, Compras still runs 7-19% higher in Odoo than in Wansoft across the 3 Odoo branches checked (Acoxpa, Coyoacán, Oceanía) — real, stable, unresolved; candidate cause is a differing cutoff criterion (order-placed vs. invoice-registered) between the two systems.

### Inventory
No change this round for the Odoo-side valuation gap (still open, see Section 3.3/Backlog). **New finding for the still-100%-Wansoft branches:** Power BI's own "Entradas de Inventario por Factura" report is scoped to `TipoEntrada='Factura'` only — any raw comparison against `getinputinventory_entrada` must apply the same filter or it will look inflated by transfers/adjustments/processed-product entries that were never real purchases.

### Costs
No change to the 3-way routing logic itself (see Section 3.4) — it continues to validate correctly. **New this round:** confirmed Power BI's own Costos page can lag its Wansoft source by up to a day for a given branch (seen on Oceanía); when a Costos comparison doesn't match, check dev's prior day's snapshot before assuming a bug. Cortesías/Cancelaciones continue to differ from Power BI by design (sale-value vs. cost-basis), unchanged and expected.

### Meseros (new: informally tracked as part of Sales validation)
Confirmed: Power BI's Meseros ranking table excludes a per-branch delivery/app placeholder waiter from its total. Dev's raw data is complete and correct; validate by excluding the placeholder mesero before comparing to Power BI's "Total" row.

### Security / Configuration
`.env`'s `XML_DOWNLOAD_DIR_DEV` fix remains local-machine-only (Section 0). **New:** `SALES_LOOKBACK_DAYS`, `WANSOFT_LOOKBACK_DAYS` (currently 5, tuned down from the 31-day default), `PURCHASES_LOOKBACK_DAYS` are also `.env`-driven now — same local-machine-only caveat applies; these need to be set again on any fresh machine/server (see Section 17 for the production deployment plan that must carry this forward).

---

# 8. Architectural Decisions Made (chronological, all sessions to date)

| Decision | Rationale | Impact |
|---|---|---|
| Fix `save_wansoft_canonical_receipts`'s delete window to match the eligibility query's date column | Two different date columns can diverge per row, causing real duplicate-key crashes | `extract/purchases/canonical_purchase_etl.py` |
| Add a code-base matching tier before falling back to fuzzy name matching | Wansoft/Odoo codes for the same product differ only by a prefix; comparing the remainder is a real-identifier match | `analysis/build_product_mapping.py` |
| Never let a re-run of the weekly product-mapping job touch a row a human already approved/rejected, field by field | A first version only protected `mapping_status`, still let `mapping_source` get silently overwritten | `analysis/save_product_mapping.py` |
| Stop excluding a branch's own purchases from an internal-provider vendor | Company-is-internal and vendor-is-internal are different cases; only the first should exclude | `scripts/build_analytics_purchase_order_lines.py`, `scripts/build_dim_vendor.py` |
| Costs needs a 3-way governance split, not `ALWAYS_WANSOFT_DOMAINS` or plain `COMPANY_SOURCE` | Wansoft-migrated branches still have real Wansoft cost data; pure-Odoo branches have none but have a working Odoo-side calculation | `core/config/companies.py` (`COSTS_ODOO_SOURCE_COMPANIES`), 4 cost scripts |
| Cortesias/Cancelaciones always come from `getglobalcashclosing`, all 19 branches, sale value not cost basis | Sales/POS concept, Sales is always Wansoft regardless of a branch's other-domain source | `legacy/wansoft/descargarCostoWansoft/descargarCostoWansoft.py` |
| Compute month-to-date sums via a direct per-date SQL query inside the loop, not a batch pandas merge | A merge across two independently-dated series silently produces gaps/resets | Same file, Odoo cost path |
| Leave production's duplicate Wansoft Purchases/Inventory loading untouched | Explicit user instruction; dev proves the target state, production changes are separate | No code change |
| Daily-run lookback windows moved from hardcoded literals to `.env`-driven config (`core/config/lookback.py`) | The daily job needs to re-check a *configurable* number of past days for late corrections, not a fixed number baked into 9 different scripts | New file `core/config/lookback.py`; 9 scripts updated to import from it |
| `WANSOFT_LOOKBACK_DAYS` tuned from 31 to 5 | Keep the Wansoft leg of the daily cycle fast (83 min → 27 min) while still catching same-week corrections; can be raised again from `.env` alone if needed | `.env`, `.env.example` |
| Odoo purchase extraction must filter to `state in ('purchase', 'done')` | Unconfirmed RFQs (`state='sent'`) are not real purchase commitments and were inflating business-facing Compras totals by design-omission (no filter existed at all) | `extract/purchases/odoo_purchase_orders.py`, `extract/purchases/odoo_purchase_order_lines.py` |
| Compras validation for Odoo-migrated branches must compare against Wansoft's `Cuenta='Costo operativo'` bucket specifically, never the full Compras Mensuales total | The full total includes non-goods spend (software subscriptions, admin management, payroll, freight-as-service) that Odoo's purchase-order model structurally never captures — comparing against it produces false "missing purchases" gaps | Validation methodology only; no code change, captured in project memory |

---

# 9. Business Rules Implemented / Reinforced

- **Costs governance is per-branch, three states, not a domain-wide flag:** Wansoft-migrated vs. pure-Odoo vs. the Cortesias/Cancelaciones Sales-adjacent override that ignores both and always uses Wansoft's sale-value figure.
- **Internal-provider exclusion is about the buying company, never the vendor alone** — a real branch buying from an internal kitchen (El Bodegon, Las Empanadas) is a real purchase for that branch.
- **A weekly automated job must never downgrade or silently relabel a human review decision** — every field of an already-reviewed row stays untouched on re-run.
- **`getglobalcashclosing` is a legitimate, Wansoft-sourced, always-available report for every branch regardless of Purchases/Inventory/Costs migration status** — same tier as Sales itself.
- **Odoo purchase orders only represent goods procurement.** Service/subscription/payroll/administrative spend recorded in Wansoft under other `Cuenta` buckets (Gastos Directos, Sueldos y Salarios, etc.) has no Odoo purchase-order equivalent by design — it is not a gap to chase.
- **A daily job's re-check window is a tuning knob, not a constant.** It should live in `.env`, not be hardcoded per-script, so it can be widened (to self-heal after a missed run) or narrowed (to keep the daily cycle fast) without a code change.

---

# 10. Technical Conventions / Learnings

- The Bash/harness working-directory reset after every command (Section 0) means every multi-step investigation needs `cd` or absolute paths repeated constantly.
- MySQL `SUM()`/aggregate results come back as `decimal.Decimal` via `mysql.connector`, which pandas treats as `object` dtype — always cast explicitly before `cumsum()`/other numeric pandas ops.
- Never merge two pandas frames built from two independently-dated SQL queries and assume the date sets align — a per-row/per-date direct query is slower but immune to silent gaps.
- Windows Explorer/OneDrive Known Folder Move can relocate a project's entire working directory without warning; the local `.git` and `.env` survive, but hardcoded absolute paths in config/scripts need to be found and fixed after the fact.
- Querying production during business hours on an unindexed large table can hang for 1+ hours. Always check `information_schema.tables` size/indexes before an ad-hoc query against a production table larger than a few hundred MB; avoid `getoutgoinginventory_salida` (25M+ rows) entirely unless the exact task requires it.
- **Production (prod) and dev are different MySQL servers reachable through the same script's connection helper (`target="wansoft"` switches by config) — always double-check which one a query is actually hitting before concluding a table is "empty" or "wrong." A same-looking query against the wrong side (e.g. checking `getexpenses_factura` on dev for an Odoo-migrated branch) will legitimately return zero rows by design, not by bug.**
- Vendor/person names can appear in different word orders between Wansoft and Odoo ("Apellido Nombre" vs. "Nombre Apellido") for the exact same real-world vendor — normalize before treating a vendor-level mismatch as a missing record.
- Wansoft's own reports (Entradas de Inventario, cost reports) are scoped more narrowly than the raw tables backing them (e.g. `TipoEntrada='Factura'` only) — match that scope before comparing a raw-table sum against a Power BI figure.
- A same-day discrepancy between dev and Power BI is often just refresh-timing (dev captured later/fresher, or Power BI hasn't refreshed a specific branch's page yet) — before treating it as a bug, check dev's *previous* day's snapshot and/or exclude the most recent day from the comparison window.

**Git state:** branch `main`, up to date with `origin/main` through commit `0169140`. `inventory_not_found_analysis.csv` remains permanently uncommitted per convention. Loose untracked files at the repo root (`extractAllOrdersByDay.py`, `extractAllOrdersByDay_old.py`, `getAllOrdersByDay.py`) remain unexplained, not touched.

---

# 11. Important Historical Context — Combined Bug Log (do not re-investigate)

See prior reports for bugs #1-#17.

| # | Bug | Where it actually lived | Status |
|---|---|---|---|
| 18 | Cross-run duplicate-key crash in Wansoft canonical purchase receipts | `extract/purchases/canonical_purchase_etl.py`, deleting by the wrong date column | **Fixed 2026-09-15** |
| 19 | Product-mapping pipeline crashed on every run (`KeyError: odoo_code`), had never worked | `analysis/normalize_odoo_products.py` reading a stale column name | **Fixed 2026-09-15** |
| 20 | Internal-provider vendor exclusion dropped a branch's own real purchases from all business-facing Purchases numbers | `scripts/build_analytics_purchase_order_lines.py` + `scripts/build_dim_vendor.py` | **Fixed 2026-09-15** |
| 21 | `XML_DOWNLOAD_DIR_DEV` pointed at the pre-OneDrive-move dead path, silently failing every Sales XML download since the move | `core/config/.env` (local, gitignored) | **Fixed 2026-09-17** |
| 22 | Costs domain routed via `COMPANY_SOURCE` (a purchases/inventory-only signal), self-corrected twice same day before landing on the real 3-way split | `core/config/companies.py`, 4 cost scripts | **Fixed 2026-09-17** |
| 23 | Odoo-path Cortesias/Cancelaciones computation: `Decimal` dtype crash, then a cross-dataset date-merge silently resetting values to 0 | `legacy/wansoft/descargarCostoWansoft/descargarCostoWansoft.py` | **Fixed 2026-09-17** |
| 24 | Odoo purchase extraction had no `state` filter at all — unconfirmed RFQs (`state='sent'`) counted as real business purchases, inflating Compras totals for every Odoo-migrated branch | `extract/purchases/odoo_purchase_orders.py`, `extract/purchases/odoo_purchase_order_lines.py` | **Fixed 2026-09-22** |

**Also confirmed NOT bugs this round:**
- Oceanía's Costos mismatch on 2026-09-23 — Power BI's own Costos page was one day behind its Wansoft source; dev's prior-day snapshot matched exactly.
- San Jerónimo's near-doubled Entradas de Inventario figure — a report-scope mismatch (`TipoEntrada='Factura'` filter) plus one single legitimate invoice dev had that Power BI's refresh didn't have yet; not a duplicate-insert, confirmed via `IdEntrada` uniqueness check.
- Coyoacán's -26% Compras "gap" — a comparison-scope mistake (comparing Odoo against Wansoft's full Compras total instead of `Costo operativo` only); the -26% was driven ~79% by one legitimate software/admin vendor Odoo was never going to capture.
- Power BI's Meseros table excluding the delivery/app placeholder waiter from its ranked total — a report display choice, dev's underlying data is complete.

**Gate result:** unchanged, not reopened.

---

# 12. User Decisions (explicit, don't lose track of these)

- **Confirmed (2026-09-17):** Cortesias/Cancelaciones use `getglobalcashclosing`'s sale-value figure for all 19 branches uniformly, not a cost-basis conversion — informed choice, will keep differing from Power BI until Power BI is repointed.
- **Confirmed (2026-09-17):** leave production's Wansoft Purchases/Inventory duplicate-loading untouched until the server migration (Section 17) addresses it directly.
- **Confirmed (2026-09-17):** a real inventory-valuation build for pure-Odoo branches is genuine future work.
- **Confirmed (2026-09-15):** the weekly product-mapping job runs Sundays 11am.
- **Confirmed (2026-09-21):** production loads are manual today; the goal is a fully autonomous daily run once the project is in production.
- **Confirmed (2026-09-21):** `WANSOFT_LOOKBACK_DAYS` set to 5 (down from the 31-day default) for the daily cycle going forward.
- **Confirmed (2026-09-23):** validating Acoxpa, Coyoacán, San Jerónimo, and Oceanía against Power BI is sufficient to prove the methodology is correct — no standing requirement to validate the remaining 15 branches individually.
- **Confirmed (2026-09-23) — the major pivot:** the delivery/analytics layer will be a **new Django web application**, not a repoint of the existing Power BI reports. See Section 16 for full requirements as understood so far.
- **Confirmed (2026-09-23):** the production virtual server (Hyper-V) will be backed up, then rebuilt/repurposed for the new stack; GitHub will drive a recurring daily auto-update of code on that server; all old scheduled tasks on the server get cleaned up, leaving only the new pipeline's task. See Section 17.

---

# 13. Identified Legacy / Consolidated Backlog

**Backlog, in rough priority order:**
- **Inventory valuation for pure-Odoo branches** — needed for a real COGS (not a purchases-as-proxy approximation) on Puebla/CentroMyJ and any future pure-Odoo branch. No existing table has a cost/value field on inventory movements.
- **Root-cause the residual 7-19% Compras gap between Odoo and Wansoft's Costo operativo** for Acoxpa/Coyoacán/Oceanía (Section 6.2) — candidate cause is a differing "when does this count as a purchase" cutoff between systems; not chased yet.
- **San Jerónimo: unexplained ~$5,915 gap in the "Gastos de venta" `Cuenta` bucket**, and **$49,937 in Wansoft invoices with a blank `Cuenta`** (unclassified spend) — both surfaced 2026-09-23, not investigated.
- **Decide when to turn off production's duplicate Wansoft loading** for Acoxpa, Antenas, Tepeyac, Oceania, La Esquina Coyoacan — folded into the Section 17 server migration plan now, no longer a standalone open question.
- **Check whether Antenas, Tepeyac, or CentroMyJ have the same Aug 1-27 dev-only Sales history gap** as Acoxpa and Puebla — still not checked.
- Replay `sql/maintenance/add_unique_keys_dedup_protection.sql` on production once that side is promoted — carried forward, unchanged, now part of Section 17's DB migration step.
- Raise production's own `innodb_buffer_pool_size` if it's still 16M there too — never checked this round.
- Weekly product-mapping job (Sundays 11am) needs its first real Sunday run observed to confirm the schedule fires as expected.
- Origin of the loose root-level files (`extractAllOrdersByDay.py`, `extractAllOrdersByDay_old.py`, `getAllOrdersByDay.py`) — untracked, unexplained, not touched.
- `.env`'s `XML_DOWNLOAD_DIR_DEV`, `SALES_LOOKBACK_DAYS`, `WANSOFT_LOOKBACK_DAYS`, `PURCHASES_LOOKBACK_DAYS` are all local-machine-only (gitignored `.env`) — must be set correctly on the new production server as part of Section 17's deployment step.
- Isabel La Católica/San Jerónimo/Vía Vallejo Odoo cutover, at/after 2026-10-01 (unchanged, carried forward) — will change San Jerónimo's own routing shortly after this report; re-validate its Costs/Compras routing once that cutover actually happens.

---

# 14. Data Sourcing Reference — What Comes From Where, and What It Validates Against in Power BI

Captured this round because it's the exact question the validation work (Section 6) answered branch by branch. Keep this table current — it is the map the future Django app's data layer (Section 16) will need too.

| Domain | Branch state | Dev reads from | Landing table(s) in dev MySQL | Power BI figure it corresponds to |
|---|---|---|---|---|
| Sales | All 19, always | Wansoft SOAP (`extractAllOrdersByDay.py`, the Candado) | `getallordenesbyday_new_venta` | "Venta" / "# de Órdenes" card, Ventas Totales page |
| Meseros | All 19, always | Same as Sales (`Mesero` column) | `getallordenesbyday_new_venta` | Meseros page ranked table — **exclude the delivery/app placeholder mesero** before comparing to the "Total" row |
| Costs — Wansoft-migrated branches (Acoxpa, Antenas, Tepeyac, Oceania, La Esquina Coyoacan) and never-migrated branches | Wansoft SOAP (`GetCostReport_Xml` via `descargarCostoWansoft.py`) | `costeoMensual` (month-to-date cumulative) | "Costo Total" (= `CostoTotal` − `CostoDeConsumo`), "Costo Teórico" (= `CostoDeProductosVendidos`), "Gasto de Venta" (= `CostoDeConsumo`), "Costo de Mermas" |
| Costs — pure-Odoo branches (Puebla, CentroMyJ) | Odoo `account.move.line`, `expense_direct_cost` accounts | via `extract/costs/odoo_cost_report.py` | Same fields, Odoo-computed |
| Costs — Cortesías/Cancelaciones, all 19 | Wansoft `getglobalcashclosing`, sale value (not cost) | feeds into `costeoMensual`/Odoo cost path override | "Costo de Cortesías"/"Costo de Cancelaciones" — **differs from Power BI by design**, PBI still shows cost-basis |
| Purchases/Inventory — still-100%-Wansoft branches | Wansoft SOAP (`getExpenses.py`, `getInputInventory.py`) | `getexpenses_factura`, `getinputinventory_entrada` | "Compras Mensuales" (by Proveedor and by `Cuenta`), "Entradas de Inventario por Factura" (**scope to `TipoEntrada='Factura'`** to match Power BI) |
| Purchases/Inventory — Odoo-migrated branches (Acoxpa, Antenas, Tepeyac, Oceania, La Esquina Coyoacan, Puebla, CentroMyJ) | Odoo `purchase.order`/`purchase.order.line`, `state in ('purchase','done')` only | `canonical_purchase_order_snapshot`, `canonical_purchase_order_line_snapshot` → `analytics_purchase_daily_company_product` | **The `Cuenta='Costo operativo'` bucket only** in "Total de Compras por Cuenta" — never the full page total, which includes non-goods spend Odoo will never have |

---

# 15. Detailed Validation Results — Acoxpa, La Esquina Coyoacán, San Jerónimo, Oceanía (Sept 2026 MTD)

| | Acoxpa (Odoo) | Coyoacán (Odoo) | San Jerónimo (Wansoft) | Oceanía (Odoo) |
|---|---|---|---|---|
| Ventas | Exact match | Exact match | Exact match | Exact match |
| Meseros | Exact match (excl. placeholder) | Exact match (excl. placeholder) | Exact match (excl. placeholder) | Exact match |
| Costo Total / Costo Teórico / Merma | Exact match | Δ ~0.06-0.09% (timing) | Exact match | Matches dev's prior-day snapshot exactly (Power BI refresh lag) |
| Cortesías / Cancelaciones | Differs by design | Differs by design | Differs by design | Differs by design |
| Compras (vs. Wansoft `Costo operativo` only) | Odoo +7.2% | Odoo +11.1% | Exact match (100% Wansoft; matched after scoping to `TipoEntrada='Factura'` and excluding the most recent day) | Odoo +18.5% |

Conclusion the user confirmed as sufficient: the sourcing methodology (Section 14) is correct and repeatable. The residual Odoo-vs-Wansoft Compras gap (7-19%) is real, consistent in direction, and left as a documented open item rather than a blocker.

---

# 16. Strategic Pivot — Django Web Analytics App (replaces the Power BI-migration plan)

**Decision (2026-09-23):** stop planning to repoint the user's existing Power BI reports at the unified MySQL layer. Instead, build a **new, purpose-built web application** that replicates the validated Power BI pages, backed directly by the unified analytics layer, with interactive filtering and role-based access. Power BI remains the validation reference (Section 14/15) but is no longer the target platform.

## 16.1 Pages to replicate (all already validated against real data, Section 15)

- **Ventas Totales** — per-branch KPI cards (Venta, Comensales, Cheque, Ticket, # de Órdenes, Mesas, Delivery, Comensales x Mesero, Comensales x Mesa), an hourly sales bar chart (current vs. prior period), a Mix de Ventas Salón pie (Alimentos/Bebidas), and a Salón/Delivery/Llevar breakdown with a day-of-week donut.
- **Score Card** — gauge visuals for Ventas, Cheque Promedio, Ticket Promedio, Costo Total %, Comensales, against target thresholds (the red/green bands seen in Power BI).
- **Meseros** — a top-waiters bubble/scatter chart plus a ranked table (# Tickets, Total, % share), and a "top products by best waiter" treemap. Must exclude the delivery/app placeholder from the ranking exactly as Power BI does (Section 14), or explicitly decide to include it — **open design question, ask the user**.
- **Compras Mensuales** — Proveedor-level subtotal table, a "Distribución de Compras sobre Venta" chart, a "Total de Compras por Cuenta" chart, a top-products table, and a Departamento breakdown table.
- **Entradas de Inventario por Factura** — a Departamento × Month matrix with a running total column.
- **Scorecard Ventas (Tier 1 / Tier 2)** and **Scorecard Costos (Tier 1 / Tier 2)** — all-branch comparison tables, currently split into two tiers by Power BI purely for layout; the web app doesn't need that split (no per-page real-estate constraint) and could show one filterable table — **worth revisiting rather than blindly copying the tier split**.

## 16.2 Required interactivity

- **Filters:** date range, sucursal (single or multi-select — Power BI's tier tables show all branches at once, the per-branch pages show one at a time; the web app should support both modes), and mes/año.
- **Charts must be genuinely interactive** (hover tooltips, filter-driven re-render), not static images — implies a JS charting layer (Chart.js / ECharts / Plotly, or Django + HTMX + a charting library) rather than server-rendered PNGs.

## 16.3 Access control — role levels named by the user

- Dirección
- Gerente
- CGI
- Usuario básico
- Administrador general

**Open design questions, not yet answered — flag to the user before building the permission model:**
- Which branches can each role see — all branches (Dirección/Admin), only their assigned branch (Gerente), or something else (CGI)?
- Which pages/domains does each role see — does "Usuario básico" see Ventas only, or everything read-only?
- Does any role get write/edit access (e.g. approving product mappings, per the existing `inventory_mapping_dictionary` review workflow), or is this entirely read-only reporting?
- Is "CGI" a specific person/department acronym internal to Fonda Argentina that needs a specific defined scope, or a generic tier name still to be defined?

## 16.4 Tech stack notes

- **Django**, matching the precedent already set on `ControlPresupuestos_AP` (same user, same organization, already running on port 8010 per that project's convention — this new app should pick its own dedicated port, not default 8000, following the same pattern).
- Given `ControlPresupuestos_AP`'s own permission model is referenced elsewhere in this user's projects as a precedent (see project memory `project_chatbot_far_django_migration_plan` — "ControlPresupuestos_AP-style permissions" was already the chosen pattern for a *different* project's Django migration), reuse that same permission architecture here if it fits, rather than designing role-based access from scratch.
- Data layer: read directly from the existing unified MySQL tables (`analytics_purchase_daily_company_product`, `costeoMensual`, `getallordenesbyday_new_venta`, etc.) — no need to duplicate data into a separate application database; Django models can map onto the existing warehouse schema (likely via `inspectdb`/unmanaged models) or a dedicated read-optimized view layer can be added if query performance demands it once real usage patterns are known.

## 16.5 Explicitly out of scope for this pivot (unchanged from before)

The underlying ETL/data-warehouse work (Sections 2-13) is unaffected by this pivot — it continues exactly as-is. Only the *delivery* layer changes.

---

# 17. Production Infrastructure & Migration Action Plan

**Context as stated by the user:** the current production virtual server runs on **Hyper-V**. The plan is to back it up, then evolve it in place (the user's own words: "respaldarlo antes de tronarlo" — back it up before blowing it away, referring to retiring the *old legacy scripts/tasks*, not the VM or database itself) to host the new pipeline + Django app, with the codebase kept in sync from GitHub on a recurring daily basis, and all old scheduled tasks on the server replaced by a single new one for this pipeline.

## 17.0 Open questions — resolved 2026-09-23

| Question | Answer |
|---|---|
| What runs on the Hyper-V VM today? | The legacy Python scripts currently in production, reading only from Wansoft — set up as Windows Scheduled Tasks firing at different times each day. **This is very likely the same process responsible for the still-unidentified duplicate Wansoft Purchases/Inventory loading for the 5 already-Odoo-migrated branches (Section 3.5/13)** — expect Step 5 below to resolve that backlog item as a direct side effect, not a coincidence. |
| Rebuild from scratch or reuse in place? | **Reuse the VM and its existing database in place** — it holds real historical data that must be preserved. No fresh-OS rebuild. This changes the framing of Step 1 below: the backup is a safety net for an in-place evolution, not a pre-wipe snapshot. |
| Target OS/stack? | **Windows, same as dev** — no OS migration, same Python/Anaconda-style environment and Windows Task Scheduler as the mechanism. Confirmed, removes a whole axis of risk. |
| Target go-live date? | **2026-10-01** — deliberately chosen to coincide with the already-planned Odoo cutover for Isabel La Católica, Vía Vallejo, and San Jerónimo (see project memory `project_october_migration_wave`, unrelated in origin to this migration but now explicitly coordinated with it). On that date, all 10 Odoo-sourced branches (the current 7 plus these 3) start fresh with Odoo data flowing through the new production pipeline in the same rollout — no historical Odoo backfill needed for the new branches, and no delay to either plan. |

**Given the reuse-in-place decision, the plan is no longer "rebuild then deploy" — it is "back up, then safely evolve the same VM/DB":** schema gets extended (not replaced), the new pipeline code gets deployed alongside the legacy scripts first, and only once the new pipeline is confirmed working does cutover happen — removing the legacy Scheduled Tasks and the code they ran.

### Step 1 — Back up the VM and the database before touching anything
1. Take a full **Hyper-V export** (or checkpoint + export) of the VM in its current state — this captures the OS, any locally-installed services, and file system state as a restorable unit.
2. Independently of the VM-level export, take a **logical backup of every production MySQL database** the server hosts (`mysqldump` per database, or a full binary backup if the databases are large) — a VM export alone is not a substitute for a verified, restorable database dump.
3. Verify the backup is actually restorable (test-restore the mysqldump into a scratch database, at minimum) before proceeding to any destructive step — do not treat "backup completed" as "backup verified."
4. Store both the VM export and the database dumps somewhere **off** the VM itself (a backup is worthless if it lives only on the machine it protects) — this is a safety net for an in-place change, not a pre-wipe snapshot (Section 17.0: the VM and database are being reused, not rebuilt).

### Step 2 — Provision the new environment and migrate the schema
1. Diff the **production** MySQL schema against **dev**'s current schema (dev has months of iteration production doesn't have — new tables like `costeoMensual`, `canonical_purchase_order_snapshot`, `analytics_purchase_daily_company_product`, `dim_company_analytical`, etc., and columns added to existing tables).
2. Generate the missing pieces as explicit, reviewable SQL: `CREATE TABLE` statements for tables that don't exist in prod yet, and `ALTER TABLE ... ADD COLUMN` statements for existing prod tables that are missing columns dev already has (e.g. any table involved in the `.env` lookback-window changes, and anything from the Costs domain build-out in Section 3.4, which prod has never had at all).
3. Apply in dependency order (dimension tables before fact tables that reference them, base tables before the analytics tables built on top of them) — mirror the same build order the daily pipeline itself uses (`pipelines/scheduler.py`'s own step ordering is a good reference for this).
4. Carry forward `sql/maintenance/add_unique_keys_dedup_protection.sql` (already flagged in the backlog, Section 13) as part of this same migration pass, not as an afterthought.
5. Set up the production `.env` with all the same lookback/config variables dev now uses (`SALES_LOOKBACK_DAYS`, `WANSOFT_LOOKBACK_DAYS`, `PURCHASES_LOOKBACK_DAYS`, plus the corrected `XML_DOWNLOAD_DIR_DEV`-equivalent path for whatever the production download directory should be) — these do not travel via git (gitignored) and must be set by hand on the new server.

### Step 3 — Deploy the application code
1. Clone the repository fresh onto the new/rebuilt server rather than copying files by hand, so the server's checkout is a real git working tree from the start.
2. Install the same dependency set dev uses (Python packages, MySQL connector, any Odoo XML-RPC libraries) — capture dev's actual installed versions (`pip freeze` or equivalent) as a `requirements.txt`/environment spec if one doesn't already exist in the repo, so the production install isn't a guess.
3. Deploy the new Django app (Section 16) alongside the existing pipeline codebase — same repo, same server, following the `ControlPresupuestos_AP` precedent of a dedicated port.

### Step 4 — Link the server to GitHub for recurring daily auto-updates
1. Add a Windows Task Scheduler task (confirmed staying on Windows, Section 17.0) that runs `git pull` against `origin/main` on a daily cadence, **before** the daily pipeline run itself, so each day's run reflects that day's latest committed code.
2. Decide whether this should be a simple `git pull` step chained in front of `pipelines/scheduler.py`'s existing daily-trigger logic, or a separate, independent scheduled task — recommend chaining it into the same task that launches the daily cycle, so a pull failure is visible in the same place as a pipeline failure, rather than as a silent, separate process.
3. This mirrors the precedent already used for the `Chatbot_FAR` project's own dev/prod boundary (production deployed via GitHub pull) — reuse that same pattern here rather than inventing a new one.

### Step 5 — Clean up scheduled tasks, leave only the new one
1. Inventory every existing scheduled task on the server (this is also how the still-unidentified production duplicate-Wansoft-loader from Section 3.5 will finally get found and understood — it must be running from *some* scheduled task or service on this box today).
2. Once the new consolidated pipeline (git-pull + daily cycle, Step 4) is confirmed working end-to-end, remove every other scheduled task on the server — including whatever has been driving the duplicate Wansoft Purchases/Inventory loading for the 5 already-migrated branches (Section 3.5/13), resolving that long-standing backlog item as a natural side effect of the migration rather than a separate cleanup project.
3. Leave exactly one scheduled task in place: the new pipeline's daily trigger.

## 17.1 Target timeline — go-live 2026-10-01

Proposed 2026-09-23, not yet confirmed day-by-day with the user beyond the go-live date itself:

| When | What |
|---|---|
| Now → 2026-09-26 | Inventory every existing Scheduled Task on the Hyper-V VM (Step 5.1, done early so it informs everything else). In parallel, work the still-open pre-cutover checklist from `project_october_migration_wave` for Isabel La Católica/Vía Vallejo/San Jerónimo: confirm the 2024-pilot Odoo data wipe actually happened, and confirm real Odoo purchase/inventory activity has genuinely started for all three — don't assume from old snapshots. |
| 2026-09-26 → 2026-09-28 | Step 1: full backup (VM export/checkpoint + verified-restorable `mysqldump` of every production database), stored off-VM. Nothing destructive happens before this is verified. |
| 2026-09-28 → 2026-09-29 | Step 2: schema diff (prod vs. dev) and migration scripts prepared and reviewed; prod `.env` drafted with the lookback config and any path corrections it needs. |
| 2026-09-29 → 2026-09-30 | Step 3: deploy the new pipeline codebase (fresh `git clone`) **alongside** the still-running legacy scripts — no cutover yet, this is side-by-side. Apply the schema migration to the real production database. Dry-run the new pipeline against production data in a way that doesn't write anywhere the legacy scripts also write, if at all possible. |
| 2026-09-30 (evening) | Final backup immediately before cutover. |
| **2026-10-01** | Go-live, coordinated with the existing Odoo cutover for Isabel La Católica/Vía Vallejo/San Jerónimo: flip `COMPANY_SOURCE` for the 3 new branches per the standard rollout sequence (`project_october_migration_wave`), Step 4 (GitHub daily `git pull` wired in), then Step 5 (remove every legacy Scheduled Task, leave only the new consolidated one). Monitor the first live run closely. |
| 2026-10-01 → 2026-10-03 | Re-validate against the user's Power BI now that real production data is flowing through the new pipeline for all 10 Odoo-sourced branches at once — same methodology as Section 14/15. |

**This section is a plan, not yet executed.** No infrastructure work has started. The core open questions (VM role, rebuild vs. reuse, target OS, go-live date) were resolved with the user on 2026-09-23 (Section 17.0); the day-by-day timeline above is a proposal pending the user's confirmation before Step 1 begins.

## 17.2 Production VM scheduled-task inventory (exported 2026-09-23 via `Get-ScheduledTask`)

**12 legacy tasks named `FondaCroned_*`**, all daily, all running an older **loose copy** of the legacy scripts from `C:\Users\AnalisisBI\Desktop\CronedJobs_Python\` (not this repository) under the `tf_env` miniconda interpreter:

| Time | Task / script |
|---|---|
| 01:00 | `getExpenses.py` |
| 01:05 | `getInputInventory.py` |
| 03:15 | `getTotalCostByDate.py` |
| 03:30 | `descargarCostoWansoft.py` |
| 03:35 | `getGlobalCashClosing.py` |
| 03:40 | `getAllOrdersByDay.py` |
| 04:00 | `extractAllOrdersByDay.py` |
| 04:30 | `getCostReport_SemanaPyQ.py` |
| 04:45 | `getTablajeriaReport.py` |
| 05:15 | `getOutgoingInventory.py` |
| 06:10 | `zenput_mysql-forms.py` |
| 06:30 | `zenput_mysql-tasks.py` |

**Findings:**
1. **This is almost certainly the source of the production duplicate Wansoft Purchases/Inventory loading** (Section 3.5): `getExpenses`, `getInputInventory` and `getOutgoingInventory` run from an older copy that predates the `is_wansoft_company()` routing, so they load all 19 branches including the 5 already on Odoo. Still to verify by reading that copy's code before treating it as confirmed.
2. **`getAllOrdersByDay.py` (03:40) is still scheduled in production**; dev deliberately excludes it (it downloads a fixed date range; the Candado `extractAllOrdersByDay.py` is the intended Sales job). Retire it at cutover.
3. Production uses 12 fixed, staggered times between 01:00 and 06:30; dev runs the same steps as a single sequential chain from 01:00 (~27 min end to end). None of the Odoo-side jobs exist in production yet: inventory pipeline, purchases pipeline, analytics purchase rebuild, cutover validation, weekly product mapping.
4. **The VM also hosts `ControlPresupuestos_AP`** (a different live project, `C:\Apps\ControlPresupuestos_AP`, own `.venv`) with 4 tasks: `Arranque automatico` (`deploy\update.ps1`, an existing git-update pattern on this very VM, reuse it for Step 4), `Catalogos mensual` (next run 2026-10-01 04:00, go-live day), `Gastos reales AM` (05:00) and `Gastos reales PM` (14:00). **These are out of scope for the Step 5 cleanup**: "leave only one task" applies to the Wansoft/Zenput pipeline's tasks only. Pending user confirmation.
5. Edge and OneDrive tasks are system tasks, untouched.

**Implications for cutover:** remove the 12 `FondaCroned_*` tasks; run the new pipeline from a dedicated venv (not `tf_env`); for the Sept 29-30 rehearsal, restore the verified backup into a staging database on the same VM and run the new pipeline against it, rather than against the live database while the legacy tasks still write to it.

## 17.3 Weekly backup system (decided 2026-09-23)

**Decision (user):** the dumps stay on the same machine as the database, run weekly, and only the last two are kept. Trade-off: if that machine's disk is lost, the dumps go with it, so the one-time Hyper-V export taken from the host before go-live (Step 1) is still worth doing.

**Topology correction (2026-09-23, later):** the machine that runs the `FondaCroned_*` tasks (the one inventoried in 17.2) does NOT host MySQL or phpMyAdmin: nothing listens on ports 3306/3307/8088 there. The database lives on a different machine (`187.251.203.223`, phpMyAdmin on :8088), whose exact identity (another VM on the same Hyper-V, or a separate server) and remote-desktop access are still to be confirmed. The backup scripts must therefore run on the database machine; the fallback is running them from the tasks machine against the database over the network (needs `mysqldump.exe` installed there and a `backup` user allowed from that machine's IP, with `host=` in `backup.cnf` pointing at the database). The 410.6 GB free-space figure below belongs to the tasks machine; free space on the database machine has not been checked yet, and it matters for the staging-copy rehearsal. Planned for 2026-09-24: identify the database machine, check its free space, install the backup scripts there and run the first backup after business hours.

**Facts that shaped it:** production is MariaDB 10.4.28, every table is InnoDB (so `mysqldump --single-transaction` does not block writes and can run while the nightly tasks are working), the `wansoft` schema is 31.01 GB (others: `odoo` 0.06, `zenput` 0.03, `presupuestos_ap` 0.01) and the tasks machine's drive C: has 410.6 GB free (the database machine's free space is unchecked). Production has 22 tables in `wansoft` against dev's 57 plus 2 views, so the schema migration (Step 2) is bigger than "a few missing columns".

**Implementation, in `deploy/backup/`:**
- `backup_mysql.ps1`: one gzip'd dump per database (no `--databases`, so a dump can be restored under any name), verifies the dump's completion marker and that the gzip reads back fully, keeps the newest 2 complete runs and prunes only after a run succeeds; a failed run removes its own partial folder and leaves the good backups untouched.
- `restore_mysql.ps1`: restores one database into a staging database and refuses protected live names.
- `register_backup_task.ps1`: registers `Wansoft_Backup_MySQL_Semanal` (SYSTEM, Sundays 07:30).
- Backups use a dedicated read-only MariaDB user; credentials live in `C:\Backups\mysql\backup.cnf` on the VM, outside the repo.
- Tested on dev against `zenput`: retention keeps exactly 2, the failure path keeps the earlier backups, and a restore reproduces identical row counts.

**Step 5 update:** after go-live the pipeline's daily task is no longer the only new task on the VM; the weekly backup task stays alongside it (plus `ControlPresupuestos_AP` and the system tasks).

---

# 18. Next Steps — HANDOFF PROMPT

**Paste this as the first message when resuming:**

```
Continúo el proyecto Wansoft + Odoo + Zenput Data Warehouse & ETL Pipeline.
Lee completo PROJECT_CONTEXT_REPORT.md en la raíz del repositorio antes de
responder, especialmente la Sección 0 (ambiente), la Sección 11 (log
combinado de bugs), la Sección 16 (el pivote a Django) y la Sección 17
(plan de migración de infraestructura).

Resumen rápido: en las tres sesiones pasadas (21, 22 y 23 de sept) se hizo
sobre todo trabajo de validación, no construcción nueva de dominios. Se
hicieron configurables las ventanas de revisión del job diario (antes
hardcodeadas), se corrigió un bug real en la extracción de compras de Odoo
(contaba cotizaciones sin confirmar como compras reales), y se validó en
vivo contra tu Power BI real Ventas, Costos, Meseros y Compras para 4
sucursales representativas (Acoxpa, Coyoacán, San Jerónimo, Oceanía),
septiembre a la fecha. Ventas y Meseros coinciden exacto en las 4, sin
excepción. Costos coincide exacto una vez que se toma en cuenta el
refresh de Power BI. Compras necesitó una corrección real de metodología:
para sucursales en Odoo hay que comparar solo contra la cuenta "Costo
operativo" de Wansoft, no el total completo de la página (que mezcla
gastos que Odoo nunca va a capturar, como una suscripción de software que
encontramos en Coyoacán). Confirmaste que con estas 4 sucursales ya
quedó demostrado que el proceso es correcto -- no hace falta validar las
19.

Lo más importante de esta sesión: DECIDISTE UN CAMBIO DE RUMBO GRANDE. Ya
no vamos a migrar tus reportes de Power BI existentes -- vamos a construir
una aplicación web nueva en Django que replique esas mismas páginas
(Ventas Totales, Score Card, Meseros, Compras Mensuales, Entradas de
Inventario, Scorecards) con filtros interactivos de fecha/sucursal/mes y
gráficas interactivas, con niveles de acceso (Dirección, Gerente, CGI,
Usuario básico, Administrador general). Ver Sección 16 para el detalle y
las preguntas de diseño todavía abiertas (qué ve cada rol).

También pediste un plan de migración de infraestructura: tu servidor
virtual está en Hyper-V, quieres respaldarlo antes de reconstruirlo,
desplegar ahí el pipeline + la app nueva (creando/actualizando las bases
de datos que falten), dejarlo enlazado a GitHub para que se actualice
solo cada día, y al final limpiar las tareas programadas del servidor
dejando solo la de este pipeline nuevo. Ver Sección 17 -- es un plan, no
se ha ejecutado nada todavía, y tiene preguntas abiertas al inicio que
hay que resolver antes de empezar (qué corre hoy exactamente en ese
Hyper-V).
```

**Suggested title for the new chat**: `FONDA (Wansoft): Paso 24: Validación con Power BI cerrada, pivote a app Django + plan de migración a servidor`

---

# Permanent Rule

Regenerate this document in full (never as patches) when: the user explicitly asks, a major step closes, the conversation gets very long, context exceeds ~70%, or a new chat needs to be opened due to token limits. In that last case, also generate:
1. The handoff prompt (Section 18, first code block, if applicable).
2. The suggested title for the new chat, in the format **`FONDA (short project): Paso N[-M]: <short description>`** (same style as the user's own session list). `FONDA` is a fixed prefix; `(short project)` identifies which project (here: "Wansoft"). Use `N` = the major step/block number in progress, `-M` = sub-part suffix if the step spans multiple consecutive sessions/chats.

**Note on language:** this document, all commit messages, and all documentation pushed to GitHub in this project must be written in English — even though the working conversation with the user is in Spanish. See project memory `feedback_github_content_english_only` for the full rule.
