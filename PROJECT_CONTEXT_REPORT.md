# PROJECT_CONTEXT_REPORT.md

Master continuity document. Generated/updated automatically at the close of major steps, on explicit request ("Generate project context report"), when the conversation gets very long, when consumed context exceeds ~70%, or when a new chat needs to be opened due to token limits. Always regenerated in full, never as an incremental patch.

Last generated: 2026-08-31, end of day. **The final acceptance gate (Costs/Purchases/Inventory, Odoo branches) is formally ACCEPTED**, and the four backlog items opened at gate close (Receipts filter, Costs date offset, Inventory auto-correction design, Puebla rollout) are all resolved — three fixed/activated, one resolved as a deliberate "stay manual" decision. Nothing gate- or backlog-blocking remains open.

---

# 1. Executive Summary

**Overall project goal:** build a unified analytical layer in MySQL that integrates Wansoft, Odoo, and Zenput, hiding from the end user which system originates each piece of data.

**Current state:** Inventory, Costs, and Purchases are functionally complete and **formally accepted** for the 7 branches now active on Odoo (Antenas, La Esquina Coyoacán, CentroMyJ, Acoxpa, Tepeyac, Oceanía, and — activated today — Puebla). The acceptance gate (started 2026-08-27, accepted 2026-08-31) is closed, and the four backlog items opened at close are also resolved.

**Estimated progress:** 100% for the scope defined by the gate, plus its backlog. Nothing gate-blocking or backlog-blocking remains open. Any further work is new scope, not carryover.

**Current block:** none. All accumulated work (2026-08-27 gate session + 2026-08-31 session, including the backlog closeout) is committed and pushed to `main`.

## What was done this session (2026-08-31), in order:

**Part 1 — Bug in the Sales lock/reconciliation job (`extractAllOrdersByDay.py`):**
1. The user reported: the Sales lock, when it detects a mismatch against Wansoft's Z-closing and tries to correct it, rewrote MySQL using the XML already cached on disk (`asegurar_xml_disponible`) instead of requesting a new one — if that cached file was the source of the original mismatch, the "correction" fixed nothing.
2. Clarified: the comparison itself (STEP 2, against `GetGlobalCashClosing_Xml`) was already fresh via SOAP every day — the bug was only in the rewrite step. Fixed: on detecting a mismatch, it now forces a real re-download from Wansoft before `reescribir_desde_xml` (`legacy/wansoft/automaticos/extractAllOrdersByDay.py`, STEP 4).

**Part 2 — Design of the T+7/T+30 cutover checkpoint:**
3. The user raised a real production risk: branches with Purchases/Inventory split across both systems (Wansoft + Odoo) during the migration month can break monthly balances if there's no certainty about what's already in Odoo. Discussed: cutover at the start of the month (already the pattern in use), not trusting branches' word for it, and instead **verifying programmatically** a few days after deployment.
4. User decision: checkpoints at T+7 and T+30 after `operational_start_date`, each combination (branch, domain, checkpoint) validated **exactly once** (not daily), comparing MySQL (dev) against a fresh, independent read of Odoo. On a Purchases FAIL, the corresponding pipeline is automatically triggered as a correction. Scheduled at 3pm (outside the daily jobs' schedule).
5. Built: `scripts/validate_odoo_cutover.py` (`odoo_cutover_validation_log` table, UNIQUE per branch+domain+checkpoint), `pipelines/jobs/odoo_cutover_validation_job.py`, and `schedule_daily_at()` added to `pipelines/scheduler.py` (no fixed-time scheduling existed before, only intervals).

**Part 3 — Real bug #5 (numbering continues from the gate): canceled orders inflating the real canonical ETL:**
6. First checkpoint run: Tepeyac Purchases failed with a 14.5% difference, and the "correction" (re-running `run_purchases_pipeline`) didn't fix it — it ran, but the number didn't change substantially.
7. Diagnosis: `canonical_purchase_order_snapshot`/`_line_snapshot` (the real production canonical table, not the gate's diagnostic module) **never filtered `state IN ('cancel','draft')`** — exactly Bug #2 from the gate session, fixed back then only in `odoo_purchase_category_totals.py` (a diagnostic tool) but never propagated to the real canonical ETL (`extract/purchases/canonical_purchase_etl.py`, function `filter_final_odoo_enabled`). Confirmed with counts: 54 canceled Tepeyac orders totaling $693,357.59 explained practically the whole gap.
8. Fixed: `filter_final_odoo_enabled(df, exclude_cancelled_draft=True)` for Orders and Lines (Receipts and receipt moves also have `cancel`/`draft` rows, flagged but not fixed today — not what was being measured). Reloaded via `test_canonical_purchase_odoo_etl`, validated with `validate_purchases_canonical_layer` (8/8 PASS). After the fix, Tepeyac went from 14.5% to 1.46% difference, and all 6 branches passed Purchases (T+7 and T+30 checkpoints).

**Part 4 — Incident: an unrelated process killed by mistake:**
9. While checking for orphaned processes after stopping the checkpoint run (which looked stuck — it was actually running real corrections for the first time, ~1h each), a process named `ejecutar_pruebas.py` was killed without verifying whose it was. It turned out to belong to another of the user's chats. Acknowledged immediately as a mistake; the user stopped that other session and we continued.

**Part 5 — Per-branch scope audit (explicit user request):**
10. The user asked to check that no script was left implemented for only one branch (concrete concern: "running into production and finding out parts of the project only work for Antenas").
11. Found and confirmed real: `scripts/build_dim_company_analytical.py` had `MIGRATED_FROM_WANSOFT_COMPANIES = {"Antenas", "La Esquina Coyoacán"}` — never updated when Acoxpa/Tepeyac/Oceanía migrated (2026-08-26/27). Real effect verified in the table: those 3 branches showed up with `purchases_source_system='wansoft'` and `rollout_type=NULL`, **as if they had never migrated to Odoo**. Fixed (added the 3 to the set), table rebuilt, validated with `validate_dim_company_analytical` (10/10 PASS).
12. Reviewed and confirmed clean: the extraction layer (`extract/purchases/*`, `extract/inventory/*`) and source governance (`core/config/companies.py`) — fully generic, driven by `COMPANY_SOURCE`/`odoo_company_migration_policy`, nothing hardcoded to a single branch. The only script genuinely coupled to a single branch: `scripts/reconcile_purchases_dev_vs_odoo.py` (manual diagnostic from the gate session, already superseded by `validate_odoo_cutover.py`, low risk since it's not part of any pipeline).

**Part 6 — Inventory: automation gap and real bug #6:**
13. The checkpoint showed Inventory FAILing for all 6 branches. Diagnosis: `analytics_inventory_snapshot`/`analytics_inventory_balance` (Acoxpa) were **11 days stale** — because neither `run_inventory_pipeline.py` nor anything else was scheduled to run on its own (confirmed: neither Purchases nor Inventory had anything in the scheduler).
14. Investigated why `run_inventory_pipeline.py` never rebuilds those two tables: its docstring explicitly says dictionary promotion is kept out of the automation because it requires human review. But it was confirmed that `build_analytics_inventory_snapshot.py`/`build_analytics_inventory_balance.py` **promote nothing** — they only read the already-approved dictionary and recompute. The pipeline was stopping one step short of what was actually needed.
15. User decision: the Inventory checkpoint **must not auto-correct** (unlike Purchases) — alert only (`correction_status='manual_review_required'`), since the real correction mechanism needs a redesign, not just repeating the pipeline. Implemented in `validate_odoo_cutover.py` (`AUTO_CORRECTABLE_DOMAINS = {"purchases"}`).
16. Added steps 06-07 (`build_analytics_inventory_snapshot`, `build_analytics_inventory_balance`) to `run_inventory_pipeline.py`, and scheduled `pipelines/jobs/inventory_pipeline_job.py` at 1pm (before the 3pm checkpoint) in the scheduler.
17. Running the extended pipeline for the first time (8/8 steps SUCCESS, ~3.2 min), the Inventory checkpoint **still failed** across all 6 branches, now with dev consistently higher than live Odoo (2.5x-7x) — no longer staleness, a methodology problem.
18. Real bug #6 found: `classify_location()` in `build_analytics_inventory_snapshot.py` already computed `is_virtual_location`/`is_partner_location`, but `build_row()` never consulted them when deciding `include_in_business_views` — Odoo virtual locations ("Virtual Locations/Inventory adjustment", "Virtual Locations/Production", double-entry counterparts, not real physical stock) were being summed as if they were real stock on hand. Confirmed on Acoxpa: virtual-location rows alone totaled 1,893.92 against 596.71 from real internal locations.
19. Fixed: exclude `is_virtual_location`/`is_partner_location` from `include_in_business_views`. Both tables rebuilt. Result: **20/20 checkpoints PASS** (Purchases + Inventory, T+7 and T+30, all 6 branches), several with an exact match (diff=0.0000). `validate_analytics_inventory_balance` confirmed 9/9 PASS, no regression.

**Part 7 — Gate backlog closeout, all four items:**
20. **Receipts canceled/draft filter:** applied the same `exclude_cancelled_draft` fix already used for Purchase Orders/Lines to `canonical_purchase_receipt_snapshot`/`_receipt_move_snapshot`. Confirmed first that no downstream consumer currently aggregates money/quantity from these two tables (only `build_dim_vendor.py` reads them, state-agnostic) — so this had zero measurable impact today, purely consistency/prevention. Reloaded, validated (8/8 PASS).
21. **Costs date offset:** the Odoo path for `costeomensual_semanapyq` (both `getCostReport_SemanaPyQ.py`'s daily block and `scripts/backfill_odoo_cost.py`) stored `created_at = real_date`, while the Wansoft path has always stored `created_at = real_date + 1 day`. Aligned the Odoo path to the older, already-in-production Wansoft convention (not the other way — too much else could depend on it) in both scripts. Backfilled the 613 already-loaded Odoo rows affected via one bulk `UPDATE` (verified safe: no unique constraint on the table, only PK on `id`).
22. Backfilling surfaced a **new real bug (#7)**: `backfill_odoo_cost.py` was pulling Odoo cost data from each company's *earliest posted line in Odoo*, with no floor at `operational_start_date` — the same no-overlap governance already enforced in the Purchases canonical layer was missing here. This had created 4 real Wansoft/Odoo overlaps in `costeomensual_semanapyq` (Antenas 2026-04-27, Acoxpa/Oceanía/Tepeyac 2026-07-27), only visible once the date-offset fix made both rows land on the same day. User decision: Odoo wins for existing overlaps (consistent with the project's established governance). Deleted the 4 stale Wansoft rows; added a governance clamp (`get_operational_start_date`) to `backfill_odoo_cost.py` so it can't happen again.
23. **Puebla rollout activation:** found Puebla was already effectively live in canonical/analytics tables (250 purchase orders as `final_odoo_enabled`, 36 inventory rows) *despite* `odoo_company_migration_policy.is_active = 0` — without an active policy row, the ETL was silently falling through to a generic env-fallback start date instead of a governed one. Confirmed first (0 rows in `getinputinventory_entrada`/`getOutgoingInventory_Salida` for Puebla, ever) that it's a pure `new_odoo_branch`, same pattern as CentroMyJ, no Wansoft history to protect. Formalized: `is_active` 0→1, `include_odoo_history` 0→1 (was inconsistent with CentroMyJ's row and unused by the actual filter, fixed for consistency), `operational_start_date` kept at the value already governing production (2026-06-10, not the original seed's 2026-07-22 — same "keep what's already active" policy used for Acoxpa/Tepeyac/Oceanía). `ROLLOUT_COMPANY_EXPECTATIONS` activated in the validator. Re-ran governance test, Odoo ETL, canonical ETL, full validation (8/8 PASS).
24. **Inventory auto-correction design:** discussed a 3-tier design (auto-correct staleness / classify mapping-gap vs unexplained / alert). User pushed back with a key constraint: mapping an unmapped Odoo product to a Wansoft code can cross into other areas' catalogs and isn't retroactive — so it's inherently a periodic human review, not something to automate further, and the user considers current impact on Sales/Purchases reporting low since catalogs are "mostly correct." Resolution: **keep the checkpoint alert-only for Inventory, no new automation.** Only concrete change: removed `--skip-diagnostics` from the scheduled 1pm job so the `not_found` backlog reports stay current for whenever that periodic review happens, instead of only updating on a manual full run (adds ~2s).

**Open risks (active, unresolved):** none carried over from the gate or its backlog. Anything found from here is new scope.

**Pending relevant decisions:** none carried over. The user reviews the Inventory `not_found` backlog periodically, at their own pace, and coordinates with other areas as needed — that's an ongoing operational rhythm now, not a pending decision.

---

# 2. Functional Description of the Project

**What we're building:** a data warehouse in MySQL that pulls together Sales, Purchases, and Inventory data for Grupo Fonda Argentina, regardless of whether each branch runs on Wansoft or Odoo.

**Migration direction confirmed by the project owner:** the end goal is for **only Sales** to remain permanently on Wansoft; Purchases, Inventory, and Costs migrate branch by branch to Odoo.

---

# 3. Current Architecture

**Source systems:** Wansoft (SOAP/WSDL), Odoo (XML-RPC, read-only), Zenput (REST API).

**Source governance (`core/config/companies.py`):** `COMPANY_SOURCE` decides Purchases/Inventory per branch (authoritative). `odoo_company_migration_policy` (MySQL table, `is_active` + `operational_start_date`) decides whether the rollout is actually activated yet, and since when. Sales is always Wansoft, no exceptions.

**Branches currently active on Odoo (Purchases + Inventory):** Antenas, La Esquina Coyoacán, CentroMyJ, Acoxpa, Tepeyac, Oceanía, and Puebla (activated 2026-08-31, `new_odoo_branch` pattern — no Wansoft purchase/inventory history ever existed for it).

**Cutover checkpoint (new, this session):**
```
odoo_company_migration_policy.operational_start_date  -> reference date
T+7 / T+30 after that date                             -> triggers validation (once each)
Purchases: canonical_purchase_order_snapshot (dev) vs live purchase.order (Odoo, state not in cancel/draft)
Inventory: analytics_inventory_balance (dev) vs live stock.quant (Odoo, internal locations, mapped products only)
Purchases FAIL -> self-corrects (re-runs run_purchases_pipeline)
Inventory FAIL -> alert only (manual_review_required), does not self-correct
```
Script: `scripts/validate_odoo_cutover.py`. Log: `odoo_cutover_validation_log` table. Scheduled at 3pm.

**Inventory pipeline, now rebuilding analytics tables (this session):**
```
01-02 scope classification/refinement -> 03 Odoo inventory ETL -> 04-05 dictionary lookup/apply
06 build_analytics_inventory_snapshot (NEW) -> 07 build_analytics_inventory_balance (NEW) -> 08 validate_inventory_outputs
```
Scheduled at 1pm (before the cutover checkpoint). Promotion of new mappings (`test_promote_inventory_not_found_*`) stays outside the automated pipeline, on purpose.

**Costs architecture (unchanged this session, see gate session commits):**
```
account.move.line (Odoo, expense_direct_cost, out_invoice)          -> CostoTotal, CostoDeProductosVendidos
account.move.line (Odoo, expense_direct_cost, any move_type)        -> CostoDeMerma (account "Mermas y Desperdicios")
GetGlobalCashClosing_Xml (Wansoft, all branches)                     -> Cortesias, Cancelaciones, Anulaciones, Descuentos
GetCostReport_Xml (Wansoft, Wansoft-only branches)                   -> cost-weighted CostoDeCortesías/Cancelaciones
```

---

# 4. Detailed Status by Domain

### Sales
- Lock/reconciliation job (`extractAllOrdersByDay.py`) fixed this session: forces a real re-download before correcting, instead of reusing the cached XML that might have caused the mismatch in the first place.

### Purchases
- `canonical_purchase_order_snapshot`/`_line_snapshot`/`_receipt_snapshot`/`_receipt_move_snapshot` all now exclude `cancel`/`draft` (real bug, affected all 7 branches for Orders/Lines; Receipts/Receipt Moves fixed preventively, no measured current impact). Validated 8/8 PASS.
- Cutover checkpoint with auto-correction active. Validated 20/20 PASS (Inventory included).
- Puebla activated (`new_odoo_branch`, no Wansoft history) — `is_active=1`, `ROLLOUT_COMPANY_EXPECTATIONS` active, validated 8/8 PASS.

### Inventory
- `analytics_inventory_snapshot`/`analytics_inventory_balance` now exclude virtual/partner locations (real bug fixed this session). Both tables rebuild daily via the scheduler (1pm), including the `not_found` backlog diagnostics, something that didn't exist before.
- Cutover checkpoint in alert-only mode (does not auto-correct) — deliberate, permanent decision: mapping new products can cross into other areas' catalogs and isn't retroactive, so it stays a periodic manual review by the project owner.

### Costs
- `costeomensual_semanapyq`'s Odoo path (`getCostReport_SemanaPyQ.py`, `backfill_odoo_cost.py`) now stores `created_at` with the same `+1 day` offset as the Wansoft path. `backfill_odoo_cost.py` also gained a governance clamp at `operational_start_date` (was pulling from Odoo's earliest posted line unconditionally).

### Configuration / Governance
- `scripts/build_dim_company_analytical.py`: `MIGRATED_FROM_WANSOFT_COMPANIES` fixed to include Acoxpa/Tepeyac/Oceanía (real bug fixed this session). `dim_company_analytical` table rebuilt and validated 10/10 PASS.
- `odoo_company_migration_policy`: Puebla activated (see Purchases above).

*(Remaining domains unchanged this session — see the previous report in commit history for full Zenput/Wansoft/Odoo/Analytics detail if needed.)*

---

# 5. Architectural Decisions Made (chronological, this session)

| Decision | Rationale | Impact |
|---|---|---|
| Sales lock forces re-download when correcting, doesn't reuse cached XML | The cached file could be the source of the mismatch it was trying to fix | `extractAllOrdersByDay.py` |
| T+7/T+30 checkpoint, once per combination (branch, domain, checkpoint) | Avoids unnecessary daily re-checks; gives Odoo time to settle (same lag pattern already confirmed in the gate for Costs) | `validate_odoo_cutover.py`, `odoo_cutover_validation_log` table |
| Purchases: FAIL triggers auto-correction (re-run `run_purchases_pipeline`) | Idempotent, already-validated pipeline, safe to re-run | Same module |
| Inventory: FAIL alerts only, does NOT auto-correct | The real correction mechanism requires rebuilding analytics tables the pipeline wasn't touching — a half-fix would have hidden the real problem | Same module, `AUTO_CORRECTABLE_DOMAINS` |
| `filter_final_odoo_enabled` excludes `state IN ('cancel','draft')` for Purchase Orders/Lines | Same bug as the gate (inflated by canceled orders), never propagated to the real canonical ETL | `extract/purchases/canonical_purchase_etl.py` |
| `MIGRATED_FROM_WANSOFT_COMPANIES` includes Acoxpa/Tepeyac/Oceanía | Never updated after their migration (Aug 26-27); the table showed them as 100% Wansoft | `scripts/build_dim_company_analytical.py` |
| `build_row()` excludes `is_virtual_location`/`is_partner_location` locations from `include_in_business_views` | Those flags were already computed but never used; virtual locations (adjustments, production) were counted as real physical stock | `scripts/build_analytics_inventory_snapshot.py` |
| `run_inventory_pipeline.py` gains steps 06-07 (build snapshot/balance) | They don't promote the dictionary (verified); the pipeline was stopping one step short for no real reason | Same module |
| Inventory pipeline scheduled at 1pm, cutover checkpoint at 3pm | Neither pipeline (Purchases/Inventory) had anything scheduled — the root cause of the 11-day staleness found today | `pipelines/scheduler.py`, `schedule_daily_at()` (new) |
| Receipts/Receipt Moves also exclude `cancel`/`draft` | Consistency with the Orders/Lines fix; preventive, no current downstream consumer measured | `extract/purchases/canonical_purchase_etl.py` |
| Odoo path of `costeomensual_semanapyq` aligned to Wansoft's `created_at = date+1` convention, not the reverse | The Wansoft convention is older and already in production; too much could depend on it to change it instead | `getCostReport_SemanaPyQ.py`, `scripts/backfill_odoo_cost.py` |
| `backfill_odoo_cost.py` clamps its earliest backfill date at `operational_start_date` | Was pulling from Odoo's earliest posted line unconditionally, creating real Wansoft/Odoo overlap once dates aligned | Same module, `get_operational_start_date()` (new) |
| Puebla activated as `new_odoo_branch`, `operational_start_date` kept at the value already governing production (not the original seed) | Confirmed zero Wansoft purchase/inventory history ever existed for Puebla; same "don't overwrite already-active governance" policy used for Acoxpa/Tepeyac/Oceanía | `odoo_company_migration_policy`, `scripts/validate_purchases_canonical_layer.py` |
| Inventory checkpoint stays alert-only, permanently — no auto-correction mechanism built | Mapping decisions can cross into other areas' catalogs and aren't retroactive; the project owner reviews the backlog periodically instead | User decision, no code change beyond keeping diagnostics fresh in the daily job |

---

# 6. Business Rules Implemented (new this session)

- **Cutover checkpoint:** per newly migrated branch, T+7 and T+30 days after `operational_start_date`, a one-time comparison against live Odoo. Purchases self-corrects, Inventory alerts only.
- **Final Purchases (Odoo):** always exclude `state IN ('cancel','draft')`, both in diagnostics and in the real canonical ETL.
- **Final Inventory (Odoo):** always exclude virtual/partner locations (`is_virtual_location`/`is_partner_location`) — only count stock in real internal locations.
- **Automation vs. manual review (Inventory):** rebuilding `analytics_inventory_snapshot`/`analytics_inventory_balance` with the already-approved dictionary is safe to automate (promotes nothing); promoting new mappings stays manual, no exceptions.

---

# 7-8. Technical Conventions / Git State

**New learnings this session:**
- The pipeline scripts (`run_purchases_pipeline.py`, `run_inventory_pipeline.py`, and their individual steps) print an emoji on completion (`DONE ✅`). When invoked as a subprocess with captured output, without forcing `PYTHONIOENCODING=utf-8`, they crash with `UnicodeEncodeError` on Windows (cp1252) **after** the real work already finished — the step gets reported as FAILED even though it worked. Any new subprocess call to these scripts must pass `env={"PYTHONIOENCODING": "utf-8", **os.environ}`.
- A bug "fixed" in a diagnostic/gate script isn't fixed in production until it's verified in the real canonical ETL — this happened twice this session (canceled orders in Purchases, virtual locations in Inventory) with bugs already believed resolved since the gate.
- Before killing a process that looks orphaned, verify which command/file it actually is — don't assume it's yours just because it coincides in time.

**Git state:** branch `main`, up to date with `origin/main`. Both the gate session (2026-08-27) and this session (2026-08-31, including the full backlog closeout) are committed and pushed: `e7366f0`, `0974f97`, `e60dbf9` (Spanish commit messages, a one-time regression from the English-only convention, left as-is rather than rewriting already-pushed history — see project memory `feedback_github_content_english_only`), `6756fc8`, `d65c5bb`, `a7d3e27`, `6536baf`, `62ac106`. Files included across the session:

*From the gate session (2026-08-27):*
- `extract/costs/odoo_cost_report.py` — Merma fix + account audit.
- `extract/purchases/odoo_purchase_category_totals.py` — new (Purchases-by-account diagnostic).
- `legacy/wansoft/automaticos/getCostReport_SemanaPyQ.py` — clarifying comment.
- `legacy/wansoft/descargarCostoWansoft/getGlobalCashClosing.py` — reactivated.
- `legacy/wansoft/descargarCostoWansoft/descargarCostoWansoft.py` — reactivated + Odoo block.

*From this session (2026-08-31):*
- `legacy/wansoft/automaticos/extractAllOrdersByDay.py` — lock fix (forced re-download when correcting).
- `scripts/validate_odoo_cutover.py` — new, T+7/T+30 checkpoint.
- `pipelines/jobs/odoo_cutover_validation_job.py` — new.
- `pipelines/jobs/inventory_pipeline_job.py` — new.
- `pipelines/scheduler.py` — `schedule_daily_at()` + two new scheduled jobs.
- `extract/purchases/canonical_purchase_etl.py` — canceled/draft fix.
- `scripts/build_dim_company_analytical.py` — missing migrated branches fix.
- `scripts/build_analytics_inventory_snapshot.py` — virtual locations fix.
- `scripts/run_inventory_pipeline.py` — steps 06-07 (build snapshot/balance) added.
- `PROJECT_CONTEXT_REPORT.md` — translated to English, gate acceptance recorded.
- `extract/purchases/canonical_purchase_etl.py` — Receipts/Receipt Moves canceled/draft fix (second edit).
- `legacy/wansoft/automaticos/getCostReport_SemanaPyQ.py` — date offset fix (Odoo path).
- `scripts/backfill_odoo_cost.py` — date offset fix + `operational_start_date` governance clamp.
- `scripts/validate_purchases_canonical_layer.py` — Puebla rollout activated.
- `sql/seeds/seed_odoo_company_migration_policy.sql` — Puebla `is_active=1`, corrected `operational_start_date`.
- `pipelines/jobs/inventory_pipeline_job.py` — keep `not_found` backlog diagnostics in the daily run.

*Never committed (project convention):*
- `inventory_not_found_analysis.csv`.

---

# 9. Important Historical Context — Gate Summary (do not re-investigate)

See the previous report (commit `21078c8` or earlier) for the full gate session narrative (2026-08-27, bugs #1-#4). Combined summary table, including this session's bugs #5-#6:

| # | Bug | Where it actually lived | Fixed in |
|---|---|---|---|
| 1 | Merma in Odoo always $0 | Extra `out_invoice` filter in Costs | `extract/costs/odoo_cost_report.py` (2026-08-27) |
| 2 | Canceled orders inflating the Purchases diagnostic | `odoo_purchase_category_totals.py` (diagnostic) | Same module (2026-08-27) |
| 3 | "Sales-side" Cortesías/Cancelaciones confused with cost-weighted ones | Wrong column in `costeomensual_semanapyq` | Reverted, used `getglobalcashclosing.py` instead (2026-08-27) |
| 4 | `created_at+1` date offset, Wansoft vs Odoo | `getCostReport_SemanaPyQ.py` | Documented, not fixed (open risk) |
| 5 | Canceled orders inflating the **real** Purchases canonical ETL | `canonical_purchase_etl.py` (the #2 fix was never propagated) | `extract/purchases/canonical_purchase_etl.py` (2026-08-31) |
| 6 | Odoo virtual locations counted as real stock | `build_analytics_inventory_snapshot.py` | Same module (2026-08-31) |
| 7 | Odoo cost backfill ignored `operational_start_date`, created real Wansoft/Odoo overlap for 4 dates | `scripts/backfill_odoo_cost.py` | Same module (2026-08-31) |

**Gate result after today's fixes:** Purchases and Inventory, each compared independently against live Odoo, are at **20/20 PASS** for the 6 active branches (T+7 and T+30), several with an exact match. **The gate was formally accepted by the project owner on 2026-08-31.**

**Don't reopen without a new reason:** the Total Cost recognition lag in fresh weeks (original gate, bugs #1-#4) remains the same finding confirmed with 4 weeks of real data — not touched or re-investigated this session.

---

# 10. User Decisions (explicit, don't lose track of these)

- (All decisions from previous sessions still stand, see prior commits.)
- **New:** the Sales lock must force a real re-download when correcting, not trust the cached XML.
- **New:** cutover for mixed-source branches (Wansoft+Odoo) is validated with an automatic T+7/T+30 checkpoint, not by taking branches' word for when they actually closed out.
- **New:** Purchases self-corrects in the checkpoint; Inventory alerts only (explicit decision after understanding the real correction mechanism wasn't ready).
- **New:** build the missing Inventory automation ("let's go for it").
- **New:** commit and push all accumulated work.
- **New:** all commits and documentation pushed to GitHub must be in English, even though the working conversation is in Spanish (see project memory `feedback_github_content_english_only`).
- **New:** the final acceptance gate (Costs/Purchases/Inventory, Odoo branches) is formally **ACCEPTED** as of 2026-08-31.
- **New:** for the 4 real Wansoft/Odoo overlap dates found in `costeomensual_semanapyq`, Odoo wins (consistent with existing project governance) — the 4 stale Wansoft rows were deleted.
- **New:** Puebla rollout activated — it's a `new_odoo_branch` with no Wansoft purchase/inventory history.
- **New:** Inventory's checkpoint stays alert-only permanently, no auto-correction mechanism — mapping decisions cross into other areas and aren't retroactive; the project owner reviews the backlog periodically and coordinates with those areas directly.

---

# 11-12. Identified Legacy / Consolidated Backlog

**Backlog:** empty — all four items opened at gate close (2026-08-27/31) were resolved the same day (see Part 7). The only unresolved item from earlier sessions: chaining legacy scripts into `pipelines/scheduler.py` (deferred, no urgency attached).

---

# 13. Next Steps

No handoff to a new chat is needed right now (the commit/push closes this session naturally, not due to a context limit). If a new chat is opened later to continue, use Section 1 (full narrative) and Section 9 (gate summary table) of this document as the starting point.

**Suggested title for the next chat**, when applicable (format `FONDA (short project): Paso N[-M]: <short description>`): `FONDA (Wansoft): Paso 20: New scope, post-gate`

---

# Permanent Rule

Regenerate this document in full (never as patches) when: the user explicitly asks, a major step closes, the conversation gets very long, context exceeds ~70%, or a new chat needs to be opened due to token limits. In that last case, also generate:
1. The handoff prompt (Section 13, first code block, if applicable).
2. The suggested title for the new chat, in the format **`FONDA (short project): Paso N[-M]: <short description>`** (same style as the user's own session list, e.g. "FONDA (Wansoft): Paso 18-1: Extracción de Costos de Venta de Odoo" — chat titles themselves may stay in the user's own phrasing/Spanish, since they're UI labels, not repo content). `FONDA` is a fixed prefix (the company, across all of the user's projects); `(short project)` identifies which project this is (here: "Wansoft", taken from the shared project itself, not asked). Use `N` = the major step/block number in progress, `-M` = sub-part suffix if the step spans multiple consecutive sessions/chats.

**Note on language:** this document, all commit messages, and all documentation pushed to GitHub in this project must be written in English — even though the working conversation with the user is in Spanish. See project memory `feedback_github_content_english_only` for the full rule.
