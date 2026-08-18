# dim_product Design and Closeout

## Purpose

This document defines and closes the initial implementation of `dim_product`, the shared analytical product dimension for the Wansoft + Odoo + Zenput Data Warehouse and ETL Pipeline project.

The purpose of this dimension is to provide governed analytical product identities that can be used consistently across Purchases, Inventory, and future analytical domains.

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
scripts/build_dim_product.py created
scripts/validate_dim_product.py created
dim_product table created in MySQL
build completed successfully
validation completed successfully
product source identity validated
product names validated
source system values validated
product identity status values validated
mapping status values validated
mapped products require approved status
review-required products excluded from business views
normalized_product_name not used as unique identity
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
python -m scripts.build_dim_product
```

## Build Result

Latest validated build result:

```text
DIM PRODUCT BUILD SUMMARY

table: dim_product
total_rows_prepared: 2179
mapped: 251
unmapped: 432
review_required: 432
include_in_business_views: 1742

product_identity_status_counts:
  historical_only: 5
  mapped: 251
  odoo_only: 447
  pending_review: 432
  wansoft_only: 1044

source_system_counts:
  both: 113
  odoo: 848
  wansoft: 1218

mapping_status_counts:
  approved: 251
  historical_only: 5
  open_backlog: 401
  pending_review: 31
  unknown: 1491

BUILD RESULT: COMPLETED
```

---

## Validation Command

```bash
python -m scripts.validate_dim_product
```

## Validation Result

Latest validated result:

```text
total_validations: 12
passed: 12
failed: 0

VALIDATION RESULT: PASSED
```

Validated checks:

```text
dim_product_exists: PASS
dim_product_has_rows: PASS
source_identity_unique: PASS
product_names_not_null: PASS
source_product_key_not_null: PASS
source_system_values_valid: PASS
product_identity_status_values_valid: PASS
mapping_status_values_valid: PASS
mapped_products_have_approved_status: PASS
review_required_consistency: PASS
review_required_excluded_from_business_views: PASS
no_unique_identity_on_normalized_product_name: PASS
```

---

# Table Purpose

`dim_product` answers these questions:

```text
What is the analytical product identity?
Does this product come from Wansoft?
Does this product come from Odoo?
Does this product have an approved governed mapping?
Is this product Wansoft-only?
Is this product Odoo-only?
Is this product pending review?
Is this product historical-only?
Is this product part of an open backlog?
Should this product be included by default in business-facing analytical outputs?
```

This dimension prepares the analytical layer for future tables such as:

```text
analytics_purchase_order_lines
analytics_inventory_snapshot
future analytics_sales_*
future product cost analysis
future product mapping diagnostics
```

---

# Grain

The grain of the table is:

```text
1 row = 1 analytical product source identity
```

Current identity rule:

```text
source_system + source_product_key
```

This is intentional.

The table does not use product name as the identity key.

---

# Core Product Rule

The most important product rule is:

```text
Explicit reference beats name similarity.
```

This means:

```text
Do not merge products by similar names.
Do not infer product equivalence from text similarity.
Do not create automatic product aliases.
Do not use normalized_product_name as a unique analytical identity.
Do not mark a product as mapped unless approved governance exists.
```

The implementation preserves this rule.

Validation status:

```text
no_unique_identity_on_normalized_product_name: PASS
mapped_products_have_approved_status: PASS
```

---

# Current Row Counts

Current validated row count:

```text
2179 products
```

Breakdown by high-level status:

```text
mapped: 251
unmapped: 432
review_required: 432
include_in_business_views: 1742
```

Interpretation:

```text
251 products are governed mapped products.
432 products require review or are open backlog products.
1742 products are currently allowed into business-facing analytical usage.
437 products are excluded from business-facing views because they are review-required or excluded/historical.
```

Note:

```text
The excluded number is inferred from total_rows_prepared minus include_in_business_views:
2179 - 1742 = 437.
```

This aligns with:

```text
432 review_required products
5 historical_only products
```

---

# Product Identity Status

Current validated counts:

```text
wansoft_only: 1044
odoo_only: 447
pending_review: 432
mapped: 251
historical_only: 5
```

---

## mapped

Count:

```text
251
```

Meaning:

```text
The product has governed approved mapping evidence.
```

Current rule:

```text
is_mapped = true
mapping_status = approved
```

Validation status:

```text
mapped_products_have_approved_status: PASS
```

---

## wansoft_only

Count:

```text
1044
```

Meaning:

```text
The product exists as a Wansoft product identity without a governed Odoo mapping in the current dimension.
```

These products remain visible and traceable.

They are not automatically matched to Odoo products by name.

---

## odoo_only

Count:

```text
447
```

Meaning:

```text
The product exists as an Odoo product identity without a governed Wansoft mapping in the current dimension.
```

These products remain visible and traceable.

They are not automatically matched to Wansoft products by name.

---

## pending_review

Count:

```text
432
```

Meaning:

```text
The product requires review before it can be considered mapped or safe for default business-facing outputs.
```

These products are visible but excluded from business views by default.

Validation status:

```text
review_required_consistency: PASS
review_required_excluded_from_business_views: PASS
```

---

## historical_only

Count:

```text
5
```

Meaning:

```text
The product exists in governed mapping data as historical-only.
```

These products are preserved for traceability but should not be treated as active mapped products.

---

# Source System Counts

Current validated counts:

```text
both: 113
odoo: 848
wansoft: 1218
```

---

## both

Count:

```text
113
```

Meaning:

```text
The product identity has governed or dictionary-backed evidence involving both Wansoft and Odoo references.
```

Important:

```text
both does not mean fuzzy match.
both is only assigned through explicit mapping evidence.
```

---

## odoo

Count:

```text
848
```

Meaning:

```text
The product identity comes from Odoo-side evidence.
```

This includes Odoo-only products and Odoo backlog/review products.

---

## wansoft

Count:

```text
1218
```

Meaning:

```text
The product identity comes from Wansoft-side evidence.
```

This includes Wansoft-only products and Wansoft products represented through purchase evidence.

---

# Mapping Status Counts

Current validated counts:

```text
unknown: 1491
open_backlog: 401
approved: 251
pending_review: 31
historical_only: 5
```

---

## approved

Count:

```text
251
```

Meaning:

```text
Governed mapping exists and product is mapped.
```

Validation status:

```text
mapped_products_have_approved_status: PASS
```

---

## open_backlog

Count:

```text
401
```

Meaning:

```text
The product appears in odoo_purchase_inventory_mapping_backlog and should remain visible for review.
```

Rule:

```text
open_backlog products are not mapped.
open_backlog products are review-required.
open_backlog products are excluded from business views by default.
```

---

## pending_review

Count:

```text
31
```

Meaning:

```text
The product appears in governed mapping structures as pending review.
```

Rule:

```text
pending_review products are not treated as mapped.
```

---

## historical_only

Count:

```text
5
```

Meaning:

```text
The product is preserved for historical traceability but should not be treated as active mapped product.
```

---

## unknown

Count:

```text
1491
```

Meaning:

```text
The product identity was observed from source evidence but does not currently carry governed mapping status.
```

Important:

```text
unknown is not mapped.
unknown is preserved for traceability.
unknown does not imply review-required unless the product identity status or mapping status requires it.
```

This is acceptable for first implementation because many Wansoft-only or Odoo-only products do not need to be artificially mapped.

---

# Source Tables

Current source tables used by the build script:

```text
inventory_mapping_dictionary
canonical_purchase_order_line_snapshot
odoo_inventory_snapshot
odoo_purchase_inventory_mapping_backlog
```

---

## inventory_mapping_dictionary

Role:

```text
Primary governance source for product mapping.
```

Fields used include:

```text
id
domain
odoo_product_id
odoo_product_name
odoo_category_name
wansoft_code
wansoft_product_name
wansoft_department
mapping_source
mapping_status
inventory_scope
scope_source
scope_status
lifecycle_candidate
similarity_score
notes
```

Rules:

```text
mapping_status = approved -> mapped
mapping_status = pending_review -> pending_review
mapping_status = historical_only -> historical_only
```

---

## canonical_purchase_order_line_snapshot

Role:

```text
Purchase product evidence.
```

Fields used include:

```text
source_system
product_id
product_name
wansoft_code
wansoft_product_name
wansoft_department
product_mapping_found
product_mapping_status
product_mapping_source
purchase_product_scope
purchase_mapping_bucket
extracted_product_code
```

Rules:

```text
source_system = odoo and product_id exists -> Odoo product evidence
source_system = wansoft and wansoft_code exists -> Wansoft product evidence
product_mapping_status contributes to mapping classification
purchase_mapping_bucket contributes to scope/backlog context
```

---

## odoo_inventory_snapshot

Role:

```text
Inventory-side Odoo product evidence.
```

Fields used include:

```text
odoo_product_id
odoo_product_name
product_code
mapping_found
lookup_method
mapping_status
usable_for_etl
wansoft_code
wansoft_product_name
wansoft_department
lifecycle_candidate
similarity_score
mapping_notes
```

Rules:

```text
mapping_found = 1 and mapping_status = approved -> reinforces mapped identity
usable_for_etl = 0 -> excluded from business views
mapping_notes preserved in notes
```

---

## odoo_purchase_inventory_mapping_backlog

Role:

```text
Backlog and pending-review source.
```

Fields used include:

```text
product_id
product_name
purchase_product_scope
purchase_mapping_bucket
total_lines
unique_vendors
unique_companies
total_qty
total_received
total_amount
first_order_date
last_order_date
suggested_action
backlog_status
```

Rules:

```text
backlog rows become pending_review
mapping_status = open_backlog
is_review_required = true
include_in_business_views = false
```

---

# Final Field Groups

## Identity Fields

```text
product_analytical_key
product_display_name
normalized_product_name
product_canonical_name
product_identity_status
```

---

## Wansoft Fields

```text
wansoft_code
wansoft_product_name
wansoft_department
wansoft_family
wansoft_group
```

---

## Odoo Fields

```text
odoo_product_id
odoo_product_name
odoo_default_code
odoo_category
odoo_uom
```

---

## Mapping Fields

```text
mapping_status
mapping_source
mapping_confidence
is_mapped
is_unmapped
is_review_required
is_excluded
exclude_reason
```

---

## Scope Fields

```text
company_scope
scope_bucket
product_business_domain
is_restaurant_product
is_bodegon_product
is_empanadas_product
is_shared_cross_company
```

---

## Source Identity Fields

```text
source_system
source_table
source_product_key
source_product_name
```

---

## Analytical Governance Fields

```text
include_in_business_views
notes
created_at
updated_at
```

---

# Source Identity Strategy

Current unique identity:

```text
source_system + source_product_key
```

Examples:

```text
both + dict:<id>
odoo + odoo:<product_id>
wansoft + wansoft:<wansoft_code>
unknown + unknown:<normalized fallback>
```

This is safer than using:

```text
normalized_product_name
```

because product names are not reliable product identities.

Validation status:

```text
source_identity_unique: PASS
source_product_key_not_null: PASS
no_unique_identity_on_normalized_product_name: PASS
```

---

# Business View Inclusion Rule

Products are included in business-facing analytical outputs only when safe.

Current validated result:

```text
include_in_business_views: 1742
```

Products excluded from business views include:

```text
open_backlog products
pending_review products
historical_only products
review-required products
excluded products
```

Validation status:

```text
review_required_excluded_from_business_views: PASS
```

---

# Examples Observed

## Review-required products

The manual review query showed products such as:

```text
1800 Cristalino Añejo 700 Ml
400 Conejos Joven 700 Ml
Abrelatas Ind
Aceite de Oliva galón de 5lt
Alcohol Sólido Ind
Azúcar Mascabado
Bolillo
```

These rows appeared as:

```text
product_identity_status = pending_review
mapping_status = open_backlog or pending_review
source_system = odoo or wansoft
include_in_business_views = 0
```

Interpretation:

```text
Correct. These products remain visible for governance but are not exposed by default to business-facing outputs.
```

---

## Mapped products

The mapped products query showed rows such as:

```text
1800 Añejo 700 Ml
400 Conejos Tobalá 750 Ml
Aceite Vegetal
Aceituna Verde Sin Hueso
Achiote
Agua de Frambuesa
Agua de Horchata
Agua de Mango Maracuya
Aguacate Hass
Ajo Criollo
Ajo Limpio
Ajonjolí Negro
Albahaca Italiana
Amaretto Disaronno 700 Ml
```

These rows appeared as:

```text
product_identity_status = mapped
mapping_status = approved
source_product_key = dict:<id>
```

Interpretation:

```text
Correct. Mapped products come from governed dictionary rows.
```

---

# Validation Query Examples

## 1. Product identity status summary

```sql
SELECT
    product_identity_status,
    COUNT(*) AS total_products
FROM dim_product
GROUP BY product_identity_status
ORDER BY total_products DESC;
```

Current observed result:

```text
wansoft_only: 1044
odoo_only: 447
pending_review: 432
mapped: 251
historical_only: 5
```

---

## 2. Mapping status summary

```sql
SELECT
    mapping_status,
    COUNT(*) AS total_products
FROM dim_product
GROUP BY mapping_status
ORDER BY total_products DESC;
```

Current observed result:

```text
unknown: 1491
open_backlog: 401
approved: 251
pending_review: 31
historical_only: 5
```

---

## 3. Products requiring review

```sql
SELECT
    product_analytical_key,
    product_display_name,
    product_identity_status,
    mapping_status,
    source_system,
    source_product_key,
    wansoft_code,
    odoo_product_id,
    include_in_business_views,
    notes
FROM dim_product
WHERE is_review_required = TRUE
ORDER BY product_display_name
LIMIT 100;
```

Expected interpretation:

```text
Rows returned are governance work items.
They should remain visible.
They should be excluded from business views by default.
```

---

## 4. Mapped products

```sql
SELECT
    product_analytical_key,
    product_display_name,
    product_identity_status,
    mapping_status,
    source_system,
    source_product_key,
    wansoft_code,
    odoo_product_id,
    wansoft_product_name,
    odoo_product_name
FROM dim_product
WHERE is_mapped = TRUE
ORDER BY product_display_name
LIMIT 100;
```

Expected interpretation:

```text
Rows returned should have mapping_status = approved.
```

---

# Relationship to Other Analytical Objects

Implemented shared dimensions:

```text
dim_company_analytical
dim_time
dim_vendor
dim_product
```

Implemented coverage table:

```text
analytics_company_domain_coverage
```

Future purchase line analytical table should join:

```text
analytics_purchase_order_lines.company_source_key -> dim_company_analytical.company_source_key
analytics_purchase_order_lines.order_date_key -> dim_time.date_key
analytics_purchase_order_lines.vendor_analytical_key -> dim_vendor.vendor_analytical_key
analytics_purchase_order_lines.product_analytical_key -> dim_product.product_analytical_key
```

---

# Current Scripts

## Build Script

```text
scripts/build_dim_product.py
```

Purpose:

```text
Create and refresh dim_product from governed product mapping and source evidence.
```

Current behaviour:

```text
loads governed mappings from inventory_mapping_dictionary
loads purchase product evidence from canonical_purchase_order_line_snapshot
loads inventory product evidence from odoo_inventory_snapshot
loads backlog products from odoo_purchase_inventory_mapping_backlog
does not use fuzzy matching
does not use name as unique identity
marks mapped products only when approved
keeps backlog products visible
excludes review-required products from business views
uses deterministic rebuild semantics
```

---

## Validation Script

```text
scripts/validate_dim_product.py
```

Purpose:

```text
Validate product dimension consistency and product governance rules.
```

Current validations:

```text
dim_product_exists
dim_product_has_rows
source_identity_unique
product_names_not_null
source_product_key_not_null
source_system_values_valid
product_identity_status_values_valid
mapping_status_values_valid
mapped_products_have_approved_status
review_required_consistency
review_required_excluded_from_business_views
no_unique_identity_on_normalized_product_name
```

---

# Refresh Strategy

The current implementation uses deterministic rebuild semantics:

```text
DELETE FROM dim_product
INSERT current product rows
```

Reason:

```text
Section 17 is still in initial analytical design.
No downstream analytics facts depend on product_analytical_key yet.
Rebuild removes stale rows and keeps the initial dimension deterministic.
```

Future note:

```text
Once analytics facts depend on product_analytical_key, consider stable surrogate key preservation or soft-deactivation strategy.
```

Important:

```text
product_analytical_key may be reassigned during rebuild in the current version.
Do not use it yet in persistent downstream facts until the key stability strategy is defined.
```

Potential future strategy:

```text
upsert by source_system + source_product_key
preserve product_analytical_key
add is_current / deactivated_at if lifecycle tracking is needed
```

---

# Current Known Decisions

## No automatic product aliases

Decision:

```text
No product equivalence is inferred from name similarity.
```

Allowed deterministic normalisation:

```text
trim spaces
collapse spaces
remove accents
uppercase
```

Not allowed:

```text
automatic fuzzy matching
automatic name similarity merging
automatic Odoo/Wansoft equivalence by text
```

---

## Backlog products remain visible

Decision:

```text
Backlog products are inserted into dim_product.
```

Reason:

```text
Governance gaps should remain visible.
```

Current behaviour:

```text
product_identity_status = pending_review
mapping_status = open_backlog
is_review_required = true
include_in_business_views = false
```

---

## normalized_product_name is not identity

Decision:

```text
normalized_product_name is diagnostic/search support only.
```

Reason:

```text
Different products may share similar or identical names.
```

Validation status:

```text
no_unique_identity_on_normalized_product_name: PASS
```

---

## Mapping dictionary governs mapped status

Decision:

```text
Mapped products require approved mapping evidence.
```

Validation status:

```text
mapped_products_have_approved_status: PASS
```

---

# Current Known Limitations

## Some products have unknown mapping status

Current count:

```text
unknown: 1491
```

Interpretation:

```text
These are source-only product identities without explicit governed mapping status.
```

This is acceptable in the first version because they are not marked as mapped.

---

## Product surrogate key stability is not final

Current rebuild strategy may change:

```text
product_analytical_key
```

between rebuilds.

This is acceptable for now because no downstream facts depend on it yet.

Before building persistent analytical fact tables, decide whether to:

```text
preserve keys through upsert
join by source_system + source_product_key during fact build
add source alias table if needed
```

---

## Product identity is not a full master data solution

`dim_product` is an analytical dimension, not a full enterprise product master.

It does not solve:

```text
all legal product variants
all possible cross-source aliases
all warehouse-specific inventory meanings
all sales product homologation cases
```

Those can be added later through governed extensions.

---

# Step 17.17 Closeout

Step 17.17 is complete when:

```text
[x] scripts/build_dim_product.py created
[x] scripts/validate_dim_product.py created
[x] build script compiles
[x] validation script compiles
[x] dim_product table created
[x] build completed successfully
[x] validation passed
[x] 2179 products generated
[x] 251 products mapped
[x] 432 products review-required
[x] 401 open backlog products represented
[x] 5 historical-only products represented
[x] source identity uniqueness validated
[x] mapped products require approved status
[x] review-required products excluded from business views
[x] normalized_product_name not used as unique identity
```

---

# Step 17.18 Closeout

This documentation step is complete when:

```text
[x] dim_product implementation result documented
[x] actual build result documented
[x] actual validation result documented
[x] product identity status counts documented
[x] mapping status counts documented
[x] source system counts documented
[x] no automatic alias rule documented
[x] backlog visibility rule documented
[x] current limitations documented
[x] next analytical fact decision prepared
```

---

# Recommended Next Step

The core shared dimensions are now implemented:

```text
dim_company_analytical
dim_time
dim_vendor
dim_product
```

The next logical step is to start the first analytical fact table.

Recommended next step:

```text
Paso 17.19 — Diseñar analytics_purchase_order_lines
```

Reason:

```text
Purchases has the strongest canonical layer.
canonical_purchase_order_line_snapshot already exists and is validated.
The line grain is the correct first business analytical fact.
It can use all implemented shared dimensions:
    dim_company_analytical
    dim_time
    dim_vendor
    dim_product
```

Expected design topics:

```text
grain
source table
joins to dimensions
date_key rule
vendor key rule
product key rule
internal vendor filtering
product review filtering
source_system traceability
validation totals against canonical_purchase_order_line_snapshot
```