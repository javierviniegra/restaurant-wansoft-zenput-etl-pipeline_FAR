# analytics_purchase_daily_company_product Design and Closeout

## Purpose

This document defines and closes the implementation of `analytics_purchase_daily_company_product`, the first purchase aggregate fact table of the unified MySQL analytical layer.

The purpose of this table is to summarize purchase order line activity by date, company and product, using the validated line-level analytical fact as its source.

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
scripts/build_analytics_purchase_daily_company_product.py created
scripts/validate_analytics_purchase_daily_company_product.py created
analytics_purchase_daily_company_product table created in MySQL
build completed successfully
validation completed successfully
grain uniqueness validated
line count reconciled to analytics_purchase_order_lines
business line count reconciled to analytics_purchase_order_lines
excluded line count reconciled to analytics_purchase_order_lines
price_total reconciled to analytics_purchase_order_lines
business price_total reconciled to included purchase lines
excluded price_total reconciled to excluded purchase lines
company foreign key valid
date foreign key valid
product foreign key valid when populated
excluded rows have exclusion reason
business inclusion distribution available
aggregate review status distribution available
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
python -m scripts.build_analytics_purchase_daily_company_product
```

### Build Result

Latest validated build result:

```text
ANALYTICS PURCHASE DAILY COMPANY PRODUCT BUILD SUMMARY

table: analytics_purchase_daily_company_product
total_rows_prepared: 626258
include_in_business_views: 595831
excluded_from_business_views: 30427
total_line_count: 749932
total_business_line_count: 676186
total_excluded_line_count: 73746
total_review_required_line_count: 55914
total_internal_vendor_line_count: 20061
total_review_required_product_line_count: 4936
total_orphan_product_line_count: 50978
total_price_total: 1034075208.2566
total_business_price_total: 989935685.4550
total_excluded_price_total: 44139522.8016

BUILD RESULT: COMPLETED
```

---

### Validation Command

```bash
python -m scripts.validate_analytics_purchase_daily_company_product
```

### Validation Result

Latest validated result:

```text
total_validations: 15
passed: 15
failed: 0

VALIDATION RESULT: PASSED
```

Validated checks:

```text
analytics_purchase_daily_company_product_exists: PASS
analytics_purchase_daily_company_product_has_rows: PASS
daily_company_product_grain_unique: PASS
line_count_reconciles: PASS
business_line_count_reconciles: PASS
excluded_line_count_reconciles: PASS
price_total_reconciles: PASS
business_price_total_reconciles: PASS
excluded_price_total_reconciles: PASS
company_fk_valid: PASS
date_fk_valid: PASS
product_fk_valid: PASS
excluded_rows_have_reason: PASS
business_inclusion_distribution_available: PASS
aggregate_review_status_distribution_available: PASS
```

---

## Table Purpose

`analytics_purchase_daily_company_product` answers these questions:

```text
How much was purchased per company, day and product?
How many purchase lines support each daily company-product total?
How much quantity was purchased, received and invoiced?
How much purchase amount is business-ready?
How much purchase amount is excluded due to governance rules?
Which company-product-day combinations have review-required activity?
Which company-product-day combinations contain orphan product activity?
Which activity can be safely consumed by business-facing analytical views?
```

This table is an aggregate companion to:

```text
analytics_purchase_order_lines
```

---

## Grain

The grain of the table is:

```text
1 row = 1 company_source_key + 1 order_date_key + 1 product_analytical_group_key + 1 source_system
```

The implementation uses:

```text
product_analytical_group_key = product_analytical_key when available
product_analytical_group_key = 0 when product_analytical_key is null
```

This is intentional.

Reason:

```text
Some purchase lines do not yet have product_analytical_key.
Those lines must remain visible and reconcilable.
Using product_analytical_group_key = 0 allows orphan product activity to be grouped deterministically.
```

Validation status:

```text
daily_company_product_grain_unique: PASS
```

---

## Source Table

Primary source:

```text
analytics_purchase_order_lines
```

This is intentional.

Reason:

```text
analytics_purchase_order_lines already preserves all canonical purchase lines.
analytics_purchase_order_lines already joins company, time, vendor and product dimensions.
analytics_purchase_order_lines already contains business inclusion flags and exclusion reasons.
analytics_purchase_order_lines already reconciles to canonical_purchase_order_line_snapshot.
```

The aggregate does not go back to canonical purchase tables.

---

## Current Row Counts

Current aggregate row count:

```text
626258 daily company-product-source rows
```

Business inclusion distribution:

```text
include_in_business_views = 1: 595831 rows
include_in_business_views = 0: 30427 rows
```

Interpretation:

```text
595831 aggregate rows are ready for default business-facing analytical usage.
30427 aggregate rows are preserved but excluded from default business-facing views.
```

---

## Aggregate Review Status Counts

Current aggregate review status distribution:

```text
has_review_required_lines: 4453 rows
no_business_lines: 15478 rows
ok: 595831 rows
orphan_product: 10496 rows
```

Interpretation:

```text
595831 rows are clean under current governance rules.
4453 rows contain review-required lines.
10496 rows represent orphan product activity.
15478 rows contain no business-ready lines.
```

---

## Reconciliation Results

### Total Line Reconciliation

Validated result:

```text
source_line_count: 749932
aggregate_line_count: 749932
```

Validation status:

```text
line_count_reconciles: PASS
```

---

### Business Line Reconciliation

Validated result:

```text
source_business_line_count: 676186
aggregate_business_line_count: 676186
```

Validation status:

```text
business_line_count_reconciles: PASS
```

---

### Excluded Line Reconciliation

Validated result:

```text
source_excluded_line_count: 73746
aggregate_excluded_line_count: 73746
```

Validation status:

```text
excluded_line_count_reconciles: PASS
```

---

### Total Amount Reconciliation

Validated result:

```text
source_total: 1034075208.2566
aggregate_total: 1034075208.2566
difference: 0.0000
tolerance: 103407.52082566
```

Validation status:

```text
price_total_reconciles: PASS
```

---

### Business Amount Reconciliation

Validated result:

```text
source_total: 989935685.455
aggregate_total: 989935685.455
difference: 0.000
tolerance: 98993.5685455
```

Validation status:

```text
business_price_total_reconciles: PASS
```

---

### Excluded Amount Reconciliation

Validated result:

```text
source_total: 44139522.8016
aggregate_total: 44139522.8016
difference: 0.0000
tolerance: 4413.95228016
```

Validation status:

```text
excluded_price_total_reconciles: PASS
```

---

## Reconciliation Chain

The validated purchase reconciliation chain is now:

```text
canonical_purchase_order_line_snapshot
-> analytics_purchase_order_lines
-> analytics_purchase_orders
-> analytics_purchase_daily_company_product
```

The shared amount total remains:

```text
1034075208.2566
```

This confirms that the detail, order-level fact and daily company-product aggregate reconcile to the same purchase amount base.

---

## Dimension Relationships

### Company

Relationship:

```text
analytics_purchase_daily_company_product.company_source_key
    -> dim_company_analytical.company_source_key
```

Validation result:

```text
company_fk_valid: PASS
orphan_company_rows: 0
```

---

### Time

Relationship:

```text
analytics_purchase_daily_company_product.order_date_key
    -> dim_time.date_key
```

Validation result:

```text
date_fk_valid: PASS
orphan_date_rows: 0
```

---

### Product

Relationship:

```text
analytics_purchase_daily_company_product.product_analytical_key
    -> dim_product.product_analytical_key
```

Validation result:

```text
product_fk_valid: PASS
orphan_product_rows: 0
```

Important note:

```text
product_fk_valid means every populated product_analytical_key points to dim_product.
It does not mean every row has a populated product_analytical_key.
Rows without product_analytical_key are grouped under product_analytical_group_key = 0.
```

---

## Business Inclusion Rule

The current aggregate-level business inclusion rule is:

```text
include_in_business_views = true when:
    business_line_count > 0
    include_product_in_business_views = true
```

If no business-ready lines exist:

```text
include_in_business_views = false
exclude_reason includes no_business_lines
```

If product requires review:

```text
include_in_business_views = false or diagnostic
exclude_reason may include review_required_product
```

If product is not available as analytical product:

```text
aggregate_review_status = orphan_product
product_analytical_group_key = 0
```

---

## Exclusion Reasons

Excluded aggregate rows must have an `exclude_reason`.

Validation result:

```text
excluded_rows_have_reason: PASS
bad_rows: 0
```

Possible exclusion reasons include:

```text
no_business_lines
orphan_product
review_required_product
product_excluded
```

Multiple reasons may appear concatenated with:

```text
|
```

---

## Product Orphan Handling

The line fact currently includes product activity without populated `product_analytical_key`.

This aggregate handles such activity through:

```text
product_analytical_group_key = 0
```

Current build result:

```text
total_orphan_product_line_count: 50978
```

Current aggregate review status:

```text
orphan_product: 10496 aggregate rows
```

Interpretation:

```text
50978 purchase lines without product_analytical_key are preserved and grouped into 10496 daily company-product-source aggregate rows.
```

This preserves reconciliation while keeping product governance gaps visible.

---

## Internal Vendor Activity

Current build result:

```text
total_internal_vendor_line_count: 20061
```

Interpretation:

```text
Internal vendor activity remains visible in the aggregate.
It contributes to diagnostic counts and excluded totals where applicable.
```

---

## Review-Required Product Activity

Current build result:

```text
total_review_required_product_line_count: 4936
```

Interpretation:

```text
Review-required product activity remains visible in the aggregate.
It does not silently enter business-ready totals unless the line is business-ready under current rules.
```

---

## Current Scripts

### Build Script

```text
scripts/build_analytics_purchase_daily_company_product.py
```

Current behavior:

```text
uses analytics_purchase_order_lines as source
recreates analytics_purchase_daily_company_product
aggregates by company_source_key, order_date_key, product_analytical_group_key and source_system
preserves product_analytical_key when available
uses product_analytical_group_key = 0 for missing product keys
calculates total, business and excluded line counts
calculates review-required, internal vendor and orphan product line counts
calculates total, business and excluded quantities
calculates total, business and excluded amounts
sets include_in_business_views at aggregate level
sets exclude_reason
sets aggregate_review_status
prints build summary
```

---

### Validation Script

```text
scripts/validate_analytics_purchase_daily_company_product.py
```

Current validations:

```text
analytics_purchase_daily_company_product_exists
analytics_purchase_daily_company_product_has_rows
daily_company_product_grain_unique
line_count_reconciles
business_line_count_reconciles
excluded_line_count_reconciles
price_total_reconciles
business_price_total_reconciles
excluded_price_total_reconciles
company_fk_valid
date_fk_valid
product_fk_valid
excluded_rows_have_reason
business_inclusion_distribution_available
aggregate_review_status_distribution_available
```

---

## Validation Query Examples

### Aggregate Row Count

```sql
SELECT
    COUNT(1) AS total_rows
FROM analytics_purchase_daily_company_product;
```

Expected current result:

```text
626258
```

---

### Business Inclusion Distribution

```sql
SELECT
    include_in_business_views,
    COUNT(1) AS total_rows
FROM analytics_purchase_daily_company_product
GROUP BY include_in_business_views
ORDER BY include_in_business_views;
```

Expected current result:

```text
include_in_business_views = 0: 30427
include_in_business_views = 1: 595831
```

---

### Aggregate Review Status Distribution

```sql
SELECT
    aggregate_review_status,
    COUNT(1) AS total_rows
FROM analytics_purchase_daily_company_product
GROUP BY aggregate_review_status
ORDER BY aggregate_review_status;
```

Expected current result:

```text
has_review_required_lines: 4453
no_business_lines: 15478
ok: 595831
orphan_product: 10496
```

---

### Line Count Reconciliation

```sql
SELECT
    (SELECT COUNT(1) FROM analytics_purchase_order_lines) AS line_fact_rows,
    (SELECT COALESCE(SUM(line_count), 0) FROM analytics_purchase_daily_company_product) AS aggregate_line_count;
```

Expected current result:

```text
line_fact_rows = 749932
aggregate_line_count = 749932
```

---

### Price Total Reconciliation

```sql
SELECT
    (SELECT COALESCE(SUM(price_total), 0) FROM analytics_purchase_order_lines) AS line_price_total,
    (SELECT COALESCE(SUM(price_total_total), 0) FROM analytics_purchase_daily_company_product) AS aggregate_price_total;
```

Expected current result:

```text
line_price_total = 1034075208.2566
aggregate_price_total = 1034075208.2566
```

---

### Orphan Product Aggregate Sample

```sql
SELECT
    company_source_key,
    order_date_key,
    source_system,
    product_analytical_group_key,
    line_count,
    price_total_total,
    aggregate_review_status,
    exclude_reason
FROM analytics_purchase_daily_company_product
WHERE product_analytical_group_key = 0
ORDER BY price_total_total DESC
LIMIT 100;
```

Purpose:

```text
Review daily company-source product-orphan activity for product governance backlog.
```

---

## Current Known Decisions

### Use line fact as source

Decision:

```text
analytics_purchase_daily_company_product is derived from analytics_purchase_order_lines.
```

Reason:

```text
The line fact already contains validated business rules, product governance, company keys and date keys.
```

---

### Preserve excluded activity

Decision:

```text
Excluded lines are included in the aggregate.
```

Reason:

```text
The aggregate must reconcile to the full line fact and must preserve governance visibility.
```

---

### Product orphans use product_analytical_group_key = 0

Decision:

```text
Rows without product_analytical_key are grouped under product_analytical_group_key = 0.
```

Reason:

```text
This allows deterministic aggregation and reconciliation without inventing product identity.
```

---

### Vendor is not part of the grain

Decision:

```text
The aggregate does not include vendor_analytical_key in the grain.
```

Reason:

```text
This table is daily company-product-source grain.
Vendor-specific analysis can be designed as a separate aggregate if needed.
```

---

## Current Known Limitations

### Product details remain governed by dim_product

This aggregate does not resolve product mapping issues.

Product mapping is still governed by:

```text
dim_product
inventory_mapping_dictionary
product mapping backlog
```

---

### Product-orphan rows are diagnostic

Rows with:

```text
product_analytical_group_key = 0
```

are not business-ready product identities.

They exist for:

```text
reconciliation
data quality review
mapping backlog prioritization
```

---

### This aggregate is not a replacement for line detail

The authoritative detail table remains:

```text
analytics_purchase_order_lines
```

This aggregate is optimized for faster company-product-day analysis.

---

## Step 17.26 Closeout

Step 17.26 is complete when:

```text
scripts/build_analytics_purchase_daily_company_product.py created
scripts/validate_analytics_purchase_daily_company_product.py created
both scripts compile
analytics_purchase_daily_company_product table created
build completed successfully
validation passed
626258 aggregate rows generated
749932 source lines reconciled
676186 business lines reconciled
73746 excluded lines reconciled
total price reconciled
business price reconciled
excluded price reconciled
company FK valid
date FK valid
product FK valid when populated
grain uniqueness validated
```

Current status:

```text
complete
```

---

## Step 17.27 Closeout

This documentation step is complete when:

```text
analytics_purchase_daily_company_product implementation result documented
actual build result documented
actual validation result documented
aggregate row count documented
business inclusion distribution documented
review status distribution documented
line reconciliation documented
amount reconciliation documented
product orphan handling documented
next analytical step prepared
```

Current status:

```text
complete
```

---

## Current Analytical Purchase Layer Status

The analytical purchase layer now has:

```text
analytics_purchase_order_lines
analytics_purchase_orders
analytics_purchase_daily_company_product
```

All three analytical purchase objects reconcile by line counts and/or purchase amounts to the validated purchase line base.

---

## Recommended Next Step

Recommended next step:

```text
Paso 17.28 - Actualizar README.md y project-status-and-todo.md con cierre de compras analíticas
```

Reason:

```text
The purchase analytical layer now includes line-level, order-level and daily company-product aggregate tables.
This milestone should be reflected in the project-level documentation before moving to another analytical domain.
```
