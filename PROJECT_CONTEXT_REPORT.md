# PROJECT_CONTEXT_REPORT.md

Master continuity document. Generated/updated automatically at the close of major steps, on explicit request ("Generate project context report"), when the conversation gets very long, when consumed context exceeds ~70%, or when a new chat needs to be opened due to token limits. Always regenerated in full, never as an incremental patch.

Last generated: 2026-09-08, closing this chat to open a new one — **context-window pressure**, not a clean step boundary: a full daily-cycle run + dev-vs-prod validation is planned for tomorrow (2026-09-09) and needs a fresh context window. See Section 13 for the handoff prompt and new chat title.

---

# 1. Executive Summary

**Overall project goal:** build a unified analytical layer in MySQL that integrates Wansoft, Odoo, and Zenput, hiding from the end user which system originates each piece of data.

**Current state:** the acceptance gate (Costs/Purchases/Inventory, Odoo branches) remains **formally accepted** (2026-08-31, unchanged). Since then this multi-day session did three separate rounds of work: (1) automated the legacy Wansoft + Zenput daily scripts into the scheduler, (2) ran a weekly dev-vs-prod validation practice that found and fixed **three more real bugs** (Sales branch exclusion, Inventory duplicate inserts, a security bug printing passwords to stdout), survived a severe MySQL corruption incident during one of those fixes, and (3) discovered the user's real end goal — Power BI must read each domain from **one unified table** covering all 19 branches — and started migrating Purchases toward that (`analytics_purchase_orders`), which surfaced that layer as stale/unscheduled and fixed the scheduling gap.

**Scope (unchanged from 2026-08-31, now simplified — Metepec resolved):** 11 branches — 7 live on Odoo (Antenas, La Esquina Coyoacán, CentroMyJ, Acoxpa, Tepeyac, Oceanía, Puebla) + 3 staged for 2026-10-01 (Isabel La Católica, San Jerónimo, Vía Vallejo) + Metepec, which the user closed out this session as **permanently staying on Wansoft** — no longer a pending decision. The remaining 7 Wansoft branches (Aeropuerto, Cancún, Playa del Carmen, Taquería Viaducto, Taquería Parroquia, Versalles, Viaducto) stay out of scope. Napoles permanently Wansoft (franchise), not counted.

**Estimated progress:** unchanged in branch terms (7 of 11 fully live, 3 more staged), but the true finish line moved: the user's real goal isn't just "branch live on Odoo" but "Power BI reads one unified table per domain, no raw-table fallback." Inventory reached that finish line this session (confirmed safe, already scheduled). Purchases has the target table built and now scheduled, but not yet validated fresh (rebuild happens on the next scheduler run) and has an unexplained Odoo-coverage gap for 5 of the 7 live branches (see below) — not yet safe to repoint Power BI to it.

**Current block:** none. All code is committed and pushed to `main`. Three SQL helper files and one markdown report are staged locally but **not yet committed** (pending explicit user go-ahead, see Section 7-8).

## What was done this session (2026-08-31 through 2026-09-08), in order:

**Part 1 — Chain the legacy Wansoft + Zenput scripts into the scheduler (2026-08-31, commits `43ce1f6`, `643f40b`):**
1. Until now, `pipelines/scheduler.py` only automated the newer Odoo-side pipelines (Inventory 1pm, cutover checkpoint 3pm). The much older `legacy/wansoft/automaticos/*.py` scripts (Sales lock, Inventory in/out, several Costs reports) had to be run manually. User decision: chain all of them into the scheduler too, running once daily starting at 1am.
2. First pass used staggered fixed times 10 minutes apart per job — user corrected same day: "no se pueden correr en paralelo muchos" (several can't run concurrently — Wansoft SOAP / MySQL contention). Replaced with `run_daily_legacy_chain()`: one function that runs every step synchronously in order, each starting only when the previous finished, scheduled once via `schedule_daily_at(hour=1, minute=0)`. A failing step is caught/logged but doesn't block the rest of the chain.
3. User then explicitly asked to also include Zenput ("también mete al scheduler zenput") — done, even though it bypasses the documented safety gate in `docs/production-orchestration-plan.md` (which said Zenput automation needed more review first). Deliberate policy call by the project owner, not a re-verification that the underlying concern went away — flagged in code comments and memory for future reference if Zenput writes ever look off.
4. Found and fixed a real routing bug while wiring this: `automaticos/README.md` had the two Sales scripts' descriptions **swapped** vs. the actual code — the scheduler had been calling a raw XML downloader with a hardcoded May-2026 date range every 10 minutes, never the real Candado (`extractAllOrdersByDay.py`). Corrected to call the real one.
5. Full daily chain, in order: Ventas (Candado real) → Inventario entradas → Inventario salidas → Costos semana PyQ → Costos descarga Wansoft → Costos cierre global de caja → Compras facturas/gastos → Costos tablajería → Costos costo total por fecha → Zenput forms → Zenput tasks.
6. Ran the full new daily behavior end-to-end in dev twice more over the following days (2026-09-01, 2026-09-02) to let staleness close naturally — most tables converged to an exact or near-exact match with prod within 2-3 runs. `gettablajeriareport` plateaued at dev≈3,137 vs prod≈6,100 (Wansoft-only, no Odoo migration relevance) — flagged as a real, systematic gap, not yet root-caused, user chose to keep watching rather than dig in immediately.

**Part 2 — Incident: `.env` wiped and recovered (2026-09-01):**
7. The user accidentally overwrote `core/config/.env` with a blank template — all real credentials gone. Recovered from a VS Code Local History snapshot (`%APPDATA%\Code\User\History`) dated just before the wipe; verified all 4 DB targets (wansoft/zenput × dev/prod) plus Wansoft SOAP and Odoo reconnected successfully.

**Part 3 — Weekly manual dev-vs-prod verification becomes an ongoing practice, and a real schema quirk found (2026-09-02):**
8. Per the user's explicit request ("quiero validar yo mismo"), started handing over raw SQL (not scripts Claude runs) for the user to execute themselves in phpMyAdmin. Delivered `sql/maintenance/verify_dev_vs_prod.sql` (aggregate) and `sql/maintenance/verify_coyoacan_wansoft_vs_odoo.sql` (branch-specific).
9. Found while building these: `getinputinventory_entrada`/`getoutgoinginventory_salida`'s `subsidiary_name` column actually stores the **numeric Wansoft account id**, not the branch name (both legacy scripts insert `sub['id']`, not `sub['name']`) — a real schema quirk, not a bug to fix, but any hand-written SQL filtering by branch on these two tables must filter by numeric id.
10. Found, not yet resolved: prod keeps recording Coyoacán purchases in Wansoft (`getinputinventory_entrada`) all the way to 2026-08-31, well past its 2026-06-01 Odoo cutover — real, ongoing dual-system activity for a branch the project already treats as fully Odoo-sourced. Handed the user SQL to compare; not yet reviewed together — open question whether this is expected transition overlap or a real process gap. (See Part 6 below — this may be the same underlying gap as the Purchases-coverage shortfall found later this session.)

**Part 4 — Weekly practice continues; found & fixed a real Sales bug (2026-09-07, commit `51b268e`):**
11. Monday routine: ran the daily download, delivered `sql/maintenance/verify_daily_download_by_branch.sql` (reusable every day, groups by branch, annotates each branch's official Wansoft/Odoo source from the live `COMPANY_SOURCE` mapping).
12. The user ran it themselves and noticed dev's Sales table had only 12 branches vs prod's 19. Root cause: `extractAllOrdersByDay.py` (the real Sales Candado) was filtering its branch list with `is_wansoft_company()` — but Sales is `ALWAYS_WANSOFT_DOMAINS` for **all 19** branches, that filter only applies to Purchases/Inventory. This had silently dropped the 7 Odoo-migrated branches from Sales reconciliation since the scheduler chain started. Found entirely through the user's own weekly verification routine, working exactly as intended. Fixed by removing the filter; verified via an isolated run (0 errors, 19/19 branches) and later confirmed 100% dev-vs-prod match on all 19.
13. Also found a real security bug while auditing for similar issues: `getExpenses.py`/`getTablajeriaReport.py` both printed the full subsidiary list **including plaintext Wansoft passwords** to stdout — newly dangerous now that these run unattended nightly and get captured/logged. Fixed (commit `b3e0da8`, 2026-09-01) to print only branch names.
14. Also found (not fixed): the same `is_wansoft_company()` filter is present in several Costs scripts (`getCostReport_SemanaPyQ.py`, `getExpenses.py`, `getTablajeriaReport.py`, `getTotalCostByDate.py`, `descargarCostoWansoft.py`) and `getGlobalCashClosing.py` notably does not use it — consistent with the documented Costs architecture (Costs is not `ALWAYS_WANSOFT_DOMAINS`, unlike Sales). Flagged, not changed.
15. Real phpMyAdmin gotcha found while the user tested the SQL: running a multi-statement script from a **table-scoped** SQL tab throws `#1109 - Tabla desconocida` on any other table referenced, even with correct names — must run from the **database-level** SQL tab instead. Corrected the user's workflow guidance.

**Part 5 — Purchases pipeline found stale and never scheduled; fixed a UTF-8 crash (2026-09-08, commit `401e5fb`):**
16. Continuing the weekly validation, found `canonical_purchase_order_snapshot`'s Odoo-sourced rows were a week stale — `scripts/run_purchases_pipeline.py` had never actually been wired into `pipelines/scheduler.py` (only Inventory and the cutover checkpoint were). Two earlier manual attempts to run it had appeared to "FAIL" (including one that looked like a 17.5-hour hang) — root-caused to `canonical_purchase_etl.py` crashing on its own final `print("...✅...")` with no UTF-8 stdout guard, happening only **after** the real 774K+ row reload had already committed successfully. Fixed with the same `sys.stdout.reconfigure(encoding="utf-8")` guard used elsewhere in the project.
17. Added `pipelines/jobs/purchases_pipeline_job.py`, scheduled daily at 13:30 (after Inventory at 13:00, before the 3pm cutover checkpoint). A clean full re-run afterward: 10/10 steps SUCCESS, ~43 minutes.

**Part 6 — Real Inventory duplicate-insert bug + severe MySQL corruption incident (2026-09-08, commit `dbb28ad`):**
18. A comprehensive dev-vs-prod validation (Sales, Purchases, Inventory, all branches) found Sales 100% match (confirms Part 4's fix) and Purchases 100% match on the 12 Wansoft branches, but **`getOutgoingInventory_Salida` showed dev at 265%-311% of prod on every Wansoft branch**. Root cause: unlike `getInputInventory.py`, `getOutgoingInventory.py` did a blind `INSERT` with no existence check — every daily run re-inserted the same real events again within the 31-day rolling window.
19. Fixed by rewriting `generate_insert_queries()` to do one bulk pre-fetch per (subsidiary, day) using the existing `subsidiary_name` index, then compare in-memory via a dict — deliberately **not** a per-row `SELECT`, since the table has no index on `IdSalida` and is 36M+ rows.
20. **Attempting to fix this "properly" first (adding an index, then a batched DELETE) crashed the shared XAMPP MySQL instance three times in a row**, the third time boot-looping (crash-recovery itself crashing with an InnoDB assertion on the pending transaction — real page-level corruption, confirmed by a `CHECK TABLE` that also crashed it under `innodb_force_recovery=3`). Root cause: `innodb_buffer_pool_size=16M`, far too small for tables now in the tens-of-millions-of-rows range — **still unresolved, will recur on any future heavy DDL against this instance.**
21. Recovered by: booting under `innodb_force_recovery=3`, `DROP TABLE getOutgoingInventory_Salida` (safe — pure re-fetchable Wansoft API cache, not source of truth; user explicitly confirmed this destructive step), then working through a second failure caused by an orphaned 9.7GB `#sql-ib*.ibd` temp file from the crashed `CREATE INDEX` (deleted directly from disk with mysqld confirmed stopped), then `innodb_force_recovery=1` to let the pending transaction roll back cleanly, then removed `force_recovery` entirely for a fully normal restart. Full sequence documented in memory (`project_scheduler_legacy_chaining_plan`) in case this recurs.
22. Rebuilt the now-empty table from scratch via the fixed job: 415,904 rows, 0 errors, subsequently confirmed 100% match vs prod on all 12 Wansoft branches.

**Part 7 — The real goal surfaces: Power BI needs one unified table per domain, not a second table (2026-09-08):**
23. The user clarified the actual end goal driving all this validation work: "al final del día el resultado de las 19 [sucursales] va a quedar en una tabla que yo pueda leer como ahora lo hago con powerbi" — Power BI must read **one single table** per domain covering all 19 branches, explicitly "que no exista una segunda tabla." Today Purchases in Power BI reads `getexpenses_factura`, which is Wansoft-only and misses the 7 Odoo branches entirely.
24. Investigated and confirmed the target already exists: `analytics_purchase_orders` / `analytics_purchase_order_lines` / `analytics_purchase_daily_company_product`, built by `scripts/build_analytics_purchase_*.py` from `canonical_purchase_order_snapshot` — but these three build scripts were **never part of any scheduled pipeline**, confirmed stale (Puebla had 62 real canonical orders, ~$480K/10 days, but zero rows in `analytics_purchase_orders`).
25. Delivered `docs/power-bi-source-migration.md` (old table → new table mapping per domain, with exact column names and the `include_in_business_views = 1` filter recommendation) — sent to the user, **not yet committed to git**. Explicit finding: Inventory (`analytics_inventory_balance`) is already safe to repoint today (scheduled, confirmed present for all 19 branches); Purchases is **not yet safe** — stale and unscheduled at the time of writing; Sales and Costs need no change (single-source already).
26. Fixed the scheduling gap (commit `a5533d9`): added `pipelines/jobs/analytics_purchase_pipeline_job.py` (wraps the three build scripts via subprocess, same UTF-8 guard pattern) and scheduled it in `pipelines/scheduler.py` at 13:50, right after the 13:30 canonical Purchases refresh.
27. **Real, unexplained gap surfaced while investigating this, not yet root-caused:** even with canonical Purchases freshly refreshed, Acoxpa/Antenas/Tepeyac's Odoo-sourced totals only capture ~54-62% of what Wansoft residually shows for the same window, and Oceanía/La Esquina Coyoacán show **literal $0** in Odoo purchase orders in the last 10 days despite Wansoft still showing real activity ($488K and $263K respectively). Possibly the same underlying issue as the Coyoacán post-cutover Wansoft activity found in Part 3 — not yet cross-checked.
28. User confirmed Metepec's status is now **closed, not pending**: it stays permanently on Wansoft, reporting what it already reports — removed from the list of open decisions.
29. **Plan confirmed for tomorrow (2026-09-09):** run the full daily cycle (now including the 13:50 Purchases-analytics rebuild), validate dev-vs-prod correspondence, and receive SQL specifically for these corresponding analytics/canonical tables (not just the raw tables validated so far) — user's own words: "para mañana ejecutamos el ciclo completo, con la corrección de compras y validamos que la información corresponda entre dev y prod y los sql que me darás son para validar estas tablas correspondientes." Decided to close this chat here (context-window pressure) and continue in a new one before that work starts.

**Open risks (active, unresolved):**
- `innodb_buffer_pool_size=16M` on the shared XAMPP MySQL instance is far too small for this project's largest tables — any future heavy DDL (index creation, large batched deletes) risks repeating the 2026-09-08 corruption incident. Not yet raised as an action item with the user beyond the incident itself.
- Purchases-analytics layer (`analytics_purchase_orders` etc.) is now scheduled but has not actually been rebuilt fresh since the fix, and is not yet safe to repoint Power BI to.
- Acoxpa/Antenas/Tepeyac Odoo-Purchases coverage gap (~54-62% of Wansoft residual activity) and Oceanía/Coyoacán's $0 Odoo purchase orders in the last 10 days — flagged, not investigated.
- `gettablajeriareport` dev-vs-prod gap plateaued around 3,137 vs 6,100 (last 35 days) — flagged, not investigated (Wansoft-only, no Odoo relevance).

**Pending relevant decisions:**
- Whether/when to raise `innodb_buffer_pool_size` before attempting any future heavy DDL on the dev MySQL instance.
- Whether to commit `docs/power-bi-source-migration.md` and the three `sql/maintenance/*.sql` files to git (not yet explicitly requested by the user).
- Execute the real Isabel La Católica/San Jerónimo/Vallejo Odoo cutover, at/after 2026-10-01 (unchanged from the prior report, not touched this session).

---

# 2. Functional Description of the Project

**What we're building:** a data warehouse in MySQL that pulls together Sales, Purchases, and Inventory data for Grupo Fonda Argentina, regardless of whether each branch runs on Wansoft or Odoo — **and that Power BI consumes through exactly one table per domain**, never a raw source-specific table.

**Migration direction confirmed by the project owner:** the end goal is for **only Sales** to remain permanently on Wansoft; Purchases, Inventory, and Costs migrate branch by branch to Odoo. Metepec is the sole permanent exception (stays fully on Wansoft, closed decision, 2026-09-08) alongside Napoles (franchise, all domains, decided earlier).

---

# 3. Current Architecture

**Source systems:** Wansoft (SOAP/WSDL), Odoo (XML-RPC, read-only), Zenput (REST API).

**Source governance (`core/config/companies.py`):** `COMPANY_SOURCE` decides Purchases/Inventory per branch (authoritative). `odoo_company_migration_policy` (MySQL table, `is_active` + `operational_start_date`) decides whether the rollout is actually activated yet, and since when. Sales is always Wansoft, no exceptions (`ALWAYS_WANSOFT_DOMAINS`).

**Branches currently active on Odoo (Purchases + Inventory):** Antenas, La Esquina Coyoacán, CentroMyJ, Acoxpa, Tepeyac, Oceanía, Puebla.

**Branches staged for 2026-10-01** (governance ready, `COMPANY_SOURCE` still `"wansoft"`, unchanged this session): Isabel La Católica, San Jerónimo, Vía Vallejo.

**Out of current scope:** Aeropuerto, Cancún, Playa del Carmen, Taquería Viaducto, Taquería Parroquia, Versalles, Viaducto.

**Permanently Wansoft, all domains:** Metepec (closed decision, 2026-09-08 — known data-reliability issue on the franchise side, accepted as-is, not scheduled for Odoo), Napoles (franchise).

**Full scheduler (`pipelines/scheduler.py`), current state:**
```
01:00  run_daily_legacy_chain()        -- sequential, one step waits for the previous:
         1. Ventas (Candado real)          -- extract_all_orders_xml_job
         2. Inventario - entradas           -- input_inventory_job
         3. Inventario - salidas            -- outgoing_inventory_job
         4. Costos - semana PyQ             -- cost_report_semana_pyq_job
         5. Costos - descarga Wansoft       -- download_costs_job
         6. Costos - cierre global de caja  -- global_cash_closing_job
         7. Compras - facturas/gastos       -- expenses_job
         8. Costos - tablajería             -- tablajeria_report_job
         9. Costos - costo total por fecha  -- total_cost_by_date_job
        10. Zenput - forms                  -- zenput_forms_job (bypasses safety gate, owner's decision)
        11. Zenput - tasks                  -- zenput_tasks_job (same)
13:00  inventory_pipeline_job              -- rebuilds analytics_inventory_snapshot/_balance (Odoo side)
13:30  purchases_pipeline_job              -- rebuilds canonical_purchase_order_snapshot etc. (Odoo + Wansoft)
13:50  analytics_purchase_pipeline_job     -- NEW (2026-09-08): rebuilds analytics_purchase_order_lines
                                               -> analytics_purchase_orders -> analytics_purchase_daily_company_product
15:00  odoo_cutover_validation_job         -- T+7/T+30 checkpoint for newly migrated branches
```
A step failing inside `run_daily_legacy_chain` is caught/logged and doesn't block the rest of the chain.

**Cutover checkpoint (unchanged since 2026-08-31):**
```
odoo_company_migration_policy.operational_start_date  -> reference date
T+7 / T+30 after that date                             -> triggers validation (once each)
Purchases: canonical_purchase_order_snapshot (dev) vs live purchase.order (Odoo, state not in cancel/draft)
Inventory: analytics_inventory_balance (dev) vs live stock.quant (Odoo, internal locations, mapped products only)
Purchases FAIL -> self-corrects (re-runs run_purchases_pipeline)
Inventory FAIL -> alert only (manual_review_required), does not self-correct
```

**Power BI target layer (new framing this session, see `docs/power-bi-source-migration.md`):**
```
Sales     -> no change: getallordenesbyday_new_venta (+ getglobalcashclosing / costeomensual_semanapyq)
Purchases -> analytics_purchase_orders (order/invoice level) -- built, now scheduled, NOT yet safe to repoint
             (analytics_purchase_order_lines for product detail; _daily_company_product for pre-aggregated fact)
Inventory -> analytics_inventory_balance -- built, scheduled, CONFIRMED SAFE to repoint today
Costs     -> no unified table yet, out of scope for this round -- keep current raw sources
```

---

# 4. Detailed Status by Domain

### Sales
- Candado (`extractAllOrdersByDay.py`) fixed this session: no longer excludes the 7 Odoo-migrated branches (real bug, was silently limiting Sales reconciliation to 12 of 19 branches since the daily-chain automation started). Verified 100% dev-vs-prod match on all 19 branches.
- Now part of the 01:00 daily chain (previously manual / wrong-script-scheduled).

### Purchases
- Canonical layer (`canonical_purchase_order_snapshot` etc.) unchanged in logic this session; the automation gap around it is what got fixed — `purchases_pipeline_job` now scheduled daily at 13:30 (was never scheduled before, causing the Odoo side to silently go stale).
- New: the Power-BI-facing analytics layer on top of canonical (`analytics_purchase_orders` etc.) is now also scheduled (13:50), closing the gap that made it unusable as a Power BI source. Not yet rebuilt fresh since the fix, and not yet safe to repoint Power BI to — pending tomorrow's validation.
- Real, unexplained coverage gap found (not fixed): 3 of 7 live Odoo branches under-capture Wansoft's residual activity by ~40-46%, 2 more show $0 Odoo activity in a 10-day window despite real Wansoft activity for the same window. See Section 1, Part 7.

### Inventory
- `getOutgoingInventory.py` fixed this session: real duplicate-insert bug (dev at 265-311% of prod on every Wansoft branch), resolved via bulk pre-fetch + in-memory dedup instead of a blind insert. Confirmed 100% match vs prod on all 12 Wansoft branches after rebuild.
- `analytics_inventory_balance` confirmed safe and ready as the Power BI source today — already scheduled (1pm), present for all 19 branches.

### Costs
- Unchanged this session. No unified analytics table exists yet — out of scope for the current Power BI migration round.

### Security / Configuration
- Real bug fixed: `getExpenses.py`/`getTablajeriaReport.py` were printing plaintext Wansoft passwords to stdout on every run — now print only branch names.
- Metepec formally closed as permanently Wansoft (governance-level decision, no code change — it was never in `COMPANY_SOURCE` as Odoo to begin with).

*(Remaining domains/tables unchanged this session — see the previous report in commit history, or Section 9 below, for the full gate-era detail.)*

---

# 5. Architectural Decisions Made (chronological, this session)

| Decision | Rationale | Impact |
|---|---|---|
| Legacy Wansoft + Zenput scripts chained into the scheduler, once daily starting 01:00 | Previously manual; user wants a fully unattended daily cycle | `pipelines/scheduler.py`, new `pipelines/jobs/*.py` wrappers |
| Chain runs sequentially (one step waits for the previous), not staggered fixed times | "no se pueden correr en paralelo muchos" — Wansoft SOAP / MySQL contention | `run_daily_legacy_chain()` |
| Zenput included in the daily chain despite bypassing the documented safety gate | Explicit owner policy decision, not a re-verification that the gate's concerns are resolved | `pipelines/jobs/zenput_forms_job.py`/`zenput_tasks_job.py` |
| Weekly practice: run daily download in dev, hand the user raw SQL (not a script) to self-verify dev vs prod in phpMyAdmin | User wants hands-on verification capability, not just a script Claude runs | `sql/maintenance/*.sql` (untracked, see Section 7-8) |
| `getOutgoingInventory.py` dedup via one bulk pre-fetch per (subsidiary, day) + in-memory dict, not a per-row SELECT | Table has no index on `IdSalida`, is 36M+ rows; a per-row SELECT would need a new index, which crashed the DB when attempted | `legacy/wansoft/automaticos/getOutgoingInventory.py` |
| Dropped `getOutgoingInventory_Salida` during the MySQL corruption incident instead of attempting repair | Pure re-fetchable Wansoft API cache, not source of truth — safe to lose and rebuild | User explicitly confirmed this destructive step |
| Metepec stays permanently on Wansoft, decision closed | Franchise data-reliability issue accepted as a permanent limitation, not worth chasing further | Scope/governance, no code change |
| `purchases_pipeline_job` scheduled daily at 13:30 | Was never scheduled at all — root cause of week-old Odoo-side Purchases data | `pipelines/scheduler.py` |
| `canonical_purchase_etl.py` given a UTF-8 stdout guard | A print-only crash after real work had already committed was being misread as a pipeline failure twice | Same module |
| Power BI must read one unified table per domain, no second/raw-table fallback | User's explicit end goal for all the validation work this session | `docs/power-bi-source-migration.md` (new) |
| `analytics_purchase_pipeline_job` scheduled daily at 13:50, right after the canonical refresh | The three `build_analytics_purchase_*.py` scripts were never part of any pipeline — confirmed stale (Puebla: real canonical data, zero analytics rows) | `pipelines/jobs/analytics_purchase_pipeline_job.py`, `pipelines/scheduler.py` |
| Inventory (`analytics_inventory_balance`) declared safe to repoint Power BI to today; Purchases explicitly not yet | Inventory already scheduled/confirmed complete; Purchases analytics layer was stale/unscheduled at time of writing | `docs/power-bi-source-migration.md` |

---

# 6. Business Rules Implemented / Reinforced (this session)

- **Sales stays `ALWAYS_WANSOFT_DOMAINS` for all 19 branches, no exceptions** — the Candado's branch list must never be filtered by `COMPANY_SOURCE` (that governs Purchases/Inventory only).
- **`getOutgoingInventory_Salida` inserts must check for existing rows before inserting** — same upsert discipline `getInputInventory.py` already had, now applied symmetrically.
- **No credential data (passwords, tokens) may be printed to stdout in any script that runs unattended in the scheduler.**
- **Power BI consumption target, per domain: exactly one unified table, all 19 branches, no raw source-specific fallback** — the standing rule going forward for any future domain unification (Costs, when it happens, should follow the same pattern).

---

# 7-8. Technical Conventions / Git State

**New learnings this session:**
- `SHOW ENGINE INNODB STATUS` (undo log entries, `ACTIVE <n> sec inserting`) is far more reliable than client-side CPU/memory for telling whether a long-running DB write is genuinely stuck vs. just slow — buffered process output can make real progress look frozen.
- MySQL folds table names to lowercase on this server (`lower_case_table_names`); Python's mysql-connector tolerates mixed case, but phpMyAdmin's SQL tab throws `#1109` on anything but the real lowercase name. Any hand-written SQL for the user must use lowercase table names.
- phpMyAdmin: run multi-statement scripts from the **database-level** SQL tab, never a specific table's SQL tab (the latter throws `#1109` on unrelated table references even with correct casing).
- Never attempt `CREATE INDEX` / large batched `DELETE` / any heavy DDL against the shared XAMPP dev MySQL instance without first raising `innodb_buffer_pool_size` well above its current 16M default — confirmed root cause of a severe corruption incident this session.
- `getinputinventory_entrada`/`getoutgoinginventory_salida`'s `subsidiary_name` column holds the numeric Wansoft account id, not the branch name — a real (if confusing) schema quirk, not a bug.

**Git state:** branch `main`, up to date with `origin/main`. Commits this session (chronological): `43ce1f6`, `643f40b` (scheduler chaining), `b3e0da8` (security fix), `51b268e` (Sales branch-exclusion fix), `401e5fb` (Purchases pipeline scheduled + UTF-8 fix), `dbb28ad` (Inventory duplicate-insert fix), `a5533d9` (Purchases-analytics scheduling). Files touched:

- `legacy/wansoft/automaticos/extractAllOrdersByDay.py` — removed the wrong `is_wansoft_company()` filter (Sales fix); UTF-8 guard.
- `legacy/wansoft/automaticos/getInputInventory.py` — UTF-8 guard only.
- `legacy/wansoft/automaticos/getOutgoingInventory.py` — duplicate-insert fix (bulk pre-fetch + dict dedup); UTF-8 guard.
- `legacy/wansoft/automaticos/getExpenses.py`, `getTablajeriaReport.py` — stopped printing plaintext passwords; UTF-8 guard.
- `extract/purchases/canonical_purchase_etl.py` — UTF-8 stdout/stderr guard.
- `pipelines/scheduler.py` — `run_daily_legacy_chain()` (new), `DAILY_LEGACY_CHAIN_STEPS` (new), `purchases_pipeline_job` scheduled 13:30, `analytics_purchase_pipeline_job` scheduled 13:50.
- `pipelines/jobs/purchases_pipeline_job.py` — new.
- `pipelines/jobs/analytics_purchase_pipeline_job.py` — new.
- Several new `pipelines/jobs/*.py` thin wrappers for the legacy chain steps (cost_report_semana_pyq_job, download_costs_job, global_cash_closing_job, expenses_job, tablajeria_report_job, total_cost_by_date_job, zenput_forms_job, zenput_tasks_job, extract_all_orders_xml_job, input_inventory_job, outgoing_inventory_job).

**Not yet committed (pending explicit user go-ahead, not a convention exclusion):**
- `docs/power-bi-source-migration.md` — sent to the user via file share, not yet pushed to the repo.
- `sql/maintenance/verify_dev_vs_prod.sql`, `verify_daily_download_by_branch.sql`, `verify_coyoacan_wansoft_vs_odoo.sql` — handed to the user for manual phpMyAdmin use, not yet pushed.

**Never committed (project convention, unchanged):**
- `inventory_not_found_analysis.csv`.

---

# 9. Important Historical Context — Combined Bug Log (do not re-investigate)

See the 2026-08-31 report (commit `67e6a04` or earlier) for the full gate-era narrative (bugs #1-#7). This session's additions:

| # | Bug | Where it actually lived | Fixed in |
|---|---|---|---|
| 1-7 | (Gate-era bugs, see prior report) | — | 2026-08-27 / 2026-08-31 |
| 8 | Sales Candado wrongly excluded the 7 Odoo-migrated branches | `extractAllOrdersByDay.py` used `is_wansoft_company()`, a Purchases/Inventory-only filter, on a Sales script | Same file (2026-09-07, `51b268e`) |
| 9 | Plaintext Wansoft passwords printed to stdout on every run | `getExpenses.py`, `getTablajeriaReport.py` | Same files (2026-09-01, `b3e0da8`) |
| 10 | `getOutgoingInventory_Salida` re-inserted the same real events every daily run (dev at 265-311% of prod) | `getOutgoingInventory.py`, blind INSERT with no existence check | Same file (2026-09-08, `dbb28ad`) |
| 11 | Purchases pipeline (Odoo side) silently went a week stale | `run_purchases_pipeline.py` never wired into `pipelines/scheduler.py` | `pipelines/scheduler.py` (2026-09-08, `401e5fb`) |
| 12 | Real pipeline work (774K+ rows) misread as "FAILED" twice | `canonical_purchase_etl.py`, no UTF-8 guard, crashed on its own final print after committing | Same file (2026-09-08, `401e5fb`) |
| 13 | Power-BI-facing Purchases analytics layer silently stale (Puebla: real canonical data, zero analytics rows) | `scripts/build_analytics_purchase_*.py` never part of any scheduled pipeline | `pipelines/jobs/analytics_purchase_pipeline_job.py`, `pipelines/scheduler.py` (2026-09-08, `a5533d9`) |

**Gate result (unchanged since 2026-08-31):** Purchases and Inventory, each compared independently against live Odoo, were at 20/20 PASS for the 6 active branches at gate acceptance time. **Formally accepted 2026-08-31, not reopened this session** — this session's bugs were found through the separate weekly dev-vs-prod practice, not the gate checkpoint itself.

**Don't reopen without a new reason:** the Total Cost recognition lag in fresh weeks (original gate, bugs #1-#4) remains the same finding confirmed with real data — not touched this session. The `gettablajeriareport` dev-vs-prod gap (Wansoft-only) is a new, separate, still-open finding — see Section 1.

---

# 10. User Decisions (explicit, don't lose track of these)

- (All decisions from previous sessions still stand, see prior report / commit history.)
- **New:** chain the legacy Wansoft `automaticos/*.py` scripts into the scheduler, running automatically instead of manually.
- **New:** run them sequentially (one after another), not staggered — several can't run in parallel.
- **New:** include Zenput forms/tasks in the same daily chain, explicitly accepting that it bypasses the documented safety gate.
- **New:** ongoing weekly practice — run the daily download in dev, get raw SQL (not a script) to self-verify dev vs prod in phpMyAdmin each day, per domain, with the official Wansoft/Odoo source annotated per branch.
- **New:** when the MySQL corruption incident hit, explicitly confirmed dropping `getOutgoingInventory_Salida` (pure re-fetchable cache) rather than attempting repair.
- **New:** Metepec's data-reliability issue is closed — stays permanently on Wansoft, not a pending decision anymore.
- **New:** Power BI's real end goal is one unified table per domain covering all 19 branches, explicitly "que no exista una segunda tabla" — driving the Purchases-analytics scheduling fix and the `docs/power-bi-source-migration.md` report.
- **New:** for tomorrow (2026-09-09) — run the full daily cycle including the new Purchases-analytics rebuild, validate dev-vs-prod correspondence, and receive SQL specifically for the corresponding analytics/canonical tables.
- **New:** close this chat here (context pressure) and continue in a new one before that work starts.

---

# 11-12. Identified Legacy / Consolidated Backlog

**Backlog:**
- Run the full daily cycle tomorrow (2026-09-09), including the new 13:50 Purchases-analytics rebuild, and validate dev-vs-prod correspondence for those specific analytics/canonical tables — deliver SQL for this.
- Investigate the Acoxpa/Antenas/Tepeyac Odoo-Purchases coverage gap (~54-62% of Wansoft residual) and Oceanía/Coyoacán's $0 Odoo purchase orders in the last 10 days — not yet started, possibly related to the Coyoacán post-cutover Wansoft-activity finding (Section 1, Part 3).
- Decide whether/when to raise `innodb_buffer_pool_size` on the dev MySQL instance before any future heavy DDL.
- Decide whether to commit `docs/power-bi-source-migration.md` and the three `sql/maintenance/*.sql` files to git.
- Investigate the `gettablajeriareport` dev-vs-prod plateau (~3,137 vs ~6,100 in the last 35 days) — Wansoft-only, no Odoo relevance, low priority per the user.
- Execute the real Isabel La Católica/San Jerónimo/Vallejo cutover, at/after 2026-10-01 (unchanged, see project memory `project_october_migration_wave`).
- (Explicitly out of scope for now) the 7 deprioritized branches: Aeropuerto, Cancún, Playa del Carmen, Taquería Viaducto, Taquería Parroquia, Versalles, Viaducto.
- (Deferred, low priority) production rollout of the scheduler itself — still dev-only, not yet revisited this session.

---

# 13. Next Steps — HANDOFF PROMPT FOR THE NEW CHAT

**Paste this as the first message in the new chat:**

```
Continúo el proyecto Wansoft + Odoo + Zenput Data Warehouse & ETL Pipeline.
Lee completo PROJECT_CONTEXT_REPORT.md en la raíz del repositorio antes de
responder, especialmente la Sección 1 (narrativa completa de esta sesión
larga, 2026-08-31 a 2026-09-08) y la Sección 9 (log combinado de bugs).

Resumen rápido: encadené los scripts legacy de Wansoft + Zenput al
scheduler (corren solos, secuenciales, desde la 1am). Con eso activa,
empezamos una práctica semanal de validar dev vs prod con SQL que yo
mismo corro en phpMyAdmin -- eso encontró y arregló 3 bugs reales más
(Ventas excluía las 7 sucursales Odoo, Inventario duplicaba inserciones,
un bug de seguridad imprimía contraseñas). Durante uno de esos arreglos
MySQL se corrompió feo y lo recuperamos completo (detalle en memoria
project_scheduler_legacy_chaining_plan). Metepec quedó cerrado
definitivamente en Wansoft. El objetivo real detrás de toda esta
validación resultó ser que Power BI lea una sola tabla unificada por
dominio (no una tabla cruda por sistema) -- ya lo logramos para
Inventario (analytics_inventory_balance, listo hoy) y dejamos programada
la reconstrucción diaria de la capa de Compras para Power BI
(analytics_purchase_orders, 13:50) aunque todavía no está validada fresca
ni lista para repuntar Power BI.

Hoy toca: ejecutar el ciclo diario completo (incluye ahora el rebuild de
analítica de Compras a las 13:50), validar que dev y prod correspondan, y
darle al usuario el SQL para validar específicamente esas tablas
analíticas/canónicas (no solo las tablas crudas ya validadas antes). Ver
Sección 1 parte final y Sección 11-12 para el backlog completo, incluido
un hallazgo sin resolver: 3 sucursales en Odoo (Acoxpa/Antenas/Tepeyac)
solo capturan ~54-62% de lo que Wansoft sigue mostrando, y 2 más
(Oceanía/Coyoacán) muestran $0 en compras Odoo en los últimos 10 días.

Todo el trabajo es en dev (ENV=dev en PowerShell); producción solo se
toca en modo lectura. No hace falta pedir autorización para acciones de
dev. Todo commit y documentación que vaya a GitHub debe quedar en
inglés, aunque hablemos en español.
```

**Suggested title for the new chat**: `FONDA (Wansoft): Paso 20: Scheduler chaining, weekly validation, Power BI unification`

---

# Permanent Rule

Regenerate this document in full (never as patches) when: the user explicitly asks, a major step closes, the conversation gets very long, context exceeds ~70%, or a new chat needs to be opened due to token limits. In that last case, also generate:
1. The handoff prompt (Section 13, first code block, if applicable).
2. The suggested title for the new chat, in the format **`FONDA (short project): Paso N[-M]: <short description>`** (same style as the user's own session list, e.g. "FONDA (Wansoft): Paso 18-1: Extracción de Costos de Venta de Odoo" — chat titles themselves may stay in the user's own phrasing/Spanish, since they're UI labels, not repo content). `FONDA` is a fixed prefix (the company, across all of the user's projects); `(short project)` identifies which project this is (here: "Wansoft", taken from the shared project itself, not asked). Use `N` = the major step/block number in progress, `-M` = sub-part suffix if the step spans multiple consecutive sessions/chats.

**Note on language:** this document, all commit messages, and all documentation pushed to GitHub in this project must be written in English — even though the working conversation with the user is in Spanish. See project memory `feedback_github_content_english_only` for the full rule.
