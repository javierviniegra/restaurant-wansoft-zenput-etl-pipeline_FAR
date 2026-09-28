# Guía de acceso a datos — bases analíticas de Fonda Argentina

*English version: [data-access-guide.en.md](data-access-guide.en.md)*

Para: equipos externos que construirán su propio ETL sobre estas bases (por
ejemplo, una capa de preguntas y respuestas / chatbot). Indica **qué tabla usar
para cada pregunta de negocio, qué campos importan, cómo se unen las tablas y
qué trampas evitar**. Cada regla se verificó contra el esquema y los datos
reales el 2026-09-28. Versión en PDF: [data-access-guide.es.pdf](data-access-guide.es.pdf).

## Índice

1. [Qué hay y dónde](#1-qué-hay-y-dónde)
2. [Reglas de oro](#2-reglas-de-oro-léelas-antes-de-escribir-cualquier-consulta)
3. [Equivalencias de sucursales](#3-equivalencias-de-sucursales)
4. [Qué tabla responde cada pregunta](#4-qué-tabla-responde-cada-pregunta)
   - [4.1 Histórico disponible](#41-histórico-disponible)
5. [Dominios](#5-dominios)
   - [5.1 Ventas](#51-ventas-wansoft-todas-las-sucursales)
   - [5.2 Costos](#52-costos-wansoft-sucursales-nuevas-desde-odoo)
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
| **Wansoft** (punto de venta / ERP) | Ventas de todas las sucursales, costos, cierre de caja, y compras/inventario de las sucursales que aún no están en Odoo | Descarga diaria por su API SOAP |
| **Odoo** | Compras e inventario de las sucursales migradas a Odoo | Extracción diaria de solo lectura |
| **Zenput** | Checklists y tareas | Descarga diaria por API |

Capas dentro de `wansoft`:

| Capa | Tablas | Úsala para |
|---|---|---|
| Copias de Wansoft | `get*`, `costeomensual*` | Ventas, costos, cierre de caja, detalle del lado Wansoft |
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
   costos/inventario de Wansoft 5, compras 35), así que los últimos días todavía
   pueden cambiar.
7. Las tablas de costos son **fotos acumuladas**, no montos diarios (Sección 5.2).

---

## 3. Equivalencias de sucursales

| ID Wansoft | Clave corta (`Sucursal`, `company_source_key`) | Nombre largo Wansoft (costos) | Empresa en Odoo | Fuente de compras e inventario | Arranque en Odoo |
|---|---|---|---|---|---|
| 5320 | Acoxpa | Fonda Argentina - Acoxpa | FONDA COSTA NERA | Odoo | 2026-07-01 |
| 4959 | Aeropuerto | Fonda Argentina - Aeropuerto | FONDA ARGENTINA AEROPUERTO | Wansoft | — |
| 4960 | Antenas | Fonda Argentina - Antenas | FONDA ARGENTINA LAS ANTENAS | Odoo | 2026-06-01 |
| 6175 | Cancun | Fonda Argentina - Cancún | — | Wansoft | — |
| 12802 | CentroMyJ | Fonda Argentina - Centro Mario y July | MARIO Y JULY | Odoo (nació en Odoo) | 2026-06-01 |
| 4958 | Isabel La Católica | Fonda Argentina - Isabel La Católica | FONDA ARGENTINA | Wansoft → **Odoo desde 2026-10-01** | 2026-10-01 |
| 12057 | La Esquina Coyoacán | Fonda Argentina - Coyoacan | FONDA ARGENTINA COYOACAN | Odoo | 2026-06-01 |
| 4752 | Metepec | Fonda Argentina - Tollocan | FONDA ARGENTINA TOLLOCAN | Wansoft | — |
| 4433 | Napoles | Fonda Argentina - Nápoles | FONDA ARGENTINA POLYFORUM | Wansoft | — |
| 5943 | Oceanía | Fonda Argentina - Oceanía | FONDA ARGENTINA ENCUENTRO OCEANIA | Odoo | 2026-06-30 |
| 6174 | Playa del Carmen | Fonda Argentina - Playa del Carmen | — | Wansoft | — |
| 12806 | Puebla | Fonda Argentina - Puebla | FONDA ARGENTINA PUEBLA | Odoo (nació en Odoo) | 2026-06-10 |
| 5319 | San Jeronimo | Fonda Argentina – San Jerónimo | FONDA ARGENTINA SAN JERONIMO | Wansoft → **Odoo desde 2026-10-01** | 2026-10-01 |
| 5321 | Taquería parroquia | Fonda Argentina – Taquería Parroquía | — | Wansoft | — |
| 4962 | Taquería Viaducto | Fonda Argentina - Taqueria Viaducto | — | Wansoft | — |
| 6560 | Tepeyac | Fonda Argentina - Tepeyac | FONDA ARGENTINA MAQ | Odoo | 2026-06-01 |
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
- **Costos de las sucursales migradas:** hoy siguen viniendo de Wansoft, a
  propósito y de forma temporal. Por seguridad, estas sucursales siguen
  capturando sus compras también en Wansoft (respaldo si Odoo fallara, y para
  validar que las compras de Odoo corresponden a las de Wansoft), así que
  Wansoft sigue calculando su costo completo. Cuando dejen de capturar compras
  en Wansoft y ahí solo queden ventas y cierres diarios, su costo pasará a
  calcularse desde Odoo. Ver sección 5.2.
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

### 4.1 Histórico disponible

Fechas medidas en producción el 2026-09-28. Las tablas se siguen llenando a diario hasta el día anterior.

| Dato | Tabla | Fuente | Desde | Notas |
|---|---|---|---|---|
| Ventas: tickets, detalle, modificadores | `getallordenesbyday_new_venta`, `_new_detalleventa`, `_new_modificador` | Wansoft | 2021-09-01 | Del 14 al 31 de diciembre de 2021 casi no hay tickets (hueco del histórico de origen, aceptado) |
| Ventas: pagos por ticket | `getallordenesbyday_new_pago` | Wansoft | 2025-01-01 | Antes de 2025 no hay pagos por ticket; usa el cierre de caja |
| Cierre de caja diario | `getglobalcashclosing` | Wansoft | 2022-01-01 |  |
| Costo de venta diario | `gettotalcostbydate` | Wansoft (nuevas: Odoo) | 2021-07-31 |  |
| Costo mensual acumulado | `costeomensual` | Wansoft (nuevas: Odoo) | 2022-01-01 |  |
| Costo semanal acumulado | `costeomensual_semanapyq` | Wansoft (nuevas: Odoo) | 2024-01-02 |  |
| Tablajería | `gettablajeriareport` | Wansoft | 2022-01-01 | Va de salida (sección 5.2) |
| Facturas de proveedor por cuenta contable | `getexpenses_factura` | Wansoft | 2019-02-18 | El histórico más antiguo; solo mientras la sucursal captura en Wansoft |
| Entradas de inventario | `getinputinventory_entrada` | Wansoft | 2021-09-01 |  |
| Salidas de inventario | `getoutgoinginventory_salida` | Wansoft | 2020-11-30 | Unas 1.15 millones de filas traen fecha vacía (`0000-00-00`); exclúyelas |
| **Compras unificadas** | `analytics_purchase_order_lines`, `analytics_purchase_orders`, `analytics_purchase_daily_company_product` | **Wansoft + Odoo** | **2021-09-01** | Wansoft hasta el arranque de cada sucursal en Odoo y Odoo desde entonces (junio de 2026 en adelante). Verificado año por año: mismos renglones y pesos que las facturas de Wansoft en producción |
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

### 5.2 Costos (Wansoft; sucursales nuevas desde Odoo)

De dónde viene el costo de cada sucursal:

| Tipo de sucursal | Fuente del costo hoy |
|---|---|
| Solo Wansoft | Reporte de costos de Wansoft |
| Migrada a Odoo (Acoxpa, Antenas, Tepeyac, Oceanía, La Esquina Coyoacán; desde 2026-10-01 también Isabel La Católica, San Jeronimo, Vía Vallejo) | Reporte de costos de Wansoft, **temporalmente**: siguen capturando compras en paralelo en Wansoft como respaldo y para validar Odoo. Pasará a Odoo cuando dejen de hacerlo |
| Nueva, nacida en Odoo (Puebla, CentroMyJ y las que abran después) | Calculado desde la contabilidad de Odoo (cuentas de costo directo) y guardado en las mismas tablas |

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
| Costo Total | `CostoTotal - CostoDeConsumo` |
| Costo Teórico | `CostoDeProductosVendidos` |
| Gasto de Venta | `CostoDeConsumo` |
| Costo de Mermas | `CostoDeMerma` |
| Cortesías / Cancelaciones | `CostoDeCortesías`, `CostoDeCancelaciones` (valor de venta, del cierre de caja) |

```sql
-- Costo del mes por sucursal: última foto del mes
SELECT c.subsidiary_id, c.subsidiary_name, c.created_date,
       c.CostoTotal - c.CostoDeConsumo AS costo_total,
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

Ejemplo real (Acoxpa, arranque en Odoo el 2026-07-01): enero a junio salen
con `source_system = 'wansoft'` y de julio en adelante con `'odoo'`, sin
meses repetidos ni faltantes.

**`getexpenses_factura` es otra cosa:** son todas las facturas de proveedor de
Wansoft clasificadas por cuenta contable (`Cuenta`: Costo operativo, Gastos de
venta, Gastos directos, Sueldos y salarios, Fletes...), incluidos servicios,
software y nómina, que no son mercancía. Las órdenes de compra de Odoo solo
cubren mercancía. Por eso:
- Para compras de mercancía de ambos sistemas, usa la capa analítica.
- Para comparar con los reportes de "Compras" de Wansoft, usa solo
  `Cuenta = 'Costo operativo'`.
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
  Wansoft), costos/inventario/cierre de caja de Wansoft 5 días, compras 35 días.
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
