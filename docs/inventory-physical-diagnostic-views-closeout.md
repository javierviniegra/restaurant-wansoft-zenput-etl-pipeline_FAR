# Inventory Physical and Diagnostic Views Closeout

## Purpose

This document closes the implementation of the first physical and diagnostic inventory views derived from `analytics_inventory_snapshot`.

The objective of this step is to document the actual build and validation results for:

```text
vw_inventory_physical_snapshot
vw_inventory_non_physical_snapshot
```

These views implement the `location_usage_type` policy defined for inventory analytical consumption.

---

## Scope

This closeout covers:

```text
analytics_inventory_snapshot
vw_inventory_physical_snapshot
vw_inventory_non_physical_snapshot
scripts/build_inventory_snapshot_views.py
scripts/validate_inventory_snapshot_views.py
docs/inventory-location-usage-policy.md
```

This closeout does not change the grain of `analytics_inventory_snapshot`.

The grain remains:

```text
1 row = 1 row from odoo_inventory_snapshot
```

---

## Background

`analytics_inventory_snapshot` was intentionally designed as a complete evidence table.

It preserves:

```text
internal inventory rows
partner/vendor rows
virtual location rows
rows not yet ready for business use
product governance rows
inventory diagnostic rows
```

The negative stock analysis showed that the inventory base table should not be consumed directly as a physical inventory view.

The analysis showed:

```text
internal_or_unknown:
    negative_rows: 0
    total_stock_qty: 39277.6000

partner:
    negative_rows: 117
    total_stock_qty: -516507.4300

virtual:
    negative_rows: 321
    total_stock_qty: 410539.9900
```

Therefore, the project introduced two separate downstream views:

```text
1. A physical inventory view for conservative business-facing inventory analysis.
2. A diagnostic inventory view that preserves non-physical and non-ready rows for review.
```

---

## Operational Rationale

The policy is aligned with the operating principle that inventory and accounting must remain synchronized.

Internal Odoo inventory discussions have emphasized that inventory movements and accounting entries must be coordinated to avoid valuation and accounting desynchronization. They also emphasized that adjustments affecting inventory valuation should be performed through the inventory module instead of direct accounting-only adjustments.

The views created in this step support that principle by separating:

```text
physical inventory consumption
from
virtual, partner, adjustment, production and diagnostic evidence
```

This avoids treating Odoo operational locations as if they were physical branch stock.

---

## Implemented Objects

### Physical View

Implemented object:

```text
vw_inventory_physical_snapshot
```

Purpose:

```text
Provide the first conservative physical inventory snapshot for analytical consumption.
```

Policy implemented:

```sql
WHERE include_in_business_views = TRUE
  AND location_usage_type = 'internal_or_unknown'
```

This view excludes:

```text
partner locations
virtual locations
rows not ready for business-facing consumption
```

---

### Non-Physical Diagnostic View

Implemented object:

```text
vw_inventory_non_physical_snapshot
```

Purpose:

```text
Preserve all non-physical and non-ready rows for diagnostic, reconciliation and governance analysis.
```

Policy implemented:

```sql
WHERE include_in_business_views = FALSE
   OR location_usage_type <> 'internal_or_unknown'
```

This view includes:

```text
partner locations
virtual locations
internal_or_unknown rows that are not business-ready
```

---

## Implementation Scripts

Build script:

```text
scripts/build_inventory_snapshot_views.py
```

Validation script:

```text
scripts/validate_inventory_snapshot_views.py
```

Both scripts compiled without errors before execution.

Compilation commands executed:

```powershell
python -m py_compile scripts\build_inventory_snapshot_views.py
python -m py_compile scripts\validate_inventory_snapshot_views.py
```

Result:

```text
Compilation successful.
No syntax errors reported.
```

---

## Build Execution

Build command executed:

```powershell
python -m scripts.build_inventory_snapshot_views
```

Build result:

```text
BUILD RESULT: COMPLETED
```

---

## Physical View Build Result

Actual result for:

```text
vw_inventory_physical_snapshot
```

```text
total_rows: 424
negative_rows: 0
zero_rows: 1
positive_rows: 423
total_stock_qty: 20430.0700
negative_stock_qty: 0.0000
positive_stock_qty: 20430.0700
```

Interpretation:

```text
The physical inventory view contains only business-ready internal_or_unknown rows.
It contains no negative stock rows.
It preserves a positive total stock quantity of 20430.0700.
```

This confirms that the physical view is safe as a first conservative inventory consumption layer.

---

## Non-Physical Diagnostic View Build Result

Actual result for:

```text
vw_inventory_non_physical_snapshot
```

```text
total_rows: 1236
negative_rows: 438
zero_rows: 1
positive_rows: 797
total_stock_qty: -87119.9100
negative_stock_qty: -1471517.9800
positive_stock_qty: 1384398.0700
```

Interpretation:

```text
The diagnostic inventory view preserves all negative rows.
It keeps partner, virtual and non-business-ready evidence available for investigation.
It should not be used as the default physical inventory view.
```

---

## Diagnostic Distribution

Actual diagnostic distribution:

```text
partner / non_physical_partner_location:
    total_rows: 193
    negative_rows: 100
    total_stock_qty: -381178.5600

partner / not_business_ready:
    total_rows: 34
    negative_rows: 17
    total_stock_qty: -135328.8700

internal_or_unknown / not_business_ready:
    total_rows: 81
    negative_rows: 0
    total_stock_qty: 18847.5300

virtual / not_business_ready:
    total_rows: 138
    negative_rows: 62
    total_stock_qty: 115843.7300

virtual / non_physical_virtual_location:
    total_rows: 790
    negative_rows: 259
    total_stock_qty: 294696.2600
```

Interpretation:

```text
The diagnostic view correctly separates non-physical rows and non-ready rows.
Partner and virtual rows remain fully available for analysis.
Internal rows that are not business-ready are not lost, but they are excluded from the physical view.
```

---

## Validation Execution

Validation command executed:

```powershell
python -m scripts.validate_inventory_snapshot_views
```

Validation result:

```text
VALIDATION RESULT: PASSED
```

Validation summary:

```text
total_validations: 11
passed: 11
failed: 0
```

---

## Validation Details

The following validations passed:

```text
vw_inventory_physical_snapshot_exists: PASS
vw_inventory_non_physical_snapshot_exists: PASS
physical_view_count_matches_policy: PASS
non_physical_view_count_matches_policy: PASS
views_are_complementary: PASS
physical_view_only_internal_or_unknown: PASS
physical_view_only_business_ready: PASS
physical_view_has_no_negative_stock_rows: PASS
non_physical_view_has_exclude_reason: PASS
physical_summary_available: PASS
non_physical_distribution_available: PASS
```

---

## Complementarity Validation

The key validation result is:

```text
source_rows: 1660
physical_rows: 424
non_physical_rows: 1236
combined_rows: 1660
overlap_rows: 0
```

This proves:

```text
vw_inventory_physical_snapshot + vw_inventory_non_physical_snapshot = analytics_inventory_snapshot
```

with:

```text
no row loss
no duplicate overlap
no evidence deletion
```

---

## Physical View Policy Validation

The physical view was validated against the policy:

```text
include_in_business_views = TRUE
location_usage_type = internal_or_unknown
```

Actual validation:

```text
physical_view_count_matches_policy: PASS
expected_rows: 424
actual_rows: 424
```

Additional checks:

```text
physical_view_only_internal_or_unknown: PASS
bad_rows: 0

physical_view_only_business_ready: PASS
bad_rows: 0

physical_view_has_no_negative_stock_rows: PASS
negative_rows: 0
total_stock_qty: 20430.0700
```

---

## Non-Physical View Policy Validation

The diagnostic view was validated against the complement policy:

```text
include_in_business_views = FALSE
OR location_usage_type <> internal_or_unknown
```

Actual validation:

```text
non_physical_view_count_matches_policy: PASS
expected_rows: 1236
actual_rows: 1236
```

Additional check:

```text
non_physical_view_has_exclude_reason: PASS
bad_rows: 0
```

This confirms that every diagnostic row explains why it is excluded from the default physical inventory view.

---

## Usage Rules

### For physical inventory analysis

Use:

```text
vw_inventory_physical_snapshot
```

Do not use directly:

```text
analytics_inventory_snapshot
```

unless the analysis explicitly requires complete evidence or diagnostic rows.

---

### For diagnostic inventory analysis

Use:

```text
vw_inventory_non_physical_snapshot
analytics_inventory_snapshot
reports/analytics_inventory_negative_stock/*.csv
```

---

### For future aggregated inventory views

Aggregates should use the physical view unless the business question explicitly needs diagnostic evidence.

Recommended future source for physical inventory aggregates:

```text
vw_inventory_physical_snapshot
```

Example future objects:

```text
analytics_inventory_daily_product_location
analytics_inventory_current_product_location
analytics_inventory_current_product_company
```

However, company-level aggregates should wait until a governed location-to-company mapping exists.

---

## Important Limitation

`location_usage_type = internal_or_unknown` does not mean final company or branch identity.

It only means:

```text
The row is not classified as partner.
The row is not classified as virtual.
```

Company mapping remains deferred.

Future requirement:

```text
Design dim_inventory_location or another governed mapping object.
Map Odoo locations or warehouses explicitly to company_source_key.
Do not infer company from location_name.
```

---

## Current Decision

The final decision for this step is:

```text
analytics_inventory_snapshot remains the full inventory evidence table.
vw_inventory_physical_snapshot is the default physical inventory consumption view.
vw_inventory_non_physical_snapshot is the diagnostic non-physical inventory view.
The two views are complementary and cover all 1660 source rows without overlap.
Physical inventory consumption is limited to 424 business-ready internal_or_unknown rows.
Diagnostic inventory preserves 1236 rows for non-physical and non-ready analysis.
```

---

## Step 18.6 Closeout

Step 18.6 is complete because:

```text
build_inventory_snapshot_views.py compiled
validate_inventory_snapshot_views.py compiled
vw_inventory_physical_snapshot created
vw_inventory_non_physical_snapshot created
build completed successfully
validation passed
11 validations passed
0 validations failed
views are complementary
physical view has zero negative rows
non-physical view preserves diagnostic evidence
```

Current status:

```text
complete
```

---

## Step 18.7 Closeout

Step 18.7 is complete when:

```text
actual build results for both views are documented
actual validation results are documented
physical view policy result is documented
non-physical view policy result is documented
complementarity result is documented
usage rules are documented
future limitation around company mapping is documented
```

Current status:

```text
complete
```

---

## Recommended Next Step

Recommended next step:

```text
Paso 18.8 - Diseñar analytics_inventory_current_product_location
```

Purpose:

```text
Create the first inventory aggregate on top of vw_inventory_physical_snapshot, grouped by product and source location, without yet forcing company_source_key.
```
