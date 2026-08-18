# analytics_purchase_orders Design

## Purpose

This document defines the design of `analytics_purchase_orders`, the order-level analytical fact table for Purchases in the unified MySQL analytical layer.

The purpose of this table is to expose purchase order header data in a governed, validated and dimension-ready structure.

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

The project already has the shared dimensions needed to build the order-level purchase fact:

```text
dim_company_analytical
dim_time
dim_vendor
dim_product
```

The project also has the detailed purchase line fact:

```text
analytics_purchase_order_lines
```

The detailed purchase line fact is already validated with:

```text
749932 analytical purchase lines
749932 canonical purchase lines
price_total reconciled exactly
14 validations passed
0 failed validations
```

`analytics_purchase_orders` should be the order-level companion table to `analytics_purchase_order_lines`.

---

## Design Goal

`analytics_purchase_orders` should answer questions like:

```text
How many purchase orders exist?
Which company created each purchase order?
Which vendor supplied each purchase order?
What date belongs to each purchase order?
Which source system produced the order?
What is the total amount by purchase order?
How many lines belong to each purchase order?
Is the order safe for default business-facing views?
Does the order include internal vendor lines?
Does the order include review-required product lines?
Does the order contain unresolved product lines?
```

The table should provide a stable order-level analytical fact while preserving the ability to reconcile back to line-level values.

---

## Grain

The intended grain is:

```text
1 row = 1 purchase order in the canonical Purchases layer
```

Recommended canonical identity:

```text
source_system + source_order_id
```

Alternative fields to preserve:

```text
purchase_order_name
source_order_id
source_system
source_domain
```

If a canonical order snapshot already exists, the build should use its primary key.

If not, the first implementation can aggregate from:

```text
analytics_purchase_order_lines
```

using:

```text
source_system
source_order_id
purchase_order_name
company_source_key
vendor_analytical_key
order_date_key
```

---

## Source Strategy

### Preferred Source

Preferred source if available:

```text
canonical_purchase_order_snapshot
```

This source likely represents the order header grain directly.

### Fallback Source

If the canonical order snapshot is incomplete or unavailable, the initial implementation may build from:

```text
analytics_purchase_order_lines
```

Reason:

```text
analytics_purchase_order_lines is already validated against canonical_purchase_order_line_snapshot.
It preserves all lines.
It reconciles price_total exactly.
It already carries company, vendor, date and business inclusion flags.
```

### Recommended First Implementation

Recommended first implementation:

```text
Use analytics_purchase_order_lines as the primary source for analytics_purchase_orders.
```

Reason:

```text
The line fact is already validated.
Order totals can be reconciled directly by aggregating validated line values.
Business inclusion can be propagated from line-level rules.
```

---

## Target Table Name

```text
analytics_purchase_orders
```

---

## Table Classification

```text
Layer: analytical fact
Object type: analytics_
Public contract: yes
BI design: no
Source of business rules: MySQL/config/docs
```

---

## Relationship to analytics_purchase_order_lines

`analytics_purchase_orders` should reconcile to `analytics_purchase_order_lines`.

Relationship:

```text
analytics_purchase_orders.source_system
analytics_purchase_orders.source_order_id
    -> analytics_purchase_order_lines.source_system
       analytics_purchase_order_lines.source_order_id
```

Recommended checks:

```text
order line count by order
price_subtotal sum by order
price_total sum by order
business inclusion propagation
```

---

## Dimension Relationships

### Company

Join to:

```text
dim_company_analytical
```

Relationship:

```text
analytics_purchase_orders.company_source_key
    -> dim_company_analytical.company_source_key
```

Rule:

```text
Every order should have a company_source_key that exists in dim_company_analytical.
```

If the order has multiple company_source_key values across lines:

```text
mark order_review_status = review_required
include_in_business_views = false
exclude_reason includes inconsistent_company_on_order
```

---

### Time

Join to:

```text
dim_time
```

Relationship:

```text
analytics_purchase_orders.order_date_key
    -> dim_time.date_key
```

Recommended derivation:

```text
Use the minimum non-null order_date_key from lines within the order.
```

If more than one order_date_key exists for the same order:

```text
mark order_review_status = review_required
include_in_business_views = false
exclude_reason includes inconsistent_order_date_on_order
```

---

### Vendor

Join to:

```text
dim_vendor
```

Relationship:

```text
analytics_purchase_orders.vendor_analytical_key
    -> dim_vendor.vendor_analytical_key
```

Recommended derivation:

```text
Use the unique vendor_analytical_key from the order lines.
```

If more than one vendor_analytical_key exists within the same order:

```text
mark order_review_status = review_required
include_in_business_views = false
exclude_reason includes inconsistent_vendor_on_order
```

---

## Proposed Fields

### Analytical Identity Fields

```text
purchase_order_analytical_key
source_system
source_domain
source_order_id
purchase_order_name
```

---

### Company Fields

```text
company_source_key
company_analytical_key
company_id
company_name
company_migration_type
final_purchase_source_status
history_source
include_odoo_history
operational_start_date
migration_policy_source
```

---

### Time Fields

```text
order_date
order_date_key
```

Calendar attributes should be obtained by joining to:

```text
dim_time
```

---

### Vendor Fields

```text
vendor_analytical_key
vendor_id
vendor_name
normalized_vendor_name
is_internal_vendor
include_vendor_in_business_views
```

---

### Line Aggregation Fields

```text
line_count
business_line_count
excluded_line_count
review_required_line_count
internal_vendor_line_count
review_required_product_line_count
orphan_product_line_count
```

---

### Quantity and Amount Fields

```text
product_qty_total
qty_received_total
qty_invoiced_total
price_subtotal_total
price_total_total
```

These should be aggregated from:

```text
analytics_purchase_order_lines
```

Do not recalculate price totals from quantity and unit price in the first version.

---

### Source and State Fields

```text
state
canonical_loaded_at_min
canonical_loaded_at_max
```

If multiple states exist within an order, preserve a diagnostic field:

```text
state_values
```

---

### Business Inclusion Fields

```text
include_in_business_views
exclude_reason
order_review_status
```

Recommended rule:

```text
include_in_business_views = true when all required order-level dimensional relationships are valid and the order has at least one business-included line.
```

Recommended exclusion reasons:

```text
no_business_lines
internal_vendor
vendor_excluded
review_required_product
orphan_product
inconsistent_company_on_order
inconsistent_vendor_on_order
inconsistent_order_date_on_order
invalid_order_date
```

---

## Proposed Initial Schema

```sql
CREATE TABLE analytics_purchase_orders (
    purchase_order_analytical_key BIGINT AUTO_INCREMENT PRIMARY KEY,

    source_system VARCHAR(50) NOT NULL,
    source_domain VARCHAR(100) NULL,
    source_order_id VARCHAR(100) NOT NULL,
    purchase_order_name VARCHAR(255) NULL,

    company_source_key VARCHAR(255) NULL,
    company_analytical_key BIGINT NULL,
    company_id VARCHAR(100) NULL,
    company_name VARCHAR(255) NULL,
    final_purchase_source_status VARCHAR(100) NULL,
    company_migration_type VARCHAR(100) NULL,
    history_source VARCHAR(100) NULL,
    include_odoo_history BOOLEAN NULL,
    operational_start_date DATE NULL,
    migration_policy_source VARCHAR(100) NULL,

    order_date DATETIME NULL,
    order_date_key INT NULL,

    vendor_analytical_key BIGINT NULL,
    vendor_id VARCHAR(100) NULL,
    vendor_name VARCHAR(255) NULL,
    normalized_vendor_name VARCHAR(255) NULL,
    is_internal_vendor BOOLEAN NOT NULL DEFAULT FALSE,
    include_vendor_in_business_views BOOLEAN NOT NULL DEFAULT TRUE,

    line_count BIGINT NOT NULL DEFAULT 0,
    business_line_count BIGINT NOT NULL DEFAULT 0,
    excluded_line_count BIGINT NOT NULL DEFAULT 0,
    review_required_line_count BIGINT NOT NULL DEFAULT 0,
    internal_vendor_line_count BIGINT NOT NULL DEFAULT 0,
    review_required_product_line_count BIGINT NOT NULL DEFAULT 0,
    orphan_product_line_count BIGINT NOT NULL DEFAULT 0,

    product_qty_total DECIMAL(18,4) NULL,
    qty_received_total DECIMAL(18,4) NULL,
    qty_invoiced_total DECIMAL(18,4) NULL,
    price_subtotal_total DECIMAL(18,4) NULL,
    price_total_total DECIMAL(18,4) NULL,

    state_values TEXT NULL,
    canonical_loaded_at_min TIMESTAMP NULL,
    canonical_loaded_at_max TIMESTAMP NULL,

    include_in_business_views BOOLEAN NOT NULL DEFAULT TRUE,
    exclude_reason VARCHAR(500) NULL,
    order_review_status VARCHAR(100) NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uq_analytics_purchase_orders_source_order (
        source_system,
        source_order_id
    ),

    KEY idx_analytics_purchase_orders_company_date (
        company_source_key,
        order_date_key
    ),

    KEY idx_analytics_purchase_orders_vendor (
        vendor_analytical_key
    ),

    KEY idx_analytics_purchase_orders_source_system (
        source_system
    ),

    KEY idx_analytics_purchase_orders_business_views (
        include_in_business_views
    )
);
```

---

## Build Strategy

Recommended implementation script:

```text
scripts/build_analytics_purchase_orders.py
```

### Step 1: Read analytics purchase lines

Source:

```text
analytics_purchase_order_lines
```

Use all rows.

Group by:

```text
source_system
source_order_id
```

---

### Step 2: Aggregate line metrics

Aggregate:

```text
line_count
business_line_count
excluded_line_count
review_required_line_count
internal_vendor_line_count
review_required_product_line_count
orphan_product_line_count
product_qty_total
qty_received_total
qty_invoiced_total
price_subtotal_total
price_total_total
```

---

### Step 3: Derive stable order attributes

For each grouped order, derive:

```text
purchase_order_name
company_source_key
company_analytical_key
company_id
company_name
order_date
order_date_key
vendor_analytical_key
vendor_id
vendor_name
normalized_vendor_name
```

Use the value when there is exactly one distinct non-null value.

If multiple conflicting values exist, flag the order for review.

---

### Step 4: Propagate business inclusion

Recommended first rule:

```text
include_in_business_views = true when business_line_count > 0 and no order-level consistency issue exists.
```

If no business lines exist:

```text
include_in_business_views = false
exclude_reason includes no_business_lines
```

If inconsistent order-level attributes exist:

```text
include_in_business_views = false
exclude_reason includes the relevant inconsistency
order_review_status = review_required
```

---

### Step 5: Preserve review diagnostics

The order should preserve diagnostic counts from lines.

Examples:

```text
review_required_line_count
orphan_product_line_count
review_required_product_line_count
internal_vendor_line_count
excluded_line_count
```

This allows users to understand why an order is or is not business-ready.

---

## Validation Requirements

Recommended validator:

```text
scripts/validate_analytics_purchase_orders.py
```

The validator should check:

```text
table exists
row count equals distinct source_system + source_order_id from analytics_purchase_order_lines
source order identity is unique
line_count reconciles to analytics_purchase_order_lines
price_total_total reconciles to analytics_purchase_order_lines price_total
business line counts reconcile
excluded line counts reconcile
company FK is valid when populated
date FK is valid when populated
vendor FK is valid when populated
orders excluded from business views have exclude_reason
source_system distribution reconciles
```

---

## Required Reconciliation Validations

### Order Count

```sql
SELECT
    COUNT(1) AS expected_orders
FROM (
    SELECT
        source_system,
        source_order_id
    FROM analytics_purchase_order_lines
    GROUP BY
        source_system,
        source_order_id
) x;
```

Compare to:

```sql
SELECT COUNT(1) AS analytics_orders
FROM analytics_purchase_orders;
```

Expected:

```text
expected_orders = analytics_orders
```

---

### Line Count Reconciliation

```sql
SELECT
    (SELECT COUNT(1) FROM analytics_purchase_order_lines) AS line_fact_rows,
    (SELECT SUM(line_count) FROM analytics_purchase_orders) AS order_fact_line_count;
```

Expected:

```text
line_fact_rows = order_fact_line_count
```

---

### Amount Reconciliation

```sql
SELECT
    (SELECT COALESCE(SUM(price_total), 0) FROM analytics_purchase_order_lines) AS line_price_total,
    (SELECT COALESCE(SUM(price_total_total), 0) FROM analytics_purchase_orders) AS order_price_total;
```

Expected:

```text
line_price_total = order_price_total
```

Tolerance:

```text
0.01 percent
```

---

### Business Line Count Reconciliation

```sql
SELECT
    (SELECT COUNT(1) FROM analytics_purchase_order_lines WHERE include_in_business_views = TRUE) AS business_line_rows,
    (SELECT SUM(business_line_count) FROM analytics_purchase_orders) AS order_business_line_count;
```

Expected:

```text
business_line_rows = order_business_line_count
```

---

## Business Rules

### Preserve all orders

Orders should not be deleted just because their lines are excluded.

If all lines are excluded:

```text
include_in_business_views = false
exclude_reason includes no_business_lines
```

---

### Internal vendor propagation

If an order has internal vendor lines:

```text
internal_vendor_line_count > 0
```

If all business lines are excluded because of vendor rules:

```text
include_in_business_views = false
exclude_reason includes internal_vendor or vendor_excluded
```

---

### Product governance propagation

If an order has review-required product lines:

```text
review_required_product_line_count > 0
```

If all business lines are excluded because of product rules:

```text
include_in_business_views = false
exclude_reason includes review_required_product or orphan_product
```

---

### Business-ready order definition

An order is business-ready when:

```text
business_line_count > 0
company is consistent
date is consistent
vendor is consistent
no invalid required order-level dimension
```

This does not require every line to be business-ready.

Reason:

```text
A purchase order may contain some excluded lines while still having business-ready lines.
```

---

## Expected Initial Outcomes

Based on the validated line fact, the first implementation should produce:

```text
one row per distinct source_system + source_order_id
line_count sum = 749932
price_total_total sum = 1034075208.2566
business_line_count sum = 676186
excluded_line_count sum = 73746
company/date/vendor FK checks passing when populated
some orders excluded because they have no business-ready lines
some orders marked review_required because of product governance issues
```

---

## Current Known Decisions

### Build from line fact first

Decision:

```text
Build analytics_purchase_orders from analytics_purchase_order_lines in the first version.
```

Reason:

```text
The line fact is already reconciled and dimension-ready.
Aggregating from it makes validation straightforward.
```

---

### Do not recalculate totals

Decision:

```text
Aggregate line-level canonical values.
Do not recalculate totals from quantity and unit price.
```

Reason:

```text
The line fact already reconciles to canonical price_total exactly.
```

---

### Preserve partially excluded orders

Decision:

```text
Orders remain visible even if some or all lines are excluded.
```

Reason:

```text
Governance and reconciliation require full visibility.
```

---

## Deliverables for Step 17.22

This design step is complete when the project has:

```text
purpose of analytics_purchase_orders
grain
source strategy
relationship to analytics_purchase_order_lines
proposed schema
business inclusion rules
reconciliation rules
validation requirements
known decisions
```

---

## Recommended Next Step

```text
Paso 17.23 - Implementar analytics_purchase_orders
```

Suggested implementation sequence:

```text
1. Create scripts/build_analytics_purchase_orders.py.
2. Create scripts/validate_analytics_purchase_orders.py.
3. Aggregate from analytics_purchase_order_lines.
4. Derive one row per source_system + source_order_id.
5. Reconcile line counts and amount totals.
6. Validate dimensional references.
7. Validate business inclusion and exclusion reasons.
```
