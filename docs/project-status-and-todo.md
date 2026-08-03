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
keep Zenput legacy execution protected
continue Zenput modernization carefully
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
| Zenput | Legacy assessed, central mapping created, safe wrapper implemented |
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
Legacy real execution remains protected.
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

Section 15 focuses on bringing the existing Zenput legacy integration into the same operational standard as Purchases and Inventory.

The goal is not to replace working legacy scripts blindly.

The goal is to preserve working logic while adding:

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

## Section 15 Current Status

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

Confirmed special mappings:

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

## Section 15 Validators

Current Zenput validators:

```text
scripts.validate_zenput_location_mapping
scripts.validate_zenput_outputs
```

Location mapping validator result:

```text
total_validations: 4
passed: 4
failed: 0

VALIDATION RESULT: PASSED
```

Output validator result:

```text
total_validations: 6
passed: 6
failed: 0

VALIDATION RESULT: PASSED
```

Smoke test result:

```text
default_dry_run: PASS
safety_gate: PASS

TEST RESULT: PASSED
```

Validation-only execution result:

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

## Section 15 Safety Rule

Do not run this command casually:

```bash
python -m scripts.run_zenput_pipeline --execute --allow-legacy-writes
```

Reason:

```text
This command may execute legacy scripts that write to MySQL and may update last_run_timestamp.txt.
```

Recommended safe command:

```bash
python -m scripts.run_zenput_pipeline --execute --validation-only
```

---

# Updated Current TODO

## Priority 1: Finish Section 15 Documentation Consistency

Status:

```text
In progress
```

TODO:

```text
[x] Identify active Zenput legacy files
[x] Review write operations and target tables
[x] Review credentials and .env usage
[x] Create core/config/zenput.py
[x] Validate location_name mapping against MySQL
[x] Create safe run_zenput_pipeline.py wrapper
[x] Create test_run_zenput_pipeline.py
[x] Create validate_zenput_outputs.py
[x] Integrate validate_zenput_outputs.py as required pipeline step
[x] Add --validation-only mode
[x] Create docs/zenput-runbook.md
[x] Update README.md with Zenput status
[x] Update docs/project-status-and-todo.md with Zenput status
[ ] Update docs/project-technical-guide.md with Zenput status
[ ] Update docs/production-orchestration-plan.md with Zenput status
[ ] Update docs/pipeline-logging-and-run-interpretation.md with Zenput status
[ ] Add ZENPUT_API_TOKEN placeholder to core/config/.env.example if missing
[ ] Review git status
[ ] Commit Section 15 package
```

---

## Priority 2: Zenput Future Improvements

Status:

```text
Pending future refinement
```

TODO:

```text
[ ] Review whether and when to approve first controlled legacy real execution
[ ] Review transaction safety around submission_answers delete/reinsert
[ ] Review last_run_timestamp.txt future handling
[ ] Decide whether to keep last_run_timestamp.txt or migrate state to MySQL
[ ] Decide whether to create a modern extract/zenput layer
[ ] Define future Zenput analytical or canonical tables
[ ] Review whether Zenput validation results should be persisted to database
[ ] Review whether Zenput pipeline should later support scheduled execution
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
```

TODO before activation:

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
Zenput legacy real execution
Zenput last_run_timestamp.txt updates outside approved execution
Zenput submission_answers delete/reinsert strategy changes
```

Reason:

```text
These actions represent governance, operational or destructive-write decisions, not simple ETL refreshes.
```

---

# Suggested Next Work Sequence

Recommended next sequence after Step 15.16B:

```text
1. Update docs/project-technical-guide.md with Zenput status
2. Update docs/production-orchestration-plan.md with Zenput wrapper status
3. Update docs/pipeline-logging-and-run-interpretation.md with Zenput logs
4. Add ZENPUT_API_TOKEN placeholder to core/config/.env.example if missing
5. Review git status
6. Commit Section 15 package
7. Decide whether to approve first controlled Zenput legacy real execution or continue safety review
```

Recommended technical priority:

```text
Finish Section 15 documentation consistency first.
Then decide whether to proceed with controlled Zenput real execution or additional safety hardening.
```

---

# Section 15 Closeout Criteria

Section 15 can be considered complete when:

```text
[x] Zenput legacy files are identified
[x] Zenput write operations are documented
[x] Zenput credentials and .env usage are reviewed
[x] core/config/zenput.py is created
[x] Zenput location mapping validates against MySQL
[x] Zenput-only locations are documented
[x] run_zenput_pipeline.py is implemented
[x] test_run_zenput_pipeline.py passes
[x] validate_zenput_outputs.py passes
[x] validate_zenput_outputs.py is integrated as required pipeline step
[x] --validation-only mode works
[x] docs/zenput-legacy-assessment.md is updated
[x] docs/zenput-runbook.md is created
[x] README.md is updated
[x] docs/project-status-and-todo.md is updated
[ ] docs/project-technical-guide.md is updated
[ ] docs/production-orchestration-plan.md is updated
[ ] docs/pipeline-logging-and-run-interpretation.md is updated
[ ] core/config/.env.example includes ZENPUT_API_TOKEN placeholder if missing
[ ] Section 15 changes committed
```

---

# Current Decision Point After Section 15

The project now has controlled orchestration or safe wrapper capability for:

```text
Purchases
Inventory
Zenput
```

Current status:

```text
Purchases:
    real pipeline execution is validated

Inventory:
    real pipeline execution is validated

Zenput:
    safe wrapper and validators are validated
    validation-only real execution is validated
    legacy real execution remains protected
```

The next decision is whether to prioritise:

```text
controlled Zenput legacy real execution review
```

or:

```text
unified analytical consumption layer design
```

Recommended priority:

```text
Finish Section 15 documentation and commit first.
Then decide whether Zenput legacy real execution is ready for a controlled approved run.
```

Reason:

```text
Zenput legacy scripts write to MySQL and may update local timestamp state.
The safety wrapper is ready, but full legacy real execution should remain an explicit operational decision.
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

When Section 15 is ready to checkpoint:

```bash
git status

git add README.md docs/ core/config/zenput.py scripts/validate_zenput_location_mapping.py scripts/validate_zenput_outputs.py scripts/run_zenput_pipeline.py scripts/test_run_zenput_pipeline.py core/config/.env.example

git status

git commit -m "feat(zenput): add safe pipeline wrapper and validation"

git push
```

If `core/config/.env.example` is not changed, use:

```bash
git status

git add README.md docs/ core/config/zenput.py scripts/validate_zenput_location_mapping.py scripts/validate_zenput_outputs.py scripts/run_zenput_pipeline.py scripts/test_run_zenput_pipeline.py

git status

git commit -m "feat(zenput): add safe pipeline wrapper and validation"

git push
```