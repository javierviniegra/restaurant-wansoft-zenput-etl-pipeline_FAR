# inventory_location_company_mapping_config Seed Process Design

## Purpose

This document defines the governed seed process for `inventory_location_company_mapping_config`.

The purpose is to populate explicit, approved mappings from Odoo source inventory locations to `company_source_key` before building company-level or branch-level inventory aggregates.

This process protects the inventory model from unsafe inference.

The key rule remains:

```text
Do not infer company_source_key from location_name.
Do not infer company_source_key from normalized_location_name.
Do not infer company_source_key from source_location_id text patterns.
Do not infer company_source_key from location_usage_type.
```

Company mapping must be explicitly reviewed, approved and loaded as governance data.

---

## Scope

This seed process applies to:

```text
inventory_location_company_mapping_config
dim_inventory_location
analytics_inventory_current_product_location
future company-level inventory aggregates
future branch-level inventory aggregates
```

It does not directly modify:

```text
analytics_inventory_snapshot
vw_inventory_physical_snapshot
vw_inventory_non_physical_snapshot
analytics_inventory_current_product_location
```

---

## Current State

Current validated state of `dim_inventory_location`:

```text
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

Current interpretation:

```text
30 locations are eligible for physical inventory views.
0 locations are currently eligible for company-level inventory views.
54 locations are pending explicit company mapping.
```

This is correct and expected until approved mappings are loaded.

---

## Why a Seed Process Is Needed

`dim_inventory_location` deliberately separates three concepts:

```text
1. Source location identity.
2. Physical inventory eligibility.
3. Company inventory eligibility.
```

`source_location_id` identifies the Odoo source location.

`location_usage_type` classifies the source location as:

```text
internal_or_unknown
partner
virtual
```

But `location_usage_type` does not identify company or branch.

Therefore, an explicit seed process is required to approve mappings from:

```text
source_system + source_location_id
```

to:

```text
company_source_key
```

---

## Governance Principle

A location can be physically eligible but not yet company eligible.

Example:

```text
location_usage_type = internal_or_unknown
include_in_inventory_physical_views = TRUE
company_mapping_status = pending_location_mapping
include_in_company_inventory_views = FALSE
```

This is a valid state.

A location becomes company eligible only when:

```text
company_mapping_status = approved
company_source_key is not null
location_usage_type = internal_or_unknown
```

---

## Target Table

```text
inventory_location_company_mapping_config
```

Purpose:

```text
Store approved source location to company mappings outside build logic.
```

Current table already exists from Step 18.12.

---

## Required Seed Input

Recommended seed file:

```text
seeds/inventory_location_company_mapping_config_seed.csv
```

Required columns:

```text
source_system
source_location_id
location_name_snapshot
company_source_key
mapped_company_name
mapping_status
mapping_method
mapping_notes
effective_from_date
effective_to_date
is_active
```

Recommended defaults:

```text
source_system = odoo
mapping_status = approved
mapping_method = manual_governance
is_active = 1
```

---

## Seed CSV Template

```csv
source_system,source_location_id,location_name_snapshot,company_source_key,mapped_company_name,mapping_status,mapping_method,mapping_notes,effective_from_date,effective_to_date,is_active
odoo,,,,,approved,manual_governance,,,1
```

The seed should not include partner or virtual locations unless there is a documented reason and they must still not be enabled for company inventory views.

Recommended first scope:

```text
Only internal_or_unknown locations from dim_inventory_location where location_review_status = needs_governance_review.
```

---

## Recommended Worklist Query

Use this query to produce the first governance review list:

```sql
SELECT
    source_system,
    source_location_id,
    location_name,
    normalized_location_name,
    location_usage_type,
    include_in_inventory_physical_views,
    include_in_company_inventory_views,
    company_mapping_status,
    location_review_status,
    current_source_row_count,
    current_stock_qty
FROM dim_inventory_location
WHERE location_usage_type = 'internal_or_unknown'
  AND company_mapping_status = 'pending_location_mapping'
ORDER BY
    current_source_row_count DESC,
    current_stock_qty DESC,
    location_name;
```

Expected current first worklist size:

```text
30 locations
```

---

## Approved Mapping Rules

A seed row can be approved only when all of the following are true:

```text
source_system is populated.
source_location_id exists in dim_inventory_location.
location_usage_type is internal_or_unknown.
company_source_key is populated.
mapping_status is approved.
is_active is true.
There is no other active approved company mapping for the same source_system + source_location_id.
```

---

## Rejected Mapping Rules

A seed row must be rejected or held for review when any of the following are true:

```text
source_location_id does not exist in dim_inventory_location.
location_usage_type is partner.
location_usage_type is virtual.
company_source_key is blank.
mapping_status is not approved.
more than one active approved mapping exists for the same source_system + source_location_id.
company_source_key is not recognized by the company source governance table or policy.
```

If the company source governance table is not yet available, the validator should at least check that `company_source_key` is not blank and should mark deeper company validation as deferred.

---

## Manual Review Workflow

Recommended workflow:

```text
1. Export pending internal_or_unknown locations from dim_inventory_location.
2. Review each location with operations/accounting context.
3. Assign company_source_key only when the mapping is known and approved.
4. Save reviewed rows into seeds/inventory_location_company_mapping_config_seed.csv.
5. Run seed loader in dry-run mode.
6. Review validation output.
7. Run seed loader in apply mode.
8. Rebuild dim_inventory_location.
9. Validate dim_inventory_location.
10. Proceed only if company eligible location count matches the approved seed row count.
```

---

## Loader Design

Recommended loader script:

```text
scripts/seed_inventory_location_company_mapping_config.py
```

Recommended modes:

```text
--dry-run
--apply
```

Recommended default behavior:

```text
Dry run unless --apply is explicitly provided.
```

Purpose of dry-run:

```text
Validate the file and show what would be inserted, updated, skipped or rejected without modifying the database.
```

Purpose of apply:

```text
Load approved seed rows into inventory_location_company_mapping_config after all validations pass.
```

---

## Loader Responsibilities

The seed loader should:

```text
1. Read seeds/inventory_location_company_mapping_config_seed.csv.
2. Validate required columns.
3. Normalize text fields by trimming whitespace.
4. Confirm source locations exist in dim_inventory_location.
5. Confirm seed rows only approve internal_or_unknown locations.
6. Confirm company_source_key is not blank for approved rows.
7. Confirm no duplicate active mappings are present in the seed file.
8. Confirm no conflicting active mappings already exist in the database.
9. Insert new mappings when safe.
10. Optionally deactivate old mappings when the seed explicitly requests replacement.
11. Print a full validation and load summary.
```

---

## Replacement Policy

Default replacement policy:

```text
Do not update or deactivate existing active mappings automatically.
```

If a mapping needs to change, use a controlled replacement process:

```text
1. Deactivate the prior mapping by setting is_active = FALSE and effective_to_date.
2. Insert the new mapping with is_active = TRUE.
3. Add mapping_notes explaining the change.
```

This prevents silent historical changes.

---

## Date Policy

Recommended date usage:

```text
effective_from_date = date the mapping becomes valid
effective_to_date = null while active
is_active = 1 for current approved mapping
```

If date governance is not ready in the first implementation, allow null effective dates but require:

```text
is_active = 1
mapping_status = approved
mapping_method = manual_governance
```

---

## Validation Script Design

Recommended validator:

```text
scripts/validate_inventory_location_company_mapping_config.py
```

Validation checks:

```text
inventory_location_company_mapping_config exists
dim_inventory_location exists
all active mappings point to valid dim_inventory_location rows
all active approved mappings have company_source_key
no active approved mapping points to partner or virtual locations
no source_system + source_location_id has more than one active approved mapping
company eligible count in dim_inventory_location equals active approved internal mappings after rebuild
mapping status distribution is available
mapping method distribution is available
```

---

## Post-Seed Rebuild Sequence

After applying seed mappings, run:

```powershell
python -m scripts.seed_inventory_location_company_mapping_config --apply
python -m scripts.build_dim_inventory_location
python -m scripts.validate_dim_inventory_location
python -m scripts.validate_inventory_location_company_mapping_config
```

Expected behavior after approved mappings exist:

```text
approved_company_mappings > 0
company_view_eligible_locations > 0
pending_company_mappings decreases
include_in_company_inventory_views = TRUE only for approved internal_or_unknown locations
```

---

## Reconciliation Queries

### Active approved mappings

```sql
SELECT
    COUNT(1) AS active_approved_mappings
FROM inventory_location_company_mapping_config
WHERE is_active = TRUE
  AND mapping_status = 'approved';
```

---

### Active approved internal mappings

```sql
SELECT
    COUNT(1) AS active_approved_internal_mappings
FROM inventory_location_company_mapping_config m
INNER JOIN dim_inventory_location l
    ON l.source_system = m.source_system
   AND l.source_location_id = m.source_location_id
WHERE m.is_active = TRUE
  AND m.mapping_status = 'approved'
  AND l.location_usage_type = 'internal_or_unknown';
```

---

### Company-eligible locations after rebuild

```sql
SELECT
    COUNT(1) AS company_view_eligible_locations
FROM dim_inventory_location
WHERE include_in_company_inventory_views = TRUE;
```

Expected reconciliation after rebuild:

```text
active_approved_internal_mappings = company_view_eligible_locations
```

---

### Conflict detection

```sql
SELECT
    source_system,
    source_location_id,
    COUNT(1) AS active_approved_mappings
FROM inventory_location_company_mapping_config
WHERE is_active = TRUE
  AND mapping_status = 'approved'
GROUP BY
    source_system,
    source_location_id
HAVING COUNT(1) > 1;
```

Expected result:

```text
0 rows
```

---

## Output Reports

The seed loader should print:

```text
input_rows
valid_rows
rejected_rows
inserted_rows
skipped_existing_rows
conflicting_rows
approved_internal_mappings
rejected_partner_or_virtual_rows
```

If rejected rows exist, the loader should not apply changes unless a future controlled override is explicitly designed.

Recommended first version:

```text
Reject any file with validation failures.
```

---

## Expected First Seed Outcome

Before seed:

```text
company_view_eligible_locations: 0
approved_company_mappings: 0
pending_company_mappings: 54
```

After first approved seed file:

```text
company_view_eligible_locations should equal approved internal mappings.
pending_company_mappings should decrease by the number of approved internal mappings.
partner and virtual locations should remain company_view_eligible_locations = FALSE.
```

---

## Known Limitations

### Company catalog dependency

This process assumes `company_source_key` values are already defined elsewhere in the project.

If a formal company dimension or config table exists, the validator should check against it.

If not, validator should mark company catalog validation as deferred.

---

### No automatic branch inference

This process does not infer branch from names.

All mappings remain manual governance entries.

---

### No valuation impact

This process does not change stock quantity, stock value or valuation.

It only controls company eligibility for downstream analysis.

---

### No automatic historical remapping

This process does not retroactively reinterpret historical inventory facts unless downstream objects explicitly join current active mappings.

Historical effective dating can be expanded later if needed.

---

## Acceptance Criteria

Step 18.14 is complete when this design defines:

```text
seed file name
seed file columns
manual review workflow
approved mapping rules
rejected mapping rules
loader design
replacement policy
validation requirements
post-seed rebuild sequence
reconciliation queries
expected first seed outcome
known limitations
next implementation step
```

Current status:

```text
complete
```

---

## Recommended Next Step

Recommended next step:

```text
Paso 18.15 - Implementar seed_inventory_location_company_mapping_config.py y validate_inventory_location_company_mapping_config.py
```

Purpose:

```text
Create the dry-run/apply loader and validator for approved inventory location to company mappings.
```
