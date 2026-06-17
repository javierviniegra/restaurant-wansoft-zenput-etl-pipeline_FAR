

# Inventory Domain Runbook

## Purpose

This runbook describes how the inventory pipeline is expected to operate after the closeout of the baseline inventory phase.

---

## Operating model

### Source system
- Odoo is used as the operational source
- Odoo is treated as **read-only**

### Governance layer
- MySQL stores all catalog intelligence
- Inventory mapping is resolved in MySQL
- Scope classification is resolved in MySQL

---

## Main execution flow

```text
1. Extract Odoo inventory
2. Consolidate snapshot by product + location
3. Merge scope classification
4. Split scope buckets
5. Apply inventory dictionary only to allowed scope
6. Write:
   - odoo_inventory_snapshot
   - odoo_inventory_backlog
7. Export diagnostics if needed
```

---

## Config-driven behavior

The ETL is controlled through environment variables.

### Example
```env
INVENTORY_ETL_SALES_REFERENCE_SCOPE=restaurantes
INVENTORY_ETL_SALES_REFERENCE_SOURCE=sales_reference
INVENTORY_ETL_SCOPE_INCLUDE=shared_cross_company
INVENTORY_ETL_SCOPE_BACKLOG=bodegon,empanadas,bodegon_candidate,empanadas_candidate,review_scope,operational_non_inventory
```

---

## Scope buckets

### Included in current inventory ETL
- `shared_cross_company`

### Sent directly to backlog
- `scope_restaurantes_sales_reference`
- `scope_bodegon`
- `scope_bodegon_candidate`
- `scope_empanadas`
- `scope_review_scope`
- `scope_operational_non_inventory`

---

## Dictionary behavior

### Current dictionary statuses
- `approved`
- `pending_review`
- `historical_only`

### ETL rules
- `approved` → usable for ETL
- `pending_review` → backlog
- `historical_only` → backlog / reference only

---

## Backlog types

### Scope backlog
Products excluded from the active inventory ETL because of business scope:
- bodegón
- empanadas
- sales reference items
- review scope
- operational non-inventory

### Functional backlog
Products that were eligible for dictionary lookup but still unresolved:
- `not_found`
- `pending_review`
- `historical_only`

---

## Promotion workflow

The inventory dictionary is extended through controlled waves:

```text
1. Analyze not_found
2. Prioritize candidates
3. Build lifecycle-aware bridge
4. Promote approved candidates to dictionary
5. Rerun ETL
6. Measure impact
```

### Current bridge sources
- `bridge_report`
- `p1_bridge`
- `p2_bridge`
- `residual_bridge`

---

## What should be automated

### Safe to automate
- snapshot extraction
- scope merge
- dictionary lookup
- ETL execution
- backlog generation
- diagnostics export

### Keep controlled initially
- dictionary promotions
- scope heuristic changes
- historical-only decisions
- business-rule changes

---

## Current closeout state

At inventory phase closeout:

- snapshot rows: 1660
- residual functional not_found backlog: 98 unique products
- residual pending_review backlog: 5 unique products

This is considered a stable operational baseline in test.

---

## Recommended next domain

# Purchases
The inventory baseline is sufficiently mature to move into the purchases domain.
