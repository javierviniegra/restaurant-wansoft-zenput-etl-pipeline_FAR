# analytics_inventory_current_product_location Design

## Purpose

This document defines the design for `analytics_inventory_current_product_location`, the first inventory aggregate derived from the physical inventory view.

The purpose of this table is to provide a current physical stock position by product and Odoo source location, using only rows that are already eligible for first-version physical inventory consumption.

This object is not a Power BI model, not a dashboard, and not a final branch/company inventory report.

It belongs to the MySQL analytical layer.

---

## Source Dependency

Primary source view:

```text
vw_inventory_physical_snapshot
```

Do not build this aggregate directly from:

```text
analytics_inventory_snapshot
```

Reason:

```text
analytics_inventory_snapshot is the full evidence table.
vw_inventory_physical_snapshot already applies the location_usage_type policy.
```

The physical view currently represents:

```text
include_in_business_views = TRUE
AND location_usage_type = 'internal_or_unknown'
```

The validated physical view result from Step 18.6 was:

```text
total_rows: 424
negative_rows: 0
zero_rows: 1
positive_rows: 423
total_stock_qty: 20430.0700
negative_stock_qty: 0.0000
positive_stock_qty: 20430.0700
```

---

## Operational Context

Inventory analysis must separate physical stock from diagnostic and accounting/valuation evidence.

Internal inventory discussions documented that inventory and accounting must be synchronized and that inventory adjustments affecting valuation should be performed through the inventory module instead of direct accounting-only adjustments. This supports keeping the base evidence complete while using physical views for business-facing inventory consumption.

The current aggregate must therefore use `vw_inventory_physical_snapshot`, not the full diagnostic evidence table.

---

## Design Goal

`analytics_inventory_current_product_location` should answer questions such as:

```text
What is the current physical stock quantity by product and Odoo source location?
Which products have positive physical stock in each source location?
Which physical source locations currently contain each product?
What is the latest snapshot date represented in the current physical view?
Which product-location combinations are eligible for future company/location mapping?
```

It should not yet answer:

```text
What is inventory by company?
What is inventory by branch?
What is inventory valuation?
What is inventory cost?
What is inventory by warehouse hierarchy?
```

Those require future governed location mapping and/or valuation sources.

---

## Target Object

```text
analytics_inventory_current_product_location
```

---

## Table Classification

```text
Layer: analytical aggregate
Object type: analytics_*
Domain: inventory
Source: vw_inventory_physical_snapshot
Grain: current physical product-location
BI design: no
Company mapping: deferred
Valuation: deferred
```

---

## Grain

Recommended grain:

```text
1 row = 1 current physical product per Odoo source location
```

Natural grain fields:

```text
product_analytical_key
source_location_id
snapshot_date_key
```

Because this is a current-state aggregate, the build should first identify the latest available physical snapshot and then aggregate only that current snapshot.

Current snapshot rule:

```text
Use the maximum etl_loaded_at available in vw_inventory_physical_snapshot.
```

Alternative fallback rule:

```text
If etl_loaded_at is not reliable, use maximum snapshot_date_key.
```

Recommended implementation:

```text
current_snapshot_loaded_at = MAX(etl_loaded_at)
```

Then aggregate rows where:

```text
etl_loaded_at = current_snapshot_loaded_at
```

If the physical view contains multiple loads within the same day, `etl_loaded_at` is more precise than `snapshot_date_key`.

---

## Required Source Fields

From `vw_inventory_physical_snapshot`:

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
include_in_business_views
inventory_review_status
include_in_inventory_physical_views
inventory_physical_exclude_reason
```

---

## Business Rules

### Rule 1: Use only physical view rows

Source must be:

```text
vw_inventory_physical_snapshot
```

Do not reimplement the location policy inside this aggregate unless needed for validation.

The physical view already ensures:

```text
include_in_business_views = TRUE
location_usage_type = internal_or_unknown
include_in_inventory_physical_views = TRUE
```

---

### Rule 2: Use only current snapshot

Use only rows from the latest physical snapshot load.

Recommended filter:

```sql
WHERE etl_loaded_at = (
    SELECT MAX(etl_loaded_at)
    FROM vw_inventory_physical_snapshot
)
```

If future data loads introduce multiple `etl_loaded_at` values inside the same operational snapshot, revisit this rule.

---

### Rule 3: Aggregate stock quantity

Use:

```text
SUM(stock_qty)
```

as:

```text
current_stock_qty
```

Do not use valuation fields.

Do not calculate cost.

Do not calculate monetary inventory value.

---

### Rule 4: Do not force company mapping

Preserve:

```text
company_source_key
company_mapping_status
```

But do not populate `company_source_key` from `location_name`.

Until location mapping exists, expected values may remain:

```text
company_source_key = null
company_mapping_status = pending_location_mapping
```

---

### Rule 5: Keep product governance transparent

The source physical view should already contain only product-ready business rows.

Still preserve product governance fields:

```text
product_identity_status
dim_product_mapping_status
is_product_mapped
is_product_review_required
include_product_in_business_views
inventory_review_status
```

Validation should confirm that no aggregate row is built from review-required or orphan product rows.

---

## Proposed Schema

```sql
CREATE TABLE analytics_inventory_current_product_location (
    inventory_current_product_location_key BIGINT AUTO_INCREMENT PRIMARY KEY,

    snapshot_date DATE NULL,
    snapshot_date_key INT NULL,
    current_snapshot_loaded_at DATETIME NULL,

    product_analytical_key BIGINT NOT NULL,
    odoo_product_id VARCHAR(100) NULL,
    odoo_product_name VARCHAR(500) NULL,
    product_code VARCHAR(255) NULL,
    wansoft_code VARCHAR(255) NULL,
    wansoft_product_name VARCHAR(500) NULL,
    wansoft_department VARCHAR(255) NULL,

    source_location_id VARCHAR(100) NOT NULL,
    location_name VARCHAR(500) NULL,
    normalized_location_name VARCHAR(500) NULL,
    location_usage_type VARCHAR(100) NOT NULL,

    company_source_key VARCHAR(255) NULL,
    company_mapping_status VARCHAR(100) NULL,

    current_stock_qty DECIMAL(18,4) NOT NULL DEFAULT 0,
    source_row_count INT NOT NULL DEFAULT 0,

    product_identity_status VARCHAR(100) NULL,
    dim_product_mapping_status VARCHAR(100) NULL,
    is_product_mapped BOOLEAN NOT NULL DEFAULT FALSE,
    is_product_review_required BOOLEAN NOT NULL DEFAULT FALSE,
    include_product_in_business_views BOOLEAN NOT NULL DEFAULT TRUE,
    inventory_review_status VARCHAR(100) NULL,

    include_in_inventory_physical_views BOOLEAN NOT NULL DEFAULT TRUE,
    inventory-current-status VARCHAR(100) NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uq_inventory_current_product_location (
        snapshot_date_key,
        product_analytical_key,
        source_location_id
    ),

    KEY idx_inventory_current_product (
        product_analytical_key
    ),

    KEY idx_inventory_current_location (
        source_location_id
    ),

    KEY idx_inventory_current_snapshot_date (
        snapshot_date_key
    ),

    KEY idx_inventory_current_company_status (
        company_mapping_status
    )
);
```

Important correction before implementation:

```text
The field name inventory-current-status contains a hyphen and is not valid SQL identifier style.
Use inventory_current_status instead.
```

Corrected field:

```sql
inventory_current_status VARCHAR(100) NULL
```

---

## Corrected Proposed Schema

```sql
CREATE TABLE analytics_inventory_current_product_location (
    inventory_current_product_location_key BIGINT AUTO_INCREMENT PRIMARY KEY,

    snapshot_date DATE NULL,
    snapshot_date_key INT NULL,
    current_snapshot_loaded_at DATETIME NULL,

    product_analytical_key BIGINT NOT NULL,
    odoo_product_id VARCHAR(100) NULL,
    odoo_product_name VARCHAR(500) NULL,
    product_code VARCHAR(255) NULL,
    wansoft_code VARCHAR(255) NULL,
    wansoft_product_name VARCHAR(500) NULL,
    wansoft_department VARCHAR(255) NULL,

    source_location_id VARCHAR(100) NOT NULL,
    location_name VARCHAR(500) NULL,
    normalized_location_name VARCHAR(500) NULL,
    location_usage_type VARCHAR(100) NOT NULL,

    company_source_key VARCHAR(255) NULL,
    company_mapping_status VARCHAR(100) NULL,

    current_stock_qty DECIMAL(18,4) NOT NULL DEFAULT 0,
    source_row_count INT NOT NULL DEFAULT 0,

    product_identity_status VARCHAR(100) NULL,
    dim_product_mapping_status VARCHAR(100) NULL,
    is_product_mapped BOOLEAN NOT NULL DEFAULT FALSE,
    is_product_review_required BOOLEAN NOT NULL DEFAULT FALSE,
    include_product_in_business_views BOOLEAN NOT NULL DEFAULT TRUE,
    inventory_review_status VARCHAR(100) NULL,

    include_in_inventory_physical_views BOOLEAN NOT NULL DEFAULT TRUE,
    inventory_current_status VARCHAR(100) NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uq_inventory_current_product_location (
        snapshot_date_key,
        product_analytical_key,
        source_location_id
    ),

    KEY idx_inventory_current_product (
        product_analytical_key
    ),

    KEY idx_inventory_current_location (
        source_location_id
    ),

    KEY idx_inventory_current_snapshot_date (
        snapshot_date_key
    ),

    KEY idx_inventory_current_company_status (
        company_mapping_status
    )
);
```

---

## Build Logic

Recommended build script:

```text
scripts/build_analytics_inventory_current_product_location.py
```

Recommended steps:

```text
1. Confirm vw_inventory_physical_snapshot exists.
2. Identify current_snapshot_loaded_at = MAX(etl_loaded_at).
3. Drop and recreate analytics_inventory_current_product_location.
4. Insert aggregated rows from vw_inventory_physical_snapshot for the current snapshot only.
5. Group by product_analytical_key and source_location_id, preserving descriptive fields.
6. Calculate current_stock_qty = SUM(stock_qty).
7. Calculate source_row_count = COUNT(1).
8. Set inventory_current_status based on current_stock_qty.
9. Print build summary.
```

Recommended insert logic:

```sql
INSERT INTO analytics_inventory_current_product_location (
    snapshot_date,
    snapshot_date_key,
    current_snapshot_loaded_at,
    product_analytical_key,
    odoo_product_id,
    odoo_product_name,
    product_code,
    wansoft_code,
    wansoft_product_name,
    wansoft_department,
    source_location_id,
    location_name,
    normalized_location_name,
    location_usage_type,
    company_source_key,
    company_mapping_status,
    current_stock_qty,
    source_row_count,
    product_identity_status,
    dim_product_mapping_status,
    is_product_mapped,
    is_product_review_required,
    include_product_in_business_views,
    inventory_review_status,
    include_in_inventory_physical_views,
    inventory_current_status
)
SELECT
    MAX(snapshot_date) AS snapshot_date,
    snapshot_date_key,
    MAX(etl_loaded_at) AS current_snapshot_loaded_at,
    product_analytical_key,
    MAX(odoo_product_id) AS odoo_product_id,
    MAX(odoo_product_name) AS odoo_product_name,
    MAX(product_code) AS product_code,
    MAX(wansoft_code) AS wansoft_code,
    MAX(wansoft_product_name) AS wansoft_product_name,
    MAX(wansoft_department) AS wansoft_department,
    source_location_id,
    MAX(location_name) AS location_name,
    MAX(normalized_location_name) AS normalized_location_name,
    MAX(location_usage_type) AS location_usage_type,
    MAX(company_source_key) AS company_source_key,
    MAX(company_mapping_status) AS company_mapping_status,
    SUM(stock_qty) AS current_stock_qty,
    COUNT(1) AS source_row_count,
    MAX(product_identity_status) AS product_identity_status,
    MAX(dim_product_mapping_status) AS dim_product_mapping_status,
    MAX(is_product_mapped) AS is_product_mapped,
    MAX(is_product_review_required) AS is_product_review_required,
    MAX(include_product_in_business_views) AS include_product_in_business_views,
    MAX(inventory_review_status) AS inventory_review_status,
    TRUE AS include_in_inventory_physical_views,
    CASE
        WHEN SUM(stock_qty) > 0 THEN 'positive_stock'
        WHEN SUM(stock_qty) = 0 THEN 'zero_stock'
        WHEN SUM(stock_qty) < 0 THEN 'negative_stock_review_required'
        ELSE 'unknown'
    END AS inventory_current_status
FROM vw_inventory_physical_snapshot
WHERE etl_loaded_at = (
    SELECT MAX(etl_loaded_at)
    FROM vw_inventory_physical_snapshot
)
GROUP BY
    snapshot_date_key,
    product_analytical_key,
    source_location_id;
```

---

## Validation Requirements

Recommended validation script:

```text
scripts/validate_analytics_inventory_current_product_location.py
```

Validation checks:

```text
analytics_inventory_current_product_location exists
source view vw_inventory_physical_snapshot exists
current snapshot loaded_at is detected
aggregate row count is greater than zero
unique grain is respected
stock_qty reconciles to current physical source snapshot
all rows have location_usage_type = internal_or_unknown
all rows have include_in_inventory_physical_views = true
no rows have product_analytical_key null
no rows are product_review_required
no rows have inventory_review_status other than ok
no negative current_stock_qty rows unless explicitly reviewed
company_source_key remains null or governed, never inferred from location_name
```

---

## Reconciliation Queries

### Source current snapshot summary

```sql
SELECT
    MAX(etl_loaded_at) AS current_snapshot_loaded_at,
    COUNT(1) AS source_rows,
    COALESCE(SUM(stock_qty), 0) AS source_stock_qty
FROM vw_inventory_physical_snapshot
WHERE etl_loaded_at = (
    SELECT MAX(etl_loaded_at)
    FROM vw_inventory_physical_snapshot
);
```

---

### Target aggregate summary

```sql
SELECT
    MAX(current_snapshot_loaded_at) AS current_snapshot_loaded_at,
    COUNT(1) AS aggregate_rows,
    COALESCE(SUM(current_stock_qty), 0) AS aggregate_stock_qty
FROM analytics_inventory_current_product_location;
```

Expected reconciliation:

```text
source_stock_qty = aggregate_stock_qty
```

---

### Grain uniqueness

```sql
SELECT
    snapshot_date_key,
    product_analytical_key,
    source_location_id,
    COUNT(1) AS total_rows
FROM analytics_inventory_current_product_location
GROUP BY
    snapshot_date_key,
    product_analytical_key,
    source_location_id
HAVING COUNT(1) > 1;
```

Expected result:

```text
0 rows
```

---

### Location policy validation

```sql
SELECT
    location_usage_type,
    COUNT(1) AS total_rows
FROM analytics_inventory_current_product_location
GROUP BY location_usage_type;
```

Expected result:

```text
Only internal_or_unknown
```

---

### Current stock status distribution

```sql
SELECT
    inventory_current_status,
    COUNT(1) AS total_rows,
    COALESCE(SUM(current_stock_qty), 0) AS total_stock_qty
FROM analytics_inventory_current_product_location
GROUP BY inventory_current_status
ORDER BY inventory_current_status;
```

Expected first-version interpretation:

```text
positive_stock rows are business-ready.
zero_stock rows are valid but may be omitted from some downstream reports.
negative_stock_review_required should be zero based on current physical view validation, but the validator should still check it.
```

---

## Expected Result Based on Current Physical View

The latest validated physical view had:

```text
total_rows: 424
negative_rows: 0
zero_rows: 1
positive_rows: 423
total_stock_qty: 20430.0700
```

Therefore, the first implementation of `analytics_inventory_current_product_location` should reconcile to:

```text
total_stock_qty: 20430.0700
negative_stock_qty: 0.0000
```

The aggregate row count may be less than or equal to 424 because multiple source rows can collapse into the same product-location grain.

---

## Known Limitations

### No company-level reporting yet

This table does not solve company or branch mapping.

Reason:

```text
source_location_id and location_name are not yet governed company identifiers.
```

Future requirement:

```text
dim_inventory_location
```

---

### No valuation yet

This table only aggregates quantities.

It does not include:

```text
unit_cost
stock_value
inventory_value
valuation_layer_amount
```

Future valuation work must identify and reconcile a valuation source before adding monetary fields.

---

### Current snapshot semantics depend on etl_loaded_at

This table treats the maximum `etl_loaded_at` as current.

If a future snapshot execution produces multiple loaded timestamps for the same business snapshot, a governed `snapshot_batch_id` or `snapshot_date` policy may be needed.

---

### Product mapping sanity remains a separate issue

Step 18.4 showed visually suspicious Odoo/Wansoft product-name pairings in negative diagnostic output.

This table does not resolve those mappings.

Product mapping sanity should remain a separate validation/governance step.

---

## Acceptance Criteria

Step 18.8 is complete when this design defines:

```text
target object name
source view
grain
current snapshot rule
schema
build logic
validation requirements
reconciliation queries
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
Paso 18.9 - Implementar analytics_inventory_current_product_location
```

Purpose:

```text
Create and validate the first current physical inventory aggregate by product and source location using vw_inventory_physical_snapshot.
```
