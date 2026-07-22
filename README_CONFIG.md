# Odoo Catalog Maintenance Configuration

## Purpose

This document describes the Odoo Catalog Maintenance process used before ETL execution.

Its purpose is to document how catalog preparation, product lifecycle review, and product classification should be handled before loading data from Odoo into MySQL.

This file is complementary to:

```text
README.md
docs/project-technical-guide.md
docs/project-status-and-todo.md
docs/inventory-runbook.md
docs/purchases-product-mapping-policy.md
docs/production-orchestration-plan.md
```

---

## Current Status

This document currently describes a pre-ETL catalog maintenance process.

Current project principle:

```text
Odoo is treated as a read-only source for ETL pipelines.
Catalog governance decisions are stored in MySQL.
Automatic writeback to Odoo should not happen inside ETL pipelines.
```

Therefore, any catalog maintenance process that modifies Odoo directly must be treated as:

```text
controlled
manual or explicitly approved
outside the normal ETL pipeline
not part of the Purchases orchestration baseline
```

---

## Relationship With Current Pipelines

### Purchases Pipeline

The Purchases pipeline is implemented in:

```text
scripts/run_purchases_pipeline.py
```

The Purchases pipeline does not perform Odoo catalog maintenance.

It uses existing Odoo product data and applies mapping through MySQL dictionaries.

Purchases product mapping is governed by:

```text
docs/purchases-product-mapping-policy.md
```

Key rule:

```text
Explicit reference beats name similarity.
```

Products without explicit approved mapping remain as:

```text
new products
unmapped products
backlog candidates
```

The pipeline does not create aliases automatically and does not update Odoo.

---

### Inventory Pipeline

Inventory currently does not yet have a full orchestration pipeline equivalent to Purchases.

Pending future files:

```text
scripts/run_inventory_pipeline.py
scripts/test_run_inventory_pipeline.py
scripts/validate_inventory_outputs.py
logs/inventory_pipeline_runs/
```

This catalog maintenance process may become relevant to the future Inventory pipeline, but it should not be automatically integrated until reviewed.

Pending decision:

```text
Should Odoo Catalog Maintenance remain a separate controlled pre-ETL process?
Or should specific read-only diagnostics be integrated into the future Inventory pipeline?
```

---

## Current Governance Position

Current recommended governance position:

```text
Catalog diagnostics are safe to automate.
Catalog writeback is not safe to automate by default.
```

Safe to automate:

```text
extract Odoo products
identify products without integration codes
classify products by sale/inventory/inactive status
detect potential lifecycle issues
generate review datasets
generate backlog reports
compare against MySQL dictionaries
```

Keep controlled:

```text
updating sale_ok in Odoo
editing Odoo products
merging products
marking products as obsolete
creating aliases
promoting dictionary mappings
changing product references
changing product categories in Odoo
```

---

## Overview

The Odoo Catalog Maintenance process helps review catalog conditions before running ETL jobs from Odoo into MySQL.

It is intended to help identify:

```text
Odoo products without integration codes
products that should not belong to the sales domain
non-sale inventory products
product lifecycle issues
presentation changes
possible replacement candidates
catalog inconsistencies that require review
```

The process should support ETL quality without forcing automatic changes into Odoo.

---

## Key Principles

### 1. Wansoft Defines Sales

```text
Wansoft defines what is sold.
Odoo supports inventory, purchases, accounting, and operational workflows.
```

Sales remains Wansoft.

This means:

```text
Sales product governance must not depend only on Odoo names.
Public-sale product equivalence must be controlled.
```

---

### 2. Odoo Is Read-Only for ETL Baseline

The ETL baseline should not update Odoo.

Current rule:

```text
No ETL pipeline should write back to Odoo products, references, catalog fields, inventory quantities, or accounting records.
```

If direct Odoo catalog cleanup is required, it must be handled as a controlled operational task outside the automated ETL baseline.

---

### 3. MySQL Stores Governance Decisions

Catalog governance should be represented in MySQL dictionaries and supporting tables.

Examples:

```text
inventory_mapping_dictionary
inventory_product_lifecycle
odoo_inventory_scope_classification
odoo_inventory_backlog
odoo_purchase_inventory_mapping_backlog
```

This allows the project to preserve source data and keep transformation decisions auditable.

---

### 4. Detection Does Not Equal Approval

The catalog maintenance process may detect issues.

Detection does not automatically mean:

```text
merge products
replace products
change Odoo records
promote mappings
update dictionary rows
```

Any action that changes business interpretation must be reviewed.

---

## Execution Flow

Recommended controlled flow:

```text
1. Extract Odoo products.
2. Identify products without integration codes.
3. Classify product domain relevance.
4. Detect potential product replacements or presentation changes.
5. Review lifecycle candidates.
6. Generate review datasets.
7. Load findings into MySQL review/backlog tables when applicable.
8. Run ETL only after review or accepted baseline.
```

---

## Expected Diagnostic Outputs

The process may generate outputs such as:

```text
products without integration code
non-sale products
inventory candidates
sales reference candidates
historical product candidates
replacement candidates
presentation change candidates
review datasets
```

These outputs should be reviewed before taking action.

---

## Development Setup

Set environment variable:

```env
ENV=dev
```

Expected command, if the script is available:

```bash
python -m scripts.run_odoo_catalog_maintenance
```

Important:

```text
Confirm the script exists before running.
Confirm whether it is read-only or write-enabled.
Do not run write-enabled catalog maintenance unless explicitly approved.
```

---

## Production Setup

Set environment variable:

```env
ENV=prod
```

Before running any production catalog maintenance:

```text
Confirm the script exists.
Confirm whether the script writes to Odoo or only generates reports.
Confirm backups are available if any writeback is involved.
Confirm the action has been approved.
Confirm the task is outside normal ETL automation.
```

---

## Backup Before Any Write-Enabled Execution

If a controlled catalog maintenance process modifies MySQL governance tables, create backups first.

Example MySQL backup pattern:

```sql
CREATE TABLE backup_product_catalog_mapping AS
SELECT *
FROM product_catalog_mapping;
```

If the process directly modifies Odoo tables or Odoo records, do not proceed without an approved operational backup and rollback plan.

Important:

```text
Direct Odoo writes are not part of the ETL baseline.
```

---

## Run Catalog Maintenance

Development or approved controlled execution:

```bash
python -m scripts.run_odoo_catalog_maintenance
```

Before running, confirm:

```text
[ ] ENV is correct
[ ] .env is loaded
[ ] Odoo connection is valid
[ ] MySQL connection is valid
[ ] Script mode is understood
[ ] Writeback behaviour is known
[ ] Backups exist if writeback is enabled
[ ] Output datasets are reviewed after execution
```

---

## After Maintenance

Review the following outputs, if generated:

```text
product_replacement_candidates
product_catalog_mapping
Odoo products without integration code
inventory mapping candidates
sales reference candidates
lifecycle candidates
review datasets
```

Only after validation should downstream ETLs run.

Recommended downstream checks:

```text
python -m scripts.test_odoo_inventory_scope_classification
python -m scripts.test_odoo_inventory_etl
python -m scripts.test_purchase_inventory_mapping_backlog
python -m scripts.run_purchases_pipeline --dry-run
```

---

## Lifecycle Rules

Suggested lifecycle categories:

```text
active
historical
replaced
obsolete
pending_review
```

Meaning:

```text
active:
    Current product used operationally.

historical:
    Old product version preserved for traceability.

replaced:
    Product appears to have a newer equivalent or presentation.

obsolete:
    Product is no longer used and should not be treated as active.

pending_review:
    Product requires manual validation before classification.
```

---

## Replacement Detection

Replacement detection may identify possible product changes such as:

```text
750 ml to 700 ml
old presentation to new presentation
minor naming changes
brand or packaging changes
```

Important:

```text
Replacement detection does not automatically merge products.
Replacement detection does not automatically update Odoo.
Replacement detection does not automatically promote dictionary mappings.
```

Detected candidates should be reviewed and approved before any governance update.

---

## Product Scope Considerations

Catalog maintenance should consider that products may belong to different business scopes.

Examples:

```text
sales products
inventory products
purchase products
Bodegón products
Empanadas products
shared cross-company products
operational non-inventory products
review scope products
```

Inventory scope is documented in:

```text
docs/inventory-domain-closeout.md
docs/inventory-runbook.md
```

Purchases product mapping is documented in:

```text
docs/purchases-product-mapping-policy.md
```

---

## Relationship With Inventory Domain

The Inventory domain uses scope-aware and dictionary-governed logic.

Relevant concepts:

```text
inventory_mapping_dictionary
inventory_product_lifecycle
odoo_inventory_scope_classification
odoo_inventory_snapshot
odoo_inventory_backlog
```

Catalog maintenance may support Inventory by identifying:

```text
new inventory candidates
products without integration code
historical products
products requiring scope review
products requiring dictionary review
```

However:

```text
Inventory dictionary promotions must remain controlled.
```

Future Inventory pipeline should decide whether catalog maintenance diagnostics should be included as a pre-check.

---

## Relationship With Purchases Domain

Purchases uses Odoo product IDs and MySQL dictionary mapping.

Current rule:

```text
Odoo purchase products map through inventory_mapping_dictionary when explicit approved mapping exists.
```

If a purchase product has no approved mapping:

```text
it remains unmapped
it may appear in odoo_purchase_inventory_mapping_backlog
it should not be automatically mapped by similar name
```

This supports the policy:

```text
Explicit reference beats name similarity.
```

---

## Relationship With Sales Domain

Sales remains Wansoft.

The catalog maintenance process should not redefine the sales universe from Odoo alone.

Current rule:

```text
Sales always remain Wansoft.
```

Odoo product metadata can support analysis, but sales product truth remains Wansoft.

---

## Current Pipeline Compatibility

### Purchases

Current Purchases pipeline:

```text
scripts/run_purchases_pipeline.py
```

Status:

```text
implemented
validated
JSON logging enabled
canonical validation required
rollout validation enabled
```

Catalog maintenance is not a step in the current Purchases pipeline.

---

### Inventory

Future Inventory pipeline:

```text
scripts/run_inventory_pipeline.py
```

Status:

```text
pending
```

Catalog maintenance may be reviewed as a possible pre-ETL diagnostic step for Inventory.

Pending tasks:

```text
[ ] Confirm whether catalog maintenance remains standalone.
[ ] Confirm whether read-only diagnostics should be integrated into Inventory pipeline.
[ ] Confirm whether write-enabled catalog cleanup should remain manual only.
```

---

## Logging

The current Purchases pipeline writes JSON logs to:

```text
logs/purchases_pipeline_runs/
```

Future Inventory pipeline should write logs to:

```text
logs/inventory_pipeline_runs/
```

Catalog maintenance currently does not have a documented JSON logging standard.

Future recommendation:

```text
If catalog maintenance remains active, add run_id and JSON log support.
```

Possible future log folder:

```text
logs/catalog_maintenance_runs/
```

---

## Git Policy

Logs should not be committed.

Recommended `.gitignore` entry:

```gitignore
# Pipeline run logs
logs/
```

Generated review datasets should be handled carefully.

Do not commit sensitive operational exports unless intentionally versioned and sanitized.

---

## What Is Safe to Automate

Safe automation candidates:

```text
catalog diagnostics
read-only product extraction
products without integration code report
replacement candidate report
lifecycle candidate report
scope review report
MySQL review dataset generation
```

---

## What Should Remain Controlled

Controlled actions:

```text
Odoo writeback
sale_ok updates
product merges
product deletion
product category changes
dictionary promotions
automatic alias creation
lifecycle status changes that affect reporting
```

These should require explicit approval.

---

## Current Open Questions

The following items should be reviewed before treating README_CONFIG.md as fully current:

```text
[ ] Confirm scripts.run_odoo_catalog_maintenance still exists.
[ ] Confirm whether the script is read-only or write-enabled.
[ ] Confirm whether sale_ok changes are still allowed.
[ ] Confirm whether product_catalog_mapping is still used.
[ ] Confirm whether product_replacement_candidates is still used.
[ ] Confirm whether catalog maintenance should be part of Inventory pipeline.
[ ] Confirm whether catalog maintenance needs JSON logging.
```

---

## Recommended Current Position

Until reviewed, treat this process as:

```text
controlled pre-ETL catalog diagnostics
not part of automated Purchases pipeline
candidate for future Inventory pre-check
writeback disabled unless explicitly approved
```

---

## Related Documentation

```text
README.md
docs/project-technical-guide.md
docs/project-status-and-todo.md
docs/production-orchestration-plan.md
docs/inventory-domain-closeout.md
docs/inventory-runbook.md
docs/purchases-product-mapping-policy.md
docs/purchases-runbook.md
docs/pipeline-logging-and-run-interpretation.md
```

---

## Related Future Work

```text
Inventory pipeline orchestration
Inventory output validation
Inventory JSON logging
Catalog maintenance review
Catalog maintenance logging
Catalog maintenance integration decision
```

---

## Recommended Commit

When Section 13 is closed:

```bash
git status

git add README.md README_CONFIG.md docs/ scripts/ sql/ core/

git status

git commit -m "docs(project): finalize section 13 purchases orchestration and rollout documentation"

git push
```