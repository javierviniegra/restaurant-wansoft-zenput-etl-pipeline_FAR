# analytics_inventory_current_product_location Closeout

## Purpose

This document closes the real implementation of `analytics_inventory_current_product_location`.

The object was implemented as the first current physical inventory aggregate by product and Odoo source location.

It is built from:

```text
vw_inventory_physical_snapshot
```

It is not built directly from:

```text
analytics_inventory_snapshot
```

Reason:

```text
analytics_inventory_snapshot remains the complete inventory evidence table.
vw_inventory_physical_snapshot is the validated physical inventory view.
```

---

## Scope

This closeout covers:

```text
scripts/build_analytics_inventory_current_product_location.py
scripts/validate_analytics_inventory_current_product_location.py
analytics_inventory_current_product_location
vw_inventory_physical_snapshot
```

It documents:

```text
compilation result
build result
validation result
row reconciliation
stock reconciliation
grain validation
physical policy validation
dimensional validation
business inclusion status
known warnings
final step status
recommended next step
```

---

## Source Object

Source view:

```text
vw_inventory_physical_snapshot
```

The source view was previously validated as the conservative physical inventory layer.

Current source view policy:

```text
include_in_business_views = TRUE
AND location_usage_type = 'internal_or_unknown'
```

This means the aggregate intentionally excludes:

```text
partner locations
virtual locations
non-business-ready inventory rows
```

The diagnostic evidence remains available in:

```text
analytics_inventory_snapshot
vw_inventory_non_physical_snapshot
```

---

## Target Object

Target table:

```text
analytics_inventory_current_product_location
```

Object type:

```text
analytical aggregate
```

Domain:

```text
inventory
```

Current implementation level:

```text
current physical inventory by product and source location
```

---

## Grain

Implemented grain:

```text
1 row = 1 current physical product per Odoo source location per snapshot date
```

Grain fields:

```text
snapshot_date_key
product_analytical_key
source_location_id
```

Unique-grain validation passed.

---

## Current Snapshot Rule

Implemented current snapshot rule:

```text
current_snapshot_loaded_at = MAX(etl_loaded_at) from vw_inventory_physical_snapshot
```

Actual current snapshot loaded timestamp:

```text
2026-06-16 14:05:14
```

Validation result:

```text
single_current_snapshot_loaded_at: PASS
distinct_loaded_at: 1
```

Interpretation:

```text
The aggregate is based on one physical inventory snapshot load.
```

---

## Compilation

Commands executed:

```powershell
python -m py_compile scripts\build_analytics_inventory_current_product_location.py
python -m py_compile scripts\validate_analytics_inventory_current_product_location.py
```

Result:

```text
Compilation successful.
No syntax errors reported.
```

---

## Build Execution

Command executed:

```powershell
python -m scripts.build_analytics_inventory_current_product_location
```

Build result:

```text
BUILD RESULT: COMPLETED
```

Actual build summary:

```text
table: analytics_inventory_current_product_location
total_rows_prepared: 422
include_in_business_views: 422
excluded_from_business_views: 0
total_source_row_count: 424
total_current_stock_qty: 20430.0700
total_positive_stock_qty: 20430.0700
total_negative_stock_qty: 0.0000
total_negative_row_count: 0
min_snapshot_loaded_at: 2026-06-16 14:05:14
max_snapshot_loaded_at: 2026-06-16 14:05:14
```

---

## Build Interpretation

The physical source view contributed:

```text
424 source rows
```

The aggregate produced:

```text
422 aggregate rows
```

This is expected because source rows are grouped by:

```text
snapshot_date_key
product_analytical_key
source_location_id
```

Therefore:

```text
424 physical source rows collapsed into 422 unique product-location snapshot combinations.
```

No stock quantity was lost because the aggregate reconciled to the source view.

---

## Validation Execution

Command executed:

```powershell
python -m scripts.validate_analytics_inventory_current_product_location
```

Validation result:

```text
VALIDATION RESULT: PASSED
```

Validation summary:

```text
total_validations: 14
passed: 14
failed: 0
```

---

## Validation Details

The following validations passed:

```text
source_physical_view_exists: PASS
analytics_inventory_current_product_location_exists: PASS
analytics_inventory_current_product_location_has_rows: PASS
current_product_location_grain_unique: PASS
single_current_snapshot_loaded_at: PASS
source_row_count_reconciles: PASS
current_stock_qty_reconciles: PASS
date_fk_valid: PASS
product_fk_valid: PASS
only_physical_location_type: PASS
negative_current_stock_excluded_from_business_views: PASS
excluded_rows_have_reason: PASS
business_inclusion_distribution_available: PASS
aggregate_review_status_distribution_available: PASS
```

---

## Source Row Reconciliation

Actual validation result:

```text
source_current_rows: 424
aggregate_source_rows: 424
```

Validation result:

```text
source_row_count_reconciles: PASS
```

Interpretation:

```text
Every physical source row from the current snapshot is represented in the aggregate through source_row_count.
```

---

## Stock Quantity Reconciliation

Actual validation result:

```text
source_current_stock_qty: 20430.07
aggregate_current_stock_qty: 20430.07
difference: 0.00
tolerance: 2.043007
```

Validation result:

```text
current_stock_qty_reconciles: PASS
```

Interpretation:

```text
The aggregate preserves the exact current physical stock quantity from vw_inventory_physical_snapshot.
```

---

## Dimensional Integrity

Date validation:

```text
date_fk_valid: PASS
orphan_date_rows: 0
```

Product validation:

```text
product_fk_valid: PASS
orphan_product_rows: 0
```

Interpretation:

```text
snapshot_date_key and product_analytical_key are dimensionally valid for populated values.
```

---

## Physical Location Policy Validation

Validation result:

```text
only_physical_location_type: PASS
bad_rows: 0
```

Interpretation:

```text
All aggregate rows come from location_usage_type = internal_or_unknown.
```

The aggregate does not include:

```text
partner
virtual
```

---

## Negative Stock Validation

Build summary:

```text
total_negative_stock_qty: 0.0000
total_negative_row_count: 0
```

Validation result:

```text
negative_current_stock_excluded_from_business_views: PASS
bad_rows: 0
```

Interpretation:

```text
No negative current stock exists in the aggregate.
No negative current stock row was included in business views.
```

---

## Business Inclusion Distribution

Actual result:

```text
include_in_business_views: 1
total_rows: 422
```

Validation result:

```text
business_inclusion_distribution_available: PASS
```

Interpretation:

```text
All 422 aggregate rows are business-ready under the current physical inventory policy.
```

---

## Aggregate Review Status Distribution

Actual result:

```text
aggregate_review_status: ok
total_rows: 422
```

Validation result:

```text
aggregate_review_status_distribution_available: PASS
```

Interpretation:

```text
All aggregate rows are clean under the current first-version aggregate rules.
```

---

## Warning Observed

The validation produced pandas DBAPI warnings similar to:

```text
UserWarning: pandas only supports SQLAlchemy connectable...
```

This warning does not block closure because:

```text
the validation completed
the validation result was PASSED
all 14 validations passed
```

Future cleanup recommendation:

```text
Migrate validators to SQLAlchemy connections to remove pandas DBAPI warnings.
```

This is a hygiene improvement, not a functional blocker.

---

## Current Object Status

Object:

```text
analytics_inventory_current_product_location
```

Status:

```text
implemented
built
validated
ready for downstream quantity-only inventory analysis
```

Current snapshot:

```text
2026-06-16 14:05:14
```

Current aggregate summary:

```text
source rows: 424
aggregate rows: 422
current_stock_qty: 20430.0700
negative_stock_qty: 0.0000
business rows: 422
excluded rows: 0
validation failures: 0
```

---

## What This Object Can Be Used For

This table can support current physical inventory analysis by:

```text
product
source Odoo location
snapshot date
product mapping status
quantity status
```

Useful questions:

```text
Which physical locations currently have stock for each product?
What is the current physical stock quantity by product and source location?
Which products have zero stock in a physical location?
Which current product-location combinations are ready for future company mapping?
```

---

## What This Object Must Not Be Used For Yet

This table must not yet be treated as:

```text
company inventory
branch inventory
inventory valuation
financial inventory value
cost of inventory
full Odoo inventory evidence
```

Reasons:

```text
company mapping is not yet governed
valuation fields are not included
partner and virtual diagnostic rows are intentionally excluded
```

---

## Known Limitations

### Company mapping remains pending

Current design intentionally does not infer company from:

```text
location_name
source_location_id
normalized_location_name
```

Future requirement:

```text
dim_inventory_location
```

---

### Valuation remains pending

Current object includes quantity only.

It does not include:

```text
unit_cost
stock_value
inventory_value
valuation_layer_amount
```

Future valuation work must define a reconciled valuation source before adding monetary measures.

---

### Product mapping sanity remains a separate governance item

The object inherits validated product keys, but it does not resolve deeper Odoo/Wansoft semantic mapping issues.

If product name mismatches appear in downstream diagnostics, those should be handled in a separate product governance step.

---

## Step 18.9 Closeout

Step 18.9 is complete because:

```text
build script compiled
validation script compiled
analytics_inventory_current_product_location created
build completed successfully
source row count reconciled
stock quantity reconciled
grain uniqueness validated
date FK validated
product FK validated
physical location policy validated
business inclusion distribution validated
aggregate review status distribution validated
14 validations passed
0 validations failed
```

Current status:

```text
complete
```

---

## Step 18.10 Closeout

Step 18.10 is complete when this closeout document records:

```text
actual build result
actual validation result
source row reconciliation
stock quantity reconciliation
grain validation
physical policy validation
business inclusion distribution
aggregate review status distribution
known warnings
known limitations
recommended next step
```

Current status:

```text
complete
```

---

## Recommended Next Step

Recommended next step:

```text
Paso 18.11 - Diseñar dim_inventory_location
```

Purpose:

```text
Create a governed inventory location dimension before building company-level or branch-level inventory aggregates.
```

This is recommended because current inventory aggregates are still based on Odoo source locations, not governed company or branch mappings.
