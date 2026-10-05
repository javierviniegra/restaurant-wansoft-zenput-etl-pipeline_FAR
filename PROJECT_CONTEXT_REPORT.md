# PROJECT_CONTEXT_REPORT.md

Master continuity document. Generated/updated automatically at the close of major steps, on explicit request ("Generate project context report"), when the conversation gets very long, when consumed context exceeds ~70%, or when a new chat needs to be opened due to token limits. Always regenerated in full, never as an incremental patch.

Last generated: 2026-10-01 (Thursday, afternoon), right after the production cutover finished. It covers 2026-09-29 to 2026-10-01 on top of the earlier sessions kept below. **THE CUTOVER IS DONE (all 10 steps OK, Section 17.10). Production now runs on the new pipeline: `Wansoft_Pipeline_Diario` at 01:30 against the live `wansoft`/`zenput`; the first production night is 2026-10-01 to 10-02. Next action: Friday 10-02, check that night (Section 13 "After go-live").** Read Section 13 first, then Section 0 (machines), 17.10 (what ran today) and 18. The command-level procedure, including the exact commands executed today, lives in `docs/production-cutover-runbook.md` (Section 6.1).

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

**If XAMPP's MySQL will not start (2026-09-28 incident, bug #33):** read `C:\xampp\mysql\data\mysql_error.log` and the Windows Application event log (provider `MariaDB`, and `Application Error` for `mysqld.exe`). A shutdown without stopping MySQL left the Aria recovery log inconsistent (`Aria recovery failed ... delete all aria_log.########`) and three Aria system tables crashed (`mysql.db`, `mysql.proxies_priv`, `mysql.roles_mapping`). Fix that worked: stop mysqld, move `aria_log.*` and `aria_log_control` to a backup folder (not delete), check every `mysql\*.MAI` with `aria_chk -e -s`, repair the damaged ones with the safe method `aria_chk -o` (the sort method `-r` failed on a tiny sort buffer), start from the XAMPP panel (a mysqld started from the harness shell dies with the shell), then re-insert the default `root@localhost` row in `mysql.proxies_priv` and `FLUSH PRIVILEGES`. Only `root` users exist on dev, so no real grant was lost; `mysql.db`'s data file had actually been overwritten with error-log text long before. Backups of every touched file: `C:\xampp\mysql\aria_log_backup_20260928\`.

`core/config/.env` on the dev PC has `ENV=dev` and its `XML_DOWNLOAD_DIR_DEV` was corrected to the OneDrive path on 2026-09-17 (bug log #21). `.env` is gitignored, so every machine needs its own.

Git and `.env` (credentials) both survived the OneDrive move intact.

## 0.2 The two production machines — do not mix them up (confirmed 2026-09-24/25)

| | Tasks VM | Database machine |
|---|---|---|
| Name / address | `DESKTOP-1HTRVT4` (Hyper-V guest) | `DESKTOP-5DELBQN`, internal `192.168.100.183`, public `187.251.203.223` |
| Windows account that runs things | `analisisbi` | (RDP administrator) |
| What it hosts | The 12 legacy `FondaCroned_*` scheduled tasks, the separate live project `ControlPresupuestos_AP` (`C:\Apps\ControlPresupuestos_AP`, 4 tasks), the new pipeline (`C:\Apps\Wansoft_ETL` with `.venv`, Python 3.12), the backups (`C:\Backups\mysql`, 412 GB free), the MariaDB client tools (`C:\Backups\mariadb-client\mariadb-10.4.28-winx64\bin`) | XAMPP **MariaDB 10.4.28**, datadir `C:\xampp\mysql\data\`, binary log off, all tables InnoDB; phpMyAdmin on plain http port 8088 |
| Does NOT host | MySQL or phpMyAdmin (nothing listens on 3306/3307/8088) | Any pipeline or task |
| Free disk | 412 GB on C: | 258 GB on C: (less now: `wansoft_prueba` is a full ~31 GB copy) |

Databases (`wansoft` is the big one): `wansoft` 31 GB on disk (**migrated on 2026-10-01: 59 tables + 2 views**), `zenput`, `odoo`, `presupuestos_ap`, `mysql`, `phpmyadmin`, `test`, plus the test copies `wansoft_prueba` (migrated, 61 tables) and `zenput_prueba`. The tasks VM reaches the database over the internal network (`192.168.100.183`); the dev PC reaches it through the public IP. **phpMyAdmin is served unencrypted on a public IP: restrict it after go-live.**

**Both machines are Hyper-V VMs on the same host `SVR-HIKCENTER`** (owner, 2026-09-30), whose Hyper-V names are **`WansoftServer`** (database) and **`Analisis_BI`** (tasks). Checkpoints are taken from the host; both have a `PRE_CORTE_2026-10-01` checkpoint (2026-10-01 10:30/10:31, taken with MySQL stopped). `WansoftServer` also has two checkpoints of April 2024. The host's C: has 218 GB free after the 2026-10-01 cleanup; its D: (17 TB) is an external disk, not for running VMs.

**Database users (checked 2026-09-28):**
- `backup` (used by the backup/restore scripts via `C:\Backups\mysql\backup.cnf`): read-only on everything, `ALL` on `wansoft_prueba` and `zenput_prueba`.
- `wansoftuser` and `zenputuser` are the **pipeline's** accounts (`WANSOFT_DB_USER` / `ZENPUT_DB_USER` in the VM's `.env`). They got `ALL PRIVILEGES` on `wansoft_prueba` / `zenput_prueba` on 2026-09-28 (they had none; the preflight caught it).
- **`wansoftuser` is NOT read-only**, contrary to what earlier reports said: `SHOW GRANTS` shows `ALL PRIVILEGES ON wansoft.* ... WITH GRANT OPTION`. It is also the credential the dev PC uses for "read-only" comparisons. Only ever SELECT with it from dev. Split it after go-live (runbook Section 8).
- It cannot see `wansoft_prueba`/`zenput_prueba` from the dev PC's connection; checks on the test databases are run from the tasks VM with the `backup` user.
- **`tukan_wansoft` and `tukan_zenput`** (created 2026-10-01, host `'%'`): read-only for tukanmx, 22 `wansoft` tables + `zenput.*`, 4 connections, 30-minute statement cap (Section 19).
- The cutover migration was run with `wansoftuser` through a temporary option file `C:\Backups\mysql\wansoft_write.cnf`, deleted the same day.

**Since the cutover (2026-10-01) the tasks VM `.env` points at the live databases** (`WANSOFT_DB_NAME=wansoft`, `ZENPUT_DB_NAME=zenput`): every manual run on the VM writes to production, and the legacy tasks no longer write anything. To rehearse something on `wansoft_prueba` / `zenput_prueba`, switch those two lines back first and restore them afterwards. Check them before any manual run (`Select-String -Path core\config\.env -Pattern '^(ENV|WANSOFT_DB_(HOST|USER|NAME)|ZENPUT_DB_(HOST|USER|NAME))='` shows them without secrets). The pre-cutover rule "nothing new writes to production" is retired.

---

# 1. Executive Summary

**Overall project goal:** build a unified analytical layer in MySQL that integrates Wansoft, Odoo, and Zenput, hiding from the end user which system originates each piece of data.

**Delivery layer goal (decided 2026-09-23, Section 16):** a **new Django web application** replicating the validated Power BI pages with interactive filters and role-based access. Not started; role scopes undefined. **New (2026-09-28):** an external vendor, **tukanmx.com**, will also connect to these databases, build its own ETL and deliver a question-and-answer / chatbot layer (Section 19).

**Data-warehouse state:** acceptance gate accepted (2026-08-31); Sales, Meseros, Costs and Purchases validated against the owner's Power BI for Acoxpa, La Esquina Coyoacán, San Jerónimo and Oceanía (Sections 6, 14, 15).

**Infrastructure state (Section 17):**
- **Backups:** weekly system in place; first backup (2026-09-24) proven by a full restore into `wansoft_prueba` (22 tables, 121.5 min, every `DIFF` lower than production by one night of loads).
- **Migration rehearsed** on `wansoft_prueba` on 2026-09-28: 41 tables + 2 views loaded from a dev dump, 3 generated columns, 5 unique keys + 1 index, 4 old tables dropped, and two production data problems cleaned (77,370 exact duplicate rows in `getoutgoinginventory_salida`, 48 zero-valued duplicate captures in `costeomensual_semanapyq`). All in `sql/migrations/` + a dump; timings in the runbook.
- **First full cycle on the tasks VM:** 15/15 stages, 35.3 min, but four real deployment bugs surfaced and were fixed the same day (bugs #27-#30). Sales re-run: 190 of 190 XML.
- **Shadow week:** three shadow runs on the test databases (09-29 to 10-01), all 15/15 OK, comparisons clean.
- **CUTOVER DONE on 2026-10-01** (Section 17.10): legacy tasks disabled, pre-cutover backup and Hyper-V checkpoints, live `wansoft` migrated (parts 1-5), `.env` switched to the real databases, 125-day purchases reload, Puebla/CentroMyJ cost backfill, `Wansoft_Pipeline_Diario` at **01:30** against production, tukanmx users created.

**Go-live:** done Thursday **2026-10-01**, together with the Odoo cutover of Isabel La Católica, San Jerónimo and Vía Vallejo. First production night: 2026-10-01 to 10-02.

**Superseded next action (2026-09-29), kept for history:** read `C:\Apps\Wansoft_ETL\logs\daily_cycle_20260929.log` (expect `0 failed`, measure the steady-state duration), then compare `wansoft_prueba` with production for the same days.

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
No open issues in pipeline logic. Matches Power BI exactly in every branch checked (Acoxpa, Coyoacán, San Jerónimo, Oceanía; Puebla earlier). **Fixed 2026-09-28 (bug #27):** on a new machine the Candado could not write any XML (missing `data\xml\getAllOrdersByDay`) and still reported the stage as OK; it now creates the folder and exits 1 when not a single XML could be obtained. **Open, carried forward:** whether Antenas, Tepeyac or CentroMyJ have the Aug 1-27 dev-only history gap found on Acoxpa/Puebla.

Sales table facts confirmed 2026-09-28 (now in the data access guide): join header to lines/payments/modifiers on `Sucursal` + `Movimento` = `Movimiento_Id` (full coverage); amounts and `Fecha` are `varchar`; `Estatus` is always 0; `TipoOrden` in `Restaurant` / `Para llevar` / `eCommerce`. The old tables `getallordenesbyday_venta`, `_detalleventa`, `_modificador` and the empty `getallordenesbyday_new_pagos` are unused backups; the owner confirmed nothing writes to them, and they are dropped at cutover (already dropped on dev and `wansoft_prueba`).

### Purchases
Both August-round bugs and the unconfirmed-RFQ bug (#24) remain fixed. Compare Odoo-migrated branches against Wansoft's `Cuenta='Costo operativo'` only; the residual 7-19% Odoo-over-Wansoft gap stays an open item. **Confirmed 2026-09-28:** the canonical/analytics layer already merges Wansoft history (invoice-type entries, `getinputinventory_entrada` with `TipoEntrada='Factura'`) before each branch's Odoo start date with confirmed Odoo orders from that date (`final_purchase_source_status` = `final_wansoft_enabled` / `wansoft_history_before_odoo`); a live check on Acoxpa showed January-June from Wansoft and July onward from Odoo, no month repeated or missing. **Superseded 2026-09-29:** the 5 migrated branches now read Odoo only from 2026-10-01 (`cutover_04`), so their June-September purchases come from Wansoft; rehearsed on `wansoft_prueba` with a one-off 125-day Wansoft window. **Decided 2026-09-28:** after cutover the pipeline does not keep downloading Wansoft invoices/entries/exits for migrated branches (the legacy tasks did); the Odoo-vs-Wansoft validation is considered done.

### Inventory
No change to the Odoo-side valuation gap (still open). Production's `getoutgoinginventory_salida` held 77,370 surplus rows in 61,125 groups, all exact copies left by three bulk reloads of the legacy loader (2025-04, 2026-02, 2026-07; none in 2026-08/09); the cutover migration removes them before adding the unique key the new loader depends on (Section 17.8).

### Costs
**Routing changed 2026-09-29 (owner):** every branch operating on Odoo, migrated or new, takes its costs from Odoo from its Odoo start date on, per day, and from Wansoft before (`extract/costs/cost_routing.py`, start dates from `odoo_company_migration_policy`; Odoo data before a start date is filtered out of the week/month-to-date sums). **Automatic switch (2026-10-02):** the October wave (Isabel, San Jerónimo, Vía Vallejo) is in `COSTS_AUTO_SWITCH_TO_ODOO`: Wansoft until Odoo has their cost of sales, then each switches by itself (`extract/costs/cost_switch.py`, `pipelines/jobs/costs_switch_job.py`, table `costs_odoo_switch`); month/week-to-date stay continuous across a mid-period switch, Odoo rows carry NULL in Wansoft-only columns, and the stage validates duplicates and continuity of every Odoo-costed branch nightly (see `legacy/wansoft/automaticos/README.md`, "Cost routing"). **Temporary exception: Antenas** stays on Wansoft (`COSTS_WANSOFT_TEMPORARY_EXCEPTIONS` in `core/config/companies.py`): it was the Odoo prototype and its Odoo cost data is broken (September 1-27 showed 6,549 million) while that database is repaired; remove it once the owner confirms. Check before switching, Sept 1-27 Odoo vs Wansoft Costo Teórico: Acoxpa +1.1%, Tepeyac +1.3%, Oceanía -3.0%, Coyoacán +4.6%. The per-day rule matters for the October wave: after `COMPANY_SOURCE` flips, the 10-day cost window must not recompute their September days from Odoo. `COSTS_ODOO_SOURCE_COMPANIES` now only means "born on Odoo" and still drives butchery. Odoo costs only fill CostoTotal, CostoDeProductosVendidos and CostoDeMerma (courtesies/cancellations come from the cash closing). The earlier (2026-09-28) framing, migrated branches on Wansoft while they capture purchases there in parallel, is superseded. **Butchery (`gettablajeriareport`) is being phased out** for the same reason (owner, 2026-09-28): it only exists while a branch enters purchases/inventory in Wansoft (Puebla and CentroMyJ have none; migrated branches will lose it), and Odoo applies calculated yields and only checks at month end that real inventory matches the calculation. Production's `costeomensual_semanapyq` held 48 duplicate (branch, day) captures from 2025-05-06..08 where the earlier row was all zeros; the migration keeps the later, real row. Cost table semantics (now documented): `costeomensual` = month-to-date through `created_date`; `costeomensual_semanapyq` = week-to-date from Monday through the day before `created_date`; `gettotalcostbydate` = the single day `created_date`.

### Meseros
Power BI's ranking excludes the per-branch delivery/app placeholder waiter; validate by excluding it.

### Security / Configuration
Lookbacks remain `.env`-driven (`SALES 10 / WANSOFT 5 / PURCHASES 35`; `COSTS_LOOKBACK_DAYS` 10 by code default, which is why the preflight shows one expected WARN). `scripts/check_env.py` fails (not warns) when the configured database is not reachable by the configured user. Findings to act on after go-live: `wansoftuser` has full privileges with grant option; phpMyAdmin on plain http on a public IP; the production server accepts connections from the internet without TLS; the tukanmx users accept any host (`'%'`) until tukanmx gives its IPs.

### Deployment / operations
**In production since 2026-10-01.** Tasks VM: daily GitHub update (00:30), `Wansoft_Pipeline_Diario` (01:30, writes to the live `wansoft`/`zenput`), weekly backup (Thursday 18:00), preflight. The 12 `FondaCroned_*` are disabled (to delete after one or two good nights); `Wansoft_Restore_Ensayo` was unregistered. **Watch the analytics purchase stage's duration:** it took 43.5 min on the live database at midday (14.9 min in the rehearsal on `wansoft_prueba`); measure it at night before acting (candidate: production's never-checked `innodb_buffer_pool_size`).

**Power BI after the cutover:** its Compras / Entradas pages read `getexpenses_factura` and `getinputinventory_entrada`, which no longer receive the 10 Odoo branches from 2026-10-01, so October shows empty for them until the pages are repointed to `analytics_purchase_order_lines` (`include_in_business_views = 1`). The owner asked for the repoint package (final query, branch crosswalk `company_source_key` vs Wansoft IDs, column mapping of the current page) for **Monday 2026-10-05**; it needs the `.pbix` or its queries. The by-`Cuenta` (non-goods) view stays on `getexpenses_factura`; its Odoo-branch gap is covered by `analytics_expense_invoices` (also Monday).

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
| Copy the 41 new tables and 2 views to production **with dev's data** (one dump), not as empty tables | Dimensions, the approved mapping dictionary, migration policies and catalogs are rebuilt by no daily stage, and the Wansoft side of the canonical purchase tables is incremental (35 days); dev holds exactly the state validated against Power BI | `NUEVAS_<date>/wansoft_nuevas.sql.gz`, runbook 5.1 |
| Strip `DEFINER` from the dumped views and make them `SQL SECURITY INVOKER` | The `backup` user has no `SUPER`; a definer clause would fail the load | Runbook 5.1 |
| Keep the **later** row of each `costeomensual_semanapyq` duplicate pair (not the lowest id) | In all 48 pairs the earlier capture is all zeros; the documented "keep lowest id" rule would keep the zeros | `sql/migrations/cutover_02_small_tables.sql` |
| Remove the `getoutgoinginventory_salida` duplicates keeping the lowest id, only after proving every group is an exact copy | Materialise the groups once (two scans, 25.6 min) instead of re-scanning 37M rows per question; delete by primary key | `sql/migrations/cutover_03_large_inventory_tables.sql` |
| Do not add `campo1`/`campo2` to production's `getallordenesbyday_venta`; drop the 4 old Sales tables at cutover instead | Dev's table was a 4-column leftover stub; production's is a 24-column backup nobody writes or reads | Owner's decision |
| The Sales Candado exits non-zero when no XML at all was obtained | A single missing day can be a closed branch; zero XML is a system failure that must show as a failed stage | `legacy/wansoft/automaticos/extractAllOrdersByDay.py` |
| The cycle wrapper keeps one shared log handle and echoes to the console | `Add-Content` per line collided with a reader and lost lines | `deploy/run_daily_cycle.ps1` |
| Preflight: an unreachable database is a FAIL | `SHOW DATABASES` hides databases the user has no rights on; a WARN hid two blockers | `scripts/check_env.py` |
| Pre-cutover backup on Thursday, after stopping the legacy tasks and before migrating (replaces Wednesday's) | Exact final state and rollback point | Runbook 6.2b |
| External vendor access through two limited read-only users | Least privilege; the existing accounts have full rights | `sql/maintenance/create_tukan_readonly_users.sql` |
| Bilingual (Spanish + English) data access guide with a PDF, as an explicit exception to the English-only GitHub rule | It is for an external reader; commit messages stay English | `docs/data-access-guide/` |
| Mark PDF/images/gz/xlsx as binary in `.gitattributes` | `core.autocrlf` treated the PDF as text and would corrupt it on checkout | `.gitattributes` |
| Cutover migration written with `wansoftuser` through a temporary, ACL-locked option file built from the VM's `.env`, deleted the same day (2026-10-01) | It already has `ALL` on `wansoft` and reaches the database over the internal network; the password never had to be typed or shown | Runbook 6.1 |
| Pre-check duplicates on all four tables that get a unique key before part 2, not only the one being deduplicated | A new duplicate would fail an `ALTER` half-way through the file | Runbook 6.1 |
| Merge `WansoftServer`'s April 2024 checkpoints on a weekend, not on cutover day (owner asked, 2026-10-01) | Merging rewrites hundreds of GB on the database's own disk while the migration needed it, and would have removed the safety net mid-cutover | Section 13 "After go-live" |
| tukanmx users created with host `'%'` | tukanmx had not given fixed IPs; to restrict when they do | Section 19 |
| Warn in the data guide that Odoo and Wansoft purchases do not match each other (7-19%) | External readers would otherwise compare them and report it as a load error | `docs/data-access-guide/` (`82f6176`) |
| Unregister `Wansoft_Restore_Ensayo` | One-shot rehearsal task, done; avoids an accidental manual run | Tasks VM |
| October wave costs stay on Wansoft until Odoo has data, then switch automatically per branch (owner, 2026-10-02) | They cannot post cost in Odoo before their opening balances; the owner does not want to ask for a code change when it happens, and each branch may start on a different day | `COSTS_AUTO_SWITCH_TO_ODOO`, `extract/costs/cost_switch.py`, `pipelines/jobs/costs_switch_job.py`, `costs_odoo_switch` |
| Switch rule: first of 2 consecutive days with Odoo cost > 0 and within 0.5x-2x of Wansoft; Odoo from that day, Wansoft before; never switches back by itself | A test entry or stray adjustment must not trigger it (Antenas' pilot data); taking Odoo from 10-01 would leave the pre-balance days at 0 | Same |
| Month/week-to-date continuous across a mid-period switch ("D1", owner: "they are part of the cost") | Otherwise the first month after a mid-month switch loses the Wansoft days (about 450,000 for Isabel if it switched on the 10th) | `wansoft_period_base` in the monthly and weekly cost scripts |
| Nightly validation of duplicates and accumulation continuity for every Odoo-costed branch, failing the stage on problems (owner asked to validate no duplicates) | Proves each day counts exactly once; found bug #35 on its first run | `check_cost_continuity` |
| Odoo cost rows clear the Wansoft-only columns when they overwrite a Wansoft row | Power BI subtracts `CostoDeConsumo` from `CostoTotal`; a stale Wansoft consumo would distort an Odoo row | Monthly and weekly cost scripts |

---

# 9. Business Rules Implemented / Reinforced

- **Costs governance is per-branch, three states, not a domain-wide flag:** Wansoft-migrated vs. pure-Odoo vs. the Cortesias/Cancelaciones Sales-adjacent override that ignores both and always uses Wansoft's sale-value figure.
- **Internal-provider exclusion is about the buying company, never the vendor alone** — a real branch buying from an internal kitchen (El Bodegon, Las Empanadas) is a real purchase for that branch.
- **A weekly automated job must never downgrade or silently relabel a human review decision** — every field of an already-reviewed row stays untouched on re-run.
- **`getglobalcashclosing` is a legitimate, Wansoft-sourced, always-available report for every branch regardless of Purchases/Inventory/Costs migration status** — same tier as Sales itself.
- **Odoo purchase orders only represent goods procurement.** Service/subscription/payroll/administrative spend recorded in Wansoft under other `Cuenta` buckets (Gastos Directos, Sueldos y Salarios, etc.) has no Odoo purchase-order equivalent by design — it is not a gap to chase.
- **A daily job's re-check window is a tuning knob, not a constant.** It should live in `.env`, not be hardcoded per-script, so it can be widened (to self-heal after a missed run) or narrowed (to keep the daily cycle fast) without a code change.

- **Nothing new writes to production before cutover** (retired 2026-10-01: since the cutover the new pipeline is the only writer of `wansoft`/`zenput`, and a manual run on the tasks VM writes to production).
- **An unattended job must fail loudly and leave a log.** Every scheduled piece of the new stack writes a dated log under `logs\` (or the backup folder) and exits non-zero on failure; a failed backup never deletes good backups.
- **Backups are only real once restored.** The weekly dump is verified for completeness and readability, but the proof is the restore rehearsal with a row-count comparison.
- **A branch on Odoo takes its costs from Odoo from its start date, per day** (2026-09-29); Wansoft before. Temporary exceptions (Antenas) are explicit and reversible.
- **A duplicate is only deleted after proving it is an exact copy**, and which copy to keep is decided from the data (zeros vs real values), not from a fixed rule.
- **An external party never gets an existing project account**; it gets its own read-only user, limited to documented tables, with connection and query-time caps.

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

- **A table-level `GRANT` fails on a table that does not exist yet** (MariaDB), so grants on tables created by a migration must run after it.
- **`SHOW DATABASES` only lists databases the current user has privileges on**; "missing" can mean "not granted".
- **`runpy` runs legacy scripts in-process**, so a legacy script's `sys.exit(1)` becomes a `SystemExit` the cycle records as FAILED; that is how to make a legacy stage fail loudly.
- **xhtml2pdf quirks (PDF rendering):** a `div` with a background draws one box per list item (use a single-cell table instead); empty table cells collapse their column (put a dash); widths must be `width="%"` attributes on the header cells; `<pdf:toc />` builds a page-numbered table of contents from `h1`/`h2`, so the document title must not be an `h1`. xhtml2pdf is available in `ControlPresupuestos_AP\.venv`, not in this project.
- **A process started from the harness shell dies when the command ends**; services such as mysqld must be started by the user (XAMPP panel).
- **The dump/restore of the new tables took 5.7 + 11.6 minutes; adding both inventory indexes online took 4.8 minutes; a full `GROUP BY` over the 37M-row exits table took 31 minutes.** Use these to plan the cutover. **Cutover day actuals (2026-10-01):** dump 6.75, load 11.2, part 3 step A 26.6, step D 3.8 minutes; purchases + analytics 49.2 minutes (analytics alone 43.5, three times the rehearsal: the live database is shared with Power BI and ControlPresupuestos_AP at midday).
- **PowerShell drops columns silently** when one line prints different kinds of objects to the default table formatter (the first object's columns win); add `| Format-Table` or `| Format-List` per command.
- **Decompressing a `.gz` on Windows PowerShell 5.1** without extra tools: `IO.Compression.GZipStream` + `CopyTo`; check the output length against the uncompressed size measured where the dump was made.
- **MariaDB option files must be written without a BOM** (`New-Object Text.ASCIIEncoding` or UTF8 without BOM); quote the password with `"` and escape `\` and `"`.
- **Task Scheduler result 267014 (0x41306)** means the run was terminated by the user (for example, a run still going when the task was disabled and stopped).
- **A script applied on dev travels with the dump:** tables loaded from dev arrive with dev's state, so a migration already applied on dev updates 0 rows in production. Check dev first to know the expected counts.

**Git state:** branch `main`, pushed to `origin/main` (public repository; it must never hold passwords) through the commit that carries this report. `.gitattributes` now marks PDF/images/gz/xlsx as binary. `inventory_not_found_analysis.csv` remains permanently uncommitted per convention. Loose untracked files at the repo root (`extractAllOrdersByDay.py`, `extractAllOrdersByDay_old.py`, `getAllOrdersByDay.py`) remain unexplained, not touched.

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
| 27 | Sales Candado on a new machine: `data\xml\getAllOrdersByDay` did not exist, every XML write failed, every day was skipped, and the stage still reported OK | `legacy/wansoft/automaticos/extractAllOrdersByDay.py` | **Fixed 2026-09-28**: creates the folder, exits 1 when no XML at all. Re-run on the VM: 190/190 |
| 28 | The cycle wrapper lost log lines (and spammed errors) while another window followed the log: `Add-Content` reopened the file per line | `deploy/run_daily_cycle.ps1` | **Fixed 2026-09-28**: one shared write handle, UTF-8 with BOM, console echo; tested with a concurrent reader |
| 29 | The preflight only warned when the configured database was not visible, hiding two real blockers on the VM | `scripts/check_env.py` | **Fixed 2026-09-28**: FAIL with "missing or not granted" |
| 30 | Tasks VM configuration: `ZENPUT_DB_NAME` held the host IP instead of `zenput_prueba`; `wansoftuser`/`zenputuser` had no rights on the test databases | VM `.env`, database grants | **Fixed 2026-09-28** (line corrected; grants added) |
| 31 | Production `getoutgoinginventory_salida`: 77,370 surplus rows in 61,125 groups, exact copies from three legacy bulk reloads; blocks the unique key the new loader needs | Production data | **Fixed in production 2026-10-01** (same counts as the rehearsal; unique key `uq_subsidiary_fecha_idsalida` added) |
| 32 | Production `costeomensual_semanapyq`: 48 duplicate captures (2025-05-06..08), the earlier one all zeros | Production data | **Fixed in production 2026-10-01** (48 deleted, 4 unique keys) |
| 34 | The purchases canonical validation required Odoo rows for every migrated branch, so moving their Odoo start to 2026-10-01 failed the purchases pipeline on `wansoft_prueba` (and would have every night) | `scripts/validate_purchases_canonical_layer.py` | **Fixed 2026-09-29** (`66b7f27`): date-aware check (Wansoft history ends before the start date, no Odoo rows before it, Odoo rows required 3 days after it); 8/8 PASS on dev and `wansoft_prueba` |
| 35 | Week-to-date reset at a mid-week Odoo start: the 5 branches migrated on Thursday 2026-10-01 had only Odoo's Thursday in `costeomensual_semanapyq` for the week of 09-28, losing Monday-Wednesday (Acoxpa about 52,900, Tepeyac 29,900, Oceanía 45,500, Coyoacán 11,500) | `getCostReport_SemanaPyQ.py` Odoo path (same latent issue in the monthly one for mid-month starts) | **Fixed 2026-10-02** (D1, `wansoft_period_base`); production rows rewritten by the first night with the code; found by the new continuity validator |
| 36 | Rows recomputed from Odoo kept the Wansoft-only columns of their previous Wansoft version (consumo, desperdicio, robo...; weekly also cortesías/cancelaciones), which Power BI subtracts from `CostoTotal` | Monthly and weekly cost scripts, Odoo `UPDATE` | **Fixed 2026-10-02**; seen on dev only, production had none, would have hit the October wave at its switch |
| 37 | October wave without cost rows for 2026-10-01 (their costs routed to Odoo, which has none until their opening balances) | Cost routing | **Fixed 2026-10-02**: Wansoft until the automatic switch; 10-01/10-02 filled the same morning |
| 38 | The purchases pipeline FAILED on 10-04 and 10-05 (step 10, rollout check): Isabel La Católica and Vía Vallejo had no Odoo rows 3 days after their 10-01 start, because they cannot confirm purchases until their opening balances are loaded (a business state, not a load error). The canonical and analytics loads of those nights were complete (the check is the last step; Analytics purchase OK) | `scripts/validate_purchases_canonical_layer.py` (`check_migrated_split`) | **Fixed 2026-10-05**: when the Odoo download has no confirmed line for the branch it is an `[AVISO]` warning; it still FAILS when Odoo has confirmed lines that did not reach the canonical layer. Tested both paths |
| 39 | Odoo-sourced costs of the first days of each month would stay incomplete forever: Odoo's cost comes from customer invoices that keep being created for ~2 weeks and at the month-end closing, but the nightly cost window was only 10 days | `extract/costs/cost_routing.py` + the three cost scripts' Odoo path | **Fixed 2026-10-05** (`odoo_costs_window_start`: current month, plus previous month until the 10th). Not visible in September only because the cutover backfill ran on 10-01, after the closing. Tested on dev (Puebla 34 days identical to Odoo, continuity OK) |
| 33 | Dev MySQL would not start: inconsistent Aria log after an unclean shutdown, then crashed `mysql.db` / `proxies_priv` / `roles_mapping` | Dev XAMPP datadir | **Fixed 2026-09-28** (Section 0.1) |

**Also confirmed NOT bugs:**
- Oceanía's Costos mismatch on 2026-09-23: Power BI's own Costos page was one day behind its Wansoft source; dev's prior-day snapshot matched exactly.
- San Jerónimo's near-doubled Entradas de Inventario figure: a report-scope mismatch (`TipoEntrada='Factura'` filter) plus one legitimate invoice dev had that Power BI's refresh didn't have yet; not a duplicate insert.
- Coyoacán's -26% Compras gap: a comparison-scope mistake (Odoo against Wansoft's full Compras total instead of `Costo operativo`); about 79% of it was one legitimate software/admin vendor Odoo never captures.
- Power BI's Meseros table excluding the delivery/app placeholder waiter from its ranked total: a report display choice.
- The first backup attempt over the public IP was simply slow (the path leaves the network and returns); switching to the internal IP fixed it.
- `wansoft.sql` showing 0 MB while being written, and phpMyAdmin's #1046 after successful statements: display artifacts (Section 10).

- The 12 `DIFF` lines of the `wansoft` restore rehearsal (and 3 of `zenput`): all lower than production by the loads since the backup.
- The Sales re-run taking 59 minutes: the XML folder started empty and the test copy lacked Friday-Sunday, so everything was downloaded and several days rewritten; not the steady-state time.
- Git warning "LF will be replaced by CRLF" on the PDF: the committed bytes were identical; `.gitattributes` now prevents a corrupting checkout.

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
- **Daily pipeline at 01:30**, after considering 23:30 and 06:00 (Section 17.4). During the shadow week the task ran at 07:00; set to 01:30 at the cutover (2026-10-01).
- **Go-live week plan (2026-09-28 to 2026-10-01):** test on the `_prueba` databases Monday to Wednesday, go/no-go Wednesday night, cutover Thursday.
- The user prefers to be walked step by step, with one command per block, and works in short windows (about 80 minutes at a time); keep steps small and verifiable.
- **2026-09-28:** migration plan B (apply everything on `wansoft_prueba` during office hours) to rehearse exactly what Thursday needs and measure it.
- **2026-09-28:** keep the later (non-zero) row of the 48 `costeomensual_semanapyq` pairs; drop `getallordenesbyday_venta`, `_detalleventa`, `_modificador` and `getallordenesbyday_new_pagos`, in production only on Thursday.
- **2026-09-28:** no Wansoft purchase/inventory downloads for migrated branches after cutover; costs of migrated branches stay on Wansoft while they capture purchases there in parallel.
- **2026-09-28:** production backup on Thursday right before migrating (replaces Wednesday's).
- **2026-09-28:** tukanmx gets two read-only users (`tukan_wansoft`, `tukan_zenput`), created on Thursday after the migration, plus the data access guide in Spanish and English (PDF in Spanish, same layout as the ControlPresupuestos_AP manuals). The public GitHub repo is fine as long as it holds no passwords.
- **2026-09-29:** first shadow comparison: sales, payments, cash closing, butchery, invoices and Zenput identical; Puebla/CentroMyJ costs now real (production's legacy tasks store zeros); remaining cost differences only on days older than the 5-day window, because Wansoft recalculates costs afterwards. Owner chose a separate **`COSTS_LOOKBACK_DAYS=10`** (monthly, weekly PyQ and daily cost scripts; default in code, no `.env` change needed); butchery and cash closing stay on `WANSOFT_LOOKBACK_DAYS=5`.
- **2026-09-30:** second shadow comparison: costs now identical except production's zero rows for closed branch 7697 (only Puebla/CentroMyJ labelled ODOO_COST); one late butchery entry (Taquería Parroquia, 2026-09-24, $931.50) missed by the 5-day window, so butchery moved to `COSTS_LOOKBACK_DAYS` (10). Owner confirmed Isabel, San Jerónimo and Vía Vallejo all start in Odoo on 2026-10-01 (on 09-30: 22 and 37 draft orders, Vallejo none; pilot orders already wiped).
- **2026-09-29:** every branch on Odoo takes costs from Odoo (per day, from its start date); Antenas stays on Wansoft costs until the owner confirms its Odoo database is repaired.
- **2026-09-29:** the branches migrated from Wansoft (Acoxpa, Antenas, Tepeyac, Oceanía, Coyoacán) read Odoo **only from 2026-10-01** for purchases, inventory and costs: production already holds their complete Wansoft history until then (they captured in parallel), so no Odoo history is pulled for them. Puebla and CentroMyJ keep their opening dates (Odoo history from June). The two internal providers are not branches and keep their rows only so they can be excluded.
- **2026-09-28:** the owner wants a runbook in git so a future production deployment can be automated (`docs/production-cutover-runbook.md`).
- **2026-10-01 (cutover day):** use `wansoftuser` for the migration; merge the April 2024 checkpoints on a weekend, not today; tukanmx users with `'%'` until they give IPs; add the Odoo-vs-Wansoft 7-19% warning to the tukanmx guide before handing it over; unregister `Wansoft_Restore_Ensayo`; prepare the Power BI purchases/inventory repoint for Monday 2026-10-05; everything must be thoroughly documented (this report and runbook Section 6.1).

---

# 13. Identified Legacy / Consolidated Backlog

## Go-live week (in order) — CUTOVER DONE (2026-10-01)

Done Mon-Wed: restore rehearsal, migration rehearsal on `wansoft_prueba` (parts 1-5), three shadow runs (2026-09-29 87 min, 09-30 69 min, 10-01 85 min, all 15/15 OK), prueba-vs-production comparisons clean (only explained differences), costs routing and 10-day window, October-wave flip committed. Details in Sections 17.8 and 17.9.

**Cutover on Thursday 2026-10-01: all steps DONE.** Results and timings in Section 17.10; exact commands in runbook Section 6.1.
1. DONE **Step 1** — the 12 `FondaCroned_*` disabled (not deleted). They last ran 01:00-06:30 that morning.
2. DONE **Step 2** — backup `C:\Backups\mysql\20261001_091949`, copied to `PRE_CORTE_2026-10-01`.
3. DONE **Unplanned: Hyper-V host disk** cleaned, 9 → 218 GB free on `SVR-HIKCENTER` C: (unattached VHD/AVHDX of old machines removed from Hyper-V weeks ago, verified against every registered VM's disk chain). The six VMs kept: Analisis_BI, Datos Rodiva, SAE NUBE, SCOTIABANK, W10 IDSE IMSS 02, WansoftServer.
4. DONE **Step 3** — checkpoints `PRE_CORTE_2026-10-01` of `WansoftServer` (10:30:59) and `Analisis_BI` (10:31:29), MySQL stopped 10:30:07-10:32:00.
5. DONE **Step 4** — fresh dev dump (6.75 min, 176 MB, all checks pass), copied to the VM, SHA256 verified.
6. DONE **Step 5** — `wansoft` migrated with `wansoftuser`: part 1 (11.2 min), part 2 (48 deleted, 4 keys), part 3 (61,125 groups / 77,370 surplus, all identical, deleted, 2 indexes), part 4 (5 rows), part 5 (0 rows: already applied on dev). Final: 59 tables + 2 views.
7. DONE **Step 6** — `.env` on the live databases; preflight 11 passed, 0 failed.
8. DONE **Step 7** — 125-day purchases + analytics (49.2 min, 0 failed; by-month check exact) and Puebla/CentroMyJ cost backfill (1.2 min; July/August identical to dev).
9. DONE **Step 8** — `Wansoft_Pipeline_Diario` daily at **01:30**, Ready, next run 2026-10-02 01:30.
10. DONE **Step 9** — `tukan_wansoft` / `tukan_zenput` created and tested; the data guide gained the Odoo-vs-Wansoft warning (`82f6176`). **Pending (owner):** hand the credentials and the PDFs to tukanmx through a private channel.
11. DONE **Step 10** — final review of tasks; `Wansoft_Restore_Ensayo` unregistered; `wansoft_write.cnf` and the uncompressed dump deleted. The weekly backup's first automatic run is today 18:00 (check `C:\Backups\mysql\backup.log` ends with `Backup finished`).

**Rollback, if ever needed:** restore both `PRE_CORTE_2026-10-01` checkpoints from the host and re-enable `FondaCroned_*` (runbook 6.1, end).

## After go-live
- **Fri 10-02, done so far:** first production night 15/15 OK in 38.9 min (01:30-02:09; analytics purchase 13.8 min, so the 43.5 of cutover day was midday load); the 10-01 18:00 backup OK (wansoft 2,982.6 MB in 26.1 min, ~400 MB smaller after the drops/dedup; 3 runs kept); 09-30 Wansoft entries completed by the new loader (251 lines missing from the terminated legacy run); 10-01 entries from the 9 Wansoft-only branches only. Odoo `T+7/T+30` cutover checkpoints evaluate 0 until 2026-10-08 (expected). New read-only `scripts/check_odoo_vs_warehouse.py` (Odoo live vs the production snapshots, confirmed lines + validated receipts, applying the same start-date policy as the ETL): **0 real differences** for 2026-09-26..10-01 (708 lines / 147 receipts excluded by design before the migrated branches' 10-01 start). **Found:** Isabel, San Jerónimo and Vía Vallejo only have draft/RFQ orders in Odoo (owner: they cannot confirm until their opening inventory balances are loaded, expected within ~10 days), Tepeyac nothing confirmed/received in October yet; and the three had **no cost rows for 10-01** (Odoo has no cost for them). **Owner chose (option A):** Wansoft costs for them until Odoo has data (Wansoft still computes their theoretical cost: 10-01 = 49,853 / 39,091 / 25,343, 26-29% of sales; merma/consumo 0); 10-01/10-02 filled the same morning on the VM (`COSTS_ONLY_BRANCHES`, 3 days, OK). **Then automated (owner: "without me telling you"):** new `COSTS_AUTO_SWITCH_TO_ODOO` + nightly stage "Costos - cambio automático a Odoo" (now **16 stages**): each branch switches by itself on the first of 2 consecutive days with Odoo daily cost > 0 and within 0.5x-2x of Wansoft, recorded in `costs_odoo_switch`, backfilled and validated the same night (runbook 7b). **D1 (owner):** month/week-to-date stay whole across a mid-period switch (Wansoft part + Odoo part, each day once). The new validator found it live: the 5 branches migrated on Thursday 10-01 had lost Mon-Wed of that week in `costeomensual_semanapyq` (bug #35, fixed by the first night with this code). Also fixed: rows recomputed from Odoo kept stale Wansoft-only columns (bug #36; not present in production, would have hit the October wave). Tested end to end on dev with Oceanía (0 problems 06-30..10-01). Purchases need no window: the Odoo snapshots are full reloads, confirmed orders enter the night they are confirmed.
- **Fri 10-02 (original plan):** check the first production night: `C:\Apps\Wansoft_ETL\logs\daily_cycle_20261002.log` must end `0 failed`; note the duration, especially the analytics purchase stage (43.5 min at midday on cutover day vs 14.9 in the rehearsal). Check the 18:00 backup of 10-01. Check that the 09-30 Wansoft inventory entries are complete (`FondaCroned_getInputInventory`'s last run was terminated, result 267014; the new 5-day window should have reloaded them). Then build a read-only post-cutover check script: (a) source data — sales vs Wansoft Z close, Odoo-sourced purchases vs Odoo, costs vs the Wansoft/Odoo cost report; (b) purchases vs Wansoft for branches still entering purchases there (Wansoft-only branches, and Odoo branches capturing in parallel, live via the Wansoft API, `Cuenta='Costo operativo'` only); (c) per-branch coherence against the same weekdays of the previous 4 weeks. **Not against Power BI**: after the cutover it reads the new database itself. Things that may look odd on day 1 and must be confirmed, not assumed: October-wave branches with no purchases (no confirmed Odoo orders yet) or no costs (no Odoo cost-of-sales entries yet); NULL columns in Odoo cost rows; cost days 09-22..09-30 rewritten by the 10-day window.
- **Mon 10-05, weekend review:** nights 10-03 (16 stages, 0 failed, 47.6 min), 10-04 (17 stages with the Sunday product-mapping job, 1 failed) and 10-05 (16 stages, 1 failed, 40.1 min). The new costs stage was OK all three nights (October wave still on Wansoft; Acoxpa, Tepeyac, Oceanía, Coyoacán, Puebla, CentroMyJ without duplicates and continuous). The single failure both nights was the purchases rollout check for Isabel and Vía Vallejo (bug #38, fixed the same morning). San Jerónimo confirmed its first Odoo purchases on 10-02 (63 lines) and Tepeyac has 76 lines, so only Isabel and Vía Vallejo still have nothing confirmed.
- **Mon 10-05, real-data checks (all read-only from the dev PC against production):** (a) bug #35 fix confirmed: the 5 migrated branches' week of 09-28 now grows Mon-Wed (Wansoft) + Thu-Sun (Odoo), e.g. Acoxpa 90,943 + 27,940 = 118,883 on the 10-02 row; continuity OK for the 6 Odoo-costed branches. (b) `check_odoo_vs_warehouse` 09-28..10-04: 0 real differences (25 company-days of orders, 26 of receipts). San Jerónimo: 4 confirmed orders (63 lines, 39,027), no validated receipt; Isabel and Vía Vallejo: drafts/RFQs only. (c) Sales vs Wansoft Z (GetGlobalCashClosing, independent of the Candado), 19 branches x 7 days: 129/133 exact; 3 with no Z yet for Sunday 10-04 (Taquería Parroquia, Vía Vallejo, Versalles; closed after midnight, the Candado loads them from XML); Puebla 09-29: Wansoft registered two Z on that calendar day (00:10 = the 28th's 48,780; 01:34 = a single-order 6,063 Z of ticket 2990, which is in the base once inside the 29th's 42,588 whose real Z ran at 00:00 on the 30th) -- data correct, the Candado just rewrites that day nightly with an ALERTA until it leaves its 10-day window (~10-09). (d) Coherence vs the same weekday of the previous 4 weeks: sales/ticket outliers are real (Z-confirmed): Vía Vallejo 09-30 0.33x, Playa 09-29 0.32x, CentroMyJ 09-29 2.18x and 10-02 0.19x. Weekend 10-03/04 costs are low for many branches in BOTH sources and the warehouse equals the live sources exactly: Wansoft recalculates later (window will catch it); **Puebla's Odoo cost since 10-01 is only 2.4-7.7k/day (Sunday 1.6% of sales) vs 14-56k in September: ask whoever posts Puebla's October customer invoices in Odoo.** Purchases: Isabel's week has only its Wansoft days (expected); Cancún and Metepec (Wansoft) at ~0.3x of their average, possibly invoices not captured yet. **Re-run the coherence check on Wed 10-07** to see whether the weekend costs rose. **Then found (same day):** the low Odoo costs are incomplete invoicing, not a fault: in September Odoo invoiced exactly 100% of Wansoft's net sales every day but with a lag (40-70% at +1 day, 70-100% at +7, 92-100% at +14, all at the month-end closing, 766 invoices on 09-30); October at +1..+4 days: Acoxpa 32-75%, Puebla 5-32%, the others 23-97%; cost per invoiced peso unchanged (35-38%). Owner chose: **(A)** Odoo cost window = current month + previous month until the 10th (bug #39, done); **(B2)** Central de Reportes shows an **estimated** cost (cost per invoiced peso x Wansoft net sales, labelled "estimado") while the period is not fully invoiced -- to build in the Central de Reportes chat. Wansoft-side settling: snapshot of all production costs 09-21..10-05 saved outside the repo at `C:\Users\JavierViniegra\wsc\cost_snapshots\costs_2026-10-05.csv`; compare on Wednesday. Central de Reportes simulation of week 40 (live `wansoft`, `verificar_fuentes` 9 checks 0 FAIL): sales sound (gross 14.21 M, +1.5% vs previous week, -2.7% vs last year), closings 127/133 (6 Sunday closings made after midnight load the next night), cost total 25.4% not reliable yet (see above).
- **Mon 10-05, plan (owner, 2026-10-01, later the same day):** (1) review how the first production week behaved (nights 10-02 to 10-05; owner, 2026-10-02: nothing on the weekend, logs and real-data tests on Monday): the three `daily_cycle_2026100{3,4,5}.log` must end `0 failed` with **16 stages**, the new stage "Costos - cambio automático a Odoo" OK (the October wave "sigue en Wansoft" unless their balances arrived, every Odoo-costed branch "sin duplicados y acumulados continuos"); confirm in production that the 5 migrated branches' week of 09-28 in `costeomensual_semanapyq` now includes Monday-Wednesday (bug #35); run `scripts/check_odoo_vs_warehouse.py` for 09-28..10-04 (expect 0 real differences) and the continuity check on production; sales vs Wansoft Z close and per-branch coherence vs the previous 4 weeks; whether Isabel/San Jerónimo/Vía Vallejo/Tepeyac have confirmed anything in Odoo yet; (2) **simulate the week's commercial reports with the Central de Reportes app** on the production data (the owner needs to start working with Central de Reportes); (3) **start the expenses domain**, `analytics_expense_invoices` (design `docs/analytics-expense-invoices-design.md`); (4) only if time allows, the Power BI repoint = the **purchases/inventory repoint package** (Section 7, "Deployment / operations"; needs the `.pbix` or its queries).
- **Hyper-V housekeeping (planned weekend; the owner asked about it on cutover day and it was deliberately postponed):** order: first delete the `PRE_CORTE_2026-10-01` checkpoints of both VMs once two or three nights are good, then **merge WansoftServer's two checkpoints of April 2024** (`Remove-VMSnapshot`; the DB writes to a 260 GB differencing disk on top of 82 + 153 GB since then) once space allows; decide on `C:\Users\Administrador\Desktop\BackupWansoft\WansoftServer_6ene25` (459 GB VM copy from 2025-01-06); about 20 small orphan AVHDX of other VMs (Datos Rodiva, W10 IDSE IMSS - copia, SAE NUBE; likely leftovers of a backup tool) left alone; host drive F: "Respaldo" is full (not ours, tell its owner).
- Remove the `FondaCroned_*` tasks after one or two good nights.
- Antenas costs: remove it from `COSTS_WANSOFT_TEMPORARY_EXCEPTIONS` when the owner confirms its Odoo database is repaired.
- Isabel / San Jerónimo / Vía Vallejo costs switch to Odoo **automatically** (no action needed); watch the nightly log for `[AVISO] ... cambió a costos de Odoo desde ...` and check `costs_odoo_switch.validation_result` = OK afterwards. Until their opening balances are loaded their October purchases are empty in the warehouse (nothing confirmed in Odoo). Tepeyac had nothing confirmed/received in October on 10-02 either: ask.
- **Thu 10-08:** first T+7 Odoo cutover checkpoints for the branches started 10-01.
- Security: split `wansoftuser`; restrict phpMyAdmin; TLS or IP restriction for tukanmx.
- README full cleanup; schema comparison dev vs production after cutover; automation ideas in runbook Section 7.

## Older backlog
- **Inventory valuation for pure-Odoo branches** (Puebla, CentroMyJ): no cost/value field on inventory movements; needed for a real COGS.
- **Root-cause the residual 7-19% Compras gap** between Odoo and Wansoft's `Costo operativo` (Acoxpa, Coyoacán, Oceanía).
- **San Jerónimo:** ~$5,915 gap in "Gastos de venta" and $49,937 of Wansoft invoices with blank `Cuenta`; re-validate its Costs/Compras after the October cutover.
- **Check whether Antenas, Tepeyac or CentroMyJ have the August 1-27 dev-only Sales gap.**
- **Django app:** define what each role sees before building permissions (Section 16.3).
- Raise production's `innodb_buffer_pool_size` if still small (never checked).
- The weekly product-mapping job (Sundays 11am) has never been observed running as scheduled; it is part of the run-once cycle on Sundays.
- Origin of the loose untracked root files (`extractAllOrdersByDay.py`, `extractAllOrdersByDay_old.py`, `getAllOrdersByDay.py`).
- The tasks VM's `.env` is local to that machine and holds every credential; it is the only copy of its settings.

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

## 17.3 Restore rehearsal (done)

- `Wansoft_Restore_Ensayo` ran Friday 2026-09-25 22:00 to Saturday 00:17: **22 tables in 121.5 min**, 10 `SAME` (tables the legacy tasks do not load daily) and 12 `DIFF`, every one with the copy **below** production by about one night of loads (e.g. `new_venta` -795, `getglobalcashclosing` -18, `getexpenses_factura` -116). Verdict: the backup restores faithfully.
- `zenput` restored into `zenput_prueba` on 2026-09-28: 4 tables in 0.1 min, 1 `SAME`, 3 `DIFF` all lower.

## 17.4 The tasks VM deployment (done 2026-09-25, updated 2026-09-28)

- Repository `C:\Apps\Wansoft_ETL`, `.venv` (Python 3.12, pinned `requirements.txt`), `core\config\.env` locked with `icacls`: `ENV=prod`, `WANSOFT_DB_HOST=192.168.100.183`, **`WANSOFT_DB_NAME=wansoft`, `ZENPUT_DB_NAME=zenput` since the cutover (2026-10-01)** (`wansoft_prueba` / `zenput_prueba` during the shadow week; `ZENPUT_DB_NAME` was mistyped as the IP until 2026-09-28), `XML_DOWNLOAD_DIR=C:\Apps\Wansoft_ETL\data\xml`, lookbacks `10 / 5 / 35`. Preflight `python -m scripts.check_env`: **11 passed, 0 failed** against the live databases on 2026-10-01.
- `Wansoft_Update_Repo_Diario` (00:30, `git pull --ff-only`, as `analisisbi`), verified end to end.
- `Wansoft_Pipeline_Diario`: 07:00 against the test databases during the shadow week (from 2026-09-28); **re-registered on 2026-10-01 daily at 01:30 against production** (`register_daily_cycle_task.ps1 -Enable -Time 01:30`, user AnalisisBI, RunLevel Highest, 4-hour execution limit, `StartWhenAvailable`). First production run: 2026-10-02 01:30.
- `scripts/run_daily_cycle.py` + `deploy/run_daily_cycle.ps1`: every line now goes to the console and to `logs\daily_cycle_<yyyyMMdd>.log`; it is safe to follow the log with `Get-Content ... -Wait -Tail 20` from another window.

## 17.5 Go-live week (2026-09-28 to 2026-10-01)

| When | What | Status |
|---|---|---|
| Fri 09-25 22:00 | Restore rehearsal | Done, good |
| Mon 09-28 | Read restore log; restore `zenput_prueba`; schema comparison; migration rehearsal on `wansoft_prueba`; first full cycle on the VM; register shadow run | **Done** (17.8) |
| Tue 09-29 07:00 | First shadow run; compare `wansoft_prueba` vs production | **Done** (17.9) |
| Wed 09-30 07:00 | Second shadow run and comparison; **go/no-go** in the evening | **Done, go** (17.9) |
| **Thu 10-01** | Cutover (17.6) | **Done** (17.10) |

## 17.6 Cutover checklist (Thursday 2026-10-01) — the plan; executed as recorded in 17.10

Command-level detail, expected results and timings: `docs/production-cutover-runbook.md`, Section 6.

1. **Odoo readiness:** confirmed orders exist for Isabel, San Jerónimo, Vía Vallejo; flip `COMPANY_SOURCE` to `"odoo"` and `ROLLOUT_COMPANY_EXPECTATIONS` to `active: True` in `core/config/companies.py`, seed/maintenance SQL and `odoo_company_migration_policy`; commit, push, `git pull` on the VM.
2. **Stop the legacy tasks:** disable the 12 `FondaCroned_*` tasks (delete after one or two good nights). Leave `ControlPresupuestos_AP`, the backup task and system tasks alone.
3. **Backup right before migrating** (owner's decision 2026-09-28, replaces the Wednesday backup): `backup_mysql.ps1`, verify `Backup finished`, copy the folder to `C:\Backups\mysql\PRE_CORTE_2026-10-01` (outside the pruning pattern). About 30 min.
3b. **Hyper-V checkpoints of both VMs** from the host, after the backup, with MySQL stopped for a minute on the database VM (runbook 2c); rollback = restore both checkpoints and re-enable the legacy tasks; delete the checkpoints 2-3 days after a good cutover.
4. **Migrate the live `wansoft`** (additive, plus the agreed drops), with an account that has write rights on `wansoft` (the `backup` user only writes to `_prueba`; `restore_mysql.ps1` refuses live names on purpose, so load with the `mysql` client):
   - Part 1: a **fresh** dump of the 41 tables + 2 views from dev (runbook 5.1; checks: `Dump completed`, 0 `DEFINER`, 41 `CREATE TABLE`, no `` `wansoft`. `` references). Rehearsal: 5.7 min dump, 176 MB, 11.6 min load.
   - Part 2: `sql/migrations/cutover_02_small_tables.sql` (drops the 4 old Sales tables, dedups `costeomensual_semanapyq`, 3 generated columns, 4 unique keys). Re-check the duplicate count first. Seconds.
   - Part 3: `sql/migrations/cutover_03_large_inventory_tables.sql`, **one step at a time**: A materialise duplicates (~26 min), B prove they are exact copies (must equal), C delete by primary key keeping the lowest id, D the two indexes online (~5 min), E drop helpers. Budget about 35 min.
   - Part 4: `sql/migrations/cutover_04_migrated_branches_start_oct1.sql` (Odoo start 2026-10-01 for Acoxpa, Antenas, Tepeyac, Oceanía, Coyoacán; expect 5 rows).
   - **Cost history of Puebla/CentroMyJ** (found 2026-09-30): production holds zeros for their costs since opening (legacy tasks only read Wansoft); after the `.env` switch run the three cost stages with `COSTS_LOOKBACK_DAYS=125` and `COSTS_ONLY_BRANCHES=Puebla,CentroMyJ` (runbook 3d; 19 s for the monthly on dev). Also: in Odoo-sourced cost rows the columns with no Odoo equivalent are NULL, so SQL consumers must use `COALESCE` (`CostoTotal - CostoDeConsumo` is NULL for Puebla); Power BI's DAX treats BLANK as 0. The data guide says so.
   - Part 5: `sql/migrations/cutover_05_october_wave_relabel_wansoft_history.sql` (relabels Isabel/San Jerónimo/Vía Vallejo Wansoft canonical rows to `wansoft_history_before_odoo`; replaces the full-delete reload of the rollout sequence). The COMPANY_SOURCE flip and active validator expectations for the three were committed on 2026-09-30 (owner confirmed all three start in Odoo on 10-01); if the go/no-go is NO, revert that commit before 00:30.
5. **Switch the VM `.env`:** `WANSOFT_DB_NAME=wansoft`, `ZENPUT_DB_NAME=zenput`; `python -m scripts.check_env` must be all PASS. **Then** one purchases + analytics run with `PURCHASES_LOOKBACK_DAYS=125` (runbook step 3c) so the June-September Wansoft invoices of those 5 branches enter the canonical layer; never the full-delete reload script.
6. **Daily cycle to 01:30:** `register_daily_cycle_task.ps1 -Enable` (default time 01:30). First production run the night of 10-01 to 10-02; watch `logs\daily_cycle_<date>.log`.
7. **tukanmx users:** run `sql/maintenance/create_tukan_readonly_users.sql` as root with real passwords (never committed; restrict `'%'` to their IPs if given); hand over the credentials privately with `docs/data-access-guide/`.
8. The first automatic weekly backup runs at 18:00 that day.
9. Validate the first nights (10-01 to 10-03) **against real source data and against past weeks**, not Power BI (after the cutover Power BI reads the new database itself, so comparing against it proves nothing; owner, 2026-09-30): (a) source check: sales against Wansoft's daily Z close (the Candado already reconciles it nightly), Odoo-sourced purchases against Odoo, costs against the Wansoft or Odoo cost report per branch; (b) purchases against Wansoft for every branch still entering purchases there: Wansoft-only branches (warehouse vs Wansoft) and Odoo branches still capturing in Wansoft in parallel (Odoo vs Wansoft, read live from the Wansoft API, read-only, since the pipeline no longer stores their Wansoft invoices; compare against the Costo operativo bucket); (c) coherence: per branch, daily/weekly sales, tickets, purchases and cost against the same weekdays of the previous 4 weeks, flagging zero days, doubled values and October-wave branches without Odoo purchases.
10. Afterwards: security follow-ups (runbook Section 8), then the Django app (Section 16).

## 17.7 Risks and things not to forget
- (Shadow week only) The shadow run (07:00) and the legacy tasks (01:00-06:30) both called the Wansoft SOAP API and were kept apart in time. Since the cutover only `Wansoft_Pipeline_Diario` (01:30) calls it.
- Heavy operations (dump, restore, the big `GROUP BY`/`ALTER`) slow the database used by Power BI and `ControlPresupuestos_AP`; the rehearsal ran them in office hours without complaints, but prefer quiet hours on Thursday.
- Nothing may write to `getoutgoinginventory_salida` between part 3 steps A and D, so part 3 runs only after the legacy tasks are disabled.
- The pipeline task needs the `analisisbi` password at registration; nothing else stores it.
- `wansoftuser` can write to the live `wansoft`; until step 5 the `.env` database names are the only barrier.
- If anything is unclear about which machine a command runs on, check Section 0.2 first.

## 17.8 Monday 2026-09-28 — what was done and found

1. **Restore rehearsal judged good** (17.3); `zenput_prueba` restored.
2. **Schema comparison dev vs production** (read-only, from the dev PC): `zenput` identical; `wansoft` missing 41 tables and 2 views, 3 generated `created_date` columns, **5 unique keys and 1 index** from `sql/maintenance/add_unique_keys_dedup_protection.sql` (applied to dev 2026-09-14, never to production; `getOutgoingInventory.py` upserts against one of them, so it is mandatory). Dev's `campo1`/`campo2` on `getallordenesbyday_venta` were a leftover stub (not migrated). `getexpenses_factura`'s key already existed in production.
3. **Migration rehearsed on `wansoft_prueba`** (owner chose to run everything in office hours to measure it): dump 5.7 min / 176 MB; load 11.6 min (65 tables); part 2 in seconds (48 found, 48 deleted, 4 keys); exits table: plain duplicate count 31.4 min, materialise 25.6 min (61,125 groups / 138,495 rows), all groups exact copies, 77,370 deleted, both indexes online in 4.8 min; helpers dropped; final **61 tables**.
4. **First full cycle on the VM:** 15/15 OK in 35.3 min, with four bugs found and fixed (#27 Sales XML folder and false OK; #28 log lines lost; #29 preflight WARN; #30 `.env` typo and missing grants). Sales re-run: 59.2 min, **190/190 XML**.
5. **Shadow run registered** at 07:00, State Ready.
6. **Documentation:** `docs/production-cutover-runbook.md` (new, step-by-step with timings and automation ideas), README updated (it had not changed since 2026-08-20), `docs/data-access-guide/` (Section 19).
7. **Commits of the day:** `08e3425`, `1c052c0`, `aa1af8a`, `fb1f15b`, `743e442`, `7f38fb1`, `9861ff6`, `572f93b`, `fe9bb41`, `9f3c3b8`, plus the runbook backup step and this report.

---

## 17.9 Tuesday 2026-09-29 to Thursday 2026-10-01 — what changed

- **Shadow runs:** 09-29 87 min, 09-30 69 min, 10-01 85 min; all 15/15 OK. The morning load makes runs slower than at midday (35 min on 09-28).
- **Comparison script** `scripts/compare_shadow_run.py` (read-only, per day and branch; EXPECTED for Odoo branches' Wansoft gaps, ODOO_COST for Odoo-routed costs). Last result (09-30): sales, payments, cash closing, invoices, Zenput identical; costs identical except production's zero rows for closed branch 7697; one late butchery entry; entries of the latest day differ only by capture time (01:05 vs 07:00).
- **Costs:** `COSTS_LOOKBACK_DAYS=10` (default in code) for the monthly, weekly and daily cost scripts and butchery (Wansoft recalculates costs; butchery gets registered late); per-day routing `extract/costs/cost_routing.py` (Odoo from each branch's start date, Wansoft before; Antenas temporary exception); `COSTS_ONLY_BRANCHES` for one-off backfills. Production holds **zeros** for Puebla/CentroMyJ costs since opening (legacy tasks), fixed by the backfill at cutover. Odoo cost rows leave columns without Odoo equivalent NULL: SQL must use `COALESCE` (guide updated).
- **Start dates:** the 5 branches migrated from Wansoft read Odoo only from **2026-10-01** (`cutover_04`; production keeps their parallel Wansoft history); rehearsed on prueba with a 125-day Wansoft canonical window (never the full-delete reload script). October wave flipped to Odoo in code on 09-30 (`bdf07dd`), with `cutover_05` relabelling their Wansoft history (190,351 lines on prueba). Canonical validation made date-aware (bug #34).
- **October wave in Odoo on 09-30:** Isabel 22 and San Jerónimo 37 draft orders, Vallejo none; the owner confirmed all three start on 10-01.
- **Docs:** data guide corrected (both languages, HTML, PDFs; `build_en_html.py` builds the English PDF); runbook gained steps 2b (backup), 2c (Hyper-V checkpoints; both VMs on the same host), 3c (125-day purchases), 3d (Puebla/CentroMyJ costs), and post-cutover validation against source data, Wansoft and past weeks.
- **Cutover day:** see 17.10.

## 17.10 Thursday 2026-10-01 — the cutover, as executed

All steps OK; nothing had to be rolled back. Exact commands, expected and obtained results: runbook Section 6.1.

| Step | Where | Result |
|---|---|---|
| 1. Legacy tasks | Tasks VM | 12 `FondaCroned_*` disabled after their last 01:00-06:30 run. `getInputInventory` shows result 267014 (terminated): check 09-30 entries on 10-02 |
| 2. Backup | Tasks VM | `20261001_091949` (wansoft 3,392.6 MB, 32.2 min), copied to `PRE_CORTE_2026-10-01` |
| Host disk (unplanned) | `SVR-HIKCENTER` | C: 9 → 218 GB free (old unattached VHD/AVHDX removed after a chain check) |
| 3. Checkpoints | Host | `PRE_CORTE_2026-10-01` on both VMs (`Production` type), MySQL stopped 10:30:07-10:32:00; 218.2 GB still free |
| 4. Dev dump | Dev PC | 6.75 min, 175,943,354 bytes (2,035,284,204 uncompressed), 41 tables + 2 views, 0 DEFINER, 0 `wansoft`. refs; SHA256 matched on the VM |
| 5.1 Load | Tasks VM → DB | 11.2 min, `wansoft` 22 → 63 tables + 2 views |
| 5.2 `cutover_02` | Tasks VM → DB | Pre-check 48/0/0/0 duplicates; 48 deleted; 4 unique keys; 4 old Sales tables dropped |
| 5.3 `cutover_03` | Tasks VM → DB | A 26.6 min: 61,125 groups / 138,495 rows / 77,370 surplus (= rehearsal); B all identical; C 77,370 deleted; D 3.8 min, both indexes; E helpers dropped → **59 tables + 2 views** |
| 5.4 `cutover_04` | Tasks VM → DB | 5 rows: Costa Nera (was 07-01), Oceanía (06-30), Antenas, MAQ, Coyoacán (06-01) → 2026-10-01 |
| 5.5 `cutover_05` | Tasks VM → DB | 0 rows relabelled: dev had it applied, so the dumped tables already carried `wansoft_history_before_odoo` (Isabel 74,387, San Jerónimo 52,960, Vía Vallejo 62,390 lines; last Wansoft order 2026-09-22 in the dump) |
| 6. `.env` | Tasks VM | `wansoft` / `zenput`; preflight 11 passed, 0 failed |
| 7a. Purchases 125 d | Tasks VM | 49.2 min, 0 failed (purchases 5.7, analytics 43.5). 801,670 lines / 739,886 business / 155,074 orders / 669,831 daily rows; business purchases with VAT since 2021: 1,072.3 M |
| 7a check | | Migrated 5: only `wansoft` May-Sept; Puebla/CentroMyJ `odoo` from June; October Odoo already in for Acoxpa (24 lines), Puebla (17), Oceanía (6), CentroMyJ (2); no month with both systems |
| 7b. Costs backfill | Tasks VM | 1.2 min, 3 stages OK. Month-end `CostoTotal`: CentroMyJ Jul 978,581.55 / Aug 877,603.88 / Sep 772,434.77; Puebla Jul 102,389.11 / Aug 1,156,603.26 / Sep 816,400.38 (Jul/Aug identical to dev); zero days only CentroMyJ June and Puebla June + Jul 1-26 |
| 8. Daily task | Tasks VM | 01:30 daily, Ready, AnalisisBI, Highest; next 2026-10-02 01:30 |
| 9. tukanmx | DB (root, phpMyAdmin) | 2 users, 22 table grants + `zenput.*`, host `'%'`; test: allowed read OK (5,844 `dim_time` rows), other table denied (1142) |
| 10. Review | Tasks VM | Tasks as expected; `Wansoft_Restore_Ensayo` unregistered; temp `.cnf` and uncompressed dump deleted (`.gz` kept in `NUEVAS_20261001`) |

Also on cutover day: the data guide gained the Odoo-vs-Wansoft 7-19% warning (`82f6176`); the owner asked for the Power BI purchases/inventory repoint for Monday (Section 7); the owner asked whether to merge the old checkpoints now and agreed to postpone it to the weekend.

---

# 18. Next Steps — HANDOFF PROMPT

**Paste this as the first message of the new chat (Friday 2026-10-02, first day after the cutover):**

```
Continúo el proyecto Wansoft + Odoo + Zenput Data Warehouse & ETL Pipeline.
EL CORTE A PRODUCCIÓN SE TERMINÓ el jueves 1 de octubre de 2026 (todos los
pasos OK). Lee completo PROJECT_CONTEXT_REPORT.md en la raíz del repositorio
antes de responder, empezando por la Sección 13 ("Go-live week" y "After
go-live"), luego la 17.10 (lo que se corrió en el corte), la 0 (máquinas) y
la 7. Los comandos exactos del corte están en
docs/production-cutover-runbook.md, sección 6.1.

Hoy toca revisar la primera noche en producción: el log
C:\Apps\Wansoft_ETL\logs\daily_cycle_20261002.log en la VM de tareas (debe
terminar en 0 failed; fíjate en lo que tardó la etapa de analytics de
compras), el respaldo semanal de las 18:00 del jueves, y que las entradas de
inventario de Wansoft del 30 de septiembre estén completas. Después, el
script de revisión post-corte de solo lectura contra las fuentes (no contra
Power BI). El lunes 5: analytics_expense_invoices y el paquete para mover
las páginas de compras e inventario de Power BI a la capa unificada.

Reglas: la VM de tareas (Analisis_BI / DESKTOP-1HTRVT4, usuario analisisbi)
NO tiene MySQL y su .env YA APUNTA A PRODUCCIÓN (wansoft / zenput): cualquier
corrida manual escribe en las bases reales. La base está en WansoftServer
(192.168.100.183); los comandos del anfitrión Hyper-V van en SVR-HIKCENTER;
las tareas de ControlPresupuestos_AP no se tocan; las FondaCroned_* siguen
deshabilitadas (se borran tras una o dos noches buenas); los checkpoints
PRE_CORTE_2026-10-01 se borran a los 2-3 días. Me gusta ir paso a paso, un
comando por bloque.
```

**Suggested title for the new chat**: `FONDA (Wansoft): Paso 26: Primera noche en producción y revisión post-corte`

---

# 19. External data access — tukanmx (new 2026-09-28)

tukanmx.com will connect to the `wansoft` and `zenput` databases, build its own ETL and deliver a question-and-answer / chatbot layer.

- **Guide:** `docs/data-access-guide/data-access-guide.es.md` and `.en.md` (kept in sync), plus `data-access-guide.es.pdf` rendered from `data-access-guide.es.html` with `render_pdf.py` (xhtml2pdf, run with `ControlPresupuestos_AP\.venv\Scripts\python.exe`; same layout as that project's manuals; page-numbered contents). It covers layers, seven golden rules, the branch crosswalk (three different branch identifiers across tables; name mismatches such as Metepec = "Tollocan", Versalles = "Taquería Exhibimex", Napoles = "Polyforum", Acoxpa = "Costa Nera"; `7697` Taqueria San Fernando only in historical costs), which table answers which question, per-domain fields/joins/example SQL (all three examples run on dev), tables not to use, freshness and access.
- **Users:** `sql/maintenance/create_tukan_readonly_users.sql` creates `tukan_wansoft` (SELECT on the documented `wansoft` tables only) and `tukan_zenput` (SELECT on `zenput`), each with `MAX_USER_CONNECTIONS 4` and `MAX_STATEMENT_TIME 1800`. Tested on dev (allowed read works; other tables, writes and cross-database access denied). **Created in production on 2026-10-01** as root in phpMyAdmin, host `'%'` (tukanmx gave no IPs yet; restrict when they do), passwords generated locally by the owner (24 alphanumeric characters), never committed or shared in chat. `SHOW GRANTS` showed the 22 table grants; tested from the tasks VM: `dim_time` readable (5,844 rows), `canonical_purchase_order_snapshot` denied (error 1142). **Pending (owner):** hand the server address (`187.251.203.223:3306`), users, passwords and the two PDFs to tukanmx through a private channel.
- **Guide update 2026-10-01 (`82f6176`):** Section 5.3 warns that Odoo and Wansoft purchases do not match each other for the same branch and month (Odoo 7-19% above Wansoft's Costo operativo in September: Acoxpa +7.2%, Coyoacán +11.1%, Oceanía +18.5%), a source-system difference, not a load error. Spanish and English Markdown, Spanish HTML (by hand), English HTML (`build_en_html.py`, needs the `markdown` module: system `python`) and both PDFs (`render_pdf.py` with `ControlPresupuestos_AP\.venv`).
- **History (measured in production 2026-09-28, guide Section 4.1):** sales tickets since 2021-09-01, payments per ticket only since 2025-01-01, cash closing 2022-01-01, daily cost 2021-07-31, monthly cost 2022-01-01, weekly cost 2024-01-02, butchery 2022-01-01, invoices by account 2019-02-18, inventory entries 2021-09-01, exits 2020-11-30 (1.15 M rows with an empty `0000-00-00` date), Zenput 2025-06. **Unified purchases hold the full production history (from 2021-09-01): rows and amounts match production's Wansoft invoices exactly for 2021-2025, and 2026 matches once the Odoo start-date rule is applied (104,099 vs 104,104 rows through 09-22).** Unified stock is a current snapshot by design.
- **Sales gap accepted by the owner:** 2021-12-14..16 and 29..31 exist in the old `getallordenesbyday_venta` (4,366 tickets, $7.76 M) but not in `_new_venta`; 12-17..28 is nearly empty in both. The owner decided not to rescue it (the `_new_` history is enough).
- **Keep in sync:** when a table is added to or retired from the business layer, update both guides, the HTML/PDF and the grants file.

---

# Permanent Rule

Regenerate this document in full (never as patches) when: the user explicitly asks, a major step closes, the conversation gets very long, context exceeds ~70%, or a new chat needs to be opened due to token limits. In that last case, also generate:
1. The handoff prompt (Section 18, first code block, if applicable).
2. The suggested title for the new chat, in the format **`FONDA (short project): Paso N[-M]: <short description>`** (same style as the user's own session list). `FONDA` is a fixed prefix; `(short project)` identifies which project (here: "Wansoft"). Use `N` = the major step/block number in progress, `-M` = sub-part suffix if the step spans multiple consecutive sessions/chats.

**Note on language:** this document, all commit messages, and all documentation pushed to GitHub in this project must be written in English — even though the working conversation with the user is in Spanish. See project memory `feedback_github_content_english_only` for the full rule.
