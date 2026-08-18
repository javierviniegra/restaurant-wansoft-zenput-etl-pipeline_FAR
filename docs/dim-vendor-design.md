# dim_vendor Design and Closeout

## Purpose

This document defines and closes the initial implementation of `dim_vendor`, the shared analytical vendor dimension for the Wansoft + Odoo + Zenput Data Warehouse and ETL Pipeline project.

The purpose of this dimension is to provide one governed analytical row per vendor identity, so Purchases and future analytical domains can classify, join, filter, and validate vendors consistently.

This dimension belongs to the MySQL analytical layer.

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

## Current Status

Current implementation status:

```text
scripts/build_dim_vendor.py created
scripts/validate_dim_vendor.py created
dim_vendor table created in MySQL
build completed successfully
validation completed successfully
vendor names normalized deterministically
accent-insensitive normalization implemented
internal vendors classified
internal vendors excluded from business views by default
vendor source systems classified
duplicate normalized vendor names prevented
```

Current result:

```text
BUILD RESULT: COMPLETED
VALIDATION RESULT: PASSED
```

---

# Implementation Summary

## Build Command

```bash
python -m scripts.build_dim_vendor
```

## Build Result

Latest validated build result:

```text
DIM VENDOR BUILD SUMMARY

table: dim_vendor
total_rows_prepared: 414
internal_vendors: 2
external_vendors: 412
review_required: 0

vendor_source_system_counts:
  both: 32
  odoo: 27
  wansoft: 355

BUILD RESULT: COMPLETED
```

---

## Validation Command

```bash
python -m scripts.validate_dim_vendor
```

## Validation Result

Latest validated result:

```text
total_validations: 8
passed: 8
failed: 0

VALIDATION RESULT: PASSED
```

Validated checks:

```text
dim_vendor_exists: PASS
dim_vendor_has_rows: PASS
normalized_vendor_name_unique: PASS
vendor_names_not_null: PASS
vendor_source_system_values_valid: PASS
internal_vendors_classified: PASS
internal_vendor_business_flags_valid: PASS
vendor_boolean_consistency: PASS
```

---

# Table Purpose

`dim_vendor` answers these questions:

```text
What is the analytical vendor identity?
What is the normalized vendor name?
Is this vendor internal?
Is this vendor external?
Does this vendor appear in Wansoft purchases?
Does this vendor appear in Odoo purchases?
Does this vendor appear in both systems?
Should this vendor be included by default in business-facing views?
Does this vendor require manual review?
```

This dimension prepares the analytical layer for future tables such as:

```text
analytics_purchase_orders
analytics_purchase_order_lines
future purchase vendor analysis
future intercompany analysis
```

---

# Grain

The grain of the table is:

```text
1 row = 1 analytical vendor identity
```

This does not mean:

```text
1 row = 1 raw vendor spelling
```

Raw vendor names are normalized deterministically before entering the dimension.

---

# Current Row Counts

Current validated row count:

```text
414 vendors
```

Breakdown:

```text
internal_vendors: 2
external_vendors: 412
review_required: 0
```

Source system breakdown:

```text
wansoft: 355
odoo: 27
both: 32
```

Interpretation:

```text
355 vendors were detected only from Wansoft canonical purchase data.
27 vendors were detected only from Odoo canonical purchase data.
32 vendors were detected in both source systems by deterministic normalized vendor name.
```

Important:

```text
The value both does not mean a legal master-data match has been manually certified.
It means the same deterministic normalized vendor identity appeared in both source systems.
```

---

# Source Tables

Current source tables scanned by the build script:

```text
canonical_purchase_order_snapshot
canonical_purchase_order_line_snapshot
canonical_purchase_receipt_snapshot
canonical_purchase_receipt_move_snapshot
```

The build script detects available vendor fields defensively.

Candidate vendor name fields:

```text
vendor_name
source_vendor_name
partner_name
supplier_name
provider_name
proveedor
proveedor_nombre
nombre_proveedor
```

Candidate vendor ID fields:

```text
vendor_id
source_vendor_id
partner_id
supplier_id
provider_id
proveedor_id
id_proveedor
```

Candidate source system fields:

```text
source_system
source
vendor_source_system
```

---

# Final Field Groups

## Identity Fields

```text
vendor_analytical_key
vendor_display_name
normalized_vendor_name
vendor_canonical_name
```

---

## Source Traceability Fields

```text
vendor_source_system
wansoft_vendor_id
odoo_vendor_id
source_vendor_name
source_vendor_key
```

---

## Classification Fields

```text
is_internal_vendor
is_external_vendor
is_active
is_review_required
```

---

## Analytical Governance Fields

```text
include_in_business_views
exclude_reason
notes
created_at
updated_at
```

---

# Vendor Source System Values

Current valid values:

```text
wansoft
odoo
both
unknown
```

Current validated result:

```text
vendor_source_system_values_valid: PASS
```

Current observed distribution:

```text
both: 32
odoo: 27
wansoft: 355
```

No `unknown` vendor source systems were present in the latest validated build.

---

# Internal Vendor Rule

Known internal vendors:

```text
EL BODEGON DE FITO
LAS EMPANADAS DE MARIA EVA
```

Canonical analytical names:

```text
Bodegón
Empanadas
```

Current validated result:

```text
internal_vendors: 2
internal_vendors_classified: PASS
internal_vendor_business_flags_valid: PASS
```

Rules for internal vendors:

```text
is_internal_vendor = true
is_external_vendor = false
include_in_business_views = false
exclude_reason = internal_vendor
```

Business interpretation:

```text
Internal vendors are preserved in the analytical model.
Internal vendors are not deleted.
Internal vendors are excluded by default from business-facing views.
Internal vendors remain available for technical and intercompany analysis.
```

This is consistent with the broader project rule:

```text
Bodegón and Empanadas are internal providers, not final operating branches.
They may appear as vendors.
```

---

# Normalization Rule

## Current Normalization

The implementation normalizes vendor names using:

```text
trim spaces
collapse repeated spaces
remove accents
uppercase
```

Example:

```text
CERVEZAS CUAUHTÉMOC MOCTEZUMA
CERVEZAS CUAUHTEMOC MOCTEZUMA
```

both normalize to:

```text
CERVEZAS CUAUHTEMOC MOCTEZUMA
```

---

## Why Accent Removal Was Added

The first build failed with:

```text
Duplicate entry 'CERVEZAS CUAUHTEMOC MOCTEZUMA' for key 'uq_dim_vendor_normalized_vendor_name'
```

Interpretation:

```text
Python initially treated accented and non-accented strings as different normalized keys.
MariaDB collation treated them as equivalent for the unique index.
```

Fix:

```text
Remove accents before generating normalized_vendor_name.
```

Final status:

```text
Build completed successfully after accent-insensitive normalization.
```

---

# No Fuzzy Matching Rule

The implementation does not perform fuzzy matching.

This is intentional.

The rule is:

```text
Explicit identity beats name similarity.
```

This means:

```text
Do not merge vendors only because names look similar.
Do not create fuzzy vendor aliases automatically.
Do not collapse unrelated vendors based on partial text.
```

Current normalization is deterministic and limited to:

```text
spacing
case
accents
```

It does not infer legal equivalence by similarity.

---

# Relationship to dim_company_analytical

`dim_vendor` is separate from:

```text
dim_company_analytical
```

However, some business entities may appear in both dimensions with different roles.

Example:

```text
Bodegón
Empanadas
```

In `dim_company_analytical`:

```text
They are internal providers and not final operating branches.
```

In `dim_vendor`:

```text
They are internal vendors.
```

This is intentional.

The same entity can have different analytical roles:

```text
company/location role
vendor/provider role
```

---

# Relationship to Purchases

`dim_vendor` prepares future purchase analytical tables.

Expected future joins:

```text
analytics_purchase_orders.vendor_analytical_key -> dim_vendor.vendor_analytical_key
analytics_purchase_order_lines.vendor_analytical_key -> dim_vendor.vendor_analytical_key
```

Until those tables are implemented, canonical purchase tables remain the upstream source.

Future purchase analytics should not rely only on raw vendor names.

They should use:

```text
vendor_analytical_key
```

or, during transition:

```text
normalized_vendor_name
```

---

# Business View Rule

Business-facing views should exclude internal vendors by default.

Future view logic may use:

```sql
WHERE include_in_business_views = TRUE
```

or:

```sql
WHERE is_internal_vendor = FALSE
```

Technical views may include all vendors.

Important:

```text
Internal vendors should not be removed from facts.
They should be filterable.
```

---

# Current Scripts

## Build Script

```text
scripts/build_dim_vendor.py
```

Purpose:

```text
Create and refresh dim_vendor from canonical purchase tables.
```

Current behaviour:

```text
detects vendor fields defensively
normalizes vendor names
removes accents
classifies internal vendors
merges source-system presence
preserves source IDs where available
uses deterministic rebuild semantics
prints build summary
```

---

## Validation Script

```text
scripts/validate_dim_vendor.py
```

Purpose:

```text
Validate vendor dimension consistency and internal vendor rules.
```

Current validations:

```text
dim_vendor_exists
dim_vendor_has_rows
normalized_vendor_name_unique
vendor_names_not_null
vendor_source_system_values_valid
internal_vendors_classified
internal_vendor_business_flags_valid
vendor_boolean_consistency
```

---

# Validation Query Examples

## 1. Source system summary

```sql
SELECT
    vendor_source_system,
    COUNT(*) AS total_vendors
FROM dim_vendor
GROUP BY vendor_source_system
ORDER BY vendor_source_system;
```

Expected current result:

```text
both: 32
odoo: 27
wansoft: 355
```

---

## 2. Internal vendors

```sql
SELECT
    vendor_analytical_key,
    vendor_display_name,
    vendor_canonical_name,
    normalized_vendor_name,
    vendor_source_system,
    is_internal_vendor,
    is_external_vendor,
    include_in_business_views,
    exclude_reason
FROM dim_vendor
WHERE is_internal_vendor = TRUE
ORDER BY vendor_display_name;
```

Expected result:

```text
EL BODEGON DE FITO
LAS EMPANADAS DE MARIA EVA
```

with:

```text
is_internal_vendor = 1
is_external_vendor = 0
include_in_business_views = 0
exclude_reason = internal_vendor
```

---

## 3. Vendors requiring review

```sql
SELECT
    vendor_analytical_key,
    vendor_display_name,
    vendor_canonical_name,
    vendor_source_system,
    source_vendor_name,
    source_vendor_key,
    is_review_required,
    notes
FROM dim_vendor
WHERE is_review_required = TRUE
ORDER BY vendor_display_name;
```

Expected current result:

```text
0 rows
```

Current build summary:

```text
review_required: 0
```

---

## 4. Duplicate normalized vendor names

```sql
SELECT
    normalized_vendor_name,
    COUNT(*) AS total_rows
FROM dim_vendor
GROUP BY normalized_vendor_name
HAVING COUNT(*) > 1;
```

Expected result:

```text
0 rows
```

Validation status:

```text
normalized_vendor_name_unique: PASS
```

---

## 5. Internal vendor business flags

```sql
SELECT
    vendor_analytical_key,
    vendor_display_name,
    vendor_canonical_name,
    is_internal_vendor,
    is_external_vendor,
    include_in_business_views,
    exclude_reason
FROM dim_vendor
WHERE is_internal_vendor = TRUE
  AND (
        is_external_vendor <> FALSE
     OR include_in_business_views <> FALSE
     OR exclude_reason <> 'internal_vendor'
  );
```

Expected result:

```text
0 rows
```

Validation status:

```text
internal_vendor_business_flags_valid: PASS
```

---

# Refresh Strategy

The current implementation uses deterministic rebuild semantics:

```text
DELETE FROM dim_vendor
INSERT current vendor rows
```

Reason:

```text
Section 17 is still in initial analytical design.
No downstream analytics facts depend on vendor_analytical_key yet.
Rebuild removes stale vendor rows and keeps the initial dimension deterministic.
```

Future note:

```text
Once analytics facts depend on vendor_analytical_key, consider stable surrogate key preservation or soft-deactivation strategy.
```

Important:

```text
vendor_analytical_key may be reassigned during rebuild in the current version.
Do not use it yet in persistent downstream facts until the key stability strategy is defined.
```

For future fact tables, options include:

```text
join by normalized_vendor_name during initial build
preserve vendor_analytical_key through upsert
add is_current / deactivated_at if vendor lifecycle tracking is needed
```

---

# Current Known Decisions

## Internal vendors

Decision:

```text
Bodegón and Empanadas are preserved as vendors.
They are excluded from business views by default.
```

---

## Vendor aliases

Decision:

```text
No separate dim_vendor_source_alias table in first implementation.
```

Reason:

```text
First version remains deterministic and simple.
```

Potential future table:

```text
dim_vendor_source_alias
```

Potential fields:

```text
source_system
source_vendor_id
source_vendor_name
vendor_analytical_key
normalized_source_vendor_name
```

---

## Vendor matching

Decision:

```text
No fuzzy matching.
```

Allowed normalization:

```text
trim spaces
collapse spaces
remove accents
uppercase
```

Not allowed:

```text
automatic legal equivalence inference
automatic fuzzy alias creation
automatic partial-name matching
```

---

# Current Known Limitations

## Legal vendor equivalence is not fully governed

The current `both` classification is based on deterministic normalized vendor name appearing in both source systems.

This is useful, but it is not the same as a manually governed vendor master.

Future enhancement:

```text
Vendor alias table or governed vendor mapping table.
```

---

## Source vendor IDs may be multiple

The implementation preserves available IDs by appending unique source IDs where present.

This means fields such as:

```text
wansoft_vendor_id
odoo_vendor_id
source_vendor_key
```

may contain one or more values separated by:

```text
|
```

This is acceptable for initial traceability, but a future alias table would be cleaner.

---

## Surrogate key stability is not final

Current rebuild uses:

```text
DELETE FROM dim_vendor
INSERT current rows
```

This means:

```text
vendor_analytical_key can change between rebuilds.
```

This is acceptable now because no downstream facts depend on it yet.

Before using `vendor_analytical_key` in persistent analytics facts, the implementation should switch to:

```text
upsert by normalized_vendor_name
```

or another stable key strategy.

---

# Step 17.13 Closeout

Step 17.13 is complete when:

```text
[x] scripts/build_dim_vendor.py created
[x] scripts/validate_dim_vendor.py created
[x] build script compiles
[x] validation script compiles
[x] dim_vendor table created
[x] build completed successfully
[x] validation passed
[x] 414 vendors generated
[x] 2 internal vendors classified
[x] 412 external vendors classified
[x] 0 vendors requiring review
[x] source system values classified
[x] accent-insensitive normalization implemented
[x] internal vendor flags validated
```

---

# Step 17.14 Closeout

This documentation step is complete when:

```text
[x] dim_vendor implementation result documented
[x] real build result documented
[x] real validation result documented
[x] internal vendor rule documented
[x] accent-insensitive normalization documented
[x] vendor source breakdown documented
[x] current limitations documented
[x] next dimension decision prepared
```

---

# Recommended Next Shared Dimension

Current implemented shared dimensions:

```text
dim_company_analytical
dim_time
dim_vendor
```

Remaining planned shared dimension:

```text
dim_product
```

## Recommendation

The next shared dimension should be:

```text
dim_product
```

Reason:

```text
dim_company_analytical is implemented.
dim_time is implemented.
dim_vendor is implemented.
dim_product is the remaining core shared dimension needed before building detailed purchase and inventory analytical facts.
```

However, `dim_product` is the most delicate dimension.

It must respect the existing project rule:

```text
Explicit reference beats name similarity.
```

The product dimension should not automatically merge products by similar names.

---

# Recommended Next Step

```text
Paso 17.15 — Diseñar dim_product
```

Expected contents:

```text
purpose
grain
source inputs
relationship to inventory_mapping_dictionary
mapping_status rules
Wansoft/Odoo product identity rules
no automatic alias rule
proposed fields
schema draft
validation requirements
implementation approach
```