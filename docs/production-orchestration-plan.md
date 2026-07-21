# Production Orchestration Plan

## Purpose

This document defines the first production-style orchestration plan for the Wansoft + Odoo Data Warehouse and ETL Pipeline project.

The goal is to move from individually validated scripts to a controlled and repeatable execution flow.

This document does not implement automation by itself.

It defines:

```text
execution order
task classification
validation gates
safe automation candidates
controlled manual steps
logging requirements
failure handling
future orchestration structure
```

---

## Current Context

The project currently operates through validated scripts under:

```text
scripts/
```

This has been useful for step-by-step validation.

The next stage is to organise these validated scripts into repeatable workflows.

The project should not jump directly to full automation without validation gates.

---

## Orchestration Principle

Production orchestration should follow this principle:

```text
Automate extraction, transformation, loading, and validation.
Keep governance decisions controlled.
```

This means:

```text
ETL refreshes can be automated.
Dictionary promotions should remain manual or approval-based.
COMPANY_SOURCE changes should remain controlled.
Odoo writeback should not happen.
```

---

## Task Classification

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
automatic operational corrections in Odoo
```

---

# Proposed Execution Layers

## Layer 1: Governance Validation

Purpose:

```text
Confirm that source governance, company mapping, and environment assumptions are valid before loading data.
```

Recommended tasks:

```bash
python -m scripts.test_company_source_governance
python -m scripts.test_wansoft_purchase_subsidiary_mapping_report
```

Expected outputs:

```text
company source rules valid
Wansoft subsidiary mapping valid
internal providers handled correctly
Antenas and Cancun IDs correct
```

Failure handling:

```text
Stop orchestration if company source governance fails.
Stop orchestration if Wansoft subsidiary mapping has missing critical mappings.
```

---

## Layer 2: Inventory Refresh

Purpose:

```text
Refresh Odoo inventory snapshots and backlogs using controlled dictionary logic.
```

Recommended tasks:

```bash
python -m scripts.test_odoo_inventory_scope_classification
python -m scripts.test_odoo_inventory_etl
```

Optional diagnostic tasks:

```bash
python -m scripts.test_inventory_dictionary_lookup
python -m scripts.test_apply_inventory_dictionary
python -m scripts.test_inventory_not_found_analyzer
python -m scripts.test_inventory_not_found_priority_backlog
```

Failure handling:

```text
Stop if snapshot fails to load.
Warn if backlog increases unexpectedly.
Do not promote dictionary candidates automatically.
```

---

## Layer 3: Purchases Odoo Snapshot Refresh

Purpose:

```text
Refresh Odoo purchase technical snapshots.
```

Recommended tasks:

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

Recommended tasks:

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

Recommended tasks:

```bash
python -m scripts.test_canonical_purchase_odoo_etl
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
Stop if source_system coexistence validation fails.
Stop if Antenas source split fails.
```

---

## Layer 6: SQL Validation

Purpose:

```text
Validate canonical and inventory outputs after refresh.
```

Recommended validation areas:

```text
source-system coexistence
Antenas source split
Wansoft final-source companies
internal providers as vendors
internal providers not as final companies
inventory snapshot counts
inventory backlog counts
purchase mapping buckets
```

Expected behaviour:

```text
Validation results should be stored or exported.
```

Future recommendation:

```text
Create a validation script that runs key SQL checks and saves results.
```

Possible script:

```text
scripts/validate_purchases_canonical_layer.py
```

Possible table:

```text
etl_validation_result
```

---

# Proposed Orchestration Script Structure

Future orchestration scripts may follow this structure:

```text
scripts/run_inventory_pipeline.py
scripts/run_purchases_pipeline.py
scripts/run_full_datawarehouse_refresh.py
scripts/validate_canonical_outputs.py
```

---

## Proposed Purchases Orchestration

Suggested future script:

```text
scripts/run_purchases_pipeline.py
```

Suggested execution order:

```text
1. test_company_source_governance
2. test_odoo_purchase_etl
3. test_odoo_purchase_receipt_etl
4. test_purchase_inventory_mapping_backlog
5. test_purchase_backlog_product_reference_report
6. test_purchase_company_source_eligibility
7. test_canonical_purchase_odoo_etl
8. test_wansoft_purchase_subsidiary_mapping_report
9. test_canonical_purchase_wansoft_etl
10. run SQL validations
```

---

## Proposed Inventory Orchestration

Suggested future script:

```text
scripts/run_inventory_pipeline.py
```

Suggested execution order:

```text
1. test_odoo_inventory_scope_classification
2. test_odoo_inventory_etl
3. test_inventory_dictionary_lookup
4. test_apply_inventory_dictionary
5. test_inventory_not_found_analyzer
6. optional bridge reports
7. optional controlled promotions
8. rerun inventory ETL after approved promotions
9. run SQL validations
```

Important:

```text
Promotion scripts should not run automatically unless explicitly approved.
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

Possible table:

```text
etl_run_log
```

Suggested columns:

```sql
id
run_id
pipeline_name
step_name
source_system
target_table
started_at
finished_at
status
rows_affected
error_message
created_at
```

---

# Validation Result Requirements

Validation results should be stored in a structured way.

Possible table:

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
Antenas source split validation fails
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
```

---

## Manual Review Conditions

Manual review is required if:

```text
new unresolved products appear with high purchase amount
new source company appears
COMPANY_SOURCE requires update
internal provider appears in unexpected context
inventory valuation differences persist
Odoo operational errors affect data completeness
```

---

# Reload Strategy

## Source-System Isolation

Canonical tables should be refreshed by `source_system`.

Example:

```text
DELETE FROM canonical_purchase_order_snapshot
WHERE source_system = 'odoo';
```

or:

```text
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
[ ] No uncommitted risky code changes
[ ] Last successful run reviewed
[ ] Manual governance tasks are not accidentally included
```

---

# Post-Run Checklist

```text
[ ] Inventory snapshot counts reviewed
[ ] Inventory backlog reviewed
[ ] Odoo purchase snapshot counts reviewed
[ ] Odoo receipt snapshot counts reviewed
[ ] Odoo canonical counts reviewed
[ ] Wansoft canonical counts reviewed
[ ] Source-system coexistence validated
[ ] Antenas source split validated
[ ] Internal providers validated
[ ] New unmapped products reviewed
[ ] Run summary saved
```

---

# Initial Automation Recommendation

Recommended first automation target:

```text
Purchases pipeline orchestration
```

Reason:

```text
Purchases canonical layer is already validated.
Odoo and Wansoft source split is already working.
Validation queries are already defined.
Refresh by source_system is already implemented.
```

Second automation target:

```text
Inventory validation summary
```

Reason:

```text
Inventory is stable but still has controlled governance steps.
Dictionary promotions should not be fully automated yet.
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

# Related Documentation

```text
README.md
docs/project-status-and-todo.md
docs/project-technical-guide.md
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

```bash
git add README.md docs/

git commit -m "docs(project): add project status and orchestration plan"

git push
```