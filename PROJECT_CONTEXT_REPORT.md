# PROJECT_CONTEXT_REPORT.md

Master continuity document. Generated/updated automatically at the close of major steps, on explicit request ("Generate project context report"), when the conversation gets very long, when consumed context exceeds ~70%, or when a new chat needs to be opened due to token limits. Always regenerated in full, never as an incremental patch.

Last generated: 2026-09-14, closing for the day — the Inventory duplicate bug carried over from 2026-09-10 is now genuinely fixed (not just patched), verified end-to-end on a real full daily cycle. Tomorrow (2026-09-15) is planned as one final validation exercise against the user's live Power BI reports before this round of work is considered done.

---

# 1. Executive Summary

**Overall project goal:** build a unified analytical layer in MySQL that integrates Wansoft, Odoo, and Zenput, hiding from the end user which system originates each piece of data.

**Current state:** the acceptance gate remains formally accepted (2026-08-31). Today closed out the one real open item from 2026-09-10 — the cross-run Inventory duplicate bug — not by finding its exact root cause (that search came up empty again), but by making duplicate inserts **structurally impossible**: added a real unique key to `getoutgoinginventory_salida` and rewrote its insert logic to `INSERT ... ON DUPLICATE KEY UPDATE`. Extended the same defense-in-depth pattern to 5 other legacy tables sharing the identical structural risk (check-existence-in-Python-then-insert), even though only the one above was ever proven to actually duplicate. Ran today's full daily cycle end-to-end afterward: **zero duplicates**, all 5 stages succeeded, and a fresh dev-vs-prod-vs-Power-BI reconciliation came back clean.

**Big win validated today:** the full daily cycle, including the now-fast Purchases pipeline (2026-09-10 fix), ran start to finish in about 1h20m (legacy chain 73min, everything else under 12min combined) with zero data-quality issues. A live dev-vs-prod comparison (Ventas, Inventario, Costos) plus a dev-vs-Power-BI cross-check for Puebla all reconciled exactly once date ranges were compared apples-to-apples — one apparent Puebla discrepancy ($1,320,792.80 vs $1,287,596.90) turned out to be a rolling-14-day-window vs. calendar-month mismatch, not a data problem, confirmed by re-running the exact same date range (Sept 1-14) and getting an exact match (600 orders, $1,287,596.90, matching Power BI digit for digit).

**Scope:** unchanged since 2026-08-31/09-10 (see prior reports for full branch list).

**Current block:** none.

## What was done this session (2026-09-14), in order:

**Part 1 — MySQL was down at session start (not a new crash):**
1. `mysqld` was not running when the session started. Investigated carefully given the recent crash history, but this turned out to be benign: MySQL isn't a Windows service (per standing project decision), and Friday's (2026-09-10) successful recovery had switched to `--console` mode with output redirected to now-deleted scratchpad temp files, so `mysql_error.log` simply stopped receiving new entries after the last crash trace — it looked alarming but wasn't. Started `mysqld.exe` normally (with the now-standard explicit `--defaults-file`) and it came up clean, confirming the server was healthy and had just not been started since the weekend.

**Part 2 — Investigated the 2026-09-10 cross-run Inventory duplicate bug; root cause still not found, but no longer needed:**
2. Re-examined `getOutgoingInventory.py`'s preload-into-a-dict logic in detail. Directly tested the preload query in isolation (both with int and string `subsidiary_name` parameters) — it worked correctly both ways, ruling out the type-mismatch theory. The exact mechanism that let a 2026-09-08-inserted row go unrecognized by the 2026-09-10 run's preload was never identified.
3. Rather than keep chasing it, pivoted to a structural fix: a real database-level unique constraint makes the failure mode impossible regardless of what the in-memory Python logic does.

**Part 3 — Surveyed which other tables share the same structural risk:**
4. Grepped all `legacy/wansoft/automaticos/*.py` and `legacy/wansoft/descargarCostoWansoft/*.py` scripts for the "check existence via SELECT, then INSERT" pattern, and checked each target table's actual indexes in dev.
5. Found the Sales domain (`getallordenesbyday_new_venta`/`_pago`/`_detalleventa`/`_modificador`) already has real unique keys (`Movimento`, `Pagos_Id`, `Movimiento_Id`) and uses `INSERT IGNORE` — this is why Sales has never shown a duplication bug, not luck.
6. Found 6 tables genuinely vulnerable (only a `PRIMARY` auto-increment id, no unique constraint on the actual business key): `getoutgoinginventory_salida` (confirmed broken), `getexpenses_factura` (had **zero indexes of any kind**, not even a PRIMARY KEY), `costeomensual_semanapyq`, `costeomensual`, `gettotalcostbydate`, `getglobalcashclosing`.
7. Found 2 tables with a different risk profile, deliberately left alone this round: `getinputinventory_entrada` (has a supporting non-unique index already, and checks existence per-row in real time rather than via a batch-preloaded dict — structurally safer even without a hard constraint); `gettablajeriareport` (no single Wansoft-provided row ID at all — its existence check uses 7 columns together, not a clean fit for this pattern, needs its own decision later).

**Part 4 — Added unique-key protection to all 6 vulnerable tables:**
8. `getoutgoinginventory_salida`: `UNIQUE KEY (subsidiary_name, Fecha, IdSalida)` — this also fixed a real performance problem: the preload query previously could only use the `subsidiary_name` index and had to scan-filter by `Fecha`, whereas this new index covers both filter columns directly.
9. `getexpenses_factura`: `UNIQUE KEY (IdDocumento, Sucursal)`. 0 pre-existing duplicates, safe to add directly.
10. `costeomensual_semanapyq`, `costeomensual`, `gettotalcostbydate`: each keys on `(subsidiary_id, business-date)`, but the business date is only available as `DATE(created_at)` — MariaDB 10.4 can't index that expression directly in `ADD INDEX`, so each got a generated column (`created_date DATE AS (DATE(created_at)) PERSISTENT`) plus a unique key on `(subsidiary_id, created_date)`. 0 pre-existing duplicates on all three.
11. `getglobalcashclosing`: keys on `(subsidiary_id, fecha_corte)` (a real date column, no generated column needed). Had **1,170 pre-existing duplicate rows** — cleaned with the same in-memory-group + batched-PK-delete method used on 2026-09-09/10, then the constraint applied cleanly. (16 rows with NULL in one of the two key columns remain, expected — MySQL unique constraints permit multiple NULLs.)
12. Documented all of this in a new `sql/maintenance/add_unique_keys_dedup_protection.sql`, including the exact statements, for replay on production once that side is promoted.

**Part 5 — Rewrote `getOutgoingInventory.py` to use the new constraint:**
13. Replaced the preload-into-a-dict + separate insert/update-query logic with a single `INSERT ... ON DUPLICATE KEY UPDATE` per row, using MySQL's own `cursor.rowcount` (1 = inserted, 2 = updated with a real change, 0 = matched but no-op) to preserve the same `[🆕]`/`[🔁]`/`[✔]` logging distinctions as before.
14. Verified the exact rowcount semantics directly against dev with a disposable test row before trusting it in the real pipeline: insert (1) → same data again (0) → different data (2) → confirmed only 1 row total exists throughout. Cleaned up the test row afterward.
15. Committed and pushed both the code rewrite and the SQL documentation file.

**Part 6 — Full daily cycle run, clean end to end:**
16. Ran today's full daily cycle (legacy chain → inventory → purchases → analytics-purchase → cutover). All 5 stages succeeded: legacy chain 4394s (73min), inventory pipeline 24s, purchases pipeline **109s** (confirms the 2026-09-10 fix holds under real conditions, not just the earlier isolated test), analytics-purchase pipeline 690s (11.5min), cutover checkpoint 0s (nothing due).
17. Confirmed **zero duplicates** in `getoutgoinginventory_salida` after the run (486,214 rows) — the fix held under a real, unattended, full-scale run, not just the disposable-row test.

**Part 7 — Dev-vs-prod-vs-Power-BI reconciliation (last 14 days, then Puebla drilled into exact calendar dates):**
18. Sales: 19/19 branches matched exactly between dev and prod.
19. Inventory: 12/12 Wansoft branches matched exactly between dev and prod (`getoutgoinginventory_salida`).
20. Costs: 19/19 branches matched between dev and prod on all 3 tables, except Coyoacán showing dev 1 day behind prod on all three (`costeomensual`, `costeomensual_semanapyq`, `gettotalcostbydate`) — same already-understood, non-bug pattern as 2026-09-09/10 (Odoo hadn't posted that specific day's cost entries yet when the pipeline ran).
21. Purchases: canonical-vs-analytics reconciliation near-perfect (rounding-level differences only), one branch (Tepeyac) off by 1 order out of 82 — dollar impact 3 cents, not investigated further.
22. Found what looked like a real discrepancy for Puebla's Sales total ($1,320,792.80 in both dev and prod SQL vs. $1,287,596.90 in the user's live Power BI/Wansoft UI) — root-caused live: the SQL used a rolling 14-day window (which included some of late August), while Power BI was filtered to calendar September only. Re-ran the exact same query bounded to 2026-09-01 through 09-14 and got an **exact match**: 600 orders, $1,287,596.90, identical to Power BI down to the order count. Not a data bug — a reminder to always match date-range semantics exactly (calendar period vs. rolling window) when cross-checking against a calendar-filtered report.

**Part 8 — Side task, unrelated to this project:**
23. At the user's request, drafted a standalone prompt (for a separate, unrelated chat) to analyze Puebla's monthly performance (August + September 2026) from the dev database in a scorecard format matching a real weekly scorecard the user shared as a reference, explicitly excluding year-over-year comparison (Puebla has no prior-year data in the system). This is not part of this project's continuity and needs no follow-up here.

**Open items carried into tomorrow (2026-09-15):**
- One final validation exercise planned: cross-check results against the user's live Power BI reports (broader than just the Puebla Sales spot-check done today — scope to be defined tomorrow).
- Replay `sql/maintenance/add_unique_keys_dedup_protection.sql` on production once that side of the project is promoted (unchanged, now more concretely documented).
- `innodb_buffer_pool_size=16M` risk (documented 2026-09-08, still relevant after 2 crash incidents in a week) remains unresolved.
- `getinputinventory_entrada` and `gettablajeriareport` were deliberately left without the new unique-key treatment this round — revisit if either is ever shown to actually duplicate.
- Isabel La Católica/San Jerónimo/Vía Vallejo Odoo cutover, at/after 2026-10-01 (unchanged).
- `gettablajeriareport` dev-vs-prod plateau (unchanged, low priority).

---

# 2. Functional Description of the Project

**What we're building:** a data warehouse in MySQL that pulls together Sales, Purchases, and Inventory data for Grupo Fonda Argentina, regardless of whether each branch runs on Wansoft or Odoo — **and that Power BI consumes through exactly one table per domain**, never a raw source-specific table.

**Migration direction:** only Sales stays permanently on Wansoft; Purchases, Inventory, and Costs migrate branch by branch to Odoo. Metepec and Napoles are the permanent Wansoft exceptions.

---

# 3. Current Architecture

**Source systems:** Wansoft (SOAP/WSDL), Odoo (XML-RPC, read-only), Zenput (REST API).

**Source governance (`core/config/companies.py`):** `COMPANY_SOURCE` decides Purchases/Inventory per branch. Sales is always Wansoft (`ALWAYS_WANSOFT_DOMAINS`).

**Branches on Odoo (Purchases + Inventory):** Antenas, La Esquina Coyoacán, CentroMyJ, Acoxpa, Tepeyac, Oceanía, Puebla. Staged for 2026-10-01: Isabel La Católica, San Jerónimo, Vía Vallejo. Permanently Wansoft: Metepec, Napoles.

**Full daily schedule (unchanged structurally; still not running as a persistent process):**
```
01:00  run_daily_legacy_chain()        -- sequential, Wansoft Ventas/Inventario/Costos + Zenput
13:00  inventory_pipeline_job          -- rebuilds analytics_inventory_snapshot/_balance
13:30  purchases_pipeline_job          -- ~2-6 min since the 2026-09-10 incremental fix
13:50  analytics_purchase_pipeline_job -- rebuilds analytics_purchase_order_lines -> _orders -> _daily_company_product
15:00  odoo_cutover_validation_job     -- T+7/T+30 checkpoint
```

**Duplicate-insert protection, new today — real unique keys, not just application logic:**
```
getoutgoinginventory_salida    UNIQUE (subsidiary_name, Fecha, IdSalida)  -- code now uses ON DUPLICATE KEY UPDATE
getexpenses_factura            UNIQUE (IdDocumento, Sucursal)             -- had zero indexes before
costeomensual_semanapyq        UNIQUE (subsidiary_id, created_date)       -- created_date is a new generated column
costeomensual                  UNIQUE (subsidiary_id, created_date)       -- same pattern
gettotalcostbydate              UNIQUE (subsidiary_id, created_date)       -- same pattern
getglobalcashclosing            UNIQUE (subsidiary_id, fecha_corte)        -- real date column, no generated column needed
```
See `sql/maintenance/add_unique_keys_dedup_protection.sql` for the exact statements and rationale per table, including which tables were deliberately left out and why. Only `getoutgoinginventory_salida`'s Python code was rewritten to use the constraint (`INSERT ... ON DUPLICATE KEY UPDATE`); the other 5 keep their existing per-row Python existence checks, with the new constraint as a safety net, not (yet) a replacement for that logic.

**MySQL operational note (reconfirmed today):** `mysqld.exe` must be launched with an explicit `--defaults-file="C:\xampp\mysql\bin\my.ini"` or it silently ignores that config file. Also: `mysql_error.log` stops receiving entries if mysqld is ever started in `--console` mode with output redirected elsewhere (as happened during the 2026-09-10 recovery) — an apparently-stale error log is not proof the server crashed again; check whether the process is actually running before assuming the worst.

**Power BI cross-check, new today:** confirmed live that `getallordenesbyday_new_venta` (Sales) reconciles exactly against the user's real Power BI reports, both for an all-branches aggregate and for a single branch (Puebla), as long as the SQL date range exactly matches Power BI's filter semantics (calendar month, not a rolling N-day window).

---

# 4. Detailed Status by Domain

### Sales
No open issues. Reconfirmed exact match against prod and against live Power BI today (all 19 branches; Puebla spot-checked at the order level).

### Purchases
No open issues. The incremental-load fix (2026-09-10) held up under today's real full-cycle run (109s, not just the earlier isolated 368s test). Canonical-vs-analytics reconciliation near-perfect; the one 1-order Tepeyac gap is trivial and not investigated further.

### Inventory
**The cross-run duplicate bug (open since 2026-09-10) is now closed** — not via root-causing the exact mechanism (never found), but via a real unique constraint + `ON DUPLICATE KEY UPDATE` that makes the failure mode structurally impossible. Verified with a disposable-row test and then with a real full-scale daily run: zero duplicates both times.

### Costs
No new issues. Coyoacán's Odoo-posting-lag pattern reconfirmed today, still understood as expected, not a bug.

### Security / Configuration
5 additional tables (beyond Inventory) got defense-in-depth unique-key protection today, even without a proven bug in any of them — see Section 3. `getexpenses_factura` in particular went from zero indexes of any kind to having a real unique key.

---

# 5. Architectural Decisions Made (chronological, this session)

| Decision | Rationale | Impact |
|---|---|---|
| Stopped trying to root-cause the exact cross-run duplicate mechanism in `getOutgoingInventory.py`; fixed it structurally instead | Two isolated tests (preload query with int vs. string param) both worked correctly, meaning the actual failure mode is elusive; a real DB constraint closes the whole class of bug regardless of the exact mechanism | `getoutgoinginventory_salida` schema + `getOutgoingInventory.py` |
| Extended the same unique-key pattern to 5 more tables as defense-in-depth, without proving each one is actually broken | They share the identical structural risk (check-in-Python-then-insert, no DB-level guarantee); cheap and safe to add now that duplicate-checking confirmed each had 0 (or a small, cleanable number of) existing violations | 5 additional tables, data-only for the Python scripts (not rewritten to use the constraint, unlike Inventory) |
| Left `getinputinventory_entrada` and `gettablajeriareport` out of this round | The first already uses a safer per-row real-time check; the second has no clean single-ID natural key, needs its own decision | No change to either |
| Documented the exact ALTER statements in a new SQL file rather than only applying them ad hoc | Needed for eventual production replay, and as a durable record separate from chat history | `sql/maintenance/add_unique_keys_dedup_protection.sql` |

---

# 6. Business Rules Implemented / Reinforced (this session)

- Unchanged from 2026-09-10, plus: **duplicate-insert protection for the 6 tables above is now enforced at the database level, not just in application code** — any future change to these tables' loading scripts must not silently drop or bypass the unique constraints.
- **When cross-checking dev/prod SQL against a calendar-filtered report (Power BI or otherwise), match the exact date-range semantics** — a rolling N-day window and a calendar-month filter are not interchangeable and will produce genuinely different totals even when the underlying data is identical.

---

# 7-8. Technical Conventions / Git State

**New learnings this session:**
- MariaDB 10.4 cannot index a raw expression like `DATE(created_at)` directly in `ADD INDEX`/`ADD UNIQUE KEY` — a generated column (`... AS (expr) PERSISTENT`) plus an index on that column is the working pattern.
- MySQL's `INSERT ... ON DUPLICATE KEY UPDATE` rowcount is genuinely useful for distinguishing insert (1) from a real update (2) from a no-op match (0) — worth reusing anywhere similar logging is wanted.
- A stale-looking `mysql_error.log` is not proof of a new crash if the server was ever started in `--console` mode with output redirected elsewhere — check the actual process state first.
- When a rolling-window SQL comparison disagrees with a calendar-filtered report, check the date range before assuming a data bug.

**Git state:** branch `main`, up to date with `origin/main`. This session's commit: the `getOutgoingInventory.py` rewrite plus `sql/maintenance/add_unique_keys_dedup_protection.sql`. `inventory_not_found_analysis.csv` remains permanently uncommitted per convention.

---

# 9. Important Historical Context — Combined Bug Log (do not re-investigate)

See prior reports for bugs #1-#17. This session's addition:

| # | Bug | Where it actually lived | Status |
|---|---|---|---|
| 17 (update) | Cross-run Inventory duplicate (originally found 2026-09-10, root cause never identified) | `getOutgoingInventory.py` | **Closed 2026-09-14** — not via root-cause, via a real unique constraint + `ON DUPLICATE KEY UPDATE` that makes the failure mode impossible regardless of mechanism. Verified with a disposable-row test and a full real daily run (zero duplicates both times). |

**Also confirmed NOT bugs this session:** the apparent Puebla Sales discrepancy (rolling-window vs. calendar-month date range mismatch, not a data problem — see Section 1, Part 7).

**Gate result:** unchanged, not reopened.

---

# 10. User Decisions (explicit, don't lose track of these)

- **New:** confirmed applying the unique-key + `ON DUPLICATE KEY UPDATE` pattern not just to the confirmed-broken table, but proactively to all tables sharing the same structural risk ("esto sería ideal que lo hagas en todas las tablas que se necesite").
- **New:** wants the daily commit pattern to continue as established (commit + push once a fix is validated, before moving to the next task).
- **New:** confirmed a side, unrelated task (Puebla monthly scorecard analysis) should be spun off into a completely separate chat, not treated as part of this project's continuity.
- **New:** tomorrow (2026-09-15) is planned as one final validation exercise, specifically cross-checking results against the user's live Power BI reports.

---

# 11-12. Identified Legacy / Consolidated Backlog

**Backlog, in rough priority order:**
- Tomorrow's final Power BI cross-check exercise (2026-09-15) — scope to be defined at the start of that session.
- Replay `sql/maintenance/add_unique_keys_dedup_protection.sql` on production once that side of the project is promoted.
- Raise `innodb_buffer_pool_size` before it causes a third incident (unchanged, still relevant).
- Decide whether `getinputinventory_entrada` and `gettablajeriareport` need the same unique-key treatment, if either is ever shown to actually duplicate.
- Execute the Isabel La Católica/San Jerónimo/Vía Vallejo Odoo cutover, at/after 2026-10-01 (unchanged).
- `gettablajeriareport` dev-vs-prod plateau (unchanged, low priority).

---

# 13. Next Steps — HANDOFF PROMPT

**Paste this as the first message when resuming (2026-09-15 or later):**

```
Continúo el proyecto Wansoft + Odoo + Zenput Data Warehouse & ETL Pipeline.
Lee completo PROJECT_CONTEXT_REPORT.md en la raíz del repositorio antes de
responder, especialmente la Sección 1 (sesión del 2026-09-14) y la
Sección 9 (log combinado de bugs).

Resumen rápido: el bug de duplicados de Inventario que quedó pendiente el
2026-09-10 ya quedó cerrado -- no encontramos la causa exacta, pero le
pusimos un índice único real + ON DUPLICATE KEY UPDATE, así que ya es
imposible que se duplique sin importar qué esté pasando en el código
Python. De paso le pusimos el mismo blindaje a otras 5 tablas con el
mismo riesgo estructural, aunque nunca se confirmó que estuvieran rotas.
Corrimos el ciclo diario completo de ayer limpio, cero duplicados, y
validamos dev vs prod vs tu Power BI real -- todo coincidió exacto una
vez que igualamos los rangos de fecha.

Hoy toca: el ejercicio final de validación contra Power BI que quedó
pendiente de ayer.
```

**Suggested title for the new chat**: `FONDA (Wansoft): Paso 22: Inventory dedup fix closed, final Power BI validation`

---

# Permanent Rule

Regenerate this document in full (never as patches) when: the user explicitly asks, a major step closes, the conversation gets very long, context exceeds ~70%, or a new chat needs to be opened due to token limits. In that last case, also generate:
1. The handoff prompt (Section 13, first code block, if applicable).
2. The suggested title for the new chat, in the format **`FONDA (short project): Paso N[-M]: <short description>`** (same style as the user's own session list). `FONDA` is a fixed prefix; `(short project)` identifies which project (here: "Wansoft"). Use `N` = the major step/block number in progress, `-M` = sub-part suffix if the step spans multiple consecutive sessions/chats.

**Note on language:** this document, all commit messages, and all documentation pushed to GitHub in this project must be written in English — even though the working conversation with the user is in Spanish. See project memory `feedback_github_content_english_only` for the full rule.
