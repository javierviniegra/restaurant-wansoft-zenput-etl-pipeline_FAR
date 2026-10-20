# Guía de acceso a datos — bases analíticas de Fonda Argentina

*English version: [data-access-guide.en.md](data-access-guide.en.md)*

Para: equipos externos que construirán su propio ETL sobre estas bases (por
ejemplo, una capa de preguntas y respuestas / chatbot). Indica **qué tabla usar
para cada pregunta de negocio, qué campos importan, cómo se unen las tablas y
qué trampas evitar**. Cada regla se verificó contra el esquema y los datos
reales el 2026-09-28; la guía está actualizada al **2026-10-20**. El 2026-10-07
se comprobó que existen en producción todas las tablas y columnas que nombra, y
el esquema completo de cada tabla (Apéndice A) se tomó de producción el
2026-10-13. Versión en PDF: [data-access-guide.es.pdf](data-access-guide.es.pdf).

**Versión 1.6 (2026-10-20).** Cada cambio de esta guía sube su número de versión y queda registrado en la sección 10.

> **Novedades de la versión 1.6** (respecto a la 1.4 del 2026-10-16, la última entregada; incluye la 1.5):
>
> - **Acceso restringido a la tabla de gastos:** cuando entre `analytics_expense_invoices`, tukanmx deberá restringirla a los usuarios que Fonda Argentina autorice y, de preferencia, segmentar la vista por tipo de gasto (secciones 8 y 9).
> - **Cómo entran las ventas a Odoo y por qué su costo puede ir atrasado:** la automatización de Odoo solo procesa un ticket cuando hay inventario de todos los insumos de su receta; mientras falte alguno, ese día no tiene costo en Odoo (5.2).
> - **Regla del cambio de costo a Odoo:** las sucursales de la ola de octubre pasan a costo de Odoo solo cuando Odoo tiene un mes completo facturado, y desde el día 1 del mes siguiente; un mes nunca mezcla los dos sistemas (secciones 3, 5.2 y 9).

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
9. [Lo que falta (en construcción)](#9-lo-que-falta-en-construcción)
10. [Historial de versiones](#10-historial-de-versiones)

[Apéndice A. Esquema de las tablas](#apéndice-a-esquema-de-las-tablas)

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
  Jeronimo y Vía Vallejo** siguen con costo de Wansoft hasta que Odoo tenga **un mes completo
  facturado**; entonces cambian solas a Odoo desde el día 1 del mes siguiente.
  Ver sección 5.2.
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
| Lo que las sucursales de Odoo siguen capturando en Wansoft (solo para comparar) | `wansoft_parallel_inputinventory_entrada`, `wansoft_parallel_outgoinginventory_salida` | desde el 2026-10-01; nunca en totales (ver 5.4) |
| Existencias actuales, las 19 sucursales | `analytics_inventory_balance` (y `analytics_inventory_current_product_location` para Odoo por ubicación) | `include_in_business_views = 1`; solo la foto de hoy |
| Existencias a una fecha pasada, sucursales Wansoft | `getinputinventory_entrada` − `getoutgoinginventory_salida` hasta esa fecha | ver 5.4 |
| Existencias a una fecha pasada, sucursales Odoo | `odoo_inventory_quant_daily` | desde el 2026-10-08 (ver 5.4) |
| Resultados de checklists | `zenput.submissions` + `zenput.submission_answers` | |
| Tareas | `zenput.zenput_tasks` | |
| Qué fuente alimenta cada sucursal | `analytics_company_domain_coverage` | |
| Desde qué día el costo de cada sucursal sale de Odoo | `costs_source_by_company` | `odoo_cost_start_date` NULL = Wansoft |
| Todos los movimientos de inventario (compras, ventas, mermas, consumos, producción, ajustes, traslados), Wansoft + Odoo, todo el histórico | `analytics_inventory_movements` | `include_in_business_views = 1`; filtra siempre por sucursal y fechas (5.4) |
| Código de Wansoft de un producto de Odoo | `analytics_odoo_product_code` | una fila por producto de Odoo (5.4) |

### 4.1 Histórico disponible

Fechas de inicio medidas en producción el 2026-09-28; la puesta en producción del 1 de octubre no las cambió (solo quitó copias duplicadas de filas). Las tablas se siguen llenando a diario hasta el día anterior.

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
| Salidas de inventario | `getoutgoinginventory_salida` | Wansoft | 2020-11-30 | Unas 1.1 millones de filas traen `Fecha` vacía (`0000-00-00`): son ajustes y mermas con su fecha de negocio en `FechaReal`. **No las excluyas**: usa `COALESCE(NULLIF(Fecha, '0000-00-00'), FechaReal)` (5.4) |
| **Compras unificadas** | `analytics_purchase_order_lines`, `analytics_purchase_orders`, `analytics_purchase_daily_company_product` | **Wansoft + Odoo** | **2021-09-01** | Wansoft hasta el arranque de cada sucursal en Odoo y Odoo desde entonces (1 de octubre de 2026 para las migradas; Puebla y CentroMyJ desde su apertura en junio). Verificado año por año: mismos renglones y pesos que las facturas de Wansoft en producción |
| **Existencias unificadas** | `analytics_inventory_current_product_location`, `analytics_inventory_balance` | **Wansoft + Odoo** | Foto actual | Sin histórico por diseño; el saldo de Wansoft se recalcula cada noche con todos los movimientos desde 2020-11-30 |
| Inventario paralelo de Wansoft (8 sucursales migradas) | `wansoft_parallel_inputinventory_entrada`, `wansoft_parallel_outgoinginventory_salida` | Wansoft | 2026-10-01 | Solo para comparar con Odoo; las filas anteriores al 2026-10-01 son de septiembre y se leen de las tablas principales (5.4) |
| Existencias de Odoo día por día | `odoo_inventory_quant_daily` | Odoo | 2026-10-08 | Una foto cruda por noche (producto × ubicación); no hay historia de Odoo antes de esa fecha |
| Checklists | `zenput.submissions`, `zenput.submission_answers` | Zenput | 2025-06-11 |  |
| Tareas | `zenput.zenput_tasks` | Zenput | 2025-06-03 |  |
| **Movimientos de inventario unificados** | `analytics_inventory_movements` | **Wansoft + Odoo** | 2020-09-29 | Wansoft hasta el arranque de cada sucursal en Odoo y Odoo desde entonces (Puebla desde el 2026-06-09); lo capturado en paralelo se conserva con `include_in_business_views = 0` |
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
| **Ola de octubre (Isabel La Católica, San Jeronimo, Vía Vallejo)** | Wansoft hasta que Odoo tenga un mes completo facturado (cada día con venta tiene costo en Odoo y el total del mes es razonable frente a Wansoft); desde el día 1 del mes siguiente, Odoo. Un mes nunca mezcla los dos sistemas. Mientras tanto, en las filas de Wansoft la merma y el consumo vienen en 0 porque ya no se capturan ahí |
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
`switched`, `no_policy`). Úsala en lugar de copiar las reglas de esta sección.

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
- **Cómo entran las ventas a Odoo:** la venta siempre se registra en Wansoft. Una
  automatización en Odoo la convierte en orden de venta y factura de cliente, de
  la que sale el costo de venta. **Solo procesa un ticket cuando hay inventario
  de todos los insumos de su receta**; si falta alguno, la venta queda pendiente
  hasta que haya existencias. Así el costo es el real y se obliga a las
  sucursales a registrar sus producciones, recibir sus compras y administrar su
  inventario. En consecuencia, los días con ventas pendientes todavía no tienen
  costo en Odoo: no es un error de carga.

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

**Cuándo aparece una compra** (importante al leer los días recientes):
- **Odoo:** una orden cuenta cuando se **confirma**; los borradores y las
  solicitudes de cotización nunca cuentan. Entra en la carga de la noche
  siguiente a su confirmación, **con su fecha de orden**: una orden fechada el
  día 5 y confirmada el día 7 aparece en la tabla el día 8, pero en el día 5.
  Por eso las compras de días recientes pueden seguir creciendo.
- **Wansoft:** una compra cuenta cuando se **captura la factura**, normalmente
  al llegar la mercancía.
- Para la misma mercancía los dos momentos pueden ser distintos. El caso
  principal es **El Bodegón de Fito** (cocina central), que factura tarde: Odoo
  cuenta sus órdenes al confirmarlas, Wansoft hasta que llega la factura.

**Compras sin clasificar (desde la carga de la noche del 7 al 8 de octubre de
2026):** una compra real
cuenta en las vistas de negocio aunque su proveedor o su producto todavía no
estén clasificados en los catálogos. `catalog_status` dice en qué estado está:
`catalogado`, `producto_por_clasificar` (el producto existe pero falta
confirmar su clasificación), `producto_sin_catalogo`, `proveedor_sin_catalogo`
o `proveedor_y_producto_sin_catalogo`. Úsalo para mostrar esas compras aparte
en un desglose por categoría; los totales ya las incluyen. Solo quedan fuera
(`include_in_business_views = 0`) los productos excluidos a propósito y las
compras hechas por los proveedores internos. Los catálogos se reconstruyen
cada noche. Desde el 8 de octubre, una compra de Wansoft que trae su código y
departamento de Wansoft es `catalogado` aunque su vínculo con el producto
equivalente de Odoo siga pendiente de aprobar: `producto_por_clasificar`
queda solo para productos que de verdad no tienen clasificación.

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
  de origen, no un error de carga, y se explica en su mayor parte por el
  momento en que cada uno cuenta la compra (ver "Cuándo aparece una compra"):
  revisada una semana de Acoxpa, la mayoría de las órdenes coincidían exacto
  con su factura y casi toda la diferencia eran órdenes de El Bodegón de Fito
  todavía sin facturar; el resto, diferencias pequeñas entre el monto de la
  orden y el de la factura. La capa analítica no la duplica porque nunca mezcla
  ambos sistemas para la misma sucursal y día; no compares Odoo contra Wansoft
  esperando que coincidan.
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

- **Existencias de hoy, las 19 sucursales:** `analytics_inventory_balance`,
  una fila por sucursal × código de producto Wansoft; `source_system` dice de
  dónde sale: `wansoft` (las 9 sucursales Wansoft: entradas − salidas desde el
  primer movimiento) u `odoo` (las 10 de Odoo: existencias de Odoo).
  `analytics_inventory_current_product_location` da lo de Odoo por ubicación
  (almacén, cocina). Filtra `include_in_business_views = 1`. **Es la foto de
  hoy: se reescribe cada noche y no guarda historia.**
- **Movimientos de Wansoft:** `getinputinventory_entrada` (entradas;
  `TipoEntrada`: `Factura`, `Transferencia`, `Entrada con canal`, `Producto
  procesado`, `Ajuste de inventario`) y `getoutgoinginventory_salida`
  (salidas, decenas de millones de filas: filtra siempre por fecha y
  `subsidiary_name`). Sucursal = ID de Wansoft en `subsidiary_name`;
  producto = `CodigoProducto`; cantidad `Cantidad`, costo `CostoUnitario`.
  Solo traen sucursales Wansoft; las 8 migradas a Odoo llegan hasta el
  2026-09-30.
- **Inventario paralelo de Wansoft (desde la noche del 12 al 13 de octubre
  de 2026):** las 8 sucursales migradas a Odoo (Acoxpa, Antenas, Tepeyac,
  Oceanía, La Esquina Coyoacán, Isabel La Católica, San Jerónimo, Vía
  Vallejo) siguen capturando entradas y salidas en Wansoft. Eso se carga en
  `wansoft_parallel_inputinventory_entrada` y
  `wansoft_parallel_outgoinginventory_salida`, con las mismas columnas que
  las tablas principales. **Es solo para comparar Wansoft contra Odoo: nunca
  lo sumes a las existencias ni a los totales**; para esas sucursales la
  fuente oficial desde el 2026-10-01 es Odoo. Usa solo fechas desde el
  2026-10-01: las filas anteriores son movimientos de septiembre que se
  leen de las tablas principales.
- **Existencias a una fecha pasada, sucursales Wansoft:** entradas − salidas
  hasta esa fecha, con las mismas reglas que el saldo de hoy (sin
  transferencias, sin órdenes de compra, sin errores de captura ni facturas
  rechazadas). Las salidas con `Fecha` vacía son ajustes y mermas con su
  fecha en `FechaReal`: no las excluyas.

```sql
-- Existencias de Coca Cola Mini (1000-105-203-005) en Viaducto (4961) al cierre del 2026-09-30
SELECT
  (SELECT COALESCE(SUM(Cantidad), 0) FROM getinputinventory_entrada
    WHERE subsidiary_name = '4961' AND CodigoProducto = '1000-105-203-005'
      AND TipoEntrada NOT IN ('Orden de compra a proveedor', 'Transferencia')
      AND DATE(FechaEntrada) <= '2026-09-30')
  -
  (SELECT COALESCE(SUM(Cantidad), 0) FROM getoutgoinginventory_salida
    WHERE subsidiary_name = '4961' AND CodigoProducto = '1000-105-203-005'
      AND TipoSalida NOT IN ('Error de captura', 'Factura de egresos rechazada', 'Transferencia')
      AND COALESCE(NULLIF(Fecha, '0000-00-00'), FechaReal) <= '2026-09-30') AS existencias;
-- 2,939. Con '2026-10-07' da 3,170, igual que analytics_inventory_balance esa noche.
```

- **Existencias de Odoo día por día:** `odoo_inventory_quant_daily`, desde la
  fecha de existencias 2026-10-08. Una fila por `stock_date`, ubicación y
  producto de Odoo (`odoo_product_id`, `product_name`, `location_name`,
  `location_usage` `internal` o `transit`, `quantity`, `company_source_key`),
  sin mapeos. Para verlo en códigos Wansoft, une `odoo_product_id` con
  `analytics_odoo_product_code` (abajo). **No hay historia de
  existencias de Odoo antes del 2026-10-08.**
- **Movimientos de inventario unificados (desde la versión 1.4):**
  `analytics_inventory_movements`, una fila por movimiento de un producto en
  una sucursal, de Wansoft y de Odoo, con todo el histórico (unos 40 millones
  de filas). Se usa para flujos: cuánto se compró, vendió, mermó o consumió
  de cada producto, por sucursal y día, sin importar el sistema.

| Campo | Significado |
|---|---|
| `movement_date` | Fecha de negocio del movimiento |
| `company_source_key` | Sucursal (clave corta) |
| `source_system` | `wansoft` u `odoo` |
| `direction` | `in` (entra a la sucursal) u `out` (sale) |
| `movement_type` | Tipo normalizado: `purchase_receipt`, `sale_consumption`, `sale_cancellation`, `waste`, `theft`, `consumption`, `production_in`, `production_out`, `transfer_in`, `transfer_out`, `adjustment`, `initial_inventory`, `other` |
| `source_movement_type` | El tipo original (`TipoEntrada`/`TipoSalida` de Wansoft; origen → destino de Odoo) |
| `product_code`, `product_code_status` | Código de producto común: el código de Wansoft (`wansoft`) o un código temporal `ODOO-<id>` (`temporal_odoo`) mientras el producto de Odoo no tenga equivalencia; cuando la tenga, el código cambia en toda su historia |
| `wansoft_code`, `odoo_product_id`, `product_name`, `unit_name` | Producto y unidad |
| `quantity` | Cantidad con signo (+ entra, − sale), en la unidad del producto |
| `unit_cost`, `total_cost` | Costo (Wansoft: costo unitario; Odoo: valuación); `total_cost` con signo |
| `counts_in_stock` | Si el movimiento cambia las existencias (los traslados internos de Wansoft y las órdenes de compra no) |
| `final_source_status`, `include_in_business_views` | Igual que en compras: para cifras de negocio filtra `include_in_business_views = 1`. Las sucursales migradas toman Wansoft antes de su arranque en Odoo y Odoo desde entonces; lo que se capturó en paralelo en el otro sistema queda con `include_in_business_views = 0` (`wansoft_parallel_after_odoo`, `odoo_parallel_before_start`) |

```sql
-- Merma y consumo por mes de una sucursal, ambos sistemas
SELECT DATE_FORMAT(movement_date, '%Y-%m') AS mes, movement_type,
       SUM(-quantity) AS cantidad, SUM(-total_cost) AS costo
FROM analytics_inventory_movements
WHERE company_source_key = 'Acoxpa' AND include_in_business_views = 1
  AND movement_type IN ('waste', 'consumption')
  AND movement_date >= '2026-01-01'
GROUP BY mes, movement_type;
```

  Cada noche se recargan los movimientos de Wansoft capturados en los
  últimos 10 días y todo el lado Odoo, así que los días recientes todavía
  pueden cambiar. Para existencias usa `analytics_inventory_balance` (hoy) y
  `odoo_inventory_quant_daily` (Odoo por día); las existencias diarias
  unificadas están en construcción (sección 9).
- **Código de Wansoft de un producto de Odoo:** `analytics_odoo_product_code`
  (`odoo_product_id`, `odoo_product_name`, `wansoft_code`,
  `wansoft_product_name`), una fila por producto de Odoo con equivalencia
  vigente y revisada; se reescribe cada noche y es la misma que usa
  `analytics_inventory_movements`. Úsala para leer `odoo_inventory_quant_daily`
  en códigos Wansoft. **No uses `dim_product` para esto**: incluye
  equivalencias que todavía están en revisión.
- Cobertura detallada por sucursal:
 `docs/inventory-coverage-by-branch.md`
  del repositorio.

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
| `canonical_purchase_*`, `odoo_purchase_*`, `odoo_stock_move_snapshot` y las `odoo_inventory_*` **salvo `odoo_inventory_quant_daily`** | Capas intermedias; las tablas analíticas son el resultado listo para negocio |
| `inventory_*`, `product_catalog_mapping`, `backup_product_catalog_mapping`, `product_replacement_candidates`, `stg_*` | Mesa de trabajo de mapeos y revisiones; para la equivalencia de productos usa `analytics_odoo_product_code` |
| `odoo_company_migration_policy`, `odoo_cutover_validation_log` | Control del pipeline |
| `getinventorybydepartment`, `getstockinventory_inventario`, `getinventorybyday_*` | Fotos antiguas que ya no se actualizan a diario |
| `vw_inventory_*` | Vistas de diagnóstico |
| `tmp_*` | Temporales |

---

## 7. Frescura y horarios

- Pipeline diario a la **01:30** (hora de Ciudad de México), unos 40 minutos;
  datos hasta el día anterior. En producción desde el 1 de octubre de 2026.
- Revisiones continuas: ventas 10 días (cuadradas contra todos los cortes de
  caja del día en Wansoft; el último día se valida la noche siguiente),
  costos y tablajería 10 días (el costo de Odoo: el mes en curso y el anterior
  hasta el día 10), facturas/inventario/cierre de caja de Wansoft 5 días,
  compras de Wansoft 35 días. Las compras de Odoo se recargan completas cada
  noche; una orden aparece la noche siguiente a su confirmación (sección 5.3).
- Wansoft puede recalcular sus costos después; manda la foto más reciente.
- Algunas sucursales (Antenas, Vía Vallejo, Coyoacán, Metepec, Taquería
  Parroquia, Versalles, Tepeyac) suben su corte de caja a Wansoft hasta la
  mañana siguiente, aunque lo hagan en la noche: su fila de
  `getglobalcashclosing` llega **un día tarde** (la venta sí está a tiempo
  en los tickets). Mientras no llegue, ese día no tiene cancelaciones,
  cortesías ni descuentos; toma la venta de los tickets.
- Respaldo semanal los jueves a las 18:00. Evita consultas pesadas entre la
  01:30 y las 03:00.

## 8. Acceso

El acceso es mediante un usuario de base de datos **de solo lectura**, limitado
a las tablas de las Secciones 4 y 5, que se entrega por separado (las
credenciales nunca se escriben en este documento). Consulta
`getoutgoinginventory_salida` y las tablas de detalle de ventas siempre con
filtro de fechas: tienen decenas de millones de filas. Cada usuario tiene un
máximo de 4 conexiones simultáneas y 30 minutos por consulta.

Las tablas que el usuario puede leer son exactamente las del Apéndice A, con
todas sus columnas. Cuando se agrega una tabla nueva (sección 9), se concede al
usuario y se actualizan esta guía y el apéndice. Excepción: la tabla de gastos
deberá tener además acceso restringido en la plataforma de tukanmx (sección 9).

---

## 9. Lo que falta (en construcción)

Estado al 2026-10-20. Los movimientos de inventario unificados ya están en
producción (5.4). Las tablas de abajo todavía no existen; cuando entren, se
concederán al usuario y se documentarán aquí.

| Qué | Tabla | Estado | Qué resuelve |
|---|---|---|---|
| Existencias diarias unificadas | `analytics_inventory_stock_daily` | Diseñada | Existencias por sucursal × producto × día desde el primer movimiento, ambas fuentes; reemplaza la fórmula de entradas − salidas de la sección 5.4 y cubre los huecos de Odoo antes del 2026-10-08 |
| Facturas de proveedor unificadas | `analytics_expense_invoices` | Diseñada | Facturas por cuenta contable de Wansoft + facturas de proveedor de Odoo; hoy los gastos que no son mercancía de las sucursales de Odoo no se extraen (5.3) |

Otros cambios próximos:
- **Aeropuerto y Taquería Viaducto pasan a Odoo el 2026-11-01** (como
  sucursales de la empresa FONDA ARGENTINA AEROPUERTO). Desde ese día sus
  compras, inventario y costos saldrán de Odoo, con la misma regla de la
  sección 3; las ventas siguen en Wansoft.
- **Isabel La Católica, San Jerónimo y Vía Vallejo** siguen con costo de
  Wansoft hasta que Odoo tenga un mes completo facturado; `costs_source_by_company`
  muestra el día del cambio (5.2).
- **Antenas** sigue con costo de Wansoft mientras se repara su base en Odoo.
- **Requisito para tukanmx: acceso restringido a la tabla de gastos.** La tabla de facturas de proveedor (`analytics_expense_invoices`) tendrá información sensible: rentas, honorarios, sueldos y gastos administrativos, con el proveedor de cada uno. En su plataforma, tukanmx debe restringirla para todos los usuarios: solo la podrán consultar los usuarios que Fonda Argentina autorice. De preferencia, la vista debe segmentarse por tipo de gasto (cada factura traerá su tipo de egreso, cuenta y subcuenta), para que, por ejemplo, un usuario de operación vea el costo de mercancía y los gastos de venta, pero no las rentas, los honorarios ni los sueldos. Pedimos a tukanmx que nos confirme cómo lo hará antes de que se le conceda la tabla.
- **Seguridad del acceso:** el acceso del usuario quedará limitado a una IP fija y la conexión será cifrada (TLS); avisaremos la fecha y lo necesario para conectarse.

---

## 10. Historial de versiones

La versión más reciente va primero.

**Versión 1.6 (2026-10-20)**

- **Acceso restringido a la tabla de gastos:** cuando entre `analytics_expense_invoices`, tukanmx deberá restringirla a los usuarios que Fonda Argentina autorice y, de preferencia, segmentar la vista por tipo de gasto (secciones 8 y 9).

**Versión 1.5 (2026-10-19)**

- **Cómo entran las ventas a Odoo y por qué su costo puede ir atrasado:** la automatización de Odoo solo procesa un ticket cuando hay inventario de todos los insumos de su receta; mientras falte alguno, ese día no tiene costo en Odoo (5.2).
- **Regla del cambio de costo a Odoo:** las sucursales de la ola de octubre pasan a costo de Odoo solo cuando Odoo tiene un mes completo facturado, y desde el día 1 del mes siguiente; un mes nunca mezcla los dos sistemas (secciones 3, 5.2 y 9).

**Versión 1.4 (2026-10-16)**

- **Movimientos de inventario unificados:** nueva tabla `analytics_inventory_movements`, una fila por movimiento (compra, venta, merma, consumo, producción, ajuste, traslado) de Wansoft y de Odoo, con todo el histórico, tipo normalizado, costo y un código de producto común (5.4).
- **Código de Wansoft de un producto de Odoo:** nueva tabla `analytics_odoo_product_code`, actualizada cada noche (5.4). Corrige la versión 1.3, que remitía a `inventory_mapping_dictionary`, una tabla no concedida.
- **Sección 6 corregida:** `odoo_inventory_quant_daily` sí se usa; la lista de tablas que no se deben usar ya no la incluye.
- **Acceso:** quedan concedidas las 4 tablas que faltaban (`costs_source_by_company`, `odoo_inventory_quant_daily` y las dos `wansoft_parallel_*`) y las 2 nuevas; 28 tablas de `wansoft` en total, todas en el Apéndice A.
- **Sección 9 actualizada:** los movimientos unificados ya están en producción; próximos pasos: acceso limitado a una IP fija y conexión cifrada (TLS).

**Versión 1.3 (2026-10-13)**

- **Existencias de Odoo día por día:** nueva tabla `odoo_inventory_quant_daily`, desde el 2026-10-08 (secciones 4 y 5.4).
- **Existencias de Wansoft a una fecha pasada:** regla y ejemplo verificado; las salidas sin `Fecha` se fechan con `FechaReal` (5.4).
- **Inventario paralelo de Wansoft** de las 8 sucursales migradas a Odoo: nuevas tablas `wansoft_parallel_inputinventory_entrada` y `wansoft_parallel_outgoinginventory_salida`, solo para comparar (5.4).
- **Cortes de caja que llegan un día tarde** en 7 sucursales (sección 7).
- **Nueva sección 9:** lo que está en construcción (movimientos de inventario unificados, existencias diarias, facturas de proveedor) y el paso a Odoo de Aeropuerto y Taquería Viaducto el 2026-11-01.
- **Nuevo Apéndice A:** todas las columnas (tipo, nulos, llaves) de las 30 tablas que puede leer el usuario.
- **Acceso:** 3 tablas más concedidas (`odoo_inventory_quant_daily` y las dos `wansoft_parallel_*`); 26 tablas de `wansoft` en total.

**Versión 1.2 (2026-10-07)**

- Costos: la fuente del costo de cada sucursal como dato (nueva tabla `costs_source_by_company`), el cambio automático de Wansoft a Odoo por sucursal y cómo saber si los costos recientes ya están completos (5.2).
- Compras: las compras sin clasificar cuentan en las vistas de negocio, con la nueva columna `catalog_status`; cuándo aparece una compra (Odoo al confirmarse, Wansoft al llegar la factura) (5.3).
- Frescura y horarios con los datos de la primera semana en producción (sección 7).

**Versión 1.1 (2026-10-01)**

- Puesta en producción del 2026-10-01: las sucursales migradas toman compras e inventario de Odoo desde esa fecha (sección 3).
- Costos: cada sucursal en Odoo toma su costo de Odoo desde su fecha de arranque; histórico de costos de Puebla y CentroMyJ (5.2).
- Advertencia: las compras de Odoo y las de Wansoft no cuadran entre sí para la misma sucursal y mes (5.3).

**Versión 1.0 (2026-09-28)**

- Primera edición, en español e inglés con PDF: tablas por pregunta, reglas de oro, equivalencias de sucursales, histórico disponible, dominios, tablas que no se deben usar, frescura y acceso.

<!-- schema-appendix:start -->

## Apéndice A. Esquema de las tablas

Columnas de cada tabla que el usuario de solo lectura puede consultar, tomadas del esquema de producción el 2026-10-16. **Nulo**: si la columna admite NULL. **Llave**: `PRI` llave primaria, `UNI` parte de una llave única, `MUL` parte de un índice. El significado de los campos importantes está en la sección indicada entre paréntesis.

### A.1 Ventas

**`getallordenesbyday_new_venta`**: encabezado del ticket (5.1). 24 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `id` | int(11) | no | PRI |
| `Sucursal` | varchar(255) | sí |  |
| `Venta_Id` | varchar(255) | sí |  |
| `Movimento` | varchar(255) | sí | MUL |
| `Orden` | varchar(255) | sí |  |
| `Mesa` | varchar(255) | sí |  |
| `Fecha` | varchar(255) | sí |  |
| `Mesero` | varchar(255) | sí |  |
| `Subtotal` | varchar(255) | sí |  |
| `IVA` | varchar(255) | sí |  |
| `IEPS` | varchar(255) | sí |  |
| `Total` | varchar(255) | sí |  |
| `Terminal` | varchar(255) | sí |  |
| `Personas` | varchar(255) | sí |  |
| `Descuento` | varchar(255) | sí |  |
| `Impuesto` | varchar(255) | sí |  |
| `MontoDescontado` | varchar(255) | sí |  |
| `TipoOrden` | varchar(255) | sí |  |
| `HoraApertura` | varchar(255) | sí |  |
| `HoraCierre` | varchar(255) | sí |  |
| `Moneda` | varchar(255) | sí |  |
| `CodigoCliente` | varchar(255) | sí |  |
| `Estatus` | varchar(255) | sí |  |
| `Ventas_Id` | varchar(255) | sí |  |

**`getallordenesbyday_new_detalleventa`**: renglones del ticket (5.1). 30 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `id` | int(11) | no | PRI |
| `Sucursal` | varchar(255) | sí |  |
| `Movimiento_Id` | varchar(255) | sí | MUL |
| `DetalleVenta_Id` | varchar(255) | sí |  |
| `Descripcion` | varchar(255) | sí |  |
| `Cantidad` | varchar(255) | sí |  |
| `PrecioUnitario` | varchar(255) | sí |  |
| `Descuento` | varchar(255) | sí |  |
| `Subtotal` | varchar(255) | sí |  |
| `IVA` | varchar(255) | sí |  |
| `IEPS` | varchar(255) | sí |  |
| `Total` | varchar(255) | sí |  |
| `Modificador` | varchar(255) | sí |  |
| `Hora` | varchar(255) | sí |  |
| `Costo` | varchar(255) | sí |  |
| `TipoGrupo` | varchar(255) | sí |  |
| `CodigoTipoGrupo` | varchar(255) | sí |  |
| `CuentaContableTipoGrupo` | varchar(255) | sí |  |
| `Grupo` | varchar(255) | sí |  |
| `CodigoGrupo` | varchar(255) | sí |  |
| `CuentaContableGrupo` | varchar(255) | sí |  |
| `CodigoPlatillo` | varchar(255) | sí |  |
| `CuentaContablePlatillo` | varchar(255) | sí |  |
| `Platillo` | varchar(255) | sí |  |
| `ConIVA` | varchar(255) | sí |  |
| `ComandaId` | varchar(255) | sí |  |
| `TipoPlatilloId` | varchar(255) | sí |  |
| `TipoPromocionId` | varchar(255) | sí |  |
| `Cortesia` | varchar(255) | sí |  |
| `DetallesVenta_Id` | varchar(255) | sí |  |

**`getallordenesbyday_new_pago`**: pagos del ticket (5.1). 17 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `id` | int(11) | no | PRI |
| `Sucursal` | varchar(255) | sí |  |
| `Movimiento_Id` | varchar(255) | sí |  |
| `Fecha` | varchar(255) | sí |  |
| `IdMetodoDePago` | varchar(255) | sí |  |
| `MetodoDePago` | varchar(255) | sí |  |
| `CodigoMetodoDePago` | varchar(255) | sí |  |
| `ClaveSATMetodoDePago` | varchar(255) | sí |  |
| `CuentaContableMetodoDePago` | varchar(255) | sí |  |
| `Terminal` | varchar(255) | sí |  |
| `Total` | varchar(255) | sí |  |
| `Propina` | varchar(255) | sí |  |
| `Equivalencia` | varchar(255) | sí |  |
| `Moneda` | varchar(255) | sí |  |
| `MontoRecibidoEnMoneda` | varchar(255) | sí |  |
| `PagoAnticipadoId` | varchar(255) | sí |  |
| `Pagos_Id` | varchar(255) | sí | MUL |

**`getallordenesbyday_new_modificador`**: modificadores de los renglones (5.1). 28 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `id` | int(11) | no | PRI |
| `Sucursal` | varchar(255) | sí |  |
| `Movimiento_Id` | varchar(255) | sí | MUL |
| `Descripcion` | varchar(255) | sí |  |
| `Cantidad` | varchar(255) | sí |  |
| `PrecioUnitario` | varchar(255) | sí |  |
| `Descuento` | varchar(255) | sí |  |
| `Subtotal` | varchar(255) | sí |  |
| `IVA` | varchar(255) | sí |  |
| `IEPS` | varchar(255) | sí |  |
| `Total` | varchar(255) | sí |  |
| `Modificador` | varchar(255) | sí |  |
| `Hora` | varchar(255) | sí |  |
| `Costo` | varchar(255) | sí |  |
| `TipoGrupo` | varchar(255) | sí |  |
| `CodigoTipoGrupo` | varchar(255) | sí |  |
| `CuentaContableTipoGrupo` | varchar(255) | sí |  |
| `Grupo` | varchar(255) | sí |  |
| `CodigoGrupo` | varchar(255) | sí |  |
| `CuentaContableGrupo` | varchar(255) | sí |  |
| `CodigoPlatillo` | varchar(255) | sí |  |
| `CuentaContablePlatillo` | varchar(255) | sí |  |
| `Platillo` | varchar(255) | sí |  |
| `ConIVA` | varchar(255) | sí |  |
| `ComandaId` | varchar(255) | sí |  |
| `TipoPlatilloId` | varchar(255) | sí |  |
| `TipoPromocionId` | varchar(255) | sí |  |
| `Modificadores_Id` | varchar(255) | sí |  |

**`getglobalcashclosing`**: cierre de caja (corte Z) por sucursal y día (5.1). 49 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `id` | int(11) | no | PRI |
| `subsidiary_id` | int(11) | sí | MUL |
| `subsidiary_name` | varchar(255) | sí |  |
| `fecha_corte` | datetime | sí |  |
| `usuario` | varchar(255) | sí |  |
| `subtotal` | decimal(10,2) | sí |  |
| `iva` | decimal(10,2) | sí |  |
| `ieps` | decimal(10,2) | sí |  |
| `total_ventas` | decimal(10,2) | sí |  |
| `efectivo_por_ventas` | decimal(10,2) | sí |  |
| `efectivo_por_propina` | decimal(10,2) | sí |  |
| `fondo_de_caja` | decimal(10,2) | sí |  |
| `efectivo_real` | decimal(10,2) | sí |  |
| `no_ordenes` | int(11) | sí |  |
| `no_platillos` | int(11) | sí |  |
| `total_personas` | int(11) | sí |  |
| `promedio_platillos_orden` | decimal(10,2) | sí |  |
| `promedio_por_orden` | decimal(10,2) | sí |  |
| `promedio_por_persona` | decimal(10,2) | sí |  |
| `total_ordenes_para_llevar` | int(11) | sí |  |
| `total_mesas_atendidas` | int(11) | sí |  |
| `total_ordenes_a_domicilio` | int(11) | sí |  |
| `total_ordenes_recoger` | int(11) | sí |  |
| `no_cortesias_en_cuentas` | int(11) | sí |  |
| `cortesias_en_cuentas` | decimal(10,2) | sí |  |
| `no_cortesias_en_platillos` | int(11) | sí |  |
| `cortesias_en_platillos` | decimal(10,2) | sí |  |
| `no_cancelaciones_en_cuentas` | int(11) | sí |  |
| `cancelaciones_en_cuentas` | decimal(10,2) | sí |  |
| `no_cancelaciones_en_platillos` | int(11) | sí |  |
| `cancelaciones_en_platillos` | decimal(10,2) | sí |  |
| `no_descuentos_en_cuentas` | int(11) | sí |  |
| `descuentos_en_cuentas` | decimal(10,2) | sí |  |
| `no_descuentos_en_platillos` | int(11) | sí |  |
| `descuentos_en_platillos` | decimal(10,2) | sí |  |
| `no_anulaciones_en_cuentas` | int(11) | sí |  |
| `anulaciones_en_cuentas` | decimal(10,2) | sí |  |
| `no_anulaciones_en_platillos` | int(11) | sí |  |
| `anulaciones_en_platillos` | decimal(10,2) | sí |  |
| `no_dxu_platillos` | int(11) | sí |  |
| `dxu_platillos` | decimal(10,2) | sí |  |
| `no_descuentos_megapuntos` | int(11) | sí |  |
| `descuentos_megapuntos` | decimal(10,2) | sí |  |
| `no_promociones` | int(11) | sí |  |
| `promociones` | decimal(10,2) | sí |  |
| `no_cupones` | int(11) | sí |  |
| `cupones` | decimal(10,2) | sí |  |
| `mes_ano` | varchar(7) | sí |  |
| `created_at` | timestamp | no |  |

### A.2 Costos

**`costeomensual`**: costo acumulado del mes, foto diaria (5.2). 17 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `id` | int(11) | no | PRI |
| `subsidiary_id` | int(11) | sí | MUL |
| `subsidiary_name` | varchar(255) | sí |  |
| `CostoTotal` | decimal(10,2) | sí |  |
| `CostoDeProductosVendidos` | decimal(10,2) | sí |  |
| `CostoIdealDeProductosPendientesDeRebaja` | decimal(10,2) | sí |  |
| `CostoDeCortesías` | decimal(10,2) | sí |  |
| `CostoDeCancelaciones` | decimal(10,2) | sí |  |
| `CostoDeMerma` | decimal(10,2) | sí |  |
| `CostoDeDesperdicio` | decimal(10,2) | sí |  |
| `CostoDeRobo` | decimal(10,2) | sí |  |
| `CostoDeConsumo` | decimal(10,2) | sí |  |
| `AjustePorSobrantes` | decimal(10,2) | sí |  |
| `UtilidadMarginal` | decimal(10,2) | sí |  |
| `mes_ano` | varchar(7) | sí |  |
| `created_at` | timestamp | no |  |
| `created_date` | date | sí |  |

**`costeomensual_semanapyq`**: costo acumulado de la semana (5.2). 17 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `id` | int(11) | no | PRI |
| `subsidiary_id` | int(11) | sí | MUL |
| `subsidiary_name` | varchar(255) | sí |  |
| `CostoTotal` | decimal(10,2) | sí |  |
| `CostoDeProductosVendidos` | decimal(10,2) | sí |  |
| `CostoIdealDeProductosPendientesDeRebaja` | decimal(10,2) | sí |  |
| `CostoDeCortesías` | decimal(10,2) | sí |  |
| `CostoDeCancelaciones` | decimal(10,2) | sí |  |
| `CostoDeMerma` | decimal(10,2) | sí |  |
| `CostoDeDesperdicio` | decimal(10,2) | sí |  |
| `CostoDeRobo` | decimal(10,2) | sí |  |
| `CostoDeConsumo` | decimal(10,2) | sí |  |
| `AjustePorSobrantes` | decimal(10,2) | sí |  |
| `UtilidadMarginal` | decimal(10,2) | sí |  |
| `mes_ano` | varchar(7) | sí |  |
| `created_at` | timestamp | no |  |
| `created_date` | date | sí |  |

**`gettotalcostbydate`**: costo de venta del día (5.2). 7 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `id` | int(11) | no | PRI |
| `subsidiary_id` | int(11) | sí | MUL |
| `subsidiary_name` | varchar(255) | sí |  |
| `CostoTotalVenta` | decimal(10,2) | sí |  |
| `mes_ano` | varchar(7) | sí |  |
| `created_at` | timestamp | no |  |
| `created_date` | date | sí |  |

**`gettablajeriareport`**: rendimientos de tablajería, solo histórico Wansoft (5.2). 17 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `id` | int(11) | no | PRI |
| `subsidiary_id` | int(11) | sí |  |
| `subsidiary_name` | varchar(255) | sí |  |
| `InputDate` | date | sí |  |
| `UserName` | varchar(255) | sí |  |
| `QuantityOfBaseProduct` | decimal(15,10) | sí |  |
| `ProductBase` | varchar(255) | sí |  |
| `ProductBaseCost` | decimal(15,4) | sí |  |
| `UnitOfMeasureOfBaseProduct` | varchar(50) | sí |  |
| `QuantityDecrease` | decimal(15,10) | sí |  |
| `Warehouse` | varchar(255) | sí |  |
| `QuantityOfGeneratedProduct` | decimal(15,10) | sí |  |
| `GeneratedProduct` | varchar(255) | sí |  |
| `UnitCostOfGeneratedProduct` | decimal(15,10) | sí |  |
| `totalCostOfGeneratedProduct` | decimal(15,10) | sí |  |
| `RegistrationDate` | date | sí |  |
| `created_at` | timestamp | no |  |

**`costs_source_by_company`**: fuente del costo por sucursal (5.2). 6 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `company_source_key` | varchar(100) | no | PRI |
| `wansoft_subsidiary_id` | int(11) | sí |  |
| `odoo_company_id` | int(11) | sí |  |
| `odoo_cost_start_date` | date | sí |  |
| `reason` | varchar(30) | no |  |
| `updated_at` | datetime | no |  |

### A.3 Compras y facturas

**`analytics_purchase_order_lines`**: renglones de compra, Wansoft + Odoo (5.3). 58 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `purchase_order_line_analytical_key` | bigint(20) | no | PRI |
| `canonical_purchase_order_line_id` | bigint(20) | no | UNI |
| `source_system` | varchar(50) | no | MUL |
| `source_domain` | varchar(100) | sí |  |
| `source_order_line_id` | varchar(100) | sí |  |
| `source_order_id` | varchar(100) | sí |  |
| `purchase_order_name` | varchar(255) | sí |  |
| `company_source_key` | varchar(255) | sí | MUL |
| `company_analytical_key` | bigint(20) | sí |  |
| `company_id` | varchar(100) | sí |  |
| `company_name` | varchar(255) | sí |  |
| `final_purchase_source_status` | varchar(100) | sí |  |
| `company_migration_type` | varchar(100) | sí |  |
| `history_source` | varchar(100) | sí |  |
| `include_odoo_history` | tinyint(1) | sí |  |
| `operational_start_date` | date | sí |  |
| `migration_policy_source` | varchar(100) | sí |  |
| `order_date` | datetime | sí |  |
| `order_date_key` | int(11) | sí |  |
| `vendor_analytical_key` | bigint(20) | sí | MUL |
| `vendor_id` | varchar(100) | sí |  |
| `vendor_name` | varchar(255) | sí |  |
| `normalized_vendor_name` | varchar(255) | sí |  |
| `is_internal_vendor` | tinyint(1) | no |  |
| `include_vendor_in_business_views` | tinyint(1) | no |  |
| `product_analytical_key` | bigint(20) | sí | MUL |
| `product_id` | varchar(100) | sí |  |
| `product_name` | varchar(255) | sí |  |
| `wansoft_code` | varchar(100) | sí |  |
| `wansoft_product_name` | varchar(255) | sí |  |
| `wansoft_department` | varchar(255) | sí |  |
| `product_mapping_found` | tinyint(1) | sí |  |
| `product_mapping_status` | varchar(100) | sí |  |
| `product_mapping_source` | varchar(100) | sí |  |
| `purchase_line_type` | varchar(100) | sí |  |
| `purchase_product_scope` | varchar(100) | sí |  |
| `purchase_mapping_bucket` | varchar(100) | sí |  |
| `purchase_classification_source` | varchar(100) | sí |  |
| `extracted_product_code` | varchar(100) | sí |  |
| `product_identity_status` | varchar(100) | sí |  |
| `dim_product_mapping_status` | varchar(100) | sí |  |
| `is_product_mapped` | tinyint(1) | no |  |
| `is_product_review_required` | tinyint(1) | no |  |
| `include_product_in_business_views` | tinyint(1) | no |  |
| `product_qty` | decimal(18,4) | sí |  |
| `qty_received` | decimal(18,4) | sí |  |
| `qty_invoiced` | decimal(18,4) | sí |  |
| `price_unit` | decimal(18,4) | sí |  |
| `price_subtotal` | decimal(18,4) | sí |  |
| `price_total` | decimal(18,4) | sí |  |
| `state` | varchar(100) | sí |  |
| `canonical_loaded_at` | timestamp | sí |  |
| `include_in_business_views` | tinyint(1) | no | MUL |
| `exclude_reason` | varchar(500) | sí |  |
| `line_review_status` | varchar(100) | sí |  |
| `catalog_status` | varchar(50) | sí |  |
| `created_at` | datetime | no |  |
| `updated_at` | datetime | no |  |

**`analytics_purchase_orders`**: órdenes de compra / facturas, Wansoft + Odoo (5.3). 43 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `purchase_order_analytical_key` | bigint(20) | no | PRI |
| `source_system` | varchar(50) | no | MUL |
| `source_domain` | varchar(100) | sí |  |
| `source_order_id` | varchar(100) | no |  |
| `purchase_order_name` | varchar(255) | sí |  |
| `company_source_key` | varchar(255) | sí | MUL |
| `company_analytical_key` | bigint(20) | sí |  |
| `company_id` | varchar(100) | sí |  |
| `company_name` | varchar(255) | sí |  |
| `final_purchase_source_status` | varchar(100) | sí |  |
| `company_migration_type` | varchar(100) | sí |  |
| `history_source` | varchar(100) | sí |  |
| `include_odoo_history` | tinyint(1) | sí |  |
| `operational_start_date` | date | sí |  |
| `migration_policy_source` | varchar(100) | sí |  |
| `order_date` | datetime | sí |  |
| `order_date_key` | int(11) | sí |  |
| `vendor_analytical_key` | bigint(20) | sí | MUL |
| `vendor_id` | varchar(100) | sí |  |
| `vendor_name` | varchar(255) | sí |  |
| `normalized_vendor_name` | varchar(255) | sí |  |
| `is_internal_vendor` | tinyint(1) | no |  |
| `include_vendor_in_business_views` | tinyint(1) | no |  |
| `line_count` | bigint(20) | no |  |
| `business_line_count` | bigint(20) | no |  |
| `excluded_line_count` | bigint(20) | no |  |
| `review_required_line_count` | bigint(20) | no |  |
| `internal_vendor_line_count` | bigint(20) | no |  |
| `review_required_product_line_count` | bigint(20) | no |  |
| `orphan_product_line_count` | bigint(20) | no |  |
| `product_qty_total` | decimal(18,4) | sí |  |
| `qty_received_total` | decimal(18,4) | sí |  |
| `qty_invoiced_total` | decimal(18,4) | sí |  |
| `price_subtotal_total` | decimal(18,4) | sí |  |
| `price_total_total` | decimal(18,4) | sí |  |
| `state_values` | text | sí |  |
| `canonical_loaded_at_min` | timestamp | sí |  |
| `canonical_loaded_at_max` | timestamp | sí |  |
| `include_in_business_views` | tinyint(1) | no | MUL |
| `exclude_reason` | varchar(500) | sí |  |
| `order_review_status` | varchar(100) | sí |  |
| `created_at` | datetime | no |  |
| `updated_at` | datetime | no |  |

**`analytics_purchase_daily_company_product`**: compras por sucursal × día × producto (5.3). 42 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `daily_company_product_key` | bigint(20) | no | PRI |
| `company_source_key` | varchar(255) | no | MUL |
| `company_analytical_key` | bigint(20) | sí |  |
| `order_date` | date | sí |  |
| `order_date_key` | int(11) | no |  |
| `product_analytical_key` | bigint(20) | sí | MUL |
| `product_analytical_group_key` | bigint(20) | no | MUL |
| `source_system` | varchar(50) | no | MUL |
| `product_identity_status` | varchar(100) | sí |  |
| `dim_product_mapping_status` | varchar(100) | sí |  |
| `is_product_mapped` | tinyint(1) | no |  |
| `is_product_review_required` | tinyint(1) | no |  |
| `include_product_in_business_views` | tinyint(1) | no |  |
| `line_count` | bigint(20) | no |  |
| `business_line_count` | bigint(20) | no |  |
| `excluded_line_count` | bigint(20) | no |  |
| `review_required_line_count` | bigint(20) | no |  |
| `internal_vendor_line_count` | bigint(20) | no |  |
| `review_required_product_line_count` | bigint(20) | no |  |
| `orphan_product_line_count` | bigint(20) | no |  |
| `purchase_order_count` | bigint(20) | no |  |
| `vendor_count` | bigint(20) | no |  |
| `product_qty_total` | decimal(18,4) | sí |  |
| `qty_received_total` | decimal(18,4) | sí |  |
| `qty_invoiced_total` | decimal(18,4) | sí |  |
| `business_product_qty_total` | decimal(18,4) | sí |  |
| `business_qty_received_total` | decimal(18,4) | sí |  |
| `business_qty_invoiced_total` | decimal(18,4) | sí |  |
| `excluded_product_qty_total` | decimal(18,4) | sí |  |
| `excluded_qty_received_total` | decimal(18,4) | sí |  |
| `excluded_qty_invoiced_total` | decimal(18,4) | sí |  |
| `price_subtotal_total` | decimal(18,4) | sí |  |
| `price_total_total` | decimal(18,4) | sí |  |
| `business_price_subtotal_total` | decimal(18,4) | sí |  |
| `business_price_total_total` | decimal(18,4) | sí |  |
| `excluded_price_subtotal_total` | decimal(18,4) | sí |  |
| `excluded_price_total_total` | decimal(18,4) | sí |  |
| `include_in_business_views` | tinyint(1) | no | MUL |
| `exclude_reason` | varchar(500) | sí |  |
| `aggregate_review_status` | varchar(100) | sí | MUL |
| `created_at` | datetime | no |  |
| `updated_at` | datetime | no |  |

**`getexpenses_factura`**: facturas de proveedor de Wansoft por cuenta contable (5.3). 37 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `id` | int(11) | no |  |
| `Sucursal` | varchar(255) | sí |  |
| `Factura_Id` | varchar(255) | sí |  |
| `IdDocumento` | varchar(255) | sí |  |
| `Folio` | varchar(255) | sí |  |
| `RFCProveedor` | varchar(255) | sí |  |
| `NombreProveedor` | varchar(255) | sí |  |
| `ClaveProveedor` | varchar(255) | sí |  |
| `CuentaContableProveedor` | varchar(255) | sí |  |
| `Subtotal` | varchar(255) | sí |  |
| `IVA` | varchar(255) | sí |  |
| `IEPS` | varchar(255) | sí |  |
| `Total` | varchar(255) | sí |  |
| `FechaDeExpedicion` | varchar(255) | sí |  |
| `FechaDeExpiracion` | varchar(255) | sí |  |
| `TerminosDePago` | varchar(255) | sí |  |
| `Cuenta` | varchar(255) | sí |  |
| `Subcuenta` | varchar(255) | sí |  |
| `Estatus` | varchar(255) | sí |  |
| `TotalDeudor` | varchar(255) | sí |  |
| `TipoDeEgreso` | varchar(255) | sí |  |
| `UUID` | varchar(255) | sí |  |
| `IdOrdenCompra` | varchar(255) | sí |  |
| `FolioOrdenCompra` | varchar(255) | sí |  |
| `FechaDeRegistro` | varchar(255) | sí |  |
| `DiasCredito` | varchar(255) | sí |  |
| `ColoniaProveedor` | varchar(255) | sí |  |
| `CiudadProveedor` | varchar(255) | sí |  |
| `CPProveedor` | varchar(255) | sí |  |
| `TelefonoProveedor` | varchar(255) | sí |  |
| `CorreoProveedor` | varchar(255) | sí |  |
| `CalleProveedor` | varchar(255) | sí |  |
| `NumeroIntProveedor` | varchar(255) | sí |  |
| `NumeroExtProveedor` | varchar(255) | sí |  |
| `Discount` | varchar(255) | sí |  |
| `Retentions` | varchar(255) | sí |  |
| `Egresos_Id` | varchar(255) | sí |  |

### A.4 Inventario

**`analytics_inventory_balance`**: existencias de hoy, las 19 sucursales (5.4). 15 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `inventory_balance_key` | bigint(20) | no | PRI |
| `company_source_key` | varchar(255) | no | MUL |
| `source_system` | varchar(20) | no |  |
| `wansoft_code` | varchar(255) | no | MUL |
| `product_name` | varchar(500) | sí |  |
| `current_balance_qty` | decimal(18,4) | no |  |
| `source_row_count` | bigint(20) | no |  |
| `entrada_qty` | decimal(18,4) | sí |  |
| `salida_qty` | decimal(18,4) | sí |  |
| `final_inventory_source_status` | varchar(100) | no |  |
| `include_in_business_views` | tinyint(1) | no | MUL |
| `exclude_reason` | varchar(500) | sí |  |
| `refreshed_at` | datetime | no |  |
| `created_at` | datetime | no |  |
| `updated_at` | datetime | no |  |

**`analytics_inventory_current_product_location`**: existencias de hoy de Odoo por ubicación (5.4). 37 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `inventory_current_product_location_key` | bigint(20) | no | PRI |
| `current_snapshot_loaded_at` | datetime | no | MUL |
| `snapshot_date` | date | sí |  |
| `snapshot_date_key` | int(11) | no | MUL |
| `product_analytical_key` | bigint(20) | no | MUL |
| `odoo_product_id` | varchar(100) | sí |  |
| `odoo_product_name` | varchar(500) | sí |  |
| `product_code` | varchar(255) | sí |  |
| `wansoft_code` | varchar(255) | sí |  |
| `wansoft_product_name` | varchar(500) | sí |  |
| `wansoft_department` | varchar(255) | sí |  |
| `product_identity_status` | varchar(100) | sí |  |
| `dim_product_mapping_status` | varchar(100) | sí |  |
| `is_product_mapped` | tinyint(1) | no |  |
| `is_product_review_required` | tinyint(1) | no |  |
| `include_product_in_business_views` | tinyint(1) | no |  |
| `source_location_id` | varchar(100) | no | MUL |
| `location_name` | varchar(500) | sí |  |
| `normalized_location_name` | varchar(500) | sí |  |
| `location_usage_type` | varchar(100) | sí |  |
| `is_virtual_location` | tinyint(1) | no |  |
| `is_partner_location` | tinyint(1) | no |  |
| `is_internal_location` | tinyint(1) | no |  |
| `location_mapping_status` | varchar(100) | sí |  |
| `company_source_key` | varchar(255) | sí |  |
| `company_mapping_status` | varchar(100) | sí |  |
| `source_row_count` | bigint(20) | no |  |
| `current_stock_qty` | decimal(18,4) | no |  |
| `positive_stock_qty` | decimal(18,4) | no |  |
| `zero_stock_row_count` | bigint(20) | no |  |
| `negative_stock_qty` | decimal(18,4) | no |  |
| `negative_row_count` | bigint(20) | no |  |
| `include_in_business_views` | tinyint(1) | no | MUL |
| `exclude_reason` | varchar(500) | sí |  |
| `aggregate_review_status` | varchar(100) | no | MUL |
| `created_at` | datetime | no |  |
| `updated_at` | datetime | no |  |

**`getinputinventory_entrada`**: entradas de inventario de Wansoft (5.4). 38 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `id` | int(11) | no | PRI |
| `subsidiary_name` | varchar(255) | sí |  |
| `IdEntrada` | varchar(50) | sí | MUL |
| `ClaveAlmacen` | varchar(50) | sí |  |
| `Almacen` | varchar(255) | sí |  |
| `IdAlmacen` | int(11) | sí |  |
| `CuentaContableAlmacen` | varchar(255) | sí |  |
| `CodigoDepartamento` | varchar(255) | sí |  |
| `Departamento` | varchar(255) | sí |  |
| `CuentaContableDepartamento` | varchar(255) | sí |  |
| `IdProducto` | int(11) | sí |  |
| `CodigoProducto` | varchar(50) | sí |  |
| `NombreProducto` | varchar(255) | sí |  |
| `CodigoUnidadDeMedida` | varchar(50) | sí |  |
| `IdUnidadDeMedida` | int(11) | sí |  |
| `UnidadDeMedida` | varchar(50) | sí |  |
| `TipoEntrada` | varchar(50) | sí |  |
| `Cantidad` | decimal(15,10) | sí |  |
| `CostoUnitario` | decimal(15,4) | sí |  |
| `ProductoConIVA` | tinyint(1) | sí |  |
| `Caducidad` | date | sí |  |
| `FechaEntrada` | datetime | sí | MUL |
| `Factura` | varchar(50) | sí |  |
| `FechaFactura` | date | sí |  |
| `RFCProveedor` | varchar(50) | sí |  |
| `ClaveProveedor` | varchar(50) | sí |  |
| `NombreProveedor` | varchar(255) | sí |  |
| `IdTransferencia` | int(11) | sí |  |
| `FolioTransferencia` | varchar(50) | sí |  |
| `IdOrdenCompra` | int(11) | sí |  |
| `FolioOrdenCompra` | varchar(50) | sí |  |
| `RFCProveedorOrdenCompra` | varchar(50) | sí |  |
| `ProveedorOrdenCompra` | varchar(255) | sí |  |
| `IdDocumento` | int(11) | sí |  |
| `IdUsuario` | int(11) | sí |  |
| `NombreUsuario` | varchar(255) | sí |  |
| `FechaReal` | date | sí |  |
| `created_at` | timestamp | no |  |

**`getoutgoinginventory_salida`**: salidas de inventario de Wansoft (5.4). 29 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `id` | int(11) | no | PRI |
| `subsidiary_name` | varchar(255) | sí | MUL |
| `IdSalida` | varchar(50) | sí |  |
| `IdEntrada` | varchar(50) | sí |  |
| `IdAlmacen` | int(11) | sí |  |
| `Almacen` | varchar(255) | sí |  |
| `CuentaContableAlmacen` | varchar(255) | sí |  |
| `CuentaContableDepartamento` | varchar(255) | sí |  |
| `Departamento` | varchar(255) | sí |  |
| `IdProducto` | int(11) | sí |  |
| `CodigoProducto` | varchar(50) | sí |  |
| `NombreProducto` | varchar(255) | sí |  |
| `CodigoUnidadDeMedida` | varchar(50) | sí |  |
| `IdUnidadDeMedida` | int(11) | sí |  |
| `UnidadDeMedida` | varchar(50) | sí |  |
| `TipoSalida` | varchar(50) | sí |  |
| `Cantidad` | decimal(15,10) | sí |  |
| `CostoUnitario` | decimal(15,4) | sí |  |
| `Caducidad` | date | sí |  |
| `FechaSalida` | datetime | sí | MUL |
| `IdTransferencia` | varchar(50) | sí |  |
| `FolioTransferencia` | varchar(50) | sí |  |
| `Orden` | varchar(50) | sí |  |
| `Fecha` | date | sí |  |
| `IdDetalleVenta` | varchar(50) | sí |  |
| `IdUsuario` | varchar(50) | sí |  |
| `NombreUsuario` | varchar(255) | sí |  |
| `FechaReal` | date | sí |  |
| `created_at` | timestamp | no |  |

**`wansoft_parallel_inputinventory_entrada`**: entradas que las sucursales de Odoo siguen capturando en Wansoft, solo para comparar (5.4). 38 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `id` | int(11) | no | PRI |
| `subsidiary_name` | varchar(255) | sí |  |
| `IdEntrada` | varchar(50) | sí | MUL |
| `ClaveAlmacen` | varchar(50) | sí |  |
| `Almacen` | varchar(255) | sí |  |
| `IdAlmacen` | int(11) | sí |  |
| `CuentaContableAlmacen` | varchar(255) | sí |  |
| `CodigoDepartamento` | varchar(255) | sí |  |
| `Departamento` | varchar(255) | sí |  |
| `CuentaContableDepartamento` | varchar(255) | sí |  |
| `IdProducto` | int(11) | sí |  |
| `CodigoProducto` | varchar(50) | sí |  |
| `NombreProducto` | varchar(255) | sí |  |
| `CodigoUnidadDeMedida` | varchar(50) | sí |  |
| `IdUnidadDeMedida` | int(11) | sí |  |
| `UnidadDeMedida` | varchar(50) | sí |  |
| `TipoEntrada` | varchar(50) | sí |  |
| `Cantidad` | decimal(15,10) | sí |  |
| `CostoUnitario` | decimal(15,4) | sí |  |
| `ProductoConIVA` | tinyint(1) | sí |  |
| `Caducidad` | date | sí |  |
| `FechaEntrada` | datetime | sí | MUL |
| `Factura` | varchar(50) | sí |  |
| `FechaFactura` | date | sí |  |
| `RFCProveedor` | varchar(50) | sí |  |
| `ClaveProveedor` | varchar(50) | sí |  |
| `NombreProveedor` | varchar(255) | sí |  |
| `IdTransferencia` | int(11) | sí |  |
| `FolioTransferencia` | varchar(50) | sí |  |
| `IdOrdenCompra` | int(11) | sí |  |
| `FolioOrdenCompra` | varchar(50) | sí |  |
| `RFCProveedorOrdenCompra` | varchar(50) | sí |  |
| `ProveedorOrdenCompra` | varchar(255) | sí |  |
| `IdDocumento` | int(11) | sí |  |
| `IdUsuario` | int(11) | sí |  |
| `NombreUsuario` | varchar(255) | sí |  |
| `FechaReal` | date | sí |  |
| `created_at` | timestamp | no |  |

**`wansoft_parallel_outgoinginventory_salida`**: salidas que las sucursales de Odoo siguen capturando en Wansoft, solo para comparar (5.4). 29 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `id` | int(11) | no | PRI |
| `subsidiary_name` | varchar(255) | sí | MUL |
| `IdSalida` | varchar(50) | sí |  |
| `IdEntrada` | varchar(50) | sí |  |
| `IdAlmacen` | int(11) | sí |  |
| `Almacen` | varchar(255) | sí |  |
| `CuentaContableAlmacen` | varchar(255) | sí |  |
| `CuentaContableDepartamento` | varchar(255) | sí |  |
| `Departamento` | varchar(255) | sí |  |
| `IdProducto` | int(11) | sí |  |
| `CodigoProducto` | varchar(50) | sí |  |
| `NombreProducto` | varchar(255) | sí |  |
| `CodigoUnidadDeMedida` | varchar(50) | sí |  |
| `IdUnidadDeMedida` | int(11) | sí |  |
| `UnidadDeMedida` | varchar(50) | sí |  |
| `TipoSalida` | varchar(50) | sí |  |
| `Cantidad` | decimal(15,10) | sí |  |
| `CostoUnitario` | decimal(15,4) | sí |  |
| `Caducidad` | date | sí |  |
| `FechaSalida` | datetime | sí | MUL |
| `IdTransferencia` | varchar(50) | sí |  |
| `FolioTransferencia` | varchar(50) | sí |  |
| `Orden` | varchar(50) | sí |  |
| `Fecha` | date | sí |  |
| `IdDetalleVenta` | varchar(50) | sí |  |
| `IdUsuario` | varchar(50) | sí |  |
| `NombreUsuario` | varchar(255) | sí |  |
| `FechaReal` | date | sí |  |
| `created_at` | timestamp | no |  |

**`odoo_inventory_quant_daily`**: existencias de Odoo día por día, desde 2026-10-08 (5.4). 14 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `stock_date` | date | no | PRI |
| `odoo_location_id` | int(11) | no | PRI |
| `odoo_product_id` | int(11) | no | PRI |
| `captured_at` | datetime | no |  |
| `odoo_company_id` | int(11) | sí |  |
| `odoo_company_name` | varchar(255) | sí |  |
| `company_source_key` | varchar(100) | sí | MUL |
| `location_name` | varchar(500) | sí |  |
| `location_usage` | varchar(30) | no |  |
| `product_code` | varchar(100) | sí |  |
| `product_name` | varchar(500) | sí |  |
| `quantity` | decimal(18,4) | no |  |
| `reserved_quantity` | decimal(18,4) | no |  |
| `quant_count` | int(11) | no |  |

**`analytics_inventory_movements`**: movimientos de inventario unificados, Wansoft + Odoo (5.4). 24 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `movement_key` | bigint(20) | no | PRI |
| `movement_date` | date | no |  |
| `company_source_key` | varchar(100) | no | MUL |
| `source_system` | varchar(10) | no | MUL |
| `source_record` | varchar(20) | no | MUL |
| `source_movement_id` | varchar(80) | no |  |
| `captured_date` | date | sí |  |
| `direction` | char(3) | no |  |
| `movement_type` | varchar(20) | no |  |
| `source_movement_type` | varchar(100) | sí |  |
| `wansoft_code` | varchar(50) | sí |  |
| `odoo_product_id` | int(11) | sí |  |
| `product_name` | varchar(255) | sí |  |
| `unit_name` | varchar(50) | sí |  |
| `quantity` | decimal(18,6) | no |  |
| `unit_cost` | decimal(18,6) | sí |  |
| `total_cost` | decimal(18,4) | sí |  |
| `location_name` | varchar(255) | sí |  |
| `counts_in_stock` | tinyint(1) | no |  |
| `final_source_status` | varchar(40) | no |  |
| `include_in_business_views` | tinyint(1) | no |  |
| `loaded_at` | datetime | no |  |
| `product_code` | varchar(60) | sí | MUL |
| `product_code_status` | varchar(15) | sí |  |

**`analytics_odoo_product_code`**: código de Wansoft de cada producto de Odoo (5.4). 6 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `odoo_product_id` | int(11) | no | PRI |
| `odoo_product_name` | varchar(255) | sí |  |
| `wansoft_code` | varchar(50) | no | MUL |
| `wansoft_product_name` | varchar(255) | sí |  |
| `mapping_source` | varchar(50) | sí |  |
| `updated_at` | datetime | no |  |

### A.5 Gobierno y dimensiones

**`analytics_company_domain_coverage`**: fuente de cada dominio por sucursal (5.6). 31 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `company_source_key` | varchar(255) | no | PRI |
| `display_name` | varchar(255) | no |  |
| `is_active_branch` | tinyint(1) | no |  |
| `is_internal_provider` | tinyint(1) | no |  |
| `is_final_operating_branch` | tinyint(1) | no |  |
| `is_future_rollout` | tinyint(1) | no |  |
| `is_zenput_location` | tinyint(1) | no |  |
| `is_zenput_only` | tinyint(1) | no |  |
| `purchases_source_system` | varchar(100) | no |  |
| `inventory_source_system` | varchar(100) | no |  |
| `sales_source_system` | varchar(100) | no |  |
| `zenput_source_status` | varchar(100) | no |  |
| `rollout_type` | varchar(100) | sí | MUL |
| `rollout_status` | varchar(100) | sí |  |
| `operational_start_date` | date | sí |  |
| `has_purchases` | tinyint(1) | no | MUL |
| `has_purchase_orders` | tinyint(1) | no |  |
| `has_purchase_lines` | tinyint(1) | no |  |
| `has_inventory` | tinyint(1) | no |  |
| `has_zenput_submissions` | tinyint(1) | no |  |
| `has_zenput_tasks` | tinyint(1) | no |  |
| `has_sales_future_placeholder` | tinyint(1) | no |  |
| `purchase_order_count` | bigint(20) | no |  |
| `purchase_line_count` | bigint(20) | no |  |
| `inventory_snapshot_count` | bigint(20) | no |  |
| `zenput_submission_count` | bigint(20) | no |  |
| `zenput_task_count` | bigint(20) | no |  |
| `coverage_status` | varchar(100) | no | MUL |
| `coverage_notes` | text | sí |  |
| `created_at` | datetime | no |  |
| `updated_at` | datetime | no |  |

**`dim_company_analytical`**: sucursales y empresas (5.6). 25 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `company_analytical_key` | bigint(20) | no | PRI |
| `company_source_key` | varchar(255) | no | UNI |
| `display_name` | varchar(255) | no | MUL |
| `normalized_name` | varchar(255) | sí |  |
| `brand_group` | varchar(255) | sí |  |
| `is_active_branch` | tinyint(1) | no |  |
| `is_internal_provider` | tinyint(1) | no |  |
| `is_final_operating_branch` | tinyint(1) | no |  |
| `is_future_rollout` | tinyint(1) | no |  |
| `is_wansoft_company` | tinyint(1) | no |  |
| `is_odoo_company` | tinyint(1) | no |  |
| `is_zenput_location` | tinyint(1) | no |  |
| `is_zenput_only` | tinyint(1) | no |  |
| `purchases_source_system` | varchar(100) | no | MUL |
| `inventory_source_system` | varchar(100) | no |  |
| `sales_source_system` | varchar(100) | no |  |
| `zenput_source_status` | varchar(100) | no |  |
| `rollout_type` | varchar(100) | sí | MUL |
| `rollout_status` | varchar(100) | sí |  |
| `operational_start_date` | date | sí |  |
| `include_in_business_views` | tinyint(1) | no |  |
| `exclude_reason` | varchar(255) | sí |  |
| `notes` | text | sí |  |
| `created_at` | datetime | no |  |
| `updated_at` | datetime | no |  |

**`dim_product`**: productos (5.3). 38 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `product_analytical_key` | bigint(20) | no | PRI |
| `product_display_name` | varchar(500) | no |  |
| `normalized_product_name` | varchar(500) | no | MUL |
| `product_canonical_name` | varchar(500) | sí |  |
| `product_identity_status` | varchar(100) | no | MUL |
| `wansoft_code` | varchar(255) | sí | MUL |
| `wansoft_product_name` | varchar(500) | sí |  |
| `wansoft_department` | varchar(255) | sí |  |
| `wansoft_family` | varchar(255) | sí |  |
| `wansoft_group` | varchar(255) | sí |  |
| `odoo_product_id` | varchar(255) | sí | MUL |
| `odoo_product_name` | varchar(500) | sí |  |
| `odoo_default_code` | varchar(255) | sí |  |
| `odoo_category` | varchar(255) | sí |  |
| `odoo_uom` | varchar(100) | sí |  |
| `mapping_status` | varchar(100) | no | MUL |
| `mapping_source` | varchar(255) | sí |  |
| `mapping_confidence` | varchar(100) | sí |  |
| `is_mapped` | tinyint(1) | no |  |
| `is_unmapped` | tinyint(1) | no |  |
| `is_review_required` | tinyint(1) | no |  |
| `is_excluded` | tinyint(1) | no |  |
| `exclude_reason` | varchar(255) | sí |  |
| `company_scope` | varchar(255) | sí |  |
| `scope_bucket` | varchar(255) | sí | MUL |
| `product_business_domain` | varchar(255) | sí |  |
| `is_restaurant_product` | tinyint(1) | no |  |
| `is_bodegon_product` | tinyint(1) | no |  |
| `is_empanadas_product` | tinyint(1) | no |  |
| `is_shared_cross_company` | tinyint(1) | no |  |
| `source_system` | varchar(100) | no | MUL |
| `source_table` | varchar(255) | sí |  |
| `source_product_key` | varchar(255) | no |  |
| `source_product_name` | varchar(500) | sí |  |
| `include_in_business_views` | tinyint(1) | no | MUL |
| `notes` | text | sí |  |
| `created_at` | datetime | no |  |
| `updated_at` | datetime | no |  |

**`dim_vendor`**: proveedores (5.3). 18 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `vendor_analytical_key` | bigint(20) | no | PRI |
| `vendor_display_name` | varchar(255) | no | MUL |
| `normalized_vendor_name` | varchar(255) | no | UNI |
| `vendor_canonical_name` | varchar(255) | sí |  |
| `vendor_source_system` | varchar(100) | no | MUL |
| `wansoft_vendor_id` | varchar(255) | sí |  |
| `odoo_vendor_id` | varchar(255) | sí |  |
| `source_vendor_name` | text | sí |  |
| `source_vendor_key` | text | sí |  |
| `is_internal_vendor` | tinyint(1) | no | MUL |
| `is_external_vendor` | tinyint(1) | no |  |
| `is_active` | tinyint(1) | no |  |
| `is_review_required` | tinyint(1) | no |  |
| `include_in_business_views` | tinyint(1) | no | MUL |
| `exclude_reason` | varchar(255) | sí |  |
| `notes` | text | sí |  |
| `created_at` | datetime | no |  |
| `updated_at` | datetime | no |  |

**`dim_time`**: calendario (5.6). 37 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `date_key` | int(11) | no | PRI |
| `calendar_date` | date | no | UNI |
| `year` | smallint(6) | no | MUL |
| `year_start_date` | date | no |  |
| `year_end_date` | date | no |  |
| `is_year_start` | tinyint(1) | no |  |
| `is_year_end` | tinyint(1) | no |  |
| `quarter_number` | tinyint(4) | no |  |
| `quarter_name` | varchar(10) | no |  |
| `year_quarter` | varchar(20) | no | MUL |
| `quarter_start_date` | date | no |  |
| `quarter_end_date` | date | no |  |
| `is_quarter_start` | tinyint(1) | no |  |
| `is_quarter_end` | tinyint(1) | no |  |
| `month_number` | tinyint(4) | no |  |
| `month_name` | varchar(20) | no |  |
| `month_short_name` | varchar(10) | no |  |
| `year_month_label` | varchar(10) | no | MUL |
| `month_start_date` | date | no |  |
| `month_end_date` | date | no |  |
| `is_month_start` | tinyint(1) | no |  |
| `is_month_end` | tinyint(1) | no |  |
| `week_of_year` | tinyint(4) | no |  |
| `iso_week_of_year` | tinyint(4) | no |  |
| `iso_year` | smallint(6) | no | MUL |
| `week_start_date` | date | no |  |
| `week_end_date` | date | no |  |
| `is_week_start` | tinyint(1) | no |  |
| `is_week_end` | tinyint(1) | no |  |
| `day_of_month` | tinyint(4) | no |  |
| `day_of_year` | smallint(6) | no |  |
| `day_of_week_number` | tinyint(4) | no |  |
| `day_of_week_name` | varchar(20) | no |  |
| `day_of_week_short_name` | varchar(10) | no |  |
| `is_weekend` | tinyint(1) | no | MUL |
| `created_at` | datetime | no |  |
| `updated_at` | datetime | no |  |

### A.6 Zenput (base zenput)

**`form_templates`**: plantillas de checklist (5.5). 8 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `form_id` | int(11) | no | PRI |
| `title` | varchar(255) | sí |  |
| `num_submissions` | int(11) | sí |  |
| `date_created` | datetime | sí |  |
| `date_last_submitted` | datetime | sí |  |
| `creator_full_name` | varchar(255) | sí |  |
| `category_name` | varchar(255) | sí |  |
| `last_updated` | timestamp | no |  |

**`submissions`**: checklists contestados (5.5). 6 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `submission_id` | varchar(255) | no | PRI |
| `form_template_id` | int(11) | sí | MUL |
| `location_name` | varchar(255) | sí |  |
| `user_display_name` | varchar(255) | sí |  |
| `date_submitted` | datetime | sí |  |
| `time_to_complete` | int(11) | sí |  |

**`submission_answers`**: respuestas (5.5). 6 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `answer_id` | int(11) | no | PRI |
| `submission_id` | varchar(255) | sí | MUL |
| `field_id` | int(11) | sí |  |
| `title` | text | sí |  |
| `field_type` | varchar(50) | sí |  |
| `value_as_string` | text | sí |  |

**`zenput_tasks`**: tareas (5.5). 42 columnas.

| Columna | Tipo | Nulo | Llave |
|---|---|---|---|
| `task_id` | int(11) | no | PRI |
| `title` | text | sí |  |
| `description` | text | sí |  |
| `company_id` | int(11) | sí |  |
| `account_id` | int(11) | sí |  |
| `account_name` | varchar(255) | sí |  |
| `account_address` | text | sí |  |
| `account_city` | varchar(100) | sí |  |
| `account_state` | varchar(100) | sí |  |
| `account_zipcode` | varchar(20) | sí |  |
| `account_country` | varchar(10) | sí |  |
| `account_lat` | decimal(10,8) | sí |  |
| `account_lon` | decimal(11,8) | sí |  |
| `status_id` | int(11) | sí |  |
| `status_type` | varchar(50) | sí |  |
| `status_name` | varchar(50) | sí |  |
| `reply_type` | varchar(50) | sí |  |
| `reporter_id` | int(11) | sí |  |
| `reporter_display_name` | varchar(255) | sí |  |
| `assignee_id` | int(11) | sí |  |
| `assignee_display_name` | varchar(255) | sí |  |
| `date_created` | datetime | sí |  |
| `date_modified` | datetime | sí |  |
| `date_start` | datetime | sí |  |
| `date_due` | datetime | sí |  |
| `time_zone` | varchar(100) | sí |  |
| `is_active` | tinyint(1) | sí |  |
| `is_closed` | tinyint(1) | sí |  |
| `project_id` | int(11) | sí |  |
| `fulfillment_type` | varchar(50) | sí |  |
| `fulfillment_date_completed` | datetime | sí |  |
| `fulfillment_date_submitted` | datetime | sí |  |
| `fulfillment_user_id` | int(11) | sí |  |
| `fulfillment_user_display_name` | varchar(255) | sí |  |
| `fulfillment_fields` | longtext | sí |  |
| `date_submitted` | datetime | sí |  |
| `deleted` | tinyint(1) | sí |  |
| `num_comments` | int(11) | sí |  |
| `is_completed_late` | tinyint(1) | sí |  |
| `current_state` | varchar(50) | sí |  |
| `subscribers` | longtext | sí |  |
| `last_updated` | timestamp | no |  |

<!-- schema-appendix:end -->

