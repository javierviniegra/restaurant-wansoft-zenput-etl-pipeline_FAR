# Wansoft + Odoo + Zenput Data Warehouse & ETL Pipeline

## Overview

This repository contains the Python ETL, source-governance, catalog-governance and orchestration layer used to integrate **Wansoft**, **Odoo**, **Zenput**, and other operational sources into a centralized **MySQL-based analytical environment**.

The core goal of the project is to create a unified analytical layer where users can consume consistent operational and business data without needing to know:

```text
which branch still uses Wansoft
which branch migrated from Wansoft to Odoo
which branch started directly in Odoo
which branch is currently Zenput-only
which records are historical
which source system produced each record
```

The project is designed around a few core principles:

```text
Odoo is treated as a read-only source.
Wansoft remains the source of truth for Sales.
Purchases and Inventory use company-level source governance.
Zenput is treated as a separate operational source.
MySQL stores mapping dictionaries, scope classification, lifecycle logic, snapshots, canonical layers, validations, run logs and backlogs.
Catalog governance is resolved outside Odoo.
Wansoft SOAP access is centralized through a local WSDL client.
Canonical tables preserve source traceability through source_system.
Pipeline execution must be auditable.
Branch rollout behaviour must be validated before production use.
Inventory dictionary promotions must remain manual and explicitly approved.
Zenput legacy real execution must remain protected until explicitly approved.
```

The goal is to enable operational, analytical and accounting-friendly data flows without modifying Odoo as part of the ETL process.

---

## Project Scope

The primary scope of this project is:

```text
Build a unified MySQL analytical layer that combines Wansoft, Odoo and Zenput data.
```

The analytical layer should hide source-system transitions from end users.

Users should be able to consume consistent business information without needing to understand whether the underlying data came from:

```text
Wansoft
Odoo
Zenput
a migrated branch
a new Odoo branch
a Zenput-only operational location
```

BI and reporting tools, including Power BI, Excel, dashboards, SQL queries or future APIs, are downstream consumers of this MySQL analytical layer.

They are not the core scope of the project.

---

## Current Project Status

### Implemented or advanced domains

```text
Sales
Inventory
Purchases
Zenput
```

### Current validated milestones

```text
Inventory domain baseline completed
Inventory dictionary governance established
Inventory lifecycle analysis implemented
Inventory backlog and bridge-review process established
Inventory pipeline orchestration implemented
Inventory pipeline dry-run validated
Inventory pipeline smoke test validated
Inventory pipeline real execution validated
Inventory optional bridge reports validated
Inventory output validation implemented
Inventory output validation integrated as required pipeline step
Inventory JSON run logging implemented
Inventory dictionary promotions excluded from default automation

Wansoft local WSDL client implemented
Purchases Odoo snapshots implemented
Purchases company migration policy implemented
Purchases product mapping policy implemented
Purchases receipts and receipt moves implemented
Purchases canonical layer implemented
Odoo and Wansoft coexist in canonical purchase tables
Purchases pipeline orchestration implemented
Purchases pipeline dry-run validated
Purchases pipeline real execution validated
Purchases canonical validation integrated as required pipeline step
Purchases JSON run logging implemented
Branch rollout validation implemented
Branch rollout playbook created
Pipeline log interpretation documentation created
Production orchestration planning documented

Zenput legacy integration assessment started
Zenput active legacy scripts identified
Zenput write operations documented
Zenput credentials and .env usage reviewed
Zenput central DB target confirmed
Zenput central location mapping implemented
Zenput location mapping validated against MySQL submissions.location_name
Zenput-only locations classified
Zenput safe pipeline wrapper implemented
Zenput dry-run validated
Zenput safety gate validated
Zenput validation-only execution validated
Zenput output validation implemented
Zenput JSON run logging implemented
Zenput legacy real execution protected by explicit approval gate
```

### Current project stage

```text
Validated domain ETLs
→ Controlled Purchases orchestration
→ Controlled Inventory orchestration
→ Controlled Zenput wrapper
→ Pipeline logging and validation
→ Source transition abstraction
→ Branch rollout control
→ Unified analytical consumption layer
→ Future production scheduling
```

The project is no longer in early discovery.

The current focus is to move from individually validated scripts to controlled, repeatable, auditable execution flows that can later support reporting, analysis and production scheduling.

---

## Current Orchestration Status

```text
Purchases pipeline: implemented
Purchases canonical validation: implemented
Purchases JSON logging: implemented
Purchases rollout validation: implemented

Inventory pipeline: implemented
Inventory output validation: implemented
Inventory JSON logging: implemented
Inventory optional bridge reports: implemented
Inventory dictionary promotions: excluded from default automation

Zenput pipeline wrapper: implemented
Zenput dry-run: implemented
Zenput safety gate: implemented
Zenput validation-only execution: implemented
Zenput output validation: implemented
Zenput JSON logging: implemented
Zenput legacy real execution: protected by explicit --allow-legacy-writes gate

Production scheduling: pending
Unified analytical consumption layer: purchase analytical layer implemented and validated; inventory and Zenput analytical additions pending
Database run-log persistence: pending
Validation result persistence: pending
```

---

## Technical Documentation

This project includes a structured documentation layer under the `docs/` directory.

The documentation is organized into:

```text
main technical guide
project planning documents
orchestration and logging documents
branch rollout documents
domain-specific documentation
operational runbooks
technical policy documents
legacy integration assessments
```

---

## Main Technical Guide

```text
docs/project-technical-guide.md
```

This is the umbrella technical guide for the full project.

It explains:

```text
overall architecture
source systems
domain strategy
ETL flow
source governance
canonical layers
pipeline orchestration
JSON run logging
rollout validation
inventory output validation
Zenput location mapping
Zenput safe wrapper
documentation structure
future work
```

Use this document when you need to understand the project end-to-end.

---

## Project Planning Documents

```text
docs/project-status-and-todo.md
docs/production-orchestration-plan.md
```

### `docs/project-status-and-todo.md`

Documents the current project checkpoint.

It explains:

```text
where the project currently stands
what has already been completed
what is still pending
what should not be automated yet
recommended next work sequence
Section 13 status
Section 14 status
Section 15 status
Inventory pipeline implemented status
Purchases pipeline implemented status
Zenput safe wrapper status
Puebla future rollout pending work
unified analytical consumption pending work
database logging pending work
```

### `docs/production-orchestration-plan.md`

Defines the production-style orchestration plan.

It explains:

```text
execution layers
safe automation candidates
controlled manual steps
validation gates
logging requirements
failure handling
future orchestration scripts
Purchases pipeline status
Inventory pipeline status
Zenput wrapper status
rollout validation strategy
controlled promotion policy
legacy safety gates
```

---

## Pipeline, Logging and Rollout Documents

```text
docs/pipeline-logging-and-run-interpretation.md
docs/branch-rollout-playbook.md
```

### `docs/pipeline-logging-and-run-interpretation.md`

Explains how to read and interpret pipeline execution logs.

It explains:

```text
where logs are stored
what run_id means
how to read pipeline status
how to identify failed steps
how to identify the slowest step
how to interpret dry-run vs real runs
how to keep logs out of Git
how the logging pattern applies to Purchases, Inventory and Zenput
```

Current implemented log folders:

```text
logs/purchases_pipeline_runs/
logs/inventory_pipeline_runs/
logs/zenput_pipeline_runs/
```

Recommended `.gitignore` entry:

```gitignore
# Pipeline run logs
logs/
```

### `docs/branch-rollout-playbook.md`

Defines the controlled rollout process for branches moving from Wansoft to Odoo.

It explains:

```text
migrated_from_wansoft pattern
new_odoo_branch pattern
active vs inactive rollout expectations
Antenas reference pattern
La Esquina Coyoacán migrated pattern
CentroMyJ new branch pattern
Puebla future inactive rollout
required file updates
required SQL updates
validation queries
why DROP TABLE should be avoided in normal rollout testing
```

---

## Domain and Policy Documents

```text
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

### `docs/inventory-domain-closeout.md`

Documents the technical closure of the Inventory domain baseline.

It explains:

```text
inventory scope classification
dictionary governance
inventory lifecycle support
backlog status
residual not_found status
pending_review status
remaining considerations
```

### `docs/inventory-runbook.md`

Operational runbook for the Inventory domain.

It explains:

```text
recommended execution by pipeline
manual execution order
pipeline dry-run
real pipeline execution
optional bridge reports
inventory output validation
pipeline logging
troubleshooting steps
controlled promotion policy
safe execution checklist
```

Current Inventory pipeline files:

```text
scripts/run_inventory_pipeline.py
scripts/test_run_inventory_pipeline.py
scripts/validate_inventory_outputs.py
```

Current Inventory log folder:

```text
logs/inventory_pipeline_runs/
```

### `docs/purchases-company-migration-policy.md`

Documents the company migration and source governance policy for Purchases.

Key rule:

```text
COMPANY_SOURCE is the authoritative source selector.
operational_start_date only applies when COMPANY_SOURCE = 'odoo'.
```

It also documents:

```text
Antenas reference migration pattern
La Esquina Coyoacán migrated rollout pattern
CentroMyJ new Odoo branch pattern
Puebla future inactive rollout
seed SQL and maintenance SQL alignment
```

### `docs/purchases-product-mapping-policy.md`

Documents the Purchases product mapping policy.

Key rule:

```text
Explicit reference beats name similarity.
```

Products without explicit Wansoft/Odoo reference mapping remain as new products or backlog candidates.

The project does not create automatic product aliases.

### `docs/purchases-canonical-layer.md`

Documents the canonical Purchases layer.

It explains:

```text
canonical_purchase_order_snapshot
canonical_purchase_order_line_snapshot
canonical_purchase_receipt_snapshot
canonical_purchase_receipt_move_snapshot
source_system
source_domain
Odoo canonical load
Wansoft canonical load
COMPANY_SOURCE governance
internal provider handling
Antenas source split
La Esquina Coyoacán rollout validation
CentroMyJ new branch validation
Puebla future inactive rollout
Wansoft technical keys
rollout_company_patterns
validation queries
current canonical counts
```

### `docs/purchases-runbook.md`

Operational runbook for the Purchases domain.

It explains:

```text
recommended execution by pipeline
manual execution order
validation queries
troubleshooting steps
canonical refresh strategy
safe execution checklist
JSON run logging
rollout validation
source-system reload strategy
```

### `docs/zenput-legacy-assessment.md`

Documents the assessment of the existing Zenput legacy integration.

It explains:

```text
active legacy files
forms and tasks legacy scripts
write operations
target MySQL tables
credential usage
target="zenput" database routing
location_name mapping
Zenput-only locations
modernization risks
minimum modernization criteria
```

### `docs/zenput-runbook.md`

Operational runbook for Zenput controlled execution.

It explains:

```text
safe dry-run
validation-only execution
safety gate
legacy write protection
location mapping validation
output validation
Zenput JSON logs
when not to execute legacy scripts
checklist before any future real legacy execution
```

### `docs/wansoft-local-wsdl.md`

Documents the Wansoft SOAP/WSDL technical setup, including use of a local WSDL file, client configuration, environment variables, validation scripts and relationship with Wansoft endpoints.

---

## Recommended Reading Order

For a full project review, read the documentation in this order:

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

---

## Source Governance Summary

The project uses centralized source governance defined in:

```text
core/config/companies.py
```

Main source rules:

```text
Sales      -> always Wansoft
Purchases  -> COMPANY_SOURCE
Inventory  -> COMPANY_SOURCE
Zenput     -> Zenput-specific location mapping
```

`COMPANY_SOURCE` defines whether each operating company uses Wansoft or Odoo as the official source for Purchases and Inventory.

Zenput does not use `COMPANY_SOURCE` as its inclusion filter.

Zenput uses:

```text
core/config/zenput.py
```

to map:

```text
Zenput location_name -> company_source_key
```

---

## Company Mapping

### Wansoft and Odoo company mapping

Odoo company names are mapped to operational source keys.

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

Wansoft subsidiary mapping is derived from:

```python
CUENTAS_SUCURSALES
```

The derived dictionary is:

```python
WANSOFT_SUBSIDIARY_SOURCE_KEY = {
    str(subsidiary_id): company_name
    for subsidiary_id, company_name, _password in CUENTAS_SUCURSALES
}
```

Examples:

```text
4960 -> Antenas
6175 -> Cancun
5320 -> Acoxpa
6560 -> Tepeyac
5943 -> Oceanía
12806 -> Puebla
```

This avoids maintaining a second manual mapping table for Wansoft subsidiary IDs.

---

## Zenput Location Mapping

Zenput location names do not always match Odoo or Wansoft names.

The main Zenput field currently used for mapping is:

```text
submissions.location_name
```

Central mapping file:

```text
core/config/zenput.py
```

Main mapping:

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

---

## Internal Provider Companies

Some Odoo companies are used for intercompany or provider workflows but should not be treated as final operating branches in Grupo Fonda Argentina BI tables.

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
    keep the row if the buying company is a valid final company
```

Correct example:

```text
company_name = FONDA ARGENTINA LAS ANTENAS
vendor_name  = EL BODEGON DE FITO

Result:
    keep row
```

Incorrect example:

```text
company_name = EL BODEGON DE FITO

Result:
    exclude row from final branch-level canonical facts
```

---

## Canonical Layer Summary

The project separates technical source snapshots from final BI-ready canonical or analytical tables.

### Technical snapshots and output tables

Examples:

```text
odoo_purchase_order_snapshot
odoo_purchase_order_line_snapshot
odoo_purchase_receipt_snapshot
odoo_purchase_receipt_move_snapshot
odoo_inventory_snapshot
odoo_inventory_backlog
form_templates
submissions
submission_answers
zenput_tasks
```

### Canonical purchase tables

```text
canonical_purchase_order_snapshot
canonical_purchase_order_line_snapshot
canonical_purchase_receipt_snapshot
canonical_purchase_receipt_move_snapshot
```

Canonical purchase tables include:

```text
source_system = 'odoo'
source_system = 'wansoft'
```

This allows the project to preserve both systems during the transition while keeping source traceability in downstream reporting.

Zenput currently remains in controlled legacy-output validation and wrapper mode.

Future Zenput analytical or canonical tables remain pending.

---

## Current Purchases Canonical Status

The Purchases canonical layer currently supports both Odoo and Wansoft.

Current validated behaviour:

```text
Antenas:
    Wansoft historical purchases before Odoo operational start date
    Odoo final purchases from Odoo operational start date onward

La Esquina Coyoacán:
    Wansoft historical purchases before Odoo operational start date
    Odoo final purchases from Odoo operational start date onward

CentroMyJ:
    Odoo final source as new Odoo branch

Other Wansoft companies:
    Wansoft remains the final purchase source

Internal providers:
    Bodegón and Empanadas are excluded as final companies
    Bodegón and Empanadas may remain as vendors
```

Current validated canonical counts:

```text
Odoo:
    orders:        882
    lines:         4771
    receipts:      876
    receipt_moves: 4763

Wansoft:
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

## Branch Rollout Status

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

Rollout validation is implemented in:

```text
scripts/validate_purchases_canonical_layer.py
```

Validation name:

```text
rollout_company_patterns
```

---

## Architecture Principles

### 1. Odoo is read-only

This pipeline does not update Odoo to fix or normalize catalog issues.

### 2. MySQL is the governance and analytical layer

MySQL stores:

```text
mapping dictionaries
scope classification
lifecycle results
ETL snapshots
canonical tables
ETL backlogs
bridge tables for controlled dictionary expansion
company migration policies
pipeline run logs in JSON files
future validation result tables
Zenput outputs and future Zenput analytical tables
```

### 3. Scope must be resolved before mapping

Products are not treated as a single universe.

Different business scopes must be separated before dictionary matching.

### 4. Dictionary-based matching

Catalog matching is performed through controlled dictionaries stored in MySQL.

### 5. Source systems remain traceable

Canonical and analytical layers should preserve source traceability wherever relevant.

### 6. Wansoft SOAP access is centralized

Wansoft SOAP client initialization should be centralized in:

```text
core/clients/wansoft_client.py
```

ETL scripts should not instantiate Zeep clients directly with a remote WSDL URL.

### 7. Pipeline runs must be logged

Orchestrated pipelines should generate a `run_id` and JSON execution log.

Current implemented logs:

```text
logs/purchases_pipeline_runs/
logs/inventory_pipeline_runs/
logs/zenput_pipeline_runs/
```

Future database logging may be considered later.

### 8. Rollout validation must be explicit

Branch rollout expectations should be declared and validated.

Current mechanism:

```text
ROLLOUT_COMPANY_EXPECTATIONS
```

Current rule:

```text
active = True:
    enforce validation

active = False:
    document future rollout without failing current validation
```

### 9. Inventory promotions must remain controlled

Inventory dictionary promotions are excluded from default pipeline automation.

Promotion scripts require manual review and explicit approval.

### 10. Zenput legacy real execution must remain protected

Zenput legacy scripts write to MySQL and may update local state.

Therefore, real execution requires explicit approval through:

```bash
python -m scripts.run_zenput_pipeline --execute --allow-legacy-writes
```

The recommended safe command is:

```bash
python -m scripts.run_zenput_pipeline --execute --validation-only
```

---

## High-Level Architecture

```text
Odoo read-only snapshots
        ↓
Wansoft operational tables and SOAP sources
        ↓
Zenput REST API and legacy outputs
        ↓
MySQL governance and analytical layer
        ↓
Source governance through COMPANY_SOURCE
        ↓
Zenput location mapping through core/config/zenput.py
        ↓
Domain ETLs and controlled wrappers
        ↓
Snapshot, output and canonical tables
        ↓
Backlogs and dictionaries
        ↓
Pipeline validation
        ↓
JSON run logs
        ↓
Unified analytical consumption layer
```

---

## Repository Structure

```text
.
├── analysis/
├── core/
│   └── config/
│       ├── companies.py
│       └── zenput.py
├── docs/
├── extract/
├── legacy/
│   └── zenput/
│       ├── README.md
│       ├── zenput_mysql_forms.py
│       ├── zenput_mysql_tasks.py
│       ├── last_run_timestamp.txt
│       └── __init__.py
├── logs/
│   ├── purchases_pipeline_runs/
│   ├── inventory_pipeline_runs/
│   └── zenput_pipeline_runs/
├── resources/
│   └── wsdl/
├── scripts/
├── sql/
├── wansoft.sql
└── README.md
```

Important orchestration and validation files:

```text
scripts/run_purchases_pipeline.py
scripts/test_run_purchases_pipeline.py
scripts/validate_purchases_canonical_layer.py

scripts/run_inventory_pipeline.py
scripts/test_run_inventory_pipeline.py
scripts/validate_inventory_outputs.py

scripts/run_zenput_pipeline.py
scripts/test_run_zenput_pipeline.py
scripts/validate_zenput_location_mapping.py
scripts/validate_zenput_outputs.py
```

---

## Environment Configuration

Configuration is driven through `.env`.

### Inventory ETL example

```env
INVENTORY_ETL_SALES_REFERENCE_SCOPE=restaurantes
INVENTORY_ETL_SALES_REFERENCE_SOURCE=sales_reference
INVENTORY_ETL_SCOPE_INCLUDE=shared_cross_company
INVENTORY_ETL_SCOPE_BACKLOG=bodegon,empanadas,bodegon_candidate,empanadas_candidate,review_scope,operational_non_inventory
```

### Inventory not_found analyser example

```env
INVENTORY_NOT_FOUND_BUCKET=not_found
INVENTORY_SCOPE_INCLUDE=shared_cross_company,review_scope
INVENTORY_SCOPE_EXCLUDE=bodegon,empanadas,restaurantes,operational_non_inventory
INVENTORY_NOT_FOUND_EXPORT=true
INVENTORY_NOT_FOUND_EXPORT_FILE=inventory_not_found_analysis.csv
```

### Purchases ETL example

```env
PURCHASE_ETL_MIN_ORDER_DATE=2026-06-01
PURCHASE_ETL_MIN_RECEIPT_DATE=2026-06-01
PURCHASE_ETL_APPLY_PRODUCT_MAPPING=true
PURCHASE_ETL_ALLOWED_MAPPING_STATUS=approved
```

### Wansoft SOAP example

```env
WANSOFT_USE_LOCAL_WSDL=true
WANSOFT_WSDL_PATH=resources/wsdl/wansoft.wsdl
WANSOFT_SERVICE_URL=https://www.wansoft.net/wansoft.web/API/IntegrationService.asmx
```

### Zenput example

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

## Key ETL Entrypoints

### Purchases pipeline

```bash
python -m scripts.run_purchases_pipeline
```

### Purchases pipeline dry-run

```bash
python -m scripts.run_purchases_pipeline --dry-run
```

### Purchases canonical validation

```bash
python -m scripts.validate_purchases_canonical_layer
```

### Inventory pipeline

```bash
python -m scripts.run_inventory_pipeline
```

### Inventory pipeline dry-run

```bash
python -m scripts.run_inventory_pipeline --dry-run
```

### Inventory pipeline with optional bridge reports

```bash
python -m scripts.run_inventory_pipeline --include-bridge-reports
```

### Inventory pipeline smoke test

```bash
python -m scripts.test_run_inventory_pipeline
```

### Inventory output validation

```bash
python -m scripts.validate_inventory_outputs
```

### Zenput pipeline dry-run

```bash
python -m scripts.run_zenput_pipeline
```

### Zenput validation-only real execution

```bash
python -m scripts.run_zenput_pipeline --execute --validation-only
```

### Zenput safety gate test

```bash
python -m scripts.run_zenput_pipeline --execute
```

Expected behaviour:

```text
PIPELINE RESULT: FAILED
```

This failure is intentional because write-enabled legacy scripts require explicit approval.

### Zenput location mapping validation

```bash
python -m scripts.validate_zenput_location_mapping
```

### Zenput output validation

```bash
python -m scripts.validate_zenput_outputs
```

### Zenput pipeline smoke test

```bash
python -m scripts.test_run_zenput_pipeline
```

### Odoo purchases snapshot load

```bash
python -m scripts.test_odoo_purchase_etl
```

### Odoo purchase receipts load

```bash
python -m scripts.test_odoo_purchase_receipt_etl
```

### Odoo canonical purchase load

```bash
python -m scripts.test_canonical_purchase_odoo_etl
```

### Wansoft purchase subsidiary mapping report

```bash
python -m scripts.test_wansoft_purchase_subsidiary_mapping_report
```

### Wansoft canonical purchase load

```bash
python -m scripts.test_canonical_purchase_wansoft_etl
```

### Wansoft local WSDL validation

```bash
python -m scripts.test_wansoft_wsdl_client
```

---

## Sales Domain

### Current Role

The Sales domain is responsible for:

```text
homologating public-sale products between Odoo and Wansoft
building a stable sales dictionary
detecting replacements and catalog issues
preparing the commercial product layer for analytical use
```

### Status

Sales baseline is already considered functionally established.

Important rule:

```text
Sales always remain Wansoft.
```

Sales does not follow `COMPANY_SOURCE`.

---

## Inventory Domain

### Goal

Enable a scope-aware, dictionary-governed inventory ETL from Odoo into MySQL without modifying Odoo.

### Core Rules

```text
Odoo stays read-only
Inventory scope must be classified before mapping
Public-sale products are excluded from raw inventory matching
Matching is resolved in MySQL dictionaries
Inventory source follows COMPANY_SOURCE
Dictionary promotions remain controlled
```

### Scope Model

Final refined buckets:

```text
restaurantes
bodegon
empanadas
shared_cross_company
review_scope
operational_non_inventory
```

### Main Inventory Tables

```text
inventory_mapping_dictionary
inventory_product_lifecycle
odoo_inventory_scope_classification
odoo_inventory_snapshot
odoo_inventory_backlog
```

### Inventory Pipeline Summary

Run:

```bash
python -m scripts.run_inventory_pipeline
```

Dry-run:

```bash
python -m scripts.run_inventory_pipeline --dry-run
```

Extended with bridge reports:

```bash
python -m scripts.run_inventory_pipeline --include-bridge-reports
```

Current base pipeline steps:

```text
01. Odoo inventory scope classification
02. Odoo inventory ETL
03. Inventory dictionary lookup validation
04. Inventory dictionary application validation
05. Inventory not_found analyzer
06. Inventory not_found priority backlog
07. Inventory output validation
```

Current extended pipeline steps:

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

### Current Inventory Pipeline Status

```text
dry-run validated
smoke test validated
real base execution validated
optional bridge reports validated
output validation integrated as required
JSON logging implemented
promotion scripts excluded from default automation
```

Expected base result:

```text
total_steps: 7
success: 7
PIPELINE RESULT: COMPLETED
```

Expected extended result:

```text
total_steps: 10
success: 10
PIPELINE RESULT: COMPLETED
```

### Inventory Output Validation

Validator:

```bash
python -m scripts.validate_inventory_outputs
```

Current validations:

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

Expected result:

```text
total_validations: 8
passed: 8
VALIDATION RESULT: PASSED
```

### Validated Promotion Pattern

Dictionary promotions remain manual.

Excluded from default automation:

```text
scripts.test_promote_inventory_bridge_to_dictionary
scripts.test_promote_inventory_not_found_p1_to_dictionary
scripts.test_promote_inventory_not_found_p2_to_dictionary
scripts.test_promote_inventory_not_found_residual_to_dictionary
```

Important rule:

```text
Inventory dictionary promotions must not run automatically unless explicitly approved.
```

---

## Purchases Domain

### Goal

Build a Purchases domain that can analyze Odoo and Wansoft purchase activity while remaining aligned with source governance, product mapping rules, inventory dictionary logic, run logging and rollout validation.

### Current Status

Purchases domain is functionally advanced and operationally orchestrated.

Currently implemented:

```text
Odoo purchase order extraction
Odoo purchase order line extraction
Odoo purchase receipt extraction
Odoo purchase receipt move extraction
Odoo purchase ETL to MySQL
Odoo purchase product mapping
Purchase line classification
Purchase inventory mapping backlog
Company migration policy
COMPANY_SOURCE governance
Odoo canonical purchase load
Wansoft canonical purchase load
Canonical purchase layer with source_system
Purchases orchestration pipeline
Purchases canonical validation
JSON run logging
Rollout company pattern validation
```

### Main Purchases Tables

#### Odoo snapshots

```text
odoo_purchase_order_snapshot
odoo_purchase_order_line_snapshot
odoo_purchase_receipt_snapshot
odoo_purchase_receipt_move_snapshot
```

#### Backlog and policy tables

```text
odoo_company_migration_policy
odoo_purchase_inventory_mapping_backlog
```

#### Canonical tables

```text
canonical_purchase_order_snapshot
canonical_purchase_order_line_snapshot
canonical_purchase_receipt_snapshot
canonical_purchase_receipt_move_snapshot
```

---

## Zenput Domain

### Goal

Bring the existing Zenput legacy integration into the same operational standard as Purchases and Inventory, without replacing working legacy scripts blindly.

### Current Status

Zenput is currently in controlled modernization.

Implemented:

```text
legacy script assessment
write operation documentation
credential and .env review
central Zenput location mapping
location mapping validation
Zenput output validation
safe pipeline wrapper
dry-run mode
validation-only mode
safety gate
JSON run logging
Zenput runbook
```

### Current legacy scripts

```text
legacy/zenput/zenput_mysql_forms.py
legacy/zenput/zenput_mysql_tasks.py
```

### Current legacy state file

```text
legacy/zenput/last_run_timestamp.txt
```

### Current Zenput output tables

```text
form_templates
submissions
submission_answers
zenput_tasks
```

### Current modern Zenput files

```text
core/config/zenput.py
scripts/validate_zenput_location_mapping.py
scripts/validate_zenput_outputs.py
scripts/run_zenput_pipeline.py
scripts/test_run_zenput_pipeline.py
docs/zenput-legacy-assessment.md
docs/zenput-runbook.md
```

### Zenput Pipeline Summary

Dry-run:

```bash
python -m scripts.run_zenput_pipeline
```

Validation-only real execution:

```bash
python -m scripts.run_zenput_pipeline --execute --validation-only
```

Safety gate test:

```bash
python -m scripts.run_zenput_pipeline --execute
```

Full legacy real execution, protected:

```bash
python -m scripts.run_zenput_pipeline --execute --allow-legacy-writes
```

Current recommendation:

```text
Use validation-only execution as the safe real execution mode.
Do not run full legacy real execution unless explicitly approved.
```

### Current Zenput Pipeline Steps

```text
01. Zenput location mapping validation
02. Zenput forms legacy ETL
03. Zenput tasks legacy ETL
04. Zenput output validation
```

In dry-run, all steps are simulated.

In validation-only execution, only validators run.

In full legacy execution, forms and tasks legacy scripts may write to MySQL and update timestamp state.

### Zenput Output Validation

Validator:

```bash
python -m scripts.validate_zenput_outputs
```

Current validations:

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

### Zenput Location Mapping Validation

Validator:

```bash
python -m scripts.validate_zenput_location_mapping
```

Current validations:

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

---

## Purchase Product Mapping Policy

Purchase lines are enriched using:

```text
purchase.order.line.product_id
→ inventory_mapping_dictionary.odoo_product_id
→ wansoft_code
→ wansoft_product_name
→ wansoft_department
```

The Purchases domain does not create automatic product aliases.

Key rule:

```text
Explicit reference beats name similarity.
```

If a product has no explicit Wansoft/Odoo reference mapping:

```text
it remains a new product or backlog candidate
it is not automatically mapped by similar name
```

---

## Purchase Canonical Flow

```text
Odoo purchase snapshots
        ↓
Odoo eligibility by COMPANY_SOURCE
        ↓
source_system = odoo
        ↓
canonical_purchase_*

Wansoft getinputinventory_entrada
        ↓
TipoEntrada = 'Factura'
        ↓
Wansoft subsidiary mapping
        ↓
COMPANY_SOURCE
        ↓
source_system = wansoft
        ↓
canonical_purchase_*
```

---

## Wansoft Purchase Source

Wansoft purchase-like data is loaded from:

```text
getinputinventory_entrada
```

Filter:

```sql
WHERE TipoEntrada = 'Factura'
```

Main fields used:

```text
id
subsidiary_name
IdEntrada
CodigoProducto
NombreProducto
Departamento
UnidadDeMedida
Cantidad
CostoUnitario
FechaEntrada
Factura
FechaFactura
RFCProveedor
ClaveProveedor
NombreProveedor
FechaReal
```

`FechaEntrada` is used as operational purchase/input date.

`FechaReal` is preserved as Wansoft upload or capture reference date.

---

## Wansoft Technical Keys

Wansoft canonical technical keys use stable hashed identifiers to avoid issues caused by:

```text
case-insensitive MySQL collation
trailing spaces
long natural keys
inconsistent invoice casing
duplicate invoice references
```

Example shape:

```text
source_order_id = wansoft_order:{company_key}:{fecha_key}:{hash}
source_receipt_id = wansoft_receipt:{company_key}:{fecha_key}:{hash}
source_order_line_id = wansoft_line:{id}
source_stock_move_id = wansoft_move:{id}
```

---

# Pipeline Logs

Pipeline logs are written to:

```text
logs/purchases_pipeline_runs/
logs/inventory_pipeline_runs/
logs/zenput_pipeline_runs/
```

Logs should not be committed.

Recommended `.gitignore` entry:

```gitignore
# Pipeline run logs
logs/
```

---

# Wansoft SOAP / Local WSDL

## Purpose

The Wansoft SOAP integration uses a local WSDL file to avoid relying on dynamic WSDL download during each execution.

The WSDL should be stored at:

```text
resources/wsdl/wansoft.wsdl
```

## Environment Variables

```env
WANSOFT_USE_LOCAL_WSDL=true
WANSOFT_WSDL_PATH=resources/wsdl/wansoft.wsdl
WANSOFT_SERVICE_URL=https://www.wansoft.net/wansoft.web/API/IntegrationService.asmx
```

## Centralized Client

All Wansoft integrations should use:

```python
from core.clients.wansoft_client import get_wansoft_client

client = get_wansoft_client()
```

Avoid this pattern inside ETL scripts:

```python
from zeep import Client

client = Client("https://www.wansoft.net/wansoft.web/API/IntegrationService.asmx?wsdl")
```

## WSDL Test

Run:

```bash
python -m scripts.test_wansoft_wsdl_client
```

Expected output:

```text
WSDL resolved path: file:///...
SERVICES
PORTS / OPERATIONS
DONE
```

---

# SQL Folder

The `sql/` folder is located at the repository root.

```text
sql/
├── maintenance/
│   └── update_odoo_company_migration_policy.sql
└── seeds/
    └── seed_odoo_company_migration_policy.sql
```

## Purpose

### `sql/seeds/`

Contains initial controlled seed scripts.

### `sql/maintenance/`

Contains controlled SQL examples and update scripts.

These scripts are versioned because they represent configuration or operational governance, not runtime ETL logic.

Rollout changes should be reflected in:

```text
sql/seeds/seed_odoo_company_migration_policy.sql
sql/maintenance/update_odoo_company_migration_policy.sql
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
bridge report generation
Wansoft SOAP client initialization through local WSDL
canonical layer refresh by source_system
canonical validation
inventory output validation
Zenput location mapping validation
Zenput output validation
Zenput validation-only execution
JSON run logging
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
last_run_timestamp.txt changes
Zenput submission_answers delete/reinsert behaviour
```

---

# Setup Notes

## Requirements

```text
Python environment with required dependencies
MySQL access
Odoo API credentials
Wansoft SOAP credentials
Zenput API token
Zenput MySQL target credentials
Local Wansoft WSDL file
.env configured
logs/ ignored by Git
```

## General Execution Approach

Most workflows were originally executed through `scripts/test_*.py` files to validate each layer before production-style orchestration.

Purchases now has a controlled orchestration script:

```text
scripts/run_purchases_pipeline.py
```

Inventory now has a controlled orchestration script:

```text
scripts/run_inventory_pipeline.py
```

Zenput now has a controlled safe wrapper:

```text
scripts/run_zenput_pipeline.py
```

---

# Recommended Workflow For Future Development

## 1. Build domain baseline

```text
isolate source universe
understand fields
classify scope or location mapping
define snapshot, output, backlog or staging tables
```

## 2. Add governance layer

```text
dictionary
bridges
prioritization
controlled promotion
company policy
source governance
rollout expectations
Zenput location mapping
```

## 3. Validate through ETL reruns or read-only validators

```text
measure snapshot growth
measure backlog reduction
confirm source-system isolation
confirm rollout patterns
confirm location mapping coverage
keep Odoo untouched
protect legacy state files
```

## 4. Promote to canonical or analytical layer

```text
apply COMPANY_SOURCE where relevant
apply Zenput location_name mapping where relevant
apply operational start dates when relevant
load source-system-specific canonical rows
validate source split
validate provider handling
validate rollout patterns
validate Zenput-only locations
```

## 5. Orchestrate and log

```text
run pipeline or safe wrapper
generate run_id
write JSON log
run final validator
review slowest step
keep logs out of Git
```

---

# Notes For Future Production Rollout

Before broader production automation, complete or review:

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
inventory JSON logging
Zenput safe wrapper
Zenput validation-only execution
Zenput legacy real execution approval process
future database run-log persistence
future validation result persistence
```

---

# Suggested Commit Patterns

## Technical documentation index and domain documentation

```bash
git add README.md docs/

git commit -m "docs(project): update technical guide and domain documentation"

git push
```

## Purchases canonical Odoo and Wansoft load

```bash
git add .

git commit -m "feat(purchases): load Odoo and Wansoft purchases into canonical layer"

git push
```

## Purchases pipeline orchestration and rollout validation

```bash
git add README.md docs/ scripts/ sql/ core/

git commit -m "feat(purchases): add pipeline orchestration and rollout validation"

git push
```

## Inventory pipeline orchestration and validation

```bash
git add README.md docs/ scripts/

git commit -m "feat(inventory): add pipeline orchestration and output validation"

git push
```

## Zenput safe wrapper and validation

```bash
git add README.md docs/ core/config/zenput.py scripts/validate_zenput_location_mapping.py scripts/validate_zenput_outputs.py scripts/run_zenput_pipeline.py scripts/test_run_zenput_pipeline.py

git commit -m "feat(zenput): add safe pipeline wrapper and validation"

git push
```

## Wansoft local WSDL

```bash
git add .

git commit -m "fix(wansoft): use local WSDL for SOAP client initialization"

git push
```

---

# Current Next Step

Recommended next step:

```text
Finish Section 15 documentation consistency.
Commit the Zenput assessment, configuration, validation and safe wrapper package.
```

After Section 15 is committed, the next technical options are:

```text
1. Add ZENPUT_API_TOKEN placeholder to core/config/.env.example if missing
2. Review first controlled Zenput legacy real execution criteria
3. Review transaction safety around submission_answers delete/reinsert
4. Review future handling of last_run_timestamp.txt
5. Define future Zenput analytical tables
6. Review database run-log persistence
7. Continue unified analytical consumption layer design
```

Recommended technical priority:

```text
Close Section 15 documentation and commit first.
Then decide whether to approve a controlled Zenput legacy real execution or continue with additional safety reviews.
```

Reason:

```text
Zenput now has a safe wrapper, central location mapping, read-only validators and JSON logging.
Legacy write execution is still protected and should not be run casually.
```

---

## Current Analytical Purchase Layer Status

The analytical purchase layer has reached a validated multi-level structure.

Validated shared dimensions:

```text
dim_company_analytical
dim_time
dim_vendor
dim_product
```

Validated analytical support table:

```text
analytics_company_domain_coverage
```

Validated purchase analytical objects:

```text
analytics_purchase_order_lines
analytics_purchase_orders
analytics_purchase_daily_company_product
```

### Validated Purchase Reconciliation Chain

The current validated purchase analytical layer reconciles through:

```text
canonical_purchase_order_line_snapshot
-> analytics_purchase_order_lines
-> analytics_purchase_orders
-> analytics_purchase_daily_company_product
```

Shared reconciled line count:

```text
749932
```

Shared reconciled purchase amount:

```text
1034075208.2566
```

### analytics_purchase_order_lines

Purpose:

```text
Detailed analytical purchase line fact.
1 row = 1 canonical purchase order line.
```

Validated result:

```text
total_rows: 749932
include_in_business_views: 676186
excluded_from_business_views: 73746
internal_vendor_rows: 20061
review_required_product_rows: 4936
orphan_product_rows: 50978
orphan_company_rows: 0
orphan_vendor_rows: 0
invalid_order_date_rows: 0
```

Validation result:

```text
total_validations: 14
passed: 14
failed: 0
VALIDATION RESULT: PASSED
```

Amount reconciliation:

```text
canonical_purchase_order_line_snapshot.price_total: 1034075208.2566
analytics_purchase_order_lines.price_total: 1034075208.2566
difference: 0.0000
```

### analytics_purchase_orders

Purpose:

```text
Order-level analytical purchase fact.
1 row = 1 source purchase order group.
```

Validated result:

```text
total_orders: 145876
include_in_business_views: 143188
excluded_from_business_views: 2688
review_required_orders: 26497
no_business_line_orders: 2688
inconsistent_company_orders: 0
inconsistent_date_orders: 0
inconsistent_vendor_orders: 0
```

Line reconciliation:

```text
analytics_purchase_order_lines rows: 749932
analytics_purchase_orders summed line_count: 749932
```

Amount reconciliation:

```text
analytics_purchase_order_lines.price_total: 1034075208.2566
analytics_purchase_orders.price_total_total: 1034075208.2566
difference: 0.0000
```

Validation result:

```text
total_validations: 14
passed: 14
failed: 0
VALIDATION RESULT: PASSED
```

Technical note:

```text
Initial build failed with MySQL error 2013 Lost connection to MySQL server during query.
The build was rewritten to use INSERT INTO SELECT.
Final build completed successfully.
```

### analytics_purchase_daily_company_product

Purpose:

```text
Daily company-product-source purchase aggregate.
1 row = 1 company_source_key + 1 order_date_key + 1 product_analytical_group_key + 1 source_system.
```

Validated result:

```text
total_rows: 626258
include_in_business_views: 595831
excluded_from_business_views: 30427
total_line_count: 749932
total_business_line_count: 676186
total_excluded_line_count: 73746
total_review_required_line_count: 55914
total_internal_vendor_line_count: 20061
total_review_required_product_line_count: 4936
total_orphan_product_line_count: 50978
```

Amount reconciliation:

```text
total_price_total: 1034075208.2566
total_business_price_total: 989935685.4550
total_excluded_price_total: 44139522.8016
```

Validation result:

```text
total_validations: 15
passed: 15
failed: 0
VALIDATION RESULT: PASSED
```

### Product Governance Note

Current product governance diagnostics:

```text
orphan_product_lines: 50978
review_required_product_lines: 4936
```

Current handling:

```text
Rows without product_analytical_key remain visible.
Rows without product_analytical_key are excluded from default business-facing views when required.
Rows without product_analytical_key are grouped under product_analytical_group_key = 0 in analytics_purchase_daily_company_product.
```

This preserves reconciliation while keeping product mapping backlog visible.

### Current Analytical Purchase Layer Status

```text
Status: validated
Purchase line fact: complete
Purchase order fact: complete
Daily company-product aggregate: complete
Known remaining work: product governance backlog, key stability review and orchestration documentation
```

---

## Current Next Step - Updated After Section 17.28

Recommended next step:

```text
Paso 17.29 - Revisar y cerrar documentación de Sección 17
```

Recommended review scope:

```text
README.md
project-status-and-todo.md
docs/analytics-purchase-order-lines-design.md
docs/analytics-purchase-orders-design.md
docs/analytics-purchase-daily-company-product-design.md
scripts/build_analytics_purchase_order_lines.py
scripts/validate_analytics_purchase_order_lines.py
scripts/build_analytics_purchase_orders.py
scripts/validate_analytics_purchase_orders.py
scripts/build_analytics_purchase_daily_company_product.py
scripts/validate_analytics_purchase_daily_company_product.py
```

Reason:

```text
The analytical purchase layer now has validated line, order and daily company-product outputs.
The next work should close Section 17 documentation safely and prepare a commit without replacing historical project documentation.
```

