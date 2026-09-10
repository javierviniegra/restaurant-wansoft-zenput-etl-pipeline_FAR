-- ============================================================
-- Verificación manual: La Esquina Coyoacán
-- Wansoft crudo (donde todo se sigue registrando, incluso en
-- productivo, después de la migración) vs la capa canónica en
-- dev (donde Compras/Inventario ya leen de Odoo desde el corte).
-- ============================================================
--
-- Coyoacán = odoo_company_id / Wansoft account id 12057
-- Fecha de corte (operational_start_date): 2026-06-01
--   (fuente: odoo_company_migration_policy, company_name =
--    'FONDA ARGENTINA COYOACAN')
--
-- OJO — hallazgo importante: en getinputinventory_entrada y
-- getoutgoinginventory_salida, la columna `subsidiary_name` en
-- realidad NO guarda el nombre de la sucursal, guarda el ID
-- numérico de Wansoft como texto (ej. '12057'). Es un bug de
-- nombre de columna en el script legacy original, no algo que
-- cambiamos nosotros. Por eso las queries de abajo filtran por
-- subsidiary_name = '12057', no por el nombre.
--
-- Solo lectura, no escribe nada.
-- ============================================================


-- ============================================================
-- 1) PRODUCTIVO -- conéctate a la base "wansoft" de PRODUCTIVO
-- ============================================================
-- Total de compras (Cantidad x CostoUnitario) por mes, desde el
-- dato crudo de Wansoft. Esto sigue teniendo datos después del
-- corte (2026-06-01) porque en productivo Coyoacán sigue
-- registrando algo en Wansoft en la vida real.

SELECT
    DATE_FORMAT(FechaEntrada, '%Y-%m') AS mes,
    COUNT(*)                            AS num_registros,
    SUM(Cantidad * CostoUnitario)       AS total_compras_wansoft
FROM getinputinventory_entrada
WHERE subsidiary_name = '12057'
GROUP BY mes
ORDER BY mes;


-- ============================================================
-- 2) DEV -- conéctate a la base "wansoft" de DEV
-- ============================================================
-- Mismo query, en dev. Debería verse el corte limpio: datos
-- hasta ~junio 2026 y ya no después (porque el scheduler diario
-- en dev solo trae los últimos ~31 días, y Coyoacán ya no genera
-- entradas nuevas en Wansoft desde que migró).

SELECT
    DATE_FORMAT(FechaEntrada, '%Y-%m') AS mes,
    COUNT(*)                            AS num_registros,
    SUM(Cantidad * CostoUnitario)       AS total_compras_wansoft
FROM getinputinventory_entrada
WHERE subsidiary_name = '12057'
GROUP BY mes
ORDER BY mes;


-- ============================================================
-- 3) DEV -- capa canónica (esta es la comparación real)
-- ============================================================
-- canonical_purchase_order_snapshot ya combina ambas fuentes
-- para Coyoacán: filas source_system='wansoft' (histórico, antes
-- del corte) y source_system='odoo' (desde el corte en adelante).
-- Esto es lo que el proyecto realmente usa como "la verdad" para
-- Compras. Compara estos totales mensuales por source_system
-- contra el total de PRODUCTIVO del paso 1 para los mismos meses:
-- si el corte funcionó bien, los meses 'odoo' de aquí deberían
-- ser del mismo orden de magnitud que lo que productivo sigue
-- viendo en Wansoft para esos mismos meses.

SELECT
    DATE_FORMAT(order_date, '%Y-%m') AS mes,
    source_system,
    COUNT(*)                          AS num_ordenes,
    SUM(amount_total)                 AS total_compras
FROM canonical_purchase_order_snapshot
WHERE company_source_key = 'La Esquina Coyoacán'
  AND state NOT IN ('cancel', 'draft')
GROUP BY mes, source_system
ORDER BY mes, source_system;


-- ============================================================
-- 4) Inventario -- contraparte de salidas / balance
-- ============================================================
-- 4a) PRODUCTIVO: salidas de Wansoft por mes (tabla grande, el
--     COUNT(*) puede tardar; si tarda mucho usa el conteo
--     aproximado al final de este archivo).
SELECT
    DATE_FORMAT(Fecha, '%Y-%m') AS mes,
    COUNT(*)                     AS num_salidas
FROM getoutgoinginventory_salida
WHERE subsidiary_name = '12057'
GROUP BY mes
ORDER BY mes;

-- 4b) DEV: balance actual de inventario para Coyoacán, ya
--     calculado desde Odoo (analytics_inventory_balance no es
--     serie de tiempo, es un balance vivo por producto -- no hay
--     un equivalente mensual directo, solo el estado actual).
SELECT
    wansoft_code,
    product_name,
    entrada_qty,
    salida_qty,
    current_balance_qty,
    include_in_business_views
FROM analytics_inventory_balance
WHERE company_source_key = 'La Esquina Coyoacán'
ORDER BY product_name;


-- ============================================================
-- Conteo aproximado (rápido, no exacto) por si algún COUNT(*)
-- de arriba tarda demasiado en una tabla grande:
-- ============================================================
SELECT table_name, table_rows AS conteo_aproximado
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_name IN ('getinputinventory_entrada', 'getoutgoinginventory_salida');
