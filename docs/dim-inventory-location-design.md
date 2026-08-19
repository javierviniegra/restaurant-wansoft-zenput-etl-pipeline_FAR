# dim_inventory_location Design

## Purpose

This document defines the design for `dim_inventory_location`, the governed inventory location dimension for the MySQL analytical layer.

The purpose of this dimension is to create an explicit and governed bridge between Odoo inventory source locations and future business-facing inventory analysis.

This dimension is required before building company-level or branch-level inventory aggregates.

The dimension does not replace:

```text
analytics_inventory_snapshot
vw_inventory_physical_snapshot
vw_inventory_non_physical_snapshot
analytics_inventory_current_product_location
```

Instead, it provides governed location identity and mapping metadata that downstream objects can use safely.

---

## Why This Dimension Is Needed

The inventory layer currently has source location information, but not a governed company or branch mapping.

Existing inventory objects preserve fields such as:

```text
source_location_id
location_name
normalized_location_name
location_usage_type
company_source_key
company_mapping_status
```

However, current inventory aggregates intentionally do not infer company or branch from free-text location names.

The current rule remains:

```text
Do not infer company_source_key from location_name.
Do not infer branch from normalized_location_name.
Do not treat location_usage_type as company identity.
```

`dim_inventory_location` is the next required governance layer because it will make location identity explicit, auditable and reusable.

---

## Current Context

The current physical inventory aggregate is:

```text
analytics_inventory_current_product_location
```

It is built from:

```text
vw_inventory_physical_snapshot
```

Current validated result:

```text
source rows: 424
aggregate rows: 422
current_stock_qty: 20430.0700
negative_stock_qty: 0.0000
business rows: 422
excluded rows: 0
```

This aggregate is currently by:

```text
product_analytical_key
source_location_id
snapshot_date_key
```

It is not yet by:

```text
company_source_key
branch
warehouse
business unit
```

Reason:

```text
location-to-company mapping is not yet governed.
```

---

## External and Internal Semantics

Odoo inventory locations can represent physical, partner and virtual concepts.

Official Odoo documentation describes a location as a specific space within a warehouse and indicates that a location can have a type such as Vendor Location, Internal Location, Customer Location, Inventory Loss, Production or Transit Location.

For this project, source locations have already been classified into:

```text
internal_or_unknown
partner
virtual
```

This first classification supports separation of physical consumption from diagnostic evidence, but it is not enough to assign a company or branch.

Internal inventory discussions also showed that inventory and accounting processes may be affected by operational and valuation issues, so location governance must remain explicit instead of inferred.

---

## Target Object

```text
dim_inventory_location
```

---

## Table Classification

```text
Layer: dimension
Object type: dim_*
Domain: inventory
Primary source: inventory source locations from Odoo-derived analytical objects
Main purpose: governed location identity and mapping
Company mapping: explicit only
Branch mapping: explicit only
BI design: no
```

---

## Grain

Recommended grain:

```text
1 row = 1 governed inventory source location
```

Primary natural key:

```text
source_system
source_location_id
```

Initial source system:

```text
odoo
```

This is intentionally not keyed by `location_name` because names can change or be reused.

---

## Source Objects

Initial source objects for location discovery:

```text
analytics_inventory_snapshot
vw_inventory_physical_snapshot
vw_inventory_non_physical_snapshot
analytics_inventory_current_product_location
```

Recommended first implementation source priority:

```text
1. analytics_inventory_snapshot for complete location discovery.
2. vw_inventory_physical_snapshot for physical policy confirmation.
3. vw_inventory_non_physical_snapshot for diagnostic classification confirmation.
4. analytics_inventory_current_product_location for current physical usage confirmation.
```

Reason:

```text
analytics_inventory_snapshot contains the complete set of inventory locations captured from the source snapshot.
```

---

## Required Source Fields

Source fields currently available in analytical objects:

```text
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
```

Potential future source fields, if extracted from Odoo:

```text
odoo_location_id
odoo_location_complete_name
odoo_parent_location_id
odoo_location_type
odoo_warehouse_id
odoo_warehouse_name
odoo_company_id
odoo_company_name
barcode
is_scrap_location
is_return_location
```

The first implementation should work with current available fields and leave future Odoo-native fields as nullable placeholders.

---

## Design Principles

### Principle 1: Preserve source identity

Use `source_location_id` as the source identity.

Do not use names as identity.

```text
source_location_id is the key candidate.
location_name is descriptive metadata.
```

---

### Principle 2: Do not force company mapping

Company mapping must be explicit.

Forbidden mapping logic:

```text
CASE WHEN location_name LIKE '%Coyoacan%' THEN company_source_key = '...'
CASE WHEN normalized_location_name contains branch name THEN company_source_key = '...'
Hard-coded branch inference inside build SQL
```

Allowed mapping logic:

```text
Join to an explicit mapping table maintained as governance data.
Use approved mapping_status.
Use mapping notes and review status.
```

---

### Principle 3: Separate physical classification from company mapping

`location_usage_type` answers:

```text
Is this location internal/unknown, partner or virtual?
```

It does not answer:

```text
Which company does this location belong to?
Which branch does this location represent?
```

---

### Principle 4: Keep diagnostic locations visible

The dimension must include all discovered source locations, including:

```text
internal_or_unknown
partner
virtual
```

But downstream views can choose whether to include or exclude specific usage types.

---

### Principle 5: Use governance statuses

Every row should have a clear governance state.

Recommended fields:

```text
location_identity_status
company_mapping_status
location_review_status
include_in_inventory_physical_views
include_in_company_inventory_views
```

---

## Proposed Schema

```sql
CREATE TABLE dim_inventory_location (
    inventory_location_key BIGINT AUTO_INCREMENT PRIMARY KEY,

    source_system VARCHAR(50) NOT NULL DEFAULT 'odoo',
    source_location_id VARCHAR(100) NOT NULL,
    location_name VARCHAR(500) NULL,
    normalized_location_name VARCHAR(500) NULL,
    location_usage_type VARCHAR(100) NOT NULL,

    is_virtual_location BOOLEAN NOT NULL DEFAULT FALSE,
    is_partner_location BOOLEAN NOT NULL DEFAULT FALSE,
    is_internal_location BOOLEAN NOT NULL DEFAULT FALSE,

    parent_source_location_id VARCHAR(100) NULL,
    parent_location_name VARCHAR(500) NULL,
    location_path VARCHAR(1000) NULL,
    location_depth INT NULL,

    odoo_location_type VARCHAR(100) NULL,
    odoo_warehouse_id VARCHAR(100) NULL,
    odoo_warehouse_name VARCHAR(500) NULL,
    odoo_company_id VARCHAR(100) NULL,
    odoo_company_name VARCHAR(500) NULL,

    company_source_key VARCHAR(255) NULL,
    mapped_company_name VARCHAR(500) NULL,
    company_mapping_status VARCHAR(100) NOT NULL DEFAULT 'pending_location_mapping',
    company_mapping_method VARCHAR(100) NULL,
    company_mapping_notes TEXT NULL,

    include_in_inventory_physical_views BOOLEAN NOT NULL DEFAULT FALSE,
    include_in_company_inventory_views BOOLEAN NOT NULL DEFAULT FALSE,

    location_identity_status VARCHAR(100) NOT NULL DEFAULT 'active_source_location',
    location_review_status VARCHAR(100) NOT NULL DEFAULT 'needs_governance_review',
    location_mapping_status VARCHAR(100) NULL,

    first_seen_snapshot_date_key INT NULL,
    last_seen_snapshot_date_key INT NULL,
    current_source_row_count BIGINT NOT NULL DEFAULT 0,
    historical_source_row_count BIGINT NOT NULL DEFAULT 0,
    current_stock_qty DECIMAL(18,4) NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uq_dim_inventory_location_source (
        source_system,
        source_location_id
    ),

    KEY idx_dim_inventory_location_usage_type (
        location_usage_type
    ),

    KEY idx_dim_inventory_location_company_mapping_status (
        company_mapping_status
    ),

    KEY idx_dim_inventory_location_company_source_key (
        company_source_key
    ),

    KEY idx_dim_inventory_location_physical_views (
        include_in_inventory_physical_views
    ),

    KEY idx_dim_inventory_location_company_views (
        include_in_company_inventory_views
    )
);
```

---

## Mapping Support Table

Recommended governance support table:

```text
inventory_location_company_mapping_config
```

Purpose:

```text
Store explicit approved location-to-company mappings outside the build logic.
```

Suggested schema:

```sql
CREATE TABLE inventory_location_company_mapping_config (
    mapping_config_key BIGINT AUTO_INCREMENT PRIMARY KEY,

    source_system VARCHAR(50) NOT NULL DEFAULT 'odoo',
    source_location_id VARCHAR(100) NOT NULL,
    location_name_snapshot VARCHAR(500) NULL,

    company_source_key VARCHAR(255) NOT NULL,
    mapped_company_name VARCHAR(500) NULL,

    mapping_status VARCHAR(100) NOT NULL DEFAULT 'approved',
    mapping_method VARCHAR(100) NOT NULL DEFAULT 'manual_governance',
    mapping_notes TEXT NULL,

    effective_from_date DATE NULL,
    effective_to_date DATE NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uq_inventory_location_company_mapping_config (
        source_system,
        source_location_id,
        company_source_key,
        is_active
    )
);
```

Important:

```text
This support table should be empty or partly populated at first.
Unmapped locations should remain visible with company_mapping_status = pending_location_mapping.
```

---

## Initial Build Logic

Recommended build script:

```text
scripts/build_dim_inventory_location.py
```

Recommended steps:

```text
1. Confirm analytics_inventory_snapshot exists.
2. Create inventory_location_company_mapping_config if it does not exist.
3. Drop and recreate dim_inventory_location.
4. Discover distinct locations from analytics_inventory_snapshot.
5. Aggregate first_seen_snapshot_date_key and last_seen_snapshot_date_key.
6. Count historical source rows by source_location_id.
7. Join current physical aggregate when available to get current_source_row_count and current_stock_qty.
8. Join inventory_location_company_mapping_config for explicit company mappings only.
9. Set include_in_inventory_physical_views based on location_usage_type and physical policy.
10. Set include_in_company_inventory_views only when company mapping is approved.
11. Print build summary.
```

---

## Initial Classification Rules

### include_in_inventory_physical_views

Recommended rule:

```text
TRUE when location_usage_type = 'internal_or_unknown'
FALSE otherwise
```

Important:

```text
This field represents physical eligibility only.
It does not mean the location is company-mapped.
```

---

### include_in_company_inventory_views

Recommended rule:

```text
TRUE when company_mapping_status = 'approved'
     and company_source_key is not null
     and location_usage_type = 'internal_or_unknown'
FALSE otherwise
```

Expected first implementation:

```text
Most or all rows may be FALSE until explicit mappings are configured.
```

---

### company_mapping_status

Recommended statuses:

```text
approved
pending_location_mapping
mapping_review_required
inactive_mapping
conflicting_mapping
```

Initial default:

```text
pending_location_mapping
```

---

### location_review_status

Recommended statuses:

```text
ok
needs_governance_review
non_physical_location
mapping_review_required
inactive_source_location
```

Suggested initial logic:

```text
ok when location_usage_type = internal_or_unknown and company_mapping_status = approved
needs_governance_review when location_usage_type = internal_or_unknown and company_mapping_status <> approved
non_physical_location when location_usage_type in ('partner', 'virtual')
```

---

## Validation Requirements

Recommended validation script:

```text
scripts/validate_dim_inventory_location.py
```

Validation checks:

```text
dim_inventory_location exists
inventory_location_company_mapping_config exists
source row count by distinct source_location_id reconciles to analytics_inventory_snapshot
grain is unique by source_system + source_location_id
no null source_location_id
no null location_usage_type
all source locations from analytics_inventory_snapshot exist in dim_inventory_location
no company_source_key is populated unless mapping_status is approved
include_in_company_inventory_views requires approved company mapping
partner and virtual locations are excluded from company inventory views
physical eligibility distribution is available
company mapping status distribution is available
location review status distribution is available
```

---

## Reconciliation Queries

### Source location count

```sql
SELECT
    COUNT(DISTINCT source_location_id) AS source_location_count
FROM analytics_inventory_snapshot
WHERE source_location_id IS NOT NULL;
```

---

### Dimension location count

```sql
SELECT
    COUNT(1) AS dim_location_count
FROM dim_inventory_location;
```

Expected:

```text
source_location_count = dim_location_count
```

---

### Grain uniqueness

```sql
SELECT
    source_system,
    source_location_id,
    COUNT(1) AS total_rows
FROM dim_inventory_location
GROUP BY
    source_system,
    source_location_id
HAVING COUNT(1) > 1;
```

Expected:

```text
0 rows
```

---

### Mapping status distribution

```sql
SELECT
    company_mapping_status,
    COUNT(1) AS total_locations
FROM dim_inventory_location
GROUP BY company_mapping_status
ORDER BY company_mapping_status;
```

---

### Physical eligibility distribution

```sql
SELECT
    location_usage_type,
    include_in_inventory_physical_views,
    include_in_company_inventory_views,
    COUNT(1) AS total_locations
FROM dim_inventory_location
GROUP BY
    location_usage_type,
    include_in_inventory_physical_views,
    include_in_company_inventory_views
ORDER BY
    location_usage_type,
    include_in_inventory_physical_views,
    include_in_company_inventory_views;
```

---

## Downstream Usage

After `dim_inventory_location` is implemented, future inventory objects can join it by:

```text
source_system = 'odoo'
source_location_id
```

Recommended future join from `analytics_inventory_current_product_location`:

```sql
LEFT JOIN dim_inventory_location l
    ON l.source_system = 'odoo'
   AND l.source_location_id = a.source_location_id
```

Future company-level inventory aggregates should only include:

```text
l.include_in_company_inventory_views = TRUE
```

---

## What This Dimension Enables

This dimension enables future governed objects such as:

```text
analytics_inventory_current_product_company
analytics_inventory_current_company_location
analytics_inventory_daily_product_company
inventory branch-level physical views
inventory company-level physical views
```

---

## What This Dimension Does Not Solve Yet

This dimension does not solve:

```text
inventory valuation
unit cost
stock value
historical stock movement lineage
product semantic mismatches
Odoo/Wansoft product mapping quality
```

Those remain separate governance and analytical tasks.

---

## Expected First Implementation Outcome

Expected first implementation behavior:

```text
All distinct source locations from analytics_inventory_snapshot are included.
Partner and virtual locations are visible but excluded from physical/company views.
Internal_or_unknown locations are eligible for physical views.
Company mapping remains pending unless explicit mapping config exists.
No company_source_key is inferred from location names.
```

---

## Acceptance Criteria

Step 18.11 is complete when the design defines:

```text
target object
grain
source objects
schema
mapping support table
build logic
classification rules
validation requirements
reconciliation queries
downstream usage rules
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
Paso 18.12 - Implementar dim_inventory_location
```

Purpose:

```text
Create and validate the first governed inventory location dimension using analytics_inventory_snapshot as the complete location discovery source.
```
