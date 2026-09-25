# PROJECT_CONTEXT_REPORT.md

Master continuity document. Generated/updated automatically at the close of major steps, on explicit request ("Generate project context report"), when the conversation gets very long, when consumed context exceeds ~70%, or when a new chat needs to be opened due to token limits. Always regenerated in full, never as an incremental patch.

Last generated: 2026-09-25 (Friday), closing the session because the context window is running out; it covers 2026-09-24 and 2026-09-25 on top of the earlier sessions kept below. This stretch was **infrastructure, not warehouse logic**: a production backup system was built and its first real run completed, the tasks VM was set up with the new code and a daily GitHub update, a run-once daily orchestrator was written, and the **go-live week (Mon 2026-09-28 to Thu 2026-10-01)** was planned. **Read this first if you're picking this up fresh, especially Section 0 (the two production machines), Section 17 (production infrastructure: current state, go-live week and cutover checklist) and Section 18 (handoff).**

---

# 0. Critical environment note — READ FIRST

## 0.1 The dev PC

**The project's working directory moved.** OneDrive redirected the user's Desktop to the organization's OneDrive path around 2026-09-15 13:10-13:40. The old path (`C:\Users\JavierViniegra\Desktop\AnalisisRestaurantesBI\...`) is permanently empty and will stay that way — do not try to "restore" it.

**Current correct path:**
```
C:\Users\JavierViniegra\OneDrive - GRUPO FONDA ARGENTINA\Escritorio\AnalisisRestaurantesBI\Wansoft\Jupyter Notebooks\Python Files
```

The shell/harness's own default working directory still resets to the old (dead) path after every command in this environment — every command needs an explicit `cd` to the OneDrive path, or an absolute path. This is a session/tooling quirk, not a project issue.

**MySQL dev is not a Windows service (deliberate, prior decision — do not re-suggest making it one).** It does not auto-start with the machine. If a dev DB connection fails at the start of a session (`Can't connect to MySQL server on 'localhost:3306'`), ask the user to start it rather than debugging further. Dev is MariaDB 10.4.32 under XAMPP (`C:\xampp\mysql\bin`).

`core/config/.env` on the dev PC has `ENV=dev` and its `XML_DOWNLOAD_DIR_DEV` was corrected to the OneDrive path on 2026-09-17 (bug log #21). `.env` is gitignored, so every machine needs its own.

Git and `.env` (credentials) both survived the OneDrive move intact.

## 0.2 The two production machines — do not mix them up (confirmed 2026-09-24/25)

| | Tasks VM | Database machine |
|---|---|---|
| Name / address | `DESKTOP-1HTRVT4` (Hyper-V guest) | `DESKTOP-5DELBQN`, internal `192.168.100.183`, public `187.251.203.223` |
| Windows account that runs things | `analisisbi` | (RDP administrator) |
| What it hosts | The 12 legacy `FondaCroned_*` scheduled tasks, the separate live project `ControlPresupuestos_AP` (`C:\Apps\ControlPresupuestos_AP`, 4 tasks), the new pipeline (`C:\Apps\Wansoft_ETL` with `.venv`, Python 3.12), the backups (`C:\Backups\mysql`, 412 GB free), the MariaDB client tools (`C:\Backups\mariadb-client\mariadb-10.4.28-winx64\bin`) | XAMPP **MariaDB 10.4.28**, datadir `C:\xampp\mysql\data\`, binary log off, all tables InnoDB; phpMyAdmin on plain http port 8088 |
| Does NOT host | MySQL or phpMyAdmin (nothing listens on 3306/3307/8088) | Any pipeline or task |
| Free disk | 412 GB on C: | 258 GB on C: |

Databases (`wansoft` is the big one): `wansoft` 31 GB on disk (about 16 GB of data plus 15 GB of indexes, 22 base tables, zero views/triggers/routines/events), `zenput`, `odoo`, `presupuestos_ap`, `mysql`, `phpmyadmin`, `test`. The tasks VM reaches the database over the internal network (`192.168.100.183`); the dev PC reaches it through the public IP with read-only credentials for comparisons. **phpMyAdmin is served unencrypted on a public IP: restrict it after go-live.**

**Hard rule until cutover:** the new pipeline must never write to the real `wansoft` / `zenput` databases before go-live, because the legacy tasks still write to them every night. The tasks VM `.env` points at `wansoft_prueba` / `zenput_prueba` on purpose (Section 17.4).

---

# 1. Executive Summary

**Overall project goal:** build a unified analytical layer in MySQL that integrates Wansoft, Odoo, and Zenput, hiding from the end user which system originates each piece of data.

**Delivery layer goal (decided 2026-09-23, Section 16):** no longer "repoint the user's Power BI reports at the unified layer"; instead a **new Django web application** replicating the validated Power BI pages with interactive filters and charts and role-based access (Dirección, Gerente, CGI, Usuario básico, Administrador general). Power BI is now the validation reference, not the target. Not started yet; the role scopes are still undefined.

**Data-warehouse state:** the acceptance gate remains formally accepted (2026-08-31). Sales, Meseros, Costs and Purchases were validated live against the user's Power BI for four representative branches (Acoxpa, La Esquina Coyoacán, San Jerónimo, Oceanía; September 2026): Ventas and Meseros exact everywhere, Costos exact once refresh timing is accounted for, Compras understood after correcting the comparison scope (Sections 6, 14, 15). The user confirmed that is enough; the remaining 15 branches are not validated individually.

**Infrastructure state (this stretch, Section 17):**
- **Backups:** a weekly MariaDB backup system exists (`deploy/backup/`), keeps the 4 most recent runs, verifies each dump, and warns about databases missing from its list. The first real backup completed on 2026-09-24 (`wansoft` 3.38 GB compressed from about 24 GB of SQL, 29.8 minutes over the internal network). A first attempt failed on a real bug (Int32 overflow above 2 GB, bug #25), fixed and re-run.
- **Tasks VM deployment:** repository cloned to `C:\Apps\Wansoft_ETL`, virtual environment with pinned `requirements.txt`, `.env` in place, and a daily GitHub update task (00:30) verified end to end.
- **Run-once orchestrator:** `scripts/run_daily_cycle.py` plus PowerShell wrappers, prepared but the task is registered **disabled**.
- **Restore rehearsal:** a one-time task restores the backup into `wansoft_prueba` at 22:00 on Friday 2026-09-25; `zenput_prueba` exists and awaits its restore.

**Go-live:** Thursday **2026-10-01**, coordinated with the Odoo cutover of Isabel La Católica, San Jerónimo and Vía Vallejo, so all 10 Odoo-sourced branches start together. The week before is a shadow run on test databases (Section 17.5). Definitive daily pipeline time: **01:30** (the latest cash closing in 30 days was 01:07).

**Current block:** the go-live week. First action on Monday 2026-09-28: read the restore log, then apply the schema migration to `wansoft_prueba` (41 tables, 2 views, 5 columns missing versus production).

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

### Deployment / operations (new, Section 17)
Production is being moved to the new pipeline in place: the tasks VM now has the code, environment, daily GitHub update and a disabled run-once daily task; backups run weekly from the tasks VM against the database machine. Nothing writes to the real production databases from the new code yet.

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
| Run-once orchestrator (`scripts/run_daily_cycle.py`) instead of the timer-based `pipelines/scheduler.py` | `scheduler.py` is a long-running process with threads and timers; Windows Task Scheduler wants a program that runs and exits with a status. The orchestrator runs every stage in order, continues after a failed stage, and exits non-zero if any failed | `scripts/run_daily_cycle.py`, `deploy/run_daily_cycle.ps1` |
| The four subprocess-based jobs raise when their pipeline exits non-zero (`check=True`) | They used to ignore the exit code, so a failed pipeline looked like a successful stage; an unattended job has to fail loudly | `pipelines/jobs/{inventory,purchases,analytics_purchase,product_mapping_backlog}_job.py` |
| Daily pipeline task registered **disabled** unless `-Enable`; tasks VM `.env` points at `_prueba` databases | Until cutover the legacy tasks still write to the real databases; an accidental run must fail with "unknown database" instead of writing to production | `deploy/register_daily_cycle_task.ps1`, the VM's `.env` |
| Daily pipeline time 01:30 (not 23:30, not 06:00) | 550 cash closings in 30 days: 17% at or after 23:30, latest 01:07; at 01:30 all closings exist, the cycle ends about 02:00 and a failure leaves hours to retry. The code loads through yesterday only, so 23:30 would not capture the current day either | `Wansoft_Pipeline_Diario` |
| Backups: per-database gzip dumps taken over the internal network from the tasks VM, kept on the tasks VM, `--single-transaction`, keep 4, weekly | The user wanted backups separate from the database machine; all production tables are InnoDB so the dump does not block writers; dumps without `--databases` restore under any name | `deploy/backup/` |
| The daily GitHub update task runs as `analisisbi` with its stored password | Git Credential Manager credentials are stored per Windows user, so SYSTEM cannot use them | `deploy/update_repo.ps1`, `deploy/register_update_task.ps1` |
| Restore rehearsal into `wansoft_prueba`, then a shadow run on test databases for three days before cutover | Proves the backups restore and the new environment reproduces what the legacy tasks produce, without touching production | Section 17.5 |

---

# 9. Business Rules Implemented / Reinforced

- **Costs governance is per-branch, three states, not a domain-wide flag:** Wansoft-migrated vs. pure-Odoo vs. the Cortesias/Cancelaciones Sales-adjacent override that ignores both and always uses Wansoft's sale-value figure.
- **Internal-provider exclusion is about the buying company, never the vendor alone** — a real branch buying from an internal kitchen (El Bodegon, Las Empanadas) is a real purchase for that branch.
- **A weekly automated job must never downgrade or silently relabel a human review decision** — every field of an already-reviewed row stays untouched on re-run.
- **`getglobalcashclosing` is a legitimate, Wansoft-sourced, always-available report for every branch regardless of Purchases/Inventory/Costs migration status** — same tier as Sales itself.
- **Odoo purchase orders only represent goods procurement.** Service/subscription/payroll/administrative spend recorded in Wansoft under other `Cuenta` buckets (Gastos Directos, Sueldos y Salarios, etc.) has no Odoo purchase-order equivalent by design — it is not a gap to chase.
- **A daily job's re-check window is a tuning knob, not a constant.** It should live in `.env`, not be hardcoded per-script, so it can be widened (to self-heal after a missed run) or narrowed (to keep the daily cycle fast) without a code change.

- **Nothing new writes to production before cutover.** Test databases (`wansoft_prueba`, `zenput_prueba`) are the only targets until the cutover checklist (Section 17.6) is executed.
- **An unattended job must fail loudly and leave a log.** Every scheduled piece of the new stack writes a dated log under `logs\` (or the backup folder) and exits non-zero on failure; a failed backup never deletes good backups.
- **Backups are only real once restored.** The weekly dump is verified for completeness and readability, but the proof is the restore rehearsal with a row-count comparison.

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


- **Windows shows a file that another process is writing as 0 MB or with a stale size** in directory listings; open it with `FileShare.ReadWrite` (`[IO.File]::Open(path,'Open','Read','ReadWrite')`) to read its real length.
- **`[Math]::Min(512, $file.Length)` in PowerShell binds to the Int32 overload and throws for files over 2 GB**; cast one argument to `[long]`. Tests with tiny files cannot catch this class of bug; use a synthetic file above 2 GB (`fsutil file createnew`).
- **`icacls` with account names fails on a Spanish Windows** (`Administradores`); use SIDs: `*S-1-5-18` (SYSTEM) and `*S-1-5-32-544` (Administrators).
- **Git Credential Manager is per Windows user**: a scheduled task that needs GitHub access must run as that user with its password. A non-elevated token of an admin user cannot read a file whose only grants are the Administrators group (deny-only SID); the tasks are registered with `-RunLevel Highest`.
- **`git clone` into a very deep path fails on Windows** ("Filename too long"); the scratch folders under the harness's temp directory are too deep for it, use a short path such as `C:\Users\JavierViniegra\wsc`. The harness also blocks `Remove-Item` on `C:\Temp`.
- **phpMyAdmin shows "#1046 Base de datos no seleccionada" after a successful `CREATE DATABASE`/`GRANT`**; it is only the failed attempt to display a result. Verify with `SHOW DATABASES` and `SHOW GRANTS`.
- **PowerShell 5.1**: `&&` is not available; native stderr under `$ErrorActionPreference='Stop'` becomes a terminating error, so wrap native calls with `Continue`; `Start-Transcript` works in scheduled tasks; passing an array to `powershell -File ... -Param $array` splits it into separate arguments.
- **A Python heredoc containing `C:\Users\...` in a normal string fails with a unicode-escape error**; write such text with the file tool or use raw strings.
- **`mysqldump` writes a `-- Dump completed` marker** at the end of a finished dump; the backup script uses it as the completeness check.
- **Windows Task Scheduler sequencing**: `Set-ScheduledTask -Trigger` on a running task should be done after the run ends; the `MultipleInstances IgnoreNew` setting makes a second trigger during a run a no-op.

**Git state:** branch `main`, up to date with `origin/main` through commit `9e64483` (plus the commit that carries this report). `inventory_not_found_analysis.csv` remains permanently uncommitted per convention. Loose untracked files at the repo root (`extractAllOrdersByDay.py`, `extractAllOrdersByDay_old.py`, `getAllOrdersByDay.py`) remain unexplained, not touched.

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
| 24 | Odoo purchase extraction had no `state` filter at all: unconfirmed RFQs (`state='sent'`) counted as real business purchases, inflating Compras for every Odoo-migrated branch | `extract/purchases/odoo_purchase_orders.py`, `odoo_purchase_order_lines.py` | **Fixed 2026-09-22** |
| 25 | The backup script's completeness check used `[Math]::Min(512, $fs.Length)`, which binds to the Int32 overload and throws for any file over 2 GB; a real 24 GB dump was rejected and its folder deleted (first attempt, 2026-09-24 14:36). Found only because earlier tests used tiny dumps | `deploy/backup/backup_mysql.ps1` | **Fixed 2026-09-24** (`[long]512`), verified on a 3 GB synthetic file |
| 26 | The four subprocess-based jobs ignored their pipeline's exit code, so a failed pipeline looked like a successful stage in any orchestrator | `pipelines/jobs/inventory_pipeline_job.py`, `purchases_pipeline_job.py`, `analytics_purchase_pipeline_job.py`, `product_mapping_backlog_job.py` | **Fixed 2026-09-25** (`check=True`). Note: the in-process legacy chain steps still swallow per-day errors internally (they print `[❌]` and continue); those are visible only in the logs |

**Also confirmed NOT bugs:**
- Oceanía's Costos mismatch on 2026-09-23: Power BI's own Costos page was one day behind its Wansoft source; dev's prior-day snapshot matched exactly.
- San Jerónimo's near-doubled Entradas de Inventario figure: a report-scope mismatch (`TipoEntrada='Factura'` filter) plus one legitimate invoice dev had that Power BI's refresh didn't have yet; not a duplicate insert.
- Coyoacán's -26% Compras gap: a comparison-scope mistake (Odoo against Wansoft's full Compras total instead of `Costo operativo`); about 79% of it was one legitimate software/admin vendor Odoo never captures.
- Power BI's Meseros table excluding the delivery/app placeholder waiter from its ranked total: a report display choice.
- The first backup attempt over the public IP was simply slow (the path leaves the network and returns); switching to the internal IP fixed it.
- `wansoft.sql` showing 0 MB while being written, and phpMyAdmin's #1046 after successful statements: display artifacts (Section 10).

**Gate result:** unchanged, not reopened.

---

# 12. User Decisions (explicit, don't lose track of these)

**Warehouse and validation**
- **Confirmed (2026-09-17):** Cortesias/Cancelaciones use `getglobalcashclosing`'s sale-value figure for all 19 branches uniformly, not a cost-basis conversion; it will keep differing from Power BI until Power BI is repointed.
- **Confirmed (2026-09-17):** a real inventory-valuation build for pure-Odoo branches is genuine future work.
- **Confirmed (2026-09-15):** the weekly product-mapping job runs Sundays 11am.
- **Confirmed (2026-09-21):** `WANSOFT_LOOKBACK_DAYS` is 5 for the daily cycle.
- **Confirmed (2026-09-23):** validating Acoxpa, Coyoacán, San Jerónimo and Oceanía against Power BI is sufficient; no standing requirement to validate the other 15.
- **Confirmed (2026-09-23), the pivot:** the delivery layer will be a new Django web application, not a Power BI repoint (Section 16).

**Production infrastructure**
- **Reuse the existing VMs and the existing database in place** (they hold history); no rebuild. Stay on Windows. Go-live **2026-10-01**, coordinated with the Odoo cutover of Isabel La Católica, San Jerónimo and Vía Vallejo (the user confirmed Vallejo also starts that day).
- The 12 legacy `FondaCroned_*` tasks **keep running until go-live and are removed at go-live, not before**. The `ControlPresupuestos_AP` tasks and the system tasks stay untouched. Production's duplicate Wansoft Purchases/Inventory loading is not touched until then; it is expected to disappear when those tasks are removed.
- **Backups:** kept separate from the database machine (stored on the tasks VM), taken over the internal network, weekly on Thursdays 18:00 (first automatic run 2026-10-01), **4 kept** (first 2, raised to 4), all 7 real databases. Sacred rule: never touch the running production backup job mid-run.
- **The daily GitHub update** runs every day at 00:30 and the `update.ps1` pattern from `ControlPresupuestos_AP` was reused and adapted.
- **Daily pipeline at 01:30**, after considering 23:30 and 06:00 (Section 17.4). During the shadow week the task runs at 07:00.
- **Go-live week plan (2026-09-28 to 2026-10-01):** test on the `_prueba` databases Monday to Wednesday, go/no-go Wednesday night, cutover Thursday.
- The user prefers to be walked step by step, with one command per block, and works in short windows (about 80 minutes at a time); keep steps small and verifiable.

---

# 13. Identified Legacy / Consolidated Backlog

## Go-live week (in order)
1. **Mon AM: read the restore rehearsal log** (`C:\Backups\mysql\20260924_144209\restore_wansoft_prueba.log`, task `Wansoft_Restore_Ensayo` ran Fri 22:00). Expect per-table `DIFF` where the legacy tasks loaded data after the Thursday 14:42 snapshot (Friday 01:00-06:30 loads): the copy must have **fewer or equal** rows than production, by about one day of loads. More rows than production, or far fewer, would be a problem.
2. **Restore `zenput` into `zenput_prueba`** (database and grants were created in phpMyAdmin on 2026-09-25; the restore command is in Section 17.5). Expect `DIFF` there too (Zenput tasks run 06:10 and 06:30).
3. **Schema migration onto `wansoft_prueba` only:** 41 tables and 2 views to create (`vw_inventory_non_physical_snapshot`, `vw_inventory_physical_snapshot`) and 5 columns to add (`created_date` on `costeomensual`, `costeomensual_semanapyq`, `gettotalcostbydate`; `campo1` and `campo2` on `getallordenesbyday_venta`); the 6 production-only legacy tables (`getallordenesbyday_detalleventa`, `getallordenesbyday_modificador`, `getcostreport`, `getexpensesbyinputdate`, `getpendingpurchaseorders`, `getpendingpurchaseorders_details`) are left untouched; no type differences on the 16 common tables. Generate the DDL from dev's `SHOW CREATE TABLE` as a reviewable SQL file. Also identify which of the 41 tables hold **non-rebuildable data** that must be copied from dev (approved rows of `inventory_mapping_dictionary`, `odoo_company_migration_policy`, dimension seeds) versus tables the pipeline rebuilds. Carry `sql/maintenance/add_unique_keys_dedup_protection.sql` along.
4. **First full manual cycle on the tasks VM** against the `_prueba` databases, to measure timing (expect about 30 minutes) and fix what breaks (run `python -m scripts.check_env` first, then `deploy\run_daily_cycle.ps1`, optionally `-Only` for single stages).
5. **Shadow run Monday night to Wednesday:** register the daily task with `-Enable -Time 07:00` (after the legacy tasks end at 06:30, to avoid both calling the Wansoft SOAP API at once), and compare `wansoft_prueba` against production every morning for the same days (same methodology as Section 14/15).
6. **Wednesday night: go/no-go** for the Thursday cutover.
7. **Around 2026-09-30:** take the pre-cutover backup and copy its folder to a name outside the pruning pattern (for example `PRE_CORTE_2026-09-30`); the pruning only touches folders named `yyyyMMdd_HHmmss`.
8. **Odoo readiness of the October wave:** as of 2026-09-23, Isabel had 14 and San Jerónimo 25 purchase orders, all `draft` (unconfirmed), and Vía Vallejo had none. Re-check live that real confirmed (`purchase`/`done`) orders exist before flipping `COMPANY_SOURCE` for the three (Section 17.6).
9. **Housekeeping on the tasks VM:** replace the VM's `C:\Backups\scripts\backup_mysql.ps1` with the current one (adds the unlisted-database warning) or, better, re-register the backup task with `-ScriptPath C:\Apps\Wansoft_ETL\deploy\backup\backup_mysql.ps1` so it follows the daily `git pull`; run `restore_mysql.ps1` tests only against `_prueba` names.

## Older backlog
- **Inventory valuation for pure-Odoo branches** (Puebla, CentroMyJ): no existing table has a cost/value field on inventory movements; needed for a real COGS.
- **Root-cause the residual 7-19% Compras gap** between Odoo and Wansoft's `Costo operativo` for Acoxpa, Coyoacán and Oceanía (candidate: order-placed versus invoice-registered cutoff); not chased.
- **San Jerónimo:** an unexplained ~$5,915 gap in the "Gastos de venta" `Cuenta` bucket and $49,937 of Wansoft invoices with a blank `Cuenta`; not investigated. San Jerónimo changes routing at the October cutover; re-validate its Costs/Compras afterwards.
- **Check whether Antenas, Tepeyac or CentroMyJ have the August 1-27 dev-only Sales history gap** found on Acoxpa and Puebla.
- **Django app:** define what each role sees before building the permission model (Section 16.3).
- Raise production's `innodb_buffer_pool_size` if it is still small (never checked on the production machine).
- The weekly product-mapping job (Sundays 11am) has never been observed running as scheduled; it is part of the run-once cycle on Sundays.
- Restrict phpMyAdmin (plain http on a public IP) after go-live.
- Origin of the loose untracked root files (`extractAllOrdersByDay.py`, `extractAllOrdersByDay_old.py`, `getAllOrdersByDay.py`, the last two contain the old OneDrive path); not in git, so they do not reach the server.
- The tasks VM's `.env` is local to that machine (gitignored) and holds every credential; it is the only copy of its settings.

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

# 17. Production Infrastructure & Migration (current state, go-live week, cutover)

## 17.0 Decisions and topology

The production side is being evolved **in place** (Section 12): the existing tasks VM and database machine stay, Windows stays, and the new pipeline is deployed next to the legacy tasks, proven on test databases, and then swapped in at cutover. Topology is in Section 0.2. Go-live is **2026-10-01**.

## 17.1 The legacy scheduled tasks (inventory exported 2026-09-23)

12 daily tasks named `FondaCroned_*` run an older loose copy of the legacy scripts from `C:\Users\AnalisisBI\Desktop\CronedJobs_Python\` (not this repository) under the `tf_env` miniconda interpreter:

| Time | Script |
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

Findings: (1) this is almost certainly the source of production's **duplicate Wansoft Purchases/Inventory loading** for the 5 already-Odoo branches (`getExpenses`, `getInputInventory`, `getOutgoingInventory` come from a copy that predates the `is_wansoft_company()` routing and load all 19 branches); still to verify by reading that copy's code. (2) `getAllOrdersByDay.py` (03:40) is still scheduled; dev deliberately excludes it (fixed date range; the Candado is the intended Sales job). (3) None of the Odoo-side jobs exist in production yet (inventory pipeline, purchases pipeline, analytics purchase rebuild, cutover validation, weekly product mapping). (4) The same VM hosts `ControlPresupuestos_AP` with 4 tasks (`Arranque automatico` runs `deploy\update.ps1`, a git-update pattern that was reused; `Catalogos mensual` fires 2026-10-01 04:00; `Gastos reales AM` 05:00 and `PM` 14:00): **out of scope for any cleanup**. (5) Edge and OneDrive tasks are system tasks.

## 17.2 Backup system (built 2026-09-23/24, `deploy/backup/`)

**Design.** Weekly MariaDB backups, one gzip'd dump per database, taken from the tasks VM against the database machine over the internal network (`backup.cnf` on the VM holds `host=192.168.100.183`, a dedicated read-only `backup` user with `SELECT, SHOW VIEW, TRIGGER, EVENT, LOCK TABLES`, and `compress`); kept on the tasks VM under `C:\Backups\mysql\<yyyyMMdd_HHmmss>\`. `mysqldump --single-transaction --quick --routines --triggers --events --hex-blob` (all tables are InnoDB, so writers are not blocked); dumps are taken without `--databases` so a dump can be restored under any name.

**Scripts.**
- `backup_mysql.ps1`: databases `wansoft, zenput, odoo, presupuestos_ap, mysql, phpmyadmin, test`; verifies the `Dump completed` marker and that the gzip reads back completely; keeps the **4** newest complete runs (`-Keep`) and prunes only after a run succeeds; a failed run removes its own partial folder and leaves good backups intact; writes `backup.log`; after a run it logs a `WARNING` listing databases on the server that are not in its list (ignoring internal schemas and names ending in `_prueba`), so a new database such as the Django app's cannot silently stay out of the backups. Adding a database means editing the `$Databases` default.
- `restore_mysql.ps1`: restores one database from a backup folder into a staging database, refuses protected live names (`wansoft`, `zenput`, `odoo`, `presupuestos_ap`, `mysql`, ...), writes `restore_<target>.log` in the backup folder (transcript) so it can run unattended, and with `-CompareWith <db>` prints a per-table `SAME`/`DIFF` row-count report.
- `register_backup_task.ps1`: registers `Wansoft_Backup_MySQL_Semanal` (SYSTEM), Thursdays 18:00, accepting `-MysqlBin`. The trigger was moved so the **first automatic run is 2026-10-01 18:00** (the first backup was taken manually).

**Tools on the VM.** The MariaDB client comes from the official 10.4.28 Windows ZIP unpacked to `C:\Backups\mariadb-client\` (portable, no service installed); its `bin` folder is passed as `-MysqlBin`.

**First real backup (2026-09-24 14:42 to 15:12).** 7 databases, `wansoft.sql.gz` 3,382.7 MB (from 26,104,910,340 bytes of SQL) in 29.8 minutes, the others in seconds; log line `Backup finished. Kept: 20260924_144209`. The very first attempt at 14:36 failed on bug #25; a run over the public IP was too slow and was stopped.

**Tests.** On dev with `zenput` (retention keeps exactly the configured count, the failure path keeps earlier backups, a restore reproduces identical row counts), on a 3 GB synthetic file (completeness check, compression and verification above 2 GB), and the unlisted-database warning in both directions.

**Trade-off accepted by the user:** backups live on the tasks VM, not on the database machine, so losing the database machine does not lose them; losing the tasks VM does, so a Hyper-V export of the VMs from the host before go-live is still worth taking.

## 17.3 Restore rehearsal (in progress)

- `wansoft_prueba` and `zenput_prueba` exist on the database machine; the `backup` user has `ALL PRIVILEGES` on each (production `wansoft` has no views, triggers, routines or events, so no `SUPER`/definer issue). Free disk on the database machine is 258 GB, enough for the 31 GB copy.
- One-time task `Wansoft_Restore_Ensayo` (SYSTEM) runs `restore_mysql.ps1 -BackupFolder C:\Backups\mysql\20260924_144209 -SourceDatabase wansoft -TargetDatabase wansoft_prueba -ConfigFile C:\Backups\mysql\backup.cnf -MysqlBin ... -CompareWith wansoft` at **22:00 on Friday 2026-09-25**, expected to take one to three hours (about 15 GB of indexes to rebuild). The database machine must not sleep during the night (the user disabled sleep).
- Pending: the equivalent restore for `zenput_prueba`.

## 17.4 The tasks VM deployment (done 2026-09-25)

- Repository cloned to `C:\Apps\Wansoft_ETL`; `.venv` created from the VM's Python 3.12 with the pinned `requirements.txt` (`python-dotenv 1.1.0, lxml 5.3.0, mysql-connector-python 9.4.0, numpy 2.1.3, pandas 2.2.3, PyMySQL 1.1.2, rapidfuzz 3.14.1, requests 2.32.3, zeep 4.3.2`, validated on Python 3.13.5 in dev; the repository had no dependency list before) and importing correctly.
- `core\config\.env` created from the template, locked with `icacls` to SYSTEM and Administrators, with `ENV=prod` (so the non-`_DEV` keys apply), `WANSOFT_DB_HOST=192.168.100.183`, and, as a **fail-safe until cutover, `WANSOFT_DB_NAME=wansoft_prueba` and `ZENPUT_DB_NAME=zenput_prueba`**; `XML_DOWNLOAD_DIR=C:\Apps\Wansoft_ETL\data\xml`; lookbacks `SALES 10 / WANSOFT 5 / PURCHASES 35`. The preflight `python -m scripts.check_env` passed there; the only warnings were the two test databases not existing yet (now created).
- **Daily update task `Wansoft_Update_Repo_Diario`** (00:30, runs `deploy\update_repo.ps1` as `analisisbi` with its stored password): `git pull --ff-only`, reinstalls dependencies only when `requirements.txt` changed, logs to `logs\update.log`, exits non-zero on failure. Verified end to end: a real update (`15d1428 -> 1d47615`, later `45aed32 -> 11c5ec1`) and a task run with `LastTaskResult 0` (which also proved the Git credentials work non-interactively).
- **Run-once cycle, prepared and NOT scheduled:** `scripts/run_daily_cycle.py` (15 stages in order, the weekly product mapping added on Sundays; `--list`, `--only`; continues after a failed stage; prints a summary; exits 1 if anything failed), `deploy/run_daily_cycle.ps1` (dated log `logs\daily_cycle_<yyyyMMdd>.log`, keeps 30 days), `deploy/register_daily_cycle_task.ps1` (registers `Wansoft_Pipeline_Diario` at **01:30**, **disabled unless `-Enable`**, asks for the account password, `-Time` is a parameter). `scripts/check_env.py` is a read-only `.env` preflight (missing keys, database and Odoo credentials, existence of the configured database, the 19 Wansoft passwords, the XML folder), never printing secrets.

## 17.5 Go-live week (2026-09-28 to 2026-10-01)

| When | What |
|---|---|
| Fri 09-25 22:00 | Restore rehearsal runs unattended (17.3) |
| **Mon 09-28 AM** | Read `restore_wansoft_prueba.log` and judge the `DIFF` lines (copy must be at or below production by about one day of loads). Restore `zenput` into `zenput_prueba`: `restore_mysql.ps1 -BackupFolder C:\Backups\mysql\20260924_144209 -SourceDatabase zenput -TargetDatabase zenput_prueba -ConfigFile C:\Backups\mysql\backup.cnf -MysqlBin C:\Backups\mariadb-client\mariadb-10.4.28-winx64\bin -CompareWith zenput`. Prepare and apply the schema migration and reference data to `wansoft_prueba` (Section 13, item 3) |
| Mon 09-28 PM | First full manual cycle on the VM against the `_prueba` databases; fix what breaks; measure timing |
| Mon night to Wed | Shadow run: daily task enabled at **07:00** writing to the test databases; each morning compare `wansoft_prueba` with production for the same days |
| Wed 09-30 | Take the pre-cutover backup and copy it to `PRE_CORTE_2026-09-30`; **go/no-go** in the evening |
| **Thu 10-01** | Cutover (17.6) |

## 17.6 Cutover checklist (Thursday 2026-10-01), to confirm with the user on Monday

1. Confirm real confirmed Odoo orders exist for Isabel, San Jerónimo and Vía Vallejo (Section 13, item 8), then flip `COMPANY_SOURCE` to `"odoo"` for the three in `core/config/companies.py` and `ROLLOUT_COMPANY_EXPECTATIONS` to `active: True`, seed/maintenance SQL and `odoo_company_migration_policy` per `docs/purchases-company-migration-policy.md`, commit and push (the daily update brings it to the VM).
2. Apply the proven schema migration and reference data to the real `wansoft` (additive changes only), and create/populate whatever `zenput` needs.
3. On the VM `.env`, switch `WANSOFT_DB_NAME` to `wansoft` and `ZENPUT_DB_NAME` to `zenput`; run `python -m scripts.check_env`.
4. Stop the legacy tasks: **recommended to disable the 12 `FondaCroned_*` tasks rather than delete them**, and delete after the first one or two successful nights (the user said "remove at go-live"; disabling is equivalent operationally and reversible; confirm this with the user). Leave `ControlPresupuestos_AP`, the backup task and the system tasks alone.
5. Register/enable `Wansoft_Pipeline_Diario` at 01:30 (`register_daily_cycle_task.ps1 -Enable`); the first production run is the night of 10-01 to 10-02. Watch `logs\daily_cycle_<date>.log`.
6. The weekly backup runs at 18:00 that same day (the first automatic one).
7. Re-validate against Power BI with real data for all 10 Odoo-sourced branches over 10-01 to 10-03 (Sections 14/15); production's duplicate Wansoft Purchases/Inventory loading should be gone once the legacy tasks stop.
8. Afterwards: restrict phpMyAdmin, start the Django app work (Section 16).

## 17.7 Risks and things not to forget
- The shadow run and the legacy tasks both call the Wansoft SOAP API; keep them apart in time (07:00 versus 01:00-06:30).
- A dump or restore over the network at the wrong time slows the database used by Power BI and `ControlPresupuestos_AP`; run heavy jobs after hours.
- The pipeline task needs the `analisisbi` password at registration; nothing else stores it.
- If anything is unclear about which machine a command runs on, check Section 0.2 before running it.

---

# 18. Next Steps — HANDOFF PROMPT

**Paste this as the first message when resuming (Monday 2026-09-28):**

```
Continúo el proyecto Wansoft + Odoo + Zenput Data Warehouse & ETL Pipeline.
Lee completo PROJECT_CONTEXT_REPORT.md en la raíz del repositorio antes de
responder, especialmente la Sección 0.2 (las dos máquinas de producción,
no confundirlas), la Sección 17 (infraestructura: estado actual, semana
del corte y checklist del jueves) y la Sección 13 (pendientes en orden).

Resumen rápido: el jueves 24 y viernes 25 de sept se construyó el sistema
de respaldos semanales (hay un primer respaldo real completo y verificado),
se preparó la VM de tareas con el código nuevo, un entorno de Python y una
tarea diaria que actualiza desde GitHub a las 00:30, y se escribió el
orquestador de ciclo diario que corre de una sola vez (tarea registrada
DESHABILITADA a propósito, con hora 01:30). El .env de la VM apunta a
wansoft_prueba y zenput_prueba como seguro: no debe escribirse nada en las
bases reales antes del corte. El viernes a las 22:00 corre sola la
restauración del respaldo en wansoft_prueba, y zenput_prueba ya existe pero
falta restaurarle su respaldo.

Hoy (lunes) toca: (1) leer el log de la restauración
(C:\Backups\mysql\20260924_144209\restore_wansoft_prueba.log): debe haber
DIFF solo donde las tareas viejas cargaron datos el viernes de madrugada,
y la copia debe tener igual o menos filas que producción; (2) restaurar
zenput en zenput_prueba; (3) migración de esquema solo sobre
wansoft_prueba: faltan 41 tablas, 2 vistas y 5 columnas respecto a
producción, más los datos de referencia (mapeos aprobados, políticas de
migración); (4) primera corrida completa del ciclo en la VM contra las
bases de prueba; (5) desde el lunes en la noche hasta el miércoles,
corrida en sombra a las 07:00 comparando prueba contra producción cada
mañana; (6) el miércoles en la noche, decisión de seguir o no con el corte
del jueves 1 de octubre. La hora definitiva del ciclo diario es 01:30.

Reglas que no se pueden olvidar: la VM de tareas es DESKTOP-1HTRVT4
(usuario analisisbi) y NO tiene MySQL; la base está en otra máquina
(192.168.100.183); las 12 tareas FondaCroned_* siguen corriendo hasta el
corte; las tareas de ControlPresupuestos_AP no se tocan; y me gusta ir paso
a paso, un comando por bloque, en ventanas cortas de trabajo.
```

**Suggested title for the new chat**: `FONDA (Wansoft): Paso 25: Ensayo en paralelo en el servidor y corte a producción del 1 de octubre`

---

# Permanent Rule

Regenerate this document in full (never as patches) when: the user explicitly asks, a major step closes, the conversation gets very long, context exceeds ~70%, or a new chat needs to be opened due to token limits. In that last case, also generate:
1. The handoff prompt (Section 18, first code block, if applicable).
2. The suggested title for the new chat, in the format **`FONDA (short project): Paso N[-M]: <short description>`** (same style as the user's own session list). `FONDA` is a fixed prefix; `(short project)` identifies which project (here: "Wansoft"). Use `N` = the major step/block number in progress, `-M` = sub-part suffix if the step spans multiple consecutive sessions/chats.

**Note on language:** this document, all commit messages, and all documentation pushed to GitHub in this project must be written in English — even though the working conversation with the user is in Spanish. See project memory `feedback_github_content_english_only` for the full rule.
