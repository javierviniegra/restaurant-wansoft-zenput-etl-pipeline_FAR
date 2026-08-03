# Zenput Legacy Integration Assessment

## Purpose

This document captures the assessment and controlled modernization status of the existing legacy Zenput integration.

The purpose is to understand, classify, preserve, validate, and gradually modernize the current Zenput scripts before integrating Zenput into the unified MySQL analytical layer.

The goal is not to replace working legacy scripts unnecessarily.

The goal is to bring the Zenput legacy integration into the same operational standard already applied to Purchases and Inventory:

```text
central credentials
central location mapping
clear documentation
controlled pipeline execution
JSON logging
output validation
safe governance
controlled legacy execution
```

---

## Current Assessment Status

Current status:

```text
Zenput legacy folder identified
Active files identified
Main functional scripts identified
Incremental state file identified
Database write operations detected
Target tables detected
Credential strategy reviewed
Central database connection reviewed
Zenput location mapping defined
Zenput location mapping diagnostic implemented
Zenput output validator implemented
Zenput safe pipeline wrapper implemented
Zenput validation-only mode implemented
Zenput smoke test implemented
First controlled real legacy execution completed against development database
Post-execution validation completed
Puebla location mapping added after real execution
No production database was used in this phase
```

Important rule:

```text
Zenput legacy scripts can write to MySQL and may update local state.

Real legacy execution must remain explicitly controlled through:

python -m scripts.run_zenput_pipeline --execute --allow-legacy-writes
```

---

# Project Scope Context

The primary project scope is to build a unified MySQL analytical layer that combines operational data from:

```text
Wansoft
Odoo
Zenput
future operational sources
```

The analytical layer should hide source-system complexity from end users.

Users should be able to consume consistent business data without needing to know:

```text
which branch uses Wansoft
which branch migrated to Odoo
which branch started directly in Odoo
which branch is currently Zenput-only
which source system produced each record
```

BI and reporting tools are downstream consumers.

The core project objective is:

```text
build reliable, governed, validated and auditable MySQL analytical outputs
```

---

# Current Active Legacy Folder

Current active folder:

```text
legacy/zenput/
```

Current active files:

```text
legacy/zenput/README.md
legacy/zenput/zenput_mysql_forms.py
legacy/zenput/zenput_mysql_tasks.py
legacy/zenput/last_run_timestamp.txt
legacy/zenput/__init__.py
```

Functional scripts:

```text
legacy/zenput/zenput_mysql_forms.py
legacy/zenput/zenput_mysql_tasks.py
```

State file:

```text
legacy/zenput/last_run_timestamp.txt
```

Package marker:

```text
legacy/zenput/__init__.py
```

Legacy documentation:

```text
legacy/zenput/README.md
```

---

# Legacy README Summary

The legacy README describes the module as a Crunchtime Zenput operational ETL.

The module connects to the Zenput ecosystem using REST APIs that return JSON payloads.

The README describes the module as extracting:

```text
field operations
task completions
custom form submissions
```

The README states that the module requires:

```text
ZENPUT_API_TOKEN
Zenput database credentials
root .env configuration
```

The README also states that the module connects to a Zenput MySQL database through the central database router.

---

# Current Legacy Module Scope

Based on the existing files, the module currently covers:

```text
Zenput tasks
Zenput form templates
Zenput submissions
Zenput submission answers
incremental timestamp tracking
```

Current target database context:

```text
target = zenput
```

Current integration style:

```text
REST API
JSON payloads
Python ETL
MySQL writes
local incremental state file
```

---

# File Inventory

## 1. legacy/zenput/README.md

### Type

```text
Legacy module documentation
```

### Purpose

Documents the current Zenput operational ETL module.

### Assessment

```text
Keep
Use as source reference during migration
Support with centralized docs under docs/
```

Future documentation support:

```text
docs/zenput-legacy-assessment.md
docs/zenput-runbook.md
README.md
docs/project-technical-guide.md
docs/production-orchestration-plan.md
docs/project-status-and-todo.md
docs/pipeline-logging-and-run-interpretation.md
```

---

## 2. legacy/zenput/zenput_mysql_forms.py

### Type

```text
Python legacy ETL script
```

### Detected purpose

Extracts Zenput form-related data and loads it into MySQL.

### Functional area

```text
Zenput forms
Zenput form templates
Zenput submissions
Zenput submission answers
```

### Detected input source

```text
Zenput REST API
```

### Detected endpoint concepts

```text
list_form_templates
get_submissions
```

### Detected output target

```text
MySQL target = zenput
```

### Detected MySQL objects

```text
form_templates
submissions
submission_answers
```

### Detected dependencies

```text
os
mysql.connector
numpy
pandas
requests
datetime
timedelta
json
sys
core.database.mysql.get_db_connection
core.config.company_filter.is_wansoft_company
```

### Detected credentials

The script uses:

```text
ZENPUT_API_TOKEN
```

from environment variables.

The script also includes Wansoft-style subsidiary password references:

```text
WANSOFT_PWD_<subsidiary_id>
```

These password references appear to be inherited from the local legacy subsidiary list.

### Detected branch catalog usage

The script contains an embedded `subsidiaries` list with Wansoft subsidiary IDs and branch names.

The script filters subsidiaries using:

```text
is_wansoft_company
```

### Current concern

Zenput is an operational source independent of whether a branch is currently Wansoft-source or Odoo-source for Purchases and Inventory.

Therefore, the future Zenput logic should not use:

```text
is_wansoft_company
```

as its inclusion filter.

### Current side-effect risk

The script writes to MySQL.

Detected write targets:

```text
form_templates
submissions
submission_answers
```

### Assessment classification

```text
script_name: zenput_mysql_forms.py
path: legacy/zenput/zenput_mysql_forms.py
type: Python legacy ETL
domain: Zenput forms
input_source: Zenput REST API
output_target: MySQL target zenput
uses_api: yes
uses_credentials: yes
uses_wansoft_branch_catalog: yes
uses_company_filter: yes
writes_database: yes
writes_files: not confirmed
requires_modernization: yes
priority: high
```

---

## 3. legacy/zenput/zenput_mysql_tasks.py

### Type

```text
Python legacy ETL script
```

### Detected purpose

Extracts Zenput task data and loads it into MySQL.

### Functional area

```text
Zenput tasks
task metadata
task status
assignee information
completion information
geographic coordinates
fulfillment fields
```

### Detected input source

```text
Zenput REST API
```

### Detected endpoint concept

```text
list_tasks
```

### Detected output target

```text
MySQL target = zenput
```

### Detected MySQL object

```text
zenput_tasks
```

### Detected dependencies

```text
mysql.connector
numpy
pandas
requests
datetime
timedelta
timezone
json
time
sys
os
core.database.mysql.get_db_connection
core.config.company_filter.is_wansoft_company
```

### Detected credentials

The script uses:

```text
ZENPUT_API_TOKEN
```

from environment variables.

The script also includes Wansoft-style subsidiary password references:

```text
WANSOFT_PWD_<subsidiary_id>
```

### Detected incremental state handling

The script defines:

```text
TIMESTAMP_FILE = 'last_run_timestamp.txt'
```

The script includes functions to:

```text
read last timestamp
save current timestamp
```

### Current state file

```text
legacy/zenput/last_run_timestamp.txt
```

### Current side-effect risk

The script writes to MySQL and may update the timestamp file.

Detected write targets:

```text
zenput_tasks
last_run_timestamp.txt
```

### Assessment classification

```text
script_name: zenput_mysql_tasks.py
path: legacy/zenput/zenput_mysql_tasks.py
type: Python legacy ETL
domain: Zenput tasks
input_source: Zenput REST API
output_target: MySQL target zenput
uses_api: yes
uses_credentials: yes
uses_wansoft_branch_catalog: yes
uses_company_filter: yes
uses_incremental_state: yes
writes_database: yes
writes_files: yes, last_run_timestamp.txt
requires_modernization: yes
priority: high
```

---

## 4. legacy/zenput/last_run_timestamp.txt

### Type

```text
Legacy state file
```

### Current value after controlled execution

```text
2025-10-23T18:37:33Z
```

### Format

```text
UTC ISO 8601 style timestamp
```

### Detected purpose

Stores the last successful or last processed execution timestamp for incremental extraction.

### Current finding after first controlled real execution

The value remained unchanged after the controlled real execution:

```text
before execution: 2025-10-23T18:37:33Z
after execution:  2025-10-23T18:37:33Z
```

### Current interpretation

This is not currently blocking.

The tasks script reported full synchronization of tasks during the controlled real execution.

Therefore, the timestamp file may currently be:

```text
legacy state
unused by the current full-sync path
or only used by a code path not triggered in this execution
```

### Required future review

```text
[ ] Confirm whether last_run_timestamp.txt is still used for incremental tasks extraction.
[ ] Confirm whether the current tasks ETL always performs full sync.
[ ] Decide whether to keep this file as legacy metadata.
[ ] Decide whether to migrate timestamp state to MySQL.
[ ] Decide whether pipeline logs should record timestamp before/after.
```

### Current action

```text
Preserve
Do not manually edit
Review in future safety hardening
```

---

## 5. legacy/zenput/__init__.py

### Type

```text
Python package marker
```

### Purpose

Allows `legacy/zenput` to behave as a Python package.

### Current action

```text
Keep
```

---

# Detected Tables and Targets

## Detected MySQL target

Current scripts use:

```text
get_db_connection(target="zenput")
```

This confirms that Zenput uses the existing central database connection logic.

---

## Required Zenput tables

```text
form_templates
submissions
submission_answers
zenput_tasks
```

---

## form_templates

Detected in:

```text
legacy/zenput/zenput_mysql_forms.py
```

Detected operations:

```text
CREATE TABLE IF NOT EXISTS
INSERT ... ON DUPLICATE KEY UPDATE
cursor.executemany
connection.commit
```

Risk level:

```text
Medium
```

Reason:

```text
Existing rows may be updated during each run.
```

---

## submissions

Detected in:

```text
legacy/zenput/zenput_mysql_forms.py
```

Detected operations:

```text
CREATE TABLE IF NOT EXISTS
INSERT ... ON DUPLICATE KEY UPDATE
cursor.executemany
connection.commit
```

Risk level:

```text
Medium
```

Reason:

```text
Existing rows may be updated during each run.
```

---

## submission_answers

Detected in:

```text
legacy/zenput/zenput_mysql_forms.py
```

Detected operations:

```text
CREATE TABLE IF NOT EXISTS
DELETE FROM submission_answers WHERE submission_id IN (...)
INSERT INTO submission_answers
cursor.execute
cursor.executemany
connection.commit
```

Risk level:

```text
Medium-High
```

Reason:

```text
Existing answers are deleted for processed submission_id values and then reinserted.
```

Current interpretation:

```text
This is a targeted refresh strategy for answers belonging to submissions processed during the run.
```

Required future review:

```text
[ ] Confirm that DELETE is always scoped to known processed submission_id values.
[ ] Confirm that failed reinsertion cannot leave answers missing.
[ ] Consider transactional rollback or staging strategy.
```

---

## zenput_tasks

Detected in:

```text
legacy/zenput/zenput_mysql_tasks.py
```

Detected operations:

```text
CREATE TABLE IF NOT EXISTS
INSERT ... ON DUPLICATE KEY UPDATE
cursor.executemany
connection.commit
```

Risk level:

```text
Medium
```

Reason:

```text
Existing rows may be updated during each run.
```

---

# Detected Write Operations

## CREATE TABLE

Detected:

```text
legacy/zenput/zenput_mysql_forms.py:
    CREATE TABLE IF NOT EXISTS form_templates
    CREATE TABLE IF NOT EXISTS submissions
    CREATE TABLE IF NOT EXISTS submission_answers

legacy/zenput/zenput_mysql_tasks.py:
    CREATE TABLE IF NOT EXISTS zenput_tasks
```

Interpretation:

```text
Low risk.
Creates missing tables but does not overwrite existing data.
```

---

## INSERT

Detected:

```text
legacy/zenput/zenput_mysql_forms.py:
    INSERT INTO form_templates
    INSERT INTO submissions
    INSERT INTO submission_answers

legacy/zenput/zenput_mysql_tasks.py:
    INSERT INTO zenput_tasks
```

Interpretation:

```text
Medium risk.
The scripts load new records and may update existing records through ON DUPLICATE KEY UPDATE.
```

---

## UPDATE

Detected through:

```text
ON DUPLICATE KEY UPDATE
```

Detected in:

```text
legacy/zenput/zenput_mysql_forms.py
legacy/zenput/zenput_mysql_tasks.py
```

Interpretation:

```text
Medium risk.
Existing records may be updated on each execution.
```

---

## DELETE

Detected in:

```text
legacy/zenput/zenput_mysql_forms.py
```

Specific operation:

```text
DELETE FROM submission_answers WHERE submission_id IN (...)
```

Interpretation:

```text
Medium-High risk.
The delete appears targeted by submission_id, not global.
It supports a refresh strategy for submission answers.
It must be protected with transaction handling during modernization.
```

No global destructive operation confirmed:

```text
No DROP TABLE detected
No TRUNCATE TABLE detected
No DELETE FROM <table> without filter confirmed
No REPLACE INTO detected
```

---

## UPSERT

Detected through:

```text
ON DUPLICATE KEY UPDATE
```

Detected in:

```text
form_templates
submissions
zenput_tasks
```

Interpretation:

```text
The scripts update existing rows and insert new rows.
This is a logical refresh strategy.
```

---

# Legacy Refresh Behaviour

Based on operational memory and detected SQL patterns, the Zenput legacy scripts behave like a logical refresh process.

Detected behaviour:

```text
form_templates:
    INSERT ... ON DUPLICATE KEY UPDATE

submissions:
    INSERT ... ON DUPLICATE KEY UPDATE

submission_answers:
    DELETE existing answers for processed submission_id values
    INSERT current answers again

zenput_tasks:
    INSERT ... ON DUPLICATE KEY UPDATE
```

No global table-level destructive operation has been confirmed:

```text
No DROP TABLE
No TRUNCATE TABLE
No DELETE FROM table without filter
```

Current implication:

```text
The future Zenput pipeline should preserve this refresh behaviour unless a safer staging-based strategy is explicitly designed.
```

---

# Credential and Environment Variable Review

## Current status

The Zenput legacy scripts use environment variables and the central MySQL connection helper.

Detected API credential:

```text
ZENPUT_API_TOKEN
```

Detected database routing pattern:

```text
get_db_connection(target="zenput")
```

---

## Zenput API token

The scripts use:

```text
ZENPUT_API_TOKEN
```

Current status:

```text
Used by legacy scripts
Read from .env through os.getenv
No hardcoded token detected in reviewed searches
```

Required `.env.example` pattern:

```env
# ZENPUT API
ZENPUT_API_TOKEN=
```

No real secret values should be committed.

---

## Zenput database variables

The central MySQL router supports:

```text
target = zenput
```

Detected real environment variable names:

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

The first controlled real execution was performed against development/test database configuration, not production.

---

## Current Wansoft password references

Both legacy Zenput scripts include Wansoft-style password variables inside local `subsidiaries` lists:

```text
WANSOFT_PWD_<subsidiary_id>
```

Reviewed usage:

```text
WANSOFT_PWD_* appears inside local subsidiaries lists.
No evidence was found that the password field is used outside that list in reviewed searches.
```

Current interpretation:

```text
These variables are likely inherited from the Wansoft branch configuration.
They do not appear to be required for Zenput API extraction.
```

Required modernization action:

```text
Remove WANSOFT_PWD dependencies from future Zenput company configuration if confirmed unused.
Use Zenput-specific location mapping instead.
```

---

# Branch and Company Logic

## Current legacy branch handling

Both scripts define a local `subsidiaries` list and filter it through:

```text
is_wansoft_company
```

Current concern:

```text
Zenput operational data should not depend on whether a branch is Wansoft-source or Odoo-source for Purchases and Inventory.
```

---

## Why company_filter.py should not drive Zenput

The current `company_filter.py` logic answers this question:

```text
Is this company configured as Wansoft source?
```

That is useful for some Wansoft/Odoo source decisions.

It is not an appropriate inclusion rule for Zenput.

Zenput must answer a different question:

```text
Can this Zenput location_name be mapped to a canonical company_source_key or valid Zenput-only location?
```

Therefore:

```text
Zenput should not use is_wansoft_company as its inclusion rule.
```

---

# Zenput Location Mapping Assessment

Zenput does not use the same company naming convention as Odoo or Wansoft.

The field detected in MySQL is:

```text
submissions.location_name
```

The future Zenput integration should map:

```text
Zenput location_name -> company_source_key
```

using a Zenput-specific configuration.

It should not filter locations using:

```text
is_wansoft_company
```

because Zenput is an operational source independent from whether a branch uses Wansoft or Odoo as the source for Purchases or Inventory.

---

## Central Zenput configuration

Implemented file:

```text
core/config/zenput.py
```

Purpose:

```text
Centralize Zenput location_name mapping.
Avoid duplicating local subsidiaries lists inside Zenput scripts.
Avoid using is_wansoft_company as Zenput filter.
Preserve Zenput-only operational locations.
Support future incorporation of current Zenput-only locations into Wansoft or Odoo.
```

Main mapping:

```text
ZENPUT_LOCATION_SOURCE_KEY
```

Auxiliary metadata:

```text
ZENPUT_ONLY_LOCATIONS
ZENPUT_COMPANY_WANSOFT_ID
ZENPUT_CONFIRMED_SPECIAL_MAPPINGS
```

---

## Current distinct Zenput location_name values detected after real execution

Current values detected from:

```text
submissions.location_name
```

```text
Fonda Argentina Acoxpa
Fonda Argentina Aeropuerto
Fonda Argentina Antenas
Fonda Argentina Cancun
Fonda Argentina Coyoacán
Fonda Argentina Isabel
Fonda Argentina León
Fonda Argentina Lindavista
Fonda Argentina Napoles
Fonda Argentina Oceania
Fonda Argentina Perisur
Fonda Argentina Playa
Fonda Argentina Puebla
Fonda Argentina San Jeronimo
Fonda Argentina Tepeyac
Fonda Argentina Tollocan
Fonda Argentina Vallejo
Fonda Argentina Viaducto
Taqueria Exhibimex
Taqueria Parroquia
Taqueria Viaducto
```

Current total distinct locations:

```text
21
```

---

## Confirmed Zenput location mapping

Current mapping includes:

```python
ZENPUT_LOCATION_SOURCE_KEY = {
    "Fonda Argentina Acoxpa": "Acoxpa",
    "Fonda Argentina Aeropuerto": "Aeropuerto",
    "Fonda Argentina Antenas": "Antenas",
    "Fonda Argentina Cancun": "Cancun",
    "Fonda Argentina Coyoacán": "La Esquina Coyoacán",
    "Fonda Argentina Isabel": "Isabel La Católica",
    "Fonda Argentina León": "León",
    "Fonda Argentina Lindavista": "Lindavista",
    "Fonda Argentina Napoles": "Napoles",
    "Fonda Argentina Oceania": "Oceanía",
    "Fonda Argentina Perisur": "Perisur",
    "Fonda Argentina Playa": "Playa del Carmen",
    "Fonda Argentina Puebla": "Puebla",
    "Fonda Argentina San Jerónimo": "San Jeronimo",
    "Fonda Argentina San Jeronimo": "San Jeronimo",
    "Fonda Argentina Tepeyac": "Tepeyac",
    "Fonda Argentina Tollocan": "Metepec",
    "Fonda Argentina Vallejo": "Vía Vallejo",
    "Fonda Argentina Viaducto": "Viaducto",
    "Taqueria Exhibimex": "Versalles",
    "Taqueria Parroquia": "Taquería parroquia",
    "Taqueria Viaducto": "Taquería Viaducto",
}
```

---

## Confirmed special mappings

The following mappings were explicitly confirmed:

```text
Fonda Argentina Coyoacán -> La Esquina Coyoacán
Fonda Argentina Tollocan -> Metepec
Taqueria Exhibimex -> Versalles
Fonda Argentina Puebla -> Puebla
```

---

## Confirmed Zenput-only locations

The following locations are currently Zenput-only:

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

Important future-proofing rule:

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

## Puebla handling

Puebla appeared in Zenput after the first controlled real execution:

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

---

# Zenput Validators

## Location Mapping Validator

Implemented file:

```text
scripts/validate_zenput_location_mapping.py
```

Purpose:

```text
Validate real Zenput location_name values from MySQL against core/config/zenput.py.
```

This validator is read-only.

It does not:

```text
call Zenput API
modify MySQL
update last_run_timestamp.txt
```

Current validation checks:

```text
submissions_table_exists
zenput_location_mapping_available
zenput_only_locations_classified
zenput_governance_rule_documented
```

Current post-execution result:

```text
total_validations: 4
passed: 4
failed: 0

VALIDATION RESULT: PASSED
```

---

## Output Validator

Implemented file:

```text
scripts/validate_zenput_outputs.py
```

Purpose:

```text
Validate current Zenput MySQL outputs and local legacy timestamp state.
```

This validator is read-only.

It validates:

```text
required Zenput tables exist
Zenput table counts are available
submissions.location_name mapping is valid
Zenput-only locations are classified
last_run_timestamp.txt exists and is parseable
legacy pipeline protection is documented
```

Current validation checks:

```text
required_zenput_tables_exist
zenput_table_counts_available
zenput_submissions_location_mapping
zenput_only_locations_classified
zenput_timestamp_file_valid
zenput_legacy_pipeline_protection_documented
```

Current post-execution result:

```text
total_validations: 6
passed: 6
failed: 0

VALIDATION RESULT: PASSED
```

---

# Zenput Safe Pipeline Wrapper

Implemented file:

```text
scripts/run_zenput_pipeline.py
```

Current default pipeline plan:

```text
01. Zenput location mapping validation
02. Zenput forms legacy ETL
03. Zenput tasks legacy ETL
04. Zenput output validation
```

Current modes:

```text
dry-run
validation-only
safety gate
real legacy execution with explicit approval
```

---

## Dry-run

Command:

```bash
python -m scripts.run_zenput_pipeline
```

Expected result:

```text
total_steps: 4
dry_run: 4
PIPELINE RESULT: COMPLETED
```

Meaning:

```text
The pipeline plan is valid.
No legacy scripts run.
No API calls are made.
No MySQL writes occur.
last_run_timestamp.txt is not modified.
```

---

## Validation-only execution

Command:

```bash
python -m scripts.run_zenput_pipeline --execute --validation-only
```

Expected result:

```text
total_steps: 2
success: 2
PIPELINE RESULT: COMPLETED
```

Meaning:

```text
Only read-only validators execute.
Legacy ETLs are excluded.
No MySQL writes are performed by legacy scripts.
last_run_timestamp.txt is not modified.
```

Current post-execution validation-only result:

```text
total_steps: 2
success: 2
dry_run: 0
skipped: 0
failed_or_error: 0
required_failed_or_error: 0

PIPELINE RESULT: COMPLETED
```

---

## Safety gate

Command:

```bash
python -m scripts.run_zenput_pipeline --execute
```

Expected result:

```text
PIPELINE RESULT: FAILED
```

Meaning:

```text
The pipeline blocks real execution because write-enabled legacy scripts require explicit --allow-legacy-writes.
```

This is correct behaviour.

---

## Real legacy execution

Command:

```bash
python -m scripts.run_zenput_pipeline --execute --allow-legacy-writes
```

This command may:

```text
call Zenput API
write to MySQL target zenput
insert or update form_templates
insert or update submissions
delete and reinsert submission_answers for processed submissions
insert or update zenput_tasks
possibly update legacy/zenput/last_run_timestamp.txt
```

Current status:

```text
Executed once against development/test database.
Not executed against production.
```

---

# First Controlled Real Legacy Execution

## Execution context

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

## Pre-execution snapshot

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

## Execution result

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

It proved that the validator correctly blocks completion when Zenput introduces a location not yet present in the central mapping.

---

## Follow-up correction

Added mapping:

```text
Fonda Argentina Puebla -> Puebla
```

in:

```text
core/config/zenput.py
```

After correction:

```text
python -m py_compile core\config\zenput.py
python -m scripts.validate_zenput_location_mapping
python -m scripts.validate_zenput_outputs
python -m scripts.run_zenput_pipeline --execute --validation-only
```

All passed.

---

## Post-execution snapshot

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

## Post-execution validation result

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

# Current Findings After First Controlled Real Execution

## Finding 1: Puebla appeared in Zenput

New location:

```text
Fonda Argentina Puebla
```

Action taken:

```text
Mapped to Puebla in core/config/zenput.py
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
still valid
unchanged after controlled real execution
```

Interpretation:

```text
Not currently blocking.
Requires future review.
```

Possible explanations:

```text
tasks script is running full sync
timestamp is not used by current full sync path
timestamp update function is not called
timestamp file is legacy residue
```

Recommended future action:

```text
review timestamp logic in zenput_mysql_tasks.py
document whether incremental mode is active or obsolete
```

---

## Finding 3: Legacy scripts returned success to wrapper

The wrapper correctly captured:

```text
forms legacy ETL -> SUCCESS
tasks legacy ETL -> SUCCESS
```

This execution did not show the previous `max_allowed_packet` error after database configuration recovery.

However, a previous failed attempt suggested a legacy script may print an error without returning non-zero exit code.

Recommended future action:

```text
review legacy scripts to ensure fatal errors propagate with non-zero exit code
```

Status:

```text
pending future hardening
```

---

## Finding 4: max_allowed_packet issue was environmental

The previous error:

```text
Got a packet bigger than 'max_allowed_packet' bytes
```

was resolved by correcting the local XAMPP / MariaDB environment.

Status:

```text
resolved for current execution
```

Recommended future action:

```text
document recommended max_allowed_packet for development database if the issue recurs
```

---

# Modernization Acceptance Criteria

The Zenput legacy scripts should not be replaced automatically if they already perform the required business function.

The goal is to modernize them only where needed so they follow the project standards used by Purchases and Inventory.

---

## 1. Global credentials

Required:

```text
ZENPUT_API_TOKEN
Zenput database credentials through .env
get_db_connection(target="zenput")
```

Current status:

```text
PASS
```

---

## 2. Central location mapping

Required:

```text
Zenput location_name values must map through core/config/zenput.py.
```

Current status:

```text
PASS
```

---

## 3. Documentation

Required:

```text
legacy/zenput/README.md
docs/zenput-legacy-assessment.md
docs/zenput-runbook.md
project-level documentation
```

Current status:

```text
PASS, with ongoing updates after controlled real execution
```

---

## 4. Structural quality

Current status:

```text
Legacy scripts are structurally useful.
Safe wrapper and validators are now implemented.
Further hardening is still recommended.
```

Future hardening:

```text
error propagation
timestamp handling
transaction safety
possible extraction layer
```

---

## 5. Pipeline inclusion

Required:

```text
scripts/run_zenput_pipeline.py
scripts/test_run_zenput_pipeline.py
scripts/validate_zenput_location_mapping.py
scripts/validate_zenput_outputs.py
logs/zenput_pipeline_runs/
```

Current status:

```text
PASS
```

---

# Risks and Controls

## Direct MySQL writes

Risk:

```text
Legacy scripts write to MySQL.
```

Control:

```text
Safety gate blocks real execution unless --allow-legacy-writes is passed.
```

---

## Targeted delete in submission_answers

Risk:

```text
submission_answers are deleted by submission_id and reinserted.
```

Control:

```text
Documented.
Validators run after execution.
Future transaction review pending.
```

---

## Local timestamp state

Risk:

```text
last_run_timestamp.txt may not reflect actual sync state.
```

Control:

```text
File is validated as parseable.
Future timestamp logic review pending.
```

---

## New location_name values

Risk:

```text
Zenput may introduce new locations not yet mapped.
```

Control:

```text
Location mapping validator fails when unmapped location_name appears.
```

Example found:

```text
Fonda Argentina Puebla
```

Resolution:

```text
Mapped to Puebla.
```

---

## Legacy error propagation

Risk:

```text
Legacy scripts may print errors but still return exit code 0.
```

Control:

```text
Wrapper captures subprocess return code.
Future hardening should ensure legacy scripts return non-zero on fatal errors.
```

---

# What Should Not Be Done Yet

Do not schedule this command automatically:

```bash
python -m scripts.run_zenput_pipeline --execute --allow-legacy-writes
```

without explicit operational approval.

Do not manually edit:

```text
legacy/zenput/last_run_timestamp.txt
```

without understanding timestamp behaviour.

Do not remove:

```text
León
Lindavista
Perisur
```

from Zenput mapping.

Do not treat Puebla as Zenput-only.

Do not use:

```text
is_wansoft_company
```

as Zenput inclusion logic.

---

# Recommended Modernization Direction

Future modernized structure may look like:

```text
extract/zenput/
    zenput_client.py
    zenput_forms.py
    zenput_tasks.py
    zenput_etl.py

core/config/
    zenput.py

scripts/
    run_zenput_pipeline.py
    test_run_zenput_pipeline.py
    validate_zenput_location_mapping.py
    validate_zenput_outputs.py

logs/
    zenput_pipeline_runs/

docs/
    zenput-legacy-assessment.md
    zenput-runbook.md
```

---

# Proposed Next Phases

## Phase 1: Assessment

Status:

```text
Completed
```

---

## Phase 2: Write Operation Review

Status:

```text
Completed
```

---

## Phase 3: Configuration Review

Status:

```text
Completed
```

---

## Phase 4: Safe Wrapper

Status:

```text
Completed
```

---

## Phase 5: First Controlled Legacy Real Execution

Status:

```text
Completed against development/test database
```

Outcome:

```text
Legacy scripts executed.
Database updated.
New Puebla location detected.
Mapping corrected.
Validators passed after correction.
```

---

## Phase 6: Hardening

Pending:

```text
[ ] Review timestamp behaviour.
[ ] Review error propagation from legacy scripts.
[ ] Review transaction safety around submission_answers delete/reinsert.
[ ] Consider recording row counts in run logs.
[ ] Consider splitting legacy script logic into modern extract layer.
```

---

## Phase 7: Analytical Integration

Pending:

```text
[ ] Define Zenput staging or analytical tables.
[ ] Map Zenput outputs into unified analytical layer.
[ ] Decide how Zenput-only and future incorporated locations should be represented analytically.
[ ] Define reporting-ready Zenput facts.
```

---

# Section 16 Current Status

Current status:

```text
Step 16.1 - Pre-execution snapshot completed
Step 16.2 - First controlled real execution completed against development/test database
Step 16.3 - Puebla mapping corrected and post-execution validators passed
Step 16.4 - Documentation update in progress
```

Current post-execution validated state:

```text
form_templates:       19
submissions:          1,107
submission_answers:   89,923
zenput_tasks:         1,752

distinct location_name values: 21
unmapped locations: 0

location validator: PASSED
output validator: PASSED
validation-only pipeline: COMPLETED
```

---

# Related Documentation

```text
README.md
docs/project-status-and-todo.md
docs/project-technical-guide.md
docs/production-orchestration-plan.md
docs/pipeline-logging-and-run-interpretation.md
docs/zenput-runbook.md
docs/zenput-legacy-assessment.md
```