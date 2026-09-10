-- ============================================================
-- Verificación de las tablas ANALÍTICAS/CANÓNICAS (capa unificada
-- para Power BI): canonical_purchase_order_snapshot,
-- analytics_purchase_orders, analytics_purchase_order_lines,
-- analytics_purchase_daily_company_product, analytics_inventory_balance
-- ============================================================
-- A diferencia de verify_dev_vs_prod.sql y verify_daily_download_by_branch.sql,
-- este script NO se corre "dos veces" (dev y prod) -- estas tablas
-- todavía no existen en productivo (son la capa nueva construida
-- solo en dev sobre canonical_purchase_order_snapshot). Corre este
-- script UNA VEZ, conectado a DEV, base de datos "wansoft".
--
-- Qué valida:
--   0) Frescura -- ¿de verdad se reconstruyeron hoy?
--   1) Cobertura -- ¿las 19 sucursales están presentes?
--   2) Reconciliación -- canonical_purchase_order_snapshot vs
--      analytics_purchase_orders (deben coincidir, la analítica
--      se construye directo desde la canónica)
--   3) El hallazgo sin resolver: Acoxpa/Antenas/Tepeyac capturan
--      solo ~54-62% de lo que Wansoft residual sigue mostrando, y
--      Oceanía/Coyoacán muestran $0 en Odoo en los últimos 10 días
--   4) Inventario -- analytics_inventory_balance, cobertura y filtro
--      include_in_business_views
--
-- Solo lectura, no escribe nada.
-- ============================================================


-- ============================================================
-- 0) FRESCURA -- ¿cuándo se reconstruyó cada tabla por última vez?
--    Si updated_at/canonical_loaded_at no es de HOY, todo lo demás
--    de este script está leyendo datos viejos -- vuelve a correr
--    el ciclo diario antes de confiar en los resultados de abajo.
-- ============================================================
SELECT 'canonical_purchase_order_snapshot' AS tabla,
       COUNT(*) AS total_filas,
       MAX(order_date) AS fecha_dato_mas_reciente
FROM canonical_purchase_order_snapshot

UNION ALL

SELECT 'analytics_purchase_order_lines',
       COUNT(*),
       MAX(updated_at)
FROM analytics_purchase_order_lines

UNION ALL

SELECT 'analytics_purchase_orders',
       COUNT(*),
       MAX(updated_at)
FROM analytics_purchase_orders

UNION ALL

SELECT 'analytics_purchase_daily_company_product',
       COUNT(*),
       MAX(updated_at)
FROM analytics_purchase_daily_company_product

UNION ALL

SELECT 'analytics_inventory_balance',
       COUNT(*),
       MAX(updated_at)
FROM analytics_inventory_balance;


-- ============================================================
-- 1) COBERTURA -- ¿las 19 sucursales aparecen en analytics_purchase_orders?
--    Si falta alguna, esa sucursal no llegará a Power BI cuando se
--    repunte la fuente. Compara contra la lista de 19 sucursales de
--    verify_daily_download_by_branch.sql.
-- ============================================================
SELECT
    company_source_key AS sucursal,
    source_system,
    COUNT(*) AS num_ordenes,
    SUM(CASE WHEN include_in_business_views = 1 THEN 1 ELSE 0 END) AS incluidas_en_business_views,
    SUM(price_total_total) AS total_compras,
    MIN(order_date) AS fecha_min,
    MAX(order_date) AS fecha_max
FROM analytics_purchase_orders
GROUP BY sucursal, source_system
ORDER BY sucursal, source_system;

-- Conteo de sucursales distintas -- debe salir 19 (o menos si
-- alguna todavía no tiene ninguna orden en canonical, revisa contra
-- el bloque 1 completo para ver cuál falta)
SELECT COUNT(DISTINCT company_source_key) AS sucursales_distintas
FROM analytics_purchase_orders;


-- ============================================================
-- 2) RECONCILIACIÓN -- canonical_purchase_order_snapshot vs
--    analytics_purchase_orders. Deben coincidir en conteo y monto
--    (misma fuente, la analítica es un rebuild directo de la
--    canónica) -- si NO coinciden, el rebuild de las 13:50
--    (analytics_purchase_pipeline_job) no corrió después del
--    refresco canónico de las 13:30, o falló a medias.
-- ============================================================
SELECT
    c.sucursal,
    c.num_ordenes_canonical,
    a.num_ordenes_analytics,
    c.num_ordenes_canonical - a.num_ordenes_analytics AS diferencia_conteo,
    c.total_canonical,
    a.total_analytics,
    ROUND(c.total_canonical - a.total_analytics, 2) AS diferencia_monto
FROM (
    SELECT company_source_key AS sucursal,
           COUNT(*) AS num_ordenes_canonical,
           SUM(amount_total) AS total_canonical
    FROM canonical_purchase_order_snapshot
    WHERE state NOT IN ('cancel', 'draft')
    GROUP BY company_source_key
) c
LEFT JOIN (
    SELECT company_source_key AS sucursal,
           COUNT(*) AS num_ordenes_analytics,
           SUM(price_total_total) AS total_analytics
    FROM analytics_purchase_orders
    GROUP BY company_source_key
) a ON a.sucursal = c.sucursal
ORDER BY ABS(COALESCE(c.total_canonical,0) - COALESCE(a.total_analytics,0)) DESC;


-- ============================================================
-- 3) EL HALLAZGO SIN RESOLVER -- comparación día a día, Odoo
--    (canonical/analytics) vs Wansoft residual (tabla cruda), para
--    las 5 sucursales con el problema: Acoxpa/Antenas/Tepeyac
--    (~54-62% de cobertura) y Oceanía/La Esquina Coyoacán ($0 en
--    Odoo). Si el patrón es "faltan días completos" en vez de
--    "todos los días están un poco bajos", probablemente sea un
--    problema de sincronización/estado (state filter), no de
--    cobertura real de compras.
-- ============================================================
SELECT
    DATE(fecha) AS dia,
    sucursal,
    fuente,
    SUM(monto) AS total_dia,
    SUM(num_registros) AS num_ordenes_dia
FROM (
    SELECT order_date AS fecha,
           company_source_key AS sucursal,
           'odoo (canonical)' AS fuente,
           amount_total AS monto,
           1 AS num_registros
    FROM canonical_purchase_order_snapshot
    WHERE source_system = 'odoo'
      AND state NOT IN ('cancel', 'draft')
      AND order_date >= DATE_SUB(CURDATE(), INTERVAL 10 DAY)
      AND company_source_key IN ('Acoxpa', 'Antenas', 'Tepeyac', 'Oceanía', 'La Esquina Coyoacán')

    UNION ALL

    SELECT FechaEntrada AS fecha,
           CASE subsidiary_name
               WHEN '5320'  THEN 'Acoxpa'
               WHEN '4960'  THEN 'Antenas'
               WHEN '6560'  THEN 'Tepeyac'
               WHEN '5943'  THEN 'Oceanía'
               WHEN '12057' THEN 'La Esquina Coyoacán'
           END AS sucursal,
           'wansoft (residual)' AS fuente,
           Cantidad * CostoUnitario AS monto,
           1 AS num_registros
    FROM getinputinventory_entrada
    WHERE subsidiary_name IN ('5320', '4960', '6560', '5943', '12057')
      AND FechaEntrada >= DATE_SUB(CURDATE(), INTERVAL 10 DAY)
) combined
GROUP BY dia, sucursal, fuente
ORDER BY sucursal, dia, fuente;

-- Mismo hallazgo, resumido a un solo número por sucursal (más
-- fácil de leer que el detalle diario de arriba):
SELECT
    sucursal,
    SUM(CASE WHEN fuente = 'odoo (canonical)' THEN monto ELSE 0 END) AS total_odoo_10d,
    SUM(CASE WHEN fuente = 'wansoft (residual)' THEN monto ELSE 0 END) AS total_wansoft_residual_10d,
    ROUND(
        100 * SUM(CASE WHEN fuente = 'odoo (canonical)' THEN monto ELSE 0 END)
        / NULLIF(SUM(CASE WHEN fuente = 'wansoft (residual)' THEN monto ELSE 0 END), 0),
        1
    ) AS pct_cobertura_odoo_vs_wansoft
FROM (
    SELECT company_source_key AS sucursal, 'odoo (canonical)' AS fuente, amount_total AS monto
    FROM canonical_purchase_order_snapshot
    WHERE source_system = 'odoo'
      AND state NOT IN ('cancel', 'draft')
      AND order_date >= DATE_SUB(CURDATE(), INTERVAL 10 DAY)
      AND company_source_key IN ('Acoxpa', 'Antenas', 'Tepeyac', 'Oceanía', 'La Esquina Coyoacán')

    UNION ALL

    SELECT
        CASE subsidiary_name
            WHEN '5320'  THEN 'Acoxpa'
            WHEN '4960'  THEN 'Antenas'
            WHEN '6560'  THEN 'Tepeyac'
            WHEN '5943'  THEN 'Oceanía'
            WHEN '12057' THEN 'La Esquina Coyoacán'
        END,
        'wansoft (residual)',
        Cantidad * CostoUnitario
    FROM getinputinventory_entrada
    WHERE subsidiary_name IN ('5320', '4960', '6560', '5943', '12057')
      AND FechaEntrada >= DATE_SUB(CURDATE(), INTERVAL 10 DAY)
) x
GROUP BY sucursal
ORDER BY pct_cobertura_odoo_vs_wansoft;

-- Odoo purchase order STATE breakdown for these 5 branches -- if a
-- large chunk sits in 'draft' or 'cancel' (excluded by the filter
-- above), that alone could explain the gap without any missing sync.
SELECT
    company_source_key AS sucursal,
    state,
    COUNT(*) AS num_ordenes,
    SUM(amount_total) AS total_monto
FROM canonical_purchase_order_snapshot
WHERE source_system = 'odoo'
  AND order_date >= DATE_SUB(CURDATE(), INTERVAL 10 DAY)
  AND company_source_key IN ('Acoxpa', 'Antenas', 'Tepeyac', 'Oceanía', 'La Esquina Coyoacán')
GROUP BY sucursal, state
ORDER BY sucursal, state;


-- ============================================================
-- 4) INVENTARIO -- analytics_inventory_balance: cobertura de las
--    19 sucursales y qué tanto queda excluido por
--    include_in_business_views.
-- ============================================================
SELECT
    company_source_key AS sucursal,
    source_system,
    COUNT(*) AS num_productos,
    SUM(CASE WHEN include_in_business_views = 1 THEN 1 ELSE 0 END) AS incluidos,
    SUM(CASE WHEN include_in_business_views = 0 THEN 1 ELSE 0 END) AS excluidos,
    SUM(entrada_qty) AS total_entrada_qty,
    SUM(salida_qty) AS total_salida_qty,
    SUM(current_balance_qty) AS total_balance_qty
FROM analytics_inventory_balance
GROUP BY sucursal, source_system
ORDER BY sucursal, source_system;

SELECT COUNT(DISTINCT company_source_key) AS sucursales_distintas
FROM analytics_inventory_balance;

-- Balances negativos -- señal de datos sucios (ver memoria
-- project_inventory_balance_negative_outlier_subsidiaries, no
-- volver a investigar sin razón nueva, solo para monitoreo pasivo)
SELECT company_source_key AS sucursal, COUNT(*) AS num_productos_balance_negativo
FROM analytics_inventory_balance
WHERE current_balance_qty < 0
GROUP BY sucursal
ORDER BY num_productos_balance_negativo DESC;
