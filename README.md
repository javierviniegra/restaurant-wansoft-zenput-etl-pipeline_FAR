# Wansoft + Odoo Data Warehouse & ETL Pipeline

## Overview

This repository contains the Python ETL and catalog-governance layer used to integrate **Odoo**, **Wansoft**, and other operational sources into a centralized **MySQL-based analytical environment**.

The project is designed around a few core principles:

- **Odoo is treated as a read-only source**
- **Wansoft remains the source of truth for sales**
- **MySQL stores mapping dictionaries, scope classification, lifecycle logic, snapshots, canonical layers, run logs, validations, and backlogs**
- **Catalog governance is resolved outside Odoo**
- **Wansoft SOAP access is centralized through a local WSDL client**
- **Purchases and Inventory use company-level source governance**
- **Canonical tables preserve source traceability through `source_system`**
- **Pipeline execution must be auditable**
- **Branch rollout behaviour must be validated before production use**

The goal is to enable operational, analytical, and accounting-friendly data flows without modifying Odoo as part of the ETL process.

---

## Current Project Status

### Implemented or advanced domains

```text
Sales
Inventory
Purchases
```

### Current validated milestones

```text
Inventory domain baseline completed
Inventory dictionary governance established
Inventory lifecycle analysis implemented
Inventory backlog and bridge-review process established
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
```

### Current project stage

```text
Validated domain ETLs
→ Controlled Purchases orchestration
→ Pipeline logging and validation
→ Branch rollout control
→ Inventory orchestration pending
→ Power BI / reporting consumption
```

The project is no longer in early discovery.

The current focus is to move from individually validated scripts to controlled, repeatable, auditable execution flows.

---

## Current Orchestration Status

```text
Purchases pipeline: implemented
Purchases canonical validation: implemented
Purchases JSON logging: implemented
Purchases rollout validation: implemented
Inventory pipeline: pending
Inventory validation: pending
Production scheduling: pending
Power BI semantic layer: pending
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
Inventory pipeline pending work
Puebla future rollout pending work
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
Inventory pipeline pending work
rollout validation strategy
```

---

## Pipeline and Rollout Documents

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
how the same pattern should later apply to Inventory
```

Current implemented log folder:

```text
logs/purchases_pipeline_runs/
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
docs/wansoft-local-wsdl.md
```

### `docs/inventory-domain-closeout.md`

Documents the technical closure of the Inventory domain, including scope classification, dictionary governance, lifecycle and backlog status, and remaining considerations.

### `docs/inventory-runbook.md`

Operational runbook for the Inventory domain.

It explains:

```text
how to execute Inventory ETLs
how to validate outputs
how to review backlog candidates
how to handle dictionary promotion processes
how to troubleshoot common inventory issues
```

Inventory currently does not yet have a full pipeline equivalent to Purchases.

Pending Inventory files:

```text
scripts/run_inventory_pipeline.py
scripts/test_run_inventory_pipeline.py
scripts/validate_inventory_outputs.py
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

Products without explicit Wansoft/Odoo reference mapping remain as new products or backlog candidates. The project does not create automatic product aliases.

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

### `docs/wansoft-local-wsdl.md`

Documents the Wansoft SOAP/WSDL technical setup, including use of a local WSDL file, client configuration, environment variables, validation scripts, and relationship with Wansoft endpoints.

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
12. docs/wansoft-local-wsdl.md
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
```

`COMPANY_SOURCE` defines whether each operating company uses Wansoft or Odoo as the official source for Purchases and Inventory.

Example:

```python
COMPANY_SOURCE = {
    "Acoxpa": "wansoft",
    "Aeropuerto": "wansoft",
    "Isabel La Católica": "wansoft",
    "Antenas": "odoo",
    "CentroMyJ": "odoo",
    "La Esquina Coyoacán": "odoo",
    "Taquería parroquia": "wansoft",
    "Vía Vallejo": "wansoft",
    "Viaducto": "wansoft",
    "Taquería Viaducto": "wansoft",
    "San Jeronimo": "wansoft",
    "Tepeyac": "wansoft",
    "Playa del Carmen": "wansoft",
    "Oceanía": "wansoft",
    "Cancun": "wansoft",
    "Napoles": "wansoft",
    "Metepec": "wansoft",
    "Versalles": "wansoft",
    "Puebla": "wansoft",
}
```

### Important source-governance rule

```text
COMPANY_SOURCE determines whether a company uses Odoo or Wansoft.
operational_start_date only applies when COMPANY_SOURCE marks the company as Odoo.
.env dates are fallback values, not the main business rule.
```

---

## Company Mapping

### Odoo company mapping

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

### Wansoft subsidiary mapping

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

The project separates technical source snapshots from final BI-ready canonical tables.

### Technical snapshots

Examples:

```text
odoo_purchase_order_snapshot
odoo_purchase_order_line_snapshot
odoo_purchase_receipt_snapshot
odoo_purchase_receipt_move_snapshot
odoo_inventory_snapshot
odoo_inventory_backlog
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

### 2. MySQL is the governance layer

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
```

### 3. Scope must be resolved before mapping

Products are not treated as a single universe.

Different business scopes must be separated before dictionary matching.

### 4. Dictionary-based matching

Catalog matching is performed through controlled dictionaries stored in MySQL.

### 5. Source systems remain traceable

Canonical tables preserve:

```text
source_system
source_domain
company_source_key
final_purchase_source_status
```

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
```

Future inventory logs:

```text
logs/inventory_pipeline_runs/
```

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

---

## High-Level Architecture

```text
Odoo read-only snapshots
        ↓
Wansoft operational tables and SOAP sources
        ↓
MySQL governance layer
        ↓
Source governance through COMPANY_SOURCE
        ↓
Domain ETLs
        ↓
Snapshot tables
        ↓
Backlogs and dictionaries
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

## Repository Structure

```text
.
├── analysis/
│   ├── build_purchase_backlog_product_reference_report.py
│   ├── build_purchase_company_source_eligibility_report.py
│   ├── build_purchase_inventory_mapping_backlog.py
│   ├── build_sales_product_mapping.py
│   ├── build_wansoft_purchase_subsidiary_mapping_report.py
│   ├── inventory_not_found_analyzer.py
│   ├── odoo_inventory_scope_classifier.py
│   ├── promote_inventory_bridge_to_dictionary.py
│   ├── promote_inventory_not_found_p1_to_dictionary.py
│   ├── promote_inventory_not_found_p2_to_dictionary.py
│   ├── promote_inventory_not_found_residual_to_dictionary.py
│   ├── review_scope_refiner.py
│   ├── review_scope_refiner_v2.py
│   ├── save_inventory_bridge_report.py
│   ├── save_inventory_not_found_p1_bridge.py
│   ├── save_inventory_not_found_p2_bridge.py
│   ├── save_inventory_not_found_priority_backlog.py
│   ├── save_inventory_not_found_residual_bridge.py
│   ├── save_odoo_inventory_scope_classification.py
│   ├── save_purchase_inventory_mapping_backlog.py
│   ├── save_refined_odoo_inventory_scope.py
│   ├── save_review_scope_refiner.py
│   ├── save_review_scope_refiner_v2.py
│   └── save_wansoft_inventory_operational_lifecycle.py
│
├── core/
│   ├── clients/
│   │   ├── __init__.py
│   │   └── wansoft_client.py
│   ├── config/
│   │   ├── .env.example
│   │   ├── companies.py
│   │   ├── env_loader.py
│   │   └── inventory_env.py
│   └── database/
│       ├── mysql.py
│       └── odoo.py
│
├── docs/
│   ├── branch-rollout-playbook.md
│   ├── inventory-domain-closeout.md
│   ├── inventory-runbook.md
│   ├── pipeline-logging-and-run-interpretation.md
│   ├── production-orchestration-plan.md
│   ├── project-status-and-todo.md
│   ├── project-technical-guide.md
│   ├── purchases-canonical-layer.md
│   ├── purchases-company-migration-policy.md
│   ├── purchases-product-mapping-policy.md
│   ├── purchases-runbook.md
│   └── wansoft-local-wsdl.md
│
├── extract/
│   ├── inventory/
│   │   ├── odoo_inventory.py
│   │   └── odoo_inventory_etl.py
│   ├── products/
│   │   └── odoo_products.py
│   ├── purchases/
│   │   ├── canonical_purchase_etl.py
│   │   ├── odoo_purchase_etl.py
│   │   ├── odoo_purchase_order_lines.py
│   │   ├── odoo_purchase_orders.py
│   │   └── odoo_purchase_receipts.py
│   └── utils/
│       ├── inventory_dictionary_lookup.py
│       ├── inventory_dictionary_wrapper.py
│       └── inventory_scope_lookup.py
│
├── logs/
│   └── purchases_pipeline_runs/
│
├── resources/
│   └── wsdl/
│       └── wansoft.wsdl
│
├── scripts/
│   ├── run_purchases_pipeline.py
│   ├── test_apply_inventory_dictionary.py
│   ├── test_canonical_purchase_odoo_etl.py
│   ├── test_canonical_purchase_wansoft_etl.py
│   ├── test_company_source_governance.py
│   ├── test_extract_odoo_purchase_receipts.py
│   ├── test_extract_odoo_purchases.py
│   ├── test_inventory_dictionary_lookup.py
│   ├── test_inventory_not_found_analyzer.py
│   ├── test_inventory_not_found_p1_bridge.py
│   ├── test_inventory_not_found_p2_bridge.py
│   ├── test_inventory_not_found_priority_backlog.py
│   ├── test_inventory_not_found_residual_bridge.py
│   ├── test_odoo_inventory_etl.py
│   ├── test_odoo_inventory_scope_classification.py
│   ├── test_odoo_purchase_etl.py
│   ├── test_odoo_purchase_receipt_etl.py
│   ├── test_promote_inventory_bridge_to_dictionary.py
│   ├── test_promote_inventory_not_found_p1_to_dictionary.py
│   ├── test_promote_inventory_not_found_p2_to_dictionary.py
│   ├── test_promote_inventory_not_found_residual_to_dictionary.py
│   ├── test_purchase_backlog_product_reference_report.py
│   ├── test_purchase_company_source_eligibility.py
│   ├── test_purchase_inventory_mapping_backlog.py
│   ├── test_refine_odoo_inventory_scope.py
│   ├── test_review_scope_refiner_v2.py
│   ├── test_run_purchases_pipeline.py
│   ├── test_wansoft_purchase_subsidiary_mapping_report.py
│   ├── test_wansoft_wsdl_client.py
│   └── validate_purchases_canonical_layer.py
│
├── sql/
│   ├── maintenance/
│   │   └── update_odoo_company_migration_policy.sql
│   └── seeds/
│       └── seed_odoo_company_migration_policy.sql
│
├── wansoft.sql
└── README.md
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

## Inventory not_found analyser example

```env
INVENTORY_NOT_FOUND_BUCKET=not_found
INVENTORY_SCOPE_INCLUDE=shared_cross_company,review_scope
INVENTORY_SCOPE_EXCLUDE=bodegon,empanadas,restaurantes,operational_non_inventory
INVENTORY_NOT_FOUND_EXPORT=true
INVENTORY_NOT_FOUND_EXPORT_FILE=inventory_not_found_analysis.csv
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

## Inventory

```bash
python -m scripts.test_odoo_inventory_etl
```

## Inventory scope classification

```bash
python -m scripts.test_odoo_inventory_scope_classification
```

## Inventory dictionary lookup

```bash
python -m scripts.test_inventory_dictionary_lookup
```

## Inventory dictionary application

```bash
python -m scripts.test_apply_inventory_dictionary
```

## Inventory not_found analyser

```bash
python -m scripts.test_inventory_not_found_analyzer
```

## Odoo purchases snapshot load

```bash
python -m scripts.test_odoo_purchase_etl
```

## Odoo purchase receipts load

```bash
python -m scripts.test_odoo_purchase_receipt_etl
```

## Purchase inventory mapping backlog

```bash
python -m scripts.test_purchase_inventory_mapping_backlog
```

## Purchase backlog product reference report

```bash
python -m scripts.test_purchase_backlog_product_reference_report
```

## Purchase company source eligibility

```bash
python -m scripts.test_purchase_company_source_eligibility
```

## Odoo canonical purchase load

```bash
python -m scripts.test_canonical_purchase_odoo_etl
```

## Wansoft purchase subsidiary mapping report

```bash
python -m scripts.test_wansoft_purchase_subsidiary_mapping_report
```

## Wansoft canonical purchase load

```bash
python -m scripts.test_canonical_purchase_wansoft_etl
```

## Wansoft local WSDL validation

```bash
python -m scripts.test_wansoft_wsdl_client
```

---

# Sales Domain

## Current Role

The Sales domain is responsible for:

```text
homologating public-sale products between Odoo and Wansoft
building a stable sales dictionary
detecting replacements and catalog issues
preparing the commercial product layer for analytical use
```

## Status

Sales baseline is already considered functionally established.

Important rule:

```text
Sales always remain Wansoft.
```

Sales does not follow `COMPANY_SOURCE`.

---

# Inventory Domain

## Goal

Enable a scope-aware, dictionary-governed inventory ETL from Odoo into MySQL without modifying Odoo.

## Core Rules

```text
Odoo stays read-only
Inventory scope must be classified before mapping
Public-sale products are excluded from raw inventory matching
Matching is resolved in MySQL dictionaries
Inventory source follows COMPANY_SOURCE
```

## Scope Model

Final refined buckets:

```text
restaurantes
bodegon
empanadas
shared_cross_company
review_scope
operational_non_inventory
```

## Main Inventory Tables

```text
inventory_mapping_dictionary
inventory_product_lifecycle
odoo_inventory_scope_classification
odoo_inventory_snapshot
odoo_inventory_backlog
```

## Validated Promotion Pattern

```text
not_found backlog
→ prioritize
→ build bridge against lifecycle
→ promote approved candidates to dictionary
→ rerun ETL
→ measure improvement
```

## Current Inventory Baseline State

At current closeout state:

```text
snapshot rows: 1660
residual functional not_found: 98 unique products
residual functional pending_review: 5 unique products
```

This means the inventory phase is:

```text
technically stable
functionally advanced
good enough to support the next domain
```

## Inventory Orchestration Pending

Inventory still needs an orchestration layer equivalent to Purchases.

Pending:

```text
scripts/run_inventory_pipeline.py
scripts/test_run_inventory_pipeline.py
scripts/validate_inventory_outputs.py
logs/inventory_pipeline_runs/
```

Important rule:

```text
Inventory dictionary promotions must not run automatically unless explicitly approved.
```

---

# Purchases Domain

## Goal

Build a Purchases domain that can analyze Odoo and Wansoft purchase activity while remaining aligned with source governance, product mapping rules, inventory dictionary logic, run logging, and rollout validation.

## Current Status

Purchases domain is now functionally advanced and operationally orchestrated.

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

## Main Purchases Tables

### Odoo snapshots

```text
odoo_purchase_order_snapshot
odoo_purchase_order_line_snapshot
odoo_purchase_receipt_snapshot
odoo_purchase_receipt_move_snapshot
```

### Backlog and policy tables

```text
odoo_company_migration_policy
odoo_purchase_inventory_mapping_backlog
```

### Canonical tables

```text
canonical_purchase_order_snapshot
canonical_purchase_order_line_snapshot
canonical_purchase_receipt_snapshot
canonical_purchase_move_snapshot
canonical_purchase_receipt_move_snapshot
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

# Purchases Pipeline Summary

Run:

```bash
python -m scripts.run_purchases_pipeline
```

Dry-run:

```bash
python -m scripts.run_purchases_pipeline --dry-run
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

Expected successful result:

```text
PIPELINE RESULT: COMPLETED
```

---

# Pipeline Logs

Purchases pipeline logs are written to:

```text
logs/purchases_pipeline_runs/
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
Wansoft SOAP client initialization through local WSDL
canonical layer refresh by source_system
canonical validation
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
```

---

# Setup Notes

## Requirements

```text
Python environment with required dependencies
MySQL access
Odoo API credentials
Wansoft SOAP credentials
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

Inventory still needs an equivalent orchestration script.

---

# Recommended Workflow For Future Development

## 1. Build domain baseline

```text
isolate source universe
understand fields
classify scope
define snapshot and backlog
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
```

## 3. Validate through ETL reruns

```text
measure snapshot growth
measure backlog reduction
confirm source-system isolation
confirm rollout patterns
keep Odoo untouched
```

## 4. Promote to canonical layer

```text
apply COMPANY_SOURCE
apply operational start dates when relevant
load source_system-specific canonical rows
validate source split
validate provider handling
validate rollout patterns
```

## 5. Orchestrate and log

```text
run pipeline
generate run_id
write JSON log
run final validator
review slowest step
keep logs out of Git
```

---

# Notes For Future Production Rollout

Before broader production automation, complete:

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
```

---

# Suggested Commit Patterns

## Technical documentation index and domain documentation

```bash
git add README.md docs/

git commit -m "docs(project): add technical guide and domain documentation"

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
Finish Section 13 documentation consistency.
Commit the completed Purchases orchestration, logging and rollout validation package.
```

After Section 13 is committed, the next technical options are:

```text
1. Inventory pipeline orchestration
2. Inventory output validation
3. Inventory JSON logging
4. Wansoft canonical performance review
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