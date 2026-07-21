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
validation strategy
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

The goal is to create a reliable analytical environment where business data can be extracted, governed, mapped, validated, and consumed without modifying Odoo directly.

The project follows these principles:

```text
Odoo is read-only.
Wansoft remains the source of truth for sales.
MySQL is the governance and analytical layer.
Catalog governance is handled outside Odoo.
Source-system transitions are controlled by company-level rules.
Canonical tables preserve source traceability.
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
Documentation package is complete.
Production orchestration is pending.
Power BI semantic modelling is pending.
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

The initial production orchestration strategy is documented in:

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
2. docs/purchases-company-migration-policy.md
3. docs/purchases-product-mapping-policy.md
4. docs/purchases-canonical-layer.md
5. docs/inventory-domain-closeout.md
6. docs/inventory-runbook.md
7. docs/wansoft-local-wsdl.md
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

## Odoo Purchases Canonical Load

Entrypoint:

```bash
python -m scripts.test_canonical_purchase_odoo_etl
```

Function:

```python
run_canonical_purchase_odoo_etl()
```

Current validated Odoo canonical counts:

```text
orders_inserted: 282
lines_inserted: 1381
receipts_inserted: 268
receipt_moves_inserted: 1184
```

Current Odoo final company:

```text
company_source_key = Antenas
final_purchase_source_status = final_odoo_enabled
```

---

## Wansoft Purchases Canonical Load

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
orders_inserted: 145047
lines_inserted: 745344
receipts_inserted: 145047
receipt_moves_inserted: 745344
```

Wansoft status summary:

```text
final_wansoft_enabled        693059
wansoft_history_before_odoo   52285
```

---

## Antenas Source Split

Validated behaviour:

```text
Wansoft Antenas:
    historical purchases before 2026-06-01

Odoo Antenas:
    final purchases from 2026-06-01 onward
```

Validated ranges:

```text
Wansoft Antenas max_order_date: 2026-05-31 22:51:54
Odoo Antenas min_order_date: 2026-06-01 16:10:54
```

This confirms that Wansoft does not invade the Odoo period for Antenas.

---

## Wansoft Technical Key Strategy

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

Detailed documentation:

```text
docs/purchases-canonical-layer.md
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

# Validation Queries

The complete validation queries for Purchases canonical layer are documented in:

```text
docs/purchases-canonical-layer.md
```

Core validations include:

```text
source-system coexistence
Antenas source split
Wansoft final-source companies
internal providers as vendors
internal providers not as final companies
Wansoft Antenas cutoff validation
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
```

---

# Current Next Step

The documentation package is now ready for final commit.

Recommended immediate action:

```text
Run git status.
Confirm README.md and docs/ include the final documentation set.
Commit the documentation package.
```

After the documentation package is committed, the next technical options are:

```text
1. production orchestration implementation
2. purchases refresh orchestration
3. ETL run logging
4. Power BI integration layer
5. inventory source governance alignment
```

Recommended technical priority:

```text
production orchestration first
Power BI modelling second
```

Reason:

```text
Power BI should consume stable, repeatable, validated outputs.
```

---

# Current Next Step

Recommended next step:

```text
Review repository documentation consistency and then decide whether to continue with:
1. production orchestration planning
2. purchases runbook
3. inventory source governance alignment
4. Power BI integration layer
```