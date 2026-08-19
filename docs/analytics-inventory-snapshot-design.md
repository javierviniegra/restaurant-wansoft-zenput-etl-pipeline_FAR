# analytics_inventory_snapshot Design and Closeout

## Purpose

This document defines and closes the first implementation of `analytics_inventory_snapshot`, the first analytical inventory fact table of the unified MySQL analytical layer.

The purpose of this table is to expose Odoo inventory snapshot data in a governed, validated and dimension-ready structure.

This table belongs to the MySQL analytical layer.

It does not define:

```text
Power BI
reports
dashboards
visuals
semantic models
DAX measures
presentation layers
```

Those layers belong to a separate project.

The core rule remains:

```text
Reporting does not resolve business rules.
All business rules must be governed in MySQL before reporting consumes the data.
```

---

## Current Context

Section 17 closed the first validated purchase analytical layer.

Implemented shared dimensions:

```text
dim_company_analytical
dim_time
dim_vendor
dim_product
```

Implemented purchase analytical objects:

```text
analytics_purchase_order_lines
analytics_purchase_orders
analytics_purchase_daily_company_product
```

Section 18 starts the analytical inventory layer.

First inventory analytical object:

```text
analytics_inventory_snapshot
```

Primary source table:

```text
odoo_inventory_snapshot
```

---

## Business and Operational Context

Inventory analytics must respect the operational and accounting protocol around Odoo inventory.

Relevant internal process points:

```text
Inventory and initial balances must be aligned in the same accounting period.
Inventory loads should be validated before final application.
Adjustments should be performed through the inventory module when they affect stock valuation.
Manual accounting-only adjustments can desynchronize inventory valuation and accounting.
Inventory movements and manual variations should remain traceable.
```

This matters because inventory is not only a stock quantity domain. It also affects stock valuation, auxiliary accounts, period close processes, and the synchronization between operational inventory and accounting.

The analytical table is therefore designed to preserve all source evidence first, apply governance flags second, and avoid forcing business mappings that are not yet governed.

---

## Design Goal

`analytics_inventory_snapshot` answers questions such as:

```text
What products exist in the current Odoo inventory snapshot?
What stock quantity does each product have by Odoo location?
What Wansoft product code is mapped to the Odoo product?
Which products are approved for ETL?
Which products are pending review?
Which products are unmapped or not usable for ETL?
Which inventory rows can be included in business-facing analytical outputs?
Which inventory rows require review before business consumption?
Which rows are in virtual, partner or internal inventory locations?
Which rows cannot yet be mapped to an analytical company?
```

The first version focuses on source-level preservation and product governance.

It does not yet force company or branch mapping.

---

## Target Table Name

```text
analytics_inventory_snapshot
```

---

## Table Classification

```text
Layer: analytical fact
Object type: analytics_*
Domain: inventory
Grain: source inventory snapshot row
BI design: no
Source of business rules: MySQL/config/docs
```

---

## Grain

Implemented grain:

```text
1 row = 1 Odoo inventory snapshot row
```

Source identity:

```text
odoo_inventory_snapshot.id
```

Target identity field:

```text
source_inventory_snapshot_id
```

This grain preserves every source row without premature aggregation.

---

## Source Table

Primary source:

```text
odoo_inventory_snapshot
```

Implemented rule:

```text
Use all rows from odoo_inventory_snapshot.
Do not drop rows because product mapping is missing.
Do not drop rows because company mapping is unavailable.
Flag rows instead of deleting them.
```

---

## Implemented Dimension Relationships

### Time

Implemented join basis:

```text
etl_loaded_at
```

Derived fields:

```text
snapshot_date = DATE(etl_loaded_at)
snapshot_date_key = YYYYMMDD
```

Relationship:

```text
analytics_inventory_snapshot.snapshot_date_key
    -> dim_time.date_key
```

Validation result:

```text
date_fk_valid: PASS
orphan_date_rows: 0
```

---

### Product

Implemented product lookup basis:

```text
odoo_product_id
wansoft_code
```

Forbidden joins preserved:

```text
odoo_product_name -> normalized_product_name
wansoft_product_name -> normalized_product_name
fuzzy matching
similarity matching
```

Current rule remains:

```text
Explicit reference beats name similarity.
```

Validation result:

```text
product_fk_valid: PASS
orphan_product_rows: 0
```

Important interpretation:

```text
product_fk_valid means every populated product_analytical_key points to dim_product.
It does not mean every source inventory row has a populated product_analytical_key.
```

Current product governance diagnostics:

```text
orphan_product_rows: 50
product_review_required_rows: 203
```

---

### Company

Company mapping was intentionally not forced.

Implemented rule:

```text
company_source_key = null
company_mapping_status = pending_location_mapping
```

Validation result:

```text
company_mapping_not_forced: PASS
populated_company_rows: 0
```

Reason:

```text
odoo_inventory_snapshot does not currently expose a governed company_source_key.
location_name must not be used as company identity until an explicit governed mapping exists.
```

---

## Implemented Location Handling

Current source fields preserved:

```text
source_location_id
location_name
```

Implemented helper classification:

```text
Virtual Locations/... -> virtual
Partners/... -> partner
otherwise -> internal_or_unknown
```

Implemented helper fields:

```text
normalized_location_name
location_usage_type
is_virtual_location
is_partner_location
is_internal_location
location_mapping_status
```

Important:

```text
location_usage_type is a helper classification.
It is not a final branch/company mapping.
```

Current location classification distribution:

```text
internal_or_unknown: 505
partner: 227
virtual: 928
```

---

## Implemented Schema Summary

Implemented target table:

```text
analytics_inventory_snapshot
```

Main field groups:

```text
analytical identity fields
source inventory fields
location classification fields
company placeholder fields
time fields
product governance fields
mapping and ETL fields
quantity fields
business inclusion fields
audit fields
```

Key fields:

```text
inventory_snapshot_analytical_key
source_inventory_snapshot_id
odoo_product_id
odoo_product_name
product_code
source_location_id
location_name
normalized_location_name
location_usage_type
is_virtual_location
is_partner_location
is_internal_location
location_mapping_status
company_source_key
company_mapping_status
snapshot_date
snapshot_date_key
etl_loaded_at
product_analytical_key
wansoft_code
wansoft_product_name
wansoft_department
product_identity_status
dim_product_mapping_status
is_product_mapped
is_product_review_required
include_product_in_business_views
stock_qty
mapping_found
lookup_method
mapping_status
usable_for_etl
lifecycle_candidate
similarity_score
mapping_notes
include_in_business_views
exclude_reason
inventory_review_status
created_at
updated_at
```

Unique key:

```text
source_inventory_snapshot_id
```

---

## Build Script

Implemented script:

```text
scripts/build_analytics_inventory_snapshot.py
```

Current behavior:

```text
creates analytics_inventory_snapshot
reads all rows from odoo_inventory_snapshot
preserves source_inventory_snapshot_id
joins dim_time using DATE(etl_loaded_at)
joins dim_product using odoo_product_id or wansoft_code
never joins products by name
classifies location_name into virtual, partner or internal_or_unknown
does not force company_source_key
sets company_mapping_status = pending_location_mapping
sets include_in_business_views
sets exclude_reason
sets inventory_review_status
prints build summary
```

---

## Validation Script

Implemented script:

```text
scripts/validate_analytics_inventory_snapshot.py
```

Current validations:

```text
analytics_inventory_snapshot_exists
row_count_matches_source
source_inventory_snapshot_id_unique
stock_qty_reconciles
date_fk_valid
product_fk_valid
excluded_rows_have_reason
business_inclusion_distribution_available
inventory_review_status_distribution_available
location_classification_distribution_available
company_mapping_not_forced
```

---

## Build Result

Build command:

```bash
python -m scripts.build_analytics_inventory_snapshot
```

Latest build result:

```text
ANALYTICS INVENTORY SNAPSHOT BUILD SUMMARY

table: analytics_inventory_snapshot
total_rows_prepared: 1660
include_in_business_views: 1407
excluded_from_business_views: 253
orphan_product_rows: 50
invalid_snapshot_date_rows: 0
not_usable_for_etl_rows: 0
mapping_not_approved_rows: 0
total_stock_qty: -66689.8400

BUILD RESULT: COMPLETED
```

---

## Validation Result

Validation command:

```bash
python -m scripts.validate_analytics_inventory_snapshot
```

Latest validation result:

```text
total_validations: 11
passed: 11
failed: 0

VALIDATION RESULT: PASSED
```

Validated checks:

```text
analytics_inventory_snapshot_exists: PASS
row_count_matches_source: PASS
source_inventory_snapshot_id_unique: PASS
stock_qty_reconciles: PASS
date_fk_valid: PASS
product_fk_valid: PASS
excluded_rows_have_reason: PASS
business_inclusion_distribution_available: PASS
inventory_review_status_distribution_available: PASS
location_classification_distribution_available: PASS
company_mapping_not_forced: PASS
```

---

## Reconciliation Results

### Row Count Reconciliation

Validated result:

```text
source_rows: 1660
analytics_rows: 1660
```

Validation status:

```text
row_count_matches_source: PASS
```

Interpretation:

```text
Every source row from odoo_inventory_snapshot is preserved in analytics_inventory_snapshot.
```

---

### Source Identity Uniqueness

Validation status:

```text
source_inventory_snapshot_id_unique: PASS
```

Interpretation:

```text
The implemented grain is unique at source_inventory_snapshot_id.
```

---

### Stock Quantity Reconciliation

Validated result:

```text
source_stock_qty: -66689.84
analytics_stock_qty: -66689.84
difference: 0.00
tolerance: 6.668984
```

Validation status:

```text
stock_qty_reconciles: PASS
```

Interpretation:

```text
analytics_inventory_snapshot preserves the same stock_qty total as odoo_inventory_snapshot.
```

The negative total is not treated as a build failure because the analytical layer is reconciling to source. Further interpretation of negative stock belongs to a later inventory analysis or governance step.

---

## Business Inclusion Distribution

Validated distribution:

```text
include_in_business_views = 0: 253 rows
include_in_business_views = 1: 1407 rows
```

Validation status:

```text
business_inclusion_distribution_available: PASS
```

Interpretation:

```text
1407 rows are currently ready for default business-facing analytical usage.
253 rows are preserved but excluded from default business-facing views.
```

---

## Inventory Review Status Distribution

Validated distribution:

```text
ok: 1407 rows
orphan_product: 50 rows
product_review_required: 203 rows
```

Validation status:

```text
inventory_review_status_distribution_available: PASS
```

Interpretation:

```text
1407 inventory rows are clean under current first-version rules.
50 rows do not resolve to an analytical product.
203 rows resolve to products that require review.
```

---

## Location Classification Distribution

Validated distribution:

```text
internal_or_unknown: 505 rows
partner: 227 rows
virtual: 928 rows
```

Validation status:

```text
location_classification_distribution_available: PASS
```

Interpretation:

```text
The first-version helper classification is working.
The classification does not establish final company or branch identity.
```

---

## Business Inclusion Logic

The implemented first-version business inclusion rule excludes rows when any of the following issues are present:

```text
invalid_snapshot_date
orphan_product
product_review_required
product_excluded
not_usable_for_etl
mapping_not_approved
```

Current observed exclusions:

```text
orphan_product: 50 rows
product_review_required: 203 rows
```

Current observed clean rows:

```text
ok: 1407 rows
```

---

## Current Open Items

### Company Mapping

Current status:

```text
company_source_key not populated
company_mapping_status = pending_location_mapping
```

Future requirement:

```text
Design dim_inventory_location or dim_warehouse.
Create explicit mapping from Odoo warehouse/location to company_source_key.
Do not infer company from free-text location_name.
```

---

### Product Governance

Current diagnostics:

```text
orphan_product_rows: 50
product_review_required_rows: 203
```

Future requirement:

```text
Review product mapping gaps.
Resolve or document inventory-specific product backlog.
Keep excluded rows visible until governance is complete.
```

---

### Negative Stock Quantity Interpretation

Current total:

```text
total_stock_qty: -66689.8400
```

Current status:

```text
reconciled to source
not treated as build failure
```

Future requirement:

```text
Analyze negative stock by location_usage_type, product and source_location_id.
Determine whether negative stock reflects expected virtual flows, partner locations, timing, or operational data quality issues.
```

---

### Inventory Valuation

Current table includes:

```text
stock_qty
```

Current table does not include:

```text
stock_value
unit_cost
inventory_value
valuation_layer_amount
```

Future requirement:

```text
Only add valuation fields once their source and reconciliation rules are explicitly confirmed.
```

---

## Validation Query Examples

### Row Count Reconciliation

```sql
SELECT
    (SELECT COUNT(1) FROM odoo_inventory_snapshot) AS source_rows,
    (SELECT COUNT(1) FROM analytics_inventory_snapshot) AS analytics_rows;
```

Expected current result:

```text
source_rows = 1660
analytics_rows = 1660
```

---

### Stock Quantity Reconciliation

```sql
SELECT
    (SELECT COALESCE(SUM(stock_qty), 0) FROM odoo_inventory_snapshot) AS source_stock_qty,
    (SELECT COALESCE(SUM(stock_qty), 0) FROM analytics_inventory_snapshot) AS analytics_stock_qty;
```

Expected current result:

```text
source_stock_qty = -66689.84
analytics_stock_qty = -66689.84
```

---

### Business Inclusion Distribution

```sql
SELECT
    include_in_business_views,
    COUNT(1) AS total_rows
FROM analytics_inventory_snapshot
GROUP BY include_in_business_views
ORDER BY include_in_business_views;
```

Expected current result:

```text
include_in_business_views = 0: 253
include_in_business_views = 1: 1407
```

---

### Inventory Review Status Distribution

```sql
SELECT
    inventory_review_status,
    COUNT(1) AS total_rows
FROM analytics_inventory_snapshot
GROUP BY inventory_review_status
ORDER BY inventory_review_status;
```

Expected current result:

```text
ok: 1407
orphan_product: 50
product_review_required: 203
```

---

### Location Usage Distribution

```sql
SELECT
    location_usage_type,
    COUNT(1) AS total_rows
FROM analytics_inventory_snapshot
GROUP BY location_usage_type
ORDER BY location_usage_type;
```

Expected current result:

```text
internal_or_unknown: 505
partner: 227
virtual: 928
```

---

### Negative Stock Review Query

```sql
SELECT
    location_usage_type,
    source_location_id,
    location_name,
    COUNT(1) AS total_rows,
    COALESCE(SUM(stock_qty), 0) AS total_stock_qty
FROM analytics_inventory_snapshot
GROUP BY
    location_usage_type,
    source_location_id,
    location_name
ORDER BY total_stock_qty ASC
LIMIT 100;
```

Purpose:

```text
Review the most negative stock quantities by source location classification.
```

---

## Step 18.1 Closeout

Step 18.1 is complete because the design document defined:

```text
purpose of analytics_inventory_snapshot
grain
source table
schema draft
dimension relationships
product join rule
location handling rule
company mapping limitation
business inclusion rule
validation requirements
known limitations
```

Current status:

```text
complete
```

---

## Step 18.2 Closeout

Step 18.2 is complete because:

```text
scripts/build_analytics_inventory_snapshot.py created
scripts/validate_analytics_inventory_snapshot.py created
both scripts compile
analytics_inventory_snapshot table created
build completed successfully
validation passed
1660 source rows preserved
stock_qty reconciled
product FK valid when populated
date FK valid when populated
company_source_key not forced
excluded rows have reason
location classification distribution available
```

Current status:

```text
complete
```

---

## Step 18.3 Closeout

This documentation step is complete when:

```text
actual build result documented
actual validation result documented
row count reconciliation documented
stock_qty reconciliation documented
business inclusion distribution documented
inventory review status distribution documented
location classification distribution documented
company mapping limitation documented
open inventory governance items documented
```

Current status:

```text
complete
```

---

## Recommended Next Step

Recommended next step:

```text
Paso 18.4 - Analizar negative stock y location_usage_type en analytics_inventory_snapshot
```

Reason:

```text
analytics_inventory_snapshot is now reconciled to source.
The next meaningful inventory analytical step is to understand why total_stock_qty is negative and how it is distributed across virtual, partner and internal_or_unknown locations before designing company-level inventory aggregations.
```
