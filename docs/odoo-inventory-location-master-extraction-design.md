# Odoo Inventory Location Master Extraction Design

## Step

```text
Paso 18.16B - Diseñar extracción de maestro de ubicaciones Odoo con company_id/company_name
```

## Purpose

This document redesigns the inventory location company-mapping approach.

The previous worklist-based process is not enough because it requires manually deciding which company each inventory location belongs to. That does not scale when new branches, warehouses, kitchens, bars, production locations, intercompany transit locations or other Odoo locations are added.

The correct source of truth should be the Odoo inventory location master.

Odoo inventory locations must be extracted with their configured company fields and loaded into the analytical layer before assigning company-level inventory eligibility.

---

## Core Decision

The company of an inventory location must be obtained from Odoo configuration when it exists.

The project must not infer location company from:

```text
location_name
normalized_location_name
source_location_id text patterns
warehouse prefix
branch-like wording
```

The new design changes the mapping flow from:

```text
location_name -> manual guess -> company_source_key
```

to:

```text
Odoo stock.location -> company_id/company_name -> governed company mapping -> company_source_key
```

---

## Why This Change Is Required

The current `inventory_location_company_mapping_worklist.csv` contains 30 internal inventory locations that are physically eligible but not company-mapped.

Those locations belong to real Odoo configuration, not to a free-text list.

If the project continues with only manual worklists, every future new branch or new location would require manual interpretation again.

The scalable approach is:

```text
1. Extract the full Odoo location master.
2. Preserve Odoo company metadata.
3. Join current analytical inventory locations to that master.
4. Use explicit Odoo company mapping governance only when needed.
5. Keep manual review only for exceptions.
```

---

## Source System

Primary source system:

```text
Odoo
```

Primary Odoo model:

```text
stock.location
```

Purpose of this source model:

```text
Maintain Odoo inventory location configuration.
```

---

## Minimum Odoo Fields Required

The extraction must retrieve at least:

```text
id
name
complete_name
usage
location_id
company_id
active
scrap_location
return_location
barcode
```

Recommended expanded fields:

```text
id
name
complete_name
usage
location_id/id
location_id/name
company_id/id
company_id/name
active
scrap_location
return_location
barcode
warehouse_id/id
warehouse_id/name
write_date
create_date
```

If some fields are unavailable in the installed Odoo version or API response, they may be nullable, but the extraction must always try to preserve:

```text
id
name
complete_name
usage
company_id/id
company_id/name
```

---

## Odoo Semantics Used by This Design

Odoo documentation describes an inventory location as a specific space within a warehouse and identifies configuration fields such as location name, parent location, location type and company. Odoo documentation also states that the company field represents the company whose warehouse the location is inside of, and that the field may be left blank if the location is shared between companies.

This design relies on that source configuration rather than string inference.

---

## Internal Project Context

Internal implementation documentation for branch go-live includes Odoo/Wansoft configuration tasks such as initial company setup, warehouse setup, location configuration, multi-company validation, intercompany flow validation, intercompany transit locations and warehouse visibility validation.

This supports treating locations and company visibility as configured master data, not as names to infer from.

Internal Odoo inventory training also described different location concepts such as view locations, transit locations, internal locations, customer locations and vendor locations, and explained that inventory moves use origin and destination locations.

This supports preserving location type and source location lineage in the analytical model.

---

## New Target Staging Object

```text
stg_odoo_inventory_location_master
```

Purpose:

```text
Store the current extracted Odoo inventory location master with Odoo company metadata.
```

Recommended grain:

```text
1 row = 1 Odoo stock.location record per extraction timestamp
```

Recommended natural key:

```text
source_system
odoo_location_id
```

Initial source system:

```text
odoo
```

---

## Proposed Schema

```sql
CREATE TABLE stg_odoo_inventory_location_master (
    stg_location_master_key BIGINT AUTO_INCREMENT PRIMARY KEY,

    source_system VARCHAR(50) NOT NULL DEFAULT 'odoo',
    odoo_location_id VARCHAR(100) NOT NULL,
    source_location_id VARCHAR(100) NOT NULL,

    location_name VARCHAR(500) NULL,
    complete_location_name VARCHAR(1000) NULL,
    normalized_location_name VARCHAR(1000) NULL,

    odoo_usage VARCHAR(100) NULL,
    odoo_location_type VARCHAR(100) NULL,

    parent_odoo_location_id VARCHAR(100) NULL,
    parent_location_name VARCHAR(500) NULL,

    odoo_company_id VARCHAR(100) NULL,
    odoo_company_name VARCHAR(500) NULL,
    odoo_company_mapping_status VARCHAR(100) NOT NULL DEFAULT 'pending_company_mapping',

    is_active BOOLEAN NULL,
    is_scrap_location BOOLEAN NULL,
    is_return_location BOOLEAN NULL,
    barcode VARCHAR(255) NULL,

    odoo_create_date DATETIME NULL,
    odoo_write_date DATETIME NULL,
    etl_loaded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uq_stg_odoo_inventory_location_master_source (
        source_system,
        odoo_location_id
    ),

    KEY idx_stg_odoo_inventory_location_master_source_location (
        source_system,
        source_location_id
    ),

    KEY idx_stg_odoo_inventory_location_master_company (
        odoo_company_id,
        odoo_company_name
    ),

    KEY idx_stg_odoo_inventory_location_master_usage (
        odoo_usage
    )
);
```

Important design choice:

```text
source_location_id should equal odoo_location_id when current inventory facts are using the Odoo stock.location id.
```

The first implementation must validate this assumption.

---

## Extraction Method Options

### Option A: Odoo XML-RPC or JSON-RPC extraction

Recommended fields:

```python
fields = [
    "id",
    "name",
    "complete_name",
    "usage",
    "location_id",
    "company_id",
    "active",
    "scrap_location",
    "return_location",
    "barcode",
    "create_date",
    "write_date",
]
```

Recommended model:

```text
stock.location
```

Recommended domain:

```python
[]
```

Reason:

```text
The master should include internal, view, transit, vendor, customer, inventory, production and other location types.
Downstream analytical rules decide what is physically eligible.
```

---

### Option B: Odoo export file

If direct API extraction is not yet available, operators can export the location master from Odoo and place it in a controlled input folder.

Recommended file:

```text
inputs/odoo_inventory_location_master.csv
```

Required exported columns:

```text
id
name
complete_name
usage
location_id/id
location_id/name
company_id/id
company_id/name
active
scrap_location
return_location
barcode
```

This option is acceptable as a temporary bridge, but API extraction is preferred for repeatability.

---

## Mapping Layers

The design must distinguish three different meanings:

### 1. Odoo location identity

```text
stock.location.id
```

Stored as:

```text
odoo_location_id
source_location_id
```

---

### 2. Odoo configured company

```text
stock.location.company_id
```

Stored as:

```text
odoo_company_id
odoo_company_name
```

This reflects the Odoo company assignment.

If blank:

```text
shared_or_unassigned_location
```

---

### 3. Analytical company governance

```text
company_source_key
```

This is the analytical company key used by the data warehouse.

It must come from a governed mapping from Odoo company to analytical company, not from location name.

---

## New Governance Table

Recommended new mapping table:

```text
odoo_company_analytical_mapping_config
```

Purpose:

```text
Map Odoo company ids or names to the analytical company_source_key.
```

Suggested schema:

```sql
CREATE TABLE odoo_company_analytical_mapping_config (
    mapping_config_key BIGINT AUTO_INCREMENT PRIMARY KEY,

    source_system VARCHAR(50) NOT NULL DEFAULT 'odoo',
    odoo_company_id VARCHAR(100) NULL,
    odoo_company_name VARCHAR(500) NULL,

    company_source_key VARCHAR(255) NULL,
    mapped_company_name VARCHAR(500) NULL,

    mapping_status VARCHAR(100) NOT NULL DEFAULT 'pending_review',
    mapping_method VARCHAR(100) NOT NULL DEFAULT 'manual_governance',
    mapping_notes TEXT NULL,

    include_in_final_company_inventory BOOLEAN NOT NULL DEFAULT FALSE,
    company_role_type VARCHAR(100) NULL,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    KEY idx_odoo_company_analytical_mapping_odoo_company (
        source_system,
        odoo_company_id
    ),

    KEY idx_odoo_company_analytical_mapping_company_source_key (
        company_source_key
    ),

    KEY idx_odoo_company_analytical_mapping_status (
        mapping_status,
        is_active
    )
);
```

This table is where cases like Bodegón, Empanadas, internal providers or shared companies must be governed.

---

## Revised Role of inventory_location_company_mapping_config

The existing table:

```text
inventory_location_company_mapping_config
```

should no longer be the primary mechanism for normal mapping.

New role:

```text
Manual exception override table for locations that cannot be resolved through Odoo company_id/company_name.
```

Examples:

```text
Odoo company field is blank but business confirms the location belongs to an analytical company.
Odoo company field is shared but the location must be split or handled specially.
Specific location should be excluded even though Odoo has a company.
```

Default mapping path should become:

```text
stg_odoo_inventory_location_master.odoo_company_id
-> odoo_company_analytical_mapping_config
-> dim_inventory_location.company_source_key
```

Exception path:

```text
dim_inventory_location.source_location_id
-> inventory_location_company_mapping_config
```

Exception path should have lower precedence unless explicitly configured as an override.

---

## Revised dim_inventory_location Build Logic

The future `build_dim_inventory_location.py` should be updated as follows:

```text
1. Discover source locations from analytics_inventory_snapshot.
2. Join stg_odoo_inventory_location_master by source_system + source_location_id.
3. Bring Odoo fields into dim_inventory_location.
4. Join odoo_company_analytical_mapping_config by source_system + odoo_company_id.
5. Populate company_source_key only when mapping is approved and active.
6. Apply manual location override only for explicit exceptions.
7. Keep partner and virtual locations excluded from company inventory views.
8. Keep internal_or_unknown locations physically eligible.
9. Set company mapping status based on Odoo company availability and mapping status.
```

Recommended precedence:

```text
1. Explicit active location override, if override mode is allowed.
2. Approved Odoo company analytical mapping.
3. Pending Odoo company mapping.
4. Shared or unassigned Odoo location.
5. Missing Odoo location master row.
```

---

## Proposed Status Values

### odoo_location_master_status

```text
matched_to_odoo_master
missing_from_odoo_master
```

### odoo_company_status

```text
odoo_company_available
shared_or_unassigned_location
missing_from_odoo_master
```

### company_mapping_status

```text
approved_from_odoo_company
pending_odoo_company_mapping
shared_or_unassigned_location
manual_location_override
missing_odoo_location_master
excluded_non_physical_location
```

### location_review_status

```text
ok
needs_odoo_master_review
needs_odoo_company_mapping
shared_location_review
non_physical_location
manual_override_review
```

---

## Validation Requirements

Recommended validation script:

```text
scripts/validate_odoo_inventory_location_master.py
```

Validation checks:

```text
stg_odoo_inventory_location_master exists
stg_odoo_inventory_location_master has rows
grain unique by source_system + odoo_location_id
no null odoo_location_id
no null source_location_id
all dim_inventory_location source_location_id values exist in staging or are explicitly marked missing
Odoo company distribution is available
Odoo usage distribution is available
blank Odoo company rows are counted and reviewed
internal_or_unknown dim locations have a matched Odoo location or review status
```

---

## Reconciliation Queries

### Count unmatched dim locations

```sql
SELECT
    COUNT(1) AS missing_master_locations
FROM dim_inventory_location d
LEFT JOIN stg_odoo_inventory_location_master m
    ON m.source_system = d.source_system
   AND m.source_location_id = d.source_location_id
WHERE m.source_location_id IS NULL;
```

Expected after successful extraction:

```text
0 or explicitly explained rows
```

---

### Odoo company availability

```sql
SELECT
    CASE
        WHEN odoo_company_id IS NULL OR odoo_company_id = '' THEN 'blank_company'
        ELSE 'company_available'
    END AS odoo_company_availability,
    COUNT(1) AS total_locations
FROM stg_odoo_inventory_location_master
GROUP BY
    CASE
        WHEN odoo_company_id IS NULL OR odoo_company_id = '' THEN 'blank_company'
        ELSE 'company_available'
    END;
```

---

### Odoo usage distribution

```sql
SELECT
    odoo_usage,
    COUNT(1) AS total_locations
FROM stg_odoo_inventory_location_master
GROUP BY odoo_usage
ORDER BY odoo_usage;
```

---

### Company mapping governance distribution

```sql
SELECT
    m.odoo_company_id,
    m.odoo_company_name,
    c.company_source_key,
    c.mapping_status,
    c.include_in_final_company_inventory,
    COUNT(1) AS total_locations
FROM stg_odoo_inventory_location_master m
LEFT JOIN odoo_company_analytical_mapping_config c
    ON c.source_system = m.source_system
   AND c.odoo_company_id = m.odoo_company_id
   AND c.is_active = TRUE
GROUP BY
    m.odoo_company_id,
    m.odoo_company_name,
    c.company_source_key,
    c.mapping_status,
    c.include_in_final_company_inventory
ORDER BY
    m.odoo_company_name;
```

---

## Extraction Output Report

The extraction script should print:

```text
source_model: stock.location
total_locations_extracted
active_locations
inactive_locations
locations_with_company
locations_without_company
usage_distribution
company_distribution
output_table: stg_odoo_inventory_location_master
```

---

## Operational Handling of Blank Company

If Odoo returns no company for a location, the row should not be automatically mapped.

It should be classified as:

```text
shared_or_unassigned_location
```

Then reviewed separately.

This is important because Odoo documentation allows company to be blank when a location is shared between companies.

---

## Bodegón and Other Internal Entities

The Odoo location master may show locations whose Odoo company belongs to internal operational entities such as Bodegón or similar entities.

This design does not automatically convert those entities into final analytical companies.

Instead:

```text
Odoo company identifies the configured Odoo owner.
Analytical company mapping decides whether it enters final company inventory views.
```

This preserves the earlier governance principle that internal providers or special operational entities may require different analytical treatment.

---

## Revised Step Sequence

Recommended sequence after this design:

```text
Paso 18.16C - Implementar extracción stg_odoo_inventory_location_master
Paso 18.16D - Implementar odoo_company_analytical_mapping_config
Paso 18.16E - Modificar build_dim_inventory_location para usar Odoo company master
Paso 18.16F - Validar dim_inventory_location enriquecida con company_id/company_name
Paso 18.17 - Preparar seed sólo para excepciones no resueltas por Odoo
```

---

## Acceptance Criteria

This step is complete when the design defines:

```text
source Odoo model
required fields
staging table
company mapping layer
revised role of location mapping config
revised dim_inventory_location build logic
status values
validation requirements
reconciliation queries
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
Paso 18.16C - Implementar extracción stg_odoo_inventory_location_master
```

Purpose:

```text
Extract Odoo stock.location master data with company_id/company_name into the analytical warehouse.
```
