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
| Name | `DESKTOP-1HTRVT4` (Hyper-V VM `Analisis_BI`) | `DESKTOP-5DELBQN` (Hyper-V VM `WansoftServer`), internal `192.168.100.183` |
| Runs as | `analisisbi` | RDP administrator |
| Hosts | Scheduled tasks, `C:\Apps\Wansoft_ETL` (repo + `.venv`), backups in `C:\Backups\mysql`, MariaDB client tools in `C:\Backups\mariadb-client\mariadb-10.4.28-winx64\bin` | XAMPP MariaDB 10.4.28, phpMyAdmin |
| Does NOT host | MySQL | Any pipeline or task |

Rules:

- **Every command below runs on the tasks VM** unless it says otherwise. The VM
  reaches the database over the internal network with
  `C:\Backups\mysql\backup.cnf` (user `backup`, host `192.168.100.183`).
- Both VMs run on the Hyper-V host `SVR-HIKCENTER`; checkpoints and any
  VM-level operation are done there.
- Until cutover, the new pipeline writes **only** to `wansoft_prueba` and
  `zenput_prueba`. The VM's `core\config\.env` points there as a fail-safe.
  **Since the 2026-10-01 cutover it points at the live `wansoft` / `zenput`**
  (Section 6.1): a manual run on the VM writes to production.
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
| 1.2b | Grant the **pipeline** users access to the test databases | The pipeline does not connect as `backup`: it uses `WANSOFT_DB_USER` / `ZENPUT_DB_USER` from `.env` (`wansoftuser`, `zenputuser`), which only had rights on the live databases. On the database machine: ``GRANT ALL PRIVILEGES ON `wansoft_prueba`.* TO 'wansoftuser'@'%'; GRANT ALL PRIVILEGES ON `zenput_prueba`.* TO 'zenputuser'@'%';`` (missed at first, caught by the preflight on 2026-09-28) | Same SQL script as 1.2 |
| 1.3 | Write `backup.cnf` | `C:\Backups\mysql\backup.cnf` with `host=192.168.100.183`, the `backup` user, `compress`; ACL locked to SYSTEM and Administrators (use SIDs `*S-1-5-18`, `*S-1-5-32-544` on Spanish Windows) | Template + `icacls` in a setup script |
| 1.4 | Clone the repository | `git clone` to `C:\Apps\Wansoft_ETL` (short path: deep paths fail with "Filename too long") | Setup script |
| 1.5 | Python environment | `py -3.12 -m venv C:\Apps\Wansoft_ETL\.venv` then `.venv\Scripts\pip install -r requirements.txt` | Setup script |
| 1.6 | `.env` | Copy `core\config\.env.example` to `core\config\.env`, fill in credentials, `ENV=prod`, `WANSOFT_DB_HOST=192.168.100.183`, `WANSOFT_DB_NAME=wansoft_prueba`, `ZENPUT_DB_NAME=zenput_prueba`, `XML_DOWNLOAD_DIR=C:\Apps\Wansoft_ETL\data\xml`, lookbacks `SALES 10 / WANSOFT 5 / PURCHASES 35`; lock with `icacls` | Secrets are the one manual part; keep it manual or use a vault |
| 1.7 | Preflight | `cd C:\Apps\Wansoft_ETL; .\.venv\Scripts\python.exe -m scripts.check_env` (read-only, never prints secrets). **Every line must be `PASS`.** On 2026-09-28 it caught two real problems that were then only `WARN`s: `ZENPUT_DB_NAME` held the host IP instead of `zenput_prueba` (typo in the `.env`), and `wansoftuser` had no rights on `wansoft_prueba` (step 1.2b). Both now report `FAIL`. To inspect the `.env` without showing secrets: `Select-String -Path core\config\.env -Pattern '^(ENV\|WANSOFT_DB_(HOST\|USER\|NAME)\|ZENPUT_DB_(HOST\|USER\|NAME))='` | Already a script; run it at the start of every cycle |
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

### 5.4 First full cycle on the tasks VM (2026-09-28)

```powershell
cd C:\Apps\Wansoft_ETL; powershell -NoProfile -ExecutionPolicy Bypass -File deploy\run_daily_cycle.ps1
```

Every line goes to the screen and to `logs\daily_cycle_<yyyyMMdd>.log`. To
follow it from a second window:
`Get-Content C:\Apps\Wansoft_ETL\logs\daily_cycle_<yyyyMMdd>.log -Wait -Tail 20`.

Found on the first run, both fixed the same day:

- **The Sales stage could not save a single XML** (`No such file or directory:
  ...\data\xml/getAllOrdersByDay\...`): the subfolder existed on dev from long
  ago and nothing created it on a new machine. Every day was skipped, yet the
  stage reported `OK`. `extractAllOrdersByDay.py` now creates the folder and
  exits non-zero when no XML at all could be obtained.
- **Reading the log with `Get-Content -Wait` made the wrapper lose lines**
  (`Add-Content` reopened the file per line and collided with the reader).
  `run_daily_cycle.ps1` now keeps one shared handle open and also echoes to the
  console.

Measured 2026-09-28 on the tasks VM against the `_prueba` databases:
- Full cycle: **35.3 min, 15/15 stages OK** (the Sales stage was the silent
  failure above; slowest stage: analytics purchase pipeline, 16 min).
- Sales re-run after the fix (`-Only Ventas`): **59.2 min, 190 XML available,
  0 missing** (19 branches x 10 days). Slow only because the XML folder started
  empty and the test copy lacked Friday-Sunday, so every day was downloaded and
  several rewritten; on dev the whole cycle takes about 27 minutes. The first
  shadow run gives the steady-state timing.

Decided 2026-09-28: after cutover the pipeline does **not** keep downloading
Wansoft invoices/entries/exits for the branches migrated to Odoo (the legacy
tasks did). Their purchases and inventory come only from Odoo from their start
date; the Odoo-vs-Wansoft validation was already done.

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
2b. **Pre-cutover backup, right before migrating** (owner's decision
   2026-09-28; replaces the Wednesday backup in the original plan). With the
   legacy tasks already stopped nothing writes to production, so this is the
   exact final state and the rollback point:

   ```powershell
   & C:\Apps\Wansoft_ETL\deploy\backup\backup_mysql.ps1 -MysqlBin $bin -ConfigFile $cnf
   ```

   Check `backup.log` ends with `Backup finished`, then copy the new
   `yyyyMMdd_HHmmss` folder to `C:\Backups\mysql\PRE_CORTE_2026-10-01` (outside
   the pruning pattern, so the weekly retention never deletes it). About 30
   minutes. Do not start step 3 until it is verified.
2c. **Hyper-V checkpoints of both VMs** (owner, 2026-09-30; both VMs live on
   the same Hyper-V host). Done from the **host**, not from inside the VMs,
   after the backup of step 2b so the tasks VM checkpoint contains it:
   1. On the database machine, stop MySQL (XAMPP panel) so its disk is
      consistent; Power BI and ControlPresupuestos_AP lose the database for
      one or two minutes.
   2. On the host, in an elevated PowerShell (VM names as shown by `Get-VM`,
      which may differ from the computer names):

      ```powershell
      Get-VM | Select-Object Name, State; Checkpoint-VM -Name '<database VM>' -SnapshotName 'PRE_CORTE_2026-10-01'; Checkpoint-VM -Name '<tasks VM>' -SnapshotName 'PRE_CORTE_2026-10-01'; Get-VMSnapshot -VMName '<database VM>','<tasks VM>' | Select-Object VMName, Name, CreationTime
      ```

   3. Start MySQL again on the database machine and check that Power BI /
      the app connect.

   Rollback, if the cutover has to be undone: on the host
   `Restore-VMSnapshot -VMName '<database VM>' -Name 'PRE_CORTE_2026-10-01' -Confirm:$false`
   (and the same for the tasks VM), start both VMs, and re-enable the
   `FondaCroned_*` tasks. Minutes instead of the ~2 hours a `mysqldump` restore
   takes. **Delete both checkpoints 2-3 days after a good cutover**
   (`Remove-VMSnapshot -VMName '<vm>' -Name 'PRE_CORTE_2026-10-01'`): while they
   exist every write goes to differencing disks that grow and slow the VMs.
   Check the host's free disk before taking them.
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
3c. **Odoo start 2026-10-01 for the migrated branches** (owner, 2026-09-29):
   run `sql/migrations/cutover_04_migrated_branches_start_oct1.sql` against
   `wansoft` (expect `rows_updated_expected_5` = 5) and
   `sql/migrations/cutover_05_october_wave_relabel_wansoft_history.sql`
   (relabels the October wave's Wansoft history, about 190K lines on dev; the
   COMPANY_SOURCE flip of Isabel, San Jerónimo and Vía Vallejo is already in the
   code since commit of 2026-09-30, so step 1 only needs the Odoo check), with
   `--default-character-set=utf8mb4`. Then, **after step 4**
   (the `.env` must already point at `wansoft`), one purchases + analytics run
   with a Wansoft window reaching back before June, so the June-September
   Wansoft invoices of Acoxpa, Antenas, Tepeyac, Oceanía and Coyoacán are
   reclassified into the canonical layer and their pre-October Odoo orders drop
   out:

   ```powershell
   cd C:\Apps\Wansoft_ETL; $env:PURCHASES_LOOKBACK_DAYS = '125'; powershell -NoProfile -ExecutionPolicy Bypass -File deploy\run_daily_cycle.ps1 -Only "Purchases pipeline,Analytics purchase"; Remove-Item Env:PURCHASES_LOOKBACK_DAYS
   ```

   Never use `scripts/reload_purchase_canonical_wansoft_side.py` for this: it
   deletes the whole Wansoft side and the ETL only reloads its window, so the
   history since 2021 would be lost. Rehearsed on `wansoft_prueba` on
   2026-09-29: **21 min** (purchases 6.1 min, of which the 125-day Wansoft
   canonical load 3.2 min / 54,243 lines; analytics rebuild 14.9 min). Result
   checked per month: the 5 branches show only `wansoft` from May to
   September, Puebla `odoo` from June; the canonical validation then passes
   8/8 (it needed a date-aware fix, commit `66b7f27`, to accept migrated
   branches with no Odoo rows before their start date).
3d. **Cost history of Puebla and CentroMyJ** (found 2026-09-30): the legacy
   tasks only read Wansoft's cost report, which is zero for branches born on
   Odoo, so production holds **zeros** for their monthly, weekly and daily
   costs since they opened; the nightly cycle only rewrites the last 10 days.
   **After step 4**, one run of the three cost scripts with a long window,
   limited to those two branches (`COSTS_ONLY_BRANCHES`, read by
   `extract/costs/cost_routing.py`):

   ```powershell
   cd C:\Apps\Wansoft_ETL; $env:COSTS_LOOKBACK_DAYS = '125'; $env:COSTS_ONLY_BRANCHES = 'Puebla,CentroMyJ'; powershell -NoProfile -ExecutionPolicy Bypass -File deploy\run_daily_cycle.ps1 -Only "semana PyQ,descarga Wansoft,costo total por fecha"; Remove-Item Env:COSTS_LOOKBACK_DAYS, Env:COSTS_ONLY_BRANCHES
   ```

   Tested on dev: monthly cost in 19 s; month-end values CentroMyJ July
   978,582 / August 877,604, Puebla August 1,156,603. Odoo has no cost-of-sale
   lines for CentroMyJ in June nor for Puebla before 2026-07-27, so those days
   stay at Wansoft's zero. Do not use `-Only "Costos"`: it would also run the
   cash closing and a 125-day butchery load for every branch.
4. **Switch the `.env`:** `WANSOFT_DB_NAME=wansoft`, `ZENPUT_DB_NAME=zenput`;
   run `python -m scripts.check_env`.
5. **Enable the daily cycle:** `deploy\register_daily_cycle_task.ps1 -Enable`
   (01:30). The first production run is the night of 10-01 to 10-02; watch
   `logs\daily_cycle_<date>.log`.
6. The first automatic weekly backup runs at 18:00 that day.
6b. **External read-only users for tukanmx:** after step 3, run
   `sql/maintenance/create_tukan_readonly_users.sql` as root in phpMyAdmin with
   the two `CHANGE_ME` passwords replaced (never commit them; restrict `'%'` to
   tukanmx's IPs if they provide them). Hand over
   `docs/data-access-guide/` together with the credentials.
7. Validate the first nights (10-01 to 10-03) **against real source data and against past weeks**, not Power BI (after the cutover Power BI reads the new database itself, so comparing against it proves nothing; owner, 2026-09-30): (a) source check: sales against Wansoft's daily Z close (the Candado already reconciles it nightly), Odoo-sourced purchases against Odoo, costs against the Wansoft or Odoo cost report per branch; (b) purchases against Wansoft for every branch still entering purchases there: Wansoft-only branches (warehouse vs Wansoft) and Odoo branches still capturing in Wansoft in parallel (Odoo vs Wansoft, read live from the Wansoft API, read-only, since the pipeline no longer stores their Wansoft invoices; compare against the Costo operativo bucket); (c) coherence: per branch, daily/weekly sales, tickets, purchases and cost against the same weekdays of the previous 4 weeks, flagging zero days, doubled values and October-wave branches without Odoo purchases.

### 6.1 What actually ran on 2026-10-01 (cutover log, all steps OK)

Exact commands as executed, with measured times, so the next deployment can be
scripted from them. Machines: **host** = Hyper-V host `SVR-HIKCENTER`; **DB** =
`WansoftServer` VM (`DESKTOP-5DELBQN`, 192.168.100.183); **VM** = tasks VM
`Analisis_BI` (`DESKTOP-1HTRVT4`, user `analisisbi`); **dev** = dev PC.
In every VM block `$bin = 'C:\Backups\mariadb-client\mariadb-10.4.28-winx64\bin'`.

| # | Time | Where | Step | Result |
|---|---|---|---|---|
| 1 | early morning | VM | Disable the 12 `FondaCroned_*` (they last ran 01:00-06:30) | 12 `Disabled` |
| 2 | 09:19-09:52 | VM | `backup_mysql.ps1`, copy to `PRE_CORTE_2026-10-01` | `20261001_091949`, wansoft 3,392.6 MB in 32.2 min |
| - | morning | host | Unplanned: delete unattached VHD/AVHDX of VMs removed weeks earlier | C: free 9 → 218 GB |
| 3 | 10:30-10:32 | DB + host | MySQL stopped (XAMPP) 10:30:07, checkpoints, MySQL started 10:32:00 | 2 checkpoints, 218.2 GB still free |
| 4 | 10:35-10:42 | dev | Fresh dump of the 41 tables + 2 views | 6.75 min, 175,943,354 bytes, all 4 checks pass |
| 5.1 | ~11:00 | VM | Decompress + load into `wansoft` | 11.2 min, 63 tables + 2 views |
| 5.2 | | VM | `cutover_02_small_tables.sql` | 48 / 48 deleted, 4 keys |
| 5.3 | | VM | `cutover_03` steps A-E one by one | A 26.6 min (61,125 / 138,495 / 77,370), B identical, C 77,370 deleted, D 3.8 min, final 59 tables + 2 views |
| 5.4 | | VM | `cutover_04` | 5 rows updated |
| 5.5 | | VM | `cutover_05` | 0 relabelled (already applied on dev, so it arrived in the dump) |
| 6 | | VM | `.env` → `wansoft` / `zenput`; `check_env` | 11 passed, 0 failed (1 expected WARN: `COSTS_LOOKBACK_DAYS` uses the code default) |
| 7a | 12:23-13:12 | VM | Purchases + analytics, `PURCHASES_LOOKBACK_DAYS=125` | 49.2 min, 0 failed (purchases 5.7 min, **analytics 43.5 min**, rehearsal 14.9) |
| 7b | 13:17-13:18 | VM | Costs backfill Puebla/CentroMyJ (3 stages, 125 days) | 1.2 min, 0 failed |
| 8 | | VM | `register_daily_cycle_task.ps1 -Enable -Time 01:30` | Ready, next run 2026-10-02 01:30, AnalisisBI, Highest |
| 9 | | DB | tukanmx users as root in phpMyAdmin (host `'%'`, no IPs given yet) | 22 table grants + `zenput.*`; access test passed |
| 10 | | VM | Final review; `Wansoft_Restore_Ensayo` unregistered; temp files deleted | |

**Step 3, checkpoints (host, elevated PowerShell):**

```powershell
Checkpoint-VM -Name 'WansoftServer' -SnapshotName 'PRE_CORTE_2026-10-01'; Checkpoint-VM -Name 'Analisis_BI' -SnapshotName 'PRE_CORTE_2026-10-01'; Get-VMSnapshot -VMName 'WansoftServer','Analisis_BI' | Format-Table VMName, Name, CreationTime -AutoSize; Get-PSDrive C | Format-Table @{n='LibreGB';e={[math]::Round($_.Free/1GB,1)}}
```

Both VMs use `CheckpointType Production`. `WansoftServer` also keeps its two
checkpoints of April 2024 (merge planned for a weekend, not during a cutover:
it rewrites hundreds of GB on the same disk the database uses). Use
`Format-Table` explicitly when one PowerShell line prints several kinds of
objects, otherwise columns of the later ones are silently dropped.

**Step 4, dump (dev, Git Bash).** The object list is read from the previous
dump so it cannot drift (`grep -oE '^(CREATE TABLE|/\*!50001 VIEW) `[^`]+`'`);
on 2026-10-01 dev had 55 tables + 2 views and none created since 09-28. Checks:
`Dump completed` = 1, `DEFINER=` = 0, `CREATE TABLE` = 41, `/*!50001 VIEW` = 2,
`` `wansoft`. `` = 0. Uncompressed size 2,035,284,204 bytes. SHA256 of the
`.gz` compared on the VM after the copy (`Get-FileHash ... -eq '<hash>'`).

**Step 5, write access to `wansoft` (VM).** Account: `wansoftuser` (has `ALL` on
`wansoft`; its password is already in the VM's `.env`). A temporary option file
is generated from the `.env` without showing the secret, locked to analisisbi,
SYSTEM and Administrators, and **deleted at the end of the day**:

```powershell
$cnf='C:\Backups\mysql\wansoft_write.cnf'; $e=@{}; foreach($l in Get-Content 'C:\Apps\Wansoft_ETL\core\config\.env'){ if($l -match '^\s*(WANSOFT_DB_(HOST|PORT|USER|PASSWORD))\s*=\s*(.*)$'){ $e[$matches[1]]=$matches[3].Trim().Trim('"').Trim("'") } }; $p=$e['WANSOFT_DB_PASSWORD'].Replace('\','\\').Replace('"','\"'); $port=if($e['WANSOFT_DB_PORT']){$e['WANSOFT_DB_PORT']}else{'3306'}; [IO.File]::WriteAllText($cnf, "[client]`r`nhost=$($e['WANSOFT_DB_HOST'])`r`nport=$port`r`nuser=$($e['WANSOFT_DB_USER'])`r`npassword=`"$p`"`r`n", (New-Object Text.ASCIIEncoding)); icacls $cnf /inheritance:r /grant:r "analisisbi:F" "SYSTEM:F" "Administradores:F" | Out-Null
```

(ASCII without BOM: MariaDB's option-file parser rejects a BOM.) Decompress
with .NET (`IO.Compression.GZipStream`) and compare the length with the size
measured on dev; then:

```powershell
& "$bin\mysql.exe" --defaults-extra-file=$cnf --default-character-set=utf8mb4 --database=wansoft --execute="source C:/Backups/mysql/NUEVAS_20261001/wansoft_nuevas.sql"
```

Before part 2, check duplicates on **all four** tables that get a unique key,
not only `costeomensual_semanapyq` (expected 48 / 0 / 0 / 0); a new duplicate
would make its `ALTER` fail half-way through the file. Part 3 was run as five
separate `-e` commands copied from the file's steps A-E, checking each result.
Parts 4 and 5 with `--default-character-set=utf8mb4`. Before part 4/5, check on
dev whether they were already applied there: whatever dev has arrives with the
dump (part 5 had been, so it relabelled 0 rows).

**Step 7a, verification of the purchases switch** (by branch and month, only
`include_in_business_views = 1`): the five migrated branches show only
`wansoft` May-September and `odoo` from October (Acoxpa, Oceanía already had
October Odoo lines at 13:15); Puebla and CentroMyJ `odoo` from June; no month
with both systems. Totals after the rebuild: 801,670 lines (739,886 business),
155,074 orders, 669,831 daily rows; dev on 09-24 had 802,637 / 739,794 /
155,217.

**Step 7b, verification of the costs backfill** (`costeomensual`, month-end
`CostoTotal`): CentroMyJ July 978,581.55, August 877,603.88 (identical to dev),
September 772,434.77; Puebla July 102,389.11, August 1,156,603.26 (identical to
dev), September 816,400.38. Remaining zero days are the expected ones:
CentroMyJ June (16 days), Puebla June (25) and July 1-26 (no Odoo cost of
sales before 2026-07-27).

**Step 9, tukanmx access test (VM; the password is typed at the prompt):**

```powershell
& "$bin\mysql.exe" -h 192.168.100.183 -u tukan_wansoft -p -t --database=wansoft -e "SELECT COUNT(*) AS dias_calendario FROM dim_time; SELECT COUNT(*) FROM canonical_purchase_order_snapshot;"
```

Expected and obtained: 5,844 rows, then `ERROR 1142 ... SELECT command denied`.
Passwords were generated locally (24 alphanumeric characters) and never put in
git or in the chat.

**Step 10, final state of the VM's tasks:** 12 `FondaCroned_*` Disabled;
`Wansoft_Update_Repo_Diario` 00:30, `Wansoft_Pipeline_Diario` 01:30,
`Wansoft_Backup_MySQL_Semanal` Thursday 18:00 (first automatic run that day),
all Ready; the 4 ControlPresupuestos_AP tasks untouched (result 0);
`Wansoft_Restore_Ensayo` (one-shot of 09-25) unregistered. Deleted:
`C:\Backups\mysql\wansoft_write.cnf` and the uncompressed `wansoft_nuevas.sql`
(the `.gz` is kept). `FondaCroned_getInputInventory` shows last result
**267014** (0x41306, terminated by the user): its 01:05 run was still going
when the tasks were disabled, so Wansoft entries of 09-30 may be incomplete;
the new cycle's 5-day window reloads them.

**Rollback (if ever needed):** on the host `Restore-VMSnapshot -VMName 'WansoftServer' -Name 'PRE_CORTE_2026-10-01' -Confirm:$false` and the same
for `Analisis_BI`, start both, then re-enable `FondaCroned_*`. Alternative
without checkpoints: the `PRE_CORTE_2026-10-01` dump folder.

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

## 7b. Costs source rule (changed 2026-09-29)

Costs (`costeomensual*`, `gettotalcostbydate`) follow
`extract/costs/cost_routing.py`: a branch on Odoo takes its cost from Odoo
from its `odoo_company_migration_policy.operational_start_date` on, per day,
and from Wansoft before; branches in `COSTS_WANSOFT_TEMPORARY_EXCEPTIONS`
(`core/config/companies.py`, today **Antenas**, whose Odoo cost data is broken
by prototype-era tests) stay on Wansoft. Nothing to do at cutover: once
`COMPANY_SOURCE` flips Isabel, San Jerónimo and Vía Vallejo to Odoo, their
costs switch on 2026-10-01 and September stays on Wansoft. **Remove Antenas
from the exception set once the owner confirms its Odoo database is
repaired.** Every new branch needs its migration-policy row, or its costs stay
on Wansoft (with a warning in the log).

**Update 2026-10-02:** Isabel La Católica, San Jerónimo and Vía Vallejo were
added to the exception set. They cannot confirm purchases in Odoo until their
opening inventory balances are loaded, so Odoo had no cost for them and their
2026-10-01 cost rows were missing (sales were there). Wansoft still computes
their theoretical cost (merma and consumo come as 0). When the balances are
loaded, remove them from the set and backfill from 2026-10-01:

```powershell
cd C:\Apps\Wansoft_ETL; $env:COSTS_LOOKBACK_DAYS = '<days since 2026-10-01>'; $env:COSTS_ONLY_BRANCHES = 'Isabel La Católica,San Jeronimo,Vía Vallejo'; powershell -NoProfile -ExecutionPolicy Bypass -File deploy\run_daily_cycle.ps1 -Only "semana PyQ,descarga Wansoft,costo total por fecha"; Remove-Item Env:COSTS_LOOKBACK_DAYS, Env:COSTS_ONLY_BRANCHES
```

Consequence to expect in Power BI until it is repointed: the migrated
branches' costs in the warehouse now come from Odoo (September 1-27: within
-3% to +5% of Wansoft's Costo Teórico for Acoxpa, Tepeyac, Oceanía and
Coyoacán), while Power BI still reads Wansoft.

## 8. Security follow-ups (after cutover)

- `wansoftuser` is documented elsewhere as the dev PC's read-only credential,
  but on 2026-09-28 `SHOW GRANTS` showed `ALL PRIVILEGES ON wansoft.* ... WITH
  GRANT OPTION`, and it is also the pipeline's write account. Split it: one
  read-only user for comparisons from outside, one write user for the pipeline
  on the internal network only.
- Since the cutover (2026-10-01) the VM's `.env` points at the live `wansoft` /
  `zenput`: any manual run on the VM writes to production. To rehearse
  something on the test databases, switch those two lines back first.
- phpMyAdmin is served over plain http on a public IP: restrict it.
- `tukan_wansoft` / `tukan_zenput` were created with host `'%'` (tukanmx had
  not given IP addresses): recreate them for their IPs when known, and add TLS
  or a firewall rule for 3306.
