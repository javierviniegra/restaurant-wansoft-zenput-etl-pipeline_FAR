-- ============================================================
-- Verificación diaria por sucursal: dev vs productivo
-- ============================================================
-- Uso: corre cada bloque DOS VECES -- una conectado a la base de
-- datos DEV y otra a PRODUCTIVO (mismo nombre de base "wansoft",
-- host distinto: WANSOFT_DB_HOST vs WANSOFT_DB_HOST_DEV en
-- core/config/.env). Compara los resultados lado a lado, por
-- sucursal.
--
-- Reutiliza este mismo archivo cada día -- no hace falta
-- regenerarlo, los resultados cambian solos con los datos.
--
-- Solo lectura, no escribe nada.
-- ============================================================
--
-- REFERENCIA -- clasificación actual de fuente por sucursal
-- (core/config/companies.py, COMPANY_SOURCE). Esto SOLO aplica a
-- los dominios de Compras e Inventario -- Ventas siempre es
-- Wansoft, sin excepción, para las 19 sucursales.
--
--   id      sucursal                fuente Compras/Inventario
--   -----   ----------------------  --------------------------
--   5320    Acoxpa                  odoo
--   4960    Antenas                 odoo
--   6560    Tepeyac                 odoo
--   5943    Oceanía                 odoo
--   12057   La Esquina Coyoacán     odoo
--   12802   CentroMyJ               odoo
--   12806   Puebla                  odoo
--   4959    Aeropuerto              wansoft
--   4958    Isabel La Católica      wansoft
--   5321    Taquería parroquia      wansoft
--   5318    Vía Vallejo             wansoft
--   4961    Viaducto                wansoft
--   4962    Taquería Viaducto       wansoft
--   5319    San Jeronimo            wansoft
--   6174    Playa del Carmen        wansoft
--   6175    Cancun                  wansoft
--   4433    Napoles                 wansoft
--   4752    Metepec                 wansoft
--   5396    Versalles               wansoft
--
-- NOTA -- bug real de columna en el código legacy: en
-- getinputinventory_entrada y getoutgoinginventory_salida, la
-- columna `subsidiary_name` en realidad guarda el ID numérico de
-- Wansoft (texto), NO el nombre. Todas las demás tablas de aquí
-- sí guardan el nombre real. Las queries de abajo ya lo manejan
-- con un CASE, así que no hace falta que lo recuerdes cada vez.
--
-- NOTA -- el servidor MySQL guarda los nombres de tabla en
-- minúsculas (lower_case_table_names), aunque el código Python
-- los escriba con mayúsculas. Todas las tablas de este archivo
-- ya están en minúsculas tal cual las guarda el servidor -- si
-- alguna vez ves "#1109 - Tabla desconocida", es justo por esto.
-- ============================================================


-- ============================================================
-- 1) VENTAS -- siempre Wansoft, las 19 sucursales
--    (getallordenesbyday_new_venta.Sucursal SÍ guarda el nombre)
-- ============================================================
SELECT
    Sucursal AS sucursal,
    COUNT(*)                                                AS num_ventas,
    SUM(CAST(Total AS DECIMAL(14,2)))                       AS total_ventas,
    MIN(CAST(Fecha AS DATE))                                AS fecha_min,
    MAX(CAST(Fecha AS DATE))                                AS fecha_max
FROM getallordenesbyday_new_venta
WHERE CAST(Fecha AS DATE) >= DATE_SUB(CURDATE(), INTERVAL 10 DAY)
GROUP BY Sucursal
ORDER BY sucursal;


-- ============================================================
-- 2) COMPRAS (proxy) -- getinputinventory_entrada
--    Para sucursales "wansoft": esto ES la fuente oficial.
--    Para sucursales "odoo": esto es lo que Wansoft SIGUE viendo
--    después del corte (compárese contra el bloque 6, que es la
--    fuente oficial real para esas sucursales en dev).
-- ============================================================
SELECT
    CASE subsidiary_name
        WHEN '5320'  THEN 'Acoxpa'
        WHEN '4959'  THEN 'Aeropuerto'
        WHEN '4958'  THEN 'Isabel La Católica'
        WHEN '4960'  THEN 'Antenas'
        WHEN '5321'  THEN 'Taquería parroquia'
        WHEN '5318'  THEN 'Vía Vallejo'
        WHEN '4961'  THEN 'Viaducto'
        WHEN '4962'  THEN 'Taquería Viaducto'
        WHEN '5319'  THEN 'San Jeronimo'
        WHEN '6560'  THEN 'Tepeyac'
        WHEN '6174'  THEN 'Playa del Carmen'
        WHEN '5943'  THEN 'Oceanía'
        WHEN '6175'  THEN 'Cancun'
        WHEN '4433'  THEN 'Napoles'
        WHEN '4752'  THEN 'Metepec'
        WHEN '5396'  THEN 'Versalles'
        WHEN '12057' THEN 'La Esquina Coyoacán'
        WHEN '12802' THEN 'CentroMyJ'
        WHEN '12806' THEN 'Puebla'
        ELSE CONCAT('id_desconocido_', subsidiary_name)
    END AS sucursal,
    CASE subsidiary_name
        WHEN '5320' THEN 'odoo' WHEN '4960' THEN 'odoo' WHEN '6560' THEN 'odoo'
        WHEN '5943' THEN 'odoo' WHEN '12057' THEN 'odoo' WHEN '12802' THEN 'odoo'
        WHEN '12806' THEN 'odoo'
        ELSE 'wansoft'
    END AS fuente_oficial_compras,
    COUNT(*)                            AS num_registros,
    SUM(Cantidad * CostoUnitario)       AS total_compras_wansoft,
    MAX(FechaEntrada)                   AS fecha_max
FROM getinputinventory_entrada
WHERE FechaEntrada >= DATE_SUB(CURDATE(), INTERVAL 10 DAY)
GROUP BY subsidiary_name
ORDER BY sucursal;


-- ============================================================
-- 2b) COMPRAS -- vista combinada, las 19 sucursales en un solo
--     resultado: las 12 "wansoft" desde el dato crudo de Wansoft,
--     las 7 "odoo" desde la capa canónica (fuente oficial real).
--     SOLO DEV -- canonical_purchase_order_snapshot no existe en
--     productivo todavía.
-- ============================================================
SELECT sucursal, fuente, num_registros, total_compras, fecha_max
FROM (
    SELECT
        CASE subsidiary_name
            WHEN '4959'  THEN 'Aeropuerto'
            WHEN '4958'  THEN 'Isabel La Católica'
            WHEN '5321'  THEN 'Taquería parroquia'
            WHEN '5318'  THEN 'Vía Vallejo'
            WHEN '4961'  THEN 'Viaducto'
            WHEN '4962'  THEN 'Taquería Viaducto'
            WHEN '5319'  THEN 'San Jeronimo'
            WHEN '6174'  THEN 'Playa del Carmen'
            WHEN '6175'  THEN 'Cancun'
            WHEN '4433'  THEN 'Napoles'
            WHEN '4752'  THEN 'Metepec'
            WHEN '5396'  THEN 'Versalles'
            ELSE CONCAT('id_desconocido_', subsidiary_name)
        END AS sucursal,
        'wansoft' AS fuente,
        COUNT(*)                            AS num_registros,
        SUM(Cantidad * CostoUnitario)       AS total_compras,
        MAX(FechaEntrada)                   AS fecha_max
    FROM getinputinventory_entrada
    WHERE FechaEntrada >= DATE_SUB(CURDATE(), INTERVAL 10 DAY)
    GROUP BY subsidiary_name

    UNION ALL

    SELECT
        company_source_key AS sucursal,
        'odoo' AS fuente,
        COUNT(*)             AS num_registros,
        SUM(amount_total)    AS total_compras,
        MAX(order_date)      AS fecha_max
    FROM canonical_purchase_order_snapshot
    WHERE source_system = 'odoo'
      AND state NOT IN ('cancel', 'draft')
      AND order_date >= DATE_SUB(CURDATE(), INTERVAL 10 DAY)
      AND company_source_key IN (
          'Acoxpa', 'Antenas', 'Tepeyac', 'Oceanía',
          'La Esquina Coyoacán', 'CentroMyJ', 'Puebla'
      )
    GROUP BY company_source_key
) combined
ORDER BY sucursal;


-- ============================================================
-- 3) INVENTARIO (proxy, salidas) -- getoutgoinginventory_salida
--    Misma lógica que el bloque 2: fuente oficial solo para las
--    sucursales "wansoft"; para "odoo" es la señal residual.
--    Tabla grande -- si el WHERE por fecha tarda, usa el conteo
--    aproximado al final del archivo.
-- ============================================================
SELECT
    CASE subsidiary_name
        WHEN '5320'  THEN 'Acoxpa'
        WHEN '4959'  THEN 'Aeropuerto'
        WHEN '4958'  THEN 'Isabel La Católica'
        WHEN '4960'  THEN 'Antenas'
        WHEN '5321'  THEN 'Taquería parroquia'
        WHEN '5318'  THEN 'Vía Vallejo'
        WHEN '4961'  THEN 'Viaducto'
        WHEN '4962'  THEN 'Taquería Viaducto'
        WHEN '5319'  THEN 'San Jeronimo'
        WHEN '6560'  THEN 'Tepeyac'
        WHEN '6174'  THEN 'Playa del Carmen'
        WHEN '5943'  THEN 'Oceanía'
        WHEN '6175'  THEN 'Cancun'
        WHEN '4433'  THEN 'Napoles'
        WHEN '4752'  THEN 'Metepec'
        WHEN '5396'  THEN 'Versalles'
        WHEN '12057' THEN 'La Esquina Coyoacán'
        WHEN '12802' THEN 'CentroMyJ'
        WHEN '12806' THEN 'Puebla'
        ELSE CONCAT('id_desconocido_', subsidiary_name)
    END AS sucursal,
    CASE subsidiary_name
        WHEN '5320' THEN 'odoo' WHEN '4960' THEN 'odoo' WHEN '6560' THEN 'odoo'
        WHEN '5943' THEN 'odoo' WHEN '12057' THEN 'odoo' WHEN '12802' THEN 'odoo'
        WHEN '12806' THEN 'odoo'
        ELSE 'wansoft'
    END AS fuente_oficial_inventario,
    COUNT(*)      AS num_salidas,
    MAX(Fecha)    AS fecha_max
FROM getoutgoinginventory_salida
WHERE Fecha >= DATE_SUB(CURDATE(), INTERVAL 10 DAY)
GROUP BY subsidiary_name
ORDER BY sucursal;


-- ============================================================
-- 4) COSTOS -- las 4 tablas de costos, siempre alimentadas desde
--    Wansoft (independiente de si Compras/Inventario ya usan
--    Odoo -- ver docs/production-orchestration-plan.md, Costos
--    combina Wansoft + Odoo por partes, esto es solo el lado
--    Wansoft). subsidiary_name aquí SÍ es el nombre real.
-- ============================================================
SELECT 'costeomensual_semanapyq' AS tabla, subsidiary_name AS sucursal,
       COUNT(*) AS num_registros, MAX(created_at) AS fecha_max
FROM costeomensual_semanapyq
WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 10 DAY)
GROUP BY subsidiary_name

UNION ALL

SELECT 'costeomensual', subsidiary_name,
       COUNT(*), MAX(created_at)
FROM costeomensual
WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 10 DAY)
GROUP BY subsidiary_name

UNION ALL

SELECT 'getglobalcashclosing', subsidiary_name,
       COUNT(*), MAX(fecha_corte)
FROM getglobalcashclosing
WHERE fecha_corte >= DATE_SUB(CURDATE(), INTERVAL 10 DAY)
GROUP BY subsidiary_name

UNION ALL

SELECT 'gettotalcostbydate', subsidiary_name,
       COUNT(*), MAX(created_at)
FROM gettotalcostbydate
WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 10 DAY)
GROUP BY subsidiary_name

ORDER BY tabla, sucursal;


-- ============================================================
-- 5) COMPRAS/GASTOS -- getexpenses_factura (Sucursal SÍ es el
--    nombre real) y COSTOS -- gettablajeriareport
-- ============================================================
SELECT 'getexpenses_factura' AS tabla, Sucursal AS sucursal,
       COUNT(*) AS num_registros, NULL AS fecha_max
FROM getexpenses_factura
GROUP BY Sucursal

UNION ALL

SELECT 'gettablajeriareport', subsidiary_name,
       COUNT(*), MAX(InputDate)
FROM gettablajeriareport
WHERE InputDate >= DATE_SUB(CURDATE(), INTERVAL 10 DAY)
GROUP BY subsidiary_name

ORDER BY tabla, sucursal;


-- ============================================================
-- 6) SOLO DEV -- fuente oficial real para las 7 sucursales "odoo"
--    (Compras: canonical_purchase_order_snapshot con
--    source_system='odoo'; Inventario: analytics_inventory_balance)
--    Compara esto contra los totales "odoo" del bloque 2 y 3 de
--    PRODUCTIVO -- deberían ser del mismo orden de magnitud si el
--    corte a Odoo está funcionando bien.
-- ============================================================
SELECT
    company_source_key AS sucursal,
    DATE_FORMAT(order_date, '%Y-%m') AS mes,
    COUNT(*)             AS num_ordenes,
    SUM(amount_total)    AS total_compras_odoo
FROM canonical_purchase_order_snapshot
WHERE source_system = 'odoo'
  AND state NOT IN ('cancel', 'draft')
  AND company_source_key IN (
      'Acoxpa', 'Antenas', 'Tepeyac', 'Oceanía',
      'La Esquina Coyoacán', 'CentroMyJ', 'Puebla'
  )
GROUP BY sucursal, mes
ORDER BY sucursal, mes;

SELECT
    company_source_key AS sucursal,
    COUNT(*)                       AS num_productos,
    SUM(entrada_qty)               AS total_entrada_qty,
    SUM(salida_qty)                AS total_salida_qty,
    SUM(current_balance_qty)       AS total_balance_qty
FROM analytics_inventory_balance
WHERE company_source_key IN (
      'Acoxpa', 'Antenas', 'Tepeyac', 'Oceanía',
      'La Esquina Coyoacán', 'CentroMyJ', 'Puebla'
  )
GROUP BY sucursal
ORDER BY sucursal;


-- ============================================================
-- Conteo aproximado (rápido) por si algún COUNT/WHERE de arriba
-- tarda demasiado en las tablas grandes:
-- ============================================================
SELECT table_name, table_rows AS conteo_aproximado
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_name IN ('getinputinventory_entrada', 'getoutgoinginventory_salida',
                      'getallordenesbyday_new_detalleventa', 'getallordenesbyday_new_modificador');
