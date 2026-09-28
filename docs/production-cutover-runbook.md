# Production Cutover Runbook

Step-by-step procedure to put the new pipeline into production on the existing
servers, as rehearsed on the `_prueba` databases in the week of 2026-09-28 and
executed at the 2026-10-01 cutover. Each step says **where** it runs, **what**
to run, **what a good result looks like**, the **measured time**, and **how it
could be automated** later. The goal is that a future deployment (a new server,
a disaster recovery, or a second environment) replays this document instead of
rediscovering it.

Design background lives in `docs/production-orchestration-plan.md`; the
day-by-day history lives in `PROJECT_CONTEXT_REPORT.md` (Section 17).

---

## 0. Topology and ground rules

| | Tasks VM | Database machine |
|---|---|---|
| Name | `DESKTOP-1HTRVT4` (Hyper-V guest) | `DESKTOP-5DELBQN`, internal `192.168.100.183` |
| Runs as | `analisisbi` | RDP administrator |
| Hosts | Scheduled tasks, `C:\Apps\Wansoft_ETL` (repo + `.venv`), backups in `C:\Backups\mysql`, MariaDB client tools in `C:\Backups\mariadb-client\mariadb-10.4.28-winx64\bin` | XAMPP MariaDB 10.4.28, phpMyAdmin |
| Does NOT host | MySQL | Any pipeline or task |

Rules:

- **Every command below runs on the tasks VM** unless it says otherwise. The VM
  reaches the database over the internal network with
  `C:\Backups\mysql\backup.cnf` (user `backup`, host `192.168.100.183`).
- Until cutover, the new pipeline writes **only** to `wansoft_prueba` and
  `zenput_prueba`. The VM's `core\config\.env` points there as a fail-safe.
- `restore_mysql.ps1` refuses to restore onto live names (`wansoft`, `zenput`,
  `odoo`, ...). At cutover the schema/data changes are applied with the `mysql`
  client directly (Step 6), never with the restore script.
- Heavy operations (dumps, restores, large `ALTER TABLE`) slow down the database
  that Power BI and `ControlPresupuestos_AP` also use. Prefer quiet hours.
- `ControlPresupuestos_AP` (same VM, 4 tasks) is a separate project: never touch it.

Shorthand used below:

```powershell
$bin = 'C:\Backups\mariadb-client\mariadb-10.4.28-winx64\bin'
$cnf = 'C:\Backups\mysql\backup.cnf'
```

---

## 1. One-time machine preparation (done 2026-09-23 to 09-25)

| # | Step | Where / how | Automation idea |
|---|---|---|---|
| 1.1 | Install the MariaDB client tools | Unzip the official `mariadb-10.4.28-winx64.zip` to `C:\Backups\mariadb-client\` (portable, no service) | Script the download + unzip + hash check |
| 1.2 | Create the `backup` DB user | On the database machine (phpMyAdmin): `SELECT, SHOW VIEW, TRIGGER, EVENT, LOCK TABLES` on `*.*`, plus `ALL PRIVILEGES` on `wansoft_prueba` and `zenput_prueba` | Idempotent SQL script under `sql/maintenance/` |
| 1.3 | Write `backup.cnf` | `C:\Backups\mysql\backup.cnf` with `host=192.168.100.183`, the `backup` user, `compress`; ACL locked to SYSTEM and Administrators (use SIDs `*S-1-5-18`, `*S-1-5-32-544` on Spanish Windows) | Template + `icacls` in a setup script |
| 1.4 | Clone the repository | `git clone` to `C:\Apps\Wansoft_ETL` (short path: deep paths fail with "Filename too long") | Setup script |
| 1.5 | Python environment | `py -3.12 -m venv C:\Apps\Wansoft_ETL\.venv` then `.venv\Scripts\pip install -r requirements.txt` | Setup script |
| 1.6 | `.env` | Copy `core\config\.env.example` to `core\config\.env`, fill in credentials, `ENV=prod`, `WANSOFT_DB_HOST=192.168.100.183`, `WANSOFT_DB_NAME=wansoft_prueba`, `ZENPUT_DB_NAME=zenput_prueba`, `XML_DOWNLOAD_DIR=C:\Apps\Wansoft_ETL\data\xml`, lookbacks `SALES 10 / WANSOFT 5 / PURCHASES 35`; lock with `icacls` | Secrets are the one manual part; keep it manual or use a vault |
| 1.7 | Preflight | `C:\Apps\Wansoft_ETL\.venv\Scripts\python.exe -m scripts.check_env` (read-only, never prints secrets) | Already a script; run it at the start of every cycle |
| 1.8 | Daily repo update task | `deploy\register_update_task.ps1` registers `Wansoft_Update_Repo_Diario` (00:30, as `analisisbi` with its password, because Git credentials are per user) | Done |
| 1.9 | Weekly backup task | `deploy\backup\register_backup_task.ps1 -MysqlBin $bin` registers `Wansoft_Backup_MySQL_Semanal` (SYSTEM, Thursdays 18:00, keeps 4) | Done |

---

## 2. Backup (done 2026-09-24)

```powershell
& C:\Apps\Wansoft_ETL\deploy\backup\backup_mysql.ps1 -MysqlBin $bin -ConfigFile $cnf
```

Good result: `Backup finished. Kept: <yyyyMMdd_HHmmss>` in `backup.log`; every
database has a `.sql.gz` whose dump ends with `-- Dump completed`.

Measured: `wansoft` 3.38 GB compressed (26 GB of SQL) in **29.8 min** over the
internal network; the other databases in seconds.

---

## 3. Restore rehearsal into the test databases (done 2026-09-25 / 09-28)

```powershell
& C:\Apps\Wansoft_ETL\deploy\backup\restore_mysql.ps1 -BackupFolder C:\Backups\mysql\20260924_144209 -SourceDatabase wansoft -TargetDatabase wansoft_prueba -ConfigFile $cnf -MysqlBin $bin -CompareWith wansoft
& C:\Apps\Wansoft_ETL\deploy\backup\restore_mysql.ps1 -BackupFolder C:\Backups\mysql\20260924_144209 -SourceDatabase zenput  -TargetDatabase zenput_prueba  -ConfigFile $cnf -MysqlBin $bin -CompareWith zenput
```

Good result: `SAME` on tables nobody writes to; `DIFF` only on tables the
legacy tasks loaded after the backup, and there the copy has **fewer** rows than
production, by about the loads since the backup. More rows than production is a
failure.

Measured: `wansoft` 22 tables in **121.5 min** (unattended scheduled task,
22:00); `zenput` 4 tables in 0.1 min. Result 2026-09-28: 10 `SAME`, 12 `DIFF`
(all lower, one night of loads) for `wansoft`; 1 `SAME`, 3 `DIFF` for `zenput`.

Automation idea: the restore already logs to `restore_<target>.log`; a wrapper
could parse the `DIFF` lines and fail if any copy count exceeds the source.

---

## 4. Schema comparison: dev vs. production (done 2026-09-28, from the dev PC)

Compare `information_schema.tables`, `.columns` and `.statistics` of dev's
`wansoft`/`zenput` against production (read-only credentials). Result on
2026-09-28:

- `zenput`: identical, nothing to migrate.
- `wansoft`: 41 tables and 2 views exist only in dev (the whole Odoo/unified
  layer: `canonical_*`, `analytics_*`, `dim_*`, `odoo_*`, `inventory_*`,
  mapping and policy tables); 3 generated `created_date` columns; 5 unique keys
  and 1 index from `sql/maintenance/add_unique_keys_dedup_protection.sql`
  (applied to dev on 2026-09-14, never to production).
- False positives to ignore: dev's `getallordenesbyday_venta` was a 4-column
  leftover stub (dropped from dev 2026-09-28), so its `campo1`/`campo2` are not
  real missing columns.

Automation idea: turn the comparison into `scripts/compare_schema.py` that
prints tables, columns and indexes missing on either side and exits non-zero on
differences; run it before and after every migration.

---

## 5. Migration, rehearsed on `wansoft_prueba` (2026-09-28)

The migration has three parts. Parts 2 and 3 are in git
(`sql/migrations/`); part 1 is a data dump and is not.

### 5.1 Part 1: the 41 new tables and 2 views, with dev's data

Why copy data and not just create empty tables: dimensions, the approved
product-mapping dictionary, `odoo_company_migration_policy` and other catalogs
are not rebuilt by any daily stage, and the Wansoft side of the canonical
purchase tables is incremental (35 days), so empty tables would lose history.
Dev holds exactly the state that was validated against Power BI.

On the **dev PC** (Git Bash), dump the dev-only objects, stripping `DEFINER`
from the views (the `backup` user has no `SUPER`) and gzip:

```bash
mysqldump -u root --single-transaction --quick --hex-blob --default-character-set=utf8mb4 \
  wansoft <the 41 tables and 2 views> \
  | sed -E 's#/\*!50013 DEFINER=`[^`]+`@`[^`]+` SQL SECURITY DEFINER \*/#/*!50013 SQL SECURITY INVOKER */#; s#DEFINER=`[^`]+`@`[^`]+` ##g' \
  | gzip -6 > NUEVAS_<yyyyMMdd>/wansoft_nuevas.sql.gz
```

Checks before shipping: the dump ends with `-- Dump completed`; 0 `DEFINER=`
left; 41 `CREATE TABLE`; no `` `wansoft`. `` qualified references (otherwise the
views would read production instead of the target database).

Measured: 5.7 min to dump, **176 MB** compressed.

Copy the file to the VM as `C:\Backups\mysql\NUEVAS_<yyyyMMdd>\wansoft_nuevas.sql.gz`
(folder name outside the backup pruning pattern `yyyyMMdd_HHmmss`), then:

```powershell
& C:\Apps\Wansoft_ETL\deploy\backup\restore_mysql.ps1 -BackupFolder C:\Backups\mysql\NUEVAS_20260928 -SourceDatabase wansoft_nuevas -TargetDatabase wansoft_prueba -ConfigFile $cnf -MysqlBin $bin
```

The dump only drops/creates its own 43 objects; the existing 22 tables are not
touched. Good result: `Restored 65 tables into wansoft_prueba`.
Measured: **11.6 min**.

At cutover the target is the live `wansoft`, which the restore script refuses
on purpose; load the same file with the client instead (Step 6.3).

### 5.2 Part 2: `sql/migrations/cutover_02_small_tables.sql`

Drops the old Sales backup tables (`getallordenesbyday_venta`,
`_detalleventa`, `_modificador`) and the empty `getallordenesbyday_new_pagos`;
removes the 48 duplicate captures in `costeomensual_semanapyq` (2025-05-06..08,
the zero-valued earlier row of each pair; the later, real row is kept); adds the
three `created_date` generated columns with their unique keys and the
`getglobalcashclosing` unique key.

```powershell
& "$bin\mysql.exe" --defaults-extra-file=$cnf -t --database=wansoft_prueba --execute="source C:/Apps/Wansoft_ETL/sql/migrations/cutover_02_small_tables.sql"
```

Good result: `rows_to_delete_expected_48` = 48, `rows_deleted` = 48, and a final
list of 4 unique keys (`non_unique` = 0). Re-check the duplicate count right
before running it on production: new duplicates may have appeared.

Measured 2026-09-28 on `wansoft_prueba`: seconds; 48 found, 48 deleted, 4
unique keys created.

### 5.3 Part 3: `sql/migrations/cutover_03_large_inventory_tables.sql`

**Required before the first pipeline run:** `getOutgoingInventory.py` upserts
against the unique key `uq_subsidiary_fecha_idsalida`. Production's copy of
`getoutgoinginventory_salida` holds exact duplicate rows (the legacy loader's
bulk reloads), so the key cannot be added until they are removed. Run the file's
steps **one at a time**, checking each result:

| Step | What | Good result | Measured on `wansoft_prueba` 2026-09-28 |
|---|---|---|---|
| A | Materialise duplicate groups and rows into `tmp_salida_dup_*` (two full scans) | Counts reported | 25.6 min; 61,125 groups, 138,495 rows (a plain `GROUP BY` count alone took 31.4 min) |
| B | Read-only: are the duplicates exact copies? | `identical` = `dup_groups`; otherwise **stop** | Seconds; 61,125 of 61,125 identical. Copies came from three bulk reloads (2025-04, 2026-02, 2026-07), none in 2026-08/09, so the number is not growing nightly |
| C | Delete the surplus copies by primary key, keeping the lowest `id` | deleted = `SUM(n - 1)` | Seconds; 77,370 deleted |
| D | `ADD INDEX idx_identrada_subsidiary` on `getinputinventory_entrada`, `ADD UNIQUE KEY uq_subsidiary_fecha_idsalida` on `getoutgoinginventory_salida` (`ALGORITHM=INPLACE, LOCK=NONE`) | 2 rows, `non_unique` 1 and 0 | 4.8 min for both, online |
| E | Drop the helper tables | | |

At cutover the counts will differ slightly (production has had more nights of
loads); what must hold is B = all identical and C = `SUM(n - 1)`. Nothing may
write to the table between A and D, so run it after the legacy tasks are
disabled. Budget about 35 minutes for the whole part (A dominates).

---

## 6. Cutover day (Thursday 2026-10-01)

Order matters. Detailed business checks are in `PROJECT_CONTEXT_REPORT.md`,
Section 17.6.

1. **Odoo readiness:** confirm confirmed (`purchase`/`done`) Odoo orders exist
   for Isabel La Católica, San Jerónimo and Vía Vallejo; flip `COMPANY_SOURCE`
   and `ROLLOUT_COMPANY_EXPECTATIONS` in `core/config/companies.py` plus the
   migration-policy seed; commit and push, then `git -C C:\Apps\Wansoft_ETL pull --ff-only` on the VM.
2. **Stop the legacy tasks:** disable the 12 `FondaCroned_*` tasks (delete them
   after one or two good nights). Leave `ControlPresupuestos_AP`, the backup
   task and the system tasks alone.
3. **Migrate the live `wansoft`:** fresh dump from dev (Step 5.1, new date),
   loaded with the client, then parts 2 and 3:

   ```powershell
   # decompress wansoft_nuevas.sql.gz first (restore_mysql.ps1 does this internally)
   & "$bin\mysql.exe" --defaults-extra-file=<cnf with write access to wansoft> --default-character-set=utf8mb4 --database=wansoft --execute="source C:/Backups/mysql/NUEVAS_20261001/wansoft_nuevas.sql"
   & "$bin\mysql.exe" --defaults-extra-file=<same cnf> -t --database=wansoft --execute="source C:/Apps/Wansoft_ETL/sql/migrations/cutover_02_small_tables.sql"
   & "$bin\mysql.exe" --defaults-extra-file=<same cnf> -t --database=wansoft --execute="source C:/Apps/Wansoft_ETL/sql/migrations/cutover_03_large_inventory_tables.sql"
   ```

   The `backup` user only has write access to the `_prueba` databases; use an
   account with `ALL` on `wansoft` for this step (decide which on the day).
4. **Switch the `.env`:** `WANSOFT_DB_NAME=wansoft`, `ZENPUT_DB_NAME=zenput`;
   run `python -m scripts.check_env`.
5. **Enable the daily cycle:** `deploy\register_daily_cycle_task.ps1 -Enable`
   (01:30). The first production run is the night of 10-01 to 10-02; watch
   `logs\daily_cycle_<date>.log`.
6. The first automatic weekly backup runs at 18:00 that day.
7. Re-validate against Power BI for the 10 Odoo-sourced branches over 10-01 to 10-03.

---

## 7. Toward full automation

What is already automated: repo update (00:30), weekly backup with retention,
unattended restore with row-count comparison, the run-once daily cycle
(01:30), `.env` preflight.

What this runbook still does by hand, in priority order:

1. **Schema comparison** (Step 4) → `scripts/compare_schema.py`, exit code on drift.
2. **Numbered migrations with a ledger:** a `schema_migrations` table in each
   database and a small runner that applies `sql/migrations/*.sql` in order and
   records what ran, so a new environment is brought up by one command instead
   of this list.
3. **Reference-data export/import** (Step 5.1) → a script that dumps the
   non-rebuildable tables from a named source and loads them into a named
   target, with the checks listed above built in.
4. **Restore verification** (Step 3) → fail automatically when a copy has more
   rows than its source.
5. **Secrets** (Step 1.6) stay manual until there is a vault.
