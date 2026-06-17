# Inventory Domain Closeout

## Status
**Phase:** Completed baseline  
**Environment:** Test  
**Odoo mode:** Read-only  
**Dictionary master:** MySQL

---

## Goal of the phase

Build the **Inventory Domain** for the Odoo → MySQL pipeline while keeping:

- **Odoo** as a read-only operational source
- **MySQL** as the master layer for:
  - catalog governance
  - scope classification
  - lifecycle interpretation
  - mapping dictionary
  - ETL output snapshots and backlogs

The purpose of this phase was to stop solving catalog inconsistencies inside Odoo and instead centralize all matching and governance logic in MySQL.

---

## Final architecture

```text
Odoo (read-only)
    ↓
Inventory extraction
    ↓
Scope classification (MySQL-driven)
    ↓
Dictionary lookup (MySQL)
    ↓
Scope-aware ETL
    ↓
Snapshot + Backlog
```

### Key principle
- **Do not update Odoo for catalog correction**
- **Do not assign internal references inside Odoo from this pipeline**
- **All catalog intelligence lives in MySQL**

---

## Major design decisions

### 1. Odoo remains read-only
The project explicitly avoids writing back catalog corrections into Odoo.

### 2. MySQL becomes the governance layer
All inventory mapping logic is handled through:
- `inventory_mapping_dictionary`
- scope classification tables
- lifecycle tables
- bridge/backlog tables

### 3. Scope must be separated before mapping
Inventory cannot be treated as a single universe.

The ETL now distinguishes:
- `restaurantes`
- `bodegon`
- `empanadas`
- `shared_cross_company`
- `review_scope`
- `operational_non_inventory`

### 4. Public-sale products are not mapped as raw inventory
If a product:
- has internal reference
- and `sale_ok = True`

then it is treated as a **restaurant / public-sale product** and kept outside the inventory dictionary matching flow.

---

## Tables implemented

### Core governance
- `inventory_mapping_dictionary`
- `inventory_product_lifecycle`
- `odoo_inventory_scope_classification`

### ETL output
- `odoo_inventory_snapshot`
- `odoo_inventory_backlog`

### Backlog prioritization and bridge layers
- `inventory_not_found_priority_backlog`
- `inventory_not_found_p1_bridge`
- `inventory_not_found_p2_bridge`
- `inventory_not_found_residual_bridge`

### Intermediate classification tables
- `odoo_inventory_raw_no_code_classification`
- `inventory_bridge_report`

---

## Scope model

### Final refined scope buckets
- `restaurantes`
- `bodegon`
- `empanadas`
- `shared_cross_company`
- `review_scope`
- `operational_non_inventory`

### ETL inclusion logic
The inventory ETL currently includes only:

- `shared_cross_company`

The ETL sends these buckets directly to backlog:

- `scope_restaurantes_sales_reference`
- `scope_bodegon`
- `scope_bodegon_candidate`
- `scope_empanadas`
- `scope_review_scope`
- `scope_operational_non_inventory`

---

## Dictionary sources

The dictionary is now populated from multiple controlled sources:

- `bridge_report`
- `p1_bridge`
- `p2_bridge`
- `residual_bridge`

### Meaning
This means the dictionary has been expanded incrementally through:
1. initial bridge discovery
2. prioritized not-found backlog waves
3. lifecycle-aware promotion logic

---

## ETL status at closeout

### ETL is technically stable
The ETL now:
- extracts Odoo inventory
- merges refined scope
- selects only the intended inventory universe
- applies dictionary lookup
- writes:
  - `odoo_inventory_snapshot`
  - `odoo_inventory_backlog`

### Latest validated state
At the end of this phase, the ETL achieved:

- **Snapshot rows:** 1660
- **Approved rows:** 1660
- **Pending rows:** 25
- **Not found rows:** 873

### Functional residual backlog
- `not_found`: 98 unique products
- `pending_review`: 5 unique products

This means the inventory phase moved from broad uncontrolled mismatch to a much more manageable residual backlog.

---

## What was validated

### Validated
- scope-aware ETL execution
- MySQL dictionary lookup
- backlog partition by scope
- P1 promotion impact
- P2 promotion impact
- residual promotion impact

### Confirmed working pattern
The following loop is now validated:

```text
not_found backlog
→ prioritize
→ build bridge
→ promote candidates to dictionary
→ rerun ETL
→ measure improvement
```

---

## Remaining open items

These do not block closing the phase, but they should be documented and revisited later.

### 1. Production runbook
Define:
- what runs automatically
- what stays under controlled/manual approval

### 2. Catalog governance process
Document how new dictionary candidates are:
- discovered
- reviewed
- promoted
- rejected

### 3. ETL telemetry cleanup
Some summary metrics and persisted backlog counts should be standardized and reviewed.

### 4. Residual backlog treatment
The residual not-found backlog is now small enough to be treated as:
- future mapping candidates
- or controlled manual review

---

## Recommended production posture

### Automatic
- Odoo read-only extraction
- scope application
- dictionary lookup
- snapshot generation
- backlog generation
- diagnostics exports

### Controlled / manual
- dictionary promotions
- historical-only decisions
- scope rule changes
- heuristic refinements

---

## Phase conclusion

The **Inventory Domain baseline is complete**.

The domain is:
- technically stable
- functionally advanced
- ready to support the next pipeline domains

The next recommended domain is:

# Purchases
