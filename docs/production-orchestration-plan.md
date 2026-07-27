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
inventory pipeline orchestration
purchases pipeline orchestration
```

---

## Current Context

The project originally operated through individual validation scripts under:

```text
scripts/
```

That approach was useful for discovery and step-by-step validation.

The project has now moved into controlled orchestration for two major domains:

```text
Purchases
Inventory
```

Current orchestration status:

```text
Purchases pipeline: implemented
Purchases canonical validation: implemented
Purchases JSON logging: implemented
Purchases rollout validation: implemented

Inventory pipeline: implemented
Inventory output validation: implemented
Inventory JSON logging: implemented
Inventory optional bridge reports: implemented
Inventory promotion automation: intentionally excluded

Production scheduling: pending
Power BI semantic layer: pending
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
Output validations can be automated.
JSON logging can be automated.
Bridge reports can be automated as diagnostics.
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
inventory scope classification
inventory snapshot refresh
inventory backlog generation
purchase backlog generation
validation query execution
row-count logging
source-system count logging
diagnostic export
bridge report generation
JSON run-log generation
canonical layer validation
inventory output validation
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

# Implemented Pipeline: Purchases

## Implemented Files

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

Expected successful summary:

```text
total_steps: 10
success: 10
dry_run: 0
failed_or_error: 0
required_failed_or_error: 0
PIPELINE RESULT: COMPLETED
```

Expected dry-run summary:

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

# Implemented Pipeline: Inventory

## Implemented Files

The Inventory orchestration script is:

```text
scripts/run_inventory_pipeline.py
```

Smoke test:

```text
scripts/test_run_inventory_pipeline.py
```

Final output validator:

```text
scripts/validate_inventory_outputs.py
```

Run logs:

```text
logs/inventory_pipeline_runs/
```

The logs are local execution artefacts and should not be committed.

Recommended `.gitignore` entry:

```gitignore
# Pipeline run logs
logs/
```

---

## Inventory Pipeline Execution Order

Current base Inventory pipeline order:

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

---

## Inventory Extended Pipeline With Bridge Reports

Inventory bridge reports are optional diagnostics.

Run:

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

Optional bridge modules:

```text
scripts.test_inventory_not_found_p1_bridge
scripts.test_inventory_not_found_p2_bridge
scripts.test_inventory_not_found_residual_bridge
```

These bridge reports are diagnostic only.

They do not promote dictionary mappings.

---

## Inventory Pipeline Current Status

Current Inventory orchestration status:

```text
dry-run validated
smoke test validated
real execution validated
optional bridge reports validated
JSON logging validated
inventory output validation integrated as required step
dictionary promotions excluded from default automation
```

Expected base successful summary:

```text
total_steps: 7
success: 7
dry_run: 0
skipped: 0
failed_or_error: 0
required_failed_or_error: 0
PIPELINE RESULT: COMPLETED
```

Expected base dry-run summary:

```text
total_steps: 7
success: 0
dry_run: 7
skipped: 0
failed_or_error: 0
required_failed_or_error: 0
PIPELINE RESULT: COMPLETED
```

Expected extended successful summary:

```text
total_steps: 10
success: 10
dry_run: 0
skipped: 0
failed_or_error: 0
required_failed_or_error: 0
PIPELINE RESULT: COMPLETED
```

---

## Inventory JSON Logging

The Inventory pipeline generates a local JSON log for each run.

Log folder:

```text
logs/inventory_pipeline_runs/
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
skipped
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

# Inventory Output Validation

The final Inventory pipeline step validates Inventory outputs.

Validator:

```text
scripts/validate_inventory_outputs.py
```

The validation currently checks:

```text
required inventory tables exist
inventory table counts are available
inventory scope distribution is available
inventory snapshot mapping distribution is available
inventory backlog distribution is available
residual not_found / pending_review visibility is available
inventory dictionary coverage is available
promotion scripts remain controlled and outside default automation
```

Current validation count:

```text
total_validations: 8
```

Expected result:

```text
VALIDATION RESULT: PASSED
```

If the validator fails, the Inventory pipeline should fail because this step is required.

---

## Inventory Validation Rules

The current validator uses these validation names:

```text
required_inventory_tables_exist
inventory_table_counts_available
inventory_scope_distribution_available
inventory_snapshot_mapping_distribution_available
inventory_backlog_distribution_available
inventory_residual_visibility_available
inventory_dictionary_coverage_available
inventory_promotions_controlled
```

Important backlog rule:

```text
If odoo_inventory_backlog exists and has 0 rows, this is valid.
```

Reason:

```text
An empty backlog may mean the current ETL produced no unresolved backlog rows.
```

Important promotion rule:

```text
Inventory dictionary promotions must remain manual and explicitly approved.
```

---

# Controlled Promotion Policy

Inventory dictionary promotion scripts are intentionally not part of the default pipeline.

Excluded from default automation:

```text
scripts.test_promote_inventory_bridge_to_dictionary
scripts.test_promote_inventory_not_found_p1_to_dictionary
scripts.test_promote_inventory_not_found_p2_to_dictionary
scripts.test_promote_inventory_not_found_residual_to_dictionary
```

Reason:

```text
Promotion changes dictionary governance.
Dictionary governance changes analytical interpretation.
Therefore, promotions require manual review and explicit approval.
```

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
Implemented
```

Implemented in Inventory pipeline:

```bash
python -m scripts.run_inventory_pipeline
```

Base steps:

```text
scope classification
inventory ETL
dictionary lookup validation
dictionary application validation
not_found analysis
priority backlog diagnostics
inventory output validation
```

Optional extended diagnostics:

```bash
python -m scripts.run_inventory_pipeline --include-bridge-reports
```

Important:

```text
Inventory dictionary promotions do not run automatically.
```

Failure handling:

```text
Stop if scope classification fails.
Stop if inventory ETL fails.
Stop if dictionary lookup or dictionary application validation fails.
Stop if inventory output validation fails.
Optional bridge reports may be handled with continue-on-optional-failure if needed.
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

## Layer 6: Output and Canonical Validation

Purpose:

```text
Validate final outputs after refresh.
```

Implemented Purchases validator:

```bash
python -m scripts.validate_purchases_canonical_layer
```

Implemented Inventory validator:

```bash
python -m scripts.validate_inventory_outputs
```

Purchases validation areas:

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

Inventory validation areas:

```text
required tables
table counts
scope distribution
snapshot mapping distribution
backlog distribution
residual visibility
dictionary coverage
controlled promotion policy
```

---

# Current Orchestration Script Structure

Current implemented scripts:

```text
scripts/run_purchases_pipeline.py
scripts/run_inventory_pipeline.py
```

Current smoke tests:

```text
scripts/test_run_purchases_pipeline.py
scripts/test_run_inventory_pipeline.py
```

Current validators:

```text
scripts/validate_purchases_canonical_layer.py
scripts/validate_inventory_outputs.py
```

Future orchestration scripts:

```text
scripts/run_full_datawarehouse_refresh.py
```

Future consolidated validators:

```text
scripts/validate_canonical_outputs.py
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
Inventory JSON logs
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

Inventory logs also include:

```text
skipped
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
inventory_promotions_controlled
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
inventory scope classification fails
inventory ETL fails
inventory output validation fails
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
optional bridge report fails and continue-on-optional-failure is enabled
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
inventory dictionary promotion is required
```

---

# Reload Strategy

## Source-System Isolation

Canonical purchase tables should be refreshed by `source_system`.

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
[ ] Purchases pipeline summary reviewed, if Purchases ran
[ ] Inventory pipeline summary reviewed, if Inventory ran
[ ] JSON log file created
[ ] required_failed_or_error = 0
[ ] Final validation passed
[ ] Source-system coexistence validated, if Purchases ran
[ ] Rollout company patterns validated, if Purchases ran
[ ] Inventory output validation passed, if Inventory ran
[ ] Internal providers validated, if Purchases ran
[ ] New unmapped products reviewed
[ ] Slowest step reviewed
[ ] Logs kept out of Git
```

---

# Initial Automation Recommendation

Current recommendation:

```text
Purchases pipeline and Inventory pipeline can remain the first automation candidates.
```

Reason:

```text
Purchases canonical layer is validated.
Purchases rollout validation is implemented.
Inventory pipeline is validated.
Inventory output validation is implemented.
Both pipelines generate JSON logs.
Required validation gates are integrated.
```

Scheduling should not be added until operational cadence and monitoring are defined.

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
[ ] Keep rollout playbook updated during future branch activations
```

---

## Inventory

Current status:

```text
Implemented and passing
```

Completed:

```text
[x] Create scripts/run_inventory_pipeline.py
[x] Create scripts/test_run_inventory_pipeline.py
[x] Create scripts/validate_inventory_outputs.py
[x] Add JSON logging for inventory pipeline
[x] Add logs/inventory_pipeline_runs/
[x] Integrate inventory validation as required final step
[x] Validate base pipeline real execution
[x] Validate extended pipeline with bridge reports
[x] Keep dictionary promotions excluded from automation
```

Pending improvements:

```text
[ ] Review whether validation results should be persisted to database
[ ] Review whether inventory bridge report performance needs optimisation as volume grows
[ ] Review whether catalog maintenance should remain standalone or become a read-only pre-check
[ ] Update project-level documentation after Section 14 closeout
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

This document should be committed as part of the Section 14 documentation update.

Recommended commit when Section 14 is ready to checkpoint:

```bash
git add docs/production-orchestration-plan.md docs/inventory-runbook.md scripts/run_inventory_pipeline.py scripts/test_run_inventory_pipeline.py scripts/validate_inventory_outputs.py

git commit -m "feat(inventory): add pipeline orchestration and output validation"

git push
```