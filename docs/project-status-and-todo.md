# Project Status and TODO

## Purpose

This document explains the current status of the Wansoft + Odoo + Zenput Data Warehouse and ETL Pipeline project.

It answers three practical questions:

```text
Where are we now?
What has already been completed?
What is still pending?
```

This document should be used as the main project checkpoint before continuing with additional orchestration, Zenput modernization, production scheduling, unified analytical consumption, or future branch/source rollouts.

---

## Project Scope

The primary scope of this project is to build a unified MySQL analytical layer that combines operational data from:

```text
Wansoft
Odoo
Zenput
future operational sources
```

The analytical layer should hide source-system complexity from end users.

Users should be able to consume consistent business data without needing to know:

```text
which branch still uses Wansoft
which branch migrated from Wansoft to Odoo
which branch started directly in Odoo
which branch is Zenput-only
which data is historical
which data is current
which source system produced each record
```

The project is not primarily a Power BI project.

BI and reporting tools, including Power BI, Excel, dashboards, SQL notebooks, APIs or other reporting layers, are downstream consumers of the MySQL analytical layer.

The core project objective is:

```text
build reliable, governed, validated and auditable MySQL analytical outputs
```

---

## Current Project Phase

The project is currently between:

```text
validated domain orchestration
```

and:

```text
controlled analytical consumption and production readiness
```

The project is no longer in early discovery.

The following foundations are already in place:

```text
Odoo read-only extraction
Wansoft source integration strategy
Wansoft local WSDL setup
MySQL governance layer
inventory dictionary governance
company source governance
purchase canonical layer
purchase orchestration pipeline
purchase canonical validation
inventory orchestration pipeline
inventory output validation
Zenput legacy assessment
Zenput central location mapping
Zenput safe pipeline wrapper
Zenput read-only validators
Zenput first controlled real legacy execution against development/test database
JSON pipeline logging
branch rollout validation
technical documentation package
```

The next major project stage is:

```text
controlled analytical consumption and production-readiness decisions
```

This means:

```text
keep Purchases pipeline stable
keep Inventory pipeline stable
keep Zenput legacy execution controlled
continue Zenput hardening carefully
prepare unified analytical consumption
decide whether database run-log tables are needed
decide whether validation results should be persisted
keep manual governance decisions controlled
```

---

## Current Overall Status

| Area | Status |
|---|---|
| Sales | Functionally established |
| Purchases | Pipeline implemented, validated and logged |
| Inventory | Pipeline implemented, validated and logged |
| Zenput | Legacy assessed, safe wrapper implemented, first controlled real execution completed against development/test database |
| Wansoft SOAP/WSDL | Local WSDL setup documented |
| Purchases rollout validation | Implemented |
| Inventory output validation | Implemented |
| Zenput location mapping validation | Implemented |
| Zenput output validation | Implemented |
| JSON pipeline logging | Implemented for Purchases, Inventory and Zenput |
| Branch rollout playbook | Created |
| Pipeline log interpretation | Created |
| Production scheduling | Pending |
| Unified analytical consumption layer | Pending |
| Database run log tables | Pending |
| Validation result persistence | Pending |

---

# Completed Work

## 1. Repository Architecture

Completed:

```text
core/
analysis/
extract/
legacy/
scripts/
docs/
sql/
resources/wsdl/
logs/
```

The project now has a structured repository layout separating:

```text
database clients
source clients
configuration
analysis scripts
ETL modules
legacy integrations
test runners
SQL seeds and maintenance scripts
documentation
WSDL resources
local pipeline logs
```

---

## 2. Odoo Read-Only Principle

Completed:

```text
Odoo is treated as a read-only source.
ETLs do not update Odoo.
Catalog governance decisions are stored in MySQL.
```

Current rule:

```text
No ETL should write back to Odoo products, inventory quantities, company data, catalog references, accounting records, or operational records.
```

---

## 3. MySQL Governance and Analytical Layer

Completed:

```text
MySQL stores dictionaries, snapshots, canonical tables, backlogs, lifecycle outputs, company policies, Zenput outputs and validation-ready analytical data.
```

Main governance and analytical objects include:

```text
inventory_mapping_dictionary
inventory_product_lifecycle
odoo_inventory_scope_classification
odoo_inventory_snapshot
odoo_inventory_backlog
odoo_company_migration_policy
odoo_purchase_inventory_mapping_backlog
canonical_purchase_order_snapshot
canonical_purchase_order_line_snapshot
canonical_purchase_receipt_snapshot
canonical_purchase_receipt_move_snapshot
form_templates
submissions
submission_answers
zenput_tasks
```

Future governance objects may include:

```text
etl_run_log
etl_validation_result
```

---

## 4. Source Governance

Completed:

```text
core/config/companies.py
COMPANY_SOURCE
Odoo company-source mapping
Wansoft subsidiary-source mapping
internal provider handling
```

Current source rules:

```text
Sales      -> always Wansoft
Purchases  -> COMPANY_SOURCE
Inventory  -> COMPANY_SOURCE
Zenput     -> Zenput-specific location mapping
```

Important validated rule:

```text
operational_start_date only applies when COMPANY_SOURCE = 'odoo'
```

Zenput does not use `COMPANY_SOURCE` as its inclusion filter.

Zenput uses:

```text
core/config/zenput.py
```

to map:

```text
submissions.location_name -> company_source_key
```

---

## 5. Wansoft Subsidiary Mapping

Completed:

```text
WANSOFT_SUBSIDIARY_SOURCE_KEY is derived from CUENTAS_SUCURSALES.
```

Validated examples:

```text
4960 -> Antenas
6175 -> Cancun
5320 -> Acoxpa
6560 -> Tepeyac
5943 -> Oceanía
12806 -> Puebla
```

This avoids maintaining a second manual Wansoft subsidiary mapping.

---

## 6. Internal Provider Handling

Completed:

```text
EL BODEGON DE FITO
LAS EMPANADAS DE MARIA EVA
```

are treated as:

```text
internal providers
```

and not as final operating branches.

Rules:

```text
Exclude as company_name.
Keep as vendor_name if the buying company is final-eligible.
```

---

## 7. Inventory Domain

Completed or advanced:

```text
Odoo inventory extraction
inventory scope classification
dictionary lookup
snapshot generation
backlog generation
not_found analysis
bridge report pattern
controlled promotion pattern
inventory lifecycle support
inventory closeout documentation
inventory runbook
inventory pipeline orchestration
inventory output validation
inventory JSON logging
optional bridge reports
```

Previously validated baseline:

```text
snapshot rows: 1660
residual functional not_found: 98 unique products
residual functional pending_review: 5 unique products
```

Current status:

```text
Inventory is technically stable.
Inventory is orchestrated.
Inventory has required output validation.
Inventory has JSON logging.
Inventory optional bridge reports are validated.
Inventory dictionary promotions remain excluded from default automation.
```

---

## 8. Purchases Domain

Completed:

```text
Odoo purchase order extraction
Odoo purchase order line extraction
Odoo purchase receipt extraction
Odoo purchase receipt move extraction
purchase product mapping
purchase inventory backlog
company migration policy
company source eligibility report
Odoo canonical purchase load
Wansoft canonical purchase load
canonical purchase tables
source_system coexistence
controlled purchases pipeline
JSON run logging
canonical validation
rollout company pattern validation
```

Current validated Odoo canonical load:

```text
orders:        882
lines:         4771
receipts:      876
receipt_moves: 4763
```

Current validated Wansoft canonical load:

```text
orders:        145015
lines:         745161
receipts:      145015
receipt_moves: 745161
```

Current Wansoft status summary:

```text
final_wansoft_enabled        690000
wansoft_history_before_odoo   55161
```

---

## 9. Zenput Domain

Zenput is now included as a controlled modernization domain.

Current status:

```text
Legacy scripts assessed.
Write operations documented.
Credentials reviewed.
Central location mapping created.
Location mapping validated.
Output validation implemented.
Safe pipeline wrapper implemented.
Dry-run implemented.
Validation-only execution implemented.
Safety gate implemented.
JSON logging implemented.
First controlled real legacy execution completed against development/test database.
Puebla location mapping added.
Post-execution validators passing.
Legacy real execution remains protected for non-development or unapproved use.
```

Current legacy files:

```text
legacy/zenput/README.md
legacy/zenput/zenput_mysql_forms.py
legacy/zenput/zenput_mysql_tasks.py
legacy/zenput/last_run_timestamp.txt
legacy/zenput/__init__.py
```

Current modern files:

```text
core/config/zenput.py
scripts/validate_zenput_location_mapping.py
scripts/validate_zenput_outputs.py
scripts/run_zenput_pipeline.py
scripts/test_run_zenput_pipeline.py
docs/zenput-legacy-assessment.md
docs/zenput-runbook.md
```

Current Zenput output tables:

```text
form_templates
submissions
submission_answers
zenput_tasks
```

Current log folder:

```text
logs/zenput_pipeline_runs/
```

Logs are local execution artefacts and should not be committed.

---

# Section 13 Status: Purchases Orchestration, Logging and Rollout Validation

Section 13 focused on moving the Purchases domain from individually validated scripts to a controlled orchestration workflow.

Current status:

```text
Purchases orchestration pipeline implemented
Purchases pipeline dry-run validated
Purchases pipeline real execution validated
Canonical purchases validation implemented
Canonical purchases validation integrated as required pipeline step
JSON run logging implemented
Rollout company pattern validation implemented
Branch rollout playbook created
Pipeline log interpretation document created
Production orchestration plan updated
Purchases runbook updated
Purchases canonical layer documentation updated
Purchases company migration policy updated
Project technical guide updated
README updated
Project status and TODO updated
README_CONFIG reviewed and updated
```

Implemented files:

```text
scripts/run_purchases_pipeline.py
scripts/test_run_purchases_pipeline.py
scripts/validate_purchases_canonical_layer.py
docs/pipeline-logging-and-run-interpretation.md
docs/branch-rollout-playbook.md
```

Current Purchases pipeline status:

```text
total_steps: 10
required validation integrated: yes
JSON logging integrated: yes
rollout validation integrated: yes
current result: passing
```

---

# Section 14 Status: Inventory Pipeline Orchestration, Logging and Output Validation

Section 14 focused on moving the Inventory domain from individually validated scripts to a controlled orchestration workflow equivalent to the Purchases pipeline.

Current status:

```text
Inventory orchestration pipeline implemented
Inventory pipeline dry-run validated
Inventory pipeline smoke test validated
Inventory pipeline real execution validated
Inventory JSON run logging implemented
Inventory output validation implemented
Inventory output validation integrated as required pipeline step
Inventory optional bridge reports validated
Inventory dictionary promotions explicitly excluded from default automation
Inventory runbook updated
Production orchestration plan updated with Inventory pipeline status
Project status and TODO updated
Project technical guide updated
README updated
```

Implemented files:

```text
scripts/run_inventory_pipeline.py
scripts/test_run_inventory_pipeline.py
scripts/validate_inventory_outputs.py
docs/inventory-runbook.md
docs/production-orchestration-plan.md
docs/project-status-and-todo.md
docs/project-technical-guide.md
README.md
```

Current Inventory pipeline log folder:

```text
logs/inventory_pipeline_runs/
```

Logs are local execution artefacts and should not be committed.

Required `.gitignore` rule:

```gitignore
# Pipeline run logs
logs/
```

---

## Section 14 Implemented Inventory Pipeline

Current base Inventory pipeline execution order:

```text
01. Odoo inventory scope classification
02. Odoo inventory ETL
03. Inventory dictionary lookup validation
04. Inventory dictionary application validation
05. Inventory not_found analyzer
06. Inventory not_found priority backlog
07. Inventory output validation
```

Current base modules:

```text
01. scripts.test_odoo_inventory_scope_classification
02. scripts.test_odoo_inventory_etl
03. scripts.test_inventory_dictionary_lookup
04. scripts.test_apply_inventory_dictionary
05. scripts.test_inventory_not_found_analyzer
06. scripts.test_inventory_not_found_priority_backlog
07. scripts.validate_inventory_outputs
```

Current base pipeline validated result:

```text
total_steps: 7
success: 7
dry_run: 0
skipped: 0
failed_or_error: 0
required_failed_or_error: 0

PIPELINE RESULT: COMPLETED
```

---

## Section 14 Inventory Extended Pipeline With Bridge Reports

The Inventory pipeline supports optional bridge reports.

Command:

```bash
python -m scripts.run_inventory_pipeline --include-bridge-reports
```

Extended execution order:

```text
01. Odoo inventory scope classification
02. Odoo inventory ETL
03. Inventory dictionary lookup validation
04. Inventory dictionary application validation
05. Inventory not_found analyzer
06. Inventory not_found priority backlog
07. Inventory not_found P1 bridge report
08. Inventory not_found P2 bridge report
09. Inventory not_found residual bridge report
10. Inventory output validation
```

Validated extended result:

```text
total_steps: 10
success: 10
dry_run: 0
skipped: 0
failed_or_error: 0
required_failed_or_error: 0

PIPELINE RESULT: COMPLETED
```

Important rule:

```text
Bridge reports are diagnostic only.
Bridge reports do not promote dictionary rows.
```

---

## Section 14 Inventory Output Validation

Inventory output validation is implemented in:

```text
scripts/validate_inventory_outputs.py
```

Current validation checks:

```text
1. required_inventory_tables_exist
2. inventory_table_counts_available
3. inventory_scope_distribution_available
4. inventory_snapshot_mapping_distribution_available
5. inventory_backlog_distribution_available
6. inventory_residual_visibility_available
7. inventory_dictionary_coverage_available
8. inventory_promotions_controlled
```

Validated result:

```text
total_validations: 8
passed: 8
failed: 0

VALIDATION RESULT: PASSED
```

---

## Section 14 Controlled Promotion Policy

Inventory dictionary promotions remain explicitly excluded from the default pipeline.

Excluded from default automation:

```text
scripts.test_promote_inventory_bridge_to_dictionary
scripts.test_promote_inventory_not_found_p1_to_dictionary
scripts.test_promote_inventory_not_found_p2_to_dictionary
scripts.test_promote_inventory_not_found_residual_to_dictionary
```

Governance rule:

```text
Inventory dictionary promotions must remain manual and explicitly approved.
```

---

# Section 15 Status: Zenput Legacy Integration Assessment and Safe Wrapper

Section 15 focused on bringing the existing Zenput legacy integration into the same operational standard as Purchases and Inventory.

The goal was not to replace working legacy scripts blindly.

The goal was to preserve working logic while adding:

```text
central credentials
central location mapping
documentation
safe pipeline wrapper
dry-run support
JSON logging
read-only validation
safety gate
```

---

## Section 15 Final Status

Current status:

```text
Zenput legacy folder identified
Active Zenput files identified
Write operations documented
Credentials and .env usage reviewed
Central Zenput DB target confirmed
core/config/zenput.py created
Zenput location_name mapping validated
Zenput-only locations classified
Zenput safe pipeline wrapper created
Zenput smoke test created and passing
Zenput output validator created and passing
Zenput validation-only execution created and passing
Zenput runbook created
Project README updated with Zenput status
Project status and TODO updated with Zenput status
Project technical guide updated with Zenput status
Production orchestration plan updated with Zenput status
Pipeline logging documentation updated with Zenput status
```

Implemented files:

```text
core/config/zenput.py
scripts/validate_zenput_location_mapping.py
scripts/validate_zenput_outputs.py
scripts/run_zenput_pipeline.py
scripts/test_run_zenput_pipeline.py
docs/zenput-legacy-assessment.md
docs/zenput-runbook.md
```

Existing legacy files:

```text
legacy/zenput/README.md
legacy/zenput/zenput_mysql_forms.py
legacy/zenput/zenput_mysql_tasks.py
legacy/zenput/last_run_timestamp.txt
legacy/zenput/__init__.py
```

Current log folder:

```text
logs/zenput_pipeline_runs/
```

Logs are local execution artefacts and should not be committed.

Required `.gitignore` rule:

```gitignore
# Pipeline run logs
logs/
```

---

## Section 15 Zenput Pipeline Status

Current safe pipeline plan:

```text
01. Zenput location mapping validation
02. Zenput forms legacy ETL
03. Zenput tasks legacy ETL
04. Zenput output validation
```

Current default command:

```bash
python -m scripts.run_zenput_pipeline
```

Expected dry-run result:

```text
total_steps: 4
success: 0
dry_run: 4
skipped: 0
failed_or_error: 0
required_failed_or_error: 0

PIPELINE RESULT: COMPLETED
```

Current safe real execution command:

```bash
python -m scripts.run_zenput_pipeline --execute --validation-only
```

Expected validation-only result:

```text
total_steps: 2
success: 2
dry_run: 0
skipped: 0
failed_or_error: 0
required_failed_or_error: 0

PIPELINE RESULT: COMPLETED
```

Current safety gate command:

```bash
python -m scripts.run_zenput_pipeline --execute
```

Expected result:

```text
PIPELINE RESULT: FAILED
```

This failure is correct.

Reason:

```text
The wrapper blocks write-enabled legacy scripts unless --allow-legacy-writes is explicitly provided.
```

---

## Section 15 Zenput Location Mapping Status

Central configuration:

```text
core/config/zenput.py
```

Main mapping:

```text
ZENPUT_LOCATION_SOURCE_KEY
```

Validated source field:

```text
submissions.location_name
```

Mapping rule:

```text
Zenput location_name -> company_source_key
```

Zenput should not use:

```text
is_wansoft_company
```

as its inclusion filter.

Reason:

```text
Zenput is an operational source independent from Wansoft/Odoo source governance for Purchases and Inventory.
```

Confirmed special mappings during Section 15:

```text
Fonda Argentina Coyoacán -> La Esquina Coyoacán
Fonda Argentina Tollocan -> Metepec
Taqueria Exhibimex -> Versalles
```

Confirmed Zenput-only locations:

```text
León
Lindavista
Perisur
```

Current rule:

```text
León, Lindavista and Perisur are currently Zenput-only.
They do not currently have Wansoft as an operational source.
They are valid for Zenput operational reporting.
They should be modeled as locations that could be incorporated into Wansoft or Odoo in the future.
```

---

# Section 16 Status: Controlled Zenput Legacy Real Execution Readiness

Section 16 focuses on validating the first controlled real execution of the Zenput legacy scripts through the new safe wrapper.

The execution was performed against:

```text
development / test database
```

not production.

Therefore:

```text
No production database was affected.
```

The purpose was to confirm:

```text
legacy scripts can run through the wrapper
forms legacy ETL still works
tasks legacy ETL still works
validators detect problems after real execution
new Zenput locations are caught by central mapping validation
post-execution state can be validated
```

---

## Section 16 Current Status

Current status:

```text
Pre-execution snapshot completed
First controlled real legacy execution completed against development/test database
Forms legacy ETL executed successfully
Tasks legacy ETL executed successfully
Output validator failed correctly on new unmapped location
New location Fonda Argentina Puebla detected
Puebla mapping added to core/config/zenput.py
Post-execution location mapping validation passed
Post-execution output validation passed
Validation-only pipeline passed after correction
```

---

## Section 16 Implemented / Updated Files

Updated after Section 16:

```text
core/config/zenput.py
docs/zenput-legacy-assessment.md
docs/zenput-runbook.md
docs/project-status-and-todo.md
```

Already existing Section 15 files reused:

```text
scripts/validate_zenput_location_mapping.py
scripts/validate_zenput_outputs.py
scripts/run_zenput_pipeline.py
scripts/test_run_zenput_pipeline.py
```

---

## Section 16 Pre-Execution Snapshot

Before the first controlled real execution:

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

## Section 16 Controlled Real Execution

Command executed:

```bash
python -m scripts.run_zenput_pipeline --execute --allow-legacy-writes
```

Execution context:

```text
development / test database
```

Initial execution result:

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

It confirmed that the output validator catches new Zenput locations and prevents the pipeline from being considered complete until mapping is updated.

---

## Section 16 Puebla Mapping Correction

New detected Zenput value:

```text
Fonda Argentina Puebla
```

Correct mapping:

```text
Fonda Argentina Puebla -> Puebla
```

Added to:

```text
core/config/zenput.py
```

Puebla should not be classified as Zenput-only.

Reason:

```text
Puebla already exists as a company_source_key in the project.
Puebla is modeled as a future Odoo / operational branch.
Puebla should be preserved as its own canonical key.
```

The Zenput-only list remains:

```text
León
Lindavista
Perisur
```

---

## Section 16 Post-Execution Snapshot

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
The new Puebla location was detected and then mapped.
Post-execution validators passed after correction.
```

---

## Section 16 Post-Execution Validation Results

Location mapping validator:

```text
submissions_table_exists: PASS
zenput_location_mapping_available: PASS
zenput_only_locations_classified: PASS
zenput_governance_rule_documented: PASS

total_validations: 4
passed: 4
failed: 0

VALIDATION RESULT: PASSED
```

Output validator:

```text
required_zenput_tables_exist: PASS
zenput_table_counts_available: PASS
zenput_submissions_location_mapping: PASS
zenput_only_locations_classified: PASS
zenput_timestamp_file_valid: PASS
zenput_legacy_pipeline_protection_documented: PASS

total_validations: 6
passed: 6
failed: 0

VALIDATION RESULT: PASSED
```

Validation-only pipeline after correction:

```text
01. Zenput location mapping validation -> SUCCESS
02. Zenput output validation -> SUCCESS

total_steps: 2
success: 2
dry_run: 0
skipped: 0
failed_or_error: 0
required_failed_or_error: 0

PIPELINE RESULT: COMPLETED
```

---

## Section 16 Current Findings

### Finding 1: Puebla appeared in Zenput

Status:

```text
Resolved
```

Action:

```text
Fonda Argentina Puebla -> Puebla added to core/config/zenput.py
```

---

### Finding 2: last_run_timestamp.txt did not change

Observed value after execution:

```text
2025-10-23T18:37:33Z
```

Status:

```text
Not blocking
Pending review
```

Current interpretation:

```text
tasks script may be running full sync
timestamp may not be used by current execution path
timestamp update logic may not be triggered
timestamp file may be legacy residue
```

Future TODO:

```text
[ ] Review timestamp logic in legacy/zenput/zenput_mysql_tasks.py
[ ] Decide whether last_run_timestamp.txt is still active or obsolete
[ ] Decide whether timestamp state should move to MySQL or JSON logs
```

---

### Finding 3: Legacy error propagation should be reviewed

A previous failed attempt showed a legacy error related to:

```text
max_allowed_packet
```

The wrapper relies on subprocess return codes.

Future TODO:

```text
[ ] Review legacy scripts to ensure fatal errors return non-zero exit code
```

---

### Finding 4: max_allowed_packet issue was environmental

The earlier error:

```text
Got a packet bigger than 'max_allowed_packet' bytes
```

was related to local XAMPP / MariaDB configuration.

Status:

```text
Resolved for current execution
```

Future TODO:

```text
[ ] Document recommended max_allowed_packet for development database if issue recurs
```

---

# Updated Current TODO

## Priority 1: Finish Section 16 Documentation Consistency

Status:

```text
In progress
```

TODO:

```text
[x] Capture pre-execution Zenput snapshot
[x] Confirm execution target is development/test database
[x] Run first controlled real legacy execution
[x] Detect first validation failure after real execution
[x] Add Fonda Argentina Puebla -> Puebla mapping
[x] Rerun location mapping validator
[x] Rerun output validator
[x] Rerun validation-only pipeline
[x] Update docs/zenput-legacy-assessment.md with controlled execution result
[x] Update docs/zenput-runbook.md with controlled execution result
[x] Update docs/project-status-and-todo.md with Section 16 status
[ ] Update docs/project-technical-guide.md with Section 16 controlled execution result if desired
[ ] Update docs/production-orchestration-plan.md with Section 16 controlled execution result if desired
[ ] Update docs/pipeline-logging-and-run-interpretation.md with Puebla / controlled execution notes if desired
[ ] Review git status
[ ] Commit Section 16 package
```

---

## Priority 2: Zenput Hardening After Controlled Execution

Status:

```text
Pending
```

TODO:

```text
[ ] Review timestamp behaviour in zenput_mysql_tasks.py
[ ] Confirm whether last_run_timestamp.txt is active or obsolete
[ ] Review error propagation from legacy scripts
[ ] Ensure fatal legacy errors return non-zero exit code
[ ] Review transaction safety around submission_answers delete/reinsert
[ ] Consider recording pre/post row counts directly in JSON run logs
[ ] Consider recording timestamp before/after in JSON run logs
[ ] Consider moving Zenput extraction logic to extract/zenput/
[ ] Define future Zenput analytical or canonical tables
```

Possible future files:

```text
extract/zenput/zenput_client.py
extract/zenput/zenput_forms.py
extract/zenput/zenput_tasks.py
extract/zenput/zenput_etl.py
scripts/validate_zenput_canonical_outputs.py
```

---

## Priority 3: Pipeline Logging Expansion

Status:

```text
Purchases implemented
Inventory implemented
Zenput implemented
Database persistence pending
```

Completed for Purchases:

```text
[x] run_id
[x] JSON log file
[x] dry_run flag
[x] pipeline status
[x] step status
[x] duration per step
[x] return codes
[x] error messages
[x] local logs directory
```

Completed for Inventory:

```text
[x] run_id
[x] JSON log file
[x] dry_run flag
[x] pipeline status
[x] step status
[x] duration per step
[x] return codes
[x] error messages
[x] skipped count
[x] local logs directory
```

Completed for Zenput:

```text
[x] run_id
[x] JSON log file
[x] dry_run flag
[x] execute flag
[x] allow_legacy_writes flag
[x] pipeline status
[x] step status
[x] read_only flag
[x] writes_database flag
[x] writes_file flag
[x] legacy flag
[x] duration per step
[x] return codes
[x] error messages
[x] skipped count
[x] local logs directory
```

Pending future database logging:

```text
[ ] Design etl_run_log table
[ ] Design etl_validation_result table
[ ] Add run_id as bridge between console, JSON and database logs
[ ] Add step-level row counts when available
[ ] Add validation result persistence when available
```

---

## Priority 4: Puebla Future Rollout

Status:

```text
Pending activation
```

Current temporary validation state:

```text
Puebla rollout expectation exists
active = False
validation does not fail while inactive
Puebla now appears in Zenput as Fonda Argentina Puebla
Zenput maps Fonda Argentina Puebla -> Puebla
```

TODO before operational activation:

```text
[ ] Confirm official Puebla operational_start_date
[ ] Confirm Puebla remains new_odoo_branch
[ ] Set COMPANY_SOURCE["Puebla"] = "odoo" when rollout is active
[ ] Update sql/seeds/seed_odoo_company_migration_policy.sql
[ ] Update sql/maintenance/update_odoo_company_migration_policy.sql
[ ] Apply policy update in MySQL
[ ] Set Puebla active = True in ROLLOUT_COMPANY_EXPECTATIONS
[ ] Run company source governance test
[ ] Run Odoo purchase ETL
[ ] Run Odoo purchase receipt ETL
[ ] Run Odoo canonical purchase ETL
[ ] Rebuild Wansoft canonical layer if needed
[ ] Run validate_purchases_canonical_layer.py
[ ] Confirm rollout_company_patterns = PASS
[ ] Run full purchases pipeline
```

Expected future Puebla pattern:

```text
Puebla:
    source_system = odoo
    final_purchase_source_status = final_odoo_enabled
```

Not expected after activation:

```text
Puebla:
    source_system = wansoft
    final_purchase_source_status = final_wansoft_enabled
```

---

## Priority 5: Wansoft Canonical Performance Review

Status:

```text
Pending optimisation
```

Current observation:

```text
Wansoft canonical load is the slowest Purchases pipeline step.
```

TODO:

```text
[ ] Review whether full Wansoft reload is required every run
[ ] Evaluate incremental Wansoft canonical load
[ ] Review indexes on canonical purchase tables
[ ] Review batch insert size
[ ] Review source query filters
[ ] Review whether historical Wansoft reload can be separated from daily refresh
```

Do not change business logic only to reduce runtime.

---

## Priority 6: Unified Analytical Consumption Layer

Status:

```text
Pending
```

TODO:

```text
[ ] Define analytical consumption layer using validated MySQL outputs
[ ] Confirm Purchases canonical tables as analytical inputs
[ ] Confirm Inventory snapshot and validated outputs as analytical inputs
[ ] Confirm Zenput outputs and future Zenput analytical tables as analytical inputs
[ ] Define refresh dependency on pipeline success
[ ] Decide whether reporting refresh should depend on JSON logs or future database run logs
```

Recommended rule:

```text
Analytical consumers should consume stable, repeatable, validated MySQL outputs.
```

Possible consumers:

```text
Power BI
Excel
SQL notebooks
dashboards
internal APIs
ad hoc analysis
```

---

# What Should Not Be Automated Yet

The following should remain controlled:

```text
dictionary promotions
scope rule changes
product equivalence decisions
COMPANY_SOURCE changes
company migration policy changes
rollout activation
historical-only decisions
Odoo catalog cleanup
manual correction of Odoo inventory movements
accounting reconciliation adjustments
Zenput production legacy real execution
Zenput last_run_timestamp.txt manual edits
Zenput submission_answers delete/reinsert strategy changes
Zenput error propagation changes without validation
```

Reason:

```text
These actions represent governance, operational or potentially destructive-write decisions, not simple ETL refreshes.
```

---

# Suggested Next Work Sequence

Recommended next sequence after Step 16.4C:

```text
1. Decide whether to update project-technical-guide.md with Section 16 result
2. Decide whether to update production-orchestration-plan.md with Section 16 result
3. Decide whether to update pipeline-logging-and-run-interpretation.md with Section 16 result
4. Review git status
5. Commit Section 16 documentation and mapping update
6. Decide whether to continue Zenput hardening or return to unified analytical consumption layer
```

Recommended technical priority:

```text
Commit Section 16 result first.
Then decide between Zenput hardening and unified analytical layer design.
```

---

# Section 16 Closeout Criteria

Section 16 can be considered functionally complete when:

```text
[x] Pre-execution snapshot captured
[x] Development/test execution target confirmed
[x] First controlled real legacy execution performed
[x] Legacy forms ETL executed
[x] Legacy tasks ETL executed
[x] Output validator caught new unmapped location
[x] Puebla mapping added
[x] Location mapping validator passes
[x] Output validator passes
[x] Validation-only pipeline passes
[x] docs/zenput-legacy-assessment.md updated
[x] docs/zenput-runbook.md updated
[x] docs/project-status-and-todo.md updated
[ ] Optional project-level docs updated if desired
[ ] Section 16 changes committed
```

---

# Current Decision Point After Section 16

The project now has:

```text
Purchases:
    real pipeline execution validated

Inventory:
    real pipeline execution validated

Zenput:
    safe wrapper validated
    validation-only execution validated
    first controlled real legacy execution completed against development/test database
    post-execution validators passing
```

The next decision is whether to prioritise:

```text
Zenput hardening
```

or:

```text
unified analytical consumption layer design
```

## Option A: Continue Zenput Hardening

Focus:

```text
timestamp behaviour
legacy error propagation
transaction safety
row-count logging
timestamp before/after logging
future extract/zenput layer
```

## Option B: Unified Analytical Layer Planning

Focus:

```text
business-ready MySQL outputs
common company_source_key consumption
how Purchases, Inventory and Zenput are exposed
how Zenput-only and future incorporated locations appear analytically
refresh dependency on pipeline validation
```

Recommended next step:

```text
Commit Section 16 first.
Then choose Option A or Option B.
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
docs/branch-rollout-playbook.md
docs/inventory-domain-closeout.md
docs/inventory-runbook.md
docs/purchases-company-migration-policy.md
docs/purchases-product-mapping-policy.md
docs/purchases-canonical-layer.md
docs/purchases-runbook.md
docs/zenput-legacy-assessment.md
docs/zenput-runbook.md
docs/wansoft-local-wsdl.md
```

---

# Recommended Commit

When Section 16 is ready to checkpoint:

```bash
git status

git add core/config/zenput.py docs/zenput-legacy-assessment.md docs/zenput-runbook.md docs/project-status-and-todo.md

git status

git commit -m "docs(zenput): document controlled legacy execution result"

git push
```

If additional project-level docs are updated, include them in the same commit only if they are part of the Section 16 narrative.

Do not commit:

```text
.env
logs/
logs/zenput_pipeline_runs/
*.json
```

---

## Section 17 Status: Unified Analytical Purchase Layer

Section 17 focused on building the first validated analytical consumption layer over the governed MySQL outputs.

The current purchase analytical layer is now validated across line-level, order-level and daily company-product aggregate objects.

### Current Section 17 Status

```text
Status: validated for purchase analytical layer
Purchase line fact: complete
Purchase order fact: complete
Daily company-product aggregate: complete
Known remaining work: product governance backlog, key stability review, orchestration documentation and inventory analytical layer design
```

### Implemented Shared Dimensions

```text
dim_company_analytical
dim_time
dim_vendor
dim_product
```

### Implemented Analytical Support Table

```text
analytics_company_domain_coverage
```

### Implemented Purchase Analytical Tables

```text
analytics_purchase_order_lines
analytics_purchase_orders
analytics_purchase_daily_company_product
```

### Validated Purchase Reconciliation Chain

```text
canonical_purchase_order_line_snapshot
-> analytics_purchase_order_lines
-> analytics_purchase_orders
-> analytics_purchase_daily_company_product
```

Shared reconciled line count:

```text
749932
```

Shared reconciled purchase amount:

```text
1034075208.2566
```

### Step 17.20 - Implement analytics_purchase_order_lines

Status:

```text
completed
```

Scripts:

```text
scripts/build_analytics_purchase_order_lines.py
scripts/validate_analytics_purchase_order_lines.py
```

Validated result:

```text
total_rows: 749932
include_in_business_views: 676186
excluded_from_business_views: 73746
internal_vendor_rows: 20061
review_required_product_rows: 4936
orphan_product_rows: 50978
orphan_company_rows: 0
orphan_vendor_rows: 0
invalid_order_date_rows: 0
```

Validation result:

```text
total_validations: 14
passed: 14
failed: 0
VALIDATION RESULT: PASSED
```

Amount reconciliation:

```text
canonical_price_total: 1034075208.2566
analytics_price_total: 1034075208.2566
difference: 0.0000
```

### Step 17.21 - Document analytics_purchase_order_lines closeout

Status:

```text
completed
```

Document:

```text
docs/analytics-purchase-order-lines-design.md
```

Key decisions:

```text
All canonical purchase lines are preserved.
Business-facing inclusion is controlled by include_in_business_views.
Excluded rows remain visible with exclude_reason.
Product joins do not use product names.
Review-required products and internal vendors are excluded from default business views.
```

### Step 17.22 - Design analytics_purchase_orders

Status:

```text
completed
```

Document:

```text
docs/analytics-purchase-orders-design.md
```

Design grain:

```text
1 row = 1 source purchase order group
```

Source:

```text
analytics_purchase_order_lines
```

### Step 17.23 - Implement analytics_purchase_orders

Status:

```text
completed
```

Scripts:

```text
scripts/build_analytics_purchase_orders.py
scripts/validate_analytics_purchase_orders.py
```

Validated result:

```text
total_orders: 145876
include_in_business_views: 143188
excluded_from_business_views: 2688
review_required_orders: 26497
no_business_line_orders: 2688
inconsistent_company_orders: 0
inconsistent_date_orders: 0
inconsistent_vendor_orders: 0
```

Line reconciliation:

```text
analytics_purchase_order_lines rows: 749932
analytics_purchase_orders summed line_count: 749932
```

Amount reconciliation:

```text
analytics_purchase_order_lines.price_total: 1034075208.2566
analytics_purchase_orders.price_total_total: 1034075208.2566
difference: 0.0000
```

Validation result:

```text
total_validations: 14
passed: 14
failed: 0
VALIDATION RESULT: PASSED
```

Technical issue resolved:

```text
Initial build failed with MySQL error 2013 Lost connection to MySQL server during query.
Build was rewritten to use INSERT INTO SELECT.
Final build completed successfully.
```

### Step 17.24 - Document analytics_purchase_orders closeout

Status:

```text
completed
```

Document:

```text
docs/analytics-purchase-orders-design.md
```

Key decisions:

```text
analytics_purchase_orders is derived from analytics_purchase_order_lines.
Orders with at least one business-ready line remain included unless order-level inconsistencies exist.
Orders with no business-ready lines are excluded with no_business_lines.
Order-level company, date and vendor consistency checks are clean.
```

### Step 17.25 - Design analytics_purchase_daily_company_product

Status:

```text
completed
```

Document:

```text
docs/analytics-purchase-daily-company-product-design.md
```

Design grain:

```text
company_source_key
order_date_key
product_analytical_group_key
source_system
```

Product orphan handling rule:

```text
product_analytical_group_key = product_analytical_key when populated
product_analytical_group_key = 0 when product_analytical_key is null
```

### Step 17.26 - Implement analytics_purchase_daily_company_product

Status:

```text
completed
```

Scripts:

```text
scripts/build_analytics_purchase_daily_company_product.py
scripts/validate_analytics_purchase_daily_company_product.py
```

Validated result:

```text
total_rows: 626258
include_in_business_views: 595831
excluded_from_business_views: 30427
total_line_count: 749932
total_business_line_count: 676186
total_excluded_line_count: 73746
total_review_required_line_count: 55914
total_internal_vendor_line_count: 20061
total_review_required_product_line_count: 4936
total_orphan_product_line_count: 50978
```

Amount reconciliation:

```text
total_price_total: 1034075208.2566
business_price_total: 989935685.4550
excluded_price_total: 44139522.8016
```

Validation result:

```text
total_validations: 15
passed: 15
failed: 0
VALIDATION RESULT: PASSED
```

### Step 17.27 - Document analytics_purchase_daily_company_product closeout

Status:

```text
completed
```

Document:

```text
docs/analytics-purchase-daily-company-product-design.md
```

Key decisions:

```text
Aggregate uses analytics_purchase_order_lines as source.
Aggregate preserves full line activity, including excluded lines.
Product orphans are grouped under product_analytical_group_key = 0.
Vendor is summarized through counts, not included in the grain.
Aggregate reconciles line counts and purchase amounts to analytics_purchase_order_lines.
```

### Step 17.28 - Update README.md and project-status-and-todo.md with analytical purchases closeout

Status:

```text
completed
```

Important documentation rule:

```text
README.md and project-status-and-todo.md were updated additively.
Existing historical project content was preserved.
The update records the validated purchase analytical layer without replacing prior documentation.
```

Files updated:

```text
README.md
docs/project-status-and-todo.md
```

### Section 17 Known Open Items

```text
orphan_product_lines: 50978
review_required_product_lines: 4936
product key stability review
production orchestration documentation
purchase analytical refresh runbook
inventory analytical layer design
```

### Section 17 Recommended Next Step

```text
Paso 17.29 - Revisar y cerrar documentación de Sección 17
```

---

## Current Decision Point After Section 17

The project now has:

```text
Purchases:
    canonical layer validated
    pipeline execution validated
    analytical line fact validated
    analytical order fact validated
    daily company-product aggregate validated
Inventory:
    pipeline execution validated
    analytical layer pending
Zenput:
    safe wrapper validated
    validation-only execution validated
    first controlled real legacy execution completed against development/test database
    post-execution validators passing
```

Recommended next step:

```text
Paso 17.29 - Revisar y cerrar documentación de Sección 17
```

After Section 17 closeout, the next technical domain should be:

```text
Inventory analytical layer design
```

Suggested future step:

```text
Paso 18.1 - Diseñar analytics_inventory_snapshot o analytics_inventory_daily_company_product
```

<!-- STEP_18_16D_INVENTORY_PIPELINE_SCOPE_REFINEMENT -->

# Paso 18.16D - Inventory pipeline scope refinement closeout

## Status

Completed and validated.

## Purpose

This section documents the closure of the Inventory pipeline scope-refinement correction. The Inventory pipeline now runs the Odoo inventory scope refinement step before the Odoo inventory ETL.

## Root cause corrected

The previous Inventory pipeline order executed base Odoo inventory scope classification directly before the Odoo inventory ETL. That was incomplete because `scripts.test_odoo_inventory_etl` consumes `refined_inventory_scope`, not only base `inventory_scope`.

The base classifier can correctly produce `shared_or_open`, but the ETL is configured to include `shared_cross_company` through:

```text
INVENTORY_ETL_SCOPE_INCLUDE=shared_cross_company
```

Without the refinement step, a real pipeline execution can produce:

```text
inventory_candidates_rows: 0
```

while final validation can still pass against previously loaded `odoo_inventory_snapshot` rows.

## Correction applied

The required step:

```text
scripts.test_refine_odoo_inventory_scope
```

was inserted between:

```text
scripts.test_odoo_inventory_scope_classification
```

and:

```text
scripts.test_odoo_inventory_etl
```

## Validated default Inventory pipeline order

1. `scripts.test_odoo_inventory_scope_classification`
2. `scripts.test_refine_odoo_inventory_scope`
3. `scripts.test_odoo_inventory_etl`
4. `scripts.test_inventory_dictionary_lookup`
5. `scripts.test_apply_inventory_dictionary`
6. `scripts.test_inventory_not_found_analyzer`
7. `scripts.test_inventory_not_found_priority_backlog`
8. `scripts.validate_inventory_outputs`

## Validation evidence

### Dry-run

```text
total_steps: 8
dry_run: 8
failed_or_error: 0
required_failed_or_error: 0
TEST RESULT: PASSED
```

### Real execution

```text
run_id: ba1840b2-b79e-4642-aed6-0ea925f5ed57
total_steps: 8
success: 8
failed_or_error: 0
required_failed_or_error: 0
PIPELINE RESULT: COMPLETED
duration_seconds: 16.1
log_file: logs\inventory_pipeline_runs\20260819_143706_ba1840b2-b79e-4642-aed6-0ea925f5ed57.json
```

### Scope refinement result

```text
review_scope: 579
shared_cross_company: 526
bodegon: 404
restaurantes: 224
empanadas: 27
odoo_inventory_scope_classification records updated: 1760
```

### Odoo inventory ETL after refinement

```text
sales_reference_rows: 1528
inventory_candidates_rows: 4029
scope_backlog_rows: 3890
approved_rows: 1387
pending_rows: 3
historical_rows: 0
not_found_rows: 1029
odoo_inventory_snapshot: 1387 rows
odoo_inventory_backlog: 6450 rows
```

### Final output validation

```text
total_validations: 8
passed: 8
failed: 0
VALIDATION RESULT: PASSED
```

## Controlled promotion policy

Inventory dictionary promotion scripts remain intentionally excluded from the default pipeline and require explicit manual approval.

Excluded promotion scripts:

- `scripts.test_promote_inventory_bridge_to_dictionary`
- `scripts.test_promote_inventory_not_found_p1_to_dictionary`
- `scripts.test_promote_inventory_not_found_p2_to_dictionary`
- `scripts.test_promote_inventory_not_found_residual_to_dictionary`

## Operational interpretation

The Inventory pipeline should not be considered fully refreshed unless Step 03 confirms non-zero `inventory_candidates_rows` and inserted rows into `odoo_inventory_snapshot`.

## Git traceability recommendation

Recommended commit message:

```text
Fix inventory pipeline scope refinement order
```

