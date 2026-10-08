# Inventory coverage by branch

What inventory data the warehouse holds for each of the 19 branches, from
which system, since when, and where the gaps are. Measured in production on
**2026-10-08**. Owner's standing goal: at the end of every day the warehouse
must hold sales, purchases, inventory and everything else for every branch;
every gap below is something to close, not an accepted limitation.

---

## 1. Which table answers which inventory question

| Question | Table | Notes |
|---|---|---|
| Stock **today**, every branch, both systems merged | `analytics_inventory_balance` | One row per branch × Wansoft product code, `source_system` = `wansoft` (9 branches) or `odoo` (10 branches). Rewritten every night: **no history by design** |
| Stock today in Odoo by location (warehouse, kitchen...) | `analytics_inventory_current_product_location` | Odoo branches only |
| Stock **on a past date**, Wansoft branches | `getinputinventory_entrada` − `getoutgoinginventory_salida` up to that date | Example in Section 2. Possible since each branch's first Wansoft movement (2021-2022) |
| Stock **on a past date**, Odoo branches | `odoo_inventory_quant_daily` | Raw Odoo stock per day, location and product, **from stock date 2026-10-08 on** (new nightly stage, Section 4). Nothing before |
| Movements (entries, exits, waste, consumption), Wansoft | `getinputinventory_entrada`, `getoutgoinginventory_salida` | Wansoft only |
| Purchase receipts, both systems | `canonical_purchase_receipt_snapshot`, `canonical_purchase_receipt_move_snapshot` | Entries by purchase only |
| Movements of Odoo branches (consumption, waste, transfers) | — | **Not in the warehouse** (Section 5, part b) |
| Inventory value in pesos, Odoo branches | — | **Not in the warehouse** (Section 5, part b) |

---

## 2. Stock on a past date for a Wansoft branch (verified example)

`analytics_inventory_balance` computes today's Wansoft stock as all entries
minus all exits since the first movement, with these rules:

- entries: `TipoEntrada NOT IN ('Orden de compra a proveedor', 'Transferencia')`;
- exits: `TipoSalida NOT IN ('Error de captura', 'Factura de egresos rechazada', 'Transferencia')`
  (Wansoft does not expose both legs of an intra-branch transfer reliably,
  so transfers are left out on both sides);
- branch = Wansoft id in `subsidiary_name`, product = `CodigoProducto`.

The same rules, cut at a date, give the stock on that date. **Exit date:**
`Fecha` is empty (`0000-00-00`) on about 1.1 million exits. In the example
below they are not sales (every sale has a date) but inventory adjustments,
lot adjustments and waste, and all 1,002 of them carry their business date in
`FechaReal` (`FechaSalida` is when they were captured, days later). Use
`COALESCE(NULLIF(Fecha, '0000-00-00'), FechaReal)`; do not drop them, or the
adjustments disappear and the history no longer matches today's balance.
No entry in the table lacks `FechaEntrada`.

```sql
-- Stock of Coca Cola Mini (1000-105-203-005) at Viaducto (4961) at the close of :d
SELECT
  (SELECT COALESCE(SUM(Cantidad), 0) FROM getinputinventory_entrada
    WHERE subsidiary_name = '4961' AND CodigoProducto = '1000-105-203-005'
      AND TipoEntrada NOT IN ('Orden de compra a proveedor', 'Transferencia')
      AND DATE(FechaEntrada) <= :d)
  -
  (SELECT COALESCE(SUM(Cantidad), 0) FROM getoutgoinginventory_salida
    WHERE subsidiary_name = '4961' AND CodigoProducto = '1000-105-203-005'
      AND TipoSalida NOT IN ('Error de captura', 'Factura de egresos rechazada', 'Transferencia')
      AND COALESCE(NULLIF(Fecha, '0000-00-00'), FechaReal) <= :d) AS stock;
```

| `:d` | Stock |
|---|---|
| 2026-08-31 | 3,096 |
| 2026-09-30 | 2,939 |
| 2026-10-07 | **3,170** = `analytics_inventory_balance.current_balance_qty` that night |

Filter by `subsidiary_name` (and a date) on `getoutgoinginventory_salida`:
it has tens of millions of rows. Known limitation, not investigated further:
several Wansoft branches have products with negative balances (items tracked
per unit and adjusted in batches, expense-type products).

---

## 3. Coverage per branch

Wansoft movements = rows loaded in the warehouse (`FechaEntrada`; exits by
`Fecha`). "Still captures in Wansoft" = checked live against Wansoft's API
for 2026-10-06 (entries | exits returned for that one day).

### Branches on Wansoft (9): complete

| Branch | Wansoft id | Entries in MySQL | Exits in MySQL | Stock today |
|---|---|---|---|---|
| Aeropuerto | 4959 | 2021-09-04 → yesterday | 2021-09-01 → yesterday | Wansoft |
| Taquería Parroquia | 5321 | 2021-10-19 → yesterday | 2021-10-15 → yesterday | Wansoft |
| Viaducto | 4961 | 2021-09-15 → yesterday | 2021-09-01 → yesterday | Wansoft |
| Taquería Viaducto | 4962 | 2021-09-04 → yesterday | 2021-09-01 → yesterday | Wansoft |
| Playa del Carmen | 6174 | 2022-08-05 → yesterday | 2022-08-01 → yesterday | Wansoft |
| Cancún | 6175 | 2022-08-06 → yesterday | 2022-08-03 → yesterday | Wansoft |
| Nápoles | 4433 | 2021-09-01 → yesterday | 2021-07-23 → yesterday | Wansoft |
| Metepec (Tollocan) | 4752 | 2021-09-01 → yesterday | 2020-11-30 → yesterday | Wansoft |
| Versalles | 5396 | 2021-10-29 → yesterday | 2021-10-19 → yesterday | Wansoft |

Stock on any date since the first movement can be rebuilt (Section 2). The
nightly window re-reads the last 5 days.

### Branches migrated from Wansoft to Odoo (8): gap since 2026-10-01

| Branch | Wansoft id | Odoo start | Wansoft movements in MySQL | Still captures in Wansoft (2026-10-06) | Odoo stock in MySQL |
|---|---|---|---|---|---|
| Acoxpa | 5320 | 2026-10-01 | 2021-10 → 2026-09-30 | **yes**: 62 entries / 983 exits | today + daily from 2026-10-08 |
| Antenas | 4960 | 2026-10-01 | 2021-09 → 2026-09-30 | **yes**: 78 / 758 | today + daily from 2026-10-08 |
| Tepeyac | 6560 | 2026-10-01 | 2022-11 → 2026-09-30 | **yes**: 52 / 603 | today + daily from 2026-10-08 |
| Oceanía | 5943 | 2026-10-01 | 2022-04 → 2026-09-30 | **yes**: 15 / 400 | today + daily from 2026-10-08 |
| La Esquina Coyoacán | 12057 | 2026-10-01 | 2026-01-28 → 2026-09-30 | **yes**: 11 / 264 | today + daily from 2026-10-08 |
| Isabel La Católica | 4958 | 2026-10-01 | 2021-09 → 2026-09-30 | **yes**: 97 / 1,245 | today + daily from 2026-10-08 |
| San Jerónimo | 5319 | 2026-10-01 | 2021-10 → 2026-09-30 | **yes**: 212 / 2,377 | today + daily from 2026-10-08 |
| Vía Vallejo | 5318 | 2026-10-01 | 2021-10 → 2026-09-30 | **yes**: 41 / 650 | today + daily from 2026-10-08 |

- **Their Wansoft movements stop on 2026-09-30 in the warehouse**, by the
  decision of 2026-09-28 (no Wansoft purchase/inventory downloads for
  migrated branches after the cutover). Wansoft itself keeps recording
  them: invoices, transfers and waste are still captured there in parallel,
  and every sale still deducts inventory through Wansoft's recipes.
- **Odoo stock history: none for 2026-10-01 to 2026-10-07.** The daily Odoo
  capture starts with stock date 2026-10-08; the first week can only be
  rebuilt from Odoo's stock moves (part b).
- The October wave (Isabel, San Jerónimo, Vía Vallejo) is waiting for its
  opening balances in Odoo, so its Odoo stock is not yet meaningful.

### Branches born on Odoo (2): gap since opening

| Branch | Wansoft id | Odoo start | Wansoft movements | Still captures in Wansoft | Odoo stock in MySQL |
|---|---|---|---|---|---|
| Puebla | 12806 | 2026-06-10 | none, ever | no | today + daily from 2026-10-08 |
| CentroMyJ | 12802 | 2026-06-01 | none, ever | no | today + daily from 2026-10-08 |

- **No stock history from opening to 2026-10-07** (about four months). Only
  Odoo's stock moves (part b) can rebuild it.
- No inventory value in pesos either; their real cost of goods needs the
  Odoo valuation (part b).

### Gap summary

| Gap | Branches | Period | How to close it |
|---|---|---|---|
| Odoo stock history | the 10 Odoo branches | Puebla/CentroMyJ: opening → 2026-10-07; the 8 migrated: 2026-10-01 → 2026-10-07 | Odoo stock moves, part b (the daily capture covers from 2026-10-08) |
| Odoo movements (consumption, waste, transfers) | the 10 Odoo branches | since each Odoo start | part b |
| Odoo inventory value in pesos | the 10 Odoo branches | since each Odoo start | part b (`stock.valuation.layer`) |
| Wansoft parallel capture not loaded | the 8 migrated | since 2026-10-01 | owner's decision: reload Wansoft inventory for them as a parallel (non-final) source |

---

## 4. Odoo stock, day by day (`odoo_inventory_quant_daily`, since 2026-10-08)

Nightly stage "Inventario Odoo - foto diaria" (`extract/inventory/odoo_quant_daily.py`),
right after "Inventory pipeline". It reads Odoo's `stock.quant` for every
company and keeps:

- one row per `stock_date`, `odoo_location_id`, `odoo_product_id` (lots summed);
- only `location_usage` `internal` (warehouses, kitchens) and `transit`
  (goods between warehouses): Odoo's virtual locations (customer, supplier,
  production, inventory adjustment) are not physical stock (on 2026-10-08,
  4,052 internal + 2,815 transit of 42,133 quants);
- the raw data, without mappings or scope rules: `company_source_key`
  (NULL for internal providers and for transit locations without a
  company), `location_name`, `product_code` (when Odoo shows one),
  `product_name`, `quantity`, `reserved_quantity`, `quant_count`, `captured_at`.

`stock_date` is the previous day for the nightly capture (before 06:00) and
the same day for a capture later in the day, which the next night replaces.
Each run rewrites its own `stock_date`. About 4,200 rows a night.

```sql
-- Odoo stock of Acoxpa by product on a given day (all internal locations)
SELECT odoo_product_id, product_name, SUM(quantity) AS stock
FROM odoo_inventory_quant_daily
WHERE company_source_key = 'Acoxpa' AND stock_date = '2026-10-08' AND location_usage = 'internal'
GROUP BY odoo_product_id, product_name;
```

To express it in Wansoft codes, join `odoo_product_id` to the approved rows of
`inventory_mapping_dictionary` (as `analytics_inventory_balance` does today).

---

## 5. Still missing (part b, to design with the owner)

Extract Odoo's done stock moves (`stock.move` / `stock.move.line`) and the
valuation layers (`stock.valuation.layer`) for every Odoo company since its
start date: entries, exits, consumption, waste and transfers with their dates
and value. With them, Odoo stock and value on any past date can be rebuilt
the same way as Wansoft's (Section 2), the first week of October and the
born-on-Odoo branches' history recovered, and a real cost of goods computed
for Puebla and CentroMyJ.
