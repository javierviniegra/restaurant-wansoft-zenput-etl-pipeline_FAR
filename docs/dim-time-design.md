# dim_time Design and Closeout

## Purpose

This document defines and closes the initial implementation of `dim_time`, the shared analytical calendar dimension for the Wansoft + Odoo + Zenput Data Warehouse and ETL Pipeline project.

The purpose of this dimension is to provide one governed calendar row per date, so all analytical tables can use a consistent date reference.

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
scripts/build_dim_time.py created
scripts/validate_dim_time.py created
dim_time table created in MySQL
build completed successfully
validation completed successfully
date range validated
date_key uniqueness validated
calendar_date uniqueness validated
weekend flags validated
month boundary flags validated
quarter boundary flags validated
year boundary flags validated
ISO week fields validated
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
python -m scripts.build_dim_time
```

## Build Result

Latest validated build result:

```text
DIM TIME BUILD SUMMARY

table: dim_time
start_date: 2020-01-01
end_date: 2035-12-31
total_rows_prepared: 5844
min_date_key: 20200101
max_date_key: 20351231

BUILD RESULT: COMPLETED
```

---

## Validation Command

```bash
python -m scripts.validate_dim_time
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
dim_time_exists: PASS
dim_time_row_count: PASS
dim_time_min_max_dates: PASS
date_key_unique: PASS
calendar_date_unique: PASS
calendar_date_not_null: PASS
date_key_matches_calendar_date: PASS
weekend_flags_valid: PASS
month_boundary_flags_valid: PASS
quarter_boundary_flags_valid: PASS
year_boundary_flags_valid: PASS
iso_week_fields_valid: PASS
```

---

# Table Purpose

`dim_time` answers these questions:

```text
What is the standard date_key for a calendar date?
What year, quarter, month, week and day does a date belong to?
Is the date a weekend?
Is the date the start or end of a month?
Is the date the start or end of a quarter?
Is the date the start or end of a year?
What ISO week and ISO year does the date belong to?
```

This dimension is the calendar anchor for:

```text
analytics_purchase_orders
analytics_purchase_order_lines
analytics_inventory_snapshot
analytics_zenput_submissions
analytics_zenput_tasks
future analytics_sales_*
future aggregate tables
future temporal validation scripts
```

---

# Grain

The grain of the table is:

```text
1 row = 1 calendar date
```

Each day appears exactly once.

Example:

```text
calendar_date = 2026-08-05
date_key = 20260805
```

---

# Date Range

The implemented date range is:

```text
2020-01-01 to 2035-12-31
```

The range is inclusive.

Current validated row count:

```text
5844 rows
```

Reason for this range:

```text
Covers historical Wansoft data.
Covers current Odoo data.
Covers current Zenput data.
Covers current migration windows.
Covers future rollout planning.
Avoids frequent calendar extension.
```

---

# Primary Key and Natural Key

## Primary Key

```text
date_key
```

Format:

```text
YYYYMMDD
```

Example:

```text
20260805
```

## Natural Date

```text
calendar_date
```

Type:

```text
DATE
```

Validation status:

```text
date_key_unique: PASS
calendar_date_unique: PASS
date_key_matches_calendar_date: PASS
```

---

# Final Field Groups

## Core Date Fields

```text
date_key
calendar_date
```

---

## Year Fields

```text
year
year_start_date
year_end_date
is_year_start
is_year_end
```

---

## Quarter Fields

```text
quarter_number
quarter_name
year_quarter
quarter_start_date
quarter_end_date
is_quarter_start
is_quarter_end
```

---

## Month Fields

```text
month_number
month_name
month_short_name
year_month_label
month_start_date
month_end_date
is_month_start
is_month_end
```

Important implementation note:

```text
The original proposed field year_month was renamed to year_month_label.
```

Reason:

```text
year_month can conflict with MariaDB / MySQL syntax or reserved interval terminology.
year_month_label avoids SQL parser ambiguity.
```

---

## Week Fields

```text
week_of_year
iso_week_of_year
iso_year
week_start_date
week_end_date
is_week_start
is_week_end
```

Current convention:

```text
ISO week starts on Monday.
```

---

## Day Fields

```text
day_of_month
day_of_year
day_of_week_number
day_of_week_name
day_of_week_short_name
is_weekend
```

Day-of-week convention:

```text
1 = Monday
2 = Tuesday
3 = Wednesday
4 = Thursday
5 = Friday
6 = Saturday
7 = Sunday
```

Weekend rule:

```text
Saturday and Sunday = true
Monday to Friday = false
```

Validation status:

```text
weekend_flags_valid: PASS
```

---

# Visual Validation Performed

Manual MySQL checks were performed after the build.

## August 2026 sample

A sample query for:

```text
2026-08-01 to 2026-08-10
```

confirmed:

```text
2026-08-01 Saturday is_weekend = 1
2026-08-02 Sunday is_weekend = 1
2026-08-03 Monday is_weekend = 0
2026-08-04 Tuesday is_weekend = 0
2026-08-05 Wednesday is_weekend = 0
2026-08-06 Thursday is_weekend = 0
2026-08-07 Friday is_weekend = 0
2026-08-08 Saturday is_weekend = 1
2026-08-09 Sunday is_weekend = 1
2026-08-10 Monday is_weekend = 0
```

This confirms that:

```text
day_of_week_name is populated correctly
is_weekend is populated correctly
year_month_label is populated correctly
year_quarter is populated correctly
```

---

## Month boundaries

A sample query for August 2026 confirmed:

```text
2026-08-01 is_month_start = 1
visible intermediate days have is_month_start = 0
visible intermediate days have is_month_end = 0
```

The full validator also confirmed:

```text
month_boundary_flags_valid: PASS
```

---

# Current Scripts

## Build Script

```text
scripts/build_dim_time.py
```

Purpose:

```text
Create or refresh dim_time using deterministic generated calendar logic.
```

Current behaviour:

```text
creates dim_time if missing
generates dates from 2020-01-01 to 2035-12-31
derives day, week, month, quarter and year fields
uses date_key = YYYYMMDD
uses exact rebuild semantics
prints build summary
```

---

## Validation Script

```text
scripts/validate_dim_time.py
```

Purpose:

```text
Validate the shared analytical calendar dimension after build.
```

Current validations:

```text
dim_time_exists
dim_time_row_count
dim_time_min_max_dates
date_key_unique
calendar_date_unique
calendar_date_not_null
date_key_matches_calendar_date
weekend_flags_valid
month_boundary_flags_valid
quarter_boundary_flags_valid
year_boundary_flags_valid
iso_week_fields_valid
```

---

# Refresh Strategy

The current implementation uses exact rebuild semantics:

```text
DELETE FROM dim_time
INSERT generated calendar rows
```

Reason:

```text
dim_time is deterministic.
date_key is stable.
calendar_date is stable.
No downstream analytical facts depend on it yet.
```

Future note:

```text
Even after downstream facts depend on dim_time, exact rebuild remains safe as long as date_key values never change for existing dates.
```

Important rule:

```text
date_key must never change for a given calendar_date.
```

---

# Query Examples

## 1. Date range and row count

```sql
SELECT
    MIN(calendar_date) AS min_date,
    MAX(calendar_date) AS max_date,
    COUNT(*) AS total_rows
FROM dim_time;
```

Expected result:

```text
min_date = 2020-01-01
max_date = 2035-12-31
total_rows = 5844
```

---

## 2. Daily sample

```sql
SELECT
    date_key,
    calendar_date,
    year,
    year_month_label,
    year_quarter,
    day_of_week_name,
    is_weekend
FROM dim_time
WHERE calendar_date BETWEEN '2026-08-01' AND '2026-08-10'
ORDER BY calendar_date;
```

---

## 3. Month boundary sample

```sql
SELECT
    date_key,
    calendar_date,
    year_month_label,
    is_month_start,
    is_month_end
FROM dim_time
WHERE calendar_date BETWEEN '2026-08-01' AND '2026-08-31'
ORDER BY calendar_date;
```

---

## 4. Quarter boundary sample

```sql
SELECT
    date_key,
    calendar_date,
    year_quarter,
    quarter_start_date,
    quarter_end_date,
    is_quarter_start,
    is_quarter_end
FROM dim_time
WHERE calendar_date BETWEEN '2026-07-01' AND '2026-09-30'
ORDER BY calendar_date;
```

---

## 5. ISO week sample

```sql
SELECT
    date_key,
    calendar_date,
    iso_year,
    iso_week_of_year,
    week_start_date,
    week_end_date,
    is_week_start,
    is_week_end
FROM dim_time
WHERE calendar_date BETWEEN '2026-12-28' AND '2027-01-04'
ORDER BY calendar_date;
```

---

# Relationship to Analytical Layer

`dim_time` is now the second implemented shared dimension.

Implemented dimensions:

```text
dim_company_analytical
dim_time
```

Implemented analytical coverage table:

```text
analytics_company_domain_coverage
```

`dim_time` will support future analytical tables such as:

```text
analytics_purchase_orders
analytics_purchase_order_lines
analytics_inventory_snapshot
analytics_zenput_submissions
analytics_zenput_tasks
future analytics_sales_*
```

---

# Expected Future Joins

## Purchases

Expected future joins:

```text
analytics_purchase_orders.order_date_key -> dim_time.date_key
analytics_purchase_order_lines.order_date_key -> dim_time.date_key
```

Candidate source dates:

```text
order_date
receipt_date
```

---

## Inventory

Expected future joins:

```text
analytics_inventory_snapshot.snapshot_date_key -> dim_time.date_key
```

Open decision:

```text
Inventory snapshot date must be defined explicitly.
```

Current possible source:

```text
DATE(etl_loaded_at)
```

but this needs business confirmation before implementation.

---

## Zenput

Expected future joins:

```text
analytics_zenput_submissions.submitted_date_key -> dim_time.date_key
analytics_zenput_tasks.created_date_key -> dim_time.date_key
analytics_zenput_tasks.due_date_key -> dim_time.date_key
analytics_zenput_tasks.completed_date_key -> dim_time.date_key
```

Candidate source fields:

```text
submitted_at
date_submitted
date_created
date_due
fulfillment_date_completed
last_updated
```

---

## Future Sales

Sales is deferred to a later section.

Expected future joins:

```text
analytics_sales_*.sale_date_key -> dim_time.date_key
```

---

# Current Known Decisions

## Month labels

Current implementation uses:

```text
month_name
month_short_name
day_of_week_name
day_of_week_short_name
```

in English.

Decision:

```text
Keep English labels in first version.
```

Reason:

```text
The dimension is a technical MySQL analytical object.
Spanish labels can be added later if needed inside MySQL.
```

Potential future fields:

```text
month_name_es
month_short_name_es
day_of_week_name_es
day_of_week_short_name_es
```

---

## Fiscal calendar

Current implementation:

```text
No fiscal calendar fields.
```

Reason:

```text
No governed fiscal calendar has been defined yet.
```

Potential future fields:

```text
fiscal_year
fiscal_quarter
fiscal_month
is_fiscal_year_start
is_fiscal_year_end
```

---

## Holiday calendar

Current implementation:

```text
No holiday fields.
```

Reason:

```text
Holiday logic requires a governed holiday table or policy.
```

Potential future table:

```text
dim_holiday
```

Potential future fields:

```text
is_holiday
holiday_name
holiday_country
```

---

## Business day flag

Current implementation:

```text
is_weekend only
```

Reason:

```text
A true business day depends on holiday and operating calendar rules.
```

Potential future field:

```text
is_business_day
```

---

# Validation Warnings

The validator currently raises pandas DBAPI warnings such as:

```text
pandas only supports SQLAlchemy connectable...
```

Current status:

```text
Non-blocking
```

Reason:

```text
The warnings do not affect validation results.
The validator returns 12 passed validations and 0 failed validations.
```

Future improvement:

```text
Migrate validators to SQLAlchemy engine if warning cleanup becomes desirable.
```

---

# Step 17.10 Closeout

Step 17.10 is complete when:

```text
[x] scripts/build_dim_time.py created
[x] scripts/validate_dim_time.py created
[x] both scripts compile
[x] dim_time table created
[x] build completed successfully
[x] validation passed
[x] 5844 rows generated
[x] date range 2020-01-01 to 2035-12-31 confirmed
[x] date_key uniqueness validated
[x] calendar_date uniqueness validated
[x] weekend logic validated
[x] month boundary logic validated
[x] quarter boundary logic validated
[x] year boundary logic validated
[x] ISO week fields validated
[x] year_month renamed to year_month_label to avoid MariaDB syntax issue
```

---

# Step 17.11 Closeout

This documentation step is complete when:

```text
[x] dim_time implementation result documented
[x] real build result documented
[x] real validation result documented
[x] year_month_label decision documented
[x] query examples documented
[x] relationship to future analytics tables documented
[x] next shared dimension decision prepared
```

---

# Recommended Next Shared Dimension

Current implemented shared dimensions:

```text
dim_company_analytical
dim_time
```

Remaining planned shared dimensions:

```text
dim_product
dim_vendor
```

## Recommendation

The next shared dimension should be:

```text
dim_vendor
```

---

## Why dim_vendor before dim_product

`dim_vendor` is more constrained and lower risk than `dim_product`.

Reasons:

```text
It directly supports Purchases.
It connects to the already validated internal provider rule.
It helps formalize Bodegón and Empanadas as internal vendors.
It is less complex than unifying Odoo/Wansoft products.
It prepares analytics_purchase_orders and analytics_purchase_order_lines.
```

`dim_product` is important, but more complex because it involves:

```text
Wansoft codes
Odoo product IDs
inventory_mapping_dictionary
scope logic
approved mappings
unmapped products
backlog rules
no automatic aliases
```

Therefore, the recommended sequence is:

```text
Paso 17.12 — Diseñar dim_vendor
Paso 17.13 — Implementar dim_vendor
Paso 17.14 — Diseñar dim_product
Paso 17.15 — Implementar dim_product
```

---

# Recommended Next Step

```text
Paso 17.12 — Diseñar dim_vendor
```

Expected contents:

```text
purpose
grain
source inputs
internal vendor rule
proposed fields
schema draft
validation rules
relationship to Purchases
relationship to internal providers
```