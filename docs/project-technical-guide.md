# Project Technical Guide

## Purpose

This document is the main technical guide for the Wansoft + Odoo Data Warehouse and ETL Pipeline project.

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
documentation structure
future work
```

This guide should be used when returning to the project after time away, onboarding another developer, reviewing the architecture, or preparing production orchestration.

---

## Project Overview

This project integrates operational data from:

```text
Odoo
Wansoft
MySQL
future external operational sources
```

The goal is to create a reliable analytical environment where business data can be extracted, governed, mapped, validated, orchestrated, logged, and consumed without modifying Odoo directly.

The project follows these principles:

```text
Odoo is read-only.
Wansoft remains the source of truth for sales.
MySQL is the governance and analytical layer.
Catalog governance is handled outside Odoo.
Source-system transitions are controlled by company-level rules.
Canonical tables preserve source traceability.
Pipeline execution must be auditable.
Rollout behaviour must be validated before production use.
```

---

## High-Level Architecture

```text
Odoo read-only extraction
        ↓
Wansoft operational data / SOAP sources
        ↓
MySQL staging and governance tables
        ↓
Scope classification
        ↓
Dictionary lookup
        ↓
Backlogs and bridge reports
        ↓
Company source governance
        ↓
Canonical BI-ready tables
        ↓
Pipeline validation
        ↓
JSON run logs
        ↓
Power BI / analysis / reporting
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
Inventory domain is technically stable and functionally advanced.
Purchases domain has a validated canonical layer with Odoo and Wansoft.
Purchases orchestration pipeline is implemented.
Purchases JSON logging is implemented.
Purchases rollout validation is implemented.
Documentation package is being updated for Section 13.
Inventory orchestration remains pending.
Power BI semantic modelling remains pending.
```

The next major phase is:

```text
controlled orchestration and consumption
```

This means:

```text
turn validated scripts into repeatable execution flows
define validation gates
add run logging
prepare Power BI consumption
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
inventory pipeline pending work
```

Current orchestration status:

```text
Purchases pipeline: implemented
Purchases validation: implemented
Purchases JSON logging: implemented
Purchases rollout validation: implemented
Inventory pipeline: pending
Inventory validation: pending
Production scheduling: pending
```

Recommended priority:

```text
production orchestration first
Power BI modelling second
```

Reason:

```text
Power BI should consume stable, repeatable, validated outputs.
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
12. docs/wansoft-local-wsdl.md
```

Document roles:

```text
docs/project-technical-guide.md
    Umbrella technical guide for the full project.

docs/project-status-and-todo.md
    Current project checkpoint, completed work, pending work, and TODO list.

docs/production-orchestration-plan.md
    Production-style orchestration plan, validation gates, logging needs, automation boundaries, and pending inventory orchestration.

docs/pipeline-logging-and-run-interpretation.md
    Explains how to read JSON pipeline logs, run_id, status, duration, step results, and failure signals.

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
    Operational runbook for running and validating the Inventory domain.

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
validation results
```

Odoo is not modified by the ETL. Any correction or mapping decision is stored in MySQL.

---

## Core Governance Rule

The key source governance file is:

```text
core/config/companies.py
```

The key configuration is:

```python
COMPANY_SOURCE = {
    "Antenas": "odoo",
    "La Esquina Coyoacán": "odoo",
    "CentroMyJ": "odoo",
    "Acoxpa": "wansoft",
    "Oceanía": "wansoft",
}
```

The domain source rules are:

```text
Sales      -> always Wansoft
Purchases  -> COMPANY_SOURCE
Inventory  -> COMPANY_SOURCE
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

Current inventory baseline:

```text
snapshot rows: 1660
residual functional not_found: 98 unique products
residual functional pending_review: 5 unique products
```

The Inventory domain is technically stable and functionally advanced.

Detailed documentation:

```text
docs/inventory-domain-closeout.md
docs/inventory-runbook.md
```

---

## Inventory Orchestration Status

Inventory does not yet have a full pipeline equivalent to Purchases.

Pending future files:

```text
scripts/run_inventory_pipeline.py
scripts/test_run_inventory_pipeline.py
scripts/validate_inventory_outputs.py
logs/inventory_pipeline_runs/
```

Future Inventory pipeline should follow the same principles as Purchases:

```text
dry-run support
required and optional steps
JSON logging
validation as final required step
safe automation only
manual approval for dictionary promotions
```

Important rule:

```text
Inventory dictionary promotions must not run automatically unless explicitly approved.
```

---

## Purchases Domain

The Purchases domain now supports both Odoo and Wansoft in a canonical layer.

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

Current status:

```text
dry-run validated
real execution validated
JSON logging validated
canonical validation integrated as required step
rollout company pattern validation integrated
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

Expected real-run summary:

```text
total_steps: 10
success: 10
dry_run: 0
failed_or_error: 0
required_failed_or_error: 0
PIPELINE RESULT: COMPLETED
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

Recommended `.gitignore` entry:

```gitignore
# Pipeline run logs
logs/
```

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

The validator is now integrated as the final required step of:

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

---

## migrated_from_wansoft

Expected pattern:

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

Current active migrated branches:

```text
Antenas
La Esquina Coyoacán
```

---

## new_odoo_branch

Expected pattern:

```text
Odoo:
    final_odoo_enabled
```

Not allowed after activation:

```text
wansoft / final_wansoft_enabled
```

Current active new branch:

```text
CentroMyJ
```

Current inactive future branch:

```text
Puebla
```

---

## Active and Inactive Rollout Expectations

Rollout expectations can be configured as:

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

Canonical tables are refreshed by:

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

## Purchases pipeline dry run

```bash
python -m scripts.run_purchases_pipeline --dry-run
```

## Purchases canonical validation

```bash
python -m scripts.validate_purchases_canonical_layer
```

## Inventory

```bash
python -m scripts.test_odoo_inventory_etl
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
snapshot preparation
scope merge
dictionary lookup
ETL execution
backlog generation
diagnostics export
Wansoft SOAP client initialization through local WSDL
canonical layer refresh by source_system
JSON run logging
canonical validation
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
```

---

# Production Rollout Notes

Before production automation, complete:

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
```

---

# Current Next Step

The Section 13 documentation package is being updated.

Recommended immediate action:

```text
Finish Section 13 documentation consistency.
Commit the Purchases pipeline, logging and rollout validation changes.
```

After Section 13 is committed, the next technical options are:

```text
1. Inventory pipeline orchestration
2. Inventory output validation
3. Inventory JSON logging
4. Wansoft canonical performance optimisation
5. Puebla rollout activation when operationally ready
6. Power BI integration layer
```

Recommended technical priority:

```text
Inventory pipeline orchestration first
Power BI modelling second
```

Reason:

```text
Power BI should consume stable, repeatable, validated outputs from all required domains.
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
docs/wansoft-local-wsdl.md
```

---

# Recommended Commit

This document should be committed as part of the Section 13 documentation update.

Recommended commit when Section 13 is closed:

```bash
git add README.md docs/ scripts/ sql/ core/

git commit -m "docs(project): update technical guide for purchases orchestration and rollout validation"

git push
```