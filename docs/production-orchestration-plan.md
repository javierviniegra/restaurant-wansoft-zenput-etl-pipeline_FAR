# Production Orchestration Plan

## Purpose

This document defines the production-style orchestration plan for the Wansoft + Odoo Data Warehouse and ETL Pipeline project.

The goal is to move from individually validated scripts to controlled, repeatable, auditable execution flows.

This document covers:

```text
execution order
task classification
validation gates
safe automation candidates
controlled manual steps
logging requirements
failure handling
future orchestration structure
rollout validation
inventory pipeline pending work
```

---

## Current Context

The project originally operated through individual validation scripts under:

```text
scripts/
```

That approach was useful for discovery and step-by-step validation.

The project has now moved into the first orchestration phase.

Current orchestration status:

```text
Purchases pipeline: implemented
Purchases canonical validation: implemented
Purchases JSON logging: implemented
Purchases rollout validation: implemented
Inventory pipeline: pending
Inventory validation: pending
Production scheduling: pending
```

---

## Orchestration Principle

Production orchestration should follow this principle:

```text
Automate extraction, transformation, loading, validation and logging.
Keep governance decisions controlled.
```

This means:

```text
ETL refreshes can be automated.
Canonical validations can be automated.
JSON logging can be automated.
Dictionary promotions should remain manual or approval-based.
COMPANY_SOURCE changes should remain controlled.
Odoo writeback should not happen.
Rollout activation should be explicit.
```

---

# Task Classification

## Safe to Automate

These tasks are good candidates for automation:

```text
Odoo read-only extraction
Wansoft persisted-source refresh
snapshot loading
canonical table refresh by source_system
backlog generation
validation query execution
row-count logging
source-system count logging
diagnostic export
JSON run-log generation
canonical layer validation
rollout pattern validation
```

---

## Keep Controlled

These tasks should remain controlled:

```text
dictionary promotion
manual product equivalence approval
scope rule changes
COMPANY_SOURCE changes
company migration policy changes
rollout activation
historical-only product decisions
Odoo catalog cleanup
accounting adjustments
inventory correction in Odoo
```

---

## Not Allowed

These actions are not allowed in the ETL baseline:

```text
writing updates into Odoo
automatic product alias creation
automatic dictionary promotion
automatic changes to COMPANY_SOURCE
automatic rollout activation
automatic operational corrections in Odoo
automatic accounting adjustments
```

---

# Current Implemented Pipeline: Purchases

## Implemented File

The Purchases orchestration script is:

```text
scripts/run_purchases_pipeline.py
```

Smoke test:

```text
scripts/test_run_purchases_pipeline.py
```

Final canonical validator:

```text
scripts/validate_purchases_canonical_layer.py
```

Run logs:

```text
logs/purchases_pipeline_runs/
```

The logs are local execution artefacts and should not be committed.

Recommended `.gitignore` entry:

```gitignore
# Pipeline run logs
logs/
```

---

## Purchases Pipeline Execution Order

Current Purchases pipeline order:

```text
01. Company source governance
02. Odoo purchase order and line ETL
03. Odoo purchase receipt ETL
04. Purchase inventory mapping backlog
05. Purchase backlog product reference report
06. Purchase company source eligibility
07. Odoo canonical purchase load
08. Wansoft purchase subsidiary mapping report
09. Wansoft canonical purchase load
10. Purchases canonical layer validation
```

Current modules:

```text
01. scripts.test_company_source_governance
02. scripts.test_odoo_purchase_etl
03. scripts.test_odoo_purchase_receipt_etl
04. scripts.test_purchase_inventory_mapping_backlog
05. scripts.test_purchase_backlog_product_reference_report
06. scripts.test_purchase_company_source_eligibility
07. scripts.test_canonical_purchase_odoo_etl
08. scripts.test_wansoft_purchase_subsidiary_mapping_report
09. scripts.test_canonical_purchase_wansoft_etl
10. scripts.validate_purchases_canonical_layer
```

---

## Purchases Pipeline Current Status

Current Purchases orchestration status:

```text
dry-run validated
real execution validated
JSON logging validated
canonical validation integrated as required step
rollout company pattern validation integrated
```

Current expected successful summary:

```text
total_steps: 10
success: 10
dry_run: 0
failed_or_error: 0
required_failed_or_error: 0
PIPELINE RESULT: COMPLETED
```

Dry-run expected summary:

```text
total_steps: 10
success: 0
dry_run: 10
failed_or_error: 0
required_failed_or_error: 0
PIPELINE RESULT: COMPLETED
```

---

## Purchases JSON Logging

The Purchases pipeline generates a local JSON log for each run.

Log folder:

```text
logs/purchases_pipeline_runs/
```

Each log includes:

```text
run_id
pipeline_name
status
dry_run
started_at
finished_at
duration_seconds
total_steps
success
dry_run_steps
failed_or_error
required_failed_or_error
step-level results
return codes
error messages
```

Related documentation:

```text
docs/pipeline-logging-and-run-interpretation.md
```

---

# Purchases Canonical Validation

The final Purchases pipeline step validates the canonical purchase layer.

Validator:

```text
scripts/validate_purchases_canonical_layer.py
```

The validation currently checks:

```text
source-system coexistence
Antenas source split
Wansoft final-source companies
internal providers as vendors
internal providers not as final companies
canonical product mapping distribution
canonical table counts
rollout company patterns
```

Current validation count:

```text
total_validations: 8
```

Expected result:

```text
VALIDATION RESULT: PASSED
```

If the validator fails, the Purchases pipeline should fail because this step is required.

---

# Rollout Company Pattern Validation

The Purchases validator includes rollout-specific expectations.

Current rollout expectation types:

```text
migrated_from_wansoft
new_odoo_branch
```

Current active rollout validations:

```text
Antenas:
    rollout_type = migrated_from_wansoft
    active = True

La Esquina Coyoacán:
    rollout_type = migrated_from_wansoft
    active = True

CentroMyJ:
    rollout_type = new_odoo_branch
    active = True
```

Current inactive future rollout:

```text
Puebla:
    rollout_type = new_odoo_branch
    active = False
```

---

## migrated_from_wansoft Pattern

Expected canonical pattern:

```text
Odoo:
    final_odoo_enabled from operational_start_date onward

Wansoft:
    wansoft_history_before_odoo before operational_start_date
```

Not allowed after activation:

```text
wansoft / final_wansoft_enabled
```

for the migrated company.

Validated examples:

```text
Antenas
La Esquina Coyoacán
```

---

## new_odoo_branch Pattern

Expected canonical pattern:

```text
Odoo:
    final_odoo_enabled
```

Not allowed after activation:

```text
wansoft / final_wansoft_enabled
```

for the new Odoo branch.

Validated example:

```text
CentroMyJ
```

Future inactive example:

```text
Puebla
```

---

## Active vs Inactive Rollout Expectations

Rollout expectations may be configured as:

```text
active = True
active = False
```

Meaning:

```text
active = True:
    validation is enforced and can fail the pipeline.

active = False:
    rollout is documented as future work but does not fail current validation.
```

This allows future branch rollouts to be documented before activation.

---

# Proposed Execution Layers

## Layer 1: Governance Validation

Purpose:

```text
Confirm that source governance, company mapping, and environment assumptions are valid before loading data.
```

Implemented in Purchases:

```bash
python -m scripts.test_company_source_governance
```

Expected outputs:

```text
company source rules valid
Odoo company mapping valid
Wansoft subsidiary mapping assumptions valid
internal providers handled correctly
rollout company source behaviour visible
```

Failure handling:

```text
Stop orchestration if company source governance fails.
```

---

## Layer 2: Inventory Refresh

Purpose:

```text
Refresh Odoo inventory snapshots and backlogs using controlled dictionary logic.
```

Current status:

```text
Pending orchestration
```

Inventory currently has individual scripts and documentation, but no full pipeline equivalent to Purchases.

Recommended future tasks:

```bash
python -m scripts.test_odoo_inventory_scope_classification
python -m scripts.test_odoo_inventory_etl
python -m scripts.test_inventory_dictionary_lookup
python -m scripts.test_apply_inventory_dictionary
python -m scripts.test_inventory_not_found_analyzer
python -m scripts.test_inventory_not_found_priority_backlog
```

Important:

```text
Inventory dictionary promotions should not run automatically unless explicitly approved.
```

Pending future files:

```text
scripts/run_inventory_pipeline.py
scripts/test_run_inventory_pipeline.py
scripts/validate_inventory_outputs.py
logs/inventory_pipeline_runs/
```

---

## Layer 3: Purchases Odoo Snapshot Refresh

Purpose:

```text
Refresh Odoo purchase technical snapshots.
```

Implemented in Purchases pipeline:

```bash
python -m scripts.test_odoo_purchase_etl
python -m scripts.test_odoo_purchase_receipt_etl
```

Expected outputs:

```text
odoo_purchase_order_snapshot
odoo_purchase_order_line_snapshot
odoo_purchase_receipt_snapshot
odoo_purchase_receipt_move_snapshot
```

Failure handling:

```text
Stop if Odoo purchase order or purchase line extraction fails.
Stop if Odoo receipt or receipt movement extraction fails.
```

---

## Layer 4: Purchases Backlog and Eligibility

Purpose:

```text
Refresh purchase mapping backlog and company source eligibility.
```

Implemented in Purchases pipeline:

```bash
python -m scripts.test_purchase_inventory_mapping_backlog
python -m scripts.test_purchase_backlog_product_reference_report
python -m scripts.test_purchase_company_source_eligibility
```

Expected outputs:

```text
odoo_purchase_inventory_mapping_backlog
purchase backlog reference summary
company source eligibility summary
```

Failure handling:

```text
Warn if backlog grows.
Stop if company source eligibility logic fails.
Do not automatically promote backlog products.
```

---

## Layer 5: Canonical Purchases Refresh

Purpose:

```text
Refresh canonical purchase tables from Odoo and Wansoft.
```

Implemented in Purchases pipeline:

```bash
python -m scripts.test_canonical_purchase_odoo_etl
python -m scripts.test_wansoft_purchase_subsidiary_mapping_report
python -m scripts.test_canonical_purchase_wansoft_etl
```

Expected outputs:

```text
canonical_purchase_order_snapshot
canonical_purchase_order_line_snapshot
canonical_purchase_receipt_snapshot
canonical_purchase_receipt_move_snapshot
```

Refresh rule:

```text
Odoo refresh deletes and reloads only source_system = 'odoo'.
Wansoft refresh deletes and reloads only source_system = 'wansoft'.
```

Failure handling:

```text
Stop if canonical load fails.
Stop if source-system coexistence validation fails.
Stop if rollout company pattern validation fails.
```

---

## Layer 6: Canonical Validation

Purpose:

```text
Validate canonical and inventory outputs after refresh.
```

Purchases implemented validator:

```bash
python -m scripts.validate_purchases_canonical_layer
```

Current Purchases validation areas:

```text
source-system coexistence
Antenas source split
Wansoft final-source companies
internal providers as vendors
internal providers not as final companies
canonical product mapping distribution
canonical table counts
rollout company patterns
```

Inventory validation is still pending.

Possible future Inventory validator:

```text
scripts/validate_inventory_outputs.py
```

---

# Proposed Orchestration Script Structure

Current implemented script:

```text
scripts/run_purchases_pipeline.py
```

Future orchestration scripts:

```text
scripts/run_inventory_pipeline.py
scripts/run_full_datawarehouse_refresh.py
```

Current validators:

```text
scripts/validate_purchases_canonical_layer.py
```

Future validators:

```text
scripts/validate_inventory_outputs.py
scripts/validate_canonical_outputs.py
```

---

# Proposed Inventory Orchestration

Suggested future script:

```text
scripts/run_inventory_pipeline.py
```

Suggested execution order:

```text
01. Odoo inventory scope classification
02. Odoo inventory ETL
03. Inventory dictionary lookup validation
04. Inventory dictionary application validation
05. Inventory backlog validation
06. Inventory not_found analysis
07. Optional bridge report generation
08. Optional controlled promotion
09. Rerun inventory ETL after approved promotion
10. Inventory output validation
```

Important:

```text
Promotion scripts should not run automatically unless explicitly approved.
```

Expected future logging:

```text
logs/inventory_pipeline_runs/
```

Expected future pipeline name:

```text
inventory_pipeline
```

---

# Logging Requirements

Production-style orchestration should log:

```text
run_id
pipeline_name
step_name
source_system
target_table
started_at
finished_at
status
rows_inserted
rows_updated
rows_deleted
error_message
validation_status
```

Current implemented local logging:

```text
Purchases JSON logs
```

Pending future database logging:

```text
etl_run_log
etl_validation_result
```

---

## Current JSON Log Schema

Current JSON log schema includes:

```text
run_id
pipeline_name
status
dry_run
started_at
finished_at
duration_seconds
total_steps
success
dry_run_steps
failed_or_error
required_failed_or_error
steps
```

Step-level fields:

```text
step_id
name
module
group
required
status
started_at
finished_at
duration_seconds
return_code
error_message
```

Related documentation:

```text
docs/pipeline-logging-and-run-interpretation.md
```

---

# Validation Result Requirements

Validation results should eventually be stored in a structured way.

Possible future table:

```text
etl_validation_result
```

Suggested columns:

```sql
id
run_id
validation_name
validation_group
status
metric_name
metric_value
expected_value
details
created_at
```

Examples:

```text
source_system_coexistence
antenas_source_split
rollout_company_patterns
internal_providers_not_as_companies
wansoft_final_source_companies
inventory_snapshot_count
inventory_backlog_distribution
```

---

# Failure Handling

## Stop Conditions

The orchestration should stop if:

```text
database connection fails
Odoo extraction fails
Wansoft source mapping critical failure occurs
company source governance fails
canonical load fails
duplicate key error occurs
source-system coexistence validation fails
rollout company pattern validation fails
internal providers appear as final companies
```

---

## Warning Conditions

The orchestration may continue with warnings if:

```text
backlog increases
new unmapped products appear
new vendor appears
new company appears but is not final-source
non-critical diagnostic export fails
Pandas SQLAlchemy warning appears
inactive future rollout expectation is skipped
```

---

## Manual Review Conditions

Manual review is required if:

```text
new unresolved products appear with high purchase amount
new source company appears
COMPANY_SOURCE requires update
rollout expectation should become active
internal provider appears in unexpected context
inventory valuation differences persist
Odoo operational errors affect data completeness
```

---

# Reload Strategy

## Source-System Isolation

Canonical tables should be refreshed by `source_system`.

Example:

```sql
DELETE FROM canonical_purchase_order_snapshot
WHERE source_system = 'odoo';
```

or:

```sql
DELETE FROM canonical_purchase_order_snapshot
WHERE source_system = 'wansoft';
```

This avoids removing validated rows from the other source.

---

## Odoo Canonical Refresh

Rules:

```text
delete only source_system = 'odoo'
reload eligible Odoo rows
preserve Wansoft rows
```

---

## Wansoft Canonical Refresh

Rules:

```text
delete only source_system = 'wansoft'
reload eligible Wansoft rows
preserve Odoo rows
```

---

## Avoid DROP TABLE During Normal Rollout Testing

Do not use:

```sql
DROP TABLE
```

for normal canonical refresh or rollout testing.

Use:

```sql
DELETE FROM <canonical_table>
WHERE source_system = '<source>';
```

and then reload.

Reason:

```text
DROP TABLE may remove schema, indexes, constraints or metadata.
source-specific DELETE preserves table structure.
```

---

# Branch Rollout Orchestration

Branch rollouts must follow a controlled sequence:

```text
1. Update COMPANY_SOURCE
2. Update seed SQL
3. Update maintenance SQL
4. Apply policy to MySQL
5. Update rollout expectations
6. Run governance tests
7. Rebuild Odoo canonical layer
8. Rebuild Wansoft canonical layer if needed
9. Run canonical validation
10. Run full Purchases pipeline
```

Detailed rollout process:

```text
docs/branch-rollout-playbook.md
```

---

# Environment Requirements

Before running orchestration, confirm:

```text
.env exists
Odoo credentials are valid
MySQL credentials are valid
Wansoft credentials are valid
WANSOFT_USE_LOCAL_WSDL=true
resources/wsdl/wansoft.wsdl exists
COMPANY_SOURCE is reviewed
rollout expectations are reviewed
logs/ is ignored by Git
```

---

# Pre-Run Checklist

```text
[ ] Git branch is correct
[ ] .env is loaded
[ ] MySQL connection works
[ ] Odoo connection works
[ ] Wansoft local WSDL validation passes
[ ] COMPANY_SOURCE reviewed
[ ] Rollout expectations reviewed
[ ] No uncommitted risky code changes
[ ] Last successful run reviewed
[ ] Manual governance tasks are not accidentally included
[ ] logs/ is ignored by Git
```

---

# Post-Run Checklist

```text
[ ] Purchases pipeline summary reviewed
[ ] JSON log file created
[ ] required_failed_or_error = 0
[ ] Final validation passed
[ ] Odoo purchase snapshot counts reviewed
[ ] Odoo receipt snapshot counts reviewed
[ ] Odoo canonical counts reviewed
[ ] Wansoft canonical counts reviewed
[ ] Source-system coexistence validated
[ ] Rollout company patterns validated
[ ] Internal providers validated
[ ] New unmapped products reviewed
[ ] Slowest step reviewed
```

---

# Initial Automation Recommendation

Current recommendation:

```text
Purchases pipeline can remain the first automation candidate.
```

Reason:

```text
Purchases canonical layer is validated.
Odoo and Wansoft source split is working.
Validation queries are implemented.
JSON logging is implemented.
Rollout validation is implemented.
Refresh by source_system is implemented.
```

Second automation target:

```text
Inventory pipeline orchestration
```

Reason:

```text
Inventory has validated scripts but lacks a unified orchestrator and validator.
```

---

# Future Production Options

Potential orchestration tools:

```text
Python script orchestration
Windows Task Scheduler
cron
GitHub Actions self-hosted runner
Airflow
Prefect
Dagster
```

Initial recommendation:

```text
Start with Python orchestration scripts.
Add scheduling only after validations and logs are stable.
```

---

# Current Pending Work

## Purchases

Current status:

```text
Implemented and passing
```

Pending improvements:

```text
[ ] Review Wansoft canonical load performance
[ ] Evaluate incremental Wansoft loading
[ ] Add database run-log table if needed
[ ] Add validation result persistence if needed
[ ] Finalise Section 13 documentation consistency
```

---

## Inventory

Current status:

```text
Pending orchestration
```

Pending work:

```text
[ ] Create scripts/run_inventory_pipeline.py
[ ] Create scripts/test_run_inventory_pipeline.py
[ ] Create scripts/validate_inventory_outputs.py
[ ] Add JSON logging for inventory pipeline
[ ] Add logs/inventory_pipeline_runs/
[ ] Add inventory pipeline instructions to docs/inventory-runbook.md
[ ] Add inventory pipeline strategy to this document
```

---

## Puebla Rollout

Current status:

```text
Future rollout
active = False
```

Pending work:

```text
[ ] Confirm official operational_start_date
[ ] Confirm new_odoo_branch classification
[ ] Update COMPANY_SOURCE when active
[ ] Update seed SQL
[ ] Update maintenance SQL
[ ] Apply MySQL policy update
[ ] Set active = True in ROLLOUT_COMPANY_EXPECTATIONS
[ ] Run rollout validation
[ ] Run full Purchases pipeline
```

---

# Related Documentation

```text
README.md
docs/project-status-and-todo.md
docs/project-technical-guide.md
docs/pipeline-logging-and-run-interpretation.md
docs/branch-rollout-playbook.md
docs/inventory-domain-closeout.md
docs/inventory-runbook.md
docs/purchases-company-migration-policy.md
docs/purchases-product-mapping-policy.md
docs/purchases-canonical-layer.md
docs/purchases-runbook.md
docs/wansoft-local-wsdl.md
```

---

# Recommended Commit

This document should be committed as part of the Section 13 documentation update.

Recommended commit when Section 13 is closed:

```bash
git add README.md docs/ scripts/ sql/ core/

git commit -m "docs(project): update orchestration plan for purchases pipeline and rollout validation"

git push
```