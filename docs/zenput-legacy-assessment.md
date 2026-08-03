# Zenput Legacy Integration Assessment

## Purpose

This document captures the assessment of the existing legacy Zenput integration.

The purpose is to understand, classify, preserve, and modernize the current Zenput scripts before integrating them into the unified MySQL analytical layer.

This document does not replace the existing legacy scripts.

The goal is not to rewrite working legacy scripts unnecessarily.

The goal is to bring the Zenput legacy integration into the same operational standard already applied to Purchases and Inventory:

```text
central credentials
central company configuration
clear documentation
controlled pipeline execution
JSON logging
output validation
safe governance
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
Zenput-only locations classified
No legacy script execution performed during assessment
Modernization criteria defined
```

Important rule:

```text
Do not execute legacy Zenput scripts until inputs, outputs, credentials, side effects and database writes are fully reviewed.
```

---

## Current Active Legacy Folder

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

## Legacy README Summary

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

## Current Legacy Module Scope

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

### Current documented scope

```text
tasks
form templates
form submissions
submission answers
last run timestamp
REST API extraction
MySQL load
```

### Assessment

```text
Keep
Modernize later
Use as source reference during migration
```

### Future documentation target

The current legacy README should be preserved, but its content should later be reflected in the centralized project documentation:

```text
docs/zenput-legacy-assessment.md
docs/zenput-runbook.md
README.md
docs/project-technical-guide.md
docs/production-orchestration-plan.md
docs/project-status-and-todo.md
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

The script creates or references:

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

### Detected branch catalog usage

The script contains an embedded `subsidiaries` list with Wansoft subsidiary IDs and branch names.

The script filters subsidiaries using:

```text
is_wansoft_company
```

### Current concern

Zenput is an operational source independent of whether a branch is currently Wansoft-source or Odoo-source for Purchases and Inventory.

Therefore, the use of:

```text
is_wansoft_company
```

must be removed or bypassed during modernization.

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

### Modernization priority

```text
High
```

### Recommended next review

```text
Identify exact table schemas
Confirm pagination or date-filter logic for submissions
Confirm whether all forms are downloaded every run
Confirm whether submissions are downloaded fully or incrementally
Confirm whether Wansoft company filter should be replaced
Confirm whether the targeted delete/reinsert logic for submission_answers is safe
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

The script creates or references:

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

### Detected branch catalog usage

The script contains an embedded `subsidiaries` list with Wansoft subsidiary IDs and branch names.

The script filters subsidiaries using:

```text
is_wansoft_company
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

The script writes to MySQL and likely updates the timestamp file.

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

### Modernization priority

```text
High
```

### Recommended next review

```text
Identify exact UPSERT behaviour
Confirm pagination logic
Confirm rate-limit handling
Confirm timestamp update moment
Confirm whether all active branches should be included
Confirm whether the Wansoft company filter should be removed or replaced
```

---

## 4. legacy/zenput/last_run_timestamp.txt

### Type

```text
Legacy state file
```

### Current value

```text
2025-10-23T18:37:33Z
```

### Format

```text
UTC ISO 8601 style timestamp
```

### Detected purpose

Stores the last successful or last processed execution timestamp for incremental extraction.

### Current concern

The state lives in a local file.

That means the execution state is:

```text
local
not centrally auditable
not naturally linked to pipeline run_id
not stored in MySQL
not stored in JSON run logs unless explicitly added later
```

### Assessment classification

```text
file_name: last_run_timestamp.txt
path: legacy/zenput/last_run_timestamp.txt
type: legacy state file
purpose: incremental extraction marker
current_value: 2025-10-23T18:37:33Z
requires_modernization: yes
priority: medium
```

### Recommended future decision

Decide whether to:

```text
keep temporarily
mirror into JSON run logs
move to MySQL control table
replace with explicit pipeline date parameters
integrate into future etl_run_log
```

### Current action

```text
Preserve
Do not modify manually
Do not overwrite during assessment
```

---

## 5. legacy/zenput/__init__.py

### Type

```text
Python package marker
```

### Purpose

Allows `legacy/zenput` to behave as a Python package.

### Assessment classification

```text
file_name: __init__.py
path: legacy/zenput/__init__.py
type: package marker
requires_modernization: no
priority: low
```

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

## Detected tables

Detected or documented tables:

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

Likely stores:

```text
form_id
title
num_submissions
date_created
date_last_submitted
creator_full_name
category_name
last_updated
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

Likely stores submission-level metadata from Zenput form responses.

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

Likely stores question / answer-level detail from each submission.

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
This is probably a targeted refresh strategy for answers belonging to submissions processed during the run.
```

Required future review:

```text
Confirm that DELETE is always scoped to known processed submission_id values.
Confirm that a failed reinsertion cannot leave answers missing.
Consider transactional rollback or staging strategy.
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

Likely stores task-level metadata, status, assignee, location, completion, and fulfillment detail.

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

and table definitions with:

```text
last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
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

## Commits

Detected:

```text
legacy/zenput/zenput_mysql_forms.py:
    connection.commit()

legacy/zenput/zenput_mysql_tasks.py:
    connection.commit()
```

No rollback detected:

```text
connection.rollback()
```

Interpretation:

```text
The scripts commit explicitly.
No rollback handling was detected in the search.
Modernization should add safer transaction handling where relevant.
```

---

# Legacy Refresh Behaviour

Based on operational memory, the Zenput legacy scripts appear to refresh or rewrite the relevant data on each execution so the MySQL Zenput tables remain updated.

The detected SQL pattern suggests a logical refresh strategy rather than a full destructive table rebuild.

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

No global table-level operation has been confirmed yet, such as:

```text
DROP TABLE
TRUNCATE TABLE
DELETE FROM <table> without filter
```

Current interpretation:

```text
The scripts update existing rows and insert new rows.
For submission_answers, the script performs a targeted delete-and-reinsert strategy by submission_id.
This provides an effective refresh behaviour for processed Zenput records.
```

Modernization implication:

```text
The future Zenput pipeline should preserve this refresh behaviour unless a safer incremental or staging-based strategy is explicitly designed.
```

Required future review:

```text
[ ] Confirm whether each execution downloads all available Zenput records or only a date-filtered or incremental subset.
[ ] Confirm whether last_run_timestamp.txt is currently used to limit task extraction.
[ ] Confirm whether forms/submissions use incremental filters or full refresh logic.
[ ] Confirm whether targeted delete/reinsert for submission_answers is sufficient and safe.
[ ] Confirm whether table row counts remain stable or grow correctly after repeated executions.
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

This is partially compliant with the project standard because API and database access are handled through environment variables and centralized routing.

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

Required action:

```text
Add ZENPUT_API_TOKEN placeholder to core/config/.env.example if not already present.
```

Recommended placeholder:

```env
# ZENPUT API
ZENPUT_API_TOKEN=
```

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

Current status:

```text
Documented in core/config/.env.example
Used by core/database/mysql.py through target="zenput"
```

No Zenput-specific port variable was confirmed during the review.

---

## Current Wansoft password references

Both legacy Zenput scripts include Wansoft-style password variables inside their local `subsidiaries` lists:

```text
WANSOFT_PWD_<subsidiary_id>
```

Reviewed usage:

```text
WANSOFT_PWD_* appears inside the local subsidiaries lists.
No evidence was found that the password field is used outside that list in the reviewed searches.
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

## Credential acceptance criteria

Zenput modernization must satisfy:

```text
[ ] No hardcoded API tokens.
[ ] No hardcoded database passwords.
[ ] ZENPUT_API_TOKEN comes from .env.
[ ] Zenput database credentials come from .env.
[ ] Zenput database connection uses central connection routing.
[ ] core/config/.env.example documents placeholders only.
[ ] No secret values are committed.
```

---

## Current compliance assessment

```text
ZENPUT_API_TOKEN from environment:
    PASS

get_db_connection(target="zenput"):
    PASS

Zenput DB variables documented in core/config/.env.example:
    PASS

ZENPUT_API_TOKEN documented in core/config/.env.example:
    pending

Hardcoded secrets:
    no evidence found in reviewed searches

WANSOFT_PWD dependency:
    legacy inheritance, not required for future Zenput mapping

Company configuration from companies.py or Zenput config:
    now partially addressed through core/config/zenput.py
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

This is now confirmed as an architecture issue.

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

## Current distinct Zenput location_name values detected

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
Fonda Argentina San Jeronimo
Fonda Argentina Tepeyac
Fonda Argentina Tollocan
Fonda Argentina Vallejo
Fonda Argentina Viaducto
Taqueria Exhibimex
Taqueria Parroquia
Taqueria Viaducto
```

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

## Confirmed Zenput location mapping

Current mapping:

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

Therefore, the configuration should preserve them as canonical keys now:

```text
León
Lindavista
Perisur
```

and not collapse them into another branch.

---

## WansoftID metadata

WansoftID is retained only as auxiliary metadata where available.

Rule:

```text
WansoftID should not be used as the only inclusion rule for Zenput.
```

Zenput-only locations currently have:

```text
wansoft_id = None
```

for:

```text
León
Lindavista
Perisur
```

---

# Zenput Location Mapping Validator

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

---

## Validation checks

The validator checks:

```text
1. submissions_table_exists
2. zenput_location_mapping_available
3. zenput_only_locations_classified
4. zenput_governance_rule_documented
```

---

## Validation result

After adding the missing San Jeronimo alias:

```text
Fonda Argentina San Jeronimo -> San Jeronimo
```

the validator passed all checks:

```text
total_validations: 4
passed: 4
failed: 0

VALIDATION RESULT: PASSED
```

This confirms:

```text
submissions table exists
all detected location_name values are mapped
León, Lindavista and Perisur are classified as Zenput-only
Zenput governance rule is documented
```

---

# Modernization Acceptance Criteria

The Zenput legacy scripts should not be replaced automatically if they already perform the required business function.

The goal is to modernize them only where needed so they follow the project standards used by Purchases and Inventory.

---

## 1. Global credentials

Zenput scripts must use environment variables and central database routing.

Required:

```text
ZENPUT_API_TOKEN
Zenput database credentials through .env
get_db_connection(target="zenput")
```

Not allowed:

```text
hardcoded API tokens
hardcoded database passwords
hardcoded connection strings
```

Current status:

```text
Mostly compliant.
ZENPUT_API_TOKEN is already read from environment variables.
get_db_connection(target="zenput") is already used.
Zenput database variables are already supported in the MySQL router.
ZENPUT_API_TOKEN should be added to core/config/.env.example.
```

---

## 2. Company configuration from central project config

Zenput scripts should not maintain duplicated branch lists inside each script.

Current legacy concern:

```text
Both scripts define local subsidiaries lists.
Both scripts filter through is_wansoft_company.
```

Future target:

```text
Zenput branch inclusion should come from core/config/zenput.py.
Zenput should not depend on whether a branch is Wansoft-source or Odoo-source.
```

Current status:

```text
core/config/zenput.py created and validated.
Legacy scripts not yet migrated to use it.
```

---

## 3. Centralized documentation

Zenput must be documented in:

```text
legacy/zenput/README.md
docs/zenput-legacy-assessment.md
README.md
```

Future documentation may include:

```text
docs/zenput-runbook.md
docs/production-orchestration-plan.md
docs/project-technical-guide.md
docs/project-status-and-todo.md
```

Current status:

```text
Partially compliant.
legacy/zenput/README.md exists.
docs/zenput-legacy-assessment.md is being maintained.
Project-level documentation still pending.
```

---

## 4. Structural quality

The current Zenput scripts appear structurally useful and should be preserved as the starting point.

The modernization should focus on:

```text
configuration cleanup
centralized location mapping
dry-run support
JSON logging
validation
pipeline orchestration
safe timestamp handling
transaction safety review
```

Avoid unnecessary rewrites if the existing extraction and load logic is correct.

Current status:

```text
Structurally useful legacy scripts.
Requires modernization wrapper and configuration cleanup.
```

---

## 5. Pipeline inclusion

Zenput must eventually be executable through a controlled pipeline.

Future expected files:

```text
scripts/run_zenput_pipeline.py
scripts/test_run_zenput_pipeline.py
scripts/validate_zenput_outputs.py
logs/zenput_pipeline_runs/
docs/zenput-runbook.md
```

Expected pipeline principles:

```text
dry-run support
real execution
JSON run logging
required validation step
controlled timestamp handling
no hidden credential usage
centralized location mapping
```

Current status:

```text
Not yet implemented.
```

---

# Modernization Philosophy

The Zenput modernization goal is not to replace working legacy scripts blindly.

The goal is to bring them into the same operational standard as the rest of the project:

```text
central configuration
central credentials
documented behavior
auditable execution
pipeline orchestration
validation gates
safe governance
```

Guiding principle:

```text
Preserve what works.
Centralize what is duplicated.
Orchestrate what is manual.
Validate before considering it reliable.
```

---

# Risks Identified

## 1. Direct MySQL writes

The legacy scripts create tables and perform upserts.

Risk:

```text
Running the scripts modifies the Zenput MySQL database.
```

Mitigation:

```text
Do not execute during assessment unless explicitly approved.
Identify all write statements first.
Create dry-run or read-only wrapper during modernization.
```

---

## 2. Targeted delete in submission_answers

Detected operation:

```text
DELETE FROM submission_answers WHERE submission_id IN (...)
```

Risk:

```text
If the process fails after deleting and before reinserting, answers for processed submissions may be temporarily missing.
```

Mitigation:

```text
Confirm transaction scope.
Add rollback where needed.
Consider staging table strategy if necessary.
```

---

## 3. Local timestamp state

The tasks script uses:

```text
last_run_timestamp.txt
```

Risk:

```text
Local state may be overwritten.
State may not match database contents.
State is not connected to run_id.
State is not centrally auditable.
```

Mitigation:

```text
Preserve temporarily.
Add logging around timestamp read/write.
Consider future MySQL state table.
```

---

## 4. Wansoft company filter dependency

Both scripts filter by:

```text
is_wansoft_company
```

Risk:

```text
Zenput extraction may exclude migrated Odoo branches, new Odoo branches, or Zenput-only locations.
```

Mitigation:

```text
Replace with Zenput-specific location mapping from core/config/zenput.py.
```

---

## 5. Encoding and historical script formatting

Some console outputs showed mojibake in branch names.

Risk:

```text
Incorrect branch labels may cause mapping issues if used as keys.
```

Mitigation:

```text
Use exact Zenput location_name values detected in MySQL.
Add explicit aliases where needed.
Use canonical company_source_key values from central configuration.
```

---

## 6. API authentication uncertainty

The tasks script comments indicate that Zenput task endpoint authentication may require either:

```text
X-API-TOKEN
```

or:

```text
Authorization: Bearer <token>
```

Risk:

```text
API calls may fail if endpoint authentication expectations differ.
```

Mitigation:

```text
Do not change until tested safely.
Create one central Zenput client.
Handle 401/403 explicitly.
```

---

## 7. Rate limiting

Legacy README indicates rate limiting handling for tasks.

Risk:

```text
Modernization must preserve HTTP 429 handling.
```

Mitigation:

```text
Review current implementation before refactoring.
Preserve retry/backoff behaviour.
```

---

# What Should Not Be Done Yet

Do not run without explicit decision:

```bash
python legacy/zenput/zenput_mysql_forms.py
python legacy/zenput/zenput_mysql_tasks.py
```

Do not manually edit:

```text
legacy/zenput/last_run_timestamp.txt
```

Do not remove:

```text
is_wansoft_company
```

from legacy scripts until replacement logic is wired safely.

Do not refactor write logic before the future pipeline has:

```text
dry-run
logging
validation
timestamp protection
```

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
    validate_zenput_outputs.py
    validate_zenput_location_mapping.py

logs/
    zenput_pipeline_runs/

docs/
    zenput-legacy-assessment.md
    zenput-runbook.md
```

---

## Future Zenput Client

A future centralized Zenput client should handle:

```text
base URL
headers
ZENPUT_API_TOKEN
HTTP errors
401 / 403 responses
429 rate limiting
pagination
JSON parsing
request logging
safe retries
```

---

## Future Zenput Pipeline

A future Zenput pipeline should support:

```text
dry-run
real execution
JSON run logging
required validation step
optional forms execution
optional tasks execution
incremental mode
full refresh mode if required
controlled timestamp handling
failure summaries
```

---

## Future Zenput Validation

A future validator should check:

```text
required tables exist
zenput_tasks row counts
form_templates row counts
submissions row counts
submission_answers row counts
latest extracted timestamp
null or missing location_name values
location_name mapping coverage
Zenput-only location preservation
API extraction completeness
controlled timestamp state
```

---

# Proposed Migration Phases

## Phase 1: Assessment

Current phase.

Tasks:

```text
identify active scripts
identify inputs
identify outputs
identify credentials
identify write operations
identify timestamp handling
identify branch filtering
document risks
```

Status:

```text
Completed
```

---

## Phase 2: Write Operation Review

Tasks completed:

```text
searched CREATE TABLE
searched INSERT
searched UPDATE
searched DELETE
searched ON DUPLICATE KEY UPDATE
searched cursor.execute
searched cursor.executemany
searched commit
searched rollback
```

Findings:

```text
CREATE TABLE detected
INSERT ... ON DUPLICATE KEY UPDATE detected
targeted DELETE for submission_answers detected
commit detected
rollback not detected
REPLACE INTO not detected
```

Status:

```text
Completed
```

---

## Phase 3: Configuration Review

Tasks completed:

```text
confirmed ZENPUT_API_TOKEN usage
confirmed target="zenput" database routing
confirmed Zenput DB variables in central MySQL router
confirmed Zenput DB variables in core/config/.env.example
confirmed WANSOFT_PWD appears only as legacy subsidiary-list inheritance
confirmed company_filter.py is not appropriate for future Zenput inclusion
created core/config/zenput.py
validated location mapping against real submissions.location_name values
```

Status:

```text
Completed
```

---

## Phase 4: Safe Wrapper

Next phase.

Tasks:

```text
create dry-run wrapper
avoid modifying last_run_timestamp during dry-run
print planned actions
confirm environment variables
confirm target database
summarize intended table writes
```

---

## Phase 5: Modern Extract Layer

Tasks:

```text
create extract/zenput/zenput_client.py
create extract/zenput/zenput_tasks.py
create extract/zenput/zenput_forms.py
move API logic out of legacy scripts where appropriate
centralize rate limiting
centralize pagination
```

---

## Phase 6: Zenput Pipeline

Tasks:

```text
create scripts/run_zenput_pipeline.py
create scripts/test_run_zenput_pipeline.py
create scripts/validate_zenput_outputs.py
add logs/zenput_pipeline_runs/
add docs/zenput-runbook.md
```

---

## Phase 7: Analytical Integration

Tasks:

```text
define Zenput staging tables
define Zenput canonical or analytical tables
map Zenput location_name to company_source_key
integrate with MySQL analytical layer
hide operational source complexity from users
```

---

# Initial Classification Table

```text
asset_name: README.md
path: legacy/zenput/README.md
type: documentation
purpose: documents Crunchtime Zenput operational ETL
input_source: none
output_target: none
uses_api: no
uses_credentials: describes them
writes_database: no
writes_files: no
requires_modernization: yes
priority: medium
```

```text
asset_name: zenput_mysql_forms.py
path: legacy/zenput/zenput_mysql_forms.py
type: Python legacy ETL
purpose: extracts Zenput form templates, submissions and answers
input_source: Zenput REST API
output_target: MySQL target zenput
uses_api: yes
uses_credentials: yes
writes_database: yes
writes_files: not confirmed
requires_modernization: yes
priority: high
```

```text
asset_name: zenput_mysql_tasks.py
path: legacy/zenput/zenput_mysql_tasks.py
type: Python legacy ETL
purpose: extracts Zenput tasks
input_source: Zenput REST API
output_target: MySQL target zenput
uses_api: yes
uses_credentials: yes
writes_database: yes
writes_files: yes, timestamp file
requires_modernization: yes
priority: high
```

```text
asset_name: last_run_timestamp.txt
path: legacy/zenput/last_run_timestamp.txt
type: state file
purpose: stores last run timestamp
current_value: 2025-10-23T18:37:33Z
input_source: Zenput task execution
output_target: local file
uses_api: no
uses_credentials: no
writes_database: no
writes_files: yes
requires_modernization: yes
priority: medium
```

```text
asset_name: __init__.py
path: legacy/zenput/__init__.py
type: Python package marker
purpose: package initialization
input_source: none
output_target: none
uses_api: no
uses_credentials: no
writes_database: no
writes_files: no
requires_modernization: no
priority: low
```

---

# Write Operation Classification Table

```text
script_name: zenput_mysql_forms.py
target: form_templates
operation: CREATE TABLE IF NOT EXISTS
method: cursor.execute
risk: low
modernization_action: keep, document schema, add validator
```

```text
script_name: zenput_mysql_forms.py
target: form_templates
operation: INSERT ... ON DUPLICATE KEY UPDATE
method: cursor.executemany
risk: medium
modernization_action: preserve refresh behaviour, add row count logging
```

```text
script_name: zenput_mysql_forms.py
target: submissions
operation: CREATE TABLE IF NOT EXISTS
method: cursor.execute
risk: low
modernization_action: keep, document schema, add validator
```

```text
script_name: zenput_mysql_forms.py
target: submissions
operation: INSERT ... ON DUPLICATE KEY UPDATE
method: cursor.executemany
risk: medium
modernization_action: preserve refresh behaviour, add row count logging
```

```text
script_name: zenput_mysql_forms.py
target: submission_answers
operation: CREATE TABLE IF NOT EXISTS
method: cursor.execute
risk: low
modernization_action: keep, document schema, add validator
```

```text
script_name: zenput_mysql_forms.py
target: submission_answers
operation: DELETE WHERE submission_id IN (...)
method: cursor.execute
risk: medium-high
modernization_action: confirm scoping, add transaction safety, consider staging
```

```text
script_name: zenput_mysql_forms.py
target: submission_answers
operation: INSERT
method: cursor.executemany
risk: medium
modernization_action: preserve refresh behaviour, add row count logging
```

```text
script_name: zenput_mysql_tasks.py
target: zenput_tasks
operation: CREATE TABLE IF NOT EXISTS
method: cursor.execute
risk: low
modernization_action: keep, document schema, add validator
```

```text
script_name: zenput_mysql_tasks.py
target: zenput_tasks
operation: INSERT ... ON DUPLICATE KEY UPDATE
method: cursor.executemany
risk: medium
modernization_action: preserve refresh behaviour, add row count logging
```

```text
script_name: zenput_mysql_tasks.py
target: last_run_timestamp.txt
operation: timestamp read/write
method: open/read/write
risk: medium
modernization_action: protect in dry-run, log before/after, consider MySQL state table
```

---

# Section 15 Current Status

Current status:

```text
Zenput legacy folder identified.
Active Zenput files identified.
Legacy README reviewed.
Forms script reviewed at high level.
Tasks script reviewed at high level.
Timestamp file reviewed.
Write operations detected.
Target tables detected.
Refresh behaviour documented.
Credential and .env usage reviewed.
Central MySQL target="zenput" confirmed.
core/config/zenput.py created.
Zenput location mapping validated against real MySQL submissions.location_name values.
Zenput-only locations confirmed.
Modernization acceptance criteria defined.
No legacy script execution performed.
```

Current active scripts:

```text
legacy/zenput/zenput_mysql_forms.py
legacy/zenput/zenput_mysql_tasks.py
```

Current state file:

```text
legacy/zenput/last_run_timestamp.txt
```

Current configuration file:

```text
core/config/zenput.py
```

Current validator:

```text
scripts/validate_zenput_location_mapping.py
```

Current next step:

```text
Paso 15.10 — Crear run_zenput_pipeline.py en modo dry-run / wrapper seguro
```

---

# Related Documentation

```text
README.md
README_CONFIG.md
docs/project-technical-guide.md
docs/project-status-and-todo.md
docs/production-orchestration-plan.md
docs/inventory-runbook.md
docs/purchases-runbook.md
docs/pipeline-logging-and-run-interpretation.md
```

---

# Recommended Commit Later

Recommended future Section 15 checkpoint commit:

```bash
git add docs/zenput-legacy-assessment.md core/config/zenput.py scripts/validate_zenput_location_mapping.py

git commit -m "feat(zenput): add location mapping config and legacy assessment"

git push
```