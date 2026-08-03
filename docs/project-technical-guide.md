# Project Technical Guide

## Purpose

This document is the main technical guide for the Wansoft + Odoo + Zenput Data Warehouse and ETL Pipeline project.

Its purpose is to explain the project end-to-end:

```text
source systems
business rules
source governance
domain architecture
ETL layers
canonical tables
pipeline orchestration
JSON run logging
rollout validation
inventory output validation
Zenput location mapping
Zenput safe wrapper
documentation structure
future work
```

This guide should be used when returning to the project after time away, onboarding another developer, reviewing the architecture, or preparing production-style orchestration.

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
which branch is currently Zenput-only
which data is historical
which data is current
which source system produced each record
```

This is not primarily a Power BI project.

BI and reporting tools, including Power BI, Excel, dashboards, SQL notebooks, APIs or other reporting layers, are downstream consumers of the MySQL analytical layer.

The core project objective is:

```text
build reliable, governed, validated and auditable MySQL analytical outputs
```

---

## Project Overview

This project integrates operational data from:

```text
Odoo
Wansoft
Zenput
MySQL
future external operational sources
```

The goal is to create a reliable analytical environment where business data can be extracted, governed, mapped, validated, orchestrated, logged, and consumed without modifying Odoo directly and without exposing source-system migration complexity to users.

The project follows these principles:

```text
Odoo is read-only.
Wansoft remains the source of truth for Sales.
MySQL is the governance and analytical layer.
Zenput is a separate operational source.
Catalog governance is handled outside Odoo.
Source-system transitions are controlled by company-level rules.
Canonical tables preserve source traceability.
Pipeline execution must be auditable.
Rollout behaviour must be validated before production use.
Inventory dictionary promotions must remain controlled.
Zenput legacy real execution must remain protected until explicitly approved.
```

---

## High-Level Architecture

```text
Odoo read-only extraction
        ↓
Wansoft operational data / SOAP sources
        ↓
Zenput REST API / legacy outputs
        ↓
MySQL staging, output and governance tables
        ↓
Scope classification
        ↓
Dictionary lookup
        ↓
Backlogs and bridge reports
        ↓
Company source governance
        ↓
Zenput location mapping
        ↓
Canonical / analytical MySQL tables
        ↓
Pipeline validation
        ↓
JSON run logs
        ↓
Unified analytical consumption layer
```

---

## Current Project Checkpoint

The current project checkpoint is documented in:

```text
docs/project-status-and-todo.md
```

At this stage, the project has moved beyond early discovery.

Current state:

```text
Sales domain is functionally established.
Inventory domain is technically stable, functionally advanced, orchestrated and validated.
Purchases domain has a validated canonical layer with Odoo and Wansoft.
Zenput domain has a legacy assessment, central location mapping, validators and safe wrapper.
Purchases orchestration pipeline is implemented.
Purchases JSON logging is implemented.
Purchases rollout validation is implemented.
Inventory orchestration pipeline is implemented.
Inventory JSON logging is implemented.
Inventory output validation is implemented.
Inventory optional bridge reports are validated.
Zenput safe wrapper is implemented.
Zenput validation-only execution is implemented.
Zenput JSON logging is implemented.
Zenput legacy real execution remains protected.
Documentation package is being updated for Section 15.
Unified analytical consumption layer remains pending.
Production scheduling remains pending.
```

The project now has controlled orchestration or safe wrapper capability for:

```text
Purchases
Inventory
Zenput
```

Current domain execution status:

```text
Purchases:
    real pipeline execution is validated

Inventory:
    real pipeline execution is validated

Zenput:
    dry-run wrapper is validated
    validation-only execution is validated
    safety gate is validated
    legacy real execution remains protected
```

The next major phase is:

```text
validated consumption and production readiness
```

This means:

```text
keep Purchases pipeline stable
keep Inventory pipeline stable
keep Zenput legacy execution protected
prepare unified analytical consumption
decide whether database run-log tables are needed
decide whether validation results should be persisted
keep governance decisions controlled
```

---

## Production Orchestration Plan

The production orchestration strategy is documented in:

```text
docs/production-orchestration-plan.md
```

The orchestration plan separates:

```text
safe automation
controlled governance steps
validation gates
failure handling
logging requirements
future orchestration scripts
rollout validation
inventory pipeline execution
purchases pipeline execution
Zenput safe wrapper execution
```

Current orchestration status:

```text
Purchases pipeline: implemented
Purchases validation: implemented
Purchases JSON logging: implemented
Purchases rollout validation: implemented

Inventory pipeline: implemented
Inventory validation: implemented
Inventory JSON logging: implemented
Inventory bridge reports: implemented as optional diagnostics
Inventory dictionary promotions: intentionally excluded from default automation

Zenput safe wrapper: implemented
Zenput validation-only execution: implemented
Zenput output validation: implemented
Zenput JSON logging: implemented
Zenput safety gate: implemented
Zenput legacy real execution: protected by explicit --allow-legacy-writes gate

Production scheduling: pending
Unified analytical consumption layer: pending
Database run-log persistence: pending
Validation result persistence: pending
```

Recommended priority after Section 15:

```text
finish Section 15 documentation consistency
commit Zenput assessment, configuration, validation and safe wrapper package
review whether to approve first controlled Zenput legacy real execution
continue unified analytical consumption layer design
review database run-log persistence
```

Reason:

```text
Purchases and Inventory now produce repeatable, validated outputs.
Zenput now has central mapping, read-only validators, safe wrapper and safety gate.
Full Zenput legacy execution still requires explicit operational approval because it writes to MySQL and may update local timestamp state.
```

---

## Repository Documentation Structure

The project uses a structured documentation layer under:

```text
docs/
```

Current documentation files:

```text
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

Recommended reading order:

```text
1. docs/project-technical-guide.md
2. docs/project-status-and-todo.md
3. docs/production-orchestration-plan.md
4. docs/pipeline-logging-and-run-interpretation.md
5. docs/branch-rollout-playbook.md
6. docs/purchases-company-migration-policy.md
7. docs/purchases-product-mapping-policy.md
8. docs/purchases-canonical-layer.md
9. docs/purchases-runbook.md
10. docs/inventory-domain-closeout.md
11. docs/inventory-runbook.md
12. docs/zenput-legacy-assessment.md
13. docs/zenput-runbook.md
14. docs/wansoft-local-wsdl.md
```

Document roles:

```text
docs/project-technical-guide.md
    Umbrella technical guide for the full project.

docs/project-status-and-todo.md
    Current project checkpoint, completed work, pending work, and TODO list.

docs/production-orchestration-plan.md
    Production-style orchestration plan, validation gates, logging needs, automation boundaries, Inventory pipeline, Purchases pipeline and Zenput wrapper status.

docs/pipeline-logging-and-run-interpretation.md
    Explains how to read JSON pipeline logs, run_id, status, duration, step results, dry-run, safety gates and failure signals.

docs/branch-rollout-playbook.md
    Defines the controlled rollout process for branches moving from Wansoft to Odoo.

docs/purchases-company-migration-policy.md
    Company source governance, migration policy, rollout patterns, and source rules for Purchases.

docs/purchases-product-mapping-policy.md
    Product mapping policy for Purchases. Defines why explicit reference beats name similarity.

docs/purchases-canonical-layer.md
    Technical design and validation of the canonical Purchases layer, including rollout_company_patterns.

docs/purchases-runbook.md
    Operational runbook for running and validating the Purchases domain.

docs/inventory-domain-closeout.md
    Technical closeout of the Inventory domain baseline.

docs/inventory-runbook.md
    Operational runbook for running and validating the Inventory domain, including pipeline, logging, validator and bridge reports.

docs/zenput-legacy-assessment.md
    Assessment of the existing Zenput legacy integration, including scripts, write operations, credentials, mapping, risks and modernization criteria.

docs/zenput-runbook.md
    Operational runbook for Zenput safe execution, validation-only mode, safety gate and future controlled legacy execution.

docs/wansoft-local-wsdl.md
    Technical documentation for the local Wansoft SOAP/WSDL setup.
```

---

## Source Systems

## Odoo

Odoo is treated as a read-only operational source.

The ETL does not update Odoo records.

Odoo currently contributes to:

```text
Inventory snapshots
Product metadata
Purchase orders
Purchase order lines
Purchase receipts
Purchase receipt moves
```

Odoo technical snapshots are stored in MySQL before being promoted to canonical tables.

Examples:

```text
odoo_purchase_order_snapshot
odoo_purchase_order_line_snapshot
odoo_purchase_receipt_snapshot
odoo_purchase_receipt_move_snapshot
odoo_inventory_snapshot
odoo_inventory_backlog
```

---

## Wansoft

Wansoft remains critical for:

```text
Sales
Historical purchases
Inventory references
Product codes
Operational purchase-like entries
SOAP/API source data
```

Sales always remain Wansoft.

For Purchases and Inventory, Wansoft or Odoo is selected through company-level source governance.

Wansoft purchases are currently loaded from:

```text
getinputinventory_entrada
```

using:

```sql
WHERE TipoEntrada = 'Factura'
```

---

## Zenput

Zenput is a separate operational source.

Zenput currently contributes to:

```text
field operations
task completions
custom form submissions
form templates
submission answers
operational location data
```

Current Zenput legacy output tables:

```text
form_templates
submissions
submission_answers
zenput_tasks
```

Current Zenput legacy scripts:

```text
legacy/zenput/zenput_mysql_forms.py
legacy/zenput/zenput_mysql_tasks.py
```

Current Zenput state file:

```text
legacy/zenput/last_run_timestamp.txt
```

Current Zenput central configuration:

```text
core/config/zenput.py
```

Current Zenput safe wrapper:

```text
scripts/run_zenput_pipeline.py
```

Zenput should not use `COMPANY_SOURCE` as its inclusion filter.

Zenput maps:

```text
submissions.location_name -> company_source_key
```

using:

```text
core/config/zenput.py
```

---

## MySQL

MySQL is the governance and analytical layer.

MySQL stores:

```text
technical snapshots
canonical tables
mapping dictionaries
scope classifications
backlogs
bridge reports
company migration policies
source governance outputs
pipeline outputs
Zenput output tables
validation results
future analytical consumption tables
```

Odoo is not modified by the ETL.

Any correction, mapping decision or governance decision is stored in MySQL or project configuration.

---

## Core Governance Rule

The key source governance file is:

```text
core/config/companies.py
```

The key configuration is:

```python
COMPANY_SOURCE
```

The domain source rules are:

```text
Sales      -> always Wansoft
Purchases  -> COMPANY_SOURCE
Inventory  -> COMPANY_SOURCE
Zenput     -> core/config/zenput.py location mapping
```

---

## Operational Start Date Rule

The `operational_start_date` from `odoo_company_migration_policy` is not the primary source selector.

The correct hierarchy is:

```text
1. COMPANY_SOURCE decides whether the company uses Odoo or Wansoft.
2. operational_start_date applies only when COMPANY_SOURCE = 'odoo'.
3. .env dates are fallback values.
```

Example:

```text
Antenas:
    COMPANY_SOURCE = odoo
    Wansoft is preserved before operational_start_date
    Odoo is final from operational_start_date onward

La Esquina Coyoacán:
    COMPANY_SOURCE = odoo
    Wansoft is preserved before operational_start_date
    Odoo is final from operational_start_date onward

CentroMyJ:
    COMPANY_SOURCE = odoo
    New Odoo branch pattern

Oceanía:
    COMPANY_SOURCE = wansoft
    Wansoft remains final
    Odoo activity remains technical snapshot only
```

Zenput is separate from this rule.

Zenput may include locations regardless of whether a branch is currently Wansoft or Odoo for Purchases and Inventory.

---

## Company Mapping

### Odoo company names

Odoo company names are mapped to operational company keys.

Examples:

```text
FONDA ARGENTINA LAS ANTENAS -> Antenas
FONDA ARGENTINA ENCUENTRO OCEANIA -> Oceanía
FONDA ARGENTINA SAN JERONIMO -> San Jeronimo
FONDA ARGENTINA PUEBLA -> Puebla
FONDA ARGENTINA COYOACAN -> La Esquina Coyoacán
FONDA ARGENTINA MAQ -> Tepeyac
FONDA COSTA NERA -> Acoxpa
FONDA ARGENTINA -> Isabel La Católica
MARIO Y JULY -> CentroMyJ
```

### Wansoft subsidiary IDs

Wansoft subsidiary IDs are mapped from:

```python
CUENTAS_SUCURSALES
```

The derived mapping is:

```python
WANSOFT_SUBSIDIARY_SOURCE_KEY = {
    str(subsidiary_id): company_name
    for subsidiary_id, company_name, _password in CUENTAS_SUCURSALES
}
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

This avoids maintaining duplicate manual mapping dictionaries.

---

## Zenput Location Mapping

Zenput location names do not always match Odoo or Wansoft names.

The source field currently used for Zenput mapping is:

```text
submissions.location_name
```

Central mapping file:

```text
core/config/zenput.py
```

Primary mapping object:

```text
ZENPUT_LOCATION_SOURCE_KEY
```

Mapping rule:

```text
Zenput location_name -> company_source_key
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

These locations:

```text
exist in Zenput
are valid for Zenput operational reporting
do not currently have Wansoft as operational source
are not expected to participate in Purchases or Inventory Wansoft/Odoo pipelines
should be modeled so they can be incorporated into Wansoft or Odoo in the future
```

Important:

```text
Zenput should not use is_wansoft_company as its inclusion filter.
Zenput should not depend on COMPANY_SOURCE to decide whether a location is valid.
```

---

## Internal Provider Companies

Some Odoo companies exist for intercompany or provider workflows but should not be treated as final operating branches.

Current internal provider companies:

```text
EL BODEGON DE FITO
LAS EMPANADAS DE MARIA EVA
```

Rules:

```text
If company_name is an internal provider:
    exclude from final canonical branch-level facts

If vendor_name is an internal provider:
    keep the row if the buying company is final-eligible
```

---

# Domain Architecture

## Sales Domain

Sales remain Wansoft.

Current role:

```text
public-sale product homologation
sales product dictionary
catalog issue detection
commercial product consistency
```

Important rule:

```text
Sales always use Wansoft.
```

Sales does not follow `COMPANY_SOURCE`.

---

## Inventory Domain

The Inventory domain is scope-aware and dictionary-governed.

Main goals:

```text
extract Odoo inventory
classify inventory scope
separate business universes
apply dictionary only where appropriate
send unresolved products to backlog
support controlled promotions
validate outputs
orchestrate execution
log pipeline runs
```

Main inventory tables:

```text
inventory_mapping_dictionary
inventory_product_lifecycle
odoo_inventory_scope_classification
odoo_inventory_snapshot
odoo_inventory_backlog
```

Final refined inventory scopes:

```text
restaurantes
bodegon
empanadas
shared_cross_company
review_scope
operational_non_inventory
```

Previously validated baseline:

```text
snapshot rows: 1660
residual functional not_found: 98 unique products
residual functional pending_review: 5 unique products
```

Current state:

```text
Inventory is technically stable.
Inventory is functionally advanced.
Inventory pipeline is implemented.
Inventory output validation is implemented.
Inventory JSON logging is implemented.
Inventory bridge reports are available as optional diagnostics.
Inventory dictionary promotions remain manual and explicitly approved.
```

Detailed documentation:

```text
docs/inventory-domain-closeout.md
docs/inventory-runbook.md
```

---

## Inventory Orchestration Status

Inventory has a full orchestration pipeline equivalent in structure to Purchases.

Implemented files:

```text
scripts/run_inventory_pipeline.py
scripts/test_run_inventory_pipeline.py
scripts/validate_inventory_outputs.py
```

Inventory run logs:

```text
logs/inventory_pipeline_runs/
```

The logs are local execution artefacts and should not be committed.

Required `.gitignore` rule:

```gitignore
# Pipeline run logs
logs/
```

Current Inventory pipeline base execution order:

```text
01. Odoo inventory scope classification
02. Odoo inventory ETL
03. Inventory dictionary lookup validation
04. Inventory dictionary application validation
05. Inventory not_found analyzer
06. Inventory not_found priority backlog
07. Inventory output validation
```

Current optional extended execution with bridge reports:

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

Current validated status:

```text
Inventory pipeline dry-run: passing
Inventory smoke test: passing
Inventory real base execution: passing
Inventory extended bridge execution: passing
Inventory output validation: passing
Inventory JSON logging: implemented
Inventory promotions: excluded from default automation
```

---

## Inventory Output Validation

Inventory output validation is implemented in:

```text
scripts/validate_inventory_outputs.py
```

Run manually:

```bash
python -m scripts.validate_inventory_outputs
```

This validator is integrated as the final required step of:

```text
scripts/run_inventory_pipeline.py
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

Expected result:

```text
total_validations: 8
passed: 8
failed: 0

VALIDATION RESULT: PASSED
```

---

## Purchases Domain

The Purchases domain supports both Odoo and Wansoft in a canonical layer.

Implemented:

```text
Odoo purchase order extraction
Odoo purchase order line extraction
Odoo receipt extraction
Odoo receipt move extraction
purchase line classification
product mapping against inventory_mapping_dictionary
purchase inventory mapping backlog
company source governance
Odoo canonical load
Wansoft canonical load
canonical purchase tables with source_system
controlled pipeline orchestration
JSON run logging
canonical validation
rollout company pattern validation
```

---

# Purchases Pipeline Orchestration

## Implemented Scripts

Purchases orchestration is implemented in:

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

---

## Purchases Pipeline Execution Order

Current pipeline order:

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

Current status:

```text
dry-run validated
real execution validated
JSON logging validated
canonical validation integrated as required step
rollout company pattern validation integrated
```

---

# Purchases JSON Logging

The Purchases pipeline writes local JSON logs to:

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

Logs are local execution artefacts and should not be committed.

Detailed documentation:

```text
docs/pipeline-logging-and-run-interpretation.md
```

---

# Purchases Product Mapping Policy

Purchase lines are enriched using:

```text
purchase.order.line.product_id
→ inventory_mapping_dictionary.odoo_product_id
→ wansoft_code
→ wansoft_product_name
→ wansoft_department
```

The project does not create automatic product aliases.

Key rule:

```text
Explicit reference beats name similarity.
```

If a product has no explicit approved reference:

```text
it remains a new product
it stays in backlog
it is not mapped by similar name
```

Detailed documentation:

```text
docs/purchases-product-mapping-policy.md
```

---

# Purchases Canonical Layer

The Purchases canonical layer contains final BI-ready tables.

Canonical tables:

```text
canonical_purchase_order_snapshot
canonical_purchase_order_line_snapshot
canonical_purchase_receipt_snapshot
canonical_purchase_receipt_move_snapshot
```

These tables include:

```text
source_system
source_domain
company_source_key
final_purchase_source_status
```

Supported values:

```text
source_system = odoo
source_system = wansoft
```

---

## Current Canonical Counts

Current validated canonical counts:

```text
canonical_purchase_order_snapshot:
    odoo:      882
    wansoft: 145015

canonical_purchase_order_line_snapshot:
    odoo:      4771
    wansoft: 745161

canonical_purchase_receipt_snapshot:
    odoo:      876
    wansoft: 145015

canonical_purchase_receipt_move_snapshot:
    odoo:      4763
    wansoft: 745161
```

These counts are validated by:

```bash
python -m scripts.validate_purchases_canonical_layer
```

---

# Purchases Canonical Validation

Canonical validation is implemented in:

```text
scripts/validate_purchases_canonical_layer.py
```

Current validation checks:

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

The validator is integrated as the final required step of:

```text
scripts/run_purchases_pipeline.py
```

If validation fails:

```text
The Purchases pipeline fails.
```

---

# Branch Rollout Validation

Branch rollout validation is implemented through:

```text
ROLLOUT_COMPANY_EXPECTATIONS
```

in:

```text
scripts/validate_purchases_canonical_layer.py
```

Supported rollout types:

```text
migrated_from_wansoft
new_odoo_branch
```

Current rollout state:

```text
Antenas:
    migrated_from_wansoft
    active = True
    validation = PASS

La Esquina Coyoacán:
    migrated_from_wansoft
    active = True
    validation = PASS

CentroMyJ:
    new_odoo_branch
    active = True
    validation = PASS

Puebla:
    new_odoo_branch
    active = False
    validation = skipped
```

Detailed rollout documentation:

```text
docs/branch-rollout-playbook.md
```

---

# Zenput Domain

Zenput is an operational source that contains field operations, task completions and custom form submission data.

Zenput is separate from the Wansoft/Odoo source governance used by Purchases and Inventory.

The current Zenput work does not replace the existing legacy scripts.

The current objective is:

```text
preserve working legacy behaviour
centralize configuration
validate outputs
protect write-enabled execution
add safe orchestration wrapper
document operational use
```

---

## Zenput Current Status

Current status:

```text
legacy scripts assessed
write operations documented
central location mapping implemented
location mapping validated
output validation implemented
safe pipeline wrapper implemented
JSON logging implemented
safety gate implemented
validation-only execution implemented
legacy real execution protected
```

Current legacy scripts:

```text
legacy/zenput/zenput_mysql_forms.py
legacy/zenput/zenput_mysql_tasks.py
```

Current legacy state file:

```text
legacy/zenput/last_run_timestamp.txt
```

Current modern configuration:

```text
core/config/zenput.py
```

Current modern scripts:

```text
scripts/validate_zenput_location_mapping.py
scripts/validate_zenput_outputs.py
scripts/run_zenput_pipeline.py
scripts/test_run_zenput_pipeline.py
```

Current documentation:

```text
docs/zenput-legacy-assessment.md
docs/zenput-runbook.md
```

---

## Zenput Legacy Scripts

## zenput_mysql_forms.py

Functional area:

```text
Zenput forms
form templates
submissions
submission answers
```

Detected write targets:

```text
form_templates
submissions
submission_answers
```

Detected operations:

```text
CREATE TABLE IF NOT EXISTS
INSERT ... ON DUPLICATE KEY UPDATE
DELETE FROM submission_answers WHERE submission_id IN (...)
INSERT INTO submission_answers
connection.commit()
```

Risk:

```text
This script writes to MySQL.
The submission_answers refresh strategy should remain controlled.
```

---

## zenput_mysql_tasks.py

Functional area:

```text
Zenput tasks
task metadata
task status
completion information
fulfillment details
```

Detected write target:

```text
zenput_tasks
```

Detected local state file:

```text
legacy/zenput/last_run_timestamp.txt
```

Detected operations:

```text
CREATE TABLE IF NOT EXISTS
INSERT ... ON DUPLICATE KEY UPDATE
connection.commit()
timestamp read/write
```

Risk:

```text
This script writes to MySQL.
This script may update last_run_timestamp.txt.
```

---

## Zenput Location Mapping

Zenput uses operational location names from:

```text
submissions.location_name
```

Central mapping:

```text
ZENPUT_LOCATION_SOURCE_KEY
```

in:

```text
core/config/zenput.py
```

Mapping rule:

```text
Zenput location_name -> company_source_key
```

Zenput should not use:

```text
is_wansoft_company
```

as an inclusion filter.

Reason:

```text
Zenput is independent from the Wansoft/Odoo source selection used by Purchases and Inventory.
```

Confirmed Zenput-only locations:

```text
León
Lindavista
Perisur
```

These locations are valid for Zenput operational analysis.

They do not currently have Wansoft as an operational source.

They should be modeled so they can be incorporated into Wansoft or Odoo in the future if operations change.

---

## Zenput Pipeline Status

Current Zenput pipeline wrapper:

```bash
python -m scripts.run_zenput_pipeline
```

Current default dry-run result:

```text
total_steps: 4
dry_run: 4
PIPELINE RESULT: COMPLETED
```

Current validation-only execution:

```bash
python -m scripts.run_zenput_pipeline --execute --validation-only
```

This executes only read-only validators.

Expected result:

```text
total_steps: 2
success: 2
PIPELINE RESULT: COMPLETED
```

Current safety gate:

```bash
python -m scripts.run_zenput_pipeline --execute
```

Expected result:

```text
PIPELINE RESULT: FAILED
```

This is intentional.

Reason:

```text
Write-enabled legacy scripts require explicit --allow-legacy-writes.
```

Full real legacy execution is protected:

```bash
python -m scripts.run_zenput_pipeline --execute --allow-legacy-writes
```

This command is not recommended for routine execution until explicitly approved.

---

## Zenput Validators

Location mapping validator:

```bash
python -m scripts.validate_zenput_location_mapping
```

Current checks:

```text
submissions_table_exists
zenput_location_mapping_available
zenput_only_locations_classified
zenput_governance_rule_documented
```

Expected result:

```text
total_validations: 4
passed: 4
VALIDATION RESULT: PASSED
```

Output validator:

```bash
python -m scripts.validate_zenput_outputs
```

Current checks:

```text
required_zenput_tables_exist
zenput_table_counts_available
zenput_submissions_location_mapping
zenput_only_locations_classified
zenput_timestamp_file_valid
zenput_legacy_pipeline_protection_documented
```

Expected result:

```text
total_validations: 6
passed: 6
VALIDATION RESULT: PASSED
```

Smoke test:

```bash
python -m scripts.test_run_zenput_pipeline
```

Expected result:

```text
default_dry_run: PASS
safety_gate: PASS
TEST RESULT: PASSED
```

---

# Odoo Purchases Canonical Load

Entrypoint:

```bash
python -m scripts.test_canonical_purchase_odoo_etl
```

Function:

```python
run_canonical_purchase_odoo_etl()
```

Current active Odoo final companies:

```text
Antenas
La Esquina Coyoacán
CentroMyJ
```

Current validated Odoo canonical counts:

```text
orders:        882
lines:         4771
receipts:      876
receipt_moves: 4763
```

---

# Wansoft Purchases Canonical Load

Entrypoint:

```bash
python -m scripts.test_canonical_purchase_wansoft_etl
```

Function:

```python
run_canonical_purchase_wansoft_etl()
```

Source table:

```text
getinputinventory_entrada
```

Filter:

```sql
WHERE TipoEntrada = 'Factura'
```

Current validated Wansoft canonical counts:

```text
orders:        145015
lines:         745161
receipts:      145015
receipt_moves: 745161
```

Wansoft status summary:

```text
final_wansoft_enabled        690000
wansoft_history_before_odoo   55161
```

---

# Wansoft Technical Key Strategy

Wansoft natural invoice keys are not used directly as unique database IDs because of:

```text
case-insensitive MySQL collation
trailing spaces
long natural keys
inconsistent invoice casing
duplicate invoice references
```

Instead, stable hashed technical keys are used.

Examples:

```text
source_order_id = wansoft_order:{company_key}:{fecha_key}:{hash}
source_receipt_id = wansoft_receipt:{company_key}:{fecha_key}:{hash}
source_order_line_id = wansoft_line:{id}
source_stock_move_id = wansoft_move:{id}
```

Natural values remain available in business columns such as:

```text
purchase_order_name
vendor_id
vendor_name
wansoft_code
wansoft_product_name
order_date
```

Detailed documentation:

```text
docs/purchases-canonical-layer.md
```

---

# Source-System Reload Strategy

Canonical purchase tables are refreshed by:

```text
source_system
```

Odoo refresh:

```text
Delete only source_system = 'odoo'
Reload eligible Odoo rows
Preserve source_system = 'wansoft'
```

Wansoft refresh:

```text
Delete only source_system = 'wansoft'
Reload eligible Wansoft rows
Preserve source_system = 'odoo'
```

For normal rollout testing, avoid:

```sql
DROP TABLE
```

Use source-specific cleanup:

```sql
DELETE FROM canonical_purchase_order_snapshot
WHERE source_system = 'wansoft';

DELETE FROM canonical_purchase_order_line_snapshot
WHERE source_system = 'wansoft';

DELETE FROM canonical_purchase_receipt_snapshot
WHERE source_system = 'wansoft';

DELETE FROM canonical_purchase_receipt_move_snapshot
WHERE source_system = 'wansoft';
```

Then reload:

```bash
python -m scripts.test_canonical_purchase_wansoft_etl
```

and validate:

```bash
python -m scripts.validate_purchases_canonical_layer
```

---

# Wansoft SOAP / Local WSDL

The Wansoft SOAP client uses a local WSDL file.

WSDL path:

```text
resources/wsdl/wansoft.wsdl
```

Environment variables:

```env
WANSOFT_USE_LOCAL_WSDL=true
WANSOFT_WSDL_PATH=resources/wsdl/wansoft.wsdl
WANSOFT_SERVICE_URL=https://www.wansoft.net/wansoft.web/API/IntegrationService.asmx
```

Centralized client:

```python
from core.clients.wansoft_client import get_wansoft_client

client = get_wansoft_client()
```

Do not instantiate Zeep clients directly inside ETL scripts.

Validation:

```bash
python -m scripts.test_wansoft_wsdl_client
```

Detailed documentation:

```text
docs/wansoft-local-wsdl.md
```

---

# Key ETL Entrypoints

## Purchases pipeline

```bash
python -m scripts.run_purchases_pipeline
```

## Purchases pipeline dry-run

```bash
python -m scripts.run_purchases_pipeline --dry-run
```

## Purchases canonical validation

```bash
python -m scripts.validate_purchases_canonical_layer
```

## Inventory pipeline

```bash
python -m scripts.run_inventory_pipeline
```

## Inventory pipeline dry-run

```bash
python -m scripts.run_inventory_pipeline --dry-run
```

## Inventory pipeline with optional bridge reports

```bash
python -m scripts.run_inventory_pipeline --include-bridge-reports
```

## Inventory pipeline smoke test

```bash
python -m scripts.test_run_inventory_pipeline
```

## Inventory output validation

```bash
python -m scripts.validate_inventory_outputs
```

## Zenput pipeline dry-run

```bash
python -m scripts.run_zenput_pipeline
```

## Zenput validation-only execution

```bash
python -m scripts.run_zenput_pipeline --execute --validation-only
```

## Zenput safety gate test

```bash
python -m scripts.run_zenput_pipeline --execute
```

Expected result:

```text
PIPELINE RESULT: FAILED
```

This is correct because write-enabled legacy steps require explicit `--allow-legacy-writes`.

## Zenput full legacy execution

```bash
python -m scripts.run_zenput_pipeline --execute --allow-legacy-writes
```

Current recommendation:

```text
Do not run casually.
Requires explicit operational approval.
```

## Zenput pipeline smoke test

```bash
python -m scripts.test_run_zenput_pipeline
```

## Zenput location mapping validation

```bash
python -m scripts.validate_zenput_location_mapping
```

## Zenput output validation

```bash
python -m scripts.validate_zenput_outputs
```

## Odoo purchases snapshot load

```bash
python -m scripts.test_odoo_purchase_etl
```

## Odoo purchase receipts load

```bash
python -m scripts.test_odoo_purchase_receipt_etl
```

## Odoo canonical purchase load

```bash
python -m scripts.test_canonical_purchase_odoo_etl
```

## Wansoft canonical purchase load

```bash
python -m scripts.test_canonical_purchase_wansoft_etl
```

## Wansoft purchase subsidiary mapping report

```bash
python -m scripts.test_wansoft_purchase_subsidiary_mapping_report
```

## Company source governance test

```bash
python -m scripts.test_company_source_governance
```

## Wansoft local WSDL validation

```bash
python -m scripts.test_wansoft_wsdl_client
```

---

# Environment Configuration

Configuration is driven through `.env`.

## Inventory ETL example

```env
INVENTORY_ETL_SALES_REFERENCE_SCOPE=restaurantes
INVENTORY_ETL_SALES_REFERENCE_SOURCE=sales_reference
INVENTORY_ETL_SCOPE_INCLUDE=shared_cross_company
INVENTORY_ETL_SCOPE_BACKLOG=bodegon,empanadas,bodegon_candidate,empanadas_candidate,review_scope,operational_non_inventory
```

## Purchases ETL example

```env
PURCHASE_ETL_MIN_ORDER_DATE=2026-06-01
PURCHASE_ETL_MIN_RECEIPT_DATE=2026-06-01
PURCHASE_ETL_APPLY_PRODUCT_MAPPING=true
PURCHASE_ETL_ALLOWED_MAPPING_STATUS=approved
```

## Wansoft SOAP example

```env
WANSOFT_USE_LOCAL_WSDL=true
WANSOFT_WSDL_PATH=resources/wsdl/wansoft.wsdl
WANSOFT_SERVICE_URL=https://www.wansoft.net/wansoft.web/API/IntegrationService.asmx
```

## Zenput example

```env
ZENPUT_API_TOKEN=

ZENPUT_DB_HOST=
ZENPUT_DB_USER=
ZENPUT_DB_PASSWORD=
ZENPUT_DB_NAME=

ZENPUT_DB_HOST_DEV=
ZENPUT_DB_USER_DEV=
ZENPUT_DB_PASSWORD_DEV=
ZENPUT_DB_NAME_DEV=
```

Important:

```text
ZENPUT_API_TOKEN should be documented as a placeholder in core/config/.env.example if missing.
No real secret values should be committed.
```

---

# SQL Folder

The `sql/` folder contains seed and maintenance scripts.

```text
sql/
├── maintenance/
│   └── update_odoo_company_migration_policy.sql
└── seeds/
    └── seed_odoo_company_migration_policy.sql
```

Use cases:

```text
initial controlled seed data
company migration policy updates
operational governance examples
rollout reproducibility
```

---

# What Is Safe to Automate

## Safe to automate

```text
Odoo read-only extraction
Wansoft read-only source extraction
snapshot preparation
scope merge
dictionary lookup
ETL execution
backlog generation
diagnostics export
bridge report generation
Wansoft SOAP client initialization through local WSDL
canonical layer refresh by source_system
JSON run logging
canonical validation
inventory output validation
Zenput location mapping validation
Zenput output validation
Zenput validation-only execution
rollout pattern validation
```

## Keep controlled at first

```text
dictionary promotions
historical-only decisions
scope rule changes
heuristic changes
catalog-governance decisions
company migration policy changes
COMPANY_SOURCE changes
rollout activation
Zenput legacy real execution
Zenput last_run_timestamp.txt updates
Zenput submission_answers delete/reinsert behaviour
```

---

# Production Rollout Notes

Before production scheduling, review:

```text
runbook for automatic vs controlled jobs
dictionary governance process
ETL telemetry cleanup
company migration policy review
final residual backlog handling policy
Wansoft local WSDL validation
canonical purchases refresh orchestration
inventory pipeline orchestration
inventory validation script
Zenput safe wrapper
Zenput validation-only execution
Zenput legacy real execution approval policy
JSON run logs
future database run-log persistence
future validation result persistence
```

---

# Current Next Step

The Section 15 documentation package is being updated.

Recommended immediate action:

```text
Finish Section 15 documentation consistency.
Commit the Zenput assessment, configuration, validation and safe wrapper package.
```

Section 15 completed or in progress:

```text
Zenput legacy assessment completed
Zenput write operations documented
Zenput credentials reviewed
Zenput central location mapping created
Zenput location mapping validated
Zenput output validator created
Zenput safe pipeline wrapper created
Zenput dry-run validated
Zenput safety gate validated
Zenput validation-only execution validated
Zenput runbook created
README updated
Project status and TODO updated
Project technical guide updated
```

Remaining Section 15 documentation tasks:

```text
Update docs/production-orchestration-plan.md with Zenput status.
Update docs/pipeline-logging-and-run-interpretation.md with Zenput status.
Add ZENPUT_API_TOKEN placeholder to core/config/.env.example if missing.
Review git status.
Commit Section 15 package.
```

After Section 15 is committed, the next technical options are:

```text
1. Controlled Zenput legacy real execution review
2. Transaction safety review for submission_answers delete/reinsert
3. Future handling of last_run_timestamp.txt
4. Future Zenput analytical/canonical table design
5. Database run-log persistence
6. Validation result persistence
7. Unified analytical consumption layer
```

Recommended technical priority:

```text
Close Section 15 documentation and commit first.
Then decide whether Zenput legacy real execution is ready for a controlled approved run.
```

Reason:

```text
Zenput now has a safe wrapper, central location mapping, read-only validators and JSON logging.
Legacy write execution is still protected and should not be run casually.
```

---

# Related Documentation

```text
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

This document should be committed as part of the Section 15 documentation update.

Recommended commit when Section 15 is ready to checkpoint:

```bash
git add README.md docs/ core/config/zenput.py scripts/validate_zenput_location_mapping.py scripts/validate_zenput_outputs.py scripts/run_zenput_pipeline.py scripts/test_run_zenput_pipeline.py

git commit -m "feat(zenput): add safe pipeline wrapper and validation"

git push
```