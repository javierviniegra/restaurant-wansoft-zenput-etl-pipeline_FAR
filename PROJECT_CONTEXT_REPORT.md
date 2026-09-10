# PROJECT_CONTEXT_REPORT.md

Master continuity document. Generated/updated automatically at the close of major steps, on explicit request ("Generate project context report"), when the conversation gets very long, when consumed context exceeds ~70%, or when a new chat needs to be opened due to token limits. Always regenerated in full, never as an incremental patch.

Last generated: 2026-09-10, closing for the day (user leaving, hard stop at 15:45) — the next work session is planned for Monday 2026-09-14 (see Section 13 handoff), so this doubles as a new-chat-ready checkpoint even though this exact chat may continue.

---

# 1. Executive Summary

**Overall project goal:** build a unified analytical layer in MySQL that integrates Wansoft, Odoo, and Zenput, hiding from the end user which system originates each piece of data.

**Current state:** the acceptance gate remains formally accepted (2026-08-31). Today (2026-09-10) the plan was to "simulate production" — treat dev as a production stand-in and validate a fixed calendar window (2026-09-01 through 09) against real prod and against real Power BI screenshots the user provided. That plan succeeded, but only after two significant detours: (1) a major performance fix to the Purchases canonical pipeline (17.6 hours → 6 minutes), which triggered (2) a real production-adjacent MySQL crash during the very next run, recovered using the same playbook as the 2026-09-08 incident, and (3) a **second, distinct** Inventory duplicate-insert bug discovered during the final validation pass — different from the one fixed 2026-09-09, not yet root-caused in code.

**Big win validated today:** Sales (`getallordenesbyday_new_venta`) reconciles **exactly** three ways — dev SQL, prod SQL, and the user's real production Power BI dashboards — both in aggregate (19 branches: 8,276 orders, $16,403,300.03) and at single-branch detail (Acoxpa: 749 orders, $1,698,819.80, matched digit-for-digit in all three sources). Purchases' new canonical/analytics layer also reconciled internally and its Acoxpa number ($653,033.39) was shown to plausibly exceed the old Power-BI-visible Wansoft-only number ($585,018.73) — consistent with Odoo capturing more than Wansoft's residual, as established 2026-09-09.

**Scope:** unchanged since 2026-08-31/09-09 (see prior reports for full branch list).

**Current block:** none blocking, but **two real open items carry into Monday**:
1. A new Inventory duplicate-insert bug (cross-run, not within-batch — distinct from the 2026-09-09 fix) is confirmed present but not yet root-caused in code. Data was cleaned twice today (107K+ then 111K+ duplicate rows) as a stopgap; the underlying cause will recur on the next legacy-chain run until fixed.
2. Root cause of today's mid-run MySQL crash (process killed abruptly, not a DDL-triggered corruption like 2026-09-08) was never identified — worth watching for a pattern if it recurs.

## What was done this session (2026-09-10), in order:

**Part 1 — Committed and pushed the 2026-09-09 backlog:**
1. With explicit user go-ahead, committed and pushed 4 commits: the `legacy_runner.py` UTF-8 fix, the `getOutgoingInventory.py` within-batch dedup fix, the 4 pending SQL/doc files from 2026-09-08 (`docs/power-bi-source-migration.md` + 3 `verify_*.sql` files), and the regenerated context report. `inventory_not_found_analysis.csv` correctly excluded per standing convention.

**Part 2 — Found and fixed a real performance bug: the Wansoft canonical Purchases load reprocessed 5 years of history on every run:**
2. Resumed the "simulate production" plan: re-ran today's full daily cycle (legacy chain → inventory → purchases → analytics-purchase → cutover). Legacy chain and inventory pipeline completed cleanly (11/11 and 10/10 steps).
3. **Real bug found:** `extract/purchases/canonical_purchase_etl.py`'s `load_wansoft_input_inventory_facturas()` had no date filter — it read `getinputinventory_entrada`'s **entire history since 2021** (1.8M+ rows, `TipoEntrada` not indexed) on every single run, then did a full DELETE+reinsert of all Wansoft-sourced canonical rows. This was the true cause of the 17.6-hour `purchases_pipeline_job` runtime observed 2026-09-08/09.
4. Per the user's explicit direction ("opción 3, y en el futuro cuando se cargan compras solo verificar que las de un mes para atrás estén completas"), implemented **incremental processing, not history truncation**: added `WANSOFT_CANONICAL_INCREMENTAL_WINDOW_DAYS = 35`, filtered the load query to that rolling window, and changed `delete_existing_wansoft_rows()` to accept a `date_column` parameter and only delete/reinsert rows within that same window per table (`order_date` for orders/lines, `date_done` for receipts, `move_date` for receipt moves) — full historical canonical data older than 35 days is now left untouched on every run instead of being wiped and reloaded.
5. Verified the fix directly: `load_wansoft_input_inventory_facturas()` went from reading the full table to **12,809 rows in 14.4 seconds**. Re-ran the purchases pipeline: **368 seconds total** (vs. 63,317s / 17.6h before) — a ~172x speedup. **Not yet committed** — deliberately held for a single "final adjustments" commit at the end of today's testing, per the user's own stated plan; committed and pushed at the very end of this session (see Part 6).

**Part 3 — A real production-adjacent MySQL crash, mid-run, and recovery:**
6. During the immediately-following `analytics_purchase_pipeline_job` run, MySQL (the shared local XAMPP dev instance) was killed abruptly mid-write — cause never identified (not a DDL-triggered crash like 2026-09-08; the process simply stopped with no graceful shutdown or crash log entry at the moment it happened). `analytics_purchase_order_lines`'s tablespace was left truncated relative to what the redo log expected, producing `[FATAL] InnoDB: Trying to read page number 46338 ... which is outside the tablespace bounds` on every subsequent boot attempt.
7. Recovered using the same playbook as 2026-09-08 (see `my.ini` comments and project memory `project_scheduler_legacy_chaining_plan` for the full precedent): `innodb_force_recovery=3` alone still hit the same FATAL error during redo application before the server could accept connections. Escalated to `innodb_force_recovery=6` (skips redo roll-forward entirely) with the user's explicit go-ahead given the (small, disclosed) risk of losing recently-committed redo on other tables — this let the server boot, but then blocked `DROP TABLE` outright ("table is read only"). What actually worked: stop mysqld, delete `analytics_purchase_order_lines.ibd` directly from disk, reboot at the much gentler `innodb_force_recovery=1` (InnoDB then treated it as a gracefully-missing tablespace, same message pattern as the 2026-09-08 case), `DROP TABLE` succeeded, removed `innodb_force_recovery` from `my.ini` entirely, clean restart confirmed healthy.
8. One operational lesson from this recovery, worth remembering: `mysqld.exe` **must** be started with an explicit `--defaults-file="C:\xampp\mysql\bin\my.ini"` — starting it bare (`mysqld.exe --console`) silently ignored `my.ini`, including the `innodb_force_recovery` setting, for several failed attempts before this was noticed.
9. Rebuilt all 3 `analytics_purchase_*` tables from scratch (all "BUILD RESULT: COMPLETED") and the cutover checkpoint (which had also failed to connect during the crash) — confirmed fully fresh and healthy afterward.

**Part 4 — The "simulate production" validation itself, fixed window 2026-09-01 to 09:**
10. At the user's request, switched from a rolling 10-day window to a fixed calendar range (Sep 1-9) specifically so it could be cross-checked against the user's real production Power BI reports.
11. **Sales: perfect 3-way match** — dev SQL, prod SQL (queried directly by Claude since the user's phpMyAdmin access to prod was too slow to use), and the user's live Power BI screenhots, both aggregate (all 19 branches) and single-branch (Acoxpa). See Executive Summary for the exact numbers.
12. **Purchases:** canonical-vs-analytics reconciliation near-perfect (rounding only). Cross-checked Acoxpa's canonical total ($653,033.39, Sep1-9) against the user's Power BI "Entradas de Inventario por Factura" report (the OLD Wansoft-only source Power BI reads today, $585,018.73 for Acoxpa/September) — canonical is higher, consistent with the 2026-09-09 finding that Odoo captures more than Wansoft's residual for migrated branches.
13. **Prod itself was very slow** for substantial queries during this window — confirmed via `SHOW FULL PROCESSLIST` on prod: a genuinely abandoned query (65+ minutes old, almost certainly the user's own orphaned phpMyAdmin tab still executing server-side after they navigated away) was found and killed (`KILL 234`, with explicit user confirmation) alongside contention from concurrent large unindexed scans on `getoutgoinginventory_salida`. After killing it and re-running fresh, both Sales and Inventory queries against prod completed in seconds.
14. **Inventory (salidas): second real duplicate-insert bug found.** After prod finally responded, dev showed all 12 Wansoft branches consistently **higher** than prod again (0.5%-42%) for the Sep1-9 window — the same symptom as the bug fixed 2026-09-09, but confirmed to be a **different mechanism**: spot-checked a duplicate pair and found one copy `created_at` 2026-09-08 14:46 (predates the 2026-09-09 fix) and the other `created_at` 2026-09-10 09:29 (today's run, **after** the fix was deployed) — same `IdSalida`. This means today's run failed to recognize an already-existing row from a **previous** run and inserted it again — a cross-run recognition failure, not the within-batch issue the 2026-09-09 fix addressed. **Not yet root-caused in code.** Cleaned up as a stopgap (111,178 duplicate rows removed, same safe in-memory-group + batched-PK-delete method as 2026-09-09); after cleanup, dev matched prod exactly on all 12 branches.
15. **Costs:** confirmed consistent with the already-understood 2026-09-09 finding (Coyoacán short 1 day in `costeomensual` for this window — Odoo hadn't posted that day's entries, not a bug).

**Part 5 — Scheduling note:**
16. User wants to continue this same "simulate production" validation practice starting **Monday 2026-09-14** and through that week, **except Wednesday 2026-09-16** (not a working day). Saved to project memory `project_dev_prod_simulation_schedule`.

**Part 6 — Final commit:**
17. Committed and pushed the incremental Wansoft canonical Purchases fix (`extract/purchases/canonical_purchase_etl.py`) as the single "final adjustments" commit for the day, per the plan stated at the start of this session. `inventory_not_found_analysis.csv` again excluded per convention.

**Open items carried into Monday 2026-09-14:**
- **Root-cause the new cross-run Inventory duplicate bug** in `getOutgoingInventory.py` — confirmed real, confirmed distinct from the 2026-09-09 fix, not yet understood or fixed in code. Will recur on every legacy-chain run until fixed.
- Understand why MySQL crashed abruptly today (no DDL involved this time, no crash-log entry at the moment of death) — watch for a recurring pattern.
- `innodb_buffer_pool_size=16M` risk (documented 2026-09-08) remains unresolved and increasingly relevant given two crash incidents in 3 days.
- Continue/extend the invoice-level Power-BI cross-check to more branches if full confidence is wanted (only Acoxpa done today; Coyoacán/Tepeyac done 2026-09-09).
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

**Full daily schedule (unchanged structurally; timings now dramatically faster for Purchases):**
```
01:00  run_daily_legacy_chain()        -- sequential, Wansoft Ventas/Inventario/Costos + Zenput
13:00  inventory_pipeline_job          -- rebuilds analytics_inventory_snapshot/_balance
13:30  purchases_pipeline_job          -- NOW ~6 min instead of ~17.6h (see Section 5)
13:50  analytics_purchase_pipeline_job -- rebuilds analytics_purchase_order_lines -> _orders -> _daily_company_product
15:00  odoo_cutover_validation_job     -- T+7/T+30 checkpoint
```
Still not running as a persistent process — each session's "daily cycle" is triggered manually by invoking the stage functions directly, in order.

**New: Wansoft canonical Purchases load is now incremental, not full-reload:**
```
WANSOFT_CANONICAL_INCREMENTAL_WINDOW_DAYS = 35  (extract/purchases/canonical_purchase_etl.py)
```
`load_wansoft_input_inventory_facturas()` only reads `getinputinventory_entrada` (TipoEntrada='Factura') for the last 35 days. `delete_existing_wansoft_rows(table_name, date_column)` only deletes/reinserts Wansoft-sourced canonical rows within that same window (per-table date column: `order_date` for orders/lines, `date_done` for receipts, `move_date` for receipt moves) — history older than 35 days is preserved untouched across runs, never reprocessed.

**MySQL operational note, new today:** `mysqld.exe` must be launched with an explicit `--defaults-file="C:\xampp\mysql\bin\my.ini"` or it silently ignores that config file (including any `innodb_force_recovery` setting) — this cost significant time during today's crash recovery before being noticed.

**Power BI target layer:** unchanged from 2026-09-08/09, now with a real cross-check against live prod Power BI confirming Sales already matches perfectly and Purchases' new number is directionally correct (higher than the old Wansoft-only figure, as expected for a migrated branch).

---

# 4. Detailed Status by Domain

### Sales
Triple-confirmed today (dev SQL = prod SQL = live Power BI), aggregate and per-branch. No open issues.

### Purchases
Canonical/analytics reconciliation near-perfect. The Wansoft-side load is now fast and incremental (Section 3). Acoxpa cross-checked against real Power BI, directionally consistent with the already-understood Odoo-captures-more-than-Wansoft-residual pattern (2026-09-09).

### Inventory
**Two distinct real bugs found in `getOutgoingInventory.py` in three days** — the within-batch one (fixed 2026-09-09, verified holding) and a new cross-run one (found today, confirmed real, not yet fixed in code). Data cleaned as a stopgap both times; underlying cross-run cause still needs code investigation before it can be trusted to run unattended.

### Costs
No change from 2026-09-09's understanding. Coyoacán's expected 1-day gap reconfirmed, not a bug.

### Security / Configuration
No new findings. New MySQL operational note (Section 3) about `--defaults-file` is worth folding into any future ops runbook.

---

# 5. Architectural Decisions Made (chronological, this session)

| Decision | Rationale | Impact |
|---|---|---|
| Wansoft canonical Purchases load made incremental (35-day window), not truncated | User's explicit direction: keep full history, but only re-verify the last ~month on each run, for performance | `extract/purchases/canonical_purchase_etl.py` |
| Escalated `innodb_force_recovery` 3 → 6, with explicit disclosed risk, to get MySQL to boot after the crash | Level 3 alone still hit the same FATAL redo-application error before accepting connections | `C:\xampp\mysql\bin\my.ini` (temporary, removed after recovery) |
| Deleted the corrupted `analytics_purchase_order_lines.ibd` directly from disk (mysqld stopped) rather than repair in place | Exact same successful pattern as the 2026-09-08 incident; table is a pure rebuildable analytics cache, not source of truth | Data file only, table rebuilt after |
| Killed an abandoned 65-minute prod query (`KILL 234`) | User confirmed it was very likely their own orphaned phpMyAdmin tab still executing server-side; was contending for I/O with legitimate validation queries | Read-only production troubleshooting, explicit user go-ahead |
| Fixed calendar window (2026-09-01 to 09) instead of rolling 10-day window for today's validation | Lets the user cross-check directly against monthly Power BI reports | This session's SQL only |
| Cleaned up the new cross-run Inventory duplicates as a stopgap without waiting to root-cause the code | Time-boxed session (user hard-stop at 15:45); unblocks today's validation, code fix deferred to Monday | `getoutgoinginventory_salida` data only, not the script |

---

# 6. Business Rules Implemented / Reinforced (this session)

- Unchanged from 2026-09-09, plus: **the Wansoft-side canonical Purchases layer is now explicitly a 35-day rolling re-verification window, not a full-history reload** — any future change to that logic should preserve this property (full history kept, only recent window reprocessed) rather than reverting to a full reload.
- **`mysqld.exe` requires an explicit `--defaults-file` argument in this environment** — bare invocation silently ignores `my.ini`.

---

# 7-8. Technical Conventions / Git State

**New learnings this session:**
- A duplicate-insert fix that only updates an in-memory lookup dict *during* a batch (2026-09-09's fix) does not by itself guarantee correctness *across* separate runs — those are two distinct failure modes and need to be verified separately, not assumed to be the same bug.
- `SHOW FULL PROCESSLIST` on a slow-seeming database is a cheap, fast, genuinely diagnostic first step before assuming general server load — today it revealed one specific abandoned query as the real cause, not ambient slowness.
- InnoDB crash recovery playbooks are refined by iteration, not perfectly reusable verbatim: today's incident needed one MORE escalation step (force_recovery 6, then back down to 1 after deleting the file) than the 2026-09-08 precedent's exact sequence, because the failure this time blocked `DROP TABLE` itself at the higher level.

**Git state:** branch `main`, up to date with `origin/main`. This session's commits (chronological): 4 commits carrying over the 2026-09-09 backlog (UTF-8 fix, within-batch dedup fix, SQL/doc files, context report), plus one final commit for the incremental Wansoft canonical Purchases fix. `inventory_not_found_analysis.csv` remains permanently uncommitted per convention.

---

# 9. Important Historical Context — Combined Bug Log (do not re-investigate)

See prior reports for bugs #1-#15. This session's addition:

| # | Bug | Where it actually lived | Status |
|---|---|---|---|
| 16 | Purchases canonical Wansoft load reprocessed the full 5-year history on every run (17.6h) | `extract/purchases/canonical_purchase_etl.py`, no date filter | **Fixed** 2026-09-10 (incremental 35-day window) |
| 17 | Inventory outgoing: cross-run duplicate — today's run re-inserted a row that already existed from a previous run | `getOutgoingInventory.py` (distinct from bug #15, the within-batch case) | **Confirmed real, NOT yet fixed in code** — data cleaned as stopgap only |

**Also confirmed NOT bugs this session:** prod's general slowness during validation (root cause was one specific abandoned query, not ambient load); the Acoxpa Purchases number being higher in canonical than in the old Power BI report (expected, per 2026-09-09's coverage finding).

**Gate result:** unchanged, not reopened.

---

# 10. User Decisions (explicit, don't lose track of these)

- **New:** chose incremental processing (35-day window, full history preserved) over truncating history, for the slow Purchases canonical load.
- **New:** explicitly approved escalating `innodb_force_recovery` to level 6 during the crash recovery, after being told the specific disclosed risk.
- **New:** explicitly approved killing prod process 234 (the abandoned query).
- **New:** wants the fixed-calendar-window (not rolling) validation style going forward when cross-checking against Power BI/monthly reports.
- **New:** confirmed the cross-run Inventory duplicate cleanup as an acceptable stopgap for today, with the real code fix deferred to Monday.
- **New:** continuing this validation practice Monday 2026-09-14 through that week, except Wednesday 2026-09-16 (not a working day) — saved to memory.
- **New:** hard-stopped this session at 15:45 for a personal commitment; explicitly asked to close cleanly rather than leave things mid-step.

---

# 11-12. Identified Legacy / Consolidated Backlog

**Backlog, in rough priority order for Monday:**
- Root-cause and fix the new cross-run Inventory duplicate bug in `getOutgoingInventory.py` — top priority, will keep recurring otherwise.
- Investigate today's unexplained abrupt MySQL kill (no DDL, no crash-log entry) — watch for a pattern; consider whether `innodb_buffer_pool_size=16M` is implicated even without an explicit ALTER/CREATE INDEX this time.
- Raise `innodb_buffer_pool_size` before it causes a third incident (unchanged, increasingly urgent).
- Extend the invoice-level Power-BI cross-check to more branches (only Acoxpa done today).
- Execute the Isabel La Católica/San Jerónimo/Vía Vallejo Odoo cutover, at/after 2026-10-01 (unchanged).
- `gettablajeriareport` dev-vs-prod plateau (unchanged, low priority).

---

# 13. Next Steps — HANDOFF PROMPT FOR MONDAY

**Paste this as the first message when resuming (Monday 2026-09-14 or later):**

```
Continúo el proyecto Wansoft + Odoo + Zenput Data Warehouse & ETL Pipeline.
Lee completo PROJECT_CONTEXT_REPORT.md en la raíz del repositorio antes de
responder, especialmente la Sección 1 (sesión del 2026-09-10) y la Sección 9
(log combinado de bugs).

Resumen rápido: arreglamos que la capa canónica de Compras (lado Wansoft)
reprocesaba 5 años de historia en cada corrida (17.6h -> 6 min, ahora es
incremental, ventana de 35 días, sin perder historial). Justo después,
MySQL se cayó a media corrida por una razón todavía sin identificar (no
fue una operación de DDL esta vez) -- lo recuperamos con el mismo
procedimiento del incidente del 2026-09-08 (force_recovery, borrar el
.ibd corrupto, DROP TABLE, reconstruir). Ya con todo sano, hicimos la
prueba de "simular productivo" para el 1-9 de septiembre: Ventas
coincidió perfecto en tres lados (dev, prod, y tu Power BI real).
Compras también coincidió bien. Pero en Inventario encontramos un bug
NUEVO y distinto al de ayer -- duplicados entre corridas distintas (no
dentro del mismo lote) -- lo limpiamos como parche pero el código
todavía no está arreglado.

Hoy toca: seguir la práctica de "simular productivo" (dev vs prod vs
Power BI), y como prioridad, encontrar y arreglar en código el bug nuevo
de duplicados entre corridas en getOutgoingInventory.py antes de que
vuelva a aparecer en la próxima corrida diaria.
```

**Suggested title for the new chat**: `FONDA (Wansoft): Paso 21: Incremental Purchases fix, MySQL recovery, prod simulation`

---

# Permanent Rule

Regenerate this document in full (never as patches) when: the user explicitly asks, a major step closes, the conversation gets very long, context exceeds ~70%, or a new chat needs to be opened due to token limits. In that last case, also generate:
1. The handoff prompt (Section 13, first code block, if applicable).
2. The suggested title for the new chat, in the format **`FONDA (short project): Paso N[-M]: <short description>`** (same style as the user's own session list). `FONDA` is a fixed prefix; `(short project)` identifies which project (here: "Wansoft"). Use `N` = the major step/block number in progress, `-M` = sub-part suffix if the step spans multiple consecutive sessions/chats.

**Note on language:** this document, all commit messages, and all documentation pushed to GitHub in this project must be written in English — even though the working conversation with the user is in Spanish. See project memory `feedback_github_content_english_only` for the full rule.
