# Inventory location_usage_type Policy

## Purpose

This document defines the policy for using `location_usage_type` in inventory analytical views derived from `analytics_inventory_snapshot`.

The objective is to separate physical inventory views from diagnostic inventory evidence without deleting or hiding source rows from the analytical base table.

This policy applies to:

```text
analytics_inventory_snapshot
future inventory views
future inventory aggregates
future dim_inventory_location design
```

It does not redefine the source table grain.

The grain of `analytics_inventory_snapshot` remains:

```text
1 row = 1 row from odoo_inventory_snapshot
```

---

## Background

`analytics_inventory_snapshot` was implemented and validated with all source rows preserved.

Latest validated build result:

```text
total_rows: 1660
include_in_business_views: 1407
excluded_from_business_views: 253
orphan_product_rows: 50
invalid_snapshot_date_rows: 0
not_usable_for_etl_rows: 0
mapping_not_approved_rows: 0
total_stock_qty: -66689.8400
```

Latest validated analysis of negative stock showed:

```text
total_rows: 1660
negative_rows: 438
zero_rows: 2
positive_rows: 1220
total_stock_qty: -66689.8400
negative_stock_qty: -1471517.9800
positive_stock_qty: 1404828.1400
```

The negative stock analysis by `location_usage_type` showed:

```text
partner:
    total_rows: 227
    negative_rows: 117
    total_stock_qty: -516507.4300
    negative_stock_qty: -1240202.7700
    positive_stock_qty: 723695.3400

internal_or_unknown:
    total_rows: 505
    negative_rows: 0
    total_stock_qty: 39277.6000
    negative_stock_qty: 0.0000
    positive_stock_qty: 39277.6000

virtual:
    total_rows: 928
    negative_rows: 321
    total_stock_qty: 410539.9900
    negative_stock_qty: -231315.2100
    positive_stock_qty: 641855.2000
```

Key observation:

```text
Negative inventory quantity is not present in internal_or_unknown locations.
Negative inventory quantity is concentrated in partner and virtual locations.
```

---

## Operational Context

Inventory analytics in Odoo must distinguish between physical stock positions and operational/valuation locations.

Internal operational discussions established that inventory and accounting must stay synchronized, and that inventory adjustments affecting valuation should be performed through the inventory module instead of direct accounting-only adjustments.

Internal discussions also identified that virtual locations, partner/vendor locations, production flows, intercompany processes, kits, valuation layers and stock movements can create records that should remain traceable but should not automatically be treated as physical inventory available in a branch.

Therefore, the analytical layer must preserve these rows while separating them from default physical inventory views.

---

## Policy Decision

`analytics_inventory_snapshot` remains the complete evidence table.

No rows are deleted.

No rows are removed from the analytical base table.

However, not every row in `analytics_inventory_snapshot` should be used in default physical inventory views.

The first official policy is:

```text
Default physical inventory views must include only rows where:
    include_in_business_views = true
    and location_usage_type = 'internal_or_unknown'
```

This rule is intentionally conservative.

It avoids treating Odoo partner and virtual locations as physical branch inventory until a governed `dim_inventory_location` or warehouse/location-to-company mapping exists.

---

## Policy Fields

The policy introduces a conceptual field for downstream views:

```text
include_in_inventory_physical_views
```

Recommended logic:

```text
include_in_inventory_physical_views = true when:
    include_in_business_views = true
    and location_usage_type = 'internal_or_unknown'
```

Recommended exclusion reason field:

```text
inventory_physical_exclude_reason
```

Recommended exclusion reasons:

```text
not_business_ready
non_physical_partner_location
non_physical_virtual_location
unknown_location_usage_type
```

---

## Location Usage Policy

### internal_or_unknown

Policy:

```text
Eligible for default physical inventory views when include_in_business_views = true.
```

Reason:

```text
Current analysis shows zero negative rows for internal_or_unknown.
This group is the safest first-version candidate for physical inventory views.
```

Important limitation:

```text
internal_or_unknown does not yet mean final branch or company identity.
It only means the location was not classified as partner or virtual under the current helper classification.
```

Future work:

```text
Map internal Odoo locations or warehouses to company_source_key through explicit governance.
```

---

### partner

Policy:

```text
Exclude from default physical inventory views.
Keep visible in analytics_inventory_snapshot.
Keep available for diagnostic and reconciliation views.
```

Reason:

```text
Partner locations represent vendor/customer-style locations in Odoo.
Current analysis shows that partner locations contain the largest negative quantity concentration.
They should not be interpreted as physical branch stock.
```

Recommended downstream handling:

```text
include_in_inventory_physical_views = false
inventory_physical_exclude_reason = non_physical_partner_location
```

---

### virtual

Policy:

```text
Exclude from default physical inventory views.
Keep visible in analytics_inventory_snapshot.
Keep available for diagnostic, production, valuation and adjustment analysis.
```

Reason:

```text
Virtual locations are used by Odoo for flows such as production, inventory adjustments, intercompany transit and other non-direct physical stock positions.
They are operationally important but should not be treated as default physical branch inventory.
```

Recommended downstream handling:

```text
include_in_inventory_physical_views = false
inventory_physical_exclude_reason = non_physical_virtual_location
```

---

## Recommended View

Recommended first downstream view:

```text
vw_inventory_physical_snapshot
```

Purpose:

```text
Expose first-version physical inventory evidence from analytics_inventory_snapshot while excluding partner and virtual locations from default consumption.
```

Recommended SQL:

```sql
CREATE OR REPLACE VIEW vw_inventory_physical_snapshot AS
SELECT
    inventory_snapshot_analytical_key,
    source_inventory_snapshot_id,
    odoo_product_id,
    odoo_product_name,
    product_code,
    source_location_id,
    location_name,
    normalized_location_name,
    location_usage_type,
    company_source_key,
    company_mapping_status,
    snapshot_date,
    snapshot_date_key,
    etl_loaded_at,
    product_analytical_key,
    wansoft_code,
    wansoft_product_name,
    wansoft_department,
    product_identity_status,
    dim_product_mapping_status,
    is_product_mapped,
    is_product_review_required,
    include_product_in_business_views,
    stock_qty,
    mapping_found,
    lookup_method,
    mapping_status,
    usable_for_etl,
    lifecycle_candidate,
    similarity_score,
    mapping_notes,
    include_in_business_views,
    exclude_reason,
    inventory_review_status,
    TRUE AS include_in_inventory_physical_views,
    NULL AS inventory_physical_exclude_reason,
    created_at,
    updated_at
FROM analytics_inventory_snapshot
WHERE include_in_business_views = TRUE
  AND location_usage_type = 'internal_or_unknown';
```

Expected current result based on the latest analysis:

```text
rows: 424
negative_rows: 0
total_stock_qty: 20430.0700
```

---

## Recommended Diagnostic View

Recommended diagnostic view:

```text
vw_inventory_non_physical_snapshot
```

Purpose:

```text
Expose partner and virtual inventory rows for diagnostic analysis without mixing them with default physical inventory views.
```

Recommended SQL:

```sql
CREATE OR REPLACE VIEW vw_inventory_non_physical_snapshot AS
SELECT
    inventory_snapshot_analytical_key,
    source_inventory_snapshot_id,
    odoo_product_id,
    odoo_product_name,
    product_code,
    source_location_id,
    location_name,
    normalized_location_name,
    location_usage_type,
    company_source_key,
    company_mapping_status,
    snapshot_date,
    snapshot_date_key,
    etl_loaded_at,
    product_analytical_key,
    wansoft_code,
    wansoft_product_name,
    wansoft_department,
    product_identity_status,
    dim_product_mapping_status,
    is_product_mapped,
    is_product_review_required,
    include_product_in_business_views,
    stock_qty,
    mapping_found,
    lookup_method,
    mapping_status,
    usable_for_etl,
    lifecycle_candidate,
    similarity_score,
    mapping_notes,
    include_in_business_views,
    exclude_reason,
    inventory_review_status,
    FALSE AS include_in_inventory_physical_views,
    CASE
        WHEN include_in_business_views = FALSE THEN 'not_business_ready'
        WHEN location_usage_type = 'partner' THEN 'non_physical_partner_location'
        WHEN location_usage_type = 'virtual' THEN 'non_physical_virtual_location'
        ELSE 'unknown_location_usage_type'
    END AS inventory_physical_exclude_reason,
    created_at,
    updated_at
FROM analytics_inventory_snapshot
WHERE include_in_business_views = FALSE
   OR location_usage_type <> 'internal_or_unknown';
```

---

## Recommended Validation Queries

### Physical View Row Count

```sql
SELECT
    COUNT(1) AS physical_rows,
    SUM(CASE WHEN stock_qty < 0 THEN 1 ELSE 0 END) AS negative_rows,
    COALESCE(SUM(stock_qty), 0) AS total_stock_qty
FROM vw_inventory_physical_snapshot;
```

Expected current result:

```text
physical_rows: 424
negative_rows: 0
total_stock_qty: 20430.0700
```

---

### Non-Physical View Distribution

```sql
SELECT
    location_usage_type,
    inventory_physical_exclude_reason,
    COUNT(1) AS total_rows,
    SUM(CASE WHEN stock_qty < 0 THEN 1 ELSE 0 END) AS negative_rows,
    COALESCE(SUM(stock_qty), 0) AS total_stock_qty
FROM vw_inventory_non_physical_snapshot
GROUP BY
    location_usage_type,
    inventory_physical_exclude_reason
ORDER BY total_stock_qty ASC;
```

Purpose:

```text
Confirm that partner and virtual locations remain available for diagnostics.
```

---

## Downstream Consumption Rules

### For physical inventory analysis

Use:

```text
vw_inventory_physical_snapshot
```

Do not use directly:

```text
analytics_inventory_snapshot
```

unless the analysis explicitly needs diagnostic or governance rows.

---

### For diagnostic inventory analysis

Use:

```text
analytics_inventory_snapshot
vw_inventory_non_physical_snapshot
reports/analytics_inventory_negative_stock/*.csv
```

---

### For future company or branch inventory views

Do not infer company from:

```text
location_name
normalized_location_name
location_usage_type
```

Use a governed mapping table or dimension.

Recommended future object:

```text
dim_inventory_location
```

---

## Governance Rationale

This policy separates two valid analytical needs:

```text
1. Physical inventory view:
   conservative, business-facing, excludes non-physical Odoo locations.

2. Diagnostic inventory evidence:
   complete, traceable, includes partner and virtual locations.
```

This prevents business-facing inventory reports from being distorted by Odoo operational locations while preserving the evidence needed to diagnose valuation, production, intercompany, vendor/customer and adjustment flows.

---

## Current Decision

Final policy decision for first-version inventory views:

```text
analytics_inventory_snapshot remains complete evidence.
Default physical inventory views include only internal_or_unknown rows that are business-ready.
Partner locations are excluded from default physical views.
Virtual locations are excluded from default physical views.
Partner and virtual locations remain available for diagnostics.
Company mapping is still deferred until dim_inventory_location or another governed mapping exists.
```

---

## Step 18.5 Closeout

Step 18.5 is complete when:

```text
location_usage_type policy is documented
physical inventory view rule is defined
partner exclusion rule is defined
virtual exclusion rule is defined
diagnostic preservation rule is defined
recommended physical and diagnostic views are defined
validation queries are defined
future dim_inventory_location dependency is documented
```

Current status:

```text
complete
```

---

## Recommended Next Step

Recommended next step:

```text
Paso 18.6 - Implementar vistas vw_inventory_physical_snapshot y vw_inventory_non_physical_snapshot
```

Purpose:

```text
Create explicit physical and diagnostic inventory views without changing analytics_inventory_snapshot.
```
