# Wansoft-Odoo Inventory Balance Unification Design

## Step

```text
Paso 18.22 - Diseñar la unificación de saldo de inventario Wansoft/Odoo
```

## Status

```text
design in progress -- transfer netting resolved 2026-08-25, balance
window resolved 2026-08-26 (full history since Inventario inicial),
product key resolution confirmed 2026-08-25. Remaining before
build_/validate_: final confirmation of the window decision with the
project owner in those exact terms (implied by action, not yet stated
verbatim), then implementation.
```

---

## Purpose

Deliver a single, governed "current inventory balance" per `company_source_key` and product that hides which source system produced it, following the same coexistence pattern already validated in Purchases (`canonical_purchase_order_snapshot`, `source_system` preserved, `COMPANY_SOURCE` decides the official source per company).

This corrects course from an earlier assumption. The original plan for this work targeted `legacy/wansoft/getStockInventory.py` / `getstockinventory_inventario`, a point-in-time stock snapshot script. The project owner confirmed (2026-08-21) that this script is **not** part of the actual current Wansoft workflow. The real inventory extraction in production use is:

```text
legacy/wansoft/automaticos/getInputInventory.py   -> getinputinventory_entrada  (entradas)
legacy/wansoft/automaticos/getOutgoingInventory.py -> getOutgoingInventory_Salida (salidas)
```

`getinputinventory_entrada` already exists and is already governed: it is the same table that feeds the Wansoft canonical Purchases layer (`extract/purchases/canonical_purchase_etl.py`, `apply_wansoft_purchase_source_flags`). No new work is needed on the entradas side for Purchases purposes; this design only adds an inventory-balance read of the same table.

`getOutgoingInventory_Salida` has no governance today. This is the genuinely new piece.

`legacy/wansoft/automaticos/getOutputInventory.py`, mentioned by the project owner as something to include later, **does not exist in the repository**. It is not an unused script; it has not been created yet. Out of scope for this design until it exists.

---

## Core Architectural Problem

Wansoft and Odoo represent inventory with fundamentally different grains, not just different column names:

```text
Wansoft: movement-based
    current_balance = SUM(entradas.Cantidad) - SUM(salidas.Cantidad)
    per subsidiary + product, accumulated over time

Odoo: snapshot-based
    current_balance = stock.quant current value
    per company + product + location, read directly, no summation needed
```

Project owner decision (2026-08-21): the unifier must deliver a **comparable current balance**, not just a schema-homogenized union of two different grains. This means the Wansoft side must be aggregated into a balance before it can sit next to the Odoo side under one schema.

---

## Source Table Schemas (confirmed from actual CREATE TABLE statements)

### getinputinventory_entrada (entradas)

```text
subsidiary_name    VARCHAR(255)   -- Wansoft numeric subsidiary id as text, e.g. "4959"
IdProducto         INT
CodigoProducto     VARCHAR(50)
NombreProducto     VARCHAR(255)
Cantidad           DECIMAL(15,10)
TipoEntrada        VARCHAR(50)    -- entry type: purchase receipt, transfer-in, adjustment, etc.
IdTransferencia    INT            -- non-null when this entry is a warehouse transfer, not a purchase
FechaEntrada       DATETIME
```

### getOutgoingInventory_Salida (salidas)

```text
subsidiary_name    VARCHAR(255)   -- same convention as entradas
IdProducto         INT
CodigoProducto     VARCHAR(50)
NombreProducto     VARCHAR(255)
Cantidad           DECIMAL(15,10)
TipoSalida         VARCHAR(50)    -- exit type
IdDetalleVenta     VARCHAR(50)    -- non-null when this exit is tied to a sale (COGS consumption)
IdTransferencia    VARCHAR(50)    -- non-null when this exit is a warehouse transfer, not consumption
FechaSalida        DATETIME
```

### Confirmed: no encoding risk on subsidiary_name

Unlike `getstockinventory_inventario.Sucursal` (confirmed corrupted for accented subsidiary names, historical data quality issue from 2024, root cause traced to the connection/column charset in effect at insert time, not a currently-active bug), `subsidiary_name` here stores the **numeric Wansoft subsidiary id as text** (e.g. `"4959"`), not the descriptive name. This is proven safe at scale: `extract/purchases/canonical_purchase_etl.py::resolve_wansoft_company_source_key()` already resolves this exact field successfully across 745,161 real rows in the validated Purchases pipeline (2026-08-20 run). This design reuses that function directly. No new mapping logic is needed for company resolution.

---

## Movement Type Catalog (confirmed from real dev data, 2026-08-21)

Actual `TipoEntrada` distribution in `getinputinventory_entrada` (1,743,882 total rows):

```text
Factura                        745,597 rows   0 with IdTransferencia
Transferencia                  423,506 rows   423,506 with IdTransferencia (100%)
Entrada con canal              286,447 rows
Ajuste de inventario           148,907 rows
Producto procesado              82,332 rows
Orden de compra a proveedor     46,479 rows   0 with IdTransferencia
Inventario inicial               7,979 rows
Eliminado por ajuste de lote      2,438 rows   153 with IdTransferencia
Anulación                           73 rows
Ajuste por lote                     55 rows
Cancelación de transferencia         7 rows   7 with IdTransferencia
Devolución                           2 rows   2 with IdTransferencia
```

Note: `TipoEntrada` values with accented characters (`Anulación`, `Cancelación de transferencia`, `Devolución`, 82 rows total) show the same historical encoding corruption already found in `getstockinventory_inventario.Sucursal` (stored as `?` instead of the accented letter). Low volume (82 of 1.74M rows, 0.005%), does not materially affect the balance, but exact-text matching on these three values will silently miss corrupted rows. Grouping/aggregation is unaffected since it groups by the corrupted value consistently.

## Confirmed Exclusion Rule (project owner, 2026-08-21)

```text
TipoEntrada = 'Orden de compra a proveedor' must be excluded from the
balance calculation entirely.
```

Reason (project owner): a purchase order is a prior state before merchandise physically arrives. It represents what is still expected to arrive, not physical stock on hand. Including it would overstate the balance with inventory that does not yet exist in the warehouse. It may be useful later as a separate "pending purchase orders" diagnostic, out of scope here.

## Transfer and Non-Purchase Movement Risk — RESOLVED (2026-08-25)

`Transferencia` (423,506 rows, 100% carrying `IdTransferencia`) represents warehouse-to-warehouse movement. At the target grain of this design (`company_source_key`, not per-warehouse), a transfer between two of the company's own warehouses should mathematically net to zero when entradas and salidas are summed together, **if and only if** both the departure (salida) and arrival (entrada) sides are captured symmetrically for the same transfer.

```text
Risk: if capture is asymmetric (e.g. the salida side is missing, delayed,
or recorded under a different subsidiary due to a data entry error), the
transfer would distort the balance instead of cancelling out.
```

**Verified empirically 2026-08-25**, once `getinputinventory_entrada` was refreshed in dev for one Wansoft-final subsidiary (Acoxpa, 90-day window, then widened to the full available overlap with `getOutgoingInventory_Salida`, 2025-01-01 to 2026-08-20). The netting hypothesis does **not** hold via simple sum, for a structural reason, not a data quality gap:

```text
Acoxpa, TipoEntrada='Transferencia', 2025-01-01 to 2026-08-20:
  8,472 entrada rows, 423,203.17 total Cantidad, 2,883 distinct IdTransferencia

Of those:
  3,004 rows (35%) DO have a matching IdTransferencia in getOutgoingInventory_Salida
    with TipoSalida='Transferencia' for the same subsidiary -> nets correctly today.
  5,468 rows (65%, 261,822.59 Cantidad, 1,880 distinct IdTransferencia) have NO
    matching salida row anywhere in the dataset -> no counterpart exists to net against.
```

Root cause confirmed directly against live Wansoft (project owner checked the UI, not inferred): for one of the unmatched IdTransferencia (`5377-5366-2069017`, 2025-04-30, Almacén Central Acoxpa -> Salón Gasto Acoxpa, same subsidiary both sides, status "Exitosa"), Wansoft shows the identical transfer document under **both** `Inventario / Entradas y Salidas / Transferencias / Recibidas` and `.../ Transferencias / Realizadas`. It is a single transaction object in Wansoft, not two independent ledger entries. `GetInputInventory_Xml` mirrors it into the entrada feed as `TipoEntrada='Transferencia'`; `GetOutgoingInventory_Xml` does not expose a matching outgoing line for this kind of intra-subsidiary transfer at all. This is a structural gap in what that SOAP endpoint returns, not a bug in `getOutgoingInventory.py` and not missing/delayed capture — no amount of re-extraction will produce the missing salida side.

Project owner additionally confirmed (2026-08-25): **near 100% of transfers are intra-subsidiary** (between warehouses/locations of the same company); cross-company transfers are essentially never seen in practice. This means the unmatched-majority pattern found for Acoxpa is expected to generalize, not an Acoxpa-specific anomaly.

**Confirmed exclusion rule (project owner, 2026-08-25):**

```text
TipoEntrada = 'Transferencia' AND TipoSalida = 'Transferencia' are both
EXCLUDED from the balance calculation entirely.

Reason: intra-subsidiary transfers relocate existing stock between a
company's own warehouses; they do not represent new physical stock
arriving or being consumed. Since Wansoft's outgoing SOAP endpoint does
not reliably expose the departure leg of these transfers, summing the
entrada side alone would inflate the balance. Excluding both sides is
the same treatment already applied to 'Orden de compra a proveedor'
(entrada) and 'Error de captura' / 'Factura de egresos rechazada' (salida):
remove event types that cannot be trusted to represent net physical
stock change, rather than attempt unreliable netting.
```

Other movement types (`Ajuste de inventario`, `Producto procesado`, `Inventario inicial`, `Ajuste por lote`, `Eliminado por ajuste de lote`, `Anulación`, `Devolución`, `Entrada con canal`) all represent real physical stock changes for different reasons and are included in the balance by default. No exclusion confirmed for these; revisit if a specific type is found to distort results during validation.

---

## TipoSalida Catalog (confirmed from real production data, 2026-08-21, read-only)

Production's `getOutgoingInventory_Salida` is actively current (`MAX(FechaSalida): 2026-08-19`), unlike dev's `getstockinventory_inventario` (frozen since 2024-06-01). This confirms the dev freshness gap found earlier was specific to that one dev table, not a sign that production's Wansoft pipeline itself is broken.

```text
Venta                              34,883,596 rows  100% with IdDetalleVenta
Transferencia                         558,672 rows  100% with IdTransferencia
Producción de subproducto             524,990 rows
Merma                                 219,497 rows
Producción de subproducto con canal   217,174 rows
Consumo                               177,320 rows  70% with IdDetalleVenta
Ajuste de inventario                  170,127 rows
Venta cancelada                        23,725 rows  100% with IdDetalleVenta
Ajuste por lote                         2,840 rows
Error de captura                        1,884 rows
Desperdicio                             1,384 rows
Devolución de producto                    699 rows
Registro de nota de crédito               583 rows
Factura de egresos rechazada              349 rows
Robo                                       40 rows
```

## Confirmed Exclusion/Inclusion Rules (project owner, 2026-08-21)

```text
TipoSalida = 'Error de captura' -> EXCLUDED.
    Reason (owner): products recorded as sold by data entry error, not a
    real movement.

TipoSalida = 'Factura de egresos rechazada' -> EXCLUDED.
    Reason (owner): a rejected outgoing invoice; the movement did not
    actually happen.

TipoSalida = 'Venta cancelada' -> INCLUDED, same treatment as 'Venta'.
    Reason (owner): represents inventory already consumed in preparation
    (cooked/fabricated) for an order that was then cancelled; the
    ingredients were wasted, not returned to stock.
    Verified empirically: Cantidad is 100% positive for all 23,725 rows
    (0 negative, 0 zero), identical sign pattern to 'Venta' (also 100%
    positive, 0 negative). This confirms it behaves as a real consumption
    event, not a reversal, consistent with the owner's interpretation.
```

## Updated Balance Calculation Rule (2026-08-25: adds Transferencia exclusion)

```text
current_balance_qty =
    SUM(getinputinventory_entrada.Cantidad
        WHERE subsidiary resolves to this company
          AND TipoEntrada NOT IN ('Orden de compra a proveedor', 'Transferencia'))
  - SUM(getOutgoingInventory_Salida.Cantidad
        WHERE subsidiary resolves to this company
          AND TipoSalida NOT IN ('Error de captura', 'Factura de egresos rechazada', 'Transferencia'))
GROUP BY company_source_key, wansoft_code
```

All other `TipoEntrada` / `TipoSalida` values are included by default (real physical movements: sales, production, adjustments, waste, theft, credit notes, returns). The `Transferencia` netting risk (see above) is now resolved: both sides are excluded rather than netted, since Wansoft does not reliably expose a matching outgoing leg for intra-subsidiary transfers.

---

## Proposed Target Grain

```text
1 row = 1 company_source_key x 1 product (wansoft_code-resolved) x 1 source_system
```

Current balance only, not a time series. Matches how `analytics_inventory_snapshot` and `analytics_inventory_current_product_location` already work (current-state, refreshed on each run), not a historical ledger.

## Proposed Columns

```text
company_source_key
source_system                    -- 'odoo' | 'wansoft'
wansoft_code                     -- shared product key, same governance as Purchases
product_name
current_balance_qty
final_inventory_source_status    -- reuse the same vocabulary already validated in
                                    analytics_inventory_snapshot.company_mapping_status:
                                    final_odoo_enabled, final_wansoft_enabled (new),
                                    parallel_diagnostic_odoo, internal_provider_excluded,
                                    out_of_scope_excluded, unmapped_location_pending_review
include_in_business_views
exclude_reason
refreshed_at
```

## Balance Calculation Rule (Wansoft side)

```text
current_balance_qty =
    SUM(getinputinventory_entrada.Cantidad
        WHERE subsidiary resolves to this company
          AND TipoEntrada NOT IN ('Orden de compra a proveedor', 'Transferencia'))
  - SUM(getOutgoingInventory_Salida.Cantidad
        WHERE subsidiary resolves to this company
          AND TipoSalida NOT IN ('Error de captura', 'Factura de egresos rechazada', 'Transferencia'))
GROUP BY company_source_key, wansoft_code
```

`Orden de compra a proveedor`, `Error de captura`, `Factura de egresos rechazada` and `Transferencia` (both sides) are excluded per the confirmed rules above.

Only computed for companies where `COMPANY_SOURCE[company] == "wansoft"` (final source). For companies where Odoo is final, the Wansoft side is not computed as a balance at all in this table; it would need its own separate diagnostic treatment if ever required, mirroring how Purchases keeps Odoo-parallel data visible but excluded.

## Balance Source (Odoo side)

Read directly from the already-governed `analytics_inventory_snapshot` (`company_mapping_status = 'final_odoo_enabled'`, `include_in_business_views = TRUE`), grouped by `company_source_key` + product. No new extraction needed; this table already exists and is validated.

---

## Product Key Reconciliation Needed

Wansoft entradas/salidas use `CodigoProducto` / `NombreProducto` / `IdProducto`. The existing Purchases governance already resolves Wansoft product identity to `wansoft_code` via `dim_product` and the inventory dictionary (`inventory_mapping_dictionary`). This design reuses that resolution rather than building a new one. Needs to be confirmed empirically against `getOutgoingInventory_Salida` specifically (only `getinputinventory_entrada` has been proven so far, via Purchases).

---

## Known Open Items Before Implementation

```text
[x] Resolve the transfer double-counting risk (TipoEntrada / TipoSalida
    review with project owner) -- RESOLVED 2026-08-25: exclude
    TipoEntrada='Transferencia' and TipoSalida='Transferencia' entirely,
    see "Transfer and Non-Purchase Movement Risk" above.
[x] Confirm getOutgoingInventory_Salida.CodigoProducto resolves cleanly
    against the existing product dictionary, same as entradas does --
    RESOLVED 2026-08-25: checked against dim_product (the actual master
    table used for wansoft_code resolution, 2,179 rows; the smaller
    inventory_mapping_dictionary, 287 rows, is Odoo<->Wansoft bridge-only
    and not the right comparison). Salida resolves 926/1,055 distinct
    CodigoProducto (87.8%); entrada resolves 1,284/1,475 (87.1%). Salida
    is not a worse case than entrada -- coverage is equivalent.
[x] Decide the balance calculation window -- RESOLVED 2026-08-26: full
    history since each subsidiary's `Inventario inicial` (2021-2022), not
    a bounded/rolling window. A rolling window would measure net movement
    in the window, not actual stock on hand -- mathematically wrong for a
    "current balance". Dev's getOutgoingInventory_Salida only covered
    from 2025-01-01 (missing 3-4 years vs. entrada's full history), which
    would have made this option impossible; resolved by copying the
    missing 2021-2024 history directly from production (read-only) into
    dev instead of re-extracting via SOAP. Verified exact match against
    production for every year: 27,308,990 total rows,
    MIN(FechaSalida)=2021-08-01, MAX(FechaSalida)=2026-08-20.

    Second gap found and closed the same day: even the "already covered"
    2025-2026 portion of dev turned out to have a 13-month hole (2025-04-14
    to 2026-05-22, identical boundary across all 15 subsidiaries -- the gap
    between the old undocumented pre-existing dev data and this week's
    90-day SOAP extraction; the middle was never extracted by anyone).
    Found by comparing dev vs. production row counts per subsidiary for
    the same window (dev had ~1/3 of production's rows; ruled out
    duplication in production first via COUNT(*) = COUNT(DISTINCT
    IdSalida)). Closed by copying ~7.6M rows from production for that
    window, same method. Post-fix, dev matches production within a few
    thousand rows per subsidiary, fully explained by the ~5 most recent
    days not yet extracted (dev max 2026-08-20 vs. production 2026-08-25).
    Per-subsidiary Inventario-inicial-vs-first-salida check also run: all
    15 in-scope subsidiaries have salida coverage starting within 0-9 days
    of their Inventario inicial date (normal onboarding lag, not a gap).
[x] getOutgoingInventory_Salida has data in dev now (extracted 2026-08-21,
    3,914,313 rows, since 2025-01-01); getinputinventory_entrada refreshed
    in dev for one subsidiary (Acoxpa, 2026-08-25, MAX(FechaEntrada) moved
    from 2026-06-09 to 2026-08-24). Remaining 14 Wansoft-final subsidiaries
    not yet refreshed -- Acoxpa was used as the validation sample per
    project owner decision (full 15-subsidiary refresh at 90 days would
    take ~4 days continuous runtime at pre-index speed; see performance
    finding in PROJECT_CONTEXT_REPORT.md).
[ ] Confirm no other currently-active legacy script also writes to
    getOutgoingInventory_Salida or getinputinventory_entrada outside
    of what's documented here
[ ] getinputinventory_entrada has no index on (IdEntrada, subsidiary_name);
    added in dev 2026-08-25 as idx_identrada_subsidiary (online, no data
    change) to fix a full-table-scan performance problem in
    getInputInventory.py's per-row dedup check. Decide whether to add this
    index to the script's self-provisioning DDL before this runs against
    production for the first time.
```

---

## Related Legacy Script Inventory (context, not yet actioned)

Provided by the project owner (2026-08-21) as the actual current legacy footprint, for a separate cleanup pass (identify unused scripts, move or remove them):

```text
Currently used:
    automaticos/extractAllOrdersByDay.py   (sales, reads XML)
    automaticos/getAllOrdersByDay.py       (sales, pulls XML from Wansoft)
    automaticos/getCostReport_SemanaPyQ.py
    automaticos/getExpenses.py             (vendor invoices)
    automaticos/getInputInventory.py       (inventory entradas)
    automaticos/getOutgoingInventory.py    (inventory salidas)
    automaticos/getTablajeriaReport.py
    automaticos/getTotalCostByDate.py
    descargarCostoWansoft/descargarCostoWansoft.py
    descargarCostoWansoft/getGlobalCashClosing.py
    zenput/zenput_mysql_forms.py
    zenput/zenput_mysql_tasks.py

Wanted but not yet created:
    automaticos/getOutputInventory.py

Not confirmed as used (candidates for archive/removal, pending owner review):
    legacy/wansoft/getStockInventory.py
    legacy/wansoft/descargarComprasWansoft.py
    legacy/wansoft/getCostReport_update.py
    legacy/wansoft/getGlobalCashClosing_update.py
    legacy/wansoft/getStockInventory.py (duplicate note, confirmed unused above)
    legacy/wansoft/descargarInventarioWansoft.py
```

This cleanup is tracked separately, not part of this design's scope.

---

## Known Related Finding (separate domain, logged not solved)

Wansoft cost reports return zero for Puebla and CentroMyJ because those branches no longer have purchases loaded in Wansoft (fully migrated to Odoo). The cost reports need to be updated to source cost data from Odoo for these two companies. This is a Costs-domain issue, not Inventory, and is out of scope for this design. Logged here so it is not lost.

---

## First Build Result and Data Quality Finding (2026-08-26)

`scripts/build_analytics_inventory_balance.py` and
`scripts/validate_analytics_inventory_balance.py` implemented and run
successfully in dev (9/9 validations PASS, including exact reconciliation of
the stored total against a fresh independent recomputation from source).

```text
wansoft: 11,469 rows, total_balance_qty = -374,434.62
odoo:       165 rows, total_balance_qty =    5,521.19
```

The large negative Wansoft total is **not a build bug** (mechanically verified
correct) but a real per-subsidiary data quality pattern:

- Acoxpa (the subsidiary validated most extensively in this project) has small,
  plausible near-zero balances across the board (e.g. -189.99, -105, -30.88,
  -21, -6.37 units) -- the formula behaves exactly as expected here.
- Metepec concentrates almost all the extreme positive outliers, several with
  `salida_qty = 0` despite tens of thousands of units of entrada (Bolillo
  95,867; Palillo estuchado 65,000; Pastillas de Menta 50,100; Servilleta de
  Papel 49,056; Sal Refinada 39,010; Ketchup Sachets 28,009) -- operationally
  implausible, points to inconsistent salida-logging discipline at that
  subsidiary specifically, not a data gap in this project's extraction.
- Vía Vallejo, Isabel La Católica, Cancún, Playa del Carmen and Taquería
  Viaducto concentrate the most negative outliers, in high-turnover disposable
  consumables (paper napkins, charcoal, mints, placemats, bread) where
  recorded salida consistently exceeds recorded entrada.

**Metepec explained (project owner, 2026-08-26):** Metepec is a franchise
location. Franchise operators do not upload their purchases into Wansoft
correctly (or consistently), so Wansoft-side inventory data for Metepec
structurally does not reflect physical reality. This is an upstream data-entry
gap, not a calculation error -- no new TipoEntrada/TipoSalida exclusion rule
would fix it. Treat Metepec as a known low-confidence subsidiary in any
Wansoft-inventory output going forward.

**Negative-outlier subsidiaries investigated (project owner, 2026-08-26)** --
item-specific causes, not one universal pattern:

- Paper napkins (Vía Vallejo, `1000-200-003-005`): two factors. (1) Recorded
  per individual sheet, not per package of ~500 -- explains the huge raw
  magnitude, same as mints and mini alfajores. (2) `TipoSalida='Ajuste de
  inventario'` clustered on only 3 distinct days, 99,112 units -- a batch
  physical-count correction, not granular daily consumption. Removing just
  that adjustment flips this item from -64,800 to +29,112.
- Charcoal ("carbón", Isabel La Católica, `5400-100-002`): different cause.
  `Ajuste de inventario` is negligible (100 units) here. `TipoEntrada='Orden
  de compra a proveedor'` (55,470, excluded per the confirmed rule) is nearly
  as large as actual `Factura` entrada (62,316) -- suggests purchase orders
  may not consistently convert to `Factura` on arrival. Owner's framing:
  charcoal is a straight expense item ("gasto"), what's bought is essentially
  consumed 1:1, so a gap here is expected/acceptable.

**Decision: leave documented as a known limitation, no further investigation
or new exclusion rules for now.** Do not revisit the `Ajuste de inventario` or
`Orden de compra a proveedor` treatment without being asked again.

## Recommended Next Step

```text
Transfer double-counting question resolved (2026-08-25). Remaining before
build_/validate_ can be written:
1. Decide the balance calculation window (still open).
2. Decide whether to refresh the remaining 14 Wansoft-final subsidiaries'
   getinputinventory_entrada now, or proceed to implementation with
   Acoxpa as the proven pattern and refresh the rest in parallel/later.
3. Confirm getOutgoingInventory_Salida.CodigoProducto resolves against
   the product dictionary (still open, not yet checked).
```
