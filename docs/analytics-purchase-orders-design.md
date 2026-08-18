# analytics_purchase_orders Design and Closeout

## Purpose

This document defines and closes the implementation of `analytics_purchase_orders`, the order-level analytical purchase fact table of the unified MySQL analytical layer.

The purpose of this table is to expose purchase order header-level information derived from the validated purchase line analytical fact.

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

## Current Status

Current implementation status:

```text
scripts/build_analytics_purchase_orders.py created
scripts/validate_analytics_purchase_orders.py created
analytics_purchase_orders table created in MySQL
build completed successfully
validation completed successfully
order-level row count reconciles to analytics_purchase_order_lines
line counts reconcile to analytics_purchase_order_lines
business line counts reconcile to analytics_purchase_order_lines
excluded line counts reconcile to analytics_purchase_order_lines
price totals reconcile exactly to analytics_purchase_order_lines
company foreign key valid
date foreign key valid
vendor foreign key valid
excluded orders have exclusion reason
source system distribution reconciles
business inclusion distribution available
order review status distribution available
```

Current result:

```text
BUILD RESULT: COMPLETED
VALIDATION RESULT: PASSED
```

---

## Implementation Summary

### Build Command

```bash
python -m scripts.build_analytics_purchase_orders
```

### Build Result

Latest validated build result:

```text
ANALYTICS PURCHASE ORDERS BUILD SUMMARY

table: analytics_purchase_orders
total_orders_prepared: 145876
include_in_business_views: 143188
excluded_from_business_views: 2688
review_required_orders: 26497
no_business_line_orders: 2688
inconsistent_company_orders: 0
inconsistent_date_orders: 0
inconsistent_vendor_orders: 0
total_line_count: 749932
total_business_line_count: 676186
total_excluded_line_count: 73746

BUILD RESULT: COMPLETED
```

---

### Validation Command

```bash
python -m scripts.validate_analytics_purchase_orders
```

### Validation Result

Latest validated result:

```text
total_validations: 14
passed: 14
failed: 0

VALIDATION RESULT: PASSED
```

Validated checks:

```text
analytics_purchase_orders_exists: PASS
row_count_matches_order_groups: PASS
source_order_identity_unique: PASS
line_count_reconciles: PASS
business_line_count_reconciles: PASS
excluded_line_count_reconciles: PASS
price_total_reconciles_with_lines: PASS
company_fk_valid: PASS
date_fk_valid: PASS
vendor_fk_valid: PASS
excluded_orders_have_reason: PASS
source_system_distribution_reconciles: PASS
business_inclusion_distribution_available: PASS
order_review_status_distribution_available: PASS
```

---

## Table Purpose

`analytics_purchase_orders` answers these questions:

```text
How many purchase orders exist in the analytical layer?
Which source system produced the purchase order?
Which company owns the order?
Which vendor is associated with the order?
What is the order date?
How many lines belong to the order?
How many lines are ready for business-facing analysis?
How many lines are excluded from business-facing analysis?
Does the order contain review-required lines?
Does the order contain internal vendor lines?
Does the order contain product governance issues?
Does the order reconcile financially to the detailed purchase line fact?
```

This table is the order-level companion to:

```text
analytics_purchase_order_lines
```

---

## Grain

The grain of the table is:

```text
1 row = 1 source purchase order group
```

Current source order identity:

```text
source_system + source_order_id
```

If a source order id is missing, the build uses a technical source order key based on the canonical purchase order line id.

This preserves all source lines while avoiding loss of records.

---

## Source Table

Primary source:

```text
analytics_purchase_order_lines
```

This is intentional.

Reason:

```text
analytics_purchase_order_lines is already validated against canonical_purchase_order_line_snapshot.
analytics_purchase_order_lines already contains dimension joins, business inclusion flags, product review flags, vendor flags and exclusion reasons.
analytics_purchase_orders should aggregate the validated line fact, not reimplement line-level business logic directly from canonical tables.
```

---

## Relationship to analytics_purchase_order_lines

Relationship:

```text
analytics_purchase_orders.source_system + analytics_purchase_orders.source_order_id
    represents grouped lines from analytics_purchase_order_lines.source_system + analytics_purchase_order_lines.source_order_id
```

Validated reconciliation:

```text
analytics_purchase_order_lines rows: 749932
analytics_purchase_orders summed line_count: 749932
```

Validation status:

```text
line_count_reconciles: PASS
```

---

## Current Row Counts

Current order count:

```text
145876 purchase orders
```

Business inclusion distribution:

```text
include_in_business_views = 1: 143188 orders
include_in_business_views = 0: 2688 orders
```

Interpretation:

```text
143188 orders have at least one line ready for default business-facing analysis and no header-level inconsistencies.
2688 orders have no business-ready lines and are excluded from default business-facing outputs.
```

---

## Review Status Counts

Current order review status distribution:

```text
ok: 119379 orders
has_review_required_lines: 26497 orders
```

Interpretation:

```text
119379 orders have no review-required lines.
26497 orders contain at least one review-required line.
```

Important note:

```text
An order can remain included in business views even if it has some review-required lines, as long as it also has valid business-ready lines and no order-level inconsistency.
```

---

## Excluded Orders

Current excluded order count:

```text
2688 orders
```

Current main exclusion reason:

```text
no_business_line_orders: 2688
```

Meaning:

```text
These orders contain no lines marked as include_in_business_views = true in analytics_purchase_order_lines.
```

Validation status:

```text
excluded_orders_have_reason: PASS
```

---

## Order-Level Consistency Checks

The build checks whether a source order has inconsistent header-level values.

Current results:

```text
inconsistent_company_orders: 0
inconsistent_date_orders: 0
inconsistent_vendor_orders: 0
```

Interpretation:

```text
No source order group has multiple company_source_key values.
No source order group has multiple order_date_key values.
No source order group has multiple vendor_analytical_key values.
```

This is a strong consistency result for the order-level analytical fact.

---

## Line Count Reconciliation

Validated line reconciliation:

```text
line_fact_rows: 749932
order_fact_line_count: 749932
```

Validation status:

```text
line_count_reconciles: PASS
```

---

## Business Line Reconciliation

Validated business line reconciliation:

```text
business_line_rows: 676186
order_business_line_count: 676186
```

Validation status:

```text
business_line_count_reconciles: PASS
```

---

## Excluded Line Reconciliation

Validated excluded line reconciliation:

```text
excluded_line_rows: 73746
order_excluded_line_count: 73746
```

Validation status:

```text
excluded_line_count_reconciles: PASS
```

---

## Amount Reconciliation

Validated amount reconciliation:

```text
line_price_total: 1034075208.2566
order_price_total: 1034075208.2566
difference: 0.0000
tolerance: 103407.52082566
```

Validation status:

```text
price_total_reconciles_with_lines: PASS
```

Interpretation:

```text
analytics_purchase_orders reconciles exactly to analytics_purchase_order_lines for price_total.
```

Because `analytics_purchase_order_lines` already reconciles exactly to `canonical_purchase_order_line_snapshot`, the validated reconciliation chain is:

```text
canonical_purchase_order_line_snapshot
-> analytics_purchase_order_lines
-> analytics_purchase_orders
```

without monetary loss.

---

## Dimension Relationships

### Company

Relationship:

```text
analytics_purchase_orders.company_source_key
    -> dim_company_analytical.company_source_key
```

Validation result:

```text
company_fk_valid: PASS
orphan_company_orders: 0
```

---

### Time

Relationship:

```text
analytics_purchase_orders.order_date_key
    -> dim_time.date_key
```

Validation result:

```text
date_fk_valid: PASS
orphan_date_orders: 0
```

---

### Vendor

Relationship:

```text
analytics_purchase_orders.vendor_analytical_key
    -> dim_vendor.vendor_analytical_key
```

Validation result:

```text
vendor_fk_valid: PASS
orphan_vendor_orders: 0
```

---

## Business Inclusion Rule

The current order-level business inclusion rule is:

```text
include_in_business_views = true when:
    the order has at least one business-ready line
    the order does not have inconsistent company values
    the order does not have inconsistent order date values
    the order does not have inconsistent vendor values
    the order has a valid source_order_id
```

If the order has no business-ready lines:

```text
include_in_business_views = false
exclude_reason includes no_business_lines
```

If an order-level inconsistency is detected:

```text
include_in_business_views = false
exclude_reason includes the detected inconsistency
order_review_status = review_required
```

---

## Important Distinction Between Order Inclusion and Line Review

An order can have:

```text
order_review_status = has_review_required_lines
include_in_business_views = true
```

This means:

```text
Some lines on the order require review, but the order also contains valid business-ready lines.
```

This is intentional.

Reason:

```text
The order-level table summarizes the full order while preserving line-level governance through counts.
```

Relevant counts:

```text
review_required_orders: 26497
excluded_from_business_views: 2688
```

These two counts are not expected to match.

---

## Current Scripts

### Build Script

```text
scripts/build_analytics_purchase_orders.py
```

Current behavior:

```text
uses analytics_purchase_order_lines as source
aggregates by source_system and source_order_id
uses INSERT INTO SELECT to aggregate inside MySQL
sets session timeouts before running large aggregation
calculates line counts and amount totals
calculates business line and excluded line counts
detects inconsistent company, order date and vendor values
sets include_in_business_views at order level
sets exclude_reason at order level
sets order_review_status at order level
prints build summary
```

Implementation note:

```text
The first implementation attempted to fetch all grouped results into Python and failed with Lost connection to MySQL server during query.
The corrected implementation performs aggregation inside MySQL using INSERT INTO SELECT.
```

---

### Validation Script

```text
scripts/validate_analytics_purchase_orders.py
```

Current validations:

```text
analytics_purchase_orders_exists
row_count_matches_order_groups
source_order_identity_unique
line_count_reconciles
business_line_count_reconciles
excluded_line_count_reconciles
price_total_reconciles_with_lines
company_fk_valid
date_fk_valid
vendor_fk_valid
excluded_orders_have_reason
source_system_distribution_reconciles
business_inclusion_distribution_available
order_review_status_distribution_available
```

---

## Known Technical Issue Resolved

Initial failure:

```text
BUILD RESULT: FAILED
error: 2013 (HY000): Lost connection to MySQL server during query
```

Cause:

```text
The original build used a large GROUP BY query and fetched the grouped result set into Python.
The query was too heavy for the connection/session behavior.
```

Resolution:

```text
The build was rewritten to use INSERT INTO SELECT.
The aggregation now runs inside MySQL.
Session timeout settings are applied before the build.
```

Final result:

```text
BUILD RESULT: COMPLETED
VALIDATION RESULT: PASSED
```

---

## Validation Query Examples

### Order Count

```sql
SELECT
    COUNT(1) AS total_orders
FROM analytics_purchase_orders;
```

Expected current result:

```text
145876
```

---

### Business Inclusion Distribution

```sql
SELECT
    include_in_business_views,
    COUNT(1) AS total_orders
FROM analytics_purchase_orders
GROUP BY include_in_business_views
ORDER BY include_in_business_views;
```

Expected current result:

```text
include_in_business_views = 0: 2688
include_in_business_views = 1: 143188
```

---

### Order Review Status Distribution

```sql
SELECT
    order_review_status,
    COUNT(1) AS total_orders
FROM analytics_purchase_orders
GROUP BY order_review_status
ORDER BY order_review_status;
```

Expected current result:

```text
has_review_required_lines: 26497
ok: 119379
```

---

### Line Count Reconciliation

```sql
SELECT
    (SELECT COUNT(1) FROM analytics_purchase_order_lines) AS line_fact_rows,
    (SELECT COALESCE(SUM(line_count), 0) FROM analytics_purchase_orders) AS order_fact_line_count;
```

Expected current result:

```text
line_fact_rows = 749932
order_fact_line_count = 749932
```

---

### Price Total Reconciliation

```sql
SELECT
    (SELECT COALESCE(SUM(price_total), 0) FROM analytics_purchase_order_lines) AS line_price_total,
    (SELECT COALESCE(SUM(price_total_total), 0) FROM analytics_purchase_orders) AS order_price_total;
```

Expected current result:

```text
line_price_total = 1034075208.2566
order_price_total = 1034075208.2566
```

---

## Current Known Decisions

### Use analytics_purchase_order_lines as source

Decision:

```text
analytics_purchase_orders is derived from analytics_purchase_order_lines.
```

Reason:

```text
The line fact already contains validated dimensions, exclusion logic and product governance flags.
The order fact should summarize the validated analytical line fact.
```

---

### Preserve excluded line counts

Decision:

```text
Excluded lines are counted at the order level.
```

Reason:

```text
This allows the order-level fact to show both business-ready and non-business-ready line composition.
```

---

### Include orders with partial review issues

Decision:

```text
Orders with at least one business-ready line remain included unless they have order-level inconsistencies.
```

Reason:

```text
Line-level exclusion should not automatically exclude a whole order if the order still has valid business-ready lines.
```

---

## Current Known Limitations

### Order source id dependency

The current grain depends on:

```text
source_system + source_order_id
```

If source order id quality changes upstream, the order aggregation may need adjustment.

---

### Order-level source fields use representative values

For fields such as:

```text
company_source_key
order_date_key
vendor_analytical_key
```

the build uses representative values from grouped lines and validates consistency through distinct counts.

Current consistency results are clean:

```text
inconsistent_company_orders: 0
inconsistent_date_orders: 0
inconsistent_vendor_orders: 0
```

---

### Product details remain line-grain

`analytics_purchase_orders` does not contain one product per order.

Product-level analysis belongs to:

```text
analytics_purchase_order_lines
```

The order table only stores product-related diagnostic counts:

```text
review_required_product_line_count
orphan_product_line_count
```

---

## Step 17.23 Closeout

Step 17.23 is complete when:

```text
scripts/build_analytics_purchase_orders.py created
scripts/validate_analytics_purchase_orders.py created
both scripts compile
analytics_purchase_orders table created
build completed successfully
validation passed
145876 orders generated
749932 lines reconciled
676186 business lines reconciled
73746 excluded lines reconciled
price_total reconciled exactly
company FK valid
date FK valid
vendor FK valid
source order identity unique
```

Current status:

```text
complete
```

---

## Step 17.24 Closeout

This documentation step is complete when:

```text
analytics_purchase_orders implementation result documented
actual build result documented
actual validation result documented
order count documented
business inclusion distribution documented
review status distribution documented
line reconciliation documented
amount reconciliation documented
technical issue and fix documented
next analytical step prepared
```

Current status:

```text
complete
```

---

## Recommended Next Step

The purchase analytical layer now has:

```text
analytics_purchase_order_lines
analytics_purchase_orders
```

Recommended next step:

```text
Paso 17.25 - Diseñar analytics_purchase_daily_company_product
```

Reason:

```text
A daily company-product aggregate can support faster analytical consumption from purchases.
It can summarize purchase lines by company, date and product.
It can reuse dim_company_analytical, dim_time and dim_product.
It can preserve business inclusion and review-required product flags.
```
