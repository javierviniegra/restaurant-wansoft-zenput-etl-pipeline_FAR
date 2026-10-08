# Wansoft + Odoo + Zenput Data Warehouse & ETL Pipeline

Python ETL, source governance and orchestration that load **Wansoft** (POS, costs,
Wansoft-side purchases and inventory), **Odoo** (purchases, inventory and costs of the
branches that migrated to it) and **Zenput** (operational checklists and tasks) into one
MariaDB/MySQL warehouse. Consumers read a single set of tables and never need to know
which system a branch uses, when it migrated, or which source produced each row.

Odoo is read-only for this project: nothing here writes to Odoo.

> **Current state (2026-10-07):** in production since **2026-10-01**. The nightly task
> `Wansoft_Pipeline_Diario` runs at **01:30** on the tasks VM, **16 stages, about 40 minutes**,
> writing to the live `wansoft` and `zenput` databases. The legacy `FondaCroned_*` tasks are
> disabled. Full history, decisions and the open backlog are in
> [`PROJECT_CONTEXT_REPORT.md`](PROJECT_CONTEXT_REPORT.md) (start with Section 13 "NOW / NEXT").

---

## Contents

1. [Machines](#1-machines)
2. [Source governance: which system feeds what](#2-source-governance-which-system-feeds-what)
3. [The nightly cycle](#3-the-nightly-cycle)
4. [Read-only checks](#4-read-only-checks)
5. [Main tables](#5-main-tables)
6. [Business rules worth knowing](#6-business-rules-worth-knowing)
7. [Configuration (`.env`)](#7-configuration-env)
8. [Running things by hand](#8-running-things-by-hand)
9. [Repository structure](#9-repository-structure)
10. [Documentation map](#10-documentation-map)
11. [Conventions](#11-conventions)

---

## 1. Machines

| | Dev PC | Tasks VM | Database machine |
|---|---|---|---|
| Name | owner's workstation | `DESKTOP-1HTRVT4` (Hyper-V `Analisis_BI`), user `analisisbi` | `DESKTOP-5DELBQN` (Hyper-V `WansoftServer`), `192.168.100.183` |
| Runs | development, read-only checks against production | every scheduled task, `C:\Apps\Wansoft_ETL` (`.venv`, Python 3.12), backups in `C:\Backups\mysql` | XAMPP MariaDB 10.4.28 (`wansoft`, `zenput`, `odoo`, `presupuestos_ap`...), phpMyAdmin |
| Database | local XAMPP MariaDB 10.4.32 (not a Windows service; start it from the XAMPP panel) | **none** | the production databases |

Both production machines are VMs on the Hyper-V host `SVR-HIKCENTER`.

**Rules:**
- The tasks VM's `.env` points at the **live** databases (`WANSOFT_DB_NAME=wansoft`,
  `ZENPUT_DB_NAME=zenput`). **Any manual run on the VM writes to production.** Check before
  running anything:
  `Select-String -Path core\config\.env -Pattern '^(ENV|WANSOFT_DB_(HOST|USER|NAME)|ZENPUT_DB_(HOST|USER|NAME))='`
- From the dev PC, production is queried **read-only** (SELECT only).
- The tasks of the separate projects `ControlPresupuestos_AP` and Central de Reportes, which
  share these machines, are not touched from this project.
- Each machine has its own `core/config/.env` (gitignored). The VM's is the only copy of its
  settings.

---

## 2. Source governance: which system feeds what

All routing lives in [`core/config/companies.py`](core/config/companies.py) and the table
`odoo_company_migration_policy` (start date per Odoo company).

| Domain | Source |
|---|---|
| Sales, payments, cash closings, waiters | **Wansoft, always**, every branch |
| Purchases, inventory | `COMPANY_SOURCE`: Wansoft, or Odoo from the branch's `operational_start_date` (Wansoft history before it) |
| Costs | per branch and per day, `extract/costs/cost_routing.py` (below) |
| Checklists, tasks | Zenput, mapped by `core/config/zenput.py` (`location_name` -> branch) |

### The 19 branches

| Branch | Wansoft id | Purchases / inventory | Costs |
|---|---|---|---|
| Acoxpa | 5320 | Odoo from 2026-10-01 | Odoo from 2026-10-01 |
| Tepeyac | 6560 | Odoo from 2026-10-01 | Odoo from 2026-10-01 |
| Oceanía | 5943 | Odoo from 2026-10-01 | Odoo from 2026-10-01 |
| La Esquina Coyoacán | 12057 | Odoo from 2026-10-01 | Odoo from 2026-10-01 |
| Antenas | 4960 | Odoo from 2026-10-01 | **Wansoft** (temporary exception: its Odoo cost data is broken) |
| Isabel La Católica | 4958 | Odoo from 2026-10-01 | Wansoft until the automatic switch |
| San Jerónimo | 5319 | Odoo from 2026-10-01 | Wansoft until the automatic switch |
| Vía Vallejo | 5318 | Odoo from 2026-10-01 | Wansoft until the automatic switch |
| Puebla | 12806 | Odoo from 2026-06-10 (born on Odoo) | Odoo from its opening (Odoo has cost of sales from 2026-07-27) |
| CentroMyJ | 12802 | Odoo from 2026-06-01 (born on Odoo) | Odoo from its opening (Odoo has cost of sales from July 2026) |
| Aeropuerto, Taquería Parroquia, Viaducto, Taquería Viaducto, Playa del Carmen, Cancún, Nápoles, Metepec (Tollocan), Versalles | 4959, 5321, 4961, 4962, 6174, 6175, 4433, 4752, 5396 | Wansoft | Wansoft |

- **Migrated branches** (Acoxpa, Antenas, Tepeyac, Oceanía, Coyoacán) read Odoo only from
  2026-10-01; their earlier months come from Wansoft, where they captured in parallel.
- **October wave** (Isabel, San Jerónimo, Vía Vallejo) went live on Odoo on 2026-10-01 as a
  fresh start. Their costs stay on Wansoft until Odoo has cost of sales for them; the nightly
  stage "Costos - cambio automático a Odoo" then switches each one by itself (first of two
  consecutive days with Odoo cost > 0 and within 0.5x-2x of Wansoft), records it in
  `costs_odoo_switch`, backfills and validates. Nobody edits code.
- **Nápoles** is a franchise and will never operate on Odoo.
- **Internal providers** `EL BODEGON DE FITO` and `LAS EMPANADAS DE MARIA EVA` are suppliers,
  not branches: their own buying is excluded, but purchases *from* them by a branch count.
- **Out of scope:** `TACOS FA FUENTES` (no longer part of the group), excluded everywhere.
- **Zenput-only locations:** León, Lindavista, Perisur (no Wansoft/Odoo data).

The current cost routing is also published as data, every night, in
`costs_source_by_company` (one row per branch: first day on Odoo costs or NULL, and why),
which Central de Reportes reads instead of copying the rule.

---

## 3. The nightly cycle

`deploy/run_daily_cycle.ps1` -> `python -m scripts.run_daily_cycle` runs every stage once,
in order, **continues after a failed stage**, and exits 1 if any stage failed. The log is
`logs\daily_cycle_<yyyyMMdd>.log` (unbuffered, UTF-8), ending in a summary and
`##### CYCLE DONE in N min, K failed`.

| # | Stage | What it does |
|---|---|---|
| 1 | Ventas (Candado real) | Wansoft tickets by day (XML), validated against **all** cash closings of the day; re-downloads any day that does not match |
| 2 | Inventario - entradas | Wansoft inventory entries (Wansoft branches) |
| 3 | Inventario - salidas | Wansoft inventory exits |
| 4 | Costos - semana PyQ | week-to-date costs (`costeomensual_semanapyq`), Wansoft or Odoo per routing |
| 5 | Costos - descarga Wansoft | month-to-date costs (`costeomensual`) |
| 6 | Costos - cierre global de caja | cash closings (`getglobalcashclosing`) |
| 7 | Compras - facturas/gastos | Wansoft invoices/expenses (`getexpenses_factura`) |
| 8 | Costos - tablajería | butchery report (Wansoft branches only; being phased out) |
| 9 | Costos - costo total por fecha | daily cost (`gettotalcostbydate`) |
| 10 | Costos - cambio automático a Odoo | automatic cost switch, publishes `costs_source_by_company`, validates duplicates and continuity of every Odoo-costed branch |
| 11 | Zenput - forms | checklists and answers |
| 12 | Zenput - tasks | tasks |
| 13 | Inventory pipeline | Odoo inventory snapshots, scope, validation |
| 14 | Purchases pipeline | Odoo snapshots (confirmed orders, receipts), canonical layer merging Wansoft history and Odoo, rollout validation |
| 15 | Analytics purchase pipeline | rebuilds `dim_vendor` / `dim_product`, then the `analytics_purchase_*` tables and their validators |
| 16 | Odoo cutover validation | T+7 / T+30 checkpoints of every branch's Odoo start |

Conditional stages, appended at the end:
- **Sundays:** "Product mapping backlog (weekly)" (product mapping dictionary).
- **Every 5 days** (calendar rhythm, `date.toordinal() % 5 == 0`; e.g. 2026-10-11, 10-16):
  "Compras por clasificar (cada 5 dias)": rewrites `purchase_catalog_review_backlog`, writes
  `reports/purchase_catalog_review/compras_por_clasificar_YYYYMMDD.csv`, prints `[AVISO]` when
  unclassified purchases exceed `PURCHASE_CATALOG_MAX_SHARE` (2%) of the month or something is
  pending more than `PURCHASE_CATALOG_MAX_DAYS` (15). It never fails the cycle.

**Reload windows** (each night re-reads these days backwards, so late changes at the source
are picked up): sales 10 days, other Wansoft reports 5, costs and butchery 10, Wansoft
purchases 35. Odoo purchase snapshots are full reloads. Odoo-sourced costs use the current
month plus the previous month until the 10th (customer invoicing keeps completing for ~2 weeks).

**Timeouts:** every source call is bounded (Wansoft 60 s connect / 600 s per call, Odoo
600 s, Zenput 120 s). A timed-out call skips that branch/day only; the reload windows retry
it the next night. The Task Scheduler limit for the whole task is 4 hours.

**Scheduled tasks on the tasks VM:**

| Task | When | What |
|---|---|---|
| `Wansoft_Update_Repo_Diario` | daily 00:30 | `git pull --ff-only` (`deploy/update_repo.ps1`) |
| `Wansoft_Pipeline_Diario` | daily 01:30 | the nightly cycle |
| `Wansoft_Backup_MySQL_Semanal` | Thursdays 18:00 | full backup of the 7 databases over the internal network, keeps 4 (`deploy/backup/`) |

How to verify a night, re-run a missed night or a single stage: runbook Section 9
([`docs/production-cutover-runbook.md`](docs/production-cutover-runbook.md)).

---

## 4. Read-only checks

All of these only SELECT and read from the sources. Run them from the project root. The
reconciliation scripts always connect with `WANSOFT_DB_*` (the production warehouse), never
the `*_DEV` variables, so they give the same answer from the dev PC or the tasks VM.

| Command | Checks |
|---|---|
| `python -m scripts.check_env` | `.env` preflight: every variable present, every database reachable by its user. Never prints secrets. Run before any manual run |
| `python -m scripts.reconcile_sources [--from D] [--to D] [--only ...]` | warehouse vs live sources, per branch and day. Sections: `ventas` (tickets vs cash closings), `cierres`, `compras` (Wansoft invoices and entries), `costos` (vs the source in `costs_source_by_company`, plus continuity), `zenput`, `negocio` (business views vs canonical). Default: the last 7 days. Exit 1 on a real difference |
| `python -m scripts.check_odoo_vs_warehouse [--from D] [--to D]` | Odoo confirmed purchase lines and validated receipts vs the nightly snapshots, applying the same start-date policy as the ETL; labels `AFTER_DOWNLOAD` (expected) vs `MISSING` / `EXTRA` (real) |
| `python -m extract.costs.cost_switch --prod [--branches ...]` | what the automatic cost-switch rule decides today for each October-wave branch |

---

## 5. Main tables

Database `wansoft` unless noted. Column-level detail, joins and example queries are in the
data access guide ([`docs/data-access-guide/`](docs/data-access-guide/)).

| Area | Tables |
|---|---|
| Sales | `getallordenesbyday_new_venta` (+ `_detalleventa`, `_pago`, `_modificador`), `getglobalcashclosing` |
| Costs | `costeomensual` (month to date), `costeomensual_semanapyq` (week to date, through the day before `created_date`), `gettotalcostbydate` (single day); `costs_source_by_company`, `costs_odoo_switch` |
| Purchases (business-ready) | `analytics_purchase_order_lines`, `analytics_purchase_orders`, `analytics_purchase_daily_company_product`; read with `include_in_business_views = 1` |
| Purchases (governance) | `purchase_catalog_review_backlog`, `dim_vendor`, `dim_product`, `inventory_mapping_dictionary`, `odoo_company_migration_policy` |
| Purchases (Wansoft raw) | `getexpenses_factura` (also non-goods spend by `Cuenta`), `getinputinventory_entrada` |
| Inventory | `getoutgoinginventory_salida`, `analytics_inventory_*`, Odoo snapshots |
| Pipeline control | `odoo_cutover_validation_log` |
| Zenput (database `zenput`) | `form_templates`, `submissions`, `submission_answers`, `zenput_tasks` |

`analytics_purchase_order_lines.catalog_status` tells how well a line is classified:
`catalogado`, `producto_por_clasificar`, `producto_sin_catalogo`, `proveedor_sin_catalogo`,
`proveedor_y_producto_sin_catalogo`. All of them count in the business views (see 6).

Intermediate layers (`canonical_purchase_*`, `odoo_purchase_*`, `stg_*`, `inventory_*`
workbench tables, `vw_inventory_*`) are not for consumers.

---

## 6. Business rules worth knowing

- **Sales:** a day is correct when its tickets equal the SUM of Wansoft's cash closings of
  that operating day (several shifts) or the LARGEST one (a full close that includes an
  earlier partial one). Closings made after midnight load the next night.
- **Purchases timing:** an Odoo purchase counts once its order is **confirmed**, from the night
  after confirmation, under its **order date**; drafts/RFQs never count. A Wansoft purchase
  counts when the **invoice** is captured. The two can differ for the same goods: El Bodegón
  (central kitchen) invoices late, so Odoo branches can show more purchases than Wansoft for
  recent days. Compare Odoo against Wansoft's `Cuenta = 'Costo operativo'` only.
- **Unclassified purchases (owner's option 1, from the night of 2026-10-07 to 10-08):** lines
  whose vendor or product is missing from the catalogs, or only pending classification,
  **count** in business views, flagged by `catalog_status`. Only deliberate exclusions
  (`dim_product.is_excluded`, not-for-business products) and internal-provider buying
  companies stay out. `dim_vendor` / `dim_product` are rebuilt every night; products still
  need a person to approve their mapping (reviewed every 5 days, stage above).
- **Costs:** Odoo costs fill `CostoTotal`, `CostoDeProductosVendidos` and `CostoDeMerma`;
  Wansoft-only columns are NULL on Odoo rows. Courtesies and cancellations come from the cash
  closing (sale value) for every branch. Month/week-to-date stay whole across a mid-period
  switch (Wansoft days + Odoo days, each day once).
- **Recent costs are incomplete for a while:** Odoo's cost follows customer invoicing (40-70%
  at +1 day, all by the month-end closing). Wansoft can keep inventory deductions pending
  (`CostoIdealDeProductosPendientesDeRebaja`) and recalculates days later. Both are rewritten
  nightly while inside their windows.

---

## 7. Configuration (`.env`)

`core/config/.env` (gitignored). `ENV=dev` makes the pipelines use the `*_DEV` database
variables; on the tasks VM `ENV` is production. Never commit real values.

| Group | Variables |
|---|---|
| Databases | `WANSOFT_DB_HOST/PORT/USER/PASSWORD/NAME` (+ `_DEV`), `ZENPUT_DB_HOST/USER/PASSWORD/NAME` (+ `_DEV`) |
| Wansoft | `WANSOFT_PWD_<subsidiary id>` (one per branch), `WANSOFT_USE_LOCAL_WSDL`, `XML_DOWNLOAD_DIR` (+ `_DEV`) |
| Odoo | `ODOO_URL`, `ODOO_DB_NAME`, `ODOO_USER`, `ODOO_PASSWORD` |
| Zenput | `ZENPUT_API_TOKEN` |
| Reload windows | `SALES_LOOKBACK_DAYS` (10), `WANSOFT_LOOKBACK_DAYS` (5 in production), `PURCHASES_LOOKBACK_DAYS` (35), `COSTS_LOOKBACK_DAYS` (10, code default) |
| Timeouts | `WANSOFT_CONNECT_TIMEOUT_SECONDS` (60), `WANSOFT_OPERATION_TIMEOUT_SECONDS` (600), `ODOO_TIMEOUT_SECONDS` (600) |
| Purchases | `PURCHASE_ETL_MIN_ORDER_DATE`, `PURCHASE_ETL_MIN_RECEIPT_DATE`, `PURCHASE_ETL_ALLOWED_MAPPING_STATUS` |
| Catalog review | `PURCHASE_CATALOG_MAX_SHARE` (0.02), `PURCHASE_CATALOG_MAX_DAYS` (15) |
| One-off runs | `COSTS_ONLY_BRANCHES` (limit the cost stages to some branches, used by backfills) |
| Inventory analysis | `INVENTORY_ETL_*`, `INVENTORY_SCOPE_*`, `INVENTORY_NOT_FOUND_*` |

---

## 8. Running things by hand

On the tasks VM every command below writes to **production** (Section 1). Check `.env` first.

```powershell
# The whole cycle, or some stages (name fragments), with the same logging as the nightly task
powershell -NoProfile -ExecutionPolicy Bypass -File deploy\run_daily_cycle.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File deploy\run_daily_cycle.ps1 -Only "Ventas"

# List the stages that would run today
.venv\Scripts\python.exe -m scripts.run_daily_cycle --list
```

Domain pipelines on their own: `python -m scripts.run_purchases_pipeline`,
`python -m scripts.run_inventory_pipeline`, `python -m scripts.run_zenput_pipeline` (Zenput
legacy writes need `--allow-legacy-writes`). Cost backfills for a few branches:
`COSTS_ONLY_BRANCHES` plus a longer `COSTS_LOOKBACK_DAYS` (runbook 7b).

---

## 9. Repository structure

```text
core/            config (companies.py, zenput.py, lookback.py, .env), Wansoft/Odoo clients, DB helpers
extract/         per-domain extractors: costs (cost_routing, cost_switch, odoo_cost_report), purchases,
                 inventory, products, sales, zenput
legacy/          the original Wansoft and Zenput download scripts, still the nightly stages 1-12
  wansoft/automaticos/          Candado (sales), inventory, expenses, weekly/daily costs, butchery
  wansoft/descargarCostoWansoft/ monthly costs, cash closing
  zenput/                       forms and tasks
  _archive/                     retired scripts, not run
pipelines/       scheduler.py (stage list) and jobs/ (one job per stage)
scripts/         run_daily_cycle.py, domain pipelines, build_* (analytics/dims), validate_*,
                 read-only checks (check_env, reconcile_sources, check_odoo_vs_warehouse)
analysis/        product/inventory mapping and classification workbench
sql/             migrations/ (cutover parts 2-5), maintenance/ (keys, tukan users, verification queries)
deploy/          run_daily_cycle.ps1, update_repo.ps1, task registration; backup/ (backup, restore)
docs/            runbooks, design documents, data access guide, history/
resources/wsdl/  local Wansoft WSDL
logs/, reports/  generated, gitignored
```

---

## 10. Documentation map

| Document | Use it for |
|---|---|
| [`PROJECT_CONTEXT_REPORT.md`](PROJECT_CONTEXT_REPORT.md) | full history, decisions, bug log, current backlog (Section 13) |
| [`docs/production-cutover-runbook.md`](docs/production-cutover-runbook.md) | deployment, cutover as executed, cost routing (7b), **post-cutover operations** (Section 9) |
| [`docs/data-access-guide/`](docs/data-access-guide/) | for consumers (tukanmx, analysts): tables, joins, golden rules; Spanish and English, Markdown/HTML/PDF |
| [`legacy/wansoft/automaticos/README.md`](legacy/wansoft/automaticos/README.md) | the Wansoft download scripts: Candado, cost routing, windows, timeouts |
| [`docs/analytics-expense-invoices-design.md`](docs/analytics-expense-invoices-design.md) | next domain: expenses (Wansoft invoices + Odoo vendor bills) |
| [`docs/power-bi-source-migration.md`](docs/power-bi-source-migration.md) | Power BI repoint of purchases/inventory |
| `docs/purchases-*.md`, `docs/inventory-*.md`, `docs/zenput-*.md` | domain runbooks and policies |
| `docs/analytics-*-design.md`, `docs/dim-*-design.md` | design of each analytics table and dimension |
| `docs/pipeline-logging-and-run-interpretation.md`, `docs/branch-rollout-playbook.md` | reading pipeline logs; onboarding a branch to Odoo |
| [`docs/history/readme-archive-2026-10-07.md`](docs/history/readme-archive-2026-10-07.md) | the previous README with the full build history |

`docs/project-status-and-todo.md`, `docs/production-orchestration-plan.md` and
`docs/unified-analytical-layer-plan.md` are planning documents from August 2026; the current
state and backlog are in the context report.

---

## 11. Conventions

- Odoo is read-only. The ETL never writes to Odoo.
- The repository is public: no secrets, no business data. `.env`, `logs/` and `reports/` are
  gitignored.
- Commit messages and documents pushed to GitHub are in English.
- Every source call has a timeout; every stage reports OK/FAILED; validators fail loudly.
- Changes that affect production are confirmed with the owner first.
