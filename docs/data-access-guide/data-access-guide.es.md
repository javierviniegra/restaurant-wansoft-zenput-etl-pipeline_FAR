# Guía de acceso a datos — bases analíticas de Fonda Argentina

*English version: [data-access-guide.en.md](data-access-guide.en.md)*

Para: equipos externos que construirán su propio ETL sobre estas bases (por
ejemplo, una capa de preguntas y respuestas / chatbot). Indica **qué tabla usar
para cada pregunta de negocio, qué campos importan, cómo se unen las tablas y
qué trampas evitar**. Cada regla se verificó contra el esquema y los datos
reales el 2026-09-28 y se actualizó el 2026-09-30. Versión en PDF: [data-access-guide.es.pdf](data-access-guide.es.pdf).

## Índice

1. [Qué hay y dónde](#1-qué-hay-y-dónde)
2. [Reglas de oro](#2-reglas-de-oro-léelas-antes-de-escribir-cualquier-consulta)
3. [Equivalencias de sucursales](#3-equivalencias-de-sucursales)
4. [Qué tabla responde cada pregunta](#4-qué-tabla-responde-cada-pregunta)
   - [4.1 Histórico disponible](#41-histórico-disponible)
5. [Dominios](#5-dominios)
   - [5.1 Ventas](#51-ventas-wansoft-todas-las-sucursales)
   - [5.2 Costos](#52-costos-wansoft-o-odoo-según-la-sucursal)
   - [5.3 Compras](#53-compras-histórico-de-wansoft--odoo-ya-unidos)
   - [5.4 Inventario](#54-inventario)
   - [5.5 Zenput](#55-zenput-base-zenput)
   - [5.6 Tablas de gobierno](#56-tablas-de-gobierno)
6. [No usar](#6-no-usar)
7. [Frescura y horarios](#7-frescura-y-horarios)
8. [Acceso](#8-acceso)

---

## 1. Qué hay y dónde

Dos bases MySQL (MariaDB 10.4) en el mismo servidor:

| Base | Contenido |
|---|---|
| `wansoft` | Ventas, costos, compras, inventario y la capa analítica unificada |
| `zenput` | Checklists operativos (formularios y respuestas) y tareas de Zenput |

Sistemas de origen:

| Origen | Qué aporta | Cómo llega |
|---|---|---|
| **Wansoft** (punto de venta / ERP) | Ventas y cierre de caja de todas las sucursales; costos, compras e inventario de las sucursales que aún no están en Odoo, y el histórico de las demás | Descarga diaria por su API SOAP |
| **Odoo** | Compras, inventario y costos de las sucursales que operan en Odoo, desde su fecha de arranque | Extracción diaria de solo lectura |
| **Zenput** | Checklists y tareas | Descarga diaria por API |

Capas dentro de `wansoft`:

| Capa | Tablas | Úsala para |
|---|---|---|
| Tablas operativas | `get*`, `costeomensual*` | Ventas, cierre de caja y detalle del lado Wansoft (copias de Wansoft); costos de todas las sucursales, calculados con Wansoft u Odoo según la sucursal (sección 5.2) |
| Canónica | `canonical_purchase_*` | Interna: compras de Odoo y Wansoft en un mismo formato. Mejor usar la capa analítica |
| **Analítica (lista para negocio)** | `analytics_*` | Compras e inventario de todas las sucursales, ambas fuentes ya unidas |
| Dimensiones | `dim_company_analytical`, `dim_product`, `dim_vendor`, `dim_time` | Descripciones y atributos para la capa analítica |

---

## 2. Reglas de oro (léelas antes de escribir cualquier consulta)

1. **Una sucursal se identifica de tres formas distintas** según la tabla. Usa
   la tabla de equivalencias de la Sección 3; nunca unas tablas por nombre de
   sucursal a ciegas.
   - Clave corta (`Acoxpa`, `Oceanía`): tablas de ventas (`Sucursal`) y capa
     analítica (`company_source_key`).
   - **ID numérico de Wansoft** (`5320`): costos (`subsidiary_id`) y tablas de
     inventario, donde el ID viene en una columna llamada, de forma engañosa,
     `subsidiary_name`.
   - Nombre largo de Wansoft (`Fonda Argentina - Acoxpa`): costos
     (`subsidiary_name`) y facturas (`getexpenses_factura.Sucursal`).
2. **En `getexpenses_factura.Sucursal` la misma sucursal aparece escrita de dos
   maneras** por un daño histórico de codificación (`Cancún` y `Canc??n`,
   `Oceanía` y `Ocean??a`). Asígnala con la tabla de equivalencias antes de agrupar.
3. **En las tablas de ventas los montos y fechas son texto** (`varchar`).
   Conviértelos: `CAST(Total AS DECIMAL(14,2))`, `DATE(Fecha)` (formato
   `2026-09-01T00:00:00`).
4. **Las tablas analíticas traen `include_in_business_views`.** Filtra
   `include_in_business_views = 1` para cifras de negocio; el resto de las filas
   se conserva para auditoría (proveedores internos, productos sin mapear, casos
   en revisión) y trae un `exclude_reason`.
5. **Compras e inventario vienen de dos sistemas; la capa analítica ya los une
   sin traslape** (Sección 5.3). No reconstruyas la unión desde las tablas crudas.
6. **Los datos se cargan una vez al día, alrededor de la 01:30, hasta el día
   anterior.** Cada corrida vuelve a revisar los días recientes (ventas 10 días,
   costos y tablajería 10, facturas/inventario/cierre de caja de Wansoft 5,
   compras 35), así que los últimos días todavía
   pueden cambiar.
7. Las tablas de costos son **fotos acumuladas**, no montos diarios (Sección 5.2).

---

## 3. Equivalencias de sucursales

| ID Wansoft | Clave corta (`Sucursal`, `company_source_key`) | Nombre largo Wansoft (costos) | Empresa en Odoo | Fuente de compras e inventario | Arranque en Odoo |
|---|---|---|---|---|---|
| 5320 | Acoxpa | Fonda Argentina - Acoxpa | FONDA COSTA NERA | Wansoft → **Odoo desde 2026-10-01** | 2026-10-01 |
| 4959 | Aeropuerto | Fonda Argentina - Aeropuerto | FONDA ARGENTINA AEROPUERTO | Wansoft | — |
| 4960 | Antenas | Fonda Argentina - Antenas | FONDA ARGENTINA LAS ANTENAS | Wansoft → **Odoo desde 2026-10-01** | 2026-10-01 |
| 6175 | Cancun | Fonda Argentina - Cancún | — | Wansoft | — |
| 12802 | CentroMyJ | Fonda Argentina - Centro Mario y July | MARIO Y JULY | Odoo (nació en Odoo) | 2026-06-01 |
| 4958 | Isabel La Católica | Fonda Argentina - Isabel La Católica | FONDA ARGENTINA | Wansoft → **Odoo desde 2026-10-01** | 2026-10-01 |
| 12057 | La Esquina Coyoacán | Fonda Argentina - Coyoacan | FONDA ARGENTINA COYOACAN | Wansoft → **Odoo desde 2026-10-01** | 2026-10-01 |
| 4752 | Metepec | Fonda Argentina - Tollocan | FONDA ARGENTINA TOLLOCAN | Wansoft | — |
| 4433 | Napoles | Fonda Argentina - Nápoles | FONDA ARGENTINA POLYFORUM | Wansoft | — |
| 5943 | Oceanía | Fonda Argentina - Oceanía | FONDA ARGENTINA ENCUENTRO OCEANIA | Wansoft → **Odoo desde 2026-10-01** | 2026-10-01 |
| 6174 | Playa del Carmen | Fonda Argentina - Playa del Carmen | — | Wansoft | — |
| 12806 | Puebla | Fonda Argentina - Puebla | FONDA ARGENTINA PUEBLA | Odoo (nació en Odoo) | 2026-06-10 |
| 5319 | San Jeronimo | Fonda Argentina – San Jerónimo | FONDA ARGENTINA SAN JERONIMO | Wansoft → **Odoo desde 2026-10-01** | 2026-10-01 |
| 5321 | Taquería parroquia | Fonda Argentina – Taquería Parroquía | — | Wansoft | — |
| 4962 | Taquería Viaducto | Fonda Argentina - Taqueria Viaducto | — | Wansoft | — |
| 6560 | Tepeyac | Fonda Argentina - Tepeyac | FONDA ARGENTINA MAQ | Wansoft → **Odoo desde 2026-10-01** | 2026-10-01 |
| 5396 | Versalles | Fonda Argentina - Taquería Exhibimex | — | Wansoft | — |
| 5318 | Vía Vallejo | Fonda Argentina – Vía Vallejo | FONDA ARGENTINA VALLEJO | Wansoft → **Odoo desde 2026-10-01** | 2026-10-01 |
| 4961 | Viaducto | Fonda Argentina - Viaducto | FONDA ARGENTINA VIADUCTO | Wansoft | — |

Notas:
- La misma sucursal tiene nombres distintos según el sistema: Metepec =
  "Tollocan", Napoles = "Polyforum", Versalles = "Taquería Exhibimex", Acoxpa =
  "Costa Nera" en Odoo. Los nombres largos usan guion (`-`) o guion largo (`–`).
- `7697` "Taqueria San Fernando" solo aparece en costos históricos; no es una de
  las 19 sucursales actuales.
- **Las ventas siempre vienen de Wansoft, para todas las sucursales**, sin
  importar la fuente de compras.
- **Sucursales nuevas** (hoy Puebla y CentroMyJ, y todas las que abran
  después) nacen en Odoo: compras, inventario y costos vienen de Odoo; en
  Wansoft solo registran ventas y cierres diarios.
- **Costos:** toda sucursal que opera en Odoo, migrada o nueva, toma su costo
  de Odoo **a partir de su fecha de arranque**, y de Wansoft antes de esa
  fecha. **Excepción temporal: Antenas** sigue con costo de Wansoft mientras se
  repara su base de datos en Odoo (fue el prototipo). **Isabel La Católica, San
  Jeronimo y Vía Vallejo** siguen con costo de Wansoft hasta que Odoo tenga su
  costo de venta (esperan sus saldos iniciales de inventario); cada una cambia
  sola a Odoo el primer día en que Odoo ya tiene datos. Ver sección 5.2.
- Los proveedores internos **El Bodegón de Fito** y **Las Empanadas de María
  Eva** (cocinas centrales) se excluyen como empresa compradora en las vistas
  de negocio.
- La misma información, como datos: `dim_company_analytical` y
  `analytics_company_domain_coverage` (Sección 5.6). Usan la clave corta y no
  traen el ID de Wansoft; para ese vínculo usa esta tabla.

---

## 4. Qué tabla responde cada pregunta

| Pregunta | Tabla | Filtro / nota |
|---|---|---|
| Venta, tickets, comensales por día y sucursal | `getallordenesbyday_new_venta` | una fila por ticket |
| Qué se vendió (platillos, grupos) | `getallordenesbyday_new_detalleventa` | una fila por renglón |
| Formas de pago, propinas | `getallordenesbyday_new_pago` | una fila por pago |
| Cierre oficial del día (corte Z), cancelaciones, cortesías, descuentos | `getglobalcashclosing` | una fila por sucursal por corte |
| Costo de venta, merma y margen del mes | `costeomensual` | foto acumulada del mes; toma el último día |
| Costo de la semana | `costeomensual_semanapyq` | foto acumulada de la semana |
| Costo de venta del día | `gettotalcostbydate` | una fila por sucursal por día |
| Rendimientos de tablajería | `gettablajeriareport` | solo histórico de sucursales Wansoft; va de salida (ver 5.2) |
| Compras (mercancía) de cualquier sucursal y periodo | `analytics_purchase_order_lines` / `analytics_purchase_orders` / `analytics_purchase_daily_company_product` | `include_in_business_views = 1` |
| Gasto por cuenta contable (Costo operativo, Gastos directos...) | `getexpenses_factura` | solo Wansoft (ver 5.3) |
| Detalle de entradas y salidas de inventario (Wansoft) | `getinputinventory_entrada`, `getoutgoinginventory_salida` | sucursales Wansoft |
| Existencias actuales | `analytics_inventory_current_product_location`, `analytics_inventory_balance` | `include_in_business_views = 1` |
| Resultados de checklists | `zenput.submissions` + `zenput.submission_answers` | |
| Tareas | `zenput.zenput_tasks` | |
| Qué fuente alimenta cada sucursal | `analytics_company_domain_coverage` | |
| Desde qué día el costo de cada sucursal sale de Odoo | `costs_source_by_company` | `odoo_cost_start_date` NULL = Wansoft |

### 4.1 Histórico disponible

Fechas medidas en producción el 2026-09-28. Las tablas se siguen llenando a diario hasta el día anterior.

| Dato | Tabla | Fuente | Desde | Notas |
|---|---|---|---|---|
| Ventas: tickets, detalle, modificadores | `getallordenesbyday_new_venta`, `_new_detalleventa`, `_new_modificador` | Wansoft | 2021-09-01 | Del 14 al 31 de diciembre de 2021 casi no hay tickets (hueco del histórico de origen, aceptado) |
| Ventas: pagos por ticket | `getallordenesbyday_new_pago` | Wansoft | 2025-01-01 | Antes de 2025 no hay pagos por ticket; usa el cierre de caja |
| Cierre de caja diario | `getglobalcashclosing` | Wansoft | 2022-01-01 |  |
| Costo de venta diario | `gettotalcostbydate` | Wansoft u Odoo (5.2) | 2021-07-31 |  |
| Costo mensual acumulado | `costeomensual` | Wansoft u Odoo (5.2) | 2022-01-01 | Puebla y CentroMyJ con costo desde julio de 2026 (5.2) |
| Costo semanal acumulado | `costeomensual_semanapyq` | Wansoft u Odoo (5.2) | 2024-01-02 |  |
| Tablajería | `gettablajeriareport` | Wansoft | 2022-01-01 | Va de salida (sección 5.2) |
| Facturas de proveedor por cuenta contable | `getexpenses_factura` | Wansoft | 2019-02-18 | El histórico más antiguo; solo mientras la sucursal captura en Wansoft |
| Entradas de inventario | `getinputinventory_entrada` | Wansoft | 2021-09-01 |  |
| Salidas de inventario | `getoutgoinginventory_salida` | Wansoft | 2020-11-30 | Unas 1.15 millones de filas traen fecha vacía (`0000-00-00`); exclúyelas |
| **Compras unificadas** | `analytics_purchase_order_lines`, `analytics_purchase_orders`, `analytics_purchase_daily_company_product` | **Wansoft + Odoo** | **2021-09-01** | Wansoft hasta el arranque de cada sucursal en Odoo y Odoo desde entonces (1 de octubre de 2026 para las migradas; Puebla y CentroMyJ desde su apertura en junio). Verificado año por año: mismos renglones y pesos que las facturas de Wansoft en producción |
| **Existencias unificadas** | `analytics_inventory_current_product_location`, `analytics_inventory_balance` | **Wansoft + Odoo** | Foto actual | Sin histórico por diseño; el saldo de Wansoft se recalcula cada noche con todos los movimientos desde 2020-11-30 |
| Checklists | `zenput.submissions`, `zenput.submission_answers` | Zenput | 2025-06-11 |  |
| Tareas | `zenput.zenput_tasks` | Zenput | 2025-06-03 |  |
| Calendario | `dim_time` | — | 2020-01-01 | Hasta 2035-12-31 |

---

## 5. Dominios

### 5.1 Ventas (Wansoft, todas las sucursales)

`getallordenesbyday_new_venta` — encabezado del ticket.

| Campo | Significado |
|---|---|
| `Sucursal` | Clave corta de la sucursal |
| `Movimento` | ID del ticket dentro de la sucursal (así, sin "i"); llave de unión |
| `Fecha` | Fecha de negocio, texto `AAAA-MM-DDT00:00:00` |
| `Total`, `Subtotal`, `IVA`, `IEPS`, `Descuento` | Montos, texto |
| `Personas` | Comensales |
| `Mesa`, `Mesero`, `Orden`, `Terminal` | Mesa, mesero, número de orden, terminal |
| `TipoOrden` | `Restaurant`, `Para llevar`, `eCommerce` |
| `HoraApertura`, `HoraCierre` | Hora de apertura y cierre |
| `Estatus` | Siempre `0` en los datos actuales |

Uniones (se necesitan las dos columnas, el ID de ticket se repite entre
sucursales):
`venta.Sucursal = detalle.Sucursal AND venta.Movimento = detalle.Movimiento_Id`;
igual para `getallordenesbyday_new_pago` y `getallordenesbyday_new_modificador`.

`getallordenesbyday_new_detalleventa` — renglones: `Platillo`, `CodigoPlatillo`,
`Grupo`, `TipoGrupo` (por ejemplo alimentos / bebidas), `Cantidad`,
`PrecioUnitario`, `Total`, `Costo`, `Cortesia`, `Hora`.

`getallordenesbyday_new_pago` — `MetodoDePago`, `Total`, `Propina`, `Terminal`.

Meseros: los pedidos de reparto y aplicaciones se atribuyen a un **mesero
genérico** cuyo nombre cambia por sucursal (`APLICACIONES`, `Apps Llevar`).
Exclúyelo al hacer rankings de meseros reales.

```sql
SELECT Sucursal, DATE(Fecha) AS dia,
       COUNT(*) AS tickets,
       SUM(CAST(Personas AS UNSIGNED)) AS comensales,
       SUM(CAST(Total AS DECIMAL(14,2))) AS venta
FROM getallordenesbyday_new_venta
WHERE Fecha >= '2026-09-01' AND Fecha < '2026-10-01'
GROUP BY Sucursal, DATE(Fecha);
```

`getglobalcashclosing` — el cierre oficial por sucursal (`subsidiary_id`,
`fecha_corte`): `total_ventas`, `no_ordenes`, `total_personas`, promedios, y
número y monto de cortesías, cancelaciones, descuentos, anulaciones y
promociones. Aquí los montos son **valor de venta**. Úsalo para cuadrar los
totales del día.

### 5.2 Costos (Wansoft u Odoo, según la sucursal)

De dónde viene el costo de cada sucursal:

| Tipo de sucursal | Fuente del costo hoy |
|---|---|
| Solo Wansoft | Reporte de costos de Wansoft |
| Migrada a Odoo (Acoxpa, Tepeyac, Oceanía, La Esquina Coyoacán) | Wansoft hasta el 30 de septiembre de 2026; Odoo desde el 1 de octubre |
| **Ola de octubre (Isabel La Católica, San Jeronimo, Vía Vallejo)** | Wansoft hasta que Odoo tenga su costo de venta; desde ese día (distinto para cada una), Odoo. Hasta entonces, en las filas de octubre de Wansoft la merma y el consumo vienen en 0 porque ya no se capturan ahí |
| Nueva, nacida en Odoo (Puebla, CentroMyJ y las que abran después) | Odoo desde su apertura. Odoo no tiene costo de venta de CentroMyJ antes de julio de 2026 ni de Puebla antes del 27 de julio de 2026: esos días valen 0 |
| **Antenas (excepción temporal)** | Wansoft, mientras se repara su base de datos en Odoo |

El costo de Odoo se calcula desde su contabilidad (cuentas de costo directo) y
se guarda en las mismas tablas. Trae `CostoTotal`, `CostoDeProductosVendidos`
y `CostoDeMerma`; `CostoDeCortesías` y `CostoDeCancelaciones` vienen del cierre
de caja; el resto de las columnas queda vacío (no tiene equivalente en Odoo).
**En las filas de Odoo las columnas sin equivalente son NULL**: usa
`COALESCE(columna, 0)` al restar o sumar, o el resultado sale NULL (por ejemplo,
`CostoTotal - CostoDeConsumo` da NULL en Puebla). El cambio de fuente aplica
por día: los días anteriores al arranque conservan el costo de Wansoft. Si el
cambio cae a mitad de mes o de semana, los acumulados (`costeomensual`,
`costeomensual_semanapyq`) siguen completos: suman lo de Wansoft hasta el día
anterior al cambio más lo de Odoo desde ese día, sin contar ningún día dos
veces. En las filas de Odoo, `CostoTotal` ya no incluye consumo.

**Qué fuente usa cada sucursal, como dato:** la tabla `costs_source_by_company`
(se reescribe cada noche con la misma regla del pipeline) trae por sucursal
`company_source_key`, `wansoft_subsidiary_id`, `odoo_company_id`,
`odoo_cost_start_date` (primer día con costo de Odoo; NULL = todo de Wansoft)
y `reason` (`wansoft`, `policy`, `exception`, `auto_switch_pending`,
`switched`). Úsala en lugar de copiar las reglas de esta sección.

**Los costos de los días recientes todavía no están completos**, y cada fuente
lo indica de forma distinta:
- **Wansoft:** su costo crece mientras procesa el descuento de inventario de lo
  vendido. `CostoIdealDeProductosPendientesDeRebaja` (en `costeomensual` y
  `costeomensual_semanapyq`) es el costo que todavía no se descuenta; cuando
  vale 0, el periodo está completo. Todo septiembre de 2026 ya está en 0; a
  inicios de octubre había entre 1% y 24% pendiente según la sucursal, más en
  fin de semana.
- **Odoo:** su costo sale de las facturas de cliente de cada día (las ventas de
  Wansoft pasadas a Odoo), que se crean con retraso: en septiembre de 2026 al
  día siguiente estaba facturado entre 40% y 70% de la venta, a los 7 días entre
  70% y 100%, y todo al cierre de mes. Para saber si un día está completo,
  compara lo facturado en Odoo con la venta neta de Wansoft de ese día. El
  pipeline vuelve a leer de Odoo el mes en curso (y el anterior hasta el día
  10), así que al cierre de mes las tablas quedan completas.

Si necesitas un costo de días recientes, márcalo como estimado o espera a que
el periodo esté completo.

Identificados por `subsidiary_id` (ID de Wansoft). Las tres son **fotos**:

| Tabla | Una fila = | Cómo leerla |
|---|---|---|
| `costeomensual` | Acumulado del mes, del día 1 hasta `created_date` | Total del mes = la fila con el `created_date` más reciente de ese mes |
| `costeomensual_semanapyq` | Acumulado de la semana, del lunes hasta el día **anterior** a `created_date` | Total de la semana = la última fila de la semana |
| `gettotalcostbydate` | Costo de venta del día `created_date` | Se suma por días |

`mes_ano` es texto `MM-AAAA`. Única por (`subsidiary_id`, `created_date`).

Campos de `costeomensual` y cómo los usan los reportes del dueño:

| Cifra del reporte | Fórmula |
|---|---|
| Costo Total | `CostoTotal - COALESCE(CostoDeConsumo, 0)` |
| Costo Teórico | `CostoDeProductosVendidos` |
| Gasto de Venta | `CostoDeConsumo` |
| Costo de Mermas | `CostoDeMerma` |
| Cortesías / Cancelaciones | `CostoDeCortesías`, `CostoDeCancelaciones` (valor de venta, del cierre de caja) |

```sql
-- Costo del mes por sucursal: última foto del mes
SELECT c.subsidiary_id, c.subsidiary_name, c.created_date,
       c.CostoTotal - COALESCE(c.CostoDeConsumo, 0) AS costo_total,
       c.CostoDeProductosVendidos AS costo_teorico
FROM costeomensual c
JOIN (SELECT subsidiary_id, MAX(created_date) AS d
      FROM costeomensual
      WHERE created_date >= '2026-08-01' AND created_date < '2026-09-01'
      GROUP BY subsidiary_id) last ON last.subsidiary_id = c.subsidiary_id AND last.d = c.created_date;
```

**Tablajería (`gettablajeriareport`) va de salida.** Solo existe para sucursales que capturan compras e inventario en Wansoft: las nuevas (Puebla, CentroMyJ) no tienen datos, y las migradas dejarán de tenerlos cuando dejen de capturar compras en Wansoft. En Odoo la tablajería no se registra así: se aplica con rendimientos calculados y al final del mes se verifica que el inventario real cuadre con el calculado. Úsala solo como histórico de sucursales Wansoft.

### 5.3 Compras (histórico de Wansoft + Odoo, ya unidos)

**Usa la capa analítica.** Ya une ambas fuentes con esta regla por sucursal:

- Sucursal que compra en Wansoft: entradas de tipo factura de Wansoft
  (`getinputinventory_entrada` con `TipoEntrada = 'Factura'`).
- Sucursal migrada a Odoo: histórico de Wansoft **antes** de su fecha de
  arranque en Odoo (Sección 3) y, desde esa fecha, órdenes de compra
  confirmadas de Odoo (`state` purchase/done). Sin traslape ni huecos.
- Se excluyen los proveedores internos como empresa compradora; si una
  sucursal le *compra a* un proveedor interno, eso sí cuenta.

`source_system` (`wansoft`/`odoo`) dice de dónde viene cada fila;
`final_purchase_source_status` explica por qué se conservó (por ejemplo
`wansoft_history_before_odoo`).

**Compras sin clasificar (desde el 7 de octubre de 2026):** una compra real
cuenta en las vistas de negocio aunque su proveedor o su producto todavía no
estén clasificados en los catálogos. `catalog_status` dice en qué estado está:
`catalogado`, `producto_por_clasificar` (el producto existe pero falta
confirmar su clasificación), `producto_sin_catalogo`, `proveedor_sin_catalogo`
o `proveedor_y_producto_sin_catalogo`. Úsalo para mostrar esas compras aparte
en un desglose por categoría; los totales ya las incluyen. Solo quedan fuera
(`include_in_business_views = 0`) los productos excluidos a propósito y las
compras hechas por los proveedores internos. Los catálogos se reconstruyen
cada noche.

| Tabla | Grano | Campos clave |
|---|---|---|
| `analytics_purchase_order_lines` | renglón de compra | `company_source_key`, `order_date`, `vendor_name`, `product_name`, `wansoft_code`, `wansoft_department`, `product_qty`, `price_unit`, `price_subtotal` (sin IVA), `price_total` (con IVA), `source_system` |
| `analytics_purchase_orders` | orden de compra / factura | los mismos campos de encabezado más totales |
| `analytics_purchase_daily_company_product` | sucursal × día × producto | `business_price_subtotal_total`, `business_product_qty_total` (ya filtrados para negocio) |

Se unen a las dimensiones con `product_analytical_key` → `dim_product`,
`vendor_analytical_key` → `dim_vendor`, `company_analytical_key` →
`dim_company_analytical`, `order_date_key` → `dim_time.date_key`.

```sql
SELECT company_source_key, DATE_FORMAT(order_date, '%Y-%m') AS mes,
       source_system, SUM(price_subtotal) AS compras_sin_iva
FROM analytics_purchase_order_lines
WHERE include_in_business_views = 1
  AND order_date >= '2026-01-01'
GROUP BY company_source_key, mes, source_system;
```

Ejemplo: las sucursales migradas (Acoxpa, Antenas, Tepeyac, Oceanía, Coyoacán)
salen con `source_system = 'wansoft'` hasta septiembre de 2026 y con `'odoo'`
desde octubre, sin meses repetidos ni faltantes; Puebla y CentroMyJ, que
nacieron en Odoo, salen con `'odoo'` desde su apertura en junio de 2026.

**`getexpenses_factura` es otra cosa:** son todas las facturas de proveedor de
Wansoft clasificadas por cuenta contable (`Cuenta`: Costo operativo, Gastos de
venta, Gastos directos, Sueldos y salarios, Fletes...), incluidos servicios,
software y nómina, que no son mercancía. Las órdenes de compra de Odoo solo
cubren mercancía. Por eso:
- Para compras de mercancía de ambos sistemas, usa la capa analítica.
- Para comparar con los reportes de "Compras" de Wansoft, usa solo
  `Cuenta = 'Costo operativo'`.
- **Odoo y Wansoft no cuadran entre sí para la misma sucursal y mes.** Durante
  la captura en paralelo, las compras de Odoo salieron entre 7% y 19% por
  encima del `Costo operativo` de Wansoft (septiembre de 2026: Acoxpa +7.2%,
  Coyoacán +11.1%, Oceanía +18.5%). Es una diferencia entre los dos sistemas
  de origen, no un error de carga, y su causa sigue en revisión. La capa
  analítica no la duplica porque nunca mezcla ambos sistemas para la misma
  sucursal y día; no compares Odoo contra Wansoft esperando que coincidan.
- **Gastos que no son mercancía** (renta, servicios, software, nómina,
  fletes...) de las sucursales que ya operan en Odoo: hoy **no** se extraen de
  Odoo. En `getexpenses_factura` esas sucursales solo tienen sus facturas hasta
  su fecha de arranque en Odoo. De la contabilidad de Odoo solo se toma el costo
  de venta (sección 5.2).

Algunas facturas de Wansoft traen `Cuenta` vacía. En esta tabla montos y
fechas son texto. **`Estatus = 'Por pagar'` no significa que no se haya
pagado:** en Wansoft las facturas casi nunca se marcan como pagadas (el pago se
registra en otro lado), así que no uses ese campo para cuentas por pagar.

### 5.4 Inventario

- **Movimientos de Wansoft** (sucursales Wansoft e histórico de las migradas):
  `getinputinventory_entrada` (entradas; `TipoEntrada`: `Factura`,
  `Transferencia`, `Entrada con canal`, `Producto procesado`, `Ajuste de
  inventario`) y `getoutgoinginventory_salida` (salidas, unos 37 millones de
  filas: filtra siempre por `Fecha` y `subsidiary_name`). Sucursal = ID de
  Wansoft en `subsidiary_name`. Cantidad `Cantidad`, costo `CostoUnitario`.
- **Existencias actuales, unificadas:** `analytics_inventory_current_product_location`
  (existencias de Odoo por producto y ubicación) y `analytics_inventory_balance`
  (saldo de Wansoft = entradas − salidas por producto). Filtra
  `include_in_business_views = 1`.
- Todavía **no hay valuación de inventario** (en dinero) para las sucursales en
  Odoo, solo cantidades.

### 5.5 Zenput (base `zenput`)

| Tabla | Grano | Campos clave |
|---|---|---|
| `form_templates` | plantilla de checklist | `form_id`, `title`, `category_name` |
| `submissions` | un checklist contestado | `submission_id`, `form_template_id` → `form_templates.form_id`, `location_name`, `user_display_name`, `date_submitted` |
| `submission_answers` | una respuesta | `submission_id`, `title` (pregunta), `field_type`, `value_as_string` |
| `zenput_tasks` | tarea | `task_id`, `title`, `account_name` (ubicación), `status_name`, `assignee_display_name`, `date_due`, `is_closed`, `is_completed_late` |

`location_name` / `account_name` son los nombres de ubicación propios de Zenput,
no la clave corta; algunas ubicaciones de Zenput no tienen sucursal en el punto
de venta.

### 5.6 Tablas de gobierno

- `dim_company_analytical`: una fila por empresa, banderas (`is_active_branch`,
  `is_internal_provider`, `is_final_operating_branch`), fuente por dominio,
  `operational_start_date`.
- `analytics_company_domain_coverage`: qué fuente alimenta cada dominio por
  sucursal, con conteos y un `coverage_status`.
- `costs_source_by_company`: desde qué día el costo de cada sucursal sale de
  Odoo (`odoo_cost_start_date`, NULL = Wansoft) y por qué (`reason`); se
  reescribe cada noche (sección 5.2).
- `dim_time`: calendario (`date_key` = `AAAAMMDD`), semanas, meses, semanas ISO.

---

## 6. No usar

| Tablas | Por qué |
|---|---|
| `canonical_purchase_*`, `odoo_purchase_*`, `odoo_inventory_*` | Capas intermedias; las tablas analíticas son el resultado listo para negocio |
| `inventory_*`, `product_catalog_mapping`, `backup_product_catalog_mapping`, `product_replacement_candidates`, `stg_*` | Mesa de trabajo de mapeos y revisiones |
| `odoo_company_migration_policy`, `odoo_cutover_validation_log` | Control del pipeline |
| `getinventorybydepartment`, `getstockinventory_inventario`, `getinventorybyday_*` | Fotos antiguas que ya no se actualizan a diario |
| `vw_inventory_*` | Vistas de diagnóstico |
| `tmp_*` | Temporales |

---

## 7. Frescura y horarios

- Pipeline diario a la **01:30** (hora de Ciudad de México); datos hasta el día
  anterior.
- Revisiones continuas: ventas 10 días (cuadradas contra el cierre diario de
  Wansoft), costos y tablajería 10 días, facturas/inventario/cierre de caja de
  Wansoft 5 días, compras 35 días.
- Wansoft puede recalcular sus costos después; manda la foto más reciente.
- Respaldo semanal los jueves a las 18:00. Evita consultas pesadas entre la
  01:30 y las 03:00.

## 8. Acceso

El acceso es mediante un usuario de base de datos **de solo lectura**, limitado
a las tablas de las Secciones 4 y 5, que se entrega por separado (las
credenciales nunca se escriben en este documento). Consulta
`getoutgoinginventory_salida` y las tablas de detalle de ventas siempre con
filtro de fechas: tienen decenas de millones de filas. Cada usuario tiene un
máximo de 4 conexiones simultáneas y 30 minutos por consulta.
