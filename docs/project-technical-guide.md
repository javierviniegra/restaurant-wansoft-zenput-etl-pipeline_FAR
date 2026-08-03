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
Zenput controlled legacy execution
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
which branch appears in Zenput before full Wansoft/Odoo incorporation
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
Zenput legacy real execution must remain explicitly controlled.
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
Zenput domain has a legacy assessment, central location mapping, validators, safe wrapper and one controlled real legacy execution against development/test database.
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
Zenput first controlled real execution has been completed against development/test database.
Zenput post-execution validators are passing.
Zenput production legacy execution remains protected.
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
    first controlled real legacy execution completed against development/test database
    post-execution validation is passing
    production legacy execution remains protected
```

The next major phase is:

```text
validated consumption and production readiness
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
keep governance decisions controlled
```

---

## Documentation Structure

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
    Assessment of the existing Zenput legacy integration, including scripts, write operations, credentials, mapping, risks, modernization criteria and first controlled real execution.

docs/zenput-runbook.md
    Operational runbook for Zenput safe execution, validation-only mode, safety gate, controlled legacy execution and future hardening.

docs/wansoft-local-wsdl.md
    Technical documentation for the local Wansoft SOAP/WSDL setup.
```

---

# Source Systems

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

Zenput has completed one controlled real legacy execution against a development/test database.

That execution updated Zenput output tables and revealed a new location:

```text
Fonda Argentina Puebla
```

The new location is now mapped as:

```text
Fonda Argentina Puebla -> Puebla
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

# Core Governance Rules

## Company Source Governance

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

Puebla:
    modeled as a future Odoo / operational branch
    appears in Zenput as Fonda Argentina Puebla
    mapped to Puebla in Zenput configuration
```

Zenput is separate from this operational start date rule.

Zenput may include locations regardless of whether a branch is currently Wansoft or Odoo for Purchases and Inventory.

---

# Company Mapping

## Odoo company names

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

## Wansoft subsidiary IDs

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
Fonda Argentina Puebla -> Puebla
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
Puebla should not be classified as Zenput-only.
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

Canonical purchase tables:

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

---

## Zenput Domain

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
test controlled legacy execution against development/test database
```

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
first controlled real legacy execution completed against development/test database
Puebla mapping added
post-execution validators passing
production legacy execution protected
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

# Orchestration and Validation

## Purchases Pipeline

Entrypoints:

```bash
python -m scripts.run_purchases_pipeline
python -m scripts.run_purchases_pipeline --dry-run
python -m scripts.validate_purchases_canonical_layer
```

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

## Inventory Pipeline

Entrypoints:

```bash
python -m scripts.run_inventory_pipeline
python -m scripts.run_inventory_pipeline --dry-run
python -m scripts.run_inventory_pipeline --include-bridge-reports
python -m scripts.validate_inventory_outputs
```

Current base pipeline order:

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

Current status:

```text
dry-run validated
smoke test validated
real base execution validated
extended bridge execution validated
output validation passing
JSON logging implemented
promotions excluded from default automation
```

---

## Zenput Pipeline

Entrypoints:

```bash
python -m scripts.run_zenput_pipeline
python -m scripts.run_zenput_pipeline --validation-only
python -m scripts.run_zenput_pipeline --execute --validation-only
python -m scripts.run_zenput_pipeline --execute
python -m scripts.run_zenput_pipeline --execute --allow-legacy-writes
python -m scripts.validate_zenput_location_mapping
python -m scripts.validate_zenput_outputs
python -m scripts.test_run_zenput_pipeline
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

Full real legacy execution:

```bash
python -m scripts.run_zenput_pipeline --execute --allow-legacy-writes
```

Current status:

```text
Tested once against development/test database.
Not recommended for routine production execution without approval.
```

---

## First Controlled Zenput Real Execution

Command executed:

```bash
python -m scripts.run_zenput_pipeline --execute --allow-legacy-writes
```

Execution target:

```text
development / test database
```

Initial result:

```text
01. Zenput location mapping validation -> SUCCESS
02. Zenput forms legacy ETL -> SUCCESS
03. Zenput tasks legacy ETL -> SUCCESS
04. Zenput output validation -> FAILED
```

Reason for failure:

```text
Fonda Argentina Puebla appeared as new unmapped location_name.
```

Correction:

```text
Fonda Argentina Puebla -> Puebla
```

After correction:

```text
location mapping validator: PASSED
output validator: PASSED
validation-only pipeline: COMPLETED
```

Pre-execution snapshot:

```text
form_templates:       19
submissions:          774
submission_answers:   61,357
zenput_tasks:         1,504
```

Post-execution snapshot:

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

---

## Zenput Current Technical Findings

### last_run_timestamp.txt did not change

Observed value after controlled execution:

```text
2025-10-23T18:37:33Z
```

Interpretation:

```text
Not currently blocking.
Requires future review.
```

Possible explanations:

```text
tasks script is running full sync
timestamp is not used by current full-sync path
timestamp update function is not called
timestamp file is legacy residue
```

Future action:

```text
review timestamp logic in zenput_mysql_tasks.py
decide whether last_run_timestamp.txt remains active or should be retired or moved
```

### Legacy error propagation should be reviewed

A previous failed attempt showed an environmental database error.

The wrapper relies on subprocess return codes.

Future action:

```text
ensure fatal legacy errors return non-zero exit code
```

### max_allowed_packet issue was environmental

A previous attempt failed due to:

```text
Got a packet bigger than 'max_allowed_packet' bytes
```

This was resolved in the local XAMPP / MariaDB development environment.

Future action:

```text
document recommended max_allowed_packet if issue recurs
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
ZENPUT_API_TOKEN should be documented as a placeholder in core/config/.env.example.
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

# Safe Automation and Controlled Actions

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

## Keep controlled

```text
dictionary promotions
historical-only decisions
scope rule changes
heuristic changes
catalog-governance decisions
company migration policy changes
COMPANY_SOURCE changes
rollout activation
Zenput production legacy real execution
Zenput last_run_timestamp.txt updates
Zenput submission_answers delete/reinsert behaviour
Zenput legacy error propagation changes
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
Zenput controlled legacy execution result
Zenput production legacy execution approval policy
JSON run logs
future database run-log persistence
future validation result persistence
```

---

# Current Next Step

The Section 16 documentation package is being updated.

Completed in Section 16:

```text
Pre-execution Zenput snapshot captured
Development/test execution target confirmed
First controlled real legacy execution performed
Legacy forms ETL executed
Legacy tasks ETL executed
Output validator caught new unmapped location
Fonda Argentina Puebla mapped to Puebla
Location mapping validator passed
Output validator passed
Validation-only pipeline passed
zenput-legacy-assessment updated
zenput-runbook updated
project-status-and-todo updated
project-technical-guide updated
```

Remaining optional Section 16 documentation tasks:

```text
Update docs/production-orchestration-plan.md with Section 16 controlled execution result.
Update docs/pipeline-logging-and-run-interpretation.md with Section 16 real validation failure example.
Review git status.
Commit Section 16 package.
```

After Section 16 is committed, the next technical options are:

```text
1. Zenput hardening
2. Timestamp behaviour review
3. Legacy error propagation review
4. Transaction safety review for submission_answers delete/reinsert
5. Future Zenput analytical/canonical table design
6. Database run-log persistence
7. Validation result persistence
8. Unified analytical consumption layer
```

Recommended technical priority:

```text
Close Section 16 documentation and commit first.
Then decide whether to continue Zenput hardening or move to unified analytical layer planning.
```

Reason:

```text
Zenput now has a safe wrapper, central location mapping, read-only validators, JSON logging and one controlled real execution result against development/test database.
Production legacy execution is still protected and should not be run casually.
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