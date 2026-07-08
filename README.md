# Wansoft + Odoo Data Warehouse & ETL Pipeline

## Overview

This repository contains the Python ETL and catalog-governance layer used to integrate **Odoo**, **Wansoft**, and other operational sources into a centralized **MySQL-based analytical environment**.

The project is designed around a core principle:

- **Odoo is treated as a read-only source**
- **MySQL stores mapping dictionaries, scope classification, lifecycle logic, snapshots, and backlogs**
- **Catalog governance is resolved outside Odoo**
- **Wansoft SOAP access is centralized through a local WSDL client**

The goal is to enable operational, analytical, and accounting-friendly data flows without modifying Odoo as part of the ETL process.

---

## Current Domains

### Implemented / Advanced

- **Sales**
- **Inventory**

### In progress

- **Purchases**

---

## Architecture Principles

### 1. Odoo is read-only

This pipeline does **not** update Odoo to fix or normalize catalog issues.

### 2. MySQL is the governance layer

MySQL stores:

- mapping dictionaries
- scope classification
- lifecycle results
- ETL snapshots
- ETL backlogs
- bridge tables for controlled dictionary expansion
- company migration policies

### 3. Scope must be resolved before mapping

Products are not treated as a single universe.

Different business scopes must be separated before dictionary matching.

### 4. Dictionary-based matching

Catalog matching is performed through controlled dictionaries stored in MySQL.

### 5. Wansoft SOAP access is centralized

Wansoft SOAP client initialization should be centralized in:

```text
core/clients/wansoft_client.py
```

ETL scripts should not instantiate Zeep clients directly with a remote WSDL URL.

---

## High-Level Architecture

```text
Odoo (read-only)
    ↓
Extraction
    ↓
Scope classification / migration policy
    ↓
Dictionary lookup
    ↓
Scope-aware ETL
    ↓
Snapshot + Backlog in MySQL
```

---

## Repository Structure

```text
.
├── analysis/
│   ├── build_sales_product_mapping.py
│   ├── build_inventory_bridge_report.py
│   ├── build_inventory_not_found_priority_backlog.py
│   ├── build_inventory_not_found_p1_bridge.py
│   ├── build_inventory_not_found_p2_bridge.py
│   ├── build_inventory_not_found_residual_bridge.py
│   ├── inventory_not_found_analyzer.py
│   ├── odoo_inventory_scope_classifier.py
│   ├── review_scope_refiner.py
│   ├── review_scope_refiner_v2.py
│   ├── save_inventory_bridge_report.py
│   ├── save_inventory_not_found_p1_bridge.py
│   ├── save_inventory_not_found_p2_bridge.py
│   ├── save_inventory_not_found_priority_backlog.py
│   ├── save_inventory_not_found_residual_bridge.py
│   ├── save_odoo_inventory_scope_classification.py
│   ├── save_refined_odoo_inventory_scope.py
│   ├── save_review_scope_refiner.py
│   ├── save_review_scope_refiner_v2.py
│   ├── save_wansoft_inventory_operational_lifecycle.py
│   ├── promote_inventory_bridge_to_dictionary.py
│   ├── promote_inventory_not_found_p1_to_dictionary.py
│   ├── promote_inventory_not_found_p2_to_dictionary.py
│   └── promote_inventory_not_found_residual_to_dictionary.py
│
├── core/
│   ├── clients/
│   │   ├── __init__.py
│   │   └── wansoft_client.py
│   ├── config/
│   │   ├── .env.example
│   │   ├── env_loader.py
│   │   └── inventory_env.py
│   ├── database/
│   │   ├── mysql.py
│   │   └── odoo.py
│
├── docs/
│   ├── inventory-domain-closeout.md
│   ├── inventory-runbook.md
│   ├── purchases-company-migration-policy.md
│   └── wansoft-local-wsdl.md
│
├── extract/
│   ├── inventory/
│   │   ├── odoo_inventory.py
│   │   └── odoo_inventory_etl.py
│   ├── products/
│   │   └── odoo_products.py
│   ├── purchases/
│   │   ├── odoo_purchase_orders.py
│   │   ├── odoo_purchase_order_lines.py
│   │   ├── odoo_purchase_receipts.py
│   │   └── odoo_purchase_etl.py
│   └── utils/
│       ├── inventory_dictionary_lookup.py
│       ├── inventory_dictionary_wrapper.py
│       └── inventory_scope_lookup.py
│
├── resources/
│   └── wsdl/
│       └── wansoft.wsdl
│
├── scripts/
│   ├── test_inventory_dictionary_lookup.py
│   ├── test_apply_inventory_dictionary.py
│   ├── test_inventory_not_found_analyzer.py
│   ├── test_inventory_not_found_priority_backlog.py
│   ├── test_inventory_not_found_p1_bridge.py
│   ├── test_inventory_not_found_p2_bridge.py
│   ├── test_inventory_not_found_residual_bridge.py
│   ├── test_odoo_inventory_etl.py
│   ├── test_odoo_inventory_scope_classification.py
│   ├── test_promote_inventory_bridge_to_dictionary.py
│   ├── test_promote_inventory_not_found_p1_to_dictionary.py
│   ├── test_promote_inventory_not_found_p2_to_dictionary.py
│   ├── test_promote_inventory_not_found_residual_to_dictionary.py
│   ├── test_refine_odoo_inventory_scope.py
│   ├── test_review_scope_refiner_v2.py
│   ├── test_extract_odoo_purchases.py
│   ├── test_odoo_purchase_etl.py
│   ├── test_extract_odoo_purchase_receipts.py
│   └── test_wansoft_wsdl_client.py
│
├── sql/
│   ├── seeds/
│   │   └── seed_odoo_company_migration_policy.sql
│   └── maintenance/
│       └── update_odoo_company_migration_policy.sql
│
├── wansoft.sql
└── README.md
```

---

# Environment Configuration

Configuration is driven through `.env`.

## Inventory ETL Example

```env
# =========================
# INVENTORY ETL
# =========================

INVENTORY_ETL_SALES_REFERENCE_SCOPE=restaurantes
INVENTORY_ETL_SALES_REFERENCE_SOURCE=sales_reference
INVENTORY_ETL_SCOPE_INCLUDE=shared_cross_company
INVENTORY_ETL_SCOPE_BACKLOG=bodegon,empanadas,bodegon_candidate,empanadas_candidate,review_scope,operational_non_inventory

# =========================
# INVENTORY NOT_FOUND ANALYZER
# =========================

INVENTORY_NOT_FOUND_BUCKET=not_found
INVENTORY_SCOPE_INCLUDE=shared_cross_company,review_scope
INVENTORY_SCOPE_EXCLUDE=bodegon,empanadas,restaurantes,operational_non_inventory
INVENTORY_NOT_FOUND_EXPORT=true
INVENTORY_NOT_FOUND_EXPORT_FILE=inventory_not_found_analysis.csv
```

## Purchases ETL Example

```env
# =========================
# PURCHASE ETL
# =========================

PURCHASE_ETL_MIN_ORDER_DATE=2026-06-01
PURCHASE_ETL_MIN_RECEIPT_DATE=2026-06-01
PURCHASE_ETL_APPLY_PRODUCT_MAPPING=true
PURCHASE_ETL_ALLOWED_MAPPING_STATUS=approved
```

## Wansoft SOAP / WSDL Example

```env
# =========================
# WANSOFT SOAP / WSDL
# =========================

WANSOFT_USE_LOCAL_WSDL=true
WANSOFT_WSDL_PATH=resources/wsdl/wansoft.wsdl
WANSOFT_SERVICE_URL=https://www.wansoft.net/wansoft.web/API/IntegrationService.asmx
```

---

# Sales Domain

## Current Role

The Sales domain is responsible for:

- homologating public-sale products between Odoo and Wansoft
- building a stable sales dictionary
- detecting replacements and catalog issues
- preparing the commercial product layer for analytical use

## Status

Sales baseline is already considered functionally established.

---

# Inventory Domain

## Goal

Enable a scope-aware, dictionary-governed inventory ETL from Odoo into MySQL without modifying Odoo.

## Core Rules

- Odoo stays read-only
- Inventory scope must be classified before mapping
- Public-sale products are excluded from raw inventory matching
- Matching is resolved in MySQL dictionaries

## Scope Model

### Final refined buckets

```text
restaurantes
bodegon
empanadas
shared_cross_company
review_scope
operational_non_inventory
```

## Current Inclusion Logic

The inventory ETL currently applies dictionary lookup only to:

```text
shared_cross_company
```

The ETL sends these buckets straight to backlog:

```text
scope_restaurantes_sales_reference
scope_bodegon
scope_bodegon_candidate
scope_empanadas
scope_review_scope
scope_operational_non_inventory
```

## Main Inventory Tables

```text
inventory_mapping_dictionary
inventory_product_lifecycle
odoo_inventory_scope_classification
odoo_inventory_snapshot
odoo_inventory_backlog
```

## Dictionary Sources Currently Used

```text
bridge_report
p1_bridge
p2_bridge
residual_bridge
```

## Validated Promotion Pattern

The following pattern is already validated:

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

- technically stable
- functionally advanced
- good enough to support the next domain

---

# Inventory ETL Execution Flow

```text
1. Extract Odoo inventory
2. Consolidate snapshot by product + location
3. Merge scope classification
4. Split scope universes
5. Apply inventory dictionary only to allowed scope
6. Save:
   - odoo_inventory_snapshot
   - odoo_inventory_backlog
7. Export diagnostics if required
```

---

# Inventory Backlog Types

## Scope Backlog

Products excluded from the main ETL because of business scope:

```text
Bodegón
Empanadas
restaurant sales-reference products
review scope
operational non-inventory
```

## Functional Backlog

Products eligible for dictionary lookup but still unresolved:

```text
not_found
pending_review
historical_only
```

---

# Purchases Domain

## Goal

Build a purchases domain that can analyze Odoo purchase activity while remaining aligned with Wansoft product governance and the inventory dictionary.

## Current Status

The purchases domain is in progress.

Currently implemented:

- purchase order extraction
- purchase order line extraction
- purchase ETL to MySQL
- line type classification
- product mapping against `inventory_mapping_dictionary`
- company migration policy table
- company migration policy seed and documentation

## Main Purchases Tables

```text
odoo_purchase_order_snapshot
odoo_purchase_order_line_snapshot
odoo_company_migration_policy
```

## Purchase Line Classification

Purchase lines are classified into:

```text
product_line
empty_line
review_line
```

### Meaning

```text
product_line = real product line
empty_line = administrative / empty line with no product, no quantity and no amount
review_line = unusual line requiring review
```

## Product Mapping in Purchases

Purchase lines are enriched using:

```text
purchase.order.line.product_id
→ inventory_mapping_dictionary.odoo_product_id
→ wansoft_code
→ wansoft_product_name
→ wansoft_department
```

This allows Odoo purchases to remain aligned with Wansoft product codes during the transition.

### Product Mapping Policy

The Purchases domain does not create automatic product aliases. A product is mapped only when it has an approved reference in `inventory_mapping_dictionary`. Similar names without an approved reference remain as new products in the purchase inventory mapping backlog.

## Current Purchases ETL Behaviour

The ETL currently:

```text
1. Extracts purchase.order
2. Extracts purchase.order.line
3. Applies migration cutoff
4. Classifies purchase lines
5. Applies product mapping using inventory_mapping_dictionary
6. Saves:
   - odoo_purchase_order_snapshot
   - odoo_purchase_order_line_snapshot
```

## Company Migration Policy

The company migration policy controls which date each company starts contributing Odoo purchase data to the pipeline.

This is required because there are two company scenarios:

```text
1. Companies migrated from Wansoft to Odoo
2. New branches that start directly in Odoo
```

### Migrated companies

```text
company_migration_type = migrated_from_wansoft
history_source = wansoft
include_odoo_history = 0
```

For these companies:

```text
Wansoft remains the historical source.
Odoo data starts only at operational_start_date.
```

### New Odoo branches

```text
company_migration_type = new_odoo_branch
history_source = odoo
include_odoo_history = 1
```

For these companies:

```text
Odoo is the historical source from operational_start_date.
```

## Company Migration Policy Files

```text
wansoft.sql
sql/seeds/seed_odoo_company_migration_policy.sql
sql/maintenance/update_odoo_company_migration_policy.sql
docs/purchases-company-migration-policy.md
```

## Current Next Step in Purchases

The next implementation step is:

```text
Integrate odoo_company_migration_policy directly into the Purchases ETL.
```

Expected result:

```text
Purchases ETL no longer relies only on PURCHASE_ETL_MIN_ORDER_DATE.
Each company uses its configured operational_start_date.
```

## Company Source Governance

`COMPANY_SOURCE` in `companies.py` is the authoritative source selector for operational domains.

Rules:

- Sales always use Wansoft.
- Purchases use `COMPANY_SOURCE`.
- Inventory uses `COMPANY_SOURCE`.
- `odoo_company_migration_policy.operational_start_date` only applies when `COMPANY_SOURCE` marks the company as `odoo`.
- `.env` dates are fallback values, not the main business rule.

This prevents Odoo parallel-operation data from replacing Wansoft before a company is formally configured as Odoo source.

### Internal Provider Companies

Some Odoo companies are used for intercompany/provider workflows but should not be treated as final operating branches in Grupo Fonda Argentina BI tables.

Current internal provider companies:

```text
EL BODEGON DE FITO
LAS EMPANADAS DE MARIA EVA

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

## WSDL Files

```text
core/clients/wansoft_client.py
scripts/test_wansoft_wsdl_client.py
resources/wsdl/wansoft.wsdl
docs/wansoft-local-wsdl.md
```

---

# SQL Folder

The `sql/` folder is located at the repository root.

```text
sql/
├── seeds/
│   └── seed_odoo_company_migration_policy.sql
└── maintenance/
    └── update_odoo_company_migration_policy.sql
```

## Purpose

### `sql/seeds/`

Contains initial controlled seed scripts.

### `sql/maintenance/`

Contains controlled SQL examples and update scripts.

These scripts are versioned because they represent configuration or operational governance, not runtime ETL logic.

---

# What Is Safe to Automate

## Safe to Automate

```text
Odoo read-only extraction
snapshot preparation
scope merge
dictionary lookup
ETL execution
backlog generation
diagnostics export
Wansoft SOAP client initialization via local WSDL
```

## Keep Controlled at First

```text
dictionary promotions
historical-only decisions
scope rule changes
heuristic changes
catalog-governance decisions
company migration policy changes
```

---

# Documentation

Detailed documentation is available in:

```text
docs/inventory-domain-closeout.md
docs/inventory-runbook.md
docs/purchases-company-migration-policy.md
docs/wansoft-local-wsdl.md
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
```

## General Execution Approach

Most workflows are currently executed through `scripts/test_*.py` files to validate each layer before production-style orchestration.

---

# Recommended Workflow For Future Development

## 1. Build Domain Baseline

```text
isolate source universe
understand fields
classify scope
define snapshot and backlog
```

## 2. Add Governance Layer

```text
dictionary
bridges
prioritization
controlled promotion
company policy
```

## 3. Validate Through ETL Reruns

```text
measure snapshot growth
measure backlog reduction
keep Odoo untouched
```

---

# Notes For Future Production Rollout

Before production automation, complete:

```text
runbook for automatic vs controlled jobs
dictionary governance process
ETL telemetry cleanup
company migration policy review
final residual backlog handling policy
Wansoft local WSDL validation
```

---

# Suggested Commit Patterns

## Inventory Documentation Only

```bash
git add .
git commit -m "docs(inventory): add inventory phase closeout and operational runbook"
git push
```

## Inventory Code + Docs Baseline Closeout

```bash
git add .
git commit -m "feat(inventory): finalize baseline and add GitHub documentation for scope-aware ETL and dictionary governance"
git push
```

## Purchases Company Migration Policy

```bash
git add .
git commit -m "feat(purchases): add per-company migration policy for Odoo-Wansoft transition"
git push
```

## Wansoft Local WSDL

```bash
git add .
git commit -m "fix(wansoft): use local WSDL for SOAP client initialization"
git push
```

---

# Current Next Step

After validating the Wansoft local WSDL client, continue with:

```text
Step 12.12 — Integrate company migration policy into Purchases ETL
```