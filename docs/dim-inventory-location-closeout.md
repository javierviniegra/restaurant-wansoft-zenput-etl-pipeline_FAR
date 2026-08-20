# dim_inventory_location Closeout

## Purpose

This document closes the real implementation of `dim_inventory_location` and its support mapping table.

The implementation created the governed inventory location dimension required before building company-level or branch-level inventory aggregates.

The dimension was built from:

```text
analytics_inventory_snapshot
```

Reason:

```text
analytics_inventory_snapshot remains the complete inventory evidence table and contains the full discovered set of source locations.
```

---

## Scope

This closeout covers:

```text
scripts/build_dim_inventory_location.py
scripts/validate_dim_inventory_location.py
dim_inventory_location
inventory_location_company_mapping_config
analytics_inventory_snapshot
analytics_inventory_current_product_location
```

It documents:

```text
compilation result
build result
validation result
source location reconciliation
grain validation
physical eligibility validation
company mapping validation
current usage reconciliation
distribution summaries
known limitations
recommended next step
```

---

## Implemented Objects

### Main dimension

```text
dim_inventory_location
```

Purpose:

```text
Governed inventory location dimension for source Odoo inventory locations.
```

Implemented grain:

```text
1 row = 1 source inventory location per source system
```

Natural key:

```text
source_system
source_location_id
```

Initial source system:

```text
odoo
```

---

### Mapping support table

```text
inventory_location_company_mapping_config
```

Purpose:

```text
Support explicit, governed mapping from source inventory locations to company_source_key.
```

Current expected state:

```text
The table can exist with zero approved mappings.
Unmapped locations remain visible with company_mapping_status = pending_location_mapping.
```

---

## Governance Principle Confirmed

The implementation confirms the governance rule:

```text
Do not infer company_source_key from location_name.
Do not infer company_source_key from normalized_location_name.
Do not infer company_source_key from location_usage_type.
```

Company-level inventory eligibility requires explicit approved mapping.

---

## Compilation

Commands executed:

```powershell
python -m py_compile scripts\build_dim_inventory_location.py
python -m py_compile scripts\validate_dim_inventory_location.py
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
python -m scripts.build_dim_inventory_location
```

Build result:

```text
BUILD RESULT: COMPLETED
```

Actual build summary:

```text
table: dim_inventory_location
total_locations: 54
internal_or_unknown_locations: 30
partner_locations: 2
virtual_locations: 22
physical_view_eligible_locations: 30
company_view_eligible_locations: 0
approved_company_mappings: 0
pending_company_mappings: 54
needs_governance_review_locations: 30
non_physical_locations: 24
current_source_row_count: 424
current_stock_qty: 20430.0700
```

---

## Build Interpretation

The dimension discovered:

```text
54 total source inventory locations
```

Distributed as:

```text
30 internal_or_unknown locations
2 partner locations
22 virtual locations
```

This confirms that `dim_inventory_location` is a complete source location dimension and not only a physical inventory location list.

---

## Physical Eligibility Result

Actual result:

```text
physical_view_eligible_locations: 30
```

Meaning:

```text
Only the 30 internal_or_unknown locations are eligible for physical inventory views.
```

This aligns with the previous location policy:

```text
include_in_inventory_physical_views = TRUE only when location_usage_type = internal_or_unknown
```

---

## Company Mapping Result

Actual result:

```text
company_view_eligible_locations: 0
approved_company_mappings: 0
pending_company_mappings: 54
```

Interpretation:

```text
No source location is currently eligible for company-level inventory views.
All 54 source locations remain pending explicit company mapping.
```

This is expected because no approved mappings have been loaded into `inventory_location_company_mapping_config`.

This is not a failure. It is the intended governance protection before producing company-level inventory reports.

---

## Location Review Result

Actual result:

```text
needs_governance_review_locations: 30
non_physical_locations: 24
```

Interpretation:

```text
The 30 internal_or_unknown locations are physical candidates but still require governance review before company mapping.
The 24 partner or virtual locations are visible for diagnostics but excluded from physical/company inventory views.
```

---

## Current Usage Reconciliation

`dim_inventory_location` also reconciles current physical usage back to:

```text
analytics_inventory_current_product_location
```

Actual validation result:

```text
source_current_rows: 424
dim_current_rows: 424
source_current_stock_qty: 20430.0700
dim_current_stock_qty: 20430.0700
```

Validation result:

```text
current_usage_reconciles: PASS
```

Interpretation:

```text
The dimension preserves the current physical usage evidence already validated in analytics_inventory_current_product_location.
```

---

## Validation Execution

Command executed:

```powershell
python -m scripts.validate_dim_inventory_location
```

Validation result:

```text
VALIDATION RESULT: PASSED
```

Validation summary:

```text
total_validations: 17
passed: 17
failed: 0
```

---

## Validation Details

The following validations passed:

```text
analytics_inventory_snapshot_exists: PASS
dim_inventory_location_exists: PASS
inventory_location_company_mapping_config_exists: PASS
source_location_count_reconciles: PASS
dim_inventory_location_grain_unique: PASS
no_null_source_location_id: PASS
no_null_location_usage_type: PASS
all_source_locations_present: PASS
no_company_key_without_approved_mapping: PASS
company_view_requires_approved_mapping: PASS
partner_virtual_excluded_from_company_views: PASS
physical_eligibility_logic_valid: PASS
mapping_config_grain_unique: PASS
current_usage_reconciles: PASS
physical_eligibility_distribution_available: PASS
company_mapping_status_distribution_available: PASS
location_review_status_distribution_available: PASS
```

---

## Source Location Reconciliation

Actual validation result:

```text
source_location_count: 54
dim_location_count: 54
```

Validation result:

```text
source_location_count_reconciles: PASS
```

Interpretation:

```text
Every distinct source_location_id from analytics_inventory_snapshot is represented in dim_inventory_location.
```

Additional validation:

```text
all_source_locations_present: PASS
missing_rows: 0
```

---

## Grain Validation

Validation result:

```text
dim_inventory_location_grain_unique: PASS
```

Interpretation:

```text
There are no duplicate rows by source_system + source_location_id.
```

---

## Required Field Validation

Source location validation:

```text
no_null_source_location_id: PASS
bad_rows: 0
```

Location usage validation:

```text
no_null_location_usage_type: PASS
bad_rows: 0
```

Interpretation:

```text
The dimension contains no null source location identifiers and no null location usage classifications.
```

---

## Company Mapping Validation

Company key governance:

```text
no_company_key_without_approved_mapping: PASS
bad_rows: 0
```

Company view requirement:

```text
company_view_requires_approved_mapping: PASS
bad_rows: 0
```

Partner/virtual exclusion:

```text
partner_virtual_excluded_from_company_views: PASS
bad_rows: 0
```

Interpretation:

```text
No company mapping was inferred incorrectly.
No location entered company inventory views without approved mapping.
Partner and virtual locations were not allowed into company inventory views.
```

---

## Physical Eligibility Distribution

Actual validation output:

```text
internal_or_unknown:
    include_in_inventory_physical_views: 1
    include_in_company_inventory_views: 0
    total_locations: 30

partner:
    include_in_inventory_physical_views: 0
    include_in_company_inventory_views: 0
    total_locations: 2

virtual:
    include_in_inventory_physical_views: 0
    include_in_company_inventory_views: 0
    total_locations: 22
```

Validation result:

```text
physical_eligibility_distribution_available: PASS
```

---

## Company Mapping Status Distribution

Actual validation output:

```text
pending_location_mapping: 54
```

Validation result:

```text
company_mapping_status_distribution_available: PASS
```

Interpretation:

```text
All discovered inventory locations are awaiting explicit location-to-company governance mapping.
```

---

## Location Review Status Distribution

Actual validation output:

```text
needs_governance_review: 30
non_physical_location: 24
```

Validation result:

```text
location_review_status_distribution_available: PASS
```

Interpretation:

```text
Internal physical candidates require governance review.
Partner and virtual locations are marked as non-physical locations.
```

---

## Current Object Status

Objects:

```text
dim_inventory_location
inventory_location_company_mapping_config
```

Status:

```text
implemented
built
validated
ready for explicit location-to-company governance mapping
```

Current summary:

```text
total_locations: 54
internal_or_unknown_locations: 30
partner_locations: 2
virtual_locations: 22
physical_view_eligible_locations: 30
company_view_eligible_locations: 0
pending_company_mappings: 54
current_source_row_count: 424
current_stock_qty: 20430.0700
validation failures: 0
```

---

## What This Enables

The dimension enables controlled downstream design for:

```text
analytics_inventory_current_product_company
analytics_inventory_current_company_location
company-level inventory views
branch-level inventory views
location governance worklists
```

But only after approved mappings are added to:

```text
inventory_location_company_mapping_config
```

---

## What This Does Not Solve Yet

This step does not yet solve:

```text
company-level inventory reporting
branch-level inventory reporting
inventory valuation
unit cost
stock value
product semantic mapping issues
historical movement lineage
```

The table is a governance foundation, not the final company inventory model.

---

## Operational Rationale

This implementation supports the inventory governance approach discussed in the Odoo inventory and valuation workstream: inventory and accounting must remain synchronized, and adjustments that affect valuation should not be treated casually as reporting-only corrections. The dimension separates source location identity, physical eligibility and company mapping readiness instead of blending those meanings into one field.

---

## Step 18.12 Closeout

Step 18.12 is complete because:

```text
build_dim_inventory_location.py compiled
validate_dim_inventory_location.py compiled
dim_inventory_location created
inventory_location_company_mapping_config created
build completed successfully
source location count reconciled
grain uniqueness validated
physical eligibility validated
company mapping governance validated
current usage reconciled
17 validations passed
0 validations failed
```

Current status:

```text
complete
```

---

## Step 18.13 Closeout

Step 18.13 is complete when this document records:

```text
actual build result
actual validation result
source location reconciliation
grain validation
physical eligibility distribution
company mapping distribution
location review distribution
current usage reconciliation
known limitations
recommended next step
```

Current status:

```text
complete
```

---

## Recommended Next Step (as of original closeout)

Recommended next step:

```text
Paso 18.14 - Diseñar inventory_location_company_mapping_config seed process
```

Purpose:

```text
Create a governed process for populating approved source_location_id to company_source_key mappings before building company-level inventory aggregates.
```

---

## Update: Paso 18.20 Reconnection (2026-08-20)

The state documented above (`company_view_eligible_locations: 0`, entirely dependent on the manual seed) was accurate at the time but is now superseded. It reflected a real architectural gap: the Odoo location master extraction (Paso 18.18) was built after this closeout but never wired back into this build script.

### What Changed

`scripts/build_dim_inventory_location.py` was updated so that `company_source_key`, `mapped_company_name`, `company_mapping_status`, `company_mapping_method` and `include_in_company_inventory_views` now prefer the governed resolution already computed in `analytics_inventory_snapshot.company_source_key` (itself resolved from `stg_odoo_inventory_location_master`, Odoo's own `stock.location.company_id`, Paso 18.18-18.20). The manual seed table (`inventory_location_company_mapping_config`) is kept as an explicit override: when an active mapping exists there, it always wins over the automatic Odoo resolution.

The governance principle from the original design is preserved exactly: `company_source_key` is never inferred from `location_name` text. It is now resolved from Odoo's structured `company_id` field instead of only from the (still empty) manual worklist.

### Actual Rebuild Result (dev, 2026-08-20)

```text
total_locations: 70
internal_or_unknown_locations: 37
partner_locations: 2
virtual_locations: 31
physical_view_eligible_locations: 37
company_view_eligible_locations: 14        (was 0)
approved_company_mappings: 0                (manual seed still empty, expected)
pending_company_mappings: 0
needs_governance_review_locations: 1
non_physical_locations: 33
current_source_row_count: 294
current_stock_qty: 4327.4549
```

`total_locations` grew from 54 to 70 and `current_source_row_count`/`current_stock_qty` changed because `analytics_inventory_snapshot` itself was rebuilt in the same session against a corrected, current `odoo_inventory_snapshot` (see Section 18 Status in `docs/project-status-and-todo.md` for the full chain). This is not a discrepancy in this object; it reflects an upstream refresh.

### Validation Result

```text
total_validations: 17
passed: 17
failed: 0
VALIDATION RESULT: PASSED
```

Includes two updated checks (`no_company_key_without_approved_mapping`, `company_view_requires_approved_mapping` in `scripts/validate_dim_inventory_location.py`) that now also accept the new `approved_from_odoo_location_master` status alongside the original `approved`/`approved_from_source`.

### Company Mapping Status Distribution

```text
approved_from_odoo_location_master: 14   (physically eligible + Odoo final -> company eligible)
final_odoo_enabled: 12                    (Odoo final, but not a physically eligible location type)
parallel_diagnostic_odoo: 22              (Wansoft is official source, Odoo data kept visible only)
internal_provider_excluded: 11
out_of_scope_excluded: 7
unmapped_location_pending_review: 4
```

### What This Still Does Not Solve

```text
The manual seed table remains empty (0 approved rows). It stays available as an
override mechanism for exceptions the Odoo location master cannot resolve, per
the original design intent, but is no longer the only path to company eligibility.
Wansoft-side inventory (getstockinventory_inventario) is still not unified with
this table.
```

### Recommended Next Step

```text
Continue with the remaining Section 18 documentation closeout, then decide
between Wansoft inventory unification and preparing for the final
production-promotion acceptance test.
```
