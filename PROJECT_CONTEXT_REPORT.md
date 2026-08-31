# PROJECT_CONTEXT_REPORT.md

Documento maestro de continuidad. Generado/actualizado automáticamente al cierre de pasos mayores, bajo solicitud explícita ("Genera reporte de contexto del proyecto"), cuando la conversación se vuelve muy extensa, cuando el contexto consumido supera ~70%, o cuando se necesita abrir un chat nuevo por límite de tokens. Siempre se regenera completo, nunca como parche incremental.

Última generación: 2026-08-31, cerrando la sesión de "checkpoint de cutover + auditoría de alcance por sucursal", antes de comitear todo el trabajo acumulado (esta sesión y la sesión del gate del 2026-08-27, que quedó sin comitear). El gate de aceptación sigue **sin cierre formal explícito** del usuario, pero la evidencia a favor se reforzó de forma importante hoy: se encontraron y corrigieron 3 bugs reales adicionales, todos en la dirección de "el sistema es más confiable de lo que las comparaciones sucias sugerían".

---

# 1. Resumen Ejecutivo

**Objetivo general del proyecto:** construir una capa analítica unificada en MySQL que integre Wansoft, Odoo y Zenput, ocultando al usuario final qué sistema origina cada dato.

**Estado actual:** Inventario, Costos y Compras funcionalmente completos para las 6 sucursales activas en Odoo (Antenas, La Esquina Coyoacán, CentroMyJ, Acoxpa, Tepeyac, Oceanía; Puebla documentada como rollout futuro, `is_active=0`). El gate de aceptación (iniciado 2026-08-27) tiene evidencia fuerte y ahora más limpia, pero el usuario nunca dio un "sí, aceptado" explícito — quedó pendiente el 28 ("permíteme y mañana continuamos") y la sesión del 31 se desvió hacia dos pedidos nuevos del usuario que terminaron revelando y corrigiendo bugs reales adicionales.

**Avance estimado:** 97% (sube desde 94%; el checkpoint de cutover automatizado quedó construido, probado con datos reales y en 20/20 PASS; 3 bugs de producción reales encontrados y corregidos; automatización de Inventario que no existía, agregada. Falta: decisión explícita de "gate aceptado" y comit/push de todo — este último se resuelve en esta misma sesión).

**Bloque actual:** comitear y pushear todo el trabajo acumulado (sesión del gate 2026-08-27 + esta sesión). Ver Sección 8.

## Qué se hizo en esta sesión (2026-08-31), en orden:

**Parte 1 — Bug en el candado de Ventas (`extractAllOrdersByDay.py`):**
1. El usuario reportó: el candado de Ventas, al detectar una diferencia contra el Cierre Z de Wansoft y corregir, reescribía MySQL usando el XML ya cacheado en disco (`asegurar_xml_disponible`) en vez de pedir uno nuevo — si ese archivo cacheado era la fuente del desfase original, la "corrección" no arreglaba nada.
2. Aclarado: la comparación (PASO 2, contra `GetGlobalCashClosing_Xml`) ya era fresca vía SOAP todos los días — el bug estaba solo en la reescritura. Corregido: al detectar diferencia, ahora se fuerza una re-descarga real desde Wansoft antes de `reescribir_desde_xml` (`legacy/wansoft/automaticos/extractAllOrdersByDay.py`, PASO 4).

**Parte 2 — Diseño del checkpoint de cutover T+7/T+30:**
3. El usuario planteó el riesgo real de producción: sucursales con Compras/Inventario en ambos sistemas (Wansoft + Odoo) durante el mes de migración pueden romper saldos mensuales si no se sabe con certeza qué ya está en Odoo. Se discutió: cutover a inicio de mes (ya es el patrón usado), no confiar en la palabra de las sucursales, y en su lugar **verificar programáticamente** unos días después del despliegue.
4. Decisión del usuario: checkpoints en T+7 y T+30 después de `operational_start_date`, cada combinación (sucursal, dominio, checkpoint) se valida **una sola vez** (no diario), comparando MySQL (dev) contra una lectura fresca e independiente de Odoo. Al detectar FAIL en Compras, se dispara automáticamente el pipeline correspondiente como corrección. Agendado a las 3pm (fuera del horario de los procesos diarios).
5. Construido: `scripts/validate_odoo_cutover.py` (tabla `odoo_cutover_validation_log`, UNIQUE por sucursal+dominio+checkpoint), `pipelines/jobs/odoo_cutover_validation_job.py`, y `schedule_daily_at()` agregado a `pipelines/scheduler.py` (no existía soporte para horario fijo, solo intervalos).

**Parte 3 — Bug real #5 (numeración continúa desde el gate): canceladas infladas en el ETL canónico real:**
6. Primera corrida del checkpoint: Tepeyac Compras falló con 14.5% de diferencia, y la "corrección" (re-ejecutar `run_purchases_pipeline`) no lo arregló — corrió, pero el número no cambió sustancialmente.
7. Diagnóstico: `canonical_purchase_order_snapshot`/`_line_snapshot` (la tabla canónica real de producción, no el módulo de diagnóstico del gate) **nunca filtraba `state IN ('cancel','draft')`** — exactamente el Bug #2 de la sesión del gate, corregido entonces solo en `odoo_purchase_category_totals.py` (herramienta de diagnóstico) pero nunca propagado al ETL canónico real (`extract/purchases/canonical_purchase_etl.py`, función `filter_final_odoo_enabled`). Confirmado con conteos: 54 órdenes canceladas de Tepeyac por $693,357.59 explicaban prácticamente toda la diferencia.
8. Corregido: `filter_final_odoo_enabled(df, exclude_cancelled_draft=True)` para Órdenes y Líneas (Recibos y movimientos de recibo también tienen filas `cancel`/`draft`, quedó señalado pero no corregido hoy — no es lo que se estaba midiendo). Recargado vía `test_canonical_purchase_odoo_etl`, validado con `validate_purchases_canonical_layer` (8/8 PASS). Tras el fix, Tepeyac pasó de 14.5% a 1.46% de diferencia, y las 6 sucursales dieron PASS en Compras (checkpoint T+7 y T+30).

**Parte 4 — Incidente: proceso ajeno terminado por error:**
9. Al revisar procesos huérfanos tras detener el checkpoint (que parecía colgado — en realidad estaba corriendo correcciones reales por primera vez, ~1h cada una), se mató un proceso `ejecutar_pruebas.py` sin verificar de quién era. Resultó ser de otro chat del usuario. Reconocido como error inmediatamente; el usuario detuvo esa otra sesión y continuamos.

**Parte 5 — Auditoría de alcance por sucursal (pedido explícito del usuario):**
10. El usuario pidió: revisar que ningún script quedara implementado solo para una sucursal (temor concreto: "toparme en productivo con que el proyecto en algunas partes solo está implementado para Antenas").
11. Encontrado y confirmado real: `scripts/build_dim_company_analytical.py` tenía `MIGRATED_FROM_WANSOFT_COMPANIES = {"Antenas", "La Esquina Coyoacán"}` — nunca actualizado cuando Acoxpa/Tepeyac/Oceanía migraron (2026-08-26/27). Efecto real verificado en la tabla: esas 3 sucursales aparecían con `purchases_source_system='wansoft'` y `rollout_type=NULL`, **como si nunca hubieran migrado a Odoo**. Corregido (agregadas las 3 al set), tabla reconstruida, validado con `validate_dim_company_analytical` (10/10 PASS).
12. Revisado y confirmado limpio: capa de extracción (`extract/purchases/*`, `extract/inventory/*`) y gobernanza de fuente (`core/config/companies.py`) — completamente genéricas, dirigidas por `COMPANY_SOURCE`/`odoo_company_migration_policy`, sin nada hardcodeado a una sucursal. Único script realmente acoplado a una sola sucursal: `scripts/reconcile_purchases_dev_vs_odoo.py` (diagnóstico manual de la sesión del gate, ya superado por `validate_odoo_cutover.py`, bajo riesgo por no ser parte de ningún pipeline).

**Parte 6 — Inventario: gap de automatización y bug real #6:**
13. El checkpoint mostró Inventario en FAIL para las 6 sucursales. Diagnóstico: `analytics_inventory_snapshot`/`analytics_inventory_balance` (Acoxpa) llevaban **11 días desactualizadas** — porque ni `run_inventory_pipeline.py` ni ningún otro mecanismo estaban agendados para correr solos (confirmado: ni Compras ni Inventario tenían nada en el scheduler).
14. Investigado por qué `run_inventory_pipeline.py` nunca reconstruye esas dos tablas: su docstring dice explícitamente que la promoción de diccionario queda fuera del automatismo por requerir revisión humana. Pero se confirmó que `build_analytics_inventory_snapshot.py`/`build_analytics_inventory_balance.py` **no promueven nada** — solo leen el diccionario ya aprobado y recalculan. El pipeline se detenía un paso antes de lo necesario.
15. Decisión del usuario: el checkpoint de Inventario **no debe auto-corregir** (a diferencia de Compras) — solo alertar (`correction_status='manual_review_required'`), dado que el mecanismo de corrección real requiere un rediseño, no solo repetir el pipeline. Implementado en `validate_odoo_cutover.py` (`AUTO_CORRECTABLE_DOMAINS = {"purchases"}`).
16. Agregados los pasos 06-07 (`build_analytics_inventory_snapshot`, `build_analytics_inventory_balance`) a `run_inventory_pipeline.py`, y `pipelines/jobs/inventory_pipeline_job.py` agendado a la 1pm (antes del checkpoint de las 3pm) en el scheduler.
17. Al correr el pipeline extendido por primera vez (8/8 pasos SUCCESS, ~3.2 min), el checkpoint de Inventario **siguió fallando** en las 6 sucursales, ahora con dev consistentemente más alto que Odoo en vivo (2.5x-7x) — ya no era desactualización, era un problema de método.
18. Bug real #6 encontrado: `classify_location()` en `build_analytics_inventory_snapshot.py` ya calculaba `is_virtual_location`/`is_partner_location`, pero `build_row()` nunca los consultaba al decidir `include_in_business_views` — ubicaciones virtuales de Odoo ("Virtual Locations/Inventory adjustment", "Virtual Locations/Production", contrapartidas de doble entrada, no stock físico real) se sumaban como si fueran existencia real. Confirmado en Acoxpa: filas virtuales solas sumaban 1,893.92 contra 596.71 de ubicaciones internas reales.
19. Corregido: excluir `is_virtual_location`/`is_partner_location` de `include_in_business_views`. Reconstruidas ambas tablas. Resultado: **20/20 checkpoints en PASS** (Compras + Inventario, T+7 y T+30, las 6 sucursales), varios con coincidencia exacta (diff=0.0000). `validate_analytics_inventory_balance` confirmó 9/9 PASS, sin regresión.

**Riesgos abiertos (activos, no resueltos):**
- El gate de aceptación final **sigue sin un "sí, aceptado" explícito** del usuario — la evidencia es ahora más fuerte que el 2026-08-27 (3 bugs reales adicionales corregidos, todos reduciendo diferencias, no aumentándolas), pero la decisión formal no se ha tomado.
- `canonical_purchase_receipt_snapshot`/`_receipt_move_snapshot` también tienen filas `cancel` (217) y `cancel` (2,228) sin filtrar — mismo patrón que el Bug #5 pero en Recibos, no confirmado si afecta algo medido hoy. Señalado, no investigado a fondo.
- La promoción de nuevos mapeos de Inventario (backlog `not_found`) sigue siendo 100% manual — es una decisión correcta (no se toca), pero significa que la cobertura de productos mapeados no crece sola.
- Desfase de fecha `created_at = fecha+1` (Wansoft) vs `created_at = fecha` (Odoo) en `costeomensual_semanapyq` — heredado de la sesión del gate, sigue sin unificar.
- Nada de esta sesión ni de la sesión del gate (2026-08-27) estaba comiteado antes de esta regeneración — se resuelve en el mismo paso que genera este documento (ver Sección 8).

**Decisiones relevantes pendientes:**
- Decisión explícita de aceptación del gate (nunca llegó, ni el 28 ni el 31).
- Si vale la pena aplicar el mismo fix de canceladas/borrador a Recibos.
- Si conviene diseñar un mecanismo de auto-corrección real para Inventario (más allá de alertar), o dejarlo como revisión manual permanente.

---

# 2. Descripción Funcional del Proyecto

**Qué estamos construyendo:** un almacén de datos (data warehouse) en MySQL que junta información de Ventas, Compras e Inventario de Grupo Fonda Argentina, sin importar si cada sucursal opera en Wansoft o en Odoo.

**Dirección de migración confirmada por el dueño del proyecto:** el objetivo final es que **solo Ventas** quede permanentemente en Wansoft; Compras, Inventario y Costos migran sucursal por sucursal a Odoo.

---

# 3. Arquitectura Actual

**Sistemas origen:** Wansoft (SOAP/WSDL), Odoo (XML-RPC, solo lectura), Zenput (API REST).

**Gobernanza de fuente (`core/config/companies.py`):** `COMPANY_SOURCE` decide Compras/Inventario por sucursal (autoritativo). `odoo_company_migration_policy` (tabla MySQL, `is_active` + `operational_start_date`) decide si el rollout ya está realmente activado y desde cuándo. Ventas siempre Wansoft, sin excepción.

**Sucursales activas en Odoo hoy (Compras + Inventario):** Antenas, La Esquina Coyoacán, CentroMyJ, Acoxpa, Tepeyac, Oceanía. Puebla: `COMPANY_SOURCE=odoo` pero rollout no activado (`is_active=0`), documentada como trabajo futuro.

**Checkpoint de cutover (nuevo, esta sesión):**
```
odoo_company_migration_policy.operational_start_date  -> fecha de referencia
T+7 / T+30 después de esa fecha                        -> dispara la validación (una sola vez cada una)
Compras: canonical_purchase_order_snapshot (dev) vs purchase.order en vivo (Odoo, state not in cancel/draft)
Inventario: analytics_inventory_balance (dev) vs stock.quant en vivo (Odoo, ubicación interna, solo productos ya mapeados)
FAIL en Compras -> corrige solo (re-ejecuta run_purchases_pipeline)
FAIL en Inventario -> solo alerta (manual_review_required), no corrige solo
```
Script: `scripts/validate_odoo_cutover.py`. Log: tabla `odoo_cutover_validation_log`. Agendado a las 3pm.

**Pipeline de Inventario, ahora con reconstrucción de tablas analíticas (esta sesión):**
```
01-02 scope classification/refinement -> 03 Odoo inventory ETL -> 04-05 dictionary lookup/apply
06 build_analytics_inventory_snapshot (NUEVO) -> 07 build_analytics_inventory_balance (NUEVO) -> 08 validate_inventory_outputs
```
Agendado a la 1pm (antes del checkpoint de cutover). La promoción de mapeos nuevos (`test_promote_inventory_not_found_*`) sigue fuera del pipeline automatizado, a propósito.

**Costos, arquitectura (sin cambios esta sesión, ver commits de la sesión del gate):**
```
account.move.line (Odoo, expense_direct_cost, out_invoice)          -> CostoTotal, CostoDeProductosVendidos
account.move.line (Odoo, expense_direct_cost, cualquier move_type)   -> CostoDeMerma (cuenta "Mermas y Desperdicios")
GetGlobalCashClosing_Xml (Wansoft, todas las sucursales)              -> Cortesias, Cancelaciones, Anulaciones, Descuentos
GetCostReport_Xml (Wansoft, solo sucursales Wansoft-puras)            -> CostoDeCortesías/Cancelaciones ponderados por costo
```

---

# 4. Estado Detallado por Dominio

### Ventas
- Candado (`extractAllOrdersByDay.py`) corregido esta sesión: fuerza re-descarga real antes de corregir, en vez de reusar el XML cacheado que pudo originar el desfase.

### Compras
- `canonical_purchase_order_snapshot`/`_line_snapshot` ya excluyen `cancel`/`draft` (bug real corregido esta sesión, afectaba a las 6 sucursales). Validado 8/8 PASS.
- Checkpoint de cutover con auto-corrección activa. Validado 20/20 PASS (con Inventario incluido) tras los 3 fixes de hoy.
- Recibos/movimientos de recibo: mismo patrón de `cancel` sin filtrar detectado pero no corregido (riesgo abierto).

### Inventario
- `analytics_inventory_snapshot`/`analytics_inventory_balance` ya excluyen ubicaciones virtuales/de socio (bug real corregido esta sesión). Ambas tablas ahora se reconstruyen diariamente vía scheduler (1pm), algo que no existía antes.
- Checkpoint de cutover en modo alerta (no auto-corrige), decisión deliberada del usuario.

### Costos
- Sin cambios esta sesión. Ver sesión del gate (2026-08-27) para el detalle completo.

### Configuración / Gobernanza
- `scripts/build_dim_company_analytical.py`: `MIGRATED_FROM_WANSOFT_COMPANIES` corregido para incluir Acoxpa/Tepeyac/Oceanía (bug real corregido esta sesión). Tabla `dim_company_analytical` reconstruida y validada 10/10 PASS.

*(Resto de dominios sin cambios relevantes esta sesión — ver reporte anterior en el historial de commits si se necesita el detalle de Zenput/Wansoft/Odoo/Analytics.)*

---

# 5. Decisiones Arquitectónicas Tomadas (cronológico, esta sesión)

| Decisión | Justificación | Impacto |
|---|---|---|
| Candado de Ventas fuerza re-descarga al corregir, no reusa XML cacheado | El archivo cacheado podía ser la fuente del desfase que se intentaba corregir | `extractAllOrdersByDay.py` |
| Checkpoint T+7/T+30, una sola vez por combinación (sucursal, dominio, checkpoint) | Evita re-chequeo diario innecesario; da tiempo a que Odoo asiente (mismo patrón de rezago confirmado en el gate para Costos) | `validate_odoo_cutover.py`, tabla `odoo_cutover_validation_log` |
| Compras: FAIL dispara auto-corrección (re-ejecutar `run_purchases_pipeline`) | Pipeline idempotente, ya validado, seguro de re-correr | Mismo módulo |
| Inventario: FAIL solo alerta, NO auto-corrige | El mecanismo de corrección real requiere reconstruir tablas analíticas que el pipeline no tocaba — corregirlo a medias hubiera ocultado el problema real | Mismo módulo, `AUTO_CORRECTABLE_DOMAINS` |
| `filter_final_odoo_enabled` excluye `state IN ('cancel','draft')` para Órdenes/Líneas de Compras | Mismo bug del gate (canceladas infladas), nunca propagado al ETL canónico real | `extract/purchases/canonical_purchase_etl.py` |
| `MIGRATED_FROM_WANSOFT_COMPANIES` incluye Acoxpa/Tepeyac/Oceanía | Nunca se actualizó tras su migración (26-27 ago); la tabla las mostraba como 100% Wansoft | `scripts/build_dim_company_analytical.py` |
| `build_row()` excluye ubicaciones `is_virtual_location`/`is_partner_location` de `include_in_business_views` | Ya se calculaban esos flags pero nunca se usaban; ubicaciones virtuales (ajustes, producción) se contaban como stock físico real | `scripts/build_analytics_inventory_snapshot.py` |
| `run_inventory_pipeline.py` gana los pasos 06-07 (build snapshot/balance) | No promueven diccionario (verificado); el pipeline se detenía un paso antes de lo necesario sin razón real | Mismo módulo |
| Pipeline de Inventario agendado a la 1pm, checkpoint de cutover a las 3pm | Ninguno de los dos pipelines (Compras/Inventario) tenía nada agendado — causa raíz de la desactualización de 11 días encontrada hoy | `pipelines/scheduler.py`, `schedule_daily_at()` (nuevo) |

---

# 6. Reglas de Negocio Implementadas (nuevas esta sesión)

- **Checkpoint de cutover:** por sucursal recién migrada, T+7 y T+30 días después de `operational_start_date`, comparación única contra Odoo en vivo. Compras se autocorrige, Inventario solo alerta.
- **Compras finales (Odoo):** excluir siempre `state IN ('cancel','draft')`, tanto en diagnóstico como en el ETL canónico real.
- **Inventario final (Odoo):** excluir siempre ubicaciones virtuales/de socio (`is_virtual_location`/`is_partner_location`) — solo cuenta stock en ubicaciones internas reales.
- **Automatización vs revisión manual (Inventario):** reconstruir `analytics_inventory_snapshot`/`analytics_inventory_balance` con el diccionario ya aprobado es seguro de automatizar (no promueve nada); promover mapeos nuevos sigue siendo manual, sin excepción.

---

# 7-8. Convenciones Técnicas / Estado Git

**Nuevo aprendizaje de esta sesión:**
- Los scripts de pipeline (`run_purchases_pipeline.py`, `run_inventory_pipeline.py`, y sus pasos individuales) imprimen emojis al terminar (`DONE ✅`). Al invocarlos como subproceso con salida capturada, sin forzar `PYTHONIOENCODING=utf-8`, revientan con `UnicodeEncodeError` en Windows (cp1252) **después** de que el trabajo real ya terminó — el paso se reporta como FAILED aunque haya funcionado. Cualquier subproceso nuevo que invoque estos scripts debe pasar `env={"PYTHONIOENCODING": "utf-8", **os.environ}`.
- Un bug "corregido" en un script de diagnóstico/gate no está corregido en producción hasta que se verifica en el ETL canónico real — pasó dos veces esta sesión (canceladas en Compras, ubicaciones virtuales en Inventario) con bugs que ya se creían resueltos desde el gate.
- Antes de matar un proceso que parece huérfano, verificar de qué comando/archivo es — no asumir que es propio solo por coincidir en tiempo.

**Estado Git:** rama `main`, último push `21078c8` (2026-08-27, antes de la sesión del gate). Ni la sesión del gate (2026-08-27) ni esta sesión (2026-08-31) estaban comiteadas — se resuelve en este mismo paso. Archivos incluidos en el commit de hoy:

*De la sesión del gate (2026-08-27):*
- `extract/costs/odoo_cost_report.py` — fix Merma + auditoría de cuentas.
- `extract/purchases/odoo_purchase_category_totals.py` — nuevo (diagnóstico de Compras por cuenta).
- `legacy/wansoft/automaticos/getCostReport_SemanaPyQ.py` — comentario aclaratorio.
- `legacy/wansoft/descargarCostoWansoft/getGlobalCashClosing.py` — reactivado.
- `legacy/wansoft/descargarCostoWansoft/descargarCostoWansoft.py` — reactivado + bloque Odoo.

*De esta sesión (2026-08-31):*
- `legacy/wansoft/automaticos/extractAllOrdersByDay.py` — fix candado (re-descarga forzada al corregir).
- `scripts/validate_odoo_cutover.py` — nuevo, checkpoint T+7/T+30.
- `pipelines/jobs/odoo_cutover_validation_job.py` — nuevo.
- `pipelines/jobs/inventory_pipeline_job.py` — nuevo.
- `pipelines/scheduler.py` — `schedule_daily_at()` + dos jobs nuevos agendados.
- `extract/purchases/canonical_purchase_etl.py` — fix canceladas/borrador.
- `scripts/build_dim_company_analytical.py` — fix sucursales migradas faltantes.
- `scripts/build_analytics_inventory_snapshot.py` — fix ubicaciones virtuales.
- `scripts/run_inventory_pipeline.py` — pasos 06-07 (build snapshot/balance) agregados.

*Nunca se comitea (convención del proyecto):*
- `inventory_not_found_analysis.csv`.

---

# 9. Contexto Histórico Importante — Resumen del Gate (para no re-investigar)

Ver reporte anterior (commit `21078c8` o antes) para la narrativa completa de la sesión del gate (2026-08-27, bugs #1-#4). Tabla resumen combinada, incluidos los bugs #5-#6 de esta sesión:

| # | Bug | Dónde vivía realmente | Corregido en |
|---|---|---|---|
| 1 | Merma en Odoo siempre $0 | Filtro `out_invoice` de más en Costos | `extract/costs/odoo_cost_report.py` (2026-08-27) |
| 2 | Canceladas infladas en diagnóstico de Compras | `odoo_purchase_category_totals.py` (diagnóstico) | Mismo módulo (2026-08-27) |
| 3 | Confusión Cortesías/Cancelaciones "de venta" vs ponderadas | Columna equivocada en `costeomensual_semanapyq` | Revertido, usada `getglobalcashclosing.py` (2026-08-27) |
| 4 | Desfase de fecha `created_at+1` Wansoft vs Odoo | `getCostReport_SemanaPyQ.py` | Documentado, no corregido (riesgo abierto) |
| 5 | Canceladas infladas en el ETL canónico **real** de Compras | `canonical_purchase_etl.py` (nunca se propagó el fix del #2) | `extract/purchases/canonical_purchase_etl.py` (2026-08-31) |
| 6 | Ubicaciones virtuales de Odoo contadas como stock real | `build_analytics_inventory_snapshot.py` | Mismo módulo (2026-08-31) |

**Resultado del gate tras los fixes de hoy:** Compras y Inventario, comparados de forma independiente contra Odoo en vivo, dan **20/20 PASS** para las 6 sucursales activas (T+7 y T+30), varios con coincidencia exacta. La evidencia es hoy más fuerte y más limpia que el 27 de agosto — pero la decisión formal de "gate aceptado" sigue sin ocurrir explícitamente.

**No reabrir sin razón nueva:** el rezago de reconocimiento de Costo Total en semanas frescas (gate original, bugs #1-#4) sigue siendo el mismo hallazgo confirmado con 4 semanas de datos reales — no se tocó ni se volvió a investigar esta sesión.

---

# 10. Decisiones del Usuario (explícitas, no perder)

- (Todas las de sesiones anteriores siguen vigentes, ver commits previos.)
- **Nuevo:** el candado de Ventas debe forzar re-descarga real al corregir, no confiar en el XML cacheado.
- **Nuevo:** el cutover de sucursales mixtas (Wansoft+Odoo) se valida con un checkpoint automático T+7/T+30, no con la palabra de las sucursales sobre cuándo cerraron.
- **Nuevo:** Compras se auto-corrige en el checkpoint; Inventario solo alerta (decisión explícita tras entender que el mecanismo de corrección real no estaba listo).
- **Nuevo:** construir la automatización de Inventario faltante ("vamos para allá").
- **Nuevo:** comitear y pushear todo el trabajo acumulado.

---

# 11-12. Legacy Identificado / Backlog Consolidado

**Backlog:**
- Decisión explícita de aceptación del gate (sigue pendiente).
- Evaluar si aplicar el fix de canceladas/borrador también a `canonical_purchase_receipt_snapshot`/`_receipt_move_snapshot`.
- Evaluar un mecanismo de auto-corrección real para Inventario (más allá de alertar), si el volumen de FAILs lo justifica con el tiempo.
- Evaluar si unificar el desfase de fecha `created_at` en `costeomensual_semanapyq` (heredado del gate).
- Ítems de sesiones anteriores sin resolver: encadenar scripts legacy en `pipelines/scheduler.py` (diferido).

---

# 13. Próximos Pasos

No se necesita traspaso a chat nuevo en este momento (el commit/push cierra la sesión de forma natural, no por límite de contexto). Si se abre un chat nuevo más adelante para continuar, usar como punto de partida la Sección 1 (narrativa completa) y la Sección 9 (tabla resumen del gate) de este documento.

**Título sugerido para el próximo chat**, cuando aplique (formato `FONDA (proyecto corto): Paso N[-M]: <descripción corta>`): `FONDA (Wansoft): Paso 19: Decisión formal del gate y siguientes pasos`

---

# Regla Permanente

Regenerar este documento completo (nunca parches) cuando: el usuario lo pida explícitamente, se cierre un paso mayor, la conversación se vuelva muy extensa, el contexto supere ~70%, o se necesite abrir un chat nuevo por límite de tokens. En este último caso, generar además:
1. El prompt de traspaso (Sección 13, primer bloque de código si aplica).
2. El título sugerido para el chat nuevo, en el formato **`FONDA (proyecto corto): Paso N[-M]: <descripción corta>`** (mismo estilo que el listado de sesiones del usuario, ej. "FONDA (Wansoft): Paso 18-1: Extracción de Costos de Venta de Odoo"). `FONDA` es prefijo fijo (la empresa, en todos los proyectos del usuario); `(proyecto corto)` identifica cuál proyecto es (aquí: "Wansoft", tomado del propio proyecto compartido, no se pregunta). Usar `N` = número del paso/bloque de trabajo mayor en curso, `-M` = sub-parte si el paso se divide en varias sesiones/chats consecutivos.
