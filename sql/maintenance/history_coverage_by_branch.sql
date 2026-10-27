-- History coverage per branch: first and last day of data in each reference table,
-- per branch and source system (Wansoft / Odoo). Read-only (SELECT only).
--
-- One row per table x branch x source. Branches use the short key everywhere
-- (company_source_key); costs and cash closing carry the Wansoft ID, translated
-- with costs_source_by_company (7697 = Taqueria San Fernando, which left the
-- group on 2025-02-28, keeps its long name). Costs are split by
-- costs_source_by_company.odoo_cost_start_date: days before it are Wansoft,
-- from it Odoo. Analytic tables count only include_in_business_views = 1.
--
-- Takes about one minute (the daily stock part is ~40 s). Do not run
-- it between 01:30 and 03:00 (nightly load) or on Thursday at 18:00 (backup).
-- Data guide section 4.1 and the reference sheet (reports/referencias) quote it.

SELECT * FROM (

    -- Sales: tickets (Wansoft, every branch). Fecha is text 'YYYY-MM-DDT00:00:00'.
    SELECT '1 Ventas' AS tema, 'getallordenesbyday_new_venta' AS tabla, 'wansoft' AS fuente,
           Sucursal AS sucursal, LEFT(MIN(Fecha), 10) AS desde, LEFT(MAX(Fecha), 10) AS hasta, COUNT(*) AS filas
    FROM getallordenesbyday_new_venta
    GROUP BY Sucursal

    UNION ALL
    -- Cash closing (Z report), Wansoft
    SELECT '2 Cierre de caja', 'getglobalcashclosing', 'wansoft',
           COALESCE(m.company_source_key, MAX(x.subsidiary_name)), MIN(DATE(x.fecha_corte)), MAX(DATE(x.fecha_corte)), COUNT(*)
    FROM getglobalcashclosing x
    LEFT JOIN costs_source_by_company m ON m.wansoft_subsidiary_id = x.subsidiary_id
    GROUP BY x.subsidiary_id, m.company_source_key

    UNION ALL
    -- Daily cost: Wansoft before the branch's Odoo cost start, Odoo from it
    SELECT '3 Costo diario', 'gettotalcostbydate',
           IF(x.created_date >= m.odoo_cost_start_date, 'odoo', 'wansoft') AS fuente,
           COALESCE(m.company_source_key, MAX(x.subsidiary_name)), MIN(x.created_date), MAX(x.created_date), COUNT(*)
    FROM gettotalcostbydate x
    LEFT JOIN costs_source_by_company m ON m.wansoft_subsidiary_id = x.subsidiary_id
    GROUP BY x.subsidiary_id, m.company_source_key, 3

    UNION ALL
    -- Monthly cost (cumulative snapshots)
    SELECT '4 Costo mensual', 'costeomensual',
           IF(x.created_date >= m.odoo_cost_start_date, 'odoo', 'wansoft'),
           COALESCE(m.company_source_key, MAX(x.subsidiary_name)), MIN(x.created_date), MAX(x.created_date), COUNT(*)
    FROM costeomensual x
    LEFT JOIN costs_source_by_company m ON m.wansoft_subsidiary_id = x.subsidiary_id
    GROUP BY x.subsidiary_id, m.company_source_key, 3

    UNION ALL
    -- Weekly cost (cumulative snapshots)
    SELECT '5 Costo semanal', 'costeomensual_semanapyq',
           IF(x.created_date >= m.odoo_cost_start_date, 'odoo', 'wansoft'),
           COALESCE(m.company_source_key, MAX(x.subsidiary_name)), MIN(x.created_date), MAX(x.created_date), COUNT(*)
    FROM costeomensual_semanapyq x
    LEFT JOIN costs_source_by_company m ON m.wansoft_subsidiary_id = x.subsidiary_id
    GROUP BY x.subsidiary_id, m.company_source_key, 3

    UNION ALL
    -- Purchases (lines), Wansoft + Odoo
    SELECT '6 Compras', 'analytics_purchase_order_lines', source_system,
           company_source_key, MIN(DATE(order_date)), MAX(DATE(order_date)), COUNT(*)
    FROM analytics_purchase_order_lines
    WHERE include_in_business_views = 1
    GROUP BY company_source_key, source_system

    UNION ALL
    -- Supplier invoices by account, Wansoft + Odoo
    SELECT '7 Gastos', 'analytics_expense_invoices', source_system,
           company_source_key, MIN(invoice_date), MAX(invoice_date), COUNT(*)
    FROM analytics_expense_invoices
    WHERE include_in_business_views = 1
    GROUP BY company_source_key, source_system

    UNION ALL
    -- Inventory movements, Wansoft + Odoo. Per branch only, through idx_company_date
    -- (instant); a split by source or a row count reads all ~40 M rows (over 10 min).
    -- The per-source dates are the same as the daily stock's below.
    SELECT '8 Movimientos de inventario', 'analytics_inventory_movements', 'wansoft + odoo',
           company_source_key, MIN(movement_date), MAX(movement_date), NULL
    FROM analytics_inventory_movements
    GROUP BY company_source_key

    UNION ALL
    -- Daily stock, Wansoft + Odoo (~40 s; filas left out: same cost, no extra information)
    SELECT '9 Existencias por dia', 'analytics_inventory_stock_daily', source_system,
           company_source_key, MIN(stock_date), MAX(stock_date), NULL
    FROM analytics_inventory_stock_daily
    GROUP BY company_source_key, source_system

) cobertura
ORDER BY tema, sucursal, desde;
