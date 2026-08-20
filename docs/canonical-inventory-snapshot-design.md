# canonical_inventory_snapshot Design

## Step

```text
Paso 18.17 - Diseñar canonical_inventory_snapshot
```

## Status

```text
closed 2026-08-20 (Paso 18.17-18.20), with a scope change from the
original title
```

## Final Outcome Note (read this first)

No separate `canonical_inventory_snapshot` table was built. Partway through implementation (Paso 18.20) it became clear that `analytics_inventory_snapshot` already carried the columns this design would have duplicated (`company_source_key`, `company_mapping_status`, `include_in_business_views`, `exclude_reason`). The project owner approved enriching `analytics_inventory_snapshot` directly instead, following the same single-flag pattern already validated in `analytics_purchase_order_lines`. This document is kept under its original filename for traceability of the decision trail, not because the original table name was implemented literally. See "Full Roadmap" below for what was actually built.

Wansoft inventory (`getstockinventory_inventario`) is still a separate, ungoverned legacy table, untouched by this work. Unifying it with the now-governed Odoo side remains open (see Section H equivalent in project status: unified analytical consumption layer).

---

## Purpose

This document defines `canonical_inventory_snapshot`, the missing governance layer that unifies Wansoft and Odoo inventory under `COMPANY_SOURCE`, following the same pattern already validated in the Purchases domain (`canonical_purchase_order_snapshot`).

The project currently has two inventory extraction paths that run fully independently, with no source governance and no unification:

```text
Wansoft path:
    pipelines/scheduler.py -> pipelines/jobs/inventory_job.py
    -> extract/inventory/wansoft_inventory.py
    -> legacy/wansoft/getStockInventory.py
    -> table getstockinventory_inventario (legacy schema, Spanish columns)

Odoo path:
    scripts/run_inventory_pipeline.py
    -> extract/inventory/odoo_inventory.py (stock.quant, unfiltered)
    -> odoo_inventory_snapshot -> analytics_inventory_snapshot -> dim_inventory_location
```

Neither path filters by `COMPANY_SOURCE`. The Wansoft legacy script pulls its own fixed subsidiary list regardless of which companies are officially Odoo. The Odoo path pulls every `stock.quant` row Odoo has, including companies that are officially Wansoft-sourced, plus internal provider companies (`EL BODEGON DE FITO`, `LAS EMPANADAS DE MARIA EVA`) that should not appear as operating branches.

There is no table that answers, for a given company and date, "what is the officially governed current inventory, regardless of source system."

---

## Purchases Migration Timeline Cross-Check (confirmed by project owner, 2026-08-20)

While validating Inventory governance, the project owner shared the real Odoo migration timeline for Purchases:

```text
2026-01  Antenas entered Odoo
2026-06  La Esquina Coyoacán and Tepeyac entered Odoo
2026-07  CentroMyJ (new branch), Oceanía and Acoxpa (Costa Nera) entered Odoo
2026-08  Puebla entered Odoo (new branch)
```

All of these except CentroMyJ and Puebla (which have no prior Wansoft history, being new branches) continue running Purchases in parallel in Wansoft as a backup.

This raised a real question: since Tepeyac, Oceanía and Acoxpa already entered Odoo the same way Coyoacán did (which is already `COMPANY_SOURCE = "odoo"`), should they also switch? The project owner confirmed explicitly:

```text
Wansoft remains the official Purchases source for Tepeyac, Oceanía and
Acoxpa for now. Odoo runs in parallel as backup/preparation, not as the
official source, until an explicit future decision.
```

No `COMPANY_SOURCE` change was made. This confirms the Inventory classification already built in Paso 18.19 is correctly aligned: Tepeyac, Oceanía and Acoxpa resolve to `parallel_diagnostic_odoo`, excluded from business views, Wansoft treated as official. The same reasoning that was applied to Napoles/Polyforum (Odoo data exists, Wansoft stays official) generalizes correctly to these three companies without any code change.

---

## Environment Governance Rule (confirmed by project owner, 2026-08-20)

```text
All development, construction and validation work happens exclusively in
the development environment (dev).

Production is not touched until:
1. The project is functionally complete in dev.
2. A real sample is reconciled (e.g. one month of Purchases, Sales and
   Inventory for Antenas) between what production currently returns and
   what the governed dev/test pipeline computes for the same period.
3. That reconciliation passes without unexplained discrepancies.

Only then is the project promoted to production, at which point every new
table is created there for the first time.
```

This rule was discovered after an attempted production run of `extract_odoo_inventory_location_master.py` failed cleanly (`Table doesn't exist`) before any write occurred, causing no harm to production. The self-provisioning DDL fix made to that script (and to `extract/inventory/odoo_inventory_etl.py`) remains correct and harmless in either environment, since `CREATE TABLE IF NOT EXISTS` is a no-op where the table already exists, but it will not be exercised against production until the reconciliation gate above is passed.

---

## Confirmed Governance Decision (input from project owner)

```text
COMPANY_SOURCE for inventory stays exactly as configured today.

Official Odoo-sourced companies (final source = odoo):
    Antenas
    La Esquina Coyoacán
    CentroMyJ
    Puebla

All other companies remain officially Wansoft-sourced.
```

Important clarification received directly from the project owner:

```text
Several Wansoft-sourced companies already have parallel data in Odoo
(Tepeyac, Oceanía, San Jerónimo, Acoxpa, Isabel La Católica, and possibly
others). The owner is not ready to cut these over to Odoo as the official
source. That Odoo data must remain visible for diagnostic/parallel review,
but must never be treated as the official current inventory for those
companies.
```

This is the same coexistence principle already confirmed for Purchases:

```text
Sales is the only domain that is always Wansoft.
Purchases already has both Odoo and Wansoft data coexisting in MySQL,
governed by COMPANY_SOURCE, with source_system preserved. Already validated.
Inventory must follow the same governance pattern.
```

---

## Core Design Decision

Inventory is a snapshot concept (current stock level), not a transactional history like Purchases. This changes how the Purchases pattern must be adapted:

```text
Purchases pattern (transactional, historical cutover):
    before operational_start_date -> Wansoft is final
    after operational_start_date  -> Odoo is final
    both periods coexist as history, never overlapping in "final" status

Inventory pattern (current-state snapshot, no historical cutover needed):
    for each company, at refresh time:
        final_inventory_source_status = odoo   if COMPANY_SOURCE[company] == "odoo"
        final_inventory_source_status = wansoft if COMPANY_SOURCE[company] == "wansoft"
    both sources are extracted and preserved in canonical_inventory_snapshot,
    but only one is flagged as the official/final row set per company at any
    given refresh.
```

This mirrors the pattern already validated in `analytics_purchase_order_lines`: **all rows are preserved**, eligibility for business-facing consumption is controlled by a flag, and excluded rows remain visible with a reason. Nothing is discarded.

---

## Target Table

```text
canonical_inventory_snapshot
```

Grain:

```text
1 row = 1 product x 1 source location x 1 source system x 1 refresh snapshot
```

Required columns (mirroring `canonical_purchase_order_snapshot` naming conventions):

```text
source_system                      -- 'odoo' | 'wansoft'
company_source_key                 -- resolved via get_company_source_key / WANSOFT_SUBSIDIARY_SOURCE_KEY
source_location_id                 -- Odoo stock.location id, or Wansoft branch id when applicable
source_product_id
product_code
product_name
stock_qty
snapshot_date
final_inventory_source_status      -- 'final_odoo_enabled' | 'final_wansoft_enabled' | 'parallel_diagnostic_odoo'
include_in_business_views          -- boolean
exclude_reason                     -- nullable text
is_internal_provider               -- boolean, true for Bodegón/Empanadas rows
refresh_run_id                     -- link to pipeline JSON log run_id
```

---

## Source Status Classification

```text
final_odoo_enabled
    COMPANY_SOURCE[company] == "odoo"
    row comes from Odoo stock.quant
    -> include_in_business_views = TRUE

final_wansoft_enabled
    COMPANY_SOURCE[company] == "wansoft"
    row comes from Wansoft getStockInventory
    -> include_in_business_views = TRUE

parallel_diagnostic_odoo
    COMPANY_SOURCE[company] == "wansoft"
    row comes from Odoo stock.quant (company already exists in Odoo in
    parallel, per ODOO_COMPANY_SOURCE_KEY, but is not yet the official source)
    -> include_in_business_views = FALSE
    -> exclude_reason = "company_source_is_wansoft_odoo_data_is_parallel"

internal_provider_excluded
    company resolves to EL BODEGON DE FITO or LAS EMPANADAS DE MARIA EVA
    -> include_in_business_views = FALSE
    -> exclude_reason = "internal_provider_company"
    -> is_internal_provider = TRUE

unmapped_location_pending_review
    source_location_id does not resolve to a known company_source_key
    (this covers the currently unidentified prefixes TACOS, FACY seen in
    inventory_location_company_mapping_worklist.csv)
    -> include_in_business_views = FALSE
    -> exclude_reason = "pending_location_company_mapping"
```

There is no `wansoft_history_before_odoo` equivalent for Inventory, because inventory has no meaningful historical cutover the way a purchase document date does. If this project later needs point-in-time historical inventory reconstruction, that must be a separate design, not part of this table.

---

## Critical Finding: location_name Prefix Is Not a Reliable Company Discriminator

Real data from `stg_odoo_inventory_location_master` (first run, ENV=dev, 2026-08-20, 388 rows) proved that the `FONDA` location prefix is shared identically across at least 8 different Odoo companies:

```text
company_id  odoo_company_name              company_source_key      COMPANY_SOURCE
5           FONDA ARGENTINA                Isabel La Católica      wansoft
6           FONDA ARGENTINA SAN JERONIMO   San Jeronimo             wansoft
8           FONDA ARGENTINA AEROPUERTO     Aeropuerto                wansoft
9           FONDA ARGENTINA LAS ANTENAS    Antenas                   odoo
14          FONDA ARGENTINA POLYFORUM      (excluded, out of scope)  n/a
17          FONDA ARGENTINA VALLEJO        Vía Vallejo                wansoft
18          FONDA ARGENTINA VIADUCTO       Viaducto                   wansoft
19          FONDA ARGENTINA TOLLOCAN       Metepec                    wansoft
```

This confirms, with real data rather than theory, that any classification based on `location_name` prefix (including the original manual worklist approach from Paso 18.14/18.15) would have been structurally wrong for the largest single location tree in Odoo. `company_id` from `stg_odoo_inventory_location_master` is the only reliable join key. `FACY` (company_id 36, `FONDA ARGENTINA COYOACAN`) and `FAMAQ` (company_id 10, `FONDA ARGENTINA MAQ`) happened to be unique per company, which is why they looked safe in isolation, but that was not a generalizable pattern.

---

## Resolved Location Prefixes (confirmed by project owner)

```text
FACY  -> La Esquina Coyoacán (company_source_key = "La Esquina Coyoacán")
         COMPANY_SOURCE["La Esquina Coyoacán"] = "odoo"
         Rows under this prefix classify as final_odoo_enabled.

TACOS -> known Odoo location, explicitly not activated for inventory
         purposes at this time. This is an owner decision, not a data gap.
         Rows under this prefix classify as deferred_not_active and remain
         excluded from business views with
         exclude_reason = "deferred_not_active_per_owner_decision".
```

This confirmation came directly from the project owner, not from name-pattern inference, so it satisfies the governance rule (explicit approval, not automatic matching).

## Open Questions Resolved

All previously open prefixes are now resolved with real Odoo data and explicit owner confirmation:

```text
FACY   -> company_id 36 -> La Esquina Coyoacán -> final_odoo_enabled
FAMAQ  -> company_id 10 -> Tepeyac             -> parallel_diagnostic_odoo (COMPANY_SOURCE still wansoft)
FONDA  -> shared by company_id 5, 6, 8, 9, 14, 17, 18, 19 (see finding above)
TACOS  -> deferred_not_active_per_owner_decision, excluded regardless of company
```

`core/config/companies.py` was updated (Paso 18.18) with the four newly confirmed mappings (`FONDA ARGENTINA AEROPUERTO`, `FONDA ARGENTINA VALLEJO`, `FONDA ARGENTINA VIADUCTO`, `FONDA ARGENTINA TOLLOCAN`).

`FONDA ARGENTINA POLYFORUM` (company_id 14) required a distinct governance category, not full exclusion. Per project owner correction:

```text
Polyforum must never be sourced from Odoo.
Polyforum is a valid branch for Sales via Wansoft, and only for Sales.
Polyforum is excluded from Purchases and Inventory entirely, regardless
of source system.
```

This was implemented as a new `SALES_ONLY_COMPANIES` governance set, distinct from `ODOO_INTERNAL_PROVIDER_COMPANIES`. `get_domain_company_source` and `should_include_company_in_final_domain` are now domain-aware for this category: `sales -> wansoft, include=True`, `purchases/inventory -> sales_only, include=False`. Verified against `scripts/test_company_source_governance.py` (no regression) plus an ad hoc check across sales, purchases and inventory domains for all 5 new cases and for `EL BODEGON DE FITO` as a regression control.

Open item found during this fix: `FONDA ARGENTINA POLYFORUM` has no matching entry in `CUENTAS_SUCURSALES` (no Wansoft subsidiary id/password configured). Sales extraction for this branch cannot run through the existing Wansoft pipeline until that entry is added. This is not yet resolved.

This fix also closes a latent data quality gap that existed in Purchases: before this correction, any Odoo purchase record for a company like Polyforum, absent from all governance dictionaries, would have silently defaulted to `wansoft` instead of being explicitly excluded from Purchases/Inventory.

---

## Governance Rules Reused From Existing Design

```text
Do not infer company_source_key from location_name.
Do not infer company_source_key from normalized_location_name.
Do not infer company_source_key from source_location_id text patterns.
Do not infer company_source_key from location_usage_type.
Internal provider companies are excluded from operational branch facts,
but preserved as vendor/provider context where applicable.
All canonical rows are preserved; exclusion is a flag, not a deletion.
```

---

## Extraction Path Changes Required

```text
1. extract/inventory/inventory_router.py already implements correct
   COMPANY_SOURCE-based routing (extract_inventory_by_company). It is
   currently unused. It becomes the single entry point for the canonical
   build, replacing direct unconditional calls to wansoft_inventory.py and
   odoo_inventory.py.

2. The Wansoft legacy extraction (legacy/wansoft/getStockInventory.py) is
   NOT modified. Its output (getstockinventory_inventario) becomes an input
   source read by the new canonical build step for companies where
   COMPANY_SOURCE == "wansoft".

3. The Odoo extraction (extract/inventory/odoo_inventory.py) is NOT
   modified either. Its full unfiltered output remains the input to
   odoo_inventory_snapshot / analytics_inventory_snapshot /
   dim_inventory_location, which stay as the diagnostic and governance
   foundation layer they already are. The canonical build reads from
   analytics_inventory_snapshot and classifies each row using the source
   status rules above.

4. No change to pipelines/scheduler.py or scripts/run_inventory_pipeline.py
   in this step. Wiring the canonical build into the scheduled/orchestrated
   path is explicitly deferred to Paso 18.21, after dry-run validation.
```

This keeps the change low-risk: nothing that currently runs in production (the hourly scheduler) is touched until the canonical layer is built and validated standalone.

---

## Validation Requirements (for Paso 18.19)

```text
canonical_inventory_snapshot_exists
grain_unique (source_system, source_location_id, source_product_id, snapshot_date)
no_null_company_source_key_for_included_rows
no_internal_provider_rows_included_in_business_views
no_company_with_two_final_source_systems_simultaneously
final_status_matches_company_source_governance
row_count_reconciles_to_analytics_inventory_snapshot_and_getstockinventory_inventario
stock_qty_reconciles_per_source_system
distribution_by_final_inventory_source_status_available
distribution_by_company_source_key_available
```

The critical check is `no_company_with_two_final_source_systems_simultaneously`: for any given `company_source_key`, only one `source_system` may carry `include_in_business_views = TRUE` at a time. This is the check that directly prevents the exact risk you flagged, duplicated or conflicting inventory per branch in final reports.

---

## What This Enables

```text
A single governed table that answers "current official inventory by
company" without the consumer needing to know source system.
Parallel Odoo diagnostic data for not-yet-migrated branches remains
queryable but never leaks into business-facing views.
Foundation for future company-level and branch-level inventory analytics
that are safe to expose in reports without narrating source system.
```

## What This Does Not Solve Yet

```text
Does not resolve the unmapped TACOS / FACY locations (pending owner input).
Does not implement inventory valuation or unit cost.
Does not change the hourly scheduler or the orchestrated pipeline
(deferred to Paso 18.21).
Does not retroactively reconstruct historical point-in-time inventory.
```

---

## Recommended Next Step (revised)

The original plan for Paso 18.18 assumed `company_source_key` could be resolved per inventory row the same way Purchases does it, from a `company_name` column already present in the Odoo snapshot. That assumption does not hold for Inventory: `extract/inventory/odoo_inventory.py` reads `stock.quant`, which does not return `company_id` or `company_name` at all, only `location_id`.

Guessing the company from the location name prefix (`FACY`, `FAMAQ`, `FONDA`, `TACOS`) would violate the project's own governance rule against name-based inference. Two prefixes were resolved by explicit owner confirmation (`FACY`, `TACOS`, see above), but the remaining prefixes cannot be resolved that way reliably at scale.

```text
Paso 18.18 - Ejecutar y cerrar la extracción del maestro de ubicaciones
Odoo ya codificada y nunca ejecutada, contra dev exclusivamente:

    scripts/extract_odoo_inventory_location_master.py
        -> stg_odoo_inventory_location_master (company_id, company_name
           read directly from Odoo stock.location configuration)

    scripts/validate_odoo_inventory_location_master.py
        -> validates the staging table

This resolves company_id per location from Odoo's own structured
configuration instead of name-prefix inference, and directly answers the
FAMAQ / FONDA open question with authoritative data instead of a guess.
```

## Full Roadmap (updated after environment governance rule)

```text
Paso 18.17  Design (this document)                              done
Paso 18.18  Resolve company_id via Odoo location master, in dev  done
            (closed 2026-08-20: stg_odoo_inventory_location_master
            self-provisioning fixed, 388 rows, 10/10 validations passed
            in dev; FACY/FAMAQ/FONDA/TACOS resolved; core/config/companies.py
            updated with 4 new mappings and SALES_ONLY_COMPANIES governance)
Paso 18.19  Implement apply_inventory_company_source_flags and
            canonical_inventory_snapshot, in dev            done
            (closed 2026-08-20: implemented as
            analysis/build_inventory_company_source_eligibility_report.py,
            classification validated against all 1660 pre-refresh rows,
            100% reconciled, TACOS FA FUENTES and Polyforum/Napoles
            resolved with real Odoo data)
Paso 18.20  Enrich analytics_inventory_snapshot with governed
            company_source_key (pivoted from a separate canonical table,
            see below), in dev                               done
            (closed 2026-08-20: build_analytics_inventory_snapshot.py and
            validate_analytics_inventory_snapshot.py updated;
            build_dim_inventory_location.py updated to prefer the Odoo
            location master resolution over the empty manual seed, manual
            seed kept as override mechanism; full downstream cascade
            rebuilt and reconciled: analytics_inventory_snapshot (1380
            rows) -> vw_inventory_physical_snapshot (294) +
            vw_inventory_non_physical_snapshot (1086) = 1380 ✓ ->
            analytics_inventory_current_product_location (294 rows,
            4327.4549 stock_qty) -> dim_inventory_location (70 locations,
            14 company-eligible, 17/17 validations passed)
Paso 18.21  Reconciliation gate (preliminary): compare governed dev
            output against live Odoo, queried independently with no
            shared code. Closed 2026-08-20 with one case (Purchases,
            Antenas, July 2026): exact match on orders, amount_total,
            lines and price_total, zero difference. Confirms the
            Odoo-final pattern computes correctly.

            Explicitly NOT the final acceptance test. Project owner
            decision (2026-08-20): the real final functional test must
            compare at least two branches against the production
            database itself (not just live Odoo), and must only be run
            once the project is functionally complete, immediately
            before production promotion (Paso 18.22). This preliminary
            gate reduces risk before that point but does not replace it.
Paso 18.22  Production promotion, only if Paso 18.21 passes without
            unexplained discrepancies. All new tables are created in
            production for the first time at this step.
Paso 18.23  Final documentation and closeout
```
