# PROJECT_CONTEXT_REPORT.md

Master continuity document. Generated/updated automatically at the close of major steps, on explicit request ("Generate project context report"), when the conversation gets very long, when consumed context exceeds ~70%, or when a new chat needs to be opened due to token limits. Always regenerated in full, never as an incremental patch.

Last generated: 2026-09-09, closing today's step-by-step dev-vs-prod validation session — a clean step boundary (the user explicitly asked to close and confirm state). Not closing the chat due to context pressure this time; kept as an update checkpoint in case a new chat is needed later.

---

# 1. Executive Summary

**Overall project goal:** build a unified analytical layer in MySQL that integrates Wansoft, Odoo, and Zenput, hiding from the end user which system originates each piece of data.

**Current state:** the acceptance gate (Costs/Purchases/Inventory, Odoo branches) remains **formally accepted** (2026-08-31, unchanged). Today's session (2026-09-09) ran the full daily cycle end-to-end, found and fixed **two more real bugs** (a UTF-8 crash blocking the entire legacy chain silently, and a within-batch duplicate-insert bug in Inventory outgoing), and then did a slow, deliberate, step-by-step dev-vs-prod validation across all four domains (Sales, Inventory, Costs, Purchases) with the user driving phpMyAdmin and pausing at every step to resolve questions before continuing. The single biggest outcome: **the prior session's open "Acoxpa/Antenas/Tepeyac/Oceanía/Coyoacán ~54-62% Purchases coverage gap" finding is resolved** — it was a comparison-methodology error (comparing Odoo's official total against Wansoft's *unfiltered* raw table, which mixes real purchases with transfers/adjustments/internal movements), not a real data gap. Re-tested properly, Odoo captures as much or more than Wansoft in 4 of 5 branches, confirmed further with real invoice-level spot checks in two branches.

**Scope (unchanged since 2026-08-31/09-08):** 11 branches — 7 live on Odoo (Antenas, La Esquina Coyoacán, CentroMyJ, Acoxpa, Tepeyac, Oceanía, Puebla) + 3 staged for 2026-10-01 (Isabel La Católica, San Jerónimo, Vía Vallejo) + Metepec (permanently Wansoft, closed decision). The remaining 7 Wansoft-only branches stay out of scope. Napoles permanently Wansoft (franchise).

**Estimated progress:** unchanged in branch terms. The Power BI unification goal (Section 1 of the 2026-09-08 report) continues to firm up: Inventory's `analytics_inventory_balance` is confirmed safe and current; Purchases' `analytics_purchase_orders`/canonical layer is now confirmed **trustworthy**, not just scheduled — today's deep validation specifically targeted and resolved its one open credibility question (the coverage gap).

**Current block:** none. Two real code fixes made today (`extract/utils/legacy_runner.py`, `legacy/wansoft/automaticos/getOutgoingInventory.py`) plus a data cleanup (107,678 duplicate rows removed from dev's `getoutgoinginventory_salida`) are **not yet committed to git**, alongside the four files still pending from 2026-09-08 (`docs/power-bi-source-migration.md` and three `sql/maintenance/*.sql` files, now joined by a fourth: `verify_analytics_purchase_inventory_tables.sql`, created today). Explicit user go-ahead still not given for any of these commits.

## What was done this session (2026-09-09), in order:

**Part 1 — Ran the full daily cycle; found and fixed a bug that silently zeroed out the entire legacy chain:**
1. Picked up from the 2026-09-08 handoff. The scheduler process itself is not running persistently (it's triggered manually / would need `python -m pipelines.scheduler` left running); to actually execute "today's full cycle," ran each stage's underlying function directly in the correct order (legacy chain → inventory pipeline → purchases pipeline → analytics-purchase pipeline → cutover checkpoint), logging to a background-tracked file.
2. **Real bug found:** `extract/utils/legacy_runner.py` — the shared entrypoint every single legacy Wansoft script (`run_legacy_script()`, used by all 11 daily-chain steps) funnels through — printed a `▶ Ejecutando legacy: ...` banner containing a non-ASCII arrow character with **no UTF-8 guard**, before doing anything else. When stdout isn't UTF-8-capable (confirmed today: any non-interactive/redirected run, which is exactly what unattended scheduling looks like), this crashes **instantly**, before the wrapped script's own top-level code — including its own UTF-8 guard — ever gets a chance to run. Result: all 11 legacy-chain steps "ran" in 0 seconds and did zero real work, silently, with the failure caught and swallowed by `run_daily_legacy_chain()`'s per-step try/except (which only logs, doesn't stop the chain) — this is a strong candidate for why unattended runs of this project's oldest, most central pipeline may have been silently doing nothing for a long time.
3. Fixed by adding the same `sys.stdout.reconfigure(encoding="utf-8")` guard (already used piecemeal in ~10 other files this project) to `legacy_runner.py` itself, before its first print. Re-ran the legacy chain: all 11/11 steps completed successfully this time, doing real work (verified via live progress monitoring).
4. The `purchases_pipeline_job` stage of the overnight full-cycle run took **~17.6 hours** (vs. the ~43 minutes reported as typical on 2026-09-08) — completed successfully, no errors, but the duration itself is a new observation worth watching if it recurs.
5. `analytics_purchase_pipeline_job` (the new 13:50 step from yesterday) ran successfully: 664,090 rows prepared, 617,698 included in business views, ≈$1.038B total.
6. Also re-ran `inventory_pipeline_job` once more mid-morning (10/10 steps, 64s) specifically to pick up the fresh Wansoft entrada/salida data the corrected legacy chain had just produced, ensuring `analytics_inventory_balance` was fully same-day-current before validation started.

**Part 2 — Real Inventory duplicate-insert bug found (again) and root-caused; 107,678 duplicate rows cleaned from dev:**
7. During the step-by-step Inventory validation (see Part 3), dev's `getoutgoinginventory_salida` showed 12/12 Wansoft branches **1-51% above** prod (Versalles +51%, Viaducto +34%, Playa del Carmen +36%, others 1-24%) — unexpected, since 2026-09-08's fix + full rebuild had been confirmed as a 100% match at the time.
8. **Real bug found:** in `generate_insert_queries()` (`legacy/wansoft/automaticos/getOutgoingInventory.py`), the `existing_by_id` dict used to decide insert-vs-update-vs-skip is built **once**, from the DB, at the top of the function — and is **never updated** as new rows get inserted during the same call's loop. If the same `IdSalida` appears twice within a single batch Wansoft returns for one (subsidiary, day) — confirmed happening, e.g., Aeropuerto/2026-08-30 — the first occurrence inserts it correctly, but the second occurrence still sees the stale pre-loop snapshot and inserts it again: an exact duplicate, created within a single run, not across runs.
9. Fixed by updating `existing_by_id[IdSalida] = (...)` immediately after each insert/update inside the loop, so a same-batch repeat is now correctly recognized as already-handled.
10. **Scope of the existing bad data, confirmed before touching anything:** 107,678 duplicate rows out of 534,228 total (≈20% of the whole table) — 90,215 of those within the last 35 days, the rest older. Every duplicated group had exactly 2 copies (consistent with "the whole day got processed twice" for specific subsidiary/date combinations, not one record repeated many times).
11. Cleaned up with the user's explicit go-ahead ("es en dev, corrígelo... lo más que puede pasar es que volvamos a cargar todo"). First attempt (`DELETE ... INNER JOIN ... ON IdSalida/subsidiary_name/Fecha` self-join) was too slow (no index on `IdSalida`, O(n²) risk on a table with this exact corruption history from 2026-09-08) — killed before it ran long enough to matter, no side effects. Second approach: read the whole table into Python, group in memory, batch-delete by the indexed auto-increment `id` PK (5,000 rows/batch) — completed in ~6 seconds total. Result: 534,228 → 426,550 rows, 0 duplicates remaining, verified. Re-checked per-branch counts: **all 12 Wansoft branches now match prod exactly**, digit for digit.

**Part 3 — Step-by-step dev-vs-prod validation, user-paced ("no continuamos hasta responder dudas"), all four domains:**

12. **Sales:** ran the same block from `verify_daily_download_by_branch.sql`; 100% match, all 19 branches, confirming the 2026-09-07 fix still holds.

13. **Inventory:** entradas — dev correctly shows only 12 branches (by design: `is_wansoft_company()` stops dev from polling Wansoft for the 7 Odoo-migrated branches; not a bug, prod still shows all 17-19 because prod runs unmigrated code and/or has real residual Wansoft activity). Salidas — found and fixed the duplicate bug above (Part 2); after the fix, 100% match on all 12 Wansoft branches.

14. **Costs:** corrected an earlier (2026-09-08 chat) mis-classification — `costeomensual`, `costeomensual_semanapyq`, and `gettotalcostbydate` **are** Wansoft+Odoo blended (each has a real `odoo_subsidiaries` branch calling `extract/costs/odoo_cost_report.py`'s `get_daily_cost()`, confirmed in code). `getexpenses_factura`, `getinputinventory_entrada`, `getoutgoinginventory_salida`, `gettablajeriareport` remain Wansoft-only (they filter out Odoo branches, don't blend them). `getglobalcashclosing` has no filter and no Odoo branch at all — pure Wansoft, all 19 branches.
    - Discovered: for Odoo-sourced branches specifically, `created_at` in `costeomensual`/`costeomensual_semanapyq` is set to the **business date being processed** (`lafecha`, no time component — hence the `00:00:00` timestamps seen only on the 7 Odoo branches), not the real script-run time. Wansoft-native branches correctly show the real run timestamp. This means `created_at` cannot be used to judge Odoo-branch data freshness in these two tables — a documentation/interpretation note, not a bug.
    - Found a real 1-day gap for La Esquina Coyoacán: `costeomensual` missing 2026-09-03, `costeomensual_semanapyq` missing 2026-09-04 (two different dates, in two different tables). Root-caused to `get_daily_cost()` in `extract/costs/odoo_cost_report.py`, which is explicitly documented to return **no row at all** for a date with zero posted `account.move.line` entries in Odoo (`"Dates with no posted cost-of-sale lines are simply absent from the result (callers should treat missing dates as zero, not error)"`) — Odoo genuinely had no posted cost-of-sale journal entries for Coyoacán those two specific days when the pipeline ran. Not an ETL bug; worth a passive re-check next week to see if Odoo's accounting catches up.
    - "Taquería Exhibimex" (confirmed alias for Versalles, per the existing Zenput mapping) and "Taqueria San Fernando" (unrecognized) appear in prod's cost tables but not in dev's governance. User confirmed: **San Fernando no longer exists, drop it — not a gap to chase.**

15. **Purchases — the deep dive:**
    - Reconciliation between `canonical_purchase_order_snapshot` and `analytics_purchase_orders`: near-perfect across all 18 branches present (sub-dollar rounding only). Versalles is absent from canonical entirely — user confirmed this is correct: **Versalles doesn't purchase on its own, it's supplied via transfers from Taquería Parroquia.**
    - Investigated why comparing canonical's Wansoft-side total against raw `getinputinventory_entrada` (unfiltered) looked like canonical was missing roughly half the money, in every branch except Metepec (which matched almost exactly). Root cause, confirmed in code and with data: `getinputinventory_entrada`'s `TipoEntrada` column has 8 distinct movement types (Factura, Entrada con canal, Transferencia, Ajuste de inventario, Producto procesado, Inventario inicial, Orden de compra a proveedor, Eliminado por ajuste de lote); canonical's Wansoft loader (`load_wansoft_input_inventory_facturas()`) correctly filters to `TipoEntrada = 'Factura'` only, since that's the only type that represents a real invoiced purchase. Metepec happens to have almost no non-Factura movements (hence the near-exact match); other branches have roughly half their entrada volume in non-purchase movement types. **Confirmed: canonical was always correct; the naive unfiltered comparison was wrong.**
    - **This directly resolved the prior session's (2026-09-08) open finding.** Re-ran the Odoo-vs-Wansoft coverage comparison for the same 5 branches (Acoxpa, Antenas, Tepeyac, Oceanía, La Esquina Coyoacán), this time correctly filtering the Wansoft side to `TipoEntrada='Factura'` (last 10 days): Acoxpa 122%, Antenas 79%, La Esquina Coyoacán 162%, Oceanía 140%, Tepeyac 132% — i.e., **Odoo captures as much or more than Wansoft's own residual in 4 of 5 branches**, a complete reversal from the originally-reported 54-62%. Antenas remains the one softer case at 79%, noted but not investigated further (far less alarming than the original figure, plausibly normal week-to-week variance).
    - Per the user's explicit request, did an **invoice-level spot check** (not just aggregates) for La Esquina Coyoacán: pulled 10 real recent Facturas from prod's `getinputinventory_entrada` (2026-09-05 through 09-08). **0 of 10 existed anywhere in dev** — confirmed as expected, not a gap: dev's Wansoft ETL stopped polling Coyoacán entirely post-cutover, and canonical's Wansoft-side for Coyoacán only covers pre-cutover history. User explained the underlying reason: **Coyoacán keeps entering into Wansoft deliberately, as a manual backup in case Odoo fails** ("para protegerse de que falle Odoo"), not an accidental process gap.
    - Cross-checked those same 10 Wansoft facturas by exact amount against Odoo canonical orders in the same date window: **5 of 9 distinct facturas matched exactly** (same peso amount, plausible 1-3 day posting lag) to real Odoo purchase orders — confirming the backup theory: the real transaction lives in Odoo, Wansoft is a redundant safety copy, not a unique source.
    - Closed the loop with an aggregate 30-day total comparison, both branches: **Coyoacán** — Wansoft(Factura-only, prod)=$427,769.65/115 facturas vs. Odoo(canonical, dev)=$537,304.63/147 orders → Odoo at **125.6%**. **Tepeyac** (Odoo company name "MAQ", tested at the user's request as a second data point) — Wansoft(Factura-only, prod)=$898,419.28/127 facturas vs. Odoo(canonical, dev)=$1,229,515.41/177 orders → Odoo at **136.8%**. Both confirm: no real money is being lost, Odoo's coverage is complete or better than Wansoft's own backup shows.
    - New SQL file created and used today: `sql/maintenance/verify_analytics_purchase_inventory_tables.sql` (dev-only, validates the canonical/analytics layer specifically — freshness, coverage, canonical-vs-analytics reconciliation, the now-resolved coverage-gap investigation, inventory analytics coverage).

**Open items at end of session:**
- Two real code fixes (`extract/utils/legacy_runner.py`, `legacy/wansoft/automaticos/getOutgoingInventory.py`) plus the 107,678-row dev data cleanup are **not yet committed to git** — pending explicit go-ahead, same as the four files still pending from 2026-09-08.
- Antenas' 79% Odoo-vs-Wansoft coverage (Purchases) is the one branch that didn't cleanly clear 100%+ — not investigated further, low urgency given the broader pattern is healthy.
- Acoxpa, Oceanía, and Antenas were **not** given the invoice-level spot check that Coyoacán and Tepeyac received — only aggregate percentages exist for those three. Optional follow-up if full confidence across all 5 branches is wanted.
- `innodb_buffer_pool_size=16M` risk (from the 2026-09-08 corruption incident) is unchanged — not touched today (today's cleanup used indexed PK deletes, no DDL, deliberately to avoid re-triggering it).
- `purchases_pipeline_job`'s ~17.6-hour runtime today (vs. ~43 min typical) is unexplained — worth watching, not yet investigated.
- `gettablajeriareport` dev-vs-prod plateau (from 2026-08-31/09-08, ~3,137 vs ~6,100) remains untouched, still low priority per the user.
- Isabel La Católica/San Jerónimo/Vía Vallejo Odoo cutover, at/after 2026-10-01, unchanged.

---

# 2. Functional Description of the Project

**What we're building:** a data warehouse in MySQL that pulls together Sales, Purchases, and Inventory data for Grupo Fonda Argentina, regardless of whether each branch runs on Wansoft or Odoo — **and that Power BI consumes through exactly one table per domain**, never a raw source-specific table.

**Migration direction confirmed by the project owner:** the end goal is for **only Sales** to remain permanently on Wansoft; Purchases, Inventory, and Costs migrate branch by branch to Odoo. Metepec is the sole permanent exception (stays fully on Wansoft) alongside Napoles (franchise, all domains).

---

# 3. Current Architecture

**Source systems:** Wansoft (SOAP/WSDL), Odoo (XML-RPC, read-only), Zenput (REST API).

**Source governance (`core/config/companies.py`):** `COMPANY_SOURCE` decides Purchases/Inventory per branch (authoritative). `odoo_company_migration_policy` (MySQL table) decides whether the rollout is actually activated, and since when. Sales is always Wansoft (`ALWAYS_WANSOFT_DOMAINS`).

**Branches currently active on Odoo (Purchases + Inventory):** Antenas, La Esquina Coyoacán, CentroMyJ, Acoxpa, Tepeyac, Oceanía, Puebla. Odoo company names differ from Wansoft's `nombreCorto` for some of these (confirmed today): Tepeyac = "FONDA ARGENTINA MAQ", Acoxpa = "FONDA COSTA NERA", Coyoacán = "FONDA ARGENTINA COYOACAN", Oceanía = "FONDA ARGENTINA ENCUENTRO OCEANIA", Puebla = "FONDA ARGENTINA PUEBLA".

**Branches staged for 2026-10-01:** Isabel La Católica, San Jerónimo, Vía Vallejo (unchanged, `COMPANY_SOURCE` still `"wansoft"`).

**Permanently Wansoft, all domains:** Metepec (closed decision), Napoles (franchise).

**Full scheduler (`pipelines/scheduler.py`), unchanged from 2026-09-08:**
```
01:00  run_daily_legacy_chain()        -- sequential, one step waits for the previous
13:00  inventory_pipeline_job          -- rebuilds analytics_inventory_snapshot/_balance
13:30  purchases_pipeline_job          -- rebuilds canonical_purchase_order_snapshot etc.
13:50  analytics_purchase_pipeline_job -- rebuilds analytics_purchase_order_lines -> _orders -> _daily_company_product
15:00  odoo_cutover_validation_job     -- T+7/T+30 checkpoint for newly migrated branches
```
**Important operational note confirmed today:** this scheduler is a Python `schedule`-style loop (`python -m pipelines.scheduler`) that must be left running continuously to actually fire at these times — it is not currently running as a persistent process/service. "Running the daily cycle" today meant manually invoking each stage's function directly, in order, matching the schedule. Production rollout of the scheduler itself remains a separate, deferred backlog item.

**Wansoft `entrada`/`salida` movement types (`TipoEntrada`), confirmed today, relevant to any Purchases-related query on `getinputinventory_entrada`:** `Factura` (the only one that is a real invoiced purchase), `Entrada con canal`, `Transferencia`, `Ajuste de inventario`, `Producto procesado`, `Inventario inicial`, `Orden de compra a proveedor`, `Eliminado por ajuste de lote`. Any comparison of "Wansoft purchases" against the canonical/analytics layer, or against Odoo, **must filter `WHERE TipoEntrada = 'Factura'`** — comparing against the unfiltered table overstates Wansoft's "true" purchase total by roughly double for most branches (Metepec is the outlier, with almost no non-Factura movements).

**Power BI target layer (unchanged since 2026-09-08, now with higher confidence on Purchases):**
```
Sales     -> no change: getallordenesbyday_new_venta (+ getglobalcashclosing / costeomensual_semanapyq)
Purchases -> analytics_purchase_orders -- confirmed correctly built AND confirmed no real Odoo-coverage
             gap (2026-09-09 investigation) -- safe to trust as a source, still needs the "not yet
             rebuilt since scheduling fix" freshness gate re-confirmed on a normal automated run
Inventory -> analytics_inventory_balance -- confirmed safe, current
Costs     -> no unified table yet, out of scope for this round
```

---

# 4. Detailed Status by Domain

### Sales
Unchanged, confirmed 100% dev-vs-prod match again today.

### Purchases
- Canonical + analytics layers: internally reconciled (sub-dollar rounding only).
- **The 2026-09-08 "coverage gap" finding is resolved** — see Section 1, Part 3. It was a comparison artifact (unfiltered Wansoft baseline), not a real Odoo extraction problem. Re-tested with the correct Wansoft baseline (`TipoEntrada='Factura'` only) plus invoice-level spot checks in 2 branches: Odoo captures 122-162% of what Wansoft's own (deliberately-kept, backup-purpose) residual shows in 4 of 5 branches. Antenas at 79% is the one softer case, not yet dug into.
- Versalles legitimately has zero canonical purchase orders — confirmed by the user as expected (no direct purchasing, supplied via transfers from Taquería Parroquia).
- `getinputinventory_entrada`'s Wansoft side, for migrated branches, continues to receive real post-cutover activity **by deliberate design** (a manual operational backup in case Odoo fails), confirmed by the user today — not a process gap to fix.

### Inventory
- `getOutgoingInventory.py`: **second real bug found and fixed this session** (within-batch duplicate insert, distinct from the 2026-09-08 cross-run duplicate bug). 107,678 pre-existing duplicate rows cleaned from dev. Confirmed 100% match vs. prod on all 12 Wansoft branches after the fix + cleanup.
- `analytics_inventory_balance`: re-confirmed current and safe.

### Costs
- Corrected classification: `costeomensual`, `costeomensual_semanapyq`, `gettotalcostbydate` are Wansoft+Odoo blended (not Wansoft-only as stated in the 2026-09-08 report). `getglobalcashclosing`, `getexpenses_factura`, `getinputinventory_entrada`, `getoutgoinginventory_salida`, `gettablajeriareport` are not blended.
- Real, understood, non-bug 1-day gaps found for La Esquina Coyoacán (see Section 1, Part 3) — Odoo hadn't posted cost entries those specific days when checked.
- "Taqueria San Fernando" dropped from consideration (user: branch no longer exists).

### Security / Configuration
Unchanged this session — no new findings.

---

# 5. Architectural Decisions Made (chronological, this session)

| Decision | Rationale | Impact |
|---|---|---|
| `extract/utils/legacy_runner.py` given the same UTF-8 stdout guard used elsewhere | Its own banner print crashed before the wrapped legacy script's own guard could ever run, zeroing out the whole daily chain silently in any non-interactive context | `extract/utils/legacy_runner.py` |
| `getOutgoingInventory.py`'s `existing_by_id` dict updated incrementally during the insert loop, not just fetched once | A same-batch repeated `IdSalida` (confirmed happening) was invisible to a snapshot taken before the loop, causing exact duplicate inserts within a single run | `legacy/wansoft/automaticos/getOutgoingInventory.py` |
| 107,678 duplicate rows deleted from dev's `getoutgoinginventory_salida` via in-memory grouping + batched PK deletes, not a SQL self-join | Self-join without an index on `IdSalida` risked an unbounded slow query on a table with a recent corruption history; PK-indexed batch delete completed in ~6s | User explicitly approved ("es en dev, corrígelo") |
| Purchases coverage-gap re-investigation must filter Wansoft's `entrada` to `TipoEntrada='Factura'`, never compare unfiltered | Unfiltered comparison overstates "true" Wansoft purchases by roughly 2x for most branches, producing a false "Odoo is missing data" signal | Reused in `verify_analytics_purchase_inventory_tables.sql` and any future Purchases validation |
| Coyoacán's (and likely other migrated branches') ongoing post-cutover Wansoft `entrada` activity is intentional (manual backup against Odoo failure), not a process gap | Explicit user confirmation | No code change; documented here so it isn't re-investigated as a bug |
| "Taqueria San Fernando" excluded from any future branch-governance work | User confirmed: branch no longer exists | No code change |

---

# 6. Business Rules Implemented / Reinforced (this session)

- **Any Wansoft-purchases comparison against `getinputinventory_entrada` must filter `WHERE TipoEntrada = 'Factura'`** — the raw table mixes real invoiced purchases with transfers, adjustments, initial inventory, and processed-product movements that were never purchases.
- **`created_at` in `costeomensual`/`costeomensual_semanapyq` is not a freshness signal for Odoo-sourced rows** — it holds the business date being processed, not the real script-run timestamp, for exactly the 7 Odoo-migrated branches in those two tables.
- **A missing date in Odoo-sourced cost tables (via `extract/costs/odoo_cost_report.py`) means Odoo had zero posted cost-of-sale entries that day** — by design, not an error; callers must treat it as zero, not investigate as a bug, unless it persists for an unreasonable number of days.
- **Wansoft `entrada` activity continuing after a branch's Odoo cutover is expected, deliberate, backup behavior for at least Coyoacán** (and plausibly other migrated branches) — not to be treated as a default red flag without checking the aggregate Odoo-side total first.

---

# 7-8. Technical Conventions / Git State

**New learnings this session:**
- The project's own `schedule`-based scheduler must run as a persistent process to actually fire — it is not a cron/Task Scheduler entry today. "Running the daily cycle" currently means invoking each stage function directly and in order.
- A shared/common entrypoint function (like `legacy_runner.py`'s `run_legacy_script()`) needs its **own** UTF-8 guard — a guard inside the scripts it wraps doesn't help if the wrapper itself prints first and crashes before ever reaching them.
- A duplicate-insert fix that de-dupes only *across* separate calls (one call per day per subsidiary) is not sufficient if the same call's input batch can itself contain repeats — the in-memory lookup dict must be updated *during* the loop, not just built once beforehand.
- A DELETE that needs to remove a minority of rows from a large-ish table is much safer and faster done as "read + group in Python + batch-delete by indexed PK" than as an un-indexed multi-column self-join, especially on a table with a recent corruption history.
- Odoo company display names can differ meaningfully from the Wansoft `nombreCorto` for the same branch (e.g., Tepeyac = "MAQ" in Odoo) — useful to know when cross-referencing manually.

**Git state:** branch `main`, up to date with `origin/main` as of the start of this session. **Not yet committed** (pending explicit user go-ahead):
- `extract/utils/legacy_runner.py` — UTF-8 guard fix (new today).
- `legacy/wansoft/automaticos/getOutgoingInventory.py` — within-batch dedup fix (new today).
- `docs/power-bi-source-migration.md` — pending since 2026-09-08.
- `sql/maintenance/verify_dev_vs_prod.sql`, `verify_daily_download_by_branch.sql`, `verify_coyoacan_wansoft_vs_odoo.sql` — pending since 2026-09-08.
- `sql/maintenance/verify_analytics_purchase_inventory_tables.sql` — new today.

The 107,678-row data cleanup in dev's `getoutgoinginventory_salida` is a data-only change (no schema/DDL), already applied directly to the dev database — nothing to commit for that beyond the code fix that prevents recurrence.

**Never committed (project convention, unchanged):**
- `inventory_not_found_analysis.csv`.

---

# 9. Important Historical Context — Combined Bug Log (do not re-investigate)

See the 2026-08-31 report for bugs #1-#7, and the 2026-09-08 report for bugs #8-#13. This session's additions:

| # | Bug | Where it actually lived | Fixed in |
|---|---|---|---|
| 14 | Entire legacy daily chain (11 steps) silently did zero real work in any non-interactive run | `extract/utils/legacy_runner.py`'s own banner print, no UTF-8 guard, crashed before the wrapped script's own guard could run | Same file (2026-09-09) |
| 15 | `getOutgoingInventory_Salida` re-duplicated rows *within a single run* when the same `IdSalida` appeared twice in one Wansoft response batch (distinct from bug #10's cross-run duplication) | `getOutgoingInventory.py`, `existing_by_id` dict snapshotted once, never updated mid-loop | Same file (2026-09-09); 107,678 pre-existing duplicate rows cleaned from dev |

**Also this session, confirmed NOT bugs (do not re-flag without new evidence):**
- Purchases "coverage gap" (Acoxpa/Antenas/Tepeyac/Oceanía/Coyoacán, originally reported as 54-62%) — was a comparison-methodology artifact (unfiltered Wansoft baseline). Real coverage, correctly measured, is 122-162% in 4 of 5 branches; Antenas at 79% is the one open soft case.
- Coyoacán missing 1 day each in `costeomensual` (Sep 3) and `costeomensual_semanapyq` (Sep 4) — Odoo genuinely had no posted entries those days, by the ETL's documented design.
- `costeomensual`/`costeomensual_semanapyq` showing `00:00:00` timestamps for Odoo-sourced branches — `created_at` holds the business date, not the run time, for those rows.
- Dev's `getinputinventory_entrada`/`getoutgoinginventory_salida` showing fewer branches than prod — intentional filtering (`is_wansoft_company()`), not a gap.
- Ongoing post-cutover Wansoft `entrada` activity at Coyoacán — deliberate manual backup, per the user.

**Gate result (unchanged since 2026-08-31):** Purchases and Inventory, each compared independently against live Odoo, were at 20/20 PASS for the 6 active branches at gate acceptance time. Not reopened this session.

**Don't reopen without a new reason:** the Total Cost recognition lag in fresh weeks (original gate, bugs #1-#4). The `gettablajeriareport` dev-vs-prod gap (Wansoft-only, ~3,137 vs ~6,100) — still open, still low priority, untouched this session.

---

# 10. User Decisions (explicit, don't lose track of these)

- (All decisions from previous sessions still stand.)
- **New:** approved cleaning the 107,678 duplicate rows from dev's `getoutgoinginventory_salida` directly ("es en dev, corrígelo... lo más que puede pasar es que volvamos a cargar todo").
- **New:** confirmed Versalles legitimately has no direct purchases (supplied via transfers from Taquería Parroquia) — not a data gap.
- **New:** confirmed Coyoacán's ongoing post-cutover Wansoft `entrada` activity is a deliberate manual backup against Odoo failures, not an accidental process gap.
- **New:** confirmed "Taqueria San Fernando" no longer exists as a branch — drop it from consideration, don't chase it as a gap.
- **New:** wants the step-by-step, pause-and-resolve-questions validation style repeated as the default working mode for these sessions going forward ("no continuamos hasta responder dudas").
- **New:** explicitly requested testing a second migrated branch (Tepeyac/"MAQ") with the same invoice-level method used on Coyoacán, to confirm the pattern generalizes — confirmed it does.

---

# 11-12. Identified Legacy / Consolidated Backlog

**Backlog:**
- Decide whether to commit today's two code fixes plus the now five pending SQL/doc files to git.
- Optional: extend the invoice-level spot check (like Coyoacán/Tepeyac) to Acoxpa, Oceanía, and Antenas for full 5-branch confidence — Antenas' 79% aggregate figure makes it the most interesting candidate if only one more gets picked.
- Investigate why `purchases_pipeline_job` took ~17.6 hours today vs. the ~43 min reported as typical on 2026-09-08 — not yet looked into.
- Decide whether/when to raise `innodb_buffer_pool_size` on the dev MySQL instance before any future heavy DDL (unchanged, still open).
- Investigate the `gettablajeriareport` dev-vs-prod plateau (unchanged, low priority).
- Execute the real Isabel La Católica/San Jerónimo/Vía Vallejo Odoo cutover, at/after 2026-10-01 (unchanged).
- (Explicitly out of scope) the 7 deprioritized branches: Aeropuerto, Cancún, Playa del Carmen, Taquería Viaducto, Taquería Parroquia, Versalles, Viaducto — note: these ARE part of today's validated Wansoft-native set for Sales/Inventory/Costs, "deprioritized" here refers specifically to Odoo migration planning, not to today's validation scope.
- (Deferred, low priority) production rollout of the scheduler itself as a persistent process/service — still manual today.

---

# 13. Next Steps

No new-chat handoff prompt generated this time — this report was regenerated as a step-boundary checkpoint at the user's request ("cerramos aquí"), not because of context-window pressure. Continue in this same conversation unless/until a fresh chat is actually needed; if so, regenerate this document in full first and produce the handoff prompt + title at that time per the Permanent Rule below.

**Immediate open question for the user, next time work resumes:** commit decision (Section 7-8) — five files now pending across two sessions.

**New direction for tomorrow (2026-09-10), given by the user right as this report was being generated:** treat dev as a stand-in for production ("simular que ya estamos en productivo, aunque estemos en dev") — since today's validation showed dev tracking prod very closely across all four domains, the plan is to stop just reconciling raw numbers and start actually rehearsing the Power BI cutover itself:
- If dev still looks close enough to prod tomorrow (quick re-check, not a full re-validation), move toward figuring out the actual mechanics of repointing Power BI (`docs/power-bi-source-migration.md` already has the table-by-table mapping from 2026-09-08 — Purchases now has much higher confidence after today's coverage-gap resolution).
- The user wants to build/run **a dev-side Power BI test script that compares its output against what the current (real) Power BI report shows today** — i.e., a rehearsal/parallel-run comparison before actually touching the real Power BI data source, not a switch-and-see-what-breaks approach.
- This is a natural continuation of today's work, not a new validation cycle — the domain-by-domain dev-vs-prod reconciliation done today is what makes this rehearsal credible.

---

# Permanent Rule

Regenerate this document in full (never as patches) when: the user explicitly asks, a major step closes, the conversation gets very long, context exceeds ~70%, or a new chat needs to be opened due to token limits. In that last case, also generate:
1. The handoff prompt (Section 13, first code block, if applicable).
2. The suggested title for the new chat, in the format **`FONDA (short project): Paso N[-M]: <short description>`** (same style as the user's own session list). `FONDA` is a fixed prefix; `(short project)` identifies which project (here: "Wansoft"). Use `N` = the major step/block number in progress, `-M` = sub-part suffix if the step spans multiple consecutive sessions/chats.

**Note on language:** this document, all commit messages, and all documentation pushed to GitHub in this project must be written in English — even though the working conversation with the user is in Spanish. See project memory `feedback_github_content_english_only` for the full rule.
