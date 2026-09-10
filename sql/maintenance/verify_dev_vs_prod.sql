-- ============================================================
-- Verificación manual dev vs productivo
-- ============================================================
-- Cómo usar: corre este mismo script DOS VECES, una conectado a
-- la base de datos DEV y otra conectado a PRODUCTIVO (mismo nombre
-- de base, "wansoft" y "zenput", pero host distinto -- ver
-- WANSOFT_DB_HOST vs WANSOFT_DB_HOST_DEV / ZENPUT_DB_HOST vs
-- ZENPUT_DB_HOST_DEV en core/config/.env). Compara los resultados
-- lado a lado.
--
-- No escribe nada, solo lectura.
-- ============================================================


-- ============================================================
-- BASE DE DATOS: wansoft
-- ============================================================

-- --- Ventas: getallordenesbyday_new_venta ---------------------
-- (Fecha se guarda como texto, no hay columna de fecha real que
--  se pueda filtrar con WHERE fecha >= ...; solo el conteo total
--  es comparable directamente. Recuerda: dev solo guarda los
--  ultimos ~10 dias por diseño del Candado, prod tiene historial
--  completo -- una diferencia grande en el TOTAL es esperada.)
SELECT COUNT(*) AS total_venta FROM getallordenesbyday_new_venta;
SELECT COUNT(*) AS total_pago  FROM getallordenesbyday_new_pago;

-- DetalleVenta y Modificador son tablas grandes; el COUNT(*) puede
-- tardar. Si tarda demasiado, usa el conteo aproximado de abajo.
SELECT COUNT(*) AS total_detalle FROM getallordenesbyday_new_detalleventa;
SELECT COUNT(*) AS total_modificador FROM getallordenesbyday_new_modificador;

-- Conteo aproximado rápido (no exacto, pero no se tarda) para
-- las tablas grandes, si el COUNT(*) de arriba tarda mucho:
SELECT table_name, table_rows AS conteo_aproximado
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_name IN ('getallordenesbyday_new_detalleventa',
                      'getallordenesbyday_new_modificador',
                      'getoutgoinginventory_salida');


-- --- Inventario: getinputinventory_entrada --------------------
SELECT COUNT(*) AS total,
       MIN(FechaEntrada) AS fecha_min,
       MAX(FechaEntrada) AS fecha_max
FROM getinputinventory_entrada;

SELECT COUNT(*) AS ultimos_35_dias
FROM getinputinventory_entrada
WHERE FechaEntrada >= DATE_SUB(CURDATE(), INTERVAL 35 DAY);


-- --- Inventario: getoutgoinginventory_salida -------------------
-- Tabla muy grande: el COUNT(*) exacto puede tardar o cortarse.
-- Usa el conteo por rango de fecha en su lugar (más rápido si
-- Fecha/FechaSalida tiene índice) o el conteo aproximado de arriba.
SELECT COUNT(*) AS ultimos_35_dias
FROM getoutgoinginventory_salida
WHERE Fecha >= DATE_SUB(CURDATE(), INTERVAL 35 DAY);


-- --- Costos: costeomensual_semanapyq ---------------------------
SELECT COUNT(*) AS total,
       MIN(created_at) AS fecha_min,
       MAX(created_at) AS fecha_max
FROM costeomensual_semanapyq;

SELECT COUNT(*) AS ultimos_35_dias
FROM costeomensual_semanapyq
WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 35 DAY);


-- --- Costos: costeomensual --------------------------------------
SELECT COUNT(*) AS total,
       MIN(created_at) AS fecha_min,
       MAX(created_at) AS fecha_max
FROM costeomensual;

SELECT COUNT(*) AS ultimos_35_dias
FROM costeomensual
WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 35 DAY);


-- --- Costos: getglobalcashclosing --------------------------------
SELECT COUNT(*) AS total,
       MIN(fecha_corte) AS fecha_min,
       MAX(fecha_corte) AS fecha_max
FROM getglobalcashclosing;

SELECT COUNT(*) AS ultimos_35_dias
FROM getglobalcashclosing
WHERE fecha_corte >= DATE_SUB(CURDATE(), INTERVAL 35 DAY);


-- --- Compras: getexpenses_factura --------------------------------
-- (FechaDeExpedicion es texto, no fecha real; solo el total es
--  directamente comparable)
SELECT COUNT(*) AS total_facturas FROM getexpenses_factura;


-- --- Costos: gettablajeriareport ----------------------------------
SELECT COUNT(*) AS total,
       MIN(InputDate) AS fecha_min,
       MAX(InputDate) AS fecha_max
FROM gettablajeriareport;

SELECT COUNT(*) AS ultimos_35_dias
FROM gettablajeriareport
WHERE InputDate >= DATE_SUB(CURDATE(), INTERVAL 35 DAY);


-- --- Costos: gettotalcostbydate -------------------------------------
SELECT COUNT(*) AS total,
       MIN(created_at) AS fecha_min,
       MAX(created_at) AS fecha_max
FROM gettotalcostbydate;

SELECT COUNT(*) AS ultimos_35_dias
FROM gettotalcostbydate
WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 35 DAY);


-- ============================================================
-- BASE DE DATOS: zenput  (cambia de conexión a la base "zenput")
-- ============================================================

-- --- form_templates -------------------------------------------------
SELECT COUNT(*) AS total,
       MIN(date_created) AS fecha_min,
       MAX(date_created) AS fecha_max
FROM form_templates;


-- --- submissions ------------------------------------------------------
SELECT COUNT(*) AS total,
       MIN(date_submitted) AS fecha_min,
       MAX(date_submitted) AS fecha_max
FROM submissions;

SELECT COUNT(*) AS ultimos_35_dias
FROM submissions
WHERE date_submitted >= DATE_SUB(CURDATE(), INTERVAL 35 DAY);


-- --- submission_answers -------------------------------------------------
-- (no tiene columna de fecha propia; solo el total es comparable)
SELECT COUNT(*) AS total_submission_answers FROM submission_answers;


-- --- zenput_tasks ----------------------------------------------------------
SELECT COUNT(*) AS total,
       MIN(date_created) AS fecha_min,
       MAX(date_created) AS fecha_max
FROM zenput_tasks;

SELECT COUNT(*) AS ultimos_35_dias
FROM zenput_tasks
WHERE date_created >= DATE_SUB(CURDATE(), INTERVAL 35 DAY);
