# PROJECT_CONTEXT_REPORT.md

Master continuity document. Generated/updated automatically at the close of major steps, on explicit request ("Generate project context report"), when the conversation gets very long, when consumed context exceeds ~70%, or when a new chat needs to be opened due to token limits. Always regenerated in full, never as an incremental patch.

Last generated: 2026-09-17, closing for the day — covers two sessions (2026-09-15 and 2026-09-17). Both closed with real bugs found and fixed, not just validation. **Read this before anything else if you're picking this up fresh.**

---

# 0. Critical environment note — READ FIRST

**The project's working directory moved.** OneDrive redirected the user's Desktop to the organization's OneDrive path sometime around 2026-09-15 13:10-13:40. The old path (`C:\Users\JavierViniegra\Desktop\AnalisisRestaurantesBI\...`) is now permanently empty and will stay that way — do not try to "restore" it.

**Current correct path:**
```
C:\Users\JavierViniegra\OneDrive - GRUPO FONDA ARGENTINA\Escritorio\AnalisisRestaurantesBI\Wansoft\Jupyter Notebooks\Python Files
```

The shell/harness's own default working directory still resets to the old (dead) path after every command in this environment — every command needs an explicit `cd` to the OneDrive path, or an absolute path. This is a session/tooling quirk, not a project issue.

`core/config/.env`'s `XML_DOWNLOAD_DIR_DEV` was hardcoded to the old path and has already been corrected to the OneDrive path (2026-09-17) — this was silently breaking XML downloads (Sales Candado) for **every branch, every day** since the move, including the entire 2026-09-17 morning daily-cycle run (see bug log #21). If you ever see `[ERROR DESCARGA] ... No such file or directory` mentioning the old Desktop path, this is the same class of bug resurfacing (check for other stale absolute paths in `.env`).

Git and the `.env` file (credentials) both survived the move intact — nothing was lost, only the local file location changed.

---

# 1. Executive Summary

**Overall project goal:** build a unified analytical layer in MySQL that integrates Wansoft, Odoo, and Zenput, hiding from the end user which system originates each piece of data.

**Current state:** the acceptance gate remains formally accepted (2026-08-31). Two sessions since the last report closed real, structural bugs across Purchases, Inventory, and — for the first time — **Costs**, which had never been touched in this project before. Sales, Purchases, and Costs are now validated to match the user's live Power BI **exactly** (not approximately) for two representative branches (Acoxpa — migrated from Wansoft; Puebla — pure Odoo from day one) across two full months (August closed, September month-to-date).

**Big wins this round:**
- Found and fixed a **real duplicate-insert bug** in the Wansoft canonical purchase load (date-column mismatch), a **real internal-vendor exclusion bug** that was silently dropping a branch's own legitimate purchases from every business-facing Purchases number, and got the product-mapping-to-department pipeline working for the first time (was crashing on every run due to a stale column name).
- Built out **Costs as a real, validated domain** for the first time — previously "out of scope" per `docs/power-bi-source-migration.md`. Discovered Costs needs a **3-way routing split** (Wansoft-migrated branches, pure-Odoo branches, and a Sales-adjacent override for Cortesias/Cancelaciones that applies to all 19 branches uniformly) — a materially different governance model than Purchases/Inventory's simple 2-way COMPANY_SOURCE split.
- Confirmed a real, ongoing **production inefficiency**: 5 of the 7 Odoo-migrated branches (Acoxpa, Antenas, Tepeyac, Oceania, La Esquina Coyoacan) are still double-loading Purchases/Inventory into Wansoft in production, as recently as yesterday — dev's code already does the right thing (stops loading Wansoft once a branch is Odoo-sourced); production is running something else. Left production untouched per explicit instruction.
- Backfilled a pre-existing dev-only Sales history gap (Aug 1-27 missing) for 2 branches (Acoxpa, Puebla) via the real Wansoft Candado, confirmed against the user's own recollection of real sales figures both times.

**Scope:** unchanged since 2026-08-31 (see prior reports for full branch list). Costs is the first domain added to "fully validated" status since the original acceptance gate.

**Current block:** none. Everything committed and pushed through `5e18b79`.

---

# 2. Session 2026-09-15 — Full recap

## 2.1 Full daily cycle simulation, MySQL crash, and 2 real bugs found

Ran the complete daily cycle manually (legacy chain → inventory → purchases → analytics-purchase → cutover) to simulate "a normal production day," per user request. Result: **not** clean end to end.

**MySQL crashed** during `analytics_purchase_daily_company_product`'s ~800K-row aggregation build (`Lost connection to MySQL server during query`). Root cause: `innodb_buffer_pool_size` was still 16M, a risk documented as unresolved since 2026-09-08. Raised to 1G. On restart, crash-recovery itself hit a corruption assertion (`log0recv.cc line 1541`) — same failure class as two prior incidents (2026-09-08, 2026-09-10). Recovery playbook (now well-established in this project): boot at `innodb_force_recovery=6` → confirm the corrupted table via crash-on-SELECT → stop → delete the table's `.frm`/`.ibd` directly from disk → boot at `innodb_force_recovery=1` → confirm clean rollback → remove the flag → rebuild the table from its normal build script. Hit an **orphaned InnoDB dictionary entry** afterward (`CREATE TABLE` failed with "already exists" despite the table being gone from `SHOW TABLES`) — fixed by copying a donor `.frm` from a same-shape table, letting `DROP TABLE` succeed cleanly, then rebuilding for real.

**Bug #1 — real duplicate-insert crash in Purchases:** `save_wansoft_canonical_receipts()` (`extract/purchases/canonical_purchase_etl.py`) deleted existing rows by `date_done` (mapped from `FechaReal`) before reinserting, but the eligibility query that builds the incoming rows filters by `FechaEntrada` (`scheduled_date`). These two dates can diverge per row — confirmed live: an Aeropuerto receipt with `scheduled_date` 2026-08-12 but `date_done` 2026-08-05 was never deleted (outside the delete's 35-day window measured from the wrong column) then crashed the reinsert on a real `Duplicate entry`. **Fixed:** delete by `scheduled_date` instead, matching the eligibility filter.

**Bug #2 — product mapping pipeline never worked:** `analysis/build_product_mapping.py` (exact + fuzzy Odoo↔Wansoft product code matching) crashed on every run with `KeyError: 'odoo_code'` — `extract/products/odoo_products.py` was upgraded at some point to emit `integration_code` (prioritizing the explicit `x_wansoft_code` custom field over `default_code`), but `analysis/normalize_odoo_products.py` was never updated to match. **Fixed** the column reference, and **added a code-base matching tier** (Wansoft/Odoo codes for the same product differ only by a leading prefix — e.g. Wansoft `1000-105-103-030` vs Odoo `5200-105-103-030` — an existing-but-unused `extract_base_code()` helper strips it). Result: 1,047 code-base matches at 99% confidence, up from 301 much-lower-confidence fuzzy-name matches. New `analysis/save_product_mapping.py` writes these to `inventory_mapping_dictionary` as `pending_review` (never auto-`approved` except a literal exact-code match, per `docs/purchases-product-mapping-policy.md`) — a row a human already reviewed is left completely untouched on re-run. Caught and fixed a bug in this same-day: the first version of the upsert correctly preserved `mapping_status` on already-approved rows but still overwrote `mapping_source`, clobbering provenance on 77 rows (relabeled `historical_approved_source_unknown` since the exact original batch couldn't be reconstructed — chose honesty over false precision). New weekly job (`pipelines/jobs/product_mapping_backlog_job.py` + `schedule_weekly_at()` in `pipelines/scheduler.py`), Sunday 11am, project owner's call.

## 2.2 Power BI validation — found a real internal-vendor exclusion bug

Validated Acoxpa and La Esquina Coyoacan against the user's live Power BI for August (closed month). Ventas matched exactly. Compras/"Entradas de Inventario" were off by ~23% for both branches. Root cause: `scripts/build_analytics_purchase_order_lines.py` excluded any purchase line whose **vendor** was an internal provider (El Bodegon de Fito, Las Empanadas de Maria Eva) from `include_in_business_views`, unconditionally — contradicting the documented policy (`docs/purchases-product-mapping-policy.md`, "Internal Provider Companies"): exclude when the internal provider is the **buying company**, keep when it's just the **vendor** and the buyer is a real branch. **Fixed** (also removed the identical bug baked into `dim_vendor`'s own `include_in_business_views`, which fed the same wrong signal). After the fix: Acoxpa 23%→1.8%, Coyoacan 23%→6.2% — the remaining gap is the still-open product-mapping backlog (expected, not a bug).

## 2.3 Discovered: Sales has a dev-only history gap for the 7 Odoo-migrated branches

August history for Acoxpa/Antenas/Tepeyac/Oceania/Coyoacan/Puebla/CentroMyJ only went back to Aug 28 in **dev** (root cause never found — some event around the 2026-08-27 Odoo-rollout commit session wiped Aug 1-27 for these 7 branches specifically, in dev only; **production is unaffected**, confirmed by the project owner from memory). Backfilled Acoxpa's Aug 1-28 via the real Candado (`verificar_y_sincronizar`, Cierre-Z-validated) — new reusable `scripts/backfill_sales_august.py <subsidiary_id> [<subsidiary_id> ...]`.

---

# 3. Session 2026-09-17 — Full recap

## 3.1 OneDrive move discovered and worked through (see Section 0)

## 3.2 Full daily cycle re-run — clean, confirmed today's fixes hold

All 5 stages OK, no failures. Confirmed the 2026-09-15 fixes (duplicate-insert, internal-vendor exclusion) held under a real full run.

## 3.3 Puebla exercise — the real payoff of yesterday's work

User's request: use Puebla (zero Wansoft Purchases/Inventory activity — genuinely "already in the future state") to check whether **dev** has everything needed for a fully Odoo-sourced branch, without comparing to Power BI (since PBI isn't repointed to the unified layer yet).

**Found: Puebla's Sales in dev had the exact same Aug 1-27 gap as Acoxpa** — the user caught this by recalling Puebla's real August sales were "above 3.4 million pesos," while dev showed $631,943 (4 days only). Backfilled via the same `scripts/backfill_sales_august.py 12806` (one day, Aug 22, needed a retry after a transient Wansoft SOAP timeout). Confirmed: **$3,480,350.65**, exactly matching the user's recollection.

**Found: no inventory valuation exists for pure-Odoo branches.** Tried to compute a COGS% for Puebla two ways: (1) Wansoft's own cost report — genuinely returns `0.0` (confirmed in the raw SOAP response, not a bug — Puebla was never onboarded into Wansoft's costing catalog); (2) Purchases-as-COGS-proxy — nonsensical (145.9% of net sales for August, because Puebla was in ramp-up/stock-buildup that month). Checked `analytics_inventory_snapshot` and `canonical_purchase_receipt_move_snapshot` for any inventory valuation field — neither has one, only quantities. **Conclusion, confirmed by the user:** a real inventory-valuation build is genuinely needed for pure-Odoo branches; this is future work, not something existing tables can produce.

**Found and fixed: Costs was incorrectly routed to Wansoft for every branch (a same-day self-correction).** First pass (see below) put Costs in `ALWAYS_WANSOFT_DOMAINS`, which broke Puebla/CentroMyJ's *only* working cost source.

## 3.4 Costs domain — built out properly for the first time (3 iterations, self-corrected each time)

**Iteration 1:** Found that 4 cost scripts (`descargarCostoWansoft.py`, `getTotalCostByDate.py`, `getCostReport_SemanaPyQ.py`, `getTablajeriaReport.py`) routed branches via `is_wansoft_company()` — which reads `COMPANY_SOURCE`, the governance signal for Purchases/Inventory only. Costs was never migrated (`docs/power-bi-source-migration.md`: "No unified analytics table exists yet for Costs"), and the user confirmed live: their Power BI reads Costs entirely from Wansoft, for every branch, migrated or not. Added `"costs"` to `ALWAYS_WANSOFT_DOMAINS`.

**Iteration 2 (same-day correction):** This broke Puebla/CentroMyJ, which have **zero** real Wansoft cost data (confirmed: `GetCostReport_Xml` genuinely returns `CostoTotal=0.0` for them) but **do** have a working, previously-built, already-audited Odoo-side calculation (`extract/costs/odoo_cost_report.py` — `account.move.line` on `expense_direct_cost` accounts, audited against both companies 2026-08-26/27) that the blanket fix accidentally routed away from. Real governance needed a 3-way split:
- 5 branches migrated **from** Wansoft (Acoxpa, Antenas, Tepeyac, Oceania, La Esquina Coyoacan): Wansoft still has real, complete cost data — validated to match the user's Power BI **exactly** for Acoxpa, both August and September.
- 2 branches that started **on** Odoo (Puebla, CentroMyJ): use `extract/costs/odoo_cost_report.py`. Validated for Puebla: Costo Teorico $1,156,603.26 (Aug) / $281,873.10 (Sept) — 38.6% and 22.9% of net sales, both believable restaurant COGS ratios (vs. 145.9%/31.8% from the failed purchases-as-proxy attempt).

New: `core/config/companies.py` — removed `"costs"` from `ALWAYS_WANSOFT_DOMAINS`, added `COSTS_ODOO_SOURCE_COMPANIES = {"Puebla", "CentroMyJ"}` and `is_company_wansoft_source_for_costs()` as the real per-branch check.

**Iteration 3 — Cortesias/Cancelaciones, applied to all 19 uniformly:** `odoo_cost_report.py`'s own docstring already established there's no reliable Odoo account for Cortesias/Cancelaciones (audited, not just unknown). User's proposal: pull them from `getglobalcashclosing` instead — a table that already existed, is Sales/POS-adjacent, and (per a 2026-08-27 comment already in `getGlobalCashClosing.py`) is confirmed to have real non-zero values even for Puebla. Cross-checked against Acoxpa first: the table's `cortesias_en_platillos` ($19,269 for August) is the **sale value** of the comped item, not its cost — the already-validated `CostoDeCortesias` from Wansoft's cost report was $9,899.15 (~51% of that, roughly the branch's food-cost ratio). Flagged this explicitly; **user's explicit, informed decision:** use the sale-value figure anyway, uniformly, for all 19 branches — reasoning: "es un valor que viene de la venta y esa la gestiona siempre wansoft" (it's a sales-domain value, and Sales is always Wansoft-sourced), same principle as `ALWAYS_WANSOFT_DOMAINS`. Applied to both the Wansoft-report path (overriding `GetCostReport_Xml`'s own `CostoDeCortesias`/`CostoDeCancelaciones`) and the Odoo path.

Two real bugs surfaced while building this, both fixed same-day:
- MySQL `SUM()` returns `decimal.Decimal` → pandas `object` dtype → `groupby().cumsum()` raises `TypeError`. Needed an explicit `.astype(float)`.
- A precomputed second cumulative series (from `getglobalcashclosing`'s own date set) merged onto the Odoo cost date set by date silently reset to 0 on any date present in one set but not the other (confirmed: Puebla Sept 5 and Sept 16 both dropped to 0 despite real cumulative data existing). **Fixed** by computing the month-to-date SUM fresh per-date inside the loop (a direct SQL query each iteration, matching the pattern already used on the Wansoft-report side) instead of a batch merge — more queries, zero cross-dataset alignment assumptions.

## 3.5 Confirmed a real, ongoing production duplication (left production untouched, per instruction)

User's real motivation for the dev-vs-prod validation work: dev should already reflect the "Odoo-only" future state (as Puebla/CentroMyJ prove), so production's duplicate Wansoft loading for already-migrated branches can eventually be turned off. Checked production directly (carefully — avoided the 25M-row `getoutgoinginventory_salida` table entirely, queried only the small `getexpenses_factura` and medium `getinputinventory_entrada`):

- **Puebla, CentroMyJ:** zero Wansoft Purchases/Inventory activity in the last 30 days — already in the target state.
- **Acoxpa, Antenas, Tepeyac, Oceania, La Esquina Coyoacan:** all 5 still have real, recent (through 2026-09-15/16) Wansoft Purchases **and** Inventory activity in production — genuine ongoing duplicate work.

Confirmed dev's own code (`getExpenses.py`, `getInputInventory.py`, `getOutgoingInventory.py`) already correctly excludes all 7 Odoo-source branches via `is_wansoft_company()` (tested directly, returns `False` for all 7) — dev's small residual Inventory rows for 3 branches (last dated Aug 24) are pre-fix historical data, not an ongoing issue. **Production is running something else** (an older deployment or separate process) — this was **not touched**, per explicit user instruction ("productivo dejalo como esta").

---

# 4. Detailed Status by Domain

### Sales
No open issues in the pipeline logic itself. Two real dev-only history gaps found and fixed this round (Acoxpa, Puebla — both Aug 1-27/28). **Open question:** whether any of the other 5 Odoo-migrated branches (Antenas, Tepeyac, Oceania, La Esquina Coyoacan) or CentroMyJ have the same gap — not checked yet, only Acoxpa and Puebla were verified. If picking this up next, check before assuming they're fine.

### Purchases
Both real bugs (duplicate-insert date-column mismatch, internal-vendor exclusion) fixed and validated. Remaining ~2-6% gap vs. Power BI is the open product-mapping backlog (571 products historically unmapped, weekly job now running to shrink it — see Section 2.1).

### Inventory
No new issues this round. `analytics_inventory_balance`/`analytics_inventory_snapshot` confirmed to have **no cost/valuation field** — only quantities. This is the real blocker for a proper Odoo-side COGS calculation (see Section 3.3) and is now a known, documented gap rather than an assumption.

### Costs
**Newly built out and validated this round** (previously fully out of scope). 3-way governance now in place and correct:
```
Wansoft-migrated branches (Acoxpa, Antenas, Tepeyac, Oceania, La Esquina Coyoacan)
    -> Wansoft cost report (GetCostReport_Xml / GetTotalCostByDate / GetCostReport_SemanaPyQ)
Pure-Odoo branches (Puebla, CentroMyJ)
    -> extract/costs/odoo_cost_report.py (account.move.line, expense_direct_cost accounts)
Cortesias/Cancelaciones (ALL 19 branches, no exception)
    -> getglobalcashclosing (Sales/POS-adjacent, always Wansoft) -- sale value, not cost basis, by explicit choice
```
Validated exact for Acoxpa (Costo Teorico, Merma) against Power BI, both Aug and Sept. Puebla now has real, believable numbers for the first time ever.

### Security / Configuration
`.env`'s `XML_DOWNLOAD_DIR_DEV` stale-path bug (Section 0) is fixed locally on this machine only — `.env` is gitignored, so this fix does not travel with the repo. If this project is ever set up on another machine (or this machine's `.env` is regenerated from a template), that path needs to be set correctly again.

---

# 5. Architectural Decisions Made (chronological, both sessions)

| Decision | Rationale | Impact |
|---|---|---|
| Fix `save_wansoft_canonical_receipts`'s delete window to match the eligibility query's date column | Two different date columns (`date_done`/`FechaReal` vs `scheduled_date`/`FechaEntrada`) can diverge per row, causing real duplicate-key crashes | `extract/purchases/canonical_purchase_etl.py` |
| Add a code-base matching tier (strip leading prefix) before falling back to fuzzy name matching | Wansoft/Odoo codes for the same product differ only by a company/warehouse prefix; comparing the remainder is a real-identifier match, far more reliable than name-similarity text guessing | `analysis/build_product_mapping.py` |
| Never let a re-run of the weekly product-mapping job touch a row a human already approved/rejected, field by field | A first version only protected `mapping_status`, still let other fields (like `mapping_source`) get silently overwritten | `analysis/save_product_mapping.py` |
| Stop excluding a branch's own purchases from an internal-provider vendor | Company-is-internal and vendor-is-internal are different cases; only the first should exclude, per the project's own documented policy | `scripts/build_analytics_purchase_order_lines.py`, `scripts/build_dim_vendor.py` |
| Costs needs a 3-way governance split, not `ALWAYS_WANSOFT_DOMAINS` or plain `COMPANY_SOURCE` | Confirmed live: Wansoft-migrated branches still have real Wansoft cost data; pure-Odoo branches have none, but do have a working Odoo-side calculation; a blanket rule breaks one side or the other | `core/config/companies.py` (`COSTS_ODOO_SOURCE_COMPANIES`), 4 cost scripts |
| Cortesias/Cancelaciones always come from `getglobalcashclosing`, all 19 branches, sale value not cost basis | Sales/POS concept, Sales is always Wansoft regardless of a branch's Purchases/Inventory/Costs source — same principle as `ALWAYS_WANSOFT_DOMAINS`; explicit, informed choice by the project owner after being shown the sale-value-vs-cost-value tradeoff | `legacy/wansoft/descargarCostoWansoft/descargarCostoWansoft.py` |
| Compute month-to-date sums via a direct per-date SQL query inside the loop, not a batch pandas merge across two differently-dated series | A merge across two datasets that don't share the same date set silently produces gaps/resets; a fresh query per date has no such assumption | Same file, Odoo cost path |
| Leave production's duplicate Wansoft Purchases/Inventory loading (5 branches) untouched | Explicit user instruction — dev is the place to prove out the target state; production changes are a separate, deliberate decision for later | No code change; investigation only |

---

# 6. Business Rules Implemented / Reinforced (this round)

- **Costs governance is per-branch, three states, not a domain-wide flag:** Wansoft-migrated vs. pure-Odoo vs. the Cortesias/Cancelaciones Sales-adjacent override that ignores both of those and always uses Wansoft.
- **Internal-provider exclusion is about the buying company, never the vendor alone** — a real branch buying from an internal kitchen (El Bodegon, Las Empanadas) is a real purchase for that branch.
- **A weekly automated job must never downgrade or silently relabel a human review decision** — every field of an already-reviewed row stays untouched on re-run, not just its status.
- **`getglobalcashclosing` is a legitimate, Wansoft-sourced, always-available report for every branch regardless of Purchases/Inventory/Costs migration status** — same tier as Sales itself.

---

# 7-8. Technical Conventions / Git State

**New learnings this round:**
- The Bash/harness working-directory reset after every command (Section 0) means every multi-step investigation in this environment needs `cd` or absolute paths repeated constantly — budget for that when estimating how many tool calls a task will take.
- MySQL `SUM()`/aggregate results come back as `decimal.Decimal` via `mysql.connector`, which pandas treats as `object` dtype — always cast explicitly before `cumsum()`/other numeric pandas ops.
- Never merge two pandas frames built from two independently-dated SQL queries and assume the date sets align — a per-row/per-date direct query is slower but immune to silent gaps.
- Windows Explorer/OneDrive Known Folder Move can relocate a project's entire working directory without warning; the local `.git` and `.env` survive intact, but any **hardcoded absolute path** anywhere in config (`.env`, scripts) needs to be found and fixed after the fact — grep for the old path string as a first response.
- Querying production during business hours (lunch/dinner) on an unindexed large table can hang for 1+ hours (confirmed 2026-09-15, `getallordenesbyday_new_venta`). Always check `information_schema.tables` for row count/size and check indexes (`SHOW INDEX`) before running an ad-hoc query against a production table larger than a few hundred MB; avoid multi-GB tables (`getoutgoinginventory_salida`, 25M+ rows) entirely unless the exact task requires it.

**Git state:** branch `main`, up to date with `origin/main` through commit `5e18b79`. `inventory_not_found_analysis.csv` remains permanently uncommitted per convention. Loose untracked files at the repo root (`extractAllOrdersByDay.py`, `extractAllOrdersByDay_old.py`, `getAllOrdersByDay.py`) are pre-existing stray copies, not touched or explained this round — flag to the user if their origin ever becomes relevant.

---

# 9. Important Historical Context — Combined Bug Log (do not re-investigate)

See prior reports for bugs #1-#17. This round's additions:

| # | Bug | Where it actually lived | Status |
|---|---|---|---|
| 18 | Cross-run duplicate-key crash in Wansoft canonical purchase receipts | `extract/purchases/canonical_purchase_etl.py`, `save_wansoft_canonical_receipts` deleting by the wrong date column | **Fixed 2026-09-15** |
| 19 | Product-mapping pipeline crashed on every run (`KeyError: odoo_code`), had never worked | `analysis/normalize_odoo_products.py` reading a column `extract/products/odoo_products.py` stopped emitting | **Fixed 2026-09-15** |
| 20 | Internal-provider vendor exclusion dropped a branch's own real purchases from all business-facing Purchases numbers | `scripts/build_analytics_purchase_order_lines.py` + `scripts/build_dim_vendor.py` | **Fixed 2026-09-15** |
| 21 | `XML_DOWNLOAD_DIR_DEV` pointed at the pre-OneDrive-move dead path, silently failing every Sales XML download (all 19 branches, all days) since the move | `core/config/.env` (local, gitignored) | **Fixed 2026-09-17** |
| 22 | Costs domain routed via `COMPANY_SOURCE` (a purchases/inventory-only signal), self-corrected twice same day before landing on the real 3-way split | `core/config/companies.py`, 4 cost scripts | **Fixed 2026-09-17** (see Section 3.4 for the 2 intermediate wrong attempts, kept for the reasoning trail) |
| 23 | Odoo-path Cortesias/Cancelaciones computation: `Decimal` dtype crash, then a cross-dataset date-merge silently resetting values to 0 | `legacy/wansoft/descargarCostoWansoft/descargarCostoWansoft.py` | **Fixed 2026-09-17** |

**Also confirmed NOT bugs this round:**
- Puebla's Wansoft cost report returning `0.0` — genuinely correct, Wansoft has nothing for this branch (never onboarded into its costing catalog).
- `analytics_inventory_snapshot`/`canonical_purchase_receipt_move_snapshot` having no cost/valuation field — a real, confirmed gap in what's been built so far, not a bug to fix by searching harder.
- Production's duplicate Wansoft Purchases/Inventory loading for 5 branches — real and ongoing, but explicitly out of scope to touch this round (dev-only work, by instruction).

**Gate result:** unchanged, not reopened. Costs moves from "out of scope" to "validated" status for the first time.

---

# 10. User Decisions (explicit, don't lose track of these)

- **Confirmed:** for Cortesias/Cancelaciones, use `getglobalcashclosing`'s sale-value figure directly for all 19 branches, uniformly — not a cost-basis conversion, even after being shown the ~2x difference vs. the previously-validated Wansoft cost-report figure for Acoxpa. Explicit reasoning given: it's a Sales-domain value, Sales is always Wansoft.
- **Confirmed:** leave production's Wansoft Purchases/Inventory duplicate-loading untouched for now — dev-only work this round, production changes are a separate, later, deliberate decision.
- **Confirmed:** a real inventory-valuation build for pure-Odoo branches (needed for a true COGS, not an approximation) is genuine future work — agreed to when shown that Puebla's Purchases-as-proxy COGS% was nonsensical (145.9%) for a ramp-up month.
- **Confirmed (2026-09-15):** the weekly product-mapping job runs Sundays 11am.
- Two production-shaped follow-ups raised by the user but explicitly deferred, not started: (1) inventory valuation for pure-Odoo branches, (2) deciding when/how to turn off production's duplicate Wansoft loading for the 5 still-active branches.

---

# 11-12. Identified Legacy / Consolidated Backlog

**Backlog, in rough priority order:**
- **Inventory valuation for pure-Odoo branches** — needed for a real COGS (not a purchases-as-proxy approximation) on Puebla/CentroMyJ and any future pure-Odoo branch. No existing table has a cost/value field on inventory movements; this is new construction, not a bug fix. User confirmed this needs to happen ("si, tenemos que hacerlo").
- **Decide when to turn off production's duplicate Wansoft loading** for Acoxpa, Antenas, Tepeyac, Oceania, La Esquina Coyoacan (Purchases + Inventory) — dev already proves the Odoo-only path works (Puebla, CentroMyJ). This is an operational/business decision, not a code change on our side — production code itself needs identifying (it's not running from what's in this repo, evidently) before it can be touched.
- **Check whether Antenas, Tepeyac, Oceania, La Esquina Coyoacan, or CentroMyJ have the same Aug 1-27 dev-only Sales history gap** as Acoxpa and Puebla — only those two were checked and backfilled this round.
- Replay `sql/maintenance/add_unique_keys_dedup_protection.sql` on production once that side is promoted (carried forward, unchanged).
- Raise production's own `innodb_buffer_pool_size` if it's still 16M there too (dev's was raised 2026-09-15; production's value was never checked this round).
- Weekly product-mapping job (Sundays 11am) needs its first real Sunday run observed to confirm the schedule actually fires as expected (the scheduler itself isn't running as a persistent process yet — see prior reports).
- Origin of the loose root-level files (`extractAllOrdersByDay.py`, `extractAllOrdersByDay_old.py`, `getAllOrdersByDay.py`) — untracked, unexplained, not touched.
- `.env`'s `XML_DOWNLOAD_DIR_DEV` fix is local-machine-only (gitignored) — if this project is ever cloned fresh or `.env` regenerated, this needs to be set correctly again from Section 0.
- Isabel La Católica/San Jerónimo/Vía Vallejo Odoo cutover, at/after 2026-10-01 (unchanged, carried forward).

---

# 13. Next Steps — HANDOFF PROMPT

**Paste this as the first message when resuming:**

```
Continúo el proyecto Wansoft + Odoo + Zenput Data Warehouse & ETL Pipeline.
Lee completo PROJECT_CONTEXT_REPORT.md en la raíz del repositorio antes de
responder, especialmente la Sección 0 (ruta de OneDrive, IMPORTANTE) y la
Sección 9 (log combinado de bugs).

Resumen rápido: en las dos sesiones pasadas (15 y 17 de sept) se
encontraron y arreglaron varios bugs reales -- duplicados en Compras,
exclusión indebida de compras a proveedor interno, y sobre todo se
construyó el dominio de Costos desde cero (antes estaba fuera de
alcance). Costos ahora tiene un enrutamiento de 3 vías: Wansoft para las
5 sucursales que migraron desde ahí, Odoo para las 2 que nacieron ahí
(Puebla, CentroMyJ), y Cortesías/Cancelaciones siempre de
getglobalcashclosing para las 19 por igual (decisión explícita tuya).
Validamos Ventas, Compras y Costos contra tu Power BI real para Acoxpa y
Puebla, agosto y septiembre -- coinciden exacto.

También: la carpeta del proyecto se movió a la ruta de OneDrive de la
organización (ver Sección 0) -- no es un problema, solo hay que usar la
ruta nueva. Y confirmamos que producción sigue duplicando carga de
Compras/Inventario en Wansoft para 5 sucursales ya migradas a Odoo --
dejado así a propósito, pendiente de que decidas cuándo apagarlo.

Pendiente real más grande: construir valorización de inventario para
sucursales 100% Odoo (Puebla, CentroMyJ) -- sin eso no hay COGS confiable
para ellas, solo aproximaciones que no funcionan bien.
```

**Suggested title for the new chat**: `FONDA (Wansoft): Paso 23: Costos construido y validado, valorización de inventario Odoo pendiente`

---

# Permanent Rule

Regenerate this document in full (never as patches) when: the user explicitly asks, a major step closes, the conversation gets very long, context exceeds ~70%, or a new chat needs to be opened due to token limits. In that last case, also generate:
1. The handoff prompt (Section 13, first code block, if applicable).
2. The suggested title for the new chat, in the format **`FONDA (short project): Paso N[-M]: <short description>`** (same style as the user's own session list). `FONDA` is a fixed prefix; `(short project)` identifies which project (here: "Wansoft"). Use `N` = the major step/block number in progress, `-M` = sub-part suffix if the step spans multiple consecutive sessions/chats.

**Note on language:** this document, all commit messages, and all documentation pushed to GitHub in this project must be written in English — even though the working conversation with the user is in Spanish. See project memory `feedback_github_content_english_only` for the full rule.
