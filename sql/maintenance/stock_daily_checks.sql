-- Checks of analytics_inventory_stock_daily for phpMyAdmin (read-only, SELECT only).
-- Same checks as scripts/validate_analytics_inventory_stock_daily.py, simplified.
-- Run in the daytime, not between 01:30 and 03:00. Tested in production 2026-10-27.

-- 1. Gaps: series (branch x source x product) missing a day. Expected: 0 rows. ~1 minute.
SELECT company_source_key, source_system, product_code, MIN(stock_date) AS desde, MAX(stock_date) AS hasta,
       COUNT(*) AS dias, DATEDIFF(MAX(stock_date), MIN(stock_date)) + 1 AS dias_esperados
FROM analytics_inventory_stock_daily
GROUP BY company_source_key, source_system, product_code
HAVING dias <> dias_esperados;

-- 2. Wansoft branches: yesterday vs analytics_inventory_balance. Expected: distintos = 0,
--    except Aeropuerto = 8 (16 raw entries of 2021 duplicated; the balance counts them twice).
SELECT s.company_source_key, COUNT(*) AS productos,
       SUM(ABS(s.stock_qty - COALESCE(b.current_balance_qty, 0)) > 0.001) AS distintos
FROM analytics_inventory_stock_daily s
LEFT JOIN analytics_inventory_balance b
       ON b.company_source_key = s.company_source_key AND b.source_system = 'wansoft' AND b.wansoft_code = s.product_code
WHERE s.final_source_status = 'wansoft_final' AND s.stock_date = CURDATE() - INTERVAL 1 DAY
GROUP BY s.company_source_key;

-- 3. Odoo branches: yesterday vs Odoo's own stock (capture of yesterday, internal locations).
--    Expected: distintos = 0 in the 10 branches.
SELECT s.company_source_key, COUNT(*) AS productos,
       SUM(ABS(s.stock_qty - COALESCE(c.qty, 0)) > 0.001) AS distintos
FROM analytics_inventory_stock_daily s
LEFT JOIN (SELECT q.company_source_key, COALESCE(m.wansoft_code, CONCAT('ODOO-', q.odoo_product_id)) AS product_code,
                  SUM(q.quantity) AS qty
           FROM odoo_inventory_quant_daily q
           LEFT JOIN analytics_odoo_product_code m ON m.odoo_product_id = q.odoo_product_id
           WHERE q.stock_date = CURDATE() - INTERVAL 1 DAY AND q.location_usage = 'internal'
           GROUP BY 1, 2) c
       ON c.company_source_key = s.company_source_key AND c.product_code = s.product_code
WHERE s.source_system = 'odoo' AND s.stock_date = CURDATE() - INTERVAL 1 DAY
GROUP BY s.company_source_key;
