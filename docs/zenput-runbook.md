# Zenput Runbook

## Purpose

This runbook explains how to operate, validate, troubleshoot, and safely execute the Zenput legacy integration during its modernization phase.

The current Zenput implementation is based on legacy scripts that already extract and load operational data into MySQL.

The current goal is not to replace working legacy scripts blindly.

The goal is to wrap, validate, document, and gradually modernize the Zenput integration so it follows the same operational standards already used by Purchases and Inventory:

```text
central credentials
central location mapping
safe execution
dry-run support
validation-only execution
JSON logging
read-only validation
pipeline safety gate
clear documentation
controlled legacy execution
```

---

## Current Status

Zenput is currently in controlled modernization.

Implemented:

```text
core/config/zenput.py
scripts/validate_zenput_location_mapping.py
scripts/validate_zenput_outputs.py
scripts/run_zenput_pipeline.py
scripts/test_run_zenput_pipeline.py
docs/zenput-legacy-assessment.md
docs/zenput-runbook.md
```

Existing legacy scripts:

```text
legacy/zenput/zenput_mysql_forms.py
legacy/zenput/zenput_mysql_tasks.py
```

Existing legacy state file:

```text
legacy/zenput/last_run_timestamp.txt
```

Current pipeline status:

```text
dry-run wrapper implemented
safety gate implemented
validation-only execution implemented
location mapping validation implemented
output validation implemented
JSON logging implemented
legacy write execution blocked unless explicitly allowed
first controlled real legacy execution completed against development/test database
post-execution validation completed
Puebla location mapping added after controlled execution
```

Important:

```text
The first controlled real legacy execution was performed against a development/test database.
No production database was used in that phase.
```

---

## Current Zenput Architecture

Current architecture:

```text
Zenput REST API
        ↓
legacy Zenput scripts
        ↓
MySQL target = zenput
        ↓
Zenput output tables
        ↓
location mapping validation
        ↓
output validation
        ↓
JSON pipeline logs
```

Future target architecture:

```text
Zenput REST API
        ↓
central Zenput client
        ↓
controlled extraction layer
        ↓
MySQL Zenput staging/output tables
        ↓
company_source_key mapping
        ↓
validation
        ↓
JSON run logs
        ↓
unified MySQL analytical layer
```

---

## Current Zenput Legacy Files

Current active files:

```text
legacy/zenput/README.md
legacy/zenput/zenput_mysql_forms.py
legacy/zenput/zenput_mysql_tasks.py
legacy/zenput/last_run_timestamp.txt
legacy/zenput/__init__.py
```

Functional ETL scripts:

```text
legacy/zenput/zenput_mysql_forms.py
legacy/zenput/zenput_mysql_tasks.py
```

The current legacy scripts write to MySQL and may update local state.

Therefore, they must be treated as write-enabled legacy scripts.

---

## Current Zenput Output Tables

Current required Zenput tables:

```text
form_templates
submissions
submission_answers
zenput_tasks
```

These tables are validated by:

```bash
python -m scripts.validate_zenput_outputs
```

---

## Zenput Database Target

Zenput uses the central MySQL connection helper:

```text
get_db_connection(target="zenput")
```

The target is configured in:

```text
core/database/mysql.py
```

Current Zenput database environment variables:

```text
ZENPUT_DB_HOST
ZENPUT_DB_USER
ZENPUT_DB_PASSWORD
ZENPUT_DB_NAME

ZENPUT_DB_HOST_DEV
ZENPUT_DB_USER_DEV
ZENPUT_DB_PASSWORD_DEV
ZENPUT_DB_NAME_DEV
```

Current Zenput API token:

```text
ZENPUT_API_TOKEN
```

Required `.env.example` placeholder:

```env
# ZENPUT API
ZENPUT_API_TOKEN=
```

Important:

```text
.env.example must contain placeholders only.
.env may contain real secrets and must not be committed.
```

---

# Zenput Location Mapping

Zenput location names do not always match Odoo or Wansoft company names.

The source field currently used for mapping is:

```text
submissions.location_name
```

Central mapping file:

```text
core/config/zenput.py
```

Primary mapping object:

```text
ZENPUT_LOCATION_SOURCE_KEY
```

Purpose:

```text
Map Zenput location_name values to canonical company_source_key values.
```

Important:

```text
Zenput should not use is_wansoft_company as its inclusion filter.
Zenput should not depend on COMPANY_SOURCE to decide whether a location is valid.
```

Reason:

```text
COMPANY_SOURCE governs Wansoft/Odoo source selection for Purchases and Inventory.
Zenput is a separate operational source and may include locations that are not Wansoft or Odoo yet.
```

---

## Confirmed Zenput Mappings

Confirmed special mappings:

```text
Fonda Argentina Coyoacán -> La Esquina Coyoacán
Fonda Argentina Tollocan -> Metepec
Taqueria Exhibimex -> Versalles
Fonda Argentina Puebla -> Puebla
```

Current mapping includes:

```text
Fonda Argentina Acoxpa -> Acoxpa
Fonda Argentina Aeropuerto -> Aeropuerto
Fonda Argentina Antenas -> Antenas
Fonda Argentina Cancun -> Cancun
Fonda Argentina Coyoacán -> La Esquina Coyoacán
Fonda Argentina Isabel -> Isabel La Católica
Fonda Argentina León -> León
Fonda Argentina Lindavista -> Lindavista
Fonda Argentina Napoles -> Napoles
Fonda Argentina Oceania -> Oceanía
Fonda Argentina Perisur -> Perisur
Fonda Argentina Playa -> Playa del Carmen
Fonda Argentina Puebla -> Puebla
Fonda Argentina San Jerónimo -> San Jeronimo
Fonda Argentina San Jeronimo -> San Jeronimo
Fonda Argentina Tepeyac -> Tepeyac
Fonda Argentina Tollocan -> Metepec
Fonda Argentina Vallejo -> Vía Vallejo
Fonda Argentina Viaducto -> Viaducto
Taqueria Exhibimex -> Versalles
Taqueria Parroquia -> Taquería parroquia
Taqueria Viaducto -> Taquería Viaducto
```

---

## Zenput-Only Locations

Current Zenput-only locations:

```text
León
Lindavista
Perisur
```

Meaning:

```text
They exist in Zenput.
They are valid for Zenput operational reporting.
They do not currently have Wansoft as an operational source.
They are not expected to participate in Purchases or Inventory Wansoft/Odoo pipelines.
They should not be forced into Wansoft source governance.
```

Future-proofing rule:

```text
León, Lindavista and Perisur are currently Zenput-only, but they should be modeled as locations that could be incorporated into Wansoft or Odoo in the future.
```

Therefore:

```text
Do not collapse them into another branch.
Do not remove them from Zenput mapping.
Do not assign fake Wansoft IDs.
```

---

## Puebla Handling

Puebla appeared in Zenput after the first controlled real legacy execution.

Detected Zenput value:

```text
Fonda Argentina Puebla
```

Correct mapping:

```text
Fonda Argentina Puebla -> Puebla
```

Puebla is not Zenput-only.

Reason:

```text
Puebla already exists as a company_source_key in the project.
Puebla is modeled as a future Odoo / operational branch.
Puebla should be preserved as its own canonical key.
```

Expected configuration:

```python
ZENPUT_LOCATION_SOURCE_KEY = {
    ...
    "Fonda Argentina Puebla": "Puebla",
    ...
}
```

Puebla should not be added to:

```python
ZENPUT_ONLY_LOCATIONS
```

---

# Recommended Execution Methods

## 1. Default Dry-Run

Command:

```bash
python -m scripts.run_zenput_pipeline
```

Purpose:

```text
Simulate the Zenput pipeline execution plan without executing any real action.
```

This mode:

```text
prints the execution plan
marks all steps as DRY_RUN
generates JSON run log
does not call Zenput API
does not execute legacy ETLs
does not write to MySQL
does not update last_run_timestamp.txt
```

Expected result:

```text
total_steps: 4
success: 0
dry_run: 4
skipped: 0
failed_or_error: 0
required_failed_or_error: 0

PIPELINE RESULT: COMPLETED
```

Current dry-run steps:

```text
01. Zenput location mapping validation
02. Zenput forms legacy ETL
03. Zenput tasks legacy ETL
04. Zenput output validation
```

---

## 2. Validation-Only Dry-Run

Command:

```bash
python -m scripts.run_zenput_pipeline --validation-only
```

Purpose:

```text
Simulate only the read-only validator steps.
```

Expected steps:

```text
01. Zenput location mapping validation
02. Zenput output validation
```

Expected result:

```text
total_steps: 2
dry_run: 2
PIPELINE RESULT: COMPLETED
```

---

## 3. Validation-Only Real Execution

Command:

```bash
python -m scripts.run_zenput_pipeline --execute --validation-only
```

Purpose:

```text
Run only read-only Zenput validators.
```

This mode executes:

```text
scripts.validate_zenput_location_mapping
scripts.validate_zenput_outputs
```

This mode does not execute:

```text
legacy.zenput.zenput_mysql_forms
legacy.zenput.zenput_mysql_tasks
```

This mode does not:

```text
call Zenput API
write MySQL through legacy scripts
update last_run_timestamp.txt
```

Expected result:

```text
total_steps: 2
success: 2
dry_run: 0
skipped: 0
failed_or_error: 0
required_failed_or_error: 0

PIPELINE RESULT: COMPLETED
```

This is currently the recommended safe real execution mode for Zenput.

---

## 4. Safety Gate Test

Command:

```bash
python -m scripts.run_zenput_pipeline --execute
```

Expected result:

```text
PIPELINE RESULT: FAILED
```

This failure is expected.

Reason:

```text
The command asks for real execution but does not explicitly allow write-enabled legacy steps.
```

Expected message:

```text
ERROR: Real execution includes write-enabled legacy steps.
To execute legacy Zenput ETLs, use:
    --execute --allow-legacy-writes

No steps were executed.
```

This is correct behaviour.

The safety gate protects:

```text
MySQL target zenput
legacy/zenput/last_run_timestamp.txt
existing legacy refresh behaviour
```

---

## 5. Real Legacy Execution

Command:

```bash
python -m scripts.run_zenput_pipeline --execute --allow-legacy-writes
```

Current status:

```text
Executed once against development/test database.
Not scheduled for production.
```

This command may execute:

```text
legacy.zenput.zenput_mysql_forms
legacy.zenput.zenput_mysql_tasks
```

Potential effects:

```text
calls Zenput API
writes to MySQL target zenput
inserts or updates form_templates
inserts or updates submissions
deletes and reinserts submission_answers for processed submissions
inserts or updates zenput_tasks
may update legacy/zenput/last_run_timestamp.txt
```

Before using this command, confirm:

```text
[ ] ZENPUT_API_TOKEN exists in .env.
[ ] Zenput DB credentials exist in .env.
[ ] target="zenput" connection works.
[ ] current last_run_timestamp.txt value is reviewed.
[ ] output validators pass before execution.
[ ] expected write behaviour is understood.
[ ] rollback or recovery plan is understood.
[ ] execution target is development/test unless production approval exists.
[ ] execution is approved.
```

---

# First Controlled Real Legacy Execution

## Execution Context

Execution type:

```text
controlled real legacy execution
```

Command:

```bash
python -m scripts.run_zenput_pipeline --execute --allow-legacy-writes
```

Environment:

```text
development / test database
```

Production impact:

```text
none
```

Reason:

```text
The execution was pointed to development/test Zenput database configuration.
```

---

## Pre-Execution Snapshot

Before execution:

```text
form_templates:       19
submissions:          774
submission_answers:   61,357
zenput_tasks:         1,504
```

Pre-execution dates:

```text
submissions:
    min_date: 2025-06-11 22:34:31
    max_date: 2026-05-27 23:00:27

zenput_tasks:
    min_date using last_updated: 2026-05-28 13:14:37
    max_date using last_updated: 2026-05-28 13:14:37
```

Pre-execution timestamp file:

```text
legacy/zenput/last_run_timestamp.txt
2025-10-23T18:37:33Z
```

---

## Initial Execution Result

Initial controlled real execution result:

```text
01. Zenput location mapping validation -> SUCCESS
02. Zenput forms legacy ETL -> SUCCESS
03. Zenput tasks legacy ETL -> SUCCESS
04. Zenput output validation -> FAILED
```

Pipeline result:

```text
PIPELINE RESULT: FAILED
```

Reason:

```text
Output validation detected a new unmapped location_name:
Fonda Argentina Puebla
```

This failure was correct and useful.

It proved that the validator correctly blocks final completion when Zenput introduces a location not yet present in the central mapping.

---

## Correction Applied

Added mapping:

```text
Fonda Argentina Puebla -> Puebla
```

in:

```text
core/config/zenput.py
```

Then reran:

```bash
python -m py_compile core\config\zenput.py
python -m scripts.validate_zenput_location_mapping
python -m scripts.validate_zenput_outputs
python -m scripts.run_zenput_pipeline --execute --validation-only
```

All validations passed.

---

## Post-Execution Snapshot

After execution and Puebla mapping correction:

```text
form_templates:       19
submissions:          1,107
submission_answers:   89,923
zenput_tasks:         1,752
```

Differences:

```text
form_templates:          +0
submissions:           +333
submission_answers:  +28,566
zenput_tasks:          +248
```

Interpretation:

```text
The controlled real execution updated the development/test Zenput database.
Forms and tasks legacy scripts ran.
Output validators now pass after adding Puebla mapping.
```

---

## Post-Execution Validation Result

Location mapping validator:

```text
total_validations: 4
passed: 4
failed: 0

VALIDATION RESULT: PASSED
```

Output validator:

```text
total_validations: 6
passed: 6
failed: 0

VALIDATION RESULT: PASSED
```

Validation-only wrapper:

```text
total_steps: 2
success: 2
failed_or_error: 0
required_failed_or_error: 0

PIPELINE RESULT: COMPLETED
```

---

# Zenput Pipeline Steps

## Base Pipeline Plan

Current default plan:

```text
01. Zenput location mapping validation
02. Zenput forms legacy ETL
03. Zenput tasks legacy ETL
04. Zenput output validation
```

---

## Step 01: Zenput Location Mapping Validation

Module:

```text
scripts.validate_zenput_location_mapping
```

Type:

```text
read-only
modern validator
required
```

Purpose:

```text
Validate that real submissions.location_name values are mapped through core/config/zenput.py.
```

Validates:

```text
submissions table exists
all location_name values are mapped
Zenput-only locations are classified
Zenput governance rule is documented
```

Manual command:

```bash
python -m scripts.validate_zenput_location_mapping
```

Expected result:

```text
total_validations: 4
passed: 4
failed: 0

VALIDATION RESULT: PASSED
```

---

## Step 02: Zenput Forms Legacy ETL

Module:

```text
legacy.zenput.zenput_mysql_forms
```

Type:

```text
legacy
write-enabled
required in full pipeline
```

Purpose:

```text
Extract Zenput form templates, submissions and submission answers.
```

Detected write targets:

```text
form_templates
submissions
submission_answers
```

Detected operations:

```text
CREATE TABLE IF NOT EXISTS
INSERT ... ON DUPLICATE KEY UPDATE
DELETE FROM submission_answers WHERE submission_id IN (...)
INSERT INTO submission_answers
connection.commit()
```

Risk:

```text
This step writes to MySQL.
This step should not be executed casually.
```

---

## Step 03: Zenput Tasks Legacy ETL

Module:

```text
legacy.zenput.zenput_mysql_tasks
```

Type:

```text
legacy
write-enabled
required in full pipeline
```

Purpose:

```text
Extract Zenput task data.
```

Detected write target:

```text
zenput_tasks
```

Detected local state file:

```text
legacy/zenput/last_run_timestamp.txt
```

Detected operations:

```text
CREATE TABLE IF NOT EXISTS
INSERT ... ON DUPLICATE KEY UPDATE
connection.commit()
timestamp read/write
```

Risk:

```text
This step writes to MySQL.
This step may update last_run_timestamp.txt.
This step should not be executed casually.
```

---

## Step 04: Zenput Output Validation

Module:

```text
scripts.validate_zenput_outputs
```

Type:

```text
read-only
modern validator
required final gate
```

Purpose:

```text
Validate current Zenput MySQL outputs and local legacy timestamp state.
```

Manual command:

```bash
python -m scripts.validate_zenput_outputs
```

Current validation checks:

```text
1. required_zenput_tables_exist
2. zenput_table_counts_available
3. zenput_submissions_location_mapping
4. zenput_only_locations_classified
5. zenput_timestamp_file_valid
6. zenput_legacy_pipeline_protection_documented
```

Expected result:

```text
total_validations: 6
passed: 6
failed: 0

VALIDATION RESULT: PASSED
```

---

# Zenput Smoke Test

Smoke test:

```text
scripts/test_run_zenput_pipeline.py
```

Run:

```bash
python -m scripts.test_run_zenput_pipeline
```

Current tests:

```text
default dry-run
safety gate
```

Expected result:

```text
default_dry_run: PASS
safety_gate: PASS

TEST RESULT: PASSED
```

Meaning:

```text
The default dry-run completes successfully.
The safety gate blocks unsafe real legacy execution.
```

Important:

```text
The safety gate test intentionally expects a FAILED pipeline result from --execute without --allow-legacy-writes.
That is correct behaviour.
```

---

# Pipeline Logging

Zenput pipeline logs are written to:

```text
logs/zenput_pipeline_runs/
```

Example:

```text
logs/zenput_pipeline_runs/YYYYMMDD_HHMMSS_<run_id>.json
```

Logs are local execution artefacts.

They should not be committed.

Required `.gitignore` rule:

```gitignore
# Pipeline run logs
logs/
```

Each Zenput log includes:

```text
run_id
pipeline_name
status
dry_run
execute
allow_legacy_writes
started_at
finished_at
duration_seconds
total_steps
success
dry_run_steps
skipped
failed_or_error
required_failed_or_error
steps
```

Step-level fields include:

```text
step_id
name
module
group
required
read_only
writes_database
writes_file
legacy
status
started_at
finished_at
duration_seconds
return_code
error_message
```

---

# How to Read Zenput Pipeline Results

## Dry-run completed

Expected:

```text
PIPELINE RESULT: COMPLETED
dry_run > 0
success = 0
required_failed_or_error = 0
```

Meaning:

```text
The plan is valid.
No real step executed.
No data was modified.
```

---

## Validation-only real execution completed

Expected:

```text
PIPELINE RESULT: COMPLETED
success = 2
required_failed_or_error = 0
```

Meaning:

```text
Read-only validators ran successfully.
No legacy ETL executed.
No data was modified by legacy scripts.
```

---

## Safety gate failed

Expected when running:

```bash
python -m scripts.run_zenput_pipeline --execute
```

Expected:

```text
Safety gate -> FAILED
PIPELINE RESULT: FAILED
required_failed_or_error = 1
```

Meaning:

```text
The wrapper protected the project from executing write-enabled legacy scripts without explicit permission.
```

This is a successful safety behaviour.

---

## Full legacy execution completed

Expected when explicitly approved and successful:

```text
01. Zenput location mapping validation -> SUCCESS
02. Zenput forms legacy ETL -> SUCCESS
03. Zenput tasks legacy ETL -> SUCCESS
04. Zenput output validation -> SUCCESS

PIPELINE RESULT: COMPLETED
```

If the final output validator fails, the pipeline should be treated as not fully successful even if the legacy ETLs ran.

Example:

```text
legacy forms -> SUCCESS
legacy tasks -> SUCCESS
output validation -> FAILED
PIPELINE RESULT: FAILED
```

Meaning:

```text
Data changed, but final validation blocked completion.
Investigate validation failure.
```

---

# Manual Validator Commands

## Validate location mapping

```bash
python -m scripts.validate_zenput_location_mapping
```

Use when:

```text
new location_name appears
mapping was changed
core/config/zenput.py was edited
Zenput-only classification needs review
```

---

## Validate Zenput outputs

```bash
python -m scripts.validate_zenput_outputs
```

Use when:

```text
checking Zenput tables
checking table counts
checking location mappings
checking last_run_timestamp.txt
checking pipeline protection documentation
```

---

# Controlled Execution Checklist

Before running any real legacy execution with:

```bash
python -m scripts.run_zenput_pipeline --execute --allow-legacy-writes
```

complete this checklist:

```text
[ ] Confirm current Git branch.
[ ] Confirm no uncommitted risky changes.
[ ] Confirm logs/ is ignored by Git.
[ ] Confirm execution target is development/test unless production approval exists.
[ ] Confirm ZENPUT_API_TOKEN is configured in .env.
[ ] Confirm Zenput DB credentials are configured in .env.
[ ] Confirm get_db_connection(target="zenput") works.
[ ] Run python -m scripts.run_zenput_pipeline --execute --validation-only.
[ ] Confirm validation-only passes.
[ ] Review legacy/zenput/last_run_timestamp.txt.
[ ] Capture table counts before execution.
[ ] Capture max dates before execution.
[ ] Confirm expected time window or refresh behaviour.
[ ] Confirm write targets are understood.
[ ] Confirm form_templates write behaviour is acceptable.
[ ] Confirm submissions write behaviour is acceptable.
[ ] Confirm submission_answers targeted delete/reinsert behaviour is acceptable.
[ ] Confirm zenput_tasks UPSERT behaviour is acceptable.
[ ] Confirm timestamp update behaviour is acceptable or currently under review.
[ ] Confirm execution approval.
```

---

# Post-Execution Checklist

After running:

```bash
python -m scripts.run_zenput_pipeline --execute --allow-legacy-writes
```

review:

```text
[ ] Pipeline summary.
[ ] Forms legacy ETL status.
[ ] Tasks legacy ETL status.
[ ] Output validation status.
[ ] JSON run log path.
[ ] Table counts after execution.
[ ] Submissions location mapping.
[ ] New unmapped location_name values.
[ ] Zenput-only classification.
[ ] last_run_timestamp.txt value.
[ ] Any printed legacy error messages.
[ ] Any mismatch between printed legacy errors and return code.
```

If output validation fails because of a new location:

```text
1. Review the new location_name.
2. Add correct mapping to core/config/zenput.py.
3. Do not classify it as Zenput-only unless explicitly confirmed.
4. Rerun validators.
5. Rerun validation-only pipeline.
```

---

# Current Findings After First Controlled Real Execution

## Finding 1: Puebla appeared in Zenput

Detected value:

```text
Fonda Argentina Puebla
```

Action taken:

```text
Mapped to Puebla in core/config/zenput.py.
```

Status:

```text
resolved
```

---

## Finding 2: last_run_timestamp.txt did not change

Observed value:

```text
2025-10-23T18:37:33Z
```

Status:

```text
valid
unchanged after controlled real execution
```

Interpretation:

```text
Not blocking.
Requires future review.
```

Possible explanations:

```text
tasks script is running full sync
timestamp is not used by current full-sync path
timestamp update function is not called
timestamp file is legacy residue
```

Recommended future action:

```text
review timestamp logic in zenput_mysql_tasks.py
document whether incremental mode is active or obsolete
```

---

## Finding 3: Legacy error propagation should be reviewed

A previous failed attempt showed a legacy error message related to `max_allowed_packet`.

The wrapper relies on subprocess return codes.

Recommended future action:

```text
review legacy scripts to ensure fatal errors return non-zero exit code
```

Status:

```text
pending future hardening
```

---

## Finding 4: max_allowed_packet was environmental

The previous error:

```text
Got a packet bigger than 'max_allowed_packet' bytes
```

was related to local XAMPP / MariaDB configuration.

The controlled execution later completed after the local database environment was recovered.

Recommended future action:

```text
document recommended max_allowed_packet for development database if the issue recurs
```

---

# What the Zenput Pipeline Does Not Do Yet

The Zenput pipeline currently does not:

```text
replace legacy scripts
refactor API logic
create a central Zenput API client
persist validation results to database
move timestamp state to MySQL
create canonical Zenput analytical tables
schedule automated production runs
```

These are future modernization steps.

---

# Current Known Pending Work

Pending:

```text
[ ] Review timestamp behaviour in zenput_mysql_tasks.py.
[ ] Review whether last_run_timestamp.txt is active or obsolete.
[ ] Review error propagation from legacy scripts.
[ ] Review transaction safety around submission_answers delete/reinsert.
[ ] Consider logging row counts before and after legacy execution.
[ ] Consider moving Zenput logic to extract/zenput/.
[ ] Define future Zenput analytical or canonical tables.
[ ] Review whether Zenput validation results should be persisted to database.
[ ] Update project-level status documents with first controlled real execution.
```

---

# Troubleshooting

## Validation-only fails

Run individual validators:

```bash
python -m scripts.validate_zenput_location_mapping
python -m scripts.validate_zenput_outputs
```

Review failed validation names.

Common causes:

```text
new unmapped location_name
missing Zenput table
invalid last_run_timestamp.txt format
database connection issue
```

---

## New unmapped location appears

Update:

```text
core/config/zenput.py
```

Add a mapping in:

```text
ZENPUT_LOCATION_SOURCE_KEY
```

Then rerun:

```bash
python -m scripts.validate_zenput_location_mapping
python -m scripts.validate_zenput_outputs
python -m scripts.run_zenput_pipeline --execute --validation-only
```

---

## Safety gate fails

If running:

```bash
python -m scripts.run_zenput_pipeline --execute
```

and it fails, that is expected.

Use validation-only if you want safe real execution:

```bash
python -m scripts.run_zenput_pipeline --execute --validation-only
```

Do not use:

```bash
python -m scripts.run_zenput_pipeline --execute --allow-legacy-writes
```

unless legacy writes are intentionally approved.

---

## last_run_timestamp.txt fails validation

Check:

```text
legacy/zenput/last_run_timestamp.txt
```

Expected format:

```text
YYYY-MM-DDTHH:MM:SSZ
```

Example:

```text
2025-10-23T18:37:33Z
```

Do not manually edit this file unless the operational impact is understood.

---

## max_allowed_packet error appears

Possible error:

```text
mysql.connector.errors.OperationalError: 1153 (08S01): Got a packet bigger than 'max_allowed_packet' bytes
```

Meaning:

```text
MySQL/MariaDB rejected a large packet sent by the client.
```

For XAMPP development environment, review:

```text
C:\xampp\mysql\bin\my.ini
```

and consider increasing under `[mysqld]`:

```ini
max_allowed_packet=256M
```

or, if needed:

```ini
max_allowed_packet=512M
```

After editing:

```text
restart MySQL/MariaDB
verify SHOW VARIABLES LIKE 'max_allowed_packet'
rerun validation-only
rerun controlled legacy execution if approved
```

---

# Recommended Git Handling

Logs should not be committed.

Check:

```bash
git status
```

Do not add:

```text
logs/
logs/zenput_pipeline_runs/
*.json
```

Recommended `.gitignore`:

```gitignore
# Pipeline run logs
logs/
```

---

# Related Files

```text
legacy/zenput/README.md
legacy/zenput/zenput_mysql_forms.py
legacy/zenput/zenput_mysql_tasks.py
legacy/zenput/last_run_timestamp.txt
legacy/zenput/__init__.py

core/config/zenput.py

scripts/validate_zenput_location_mapping.py
scripts/validate_zenput_outputs.py
scripts/run_zenput_pipeline.py
scripts/test_run_zenput_pipeline.py

docs/zenput-legacy-assessment.md
docs/zenput-runbook.md
```

---

# Related Documentation

```text
README.md
README_CONFIG.md
docs/project-technical-guide.md
docs/project-status-and-todo.md
docs/production-orchestration-plan.md
docs/pipeline-logging-and-run-interpretation.md
docs/inventory-runbook.md
docs/purchases-runbook.md
docs/zenput-legacy-assessment.md
```

---

# Current Status

Current Zenput modernization status:

```text
Legacy scripts assessed.
Write operations documented.
Credentials reviewed.
Central Zenput location mapping created.
Location mapping validator created and passing.
Zenput output validator created and passing.
Safe pipeline wrapper created.
Smoke test created and passing.
Validation-only execution created and passing.
First controlled real legacy execution completed against development/test database.
Puebla location mapping added.
Post-execution validators passing.
Legacy real execution remains protected by safety gate and explicit flag.
```

Current recommended safe command:

```bash
python -m scripts.run_zenput_pipeline --execute --validation-only
```

Current command requiring explicit approval:

```bash
python -m scripts.run_zenput_pipeline --execute --allow-legacy-writes
```