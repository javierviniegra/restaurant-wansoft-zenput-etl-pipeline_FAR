# Wansoft + Odoo Data Warehouse & ETL Pipeline

## Overview

This repository contains the Python ETL and catalog-governance layer used to integrate **Odoo**, **Wansoft**, and other operational sources into a centralized **MySQL-based analytical environment**.

The project is designed around a core principle:

- **Odoo is treated as a read-only source**
- **MySQL stores mapping dictionaries, scope classification, lifecycle logic, snapshots, and backlogs**
- **Catalog governance is resolved outside Odoo**

The goal is to enable operational, analytical, and accounting-friendly data flows without modifying Odoo as part of the ETL process.

---

## Current Domains

### Implemented / Advanced
- **Sales**
- **Inventory**

### Next recommended domain
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

### 3. Scope must be resolved before mapping
Products are not treated as a single universe.  
Different business scopes must be separated before dictionary matching.

### 4. Dictionary-based matching
Catalog matching is performed through controlled dictionaries stored in MySQL.

---

## High-Level Architecture

```text
Odoo (read-only)
    ↓
Extraction
    ↓
Scope classification
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
│   └── inventory-runbook.md
│
├── extract/
│   ├── inventory/
│   │   ├── odoo_inventory.py
│   │   └── odoo_inventory_etl.py
│   ├── products/
│   │   └── odoo_products.py
│   └── utils/
│       ├── inventory_dictionary_lookup.py
│       ├── inventory_dictionary_wrapper.py
│       └── inventory_scope_lookup.py
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
│   └── test_review_scope_refiner_v2.py
│
└── wansoft.sql
```

---

# Environment Configuration

Configuration is driven through `.env`.

## Example

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

---

# Sales Domain

## Current role
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

## Core rules
- Odoo stays read-only
- Inventory scope must be classified before mapping
- Public-sale products are excluded from raw inventory matching
- Matching is resolved in MySQL dictionaries

## Scope model

### Final refined buckets
- `restaurantes`
- `bodegon`
- `empanadas`
- `shared_cross_company`
- `review_scope`
- `operational_non_inventory`

## Current inclusion logic
The inventory ETL currently applies dictionary lookup only to:

- `shared_cross_company`

The ETL sends these buckets straight to backlog:

- `scope_restaurantes_sales_reference`
- `scope_bodegon`
- `scope_bodegon_candidate`
- `scope_empanadas`
- `scope_review_scope`
- `scope_operational_non_inventory`

## Main inventory tables
- `inventory_mapping_dictionary`
- `inventory_product_lifecycle`
- `odoo_inventory_scope_classification`
- `odoo_inventory_snapshot`
- `odoo_inventory_backlog`

## Dictionary sources currently used
- `bridge_report`
- `p1_bridge`
- `p2_bridge`
- `residual_bridge`

## Validated promotion pattern
The following pattern is already validated:

```text
not_found backlog
→ prioritize
→ build bridge against lifecycle
→ promote approved candidates to dictionary
→ rerun ETL
→ measure improvement
```

## Current inventory baseline state
At current closeout state:

- snapshot rows: `1660`
- residual functional `not_found`: `98 unique products`
- residual functional `pending_review`: `5 unique products`

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

## Scope backlog
Products excluded from the main ETL because of business scope:
- Bodegón
- Empanadas
- restaurant sales-reference products
- review scope
- operational non-inventory

## Functional backlog
Products eligible for dictionary lookup but still unresolved:
- `not_found`
- `pending_review`
- `historical_only`

---

# What is safe to automate

## Safe to automate
- Odoo read-only extraction
- snapshot preparation
- scope merge
- dictionary lookup
- ETL execution
- backlog generation
- diagnostics export

## Keep controlled at first
- dictionary promotions
- historical-only decisions
- scope rule changes
- heuristic changes
- catalog-governance decisions

---

# Documentation

Detailed inventory documentation is available in:

- `docs/inventory-domain-closeout.md`
- `docs/inventory-runbook.md`

---

# Current operational recommendation

## Recommended sequence
1. keep inventory baseline as reference
2. document the process
3. move to the next domain

---

# Next Domain

## Purchases

The next recommended domain is **Purchases**, because it is the natural upstream complement to the work already completed in Inventory.

Expected initial focus:
- purchase orders
- purchase lines
- receipts / receptions
- supplier linkage
- accountable inventory entry flow
- purchase status visibility

---

# Setup Notes

## Requirements
- Python environment with required dependencies
- MySQL access
- Odoo API credentials
- `.env` configured

## General execution approach
Most workflows are currently executed through `scripts/test_*.py` files to validate each layer before production-style orchestration.

---

# Recommended workflow for future development

## 1. Build domain baseline
- isolate source universe
- understand fields
- classify scope
- define snapshot and backlog

## 2. Add governance layer
- dictionary
- bridges
- prioritization
- controlled promotion

## 3. Validate through ETL reruns
- measure snapshot growth
- measure backlog reduction
- keep Odoo untouched

---

# Notes for future production rollout

Before production automation, complete:
- runbook for automatic vs controlled jobs
- dictionary governance process
- ETL telemetry cleanup
- final residual backlog handling policy

---