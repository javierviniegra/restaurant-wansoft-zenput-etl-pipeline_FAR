# Inventory Runbook

## Purpose

This runbook explains how to operate, validate, and troubleshoot the Inventory domain ETL.

It is intended for day-to-day execution and technical validation of:

```text
Odoo inventory scope classification
Odoo inventory ETL
inventory dictionary lookup
inventory dictionary application
inventory backlog outputs
not_found diagnostics
bridge reports
inventory output validation
pipeline JSON logging
controlled promotion policy
```

This document is operational.

For architecture and design context, refer to:

```text
docs/project-technical-guide.md
docs/inventory-domain-closeout.md
docs/production-orchestration-plan.md
docs/pipeline-logging-and-run-interpretation.md
docs/branch-rollout-playbook.md
```

---

## Current Status

The Inventory domain now has a controlled orchestration pipeline.

Implemented:

```text
scripts/run_inventory_pipeline.py
scripts/test_run_inventory_pipeline.py
scripts/validate_inventory_outputs.py
```

Current status:

```text
dry-run validated
real pipeline execution validated
optional bridge reports validated
inventory output validation integrated as required final step
JSON run logging implemented
dictionary promotions excluded from default automation
```

Current pipeline result expectation:

```text
PIPELINE RESULT: COMPLETED
```

Current validator result expectation:

```text
VALIDATION RESULT: PASSED
```

---

## Inventory Architecture

The Inventory domain is built in layers:

```text
Odoo product and inventory data
    ↓
scope classification
    ↓
dictionary lookup
    ↓
inventory ETL
    ↓
snapshot and backlog outputs
    ↓
not_found diagnostics
    ↓
optional bridge reports
    ↓
inventory output validation
    ↓
JSON pipeline log
```

---

## Source Governance Rules

Inventory follows company-level source governance from:

```text
core/config/companies.py
```

Main source rules:

```text
Sales      -> always Wansoft
Purchases  -> COMPANY_SOURCE
Inventory  -> COMPANY_SOURCE
```

For Inventory:

```text
If COMPANY_SOURCE = 'odoo':
    Odoo is the final operational source for inventory.

If COMPANY_SOURCE = 'wansoft':
    Wansoft remains the final operational source for inventory.

If company_name is an internal provider:
    treat according to internal-provider governance.
```

Important:

```text
Inventory orchestration does not change COMPANY_SOURCE.
Inventory orchestration does not update Odoo.
Inventory orchestration does not promote dictionary mappings automatically.
```

---

## Current Inventory Scope Model

The Inventory domain uses scope-aware classification.

Current refined inventory scopes include:

```text
restaurantes
bodegon
empanadas
shared_cross_company
review_scope
operational_non_inventory
```

The purpose of scope classification is to prevent all products from being treated as one single universe.

Different product families require different governance behaviour.

---

## Main Inventory Tables

The key Inventory tables are:

```text
odoo_inventory_scope_classification
odoo_inventory_snapshot
odoo_inventory_backlog
inventory_mapping_dictionary
inventory_product_lifecycle
```

These tables are validated by:

```text
scripts/validate_inventory_outputs.py
```

---

## Current Inventory Baseline

Previously validated baseline:

```text
snapshot rows: 1660
residual functional not_found: 98 unique products
residual functional pending_review: 5 unique products
```

Current values may change after each ETL execution.

Use the current validator to review live output state:

```bash
python -m scripts.validate_inventory_outputs
```

---

# Recommended Execution Method

The recommended way to run the Inventory domain is now:

```bash
python -m scripts.run_inventory_pipeline
```

This executes the controlled base pipeline.

Before running the real pipeline, validate the orchestration structure with:

```bash
python -m scripts.run_inventory_pipeline --dry-run
```

---

# Inventory Pipeline Execution Order

The current base pipeline executes these steps:

```text
01. Odoo inventory scope classification
02. Odoo inventory ETL
03. Inventory dictionary lookup validation
04. Inventory dictionary application validation
05. Inventory not_found analyzer
06. Inventory not_found priority backlog
07. Inventory output validation
```

Modules executed:

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

## Dry Run

Run:

```bash
python -m scripts.run_inventory_pipeline --dry-run
```

Expected result:

```text
total_steps: 7
success: 0
dry_run: 7
skipped: 0
failed_or_error: 0
required_failed_or_error: 0

PIPELINE RESULT: COMPLETED
```

A dry run does not execute ETLs.

It validates:

```text
pipeline structure
step order
required or optional flags
summary generation
JSON log generation
```

---

## Real Pipeline Run

Run:

```bash
python -m scripts.run_inventory_pipeline
```

Expected result:

```text
total_steps: 7
success: 7
dry_run: 0
skipped: 0
failed_or_error: 0
required_failed_or_error: 0

PIPELINE RESULT: COMPLETED
```

If any required step fails, the pipeline should stop and return a failed result.

---

# Optional Bridge Reports

The Inventory pipeline can include optional bridge reports.

Run:

```bash
python -m scripts.run_inventory_pipeline --include-bridge-reports
```

This executes:

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

Expected result:

```text
total_steps: 10
success: 10
dry_run: 0
skipped: 0
failed_or_error: 0
required_failed_or_error: 0

PIPELINE RESULT: COMPLETED
```

Optional bridge modules:

```text
scripts.test_inventory_not_found_p1_bridge
scripts.test_inventory_not_found_p2_bridge
scripts.test_inventory_not_found_residual_bridge
```

These bridge reports are diagnostic.

They do not promote dictionary rows.

---

## Optional Failure Handling

If an optional diagnostic step fails, the default conservative behaviour may stop the pipeline.

To continue after optional failures, use:

```bash
python -m scripts.run_inventory_pipeline --include-bridge-reports --continue-on-optional-failure
```

Use this only when the failure is known to be non-critical.

Required steps should always stop the pipeline when they fail.

---

# Pipeline Logging

The Inventory pipeline generates a local JSON log for every execution.

Log folder:

```text
logs/inventory_pipeline_runs/
```

Example:

```text
logs/inventory_pipeline_runs/20260727_113332_3618c07a-8ec6-4eda-9b0a-1e29598d95f2.json
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

The logs are local execution artefacts.

They should not be committed.

Recommended `.gitignore` entry:

```gitignore
# Pipeline run logs
logs/
```

For detailed log interpretation, refer to:

```text
docs/pipeline-logging-and-run-interpretation.md
```

---

# How to Read a Successful Run

A successful real run should show:

```text
PIPELINE RESULT: COMPLETED
required_failed_or_error: 0
failed_or_error: 0
```

The JSON log should show:

```text
status = COMPLETED
dry_run = false
required_failed_or_error = 0
```

Step statuses should show:

```text
SUCCESS
```

for all required steps.

---

# How to Identify the Slowest Step

In the console summary or JSON log, review:

```text
duration_seconds
```

The slowest current optional step observed in the extended Inventory pipeline was:

```text
Inventory not_found P1 bridge report
```

Current observation:

```text
This is not a blocker.
It should be monitored if inventory volume grows.
```

Do not change business logic only to reduce runtime.

---

# Manual Execution Order

If the full pipeline is not needed, run the individual steps in this order.

---

## 1. Run Odoo Inventory Scope Classification

```bash
python -m scripts.test_odoo_inventory_scope_classification
```

Purpose:

```text
Classify Odoo inventory products into the appropriate inventory scopes.
```

Expected output:

```text
odoo_inventory_scope_classification
```

This step is required before interpreting inventory rows by business universe.

---

## 2. Run Odoo Inventory ETL

```bash
python -m scripts.test_odoo_inventory_etl
```

Purpose:

```text
Load Odoo inventory data into MySQL using scope-aware dictionary logic.
```

Expected outputs:

```text
odoo_inventory_snapshot
odoo_inventory_backlog
```

---

## 3. Validate Inventory Dictionary Lookup

```bash
python -m scripts.test_inventory_dictionary_lookup
```

Purpose:

```text
Validate dictionary lookup logic without promoting products.
```

This step checks dictionary access and mapping logic.

It does not modify dictionary governance.

---

## 4. Validate Inventory Dictionary Application

```bash
python -m scripts.test_apply_inventory_dictionary
```

Purpose:

```text
Validate how inventory dictionary logic applies to inventory rows.
```

This step confirms dictionary behaviour but does not perform promotions.

---

## 5. Run Inventory not_found Analyzer

```bash
python -m scripts.test_inventory_not_found_analyzer
```

Purpose:

```text
Analyze residual inventory products with not_found mapping status.
```

The goal is to preserve visibility of unresolved products.

---

## 6. Run Inventory not_found Priority Backlog

```bash
python -m scripts.test_inventory_not_found_priority_backlog
```

Purpose:

```text
Build or validate priority backlog diagnostics for unresolved inventory products.
```

This step is diagnostic.

It does not promote products.

---

## 7. Run Inventory Output Validation

```bash
python -m scripts.validate_inventory_outputs
```

Expected result:

```text
VALIDATION RESULT: PASSED
```

The full inventory pipeline should not be considered successful unless this validation passes.

---

# Optional Manual Bridge Report Execution

Bridge reports can be run individually.

## P1 Bridge Report

```bash
python -m scripts.test_inventory_not_found_p1_bridge
```

## P2 Bridge Report

```bash
python -m scripts.test_inventory_not_found_p2_bridge
```

## Residual Bridge Report

```bash
python -m scripts.test_inventory_not_found_residual_bridge
```

These reports are for diagnostics and review.

They do not promote dictionary mappings.

---

# Inventory Output Validation

The final validator is:

```text
scripts/validate_inventory_outputs.py
```

Run:

```bash
python -m scripts.validate_inventory_outputs
```

Current validations:

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

Expected result:

```text
total_validations: 8
passed: 8
failed: 0

VALIDATION RESULT: PASSED
```

---

## 1. required_inventory_tables_exist

Validates that the key Inventory tables exist:

```text
odoo_inventory_scope_classification
odoo_inventory_snapshot
odoo_inventory_backlog
inventory_mapping_dictionary
inventory_product_lifecycle
```

If any required table is missing, validation fails.

---

## 2. inventory_table_counts_available

Validates row counts for required Inventory tables.

Core tables expected to have rows:

```text
odoo_inventory_scope_classification
odoo_inventory_snapshot
inventory_mapping_dictionary
```

The backlog table may be empty and still valid, depending on current ETL output.

---

## 3. inventory_scope_distribution_available

Validates that scope distribution is visible.

This helps confirm that products are classified into business scopes.

Expected scope-like values may include:

```text
restaurantes
bodegon
empanadas
shared_cross_company
review_scope
operational_non_inventory
```

---

## 4. inventory_snapshot_mapping_distribution_available

Validates that mapping status distribution is visible in:

```text
odoo_inventory_snapshot
```

This confirms the project can inspect mapped, not_found, pending_review, or equivalent inventory mapping states.

---

## 5. inventory_backlog_distribution_available

Validates the inventory backlog output.

Important rule:

```text
If odoo_inventory_backlog exists and has 0 rows, this is valid.
```

Reason:

```text
An empty backlog may mean the current ETL produced no unresolved backlog rows.
```

Validation logic:

```text
table does not exist -> FAIL
table exists and is empty -> PASS with note
table exists and has rows -> PASS if distribution can be shown
```

---

## 6. inventory_residual_visibility_available

Validates that residual statuses such as:

```text
not_found
pending_review
open
review
```

remain visible when present.

This is important because residual visibility is part of governance.

---

## 7. inventory_dictionary_coverage_available

Validates that the dictionary table can provide coverage visibility.

Table:

```text
inventory_mapping_dictionary
```

The script attempts to summarise available dictionary status or scope columns.

---

## 8. inventory_promotions_controlled

Validates the governance rule that dictionary promotions are excluded from default automation.

Promotion scripts are intentionally not part of the default pipeline:

```text
scripts.test_promote_inventory_bridge_to_dictionary
scripts.test_promote_inventory_not_found_p1_to_dictionary
scripts.test_promote_inventory_not_found_p2_to_dictionary
scripts.test_promote_inventory_not_found_residual_to_dictionary
```

Expected validation result:

```text
inventory_promotions_controlled: PASS
```

---

# Controlled Promotion Policy

Inventory dictionary promotions must remain manual and explicitly approved.

The following scripts must not be included in the default inventory pipeline:

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

# What the Pipeline Does Not Do

The Inventory pipeline does not:

```text
promote dictionary mappings
update Odoo
change COMPANY_SOURCE
schedule itself
modify product categories
merge products
write operational corrections
replace manual governance review
```

This is intentional.

---

# Troubleshooting

## Syntax or Encoding Issues

If a Python file contains escaped HTML such as:

```text
-&gt;
&lt;
&gt;
```

replace those values with normal Python syntax or remove the affected return annotation.

Example problem:

```python
def get_table_columns(table_name: str) -&gt; List"""
```

Correct pattern:

```python
def get_table_columns(table_name: str):
```

or:

```python
def get_table_columns(table_name: str) -> List```

---

## Backlog Distribution Fails

If:

```text
inventory_backlog_distribution_available: FAIL
```

check whether:

```text
odoo_inventory_backlog exists
odoo_inventory_backlog has rows
column names match the validator expectations
```

An empty backlog should not fail validation if the table exists.

Current intended rule:

```text
empty backlog table = PASS
missing backlog table = FAIL
```

---

## Snapshot Mapping Distribution Fails

If:

```text
inventory_snapshot_mapping_distribution_available: FAIL
```

check the columns in:

```text
odoo_inventory_snapshot
```

The validator searches for status-like columns such as:

```text
inventory_mapping_status
mapping_status
dictionary_status
match_status
mapped_status
```

If the real table uses another column name, update:

```text
scripts/validate_inventory_outputs.py
```

---

## Scope Distribution Fails

If:

```text
inventory_scope_distribution_available: FAIL
```

check the columns in:

```text
odoo_inventory_scope_classification
```

The validator searches for scope-like columns such as:

```text
inventory_scope
refined_inventory_scope
product_scope
scope
scope_bucket
```

If the real table uses another column name, update:

```text
scripts/validate_inventory_outputs.py
```

---

## Dictionary Coverage Fails

If:

```text
inventory_dictionary_coverage_available: FAIL
```

check whether:

```text
inventory_mapping_dictionary exists
inventory_mapping_dictionary has rows
dictionary status or scope columns exist
```

The validator can still pass with a simple total count if detailed status columns are unavailable.

---

## Optional Bridge Report Fails

Bridge reports are optional diagnostics.

If one fails, review the failing step.

You may rerun the pipeline with:

```bash
python -m scripts.run_inventory_pipeline --include-bridge-reports --continue-on-optional-failure
```

Use this only when the failure is known to be non-critical.

---

# Recommended Execution Checklist

Use this checklist when running the Inventory domain.

```text
[ ] Confirm .env is loaded
[ ] Confirm MySQL connection
[ ] Confirm Odoo connection
[ ] Confirm current Git branch
[ ] Confirm no uncommitted risky changes
[ ] Confirm logs/ is ignored by Git
[ ] Run inventory pipeline dry-run
[ ] Run real inventory pipeline
[ ] Confirm pipeline summary
[ ] Confirm JSON log file was generated
[ ] Confirm final validation passed
[ ] Review optional bridge reports if included
[ ] Confirm no promotion script was executed automatically
[ ] Keep logs out of Git
```

---

# Current Inventory Pipeline Status

Current state:

```text
Inventory pipeline is implemented.
Inventory pipeline dry-run works.
Inventory pipeline smoke test works.
Inventory pipeline real execution works.
Inventory bridge reports work.
Inventory output validation is integrated as required.
JSON logging is implemented.
Promotion scripts remain excluded from default automation.
```

Current known pending work:

```text
document Section 14 updates in project-level docs
review whether Inventory validator should persist validation results later
review whether Inventory logs should be added to future database logging
review bridge report performance if volume grows
```

---

# Current Validated Pipeline Results

Base pipeline validated:

```text
total_steps: 7
success: 7
dry_run: 0
skipped: 0
failed_or_error: 0
required_failed_or_error: 0

PIPELINE RESULT: COMPLETED
```

Extended pipeline with bridge reports validated:

```text
total_steps: 10
success: 10
dry_run: 0
skipped: 0
failed_or_error: 0
required_failed_or_error: 0

PIPELINE RESULT: COMPLETED
```

Inventory validation validated:

```text
total_validations: 8
passed: 8
failed: 0

VALIDATION RESULT: PASSED
```

---

# Related Documentation

```text
docs/project-technical-guide.md
docs/project-status-and-todo.md
docs/production-orchestration-plan.md
docs/pipeline-logging-and-run-interpretation.md
docs/inventory-domain-closeout.md
docs/purchases-runbook.md
docs/purchases-canonical-layer.md
docs/branch-rollout-playbook.md
```

---

# Related Files

```text
scripts/run_inventory_pipeline.py
scripts/test_run_inventory_pipeline.py
scripts/validate_inventory_outputs.py
scripts/test_odoo_inventory_scope_classification.py
scripts/test_odoo_inventory_etl.py
scripts/test_inventory_dictionary_lookup.py
scripts/test_apply_inventory_dictionary.py
scripts/test_inventory_not_found_analyzer.py
scripts/test_inventory_not_found_priority_backlog.py
scripts/test_inventory_not_found_p1_bridge.py
scripts/test_inventory_not_found_p2_bridge.py
scripts/test_inventory_not_found_residual_bridge.py
```

---

# Recommended Commit

This document should be committed as part of the Section 14 documentation update.

Recommended commit when Section 14 is ready to checkpoint:

```bash
git status

git add docs/inventory-runbook.md scripts/run_inventory_pipeline.py scripts/test_run_inventory_pipeline.py scripts/validate_inventory_outputs.py

git status

git commit -m "feat(inventory): add pipeline orchestration, logging and output validation"

git push
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

