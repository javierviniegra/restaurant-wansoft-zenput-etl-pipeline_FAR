# Project Status and TODO

## Purpose

This document explains the current status of the Wansoft + Odoo Data Warehouse and ETL Pipeline project.

It answers three practical questions:

```text
Where are we now?
What has already been completed?
What is still pending?
```

This document should be used as the main project checkpoint before continuing with Inventory orchestration, Power BI integration, production scheduling, or additional branch rollouts.

---

## Current Project Phase

The project is currently between:

```text
validated domain ETLs
```

and:

```text
controlled orchestration and BI consumption
```

The project is no longer in early discovery.

The following foundations are already in place:

```text
Odoo read-only extraction
Wansoft source integration strategy
MySQL governance layer
inventory dictionary governance
company source governance
purchase canonical layer
purchase orchestration pipeline
purchase canonical validation
JSON pipeline logging
branch rollout validation
technical documentation package
```

The next major project stage is:

```text
controlled orchestration across domains
```

This means:

```text
keep Purchases pipeline stable
build Inventory pipeline equivalent
add Inventory validation
add Inventory JSON logging
prepare Power BI consumption
keep manual governance decisions controlled
```

---

## Current Overall Status

| Area | Status |
|---|---|
| Sales | Functionally established |
| Inventory | Technically stable and functionally advanced |
| Purchases | Canonical layer implemented, orchestrated and validated |
| Wansoft SOAP/WSDL | Local WSDL setup documented |
| Purchases pipeline | Implemented and validated |
| Purchases JSON logging | Implemented |
| Purchases rollout validation | Implemented |
| Branch rollout playbook | Created |
| Pipeline log interpretation | Created |
| Inventory pipeline | Pending |
| Inventory validation | Pending |
| Inventory JSON logging | Pending |
| Power BI semantic layer | Pending |
| Production scheduling | Pending |
| Controlled governance process | Partially defined, needs operating cadence |

---

# Completed Work

## 1. Repository Architecture

Completed:

```text
core/
analysis/
extract/
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

## 3. MySQL Governance Layer

Completed:

```text
MySQL stores dictionaries, snapshots, canonical tables, backlogs, lifecycle outputs, and company policies.
```

Main governance objects include:

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
```

Important validated rule:

```text
operational_start_date only applies when COMPANY_SOURCE = 'odoo'
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
```

Current validated baseline:

```text
snapshot rows: 1660
residual functional not_found: 98 unique products
residual functional pending_review: 5 unique products
```

Status:

```text
Inventory is technically stable.
Inventory is good enough to support Purchases.
Residual products remain visible and controlled.
```

Pending:

```text
Inventory orchestration pipeline.
Inventory consolidated validator.
Inventory JSON logging.
Inventory production-style runbook update.
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

## 9. Purchases Pipeline Orchestration

Completed:

```text
scripts/run_purchases_pipeline.py
scripts/test_run_purchases_pipeline.py
```

Current pipeline steps:

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

Validated execution modes:

```text
dry-run
real execution
```

Expected successful result:

```text
PIPELINE RESULT: COMPLETED
```

---

## 10. Purchases Canonical Validation

Completed:

```text
scripts/validate_purchases_canonical_layer.py
```

Current validations:

```text
1. source_system_coexistence
2. antenas_source_split
3. wansoft_final_source_companies
4. internal_providers_as_vendors
5. internal_providers_not_as_companies
6. mapping_distribution_available
7. table_counts_available
8. rollout_company_patterns
```

Expected result:

```text
total_validations: 8
passed: 8
failed: 0
VALIDATION RESULT: PASSED
```

This validator is integrated as a required final step in:

```text
scripts/run_purchases_pipeline.py
```

If validation fails:

```text
Purchases pipeline fails.
```

---

## 11. JSON Pipeline Logging

Completed for Purchases.

Implemented in:

```text
scripts/run_purchases_pipeline.py
```

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

Documentation created:

```text
docs/pipeline-logging-and-run-interpretation.md
```

Required `.gitignore` rule:

```gitignore
# Pipeline run logs
logs/
```

---

## 12. Branch Rollout Validation

Completed for Purchases.

Implemented in:

```text
scripts/validate_purchases_canonical_layer.py
```

Configuration:

```text
ROLLOUT_COMPANY_EXPECTATIONS
```

Supported rollout types:

```text
migrated_from_wansoft
new_odoo_branch
```

Current active rollout validations:

```text
Antenas:
    rollout_type = migrated_from_wansoft
    active = True
    pattern = PASS

La Esquina Coyoacán:
    rollout_type = migrated_from_wansoft
    active = True
    pattern = PASS

CentroMyJ:
    rollout_type = new_odoo_branch
    active = True
    pattern = PASS
```

Current inactive future rollout:

```text
Puebla:
    rollout_type = new_odoo_branch
    active = False
    skipped by validation
```

Rollout playbook created:

```text
docs/branch-rollout-playbook.md
```

---

## 13. Documentation Package

Current documentation set:

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
docs/wansoft-local-wsdl.md
```

New or updated in Section 13:

```text
scripts/run_purchases_pipeline.py
scripts/test_run_purchases_pipeline.py
scripts/validate_purchases_canonical_layer.py
docs/pipeline-logging-and-run-interpretation.md
docs/branch-rollout-playbook.md
docs/production-orchestration-plan.md
docs/purchases-runbook.md
docs/purchases-canonical-layer.md
docs/purchases-company-migration-policy.md
docs/project-technical-guide.md
README.md
docs/project-status-and-todo.md
```

Pending documentation update:

```text
README_CONFIG.md
```

Reason:

```text
README_CONFIG.md currently documents Odoo Catalog Maintenance Pre-ETL.
It should be reviewed and aligned with current orchestration and documentation structure.
```

Recommended future step:

```text
Paso 13.16 — Actualizar README_CONFIG.md
```

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

# Current TODO

## Priority 1: Finish Section 13 Documentation Consistency

Status:

```text
Nearly complete
```

TODO:

```text
[x] Add docs/pipeline-logging-and-run-interpretation.md
[x] Add docs/branch-rollout-playbook.md
[x] Update docs/production-orchestration-plan.md
[x] Update docs/purchases-runbook.md
[x] Update docs/purchases-canonical-layer.md
[x] Update docs/purchases-company-migration-policy.md
[x] Update docs/project-technical-guide.md
[x] Update README.md
[x] Update docs/project-status-and-todo.md
[ ] Update README_CONFIG.md
[ ] Review git status
[ ] Commit Section 13 package
```

---

## Priority 2: Puebla Future Rollout

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

## Priority 3: Inventory Pipeline Orchestration

Status:

```text
Pending
```

Inventory currently has domain scripts and documentation, but it does not yet have a pipeline equivalent to Purchases.

Pending files:

```text
scripts/run_inventory_pipeline.py
scripts/test_run_inventory_pipeline.py
scripts/validate_inventory_outputs.py
logs/inventory_pipeline_runs/
```

TODO:

```text
[ ] Design scripts/run_inventory_pipeline.py
[ ] Create dry-run support for inventory pipeline
[ ] Create scripts/test_run_inventory_pipeline.py
[ ] Create scripts/validate_inventory_outputs.py
[ ] Add JSON logging for inventory pipeline
[ ] Add inventory pipeline logs under logs/inventory_pipeline_runs/
[ ] Add inventory pipeline steps to docs/inventory-runbook.md
[ ] Add inventory pipeline strategy to docs/production-orchestration-plan.md
[ ] Add inventory pipeline pending status to README.md
[ ] Add inventory pipeline pending status to docs/project-technical-guide.md
```

Expected future Inventory pipeline pattern:

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

Important rule:

```text
Inventory dictionary promotions must not run automatically unless explicitly approved.
```

---

## Priority 4: Inventory Validation Outputs

Status:

```text
Pending
```

TODO:

```text
[ ] Validate odoo_inventory_snapshot counts
[ ] Validate odoo_inventory_backlog counts
[ ] Validate mapping status distribution
[ ] Validate residual not_found products
[ ] Validate pending_review products
[ ] Validate scope classification distribution
[ ] Validate dictionary coverage
[ ] Store inventory validation summary in console output
[ ] Later store inventory validation summary in JSON log
```

Possible future validator:

```text
scripts/validate_inventory_outputs.py
```

---

## Priority 5: Pipeline Logging Expansion

Status:

```text
Purchases implemented
Inventory pending
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

Pending for Inventory:

```text
[ ] Add same logging schema to inventory pipeline
[ ] Use pipeline_name = inventory_pipeline
[ ] Use logs/inventory_pipeline_runs/
[ ] Keep logs ignored by Git
```

Current `.gitignore` recommendation:

```gitignore
# Pipeline run logs
logs/
```

---

## Priority 6: Future Production Logging Table

Status:

```text
Pending
```

Current logging is file-based JSON.

Future database logging may use:

```text
etl_run_log
etl_validation_result
```

TODO:

```text
[ ] Decide whether JSON logs are enough for first production phase
[ ] Design etl_run_log table
[ ] Design etl_validation_result table
[ ] Add run_id as bridge between console, JSON and database logs
[ ] Add step-level row counts when available
[ ] Add validation result persistence when available
```

---

## Priority 7: Wansoft Canonical Performance Review

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

## Priority 8: README_CONFIG.md Review

Status:

```text
Pending
```

Current purpose:

```text
README_CONFIG.md documents Odoo Catalog Maintenance Pre-ETL.
```

TODO:

```text
[ ] Review whether README_CONFIG.md is still current
[ ] Confirm if scripts.run_odoo_catalog_maintenance still exists and is active
[ ] Confirm how Odoo catalog maintenance relates to current Inventory and Purchases flows
[ ] Update terminology to match current documentation
[ ] Add references to README.md and docs/project-technical-guide.md if still relevant
[ ] Clarify that catalog maintenance is pre-ETL and not part of Purchases pipeline
[ ] Confirm whether this process should be integrated into future Inventory pipeline or remain separate
```

Recommended future step:

```text
Paso 13.16 — Actualizar README_CONFIG.md
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
```

Reason:

```text
These actions represent governance or operational decisions, not mechanical ETL refreshes.
```

---

# Suggested Next Work Sequence

Recommended next sequence:

```text
1. Update README_CONFIG.md
2. Review git status
3. Commit Section 13 package
4. Start Inventory pipeline design
5. Create Inventory validator
6. Add Inventory JSON logging
7. Review Wansoft canonical performance
8. Prepare Puebla rollout activation when operationally ready
9. Define Power BI consumption layer
```

---

# Current Decision Point

The project has completed the first operational orchestration pattern for Purchases.

The next technical decision is whether to prioritise:

```text
Inventory pipeline orchestration
```

or:

```text
Power BI semantic modelling
```

Recommended priority:

```text
Inventory pipeline orchestration first
Power BI modelling second
```

Reason:

```text
Power BI should consume stable, repeatable, validated outputs from all required domains.
```

---

# Section 13 Closeout Criteria

Section 13 can be considered complete when:

```text
[x] run_purchases_pipeline.py is implemented
[x] test_run_purchases_pipeline.py passes
[x] validate_purchases_canonical_layer.py has 8 passing validations
[x] JSON logging works for dry-run and real runs
[x] pipeline logs are ignored by Git
[x] branch-rollout-playbook.md exists
[x] pipeline-logging-and-run-interpretation.md exists
[x] README.md references new Section 13 documents
[x] project-technical-guide.md references new Section 13 documents
[x] production-orchestration-plan.md reflects Purchases pipeline status
[x] purchases-runbook.md includes orchestration instructions
[x] purchases-canonical-layer.md includes rollout validation
[x] purchases-company-migration-policy.md includes rollout policy
[x] project-status-and-todo.md marks Inventory pipeline as pending
[ ] README_CONFIG.md reviewed and updated if still relevant
[ ] Section 13 changes committed
```

---

# Related Documentation

```text
README.md
README_CONFIG.md
docs/project-technical-guide.md
docs/production-orchestration-plan.md
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

When Section 13 is fully closed:

```bash
git status

git add README.md README_CONFIG.md docs/ scripts/ sql/ core/

git status

git commit -m "docs(project): finalize section 13 purchases orchestration and rollout documentation"

git push
```

If `README_CONFIG.md` is not updated in this section, use:

```bash
git status

git add README.md docs/ scripts/ sql/ core/

git status

git commit -m "docs(project): finalize section 13 purchases orchestration and rollout documentation"

git push
```