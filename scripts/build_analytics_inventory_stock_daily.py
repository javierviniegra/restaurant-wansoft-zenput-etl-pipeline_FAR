"""
Build analytics_inventory_stock_daily: the stock of every product in every
branch on every day, Wansoft and Odoo together, with the whole history
(design: docs/analytics-inventory-unified-design.md, Table 2, agreed with the
owner on 2026-10-10; unified inventory step 4).

One row = branch x product x day, from the first day the product has stock in
the branch to yesterday. Source: analytics_inventory_movements (rows with
counts_in_stock = 1), plus Odoo's own stock capture for the Odoo side.

Which system a day comes from (as purchases and movements):
- a branch without an active odoo_company_migration_policy row: Wansoft;
- a branch migrated to Odoo: Wansoft before its operational_start_date, Odoo
  from it (each system's own count; Odoo starts from its opening balances);
- a branch born on Odoo (include_odoo_history = 1: Puebla, CentroMyJ): Odoo.

How a day's stock is computed:
- Wansoft: running sum of the day's net movements (forward), which is exactly
  analytics_inventory_balance on the last day.
- Odoo: rebuilt BACKWARDS from Odoo's latest daily capture
  (odoo_inventory_quant_daily, internal locations of the branch): stock(D) =
  capture + net(moves dated up to D) - net(moves dated up to the capture day).
  So the last days equal Odoo's own stock, moves registered late with an
  earlier date land on their day, and Antenas' internal inconsistency in Odoo
  stays out of the series (owner, 2026-10-12). For the consistent branches it
  equals the forward sum.

stock_value: running sum of the movements' signed total_cost (Odoo:
valuation layers; Wansoft: movement costs, approximate).

Rows of a day with zero stock and no movement are not stored unless
KEEP_ZERO_DAYS (a missing row means zero; see the decision in the design doc).

    python -m scripts.build_analytics_inventory_stock_daily                 # every branch
    python -m scripts.build_analytics_inventory_stock_daily --only Napoles  # some branches

Runs inside MySQL, one branch at a time, into a new table that replaces the
old one at the end (readers never see it empty).
"""
import argparse
import time
from datetime import date, timedelta

from core.config.companies import get_company_source_key
from core.database.mysql import get_db_connection

TABLE = "analytics_inventory_stock_daily"
STAGING = f"{TABLE}_new"
MOVES = "analytics_inventory_movements"
QUANTS = "odoo_inventory_quant_daily"
CODES = "analytics_odoo_product_code"
KEEP_ZERO_DAYS = False
ZERO = 0.000001  # quantities below this are zero (decimal noise of unit conversions)

DDL = f"""
    CREATE TABLE {STAGING} (
        stock_date                DATE          NOT NULL,
        company_source_key        VARCHAR(100)  NOT NULL,
        product_code              VARCHAR(60)   NOT NULL,
        source_system             VARCHAR(10)   NOT NULL,
        product_name              VARCHAR(255)  NULL,
        stock_qty                 DECIMAL(18,6) NOT NULL,
        stock_value               DECIMAL(18,4) NULL,
        moved_qty                 DECIMAL(18,6) NOT NULL,
        final_source_status       VARCHAR(40)   NOT NULL,
        include_in_business_views TINYINT(1)    NOT NULL,
        built_at                  DATETIME      NOT NULL,
        PRIMARY KEY (company_source_key, product_code, stock_date),
        KEY idx_stock_daily_date (stock_date, company_source_key)
    )
"""


def fetch(cur, sql, params=()):
    cur.execute(sql, params)
    return cur.fetchall()


def branch_plan(cur):
    """company_source_key -> (series start of Odoo or None, born on Odoo)."""
    plan = {}
    for name, start, all_history in fetch(cur, """
            SELECT company_name, operational_start_date, include_odoo_history
            FROM odoo_company_migration_policy WHERE is_active = 1"""):
        key = get_company_source_key(name)
        if key:
            plan[key] = (start, bool(all_history))
    return plan


def daily_net_sql(source, key_filter, extra=""):
    """Per product x day: net quantity and net cost of the stock-moving rows."""
    return f"""
        SELECT product_code, movement_date AS d, SUM(quantity) AS net_qty, SUM(COALESCE(total_cost, 0)) AS net_value,
               MAX(product_name) AS product_name
        FROM {MOVES}
        WHERE company_source_key = %s AND source_system = '{source}' AND counts_in_stock = 1
          AND product_code IS NOT NULL {key_filter} {extra}
        GROUP BY product_code, movement_date
    """


def build_branch(cur, key, odoo_start, born_on_odoo, yesterday, built_at):
    """Insert the branch's days into the staging table; returns rows inserted."""
    cur.execute("DROP TABLE IF EXISTS tmp_sd_changes")
    cur.execute("""
        CREATE TABLE tmp_sd_changes (
            product_code VARCHAR(60) NOT NULL, d DATE NOT NULL, source_system VARCHAR(10) NOT NULL,
            product_name VARCHAR(255), net_qty DECIMAL(18,6) NOT NULL, stock_qty DECIMAL(18,6) NOT NULL,
            stock_value DECIMAL(18,4) NULL, series_end DATE NOT NULL,
            PRIMARY KEY (product_code, d)
        ) ENGINE=InnoDB
    """)

    # ---- Wansoft series: running sum, cut the day before the Odoo start
    if not born_on_odoo:
        wansoft_end = (odoo_start - timedelta(days=1)) if odoo_start else yesterday
        cur.execute(f"""
            INSERT INTO tmp_sd_changes
            SELECT product_code, d, 'wansoft', product_name, net_qty,
                   SUM(net_qty) OVER (PARTITION BY product_code ORDER BY d),
                   SUM(net_value) OVER (PARTITION BY product_code ORDER BY d),
                   %s
            FROM ({daily_net_sql('wansoft', "AND include_in_business_views = 1", "AND movement_date <= %s")}) w
        """, (wansoft_end, key, wansoft_end))

    # ---- Odoo series: backwards from the latest capture of the branch
    if odoo_start or born_on_odoo:
        capture = fetch(cur, f"SELECT MAX(stock_date) FROM {QUANTS} WHERE company_source_key = %s AND stock_date <= %s",
                        (key, yesterday))[0][0]
        odoo_from = None if born_on_odoo else odoo_start
        cur.execute("DROP TABLE IF EXISTS tmp_sd_odoo")
        cur.execute(f"""
            CREATE TABLE tmp_sd_odoo ENGINE=InnoDB AS
            SELECT product_code, d, product_name, net_qty, net_value,
                   SUM(net_qty) OVER (PARTITION BY product_code ORDER BY d) AS fwd_qty,
                   SUM(net_value) OVER (PARTITION BY product_code ORDER BY d) AS fwd_value
            FROM ({daily_net_sql('odoo', '', 'AND movement_date <= %s')}) o
        """, (key, yesterday))
        cur.execute("ALTER TABLE tmp_sd_odoo ADD PRIMARY KEY (product_code, d)")
        # Odoo's stock at the capture, by the same product code as the movements.
        cur.execute("DROP TABLE IF EXISTS tmp_sd_capture")
        cur.execute(f"""
            CREATE TABLE tmp_sd_capture ENGINE=InnoDB AS
            SELECT COALESCE(c.wansoft_code, CONCAT('ODOO-', q.odoo_product_id)) AS product_code,
                   SUM(q.quantity) AS qty, MAX(q.product_name) AS product_name
            FROM {QUANTS} q LEFT JOIN {CODES} c ON c.odoo_product_id = q.odoo_product_id
            WHERE q.company_source_key = %s AND q.stock_date = %s AND q.location_usage = 'internal'
            GROUP BY 1
        """, (key, capture))
        cur.execute("ALTER TABLE tmp_sd_capture ADD PRIMARY KEY (product_code)")
        # forward sum at the capture day, per product
        cur.execute("DROP TABLE IF EXISTS tmp_sd_at_capture")
        cur.execute("""
            CREATE TABLE tmp_sd_at_capture ENGINE=InnoDB AS
            SELECT product_code, MAX(fwd_qty) AS fwd_at_capture
            FROM (SELECT o.product_code, o.fwd_qty FROM tmp_sd_odoo o
                  JOIN (SELECT product_code, MAX(d) AS d FROM tmp_sd_odoo WHERE d <= %s GROUP BY product_code) x
                    ON x.product_code = o.product_code AND x.d = o.d) t
            GROUP BY product_code
        """, (capture or date.min,))
        cur.execute("ALTER TABLE tmp_sd_at_capture ADD PRIMARY KEY (product_code)")
        # stock(D) = capture + fwd(D) - fwd(capture); with no capture, the forward sum
        series_from = odoo_from or date(2000, 1, 1)
        cur.execute(f"""
            INSERT INTO tmp_sd_changes
            SELECT o.product_code, o.d, 'odoo', COALESCE(o.product_name, cap.product_name), o.net_qty,
                   COALESCE(cap.qty, 0) + o.fwd_qty - COALESCE(a.fwd_at_capture, 0) * (%s IS NOT NULL),
                   o.fwd_value, %s
            FROM tmp_sd_odoo o
            LEFT JOIN tmp_sd_capture cap ON cap.product_code = o.product_code
            LEFT JOIN tmp_sd_at_capture a ON a.product_code = o.product_code
            WHERE o.d >= %s
        """, (capture, yesterday, series_from))
        # The stock the series starts with: the day before its first day (opening),
        # for products already holding stock when the series begins, and the
        # products Odoo holds with no movement in the series at all.
        start_day = odoo_from or None
        if start_day:
            cur.execute(f"""
                INSERT INTO tmp_sd_changes
                SELECT p.product_code, %s, 'odoo', COALESCE(o.product_name, cap.product_name), 0,
                       COALESCE(cap.qty, 0) + COALESCE(o.fwd_qty, 0) - COALESCE(a.fwd_at_capture, 0) * (%s IS NOT NULL),
                       o.fwd_value, %s
                FROM (SELECT product_code FROM tmp_sd_capture UNION SELECT DISTINCT product_code FROM tmp_sd_odoo) p
                LEFT JOIN (SELECT t.* FROM tmp_sd_odoo t
                           JOIN (SELECT product_code, MAX(d) AS d FROM tmp_sd_odoo WHERE d < %s GROUP BY product_code) x
                             ON x.product_code = t.product_code AND x.d = t.d) o ON o.product_code = p.product_code
                LEFT JOIN tmp_sd_capture cap ON cap.product_code = p.product_code
                LEFT JOIN tmp_sd_at_capture a ON a.product_code = p.product_code
                WHERE NOT EXISTS (SELECT 1 FROM tmp_sd_changes c WHERE c.product_code = p.product_code AND c.d = %s)
            """, (start_day, capture, yesterday, start_day, start_day))
        else:
            cur.execute(f"""
                INSERT INTO tmp_sd_changes
                SELECT cap.product_code, %s, 'odoo', cap.product_name, 0, cap.qty, NULL, %s
                FROM tmp_sd_capture cap
                WHERE NOT EXISTS (SELECT 1 FROM tmp_sd_odoo o WHERE o.product_code = cap.product_code)
            """, (capture, yesterday))

    # ---- Expand each change to the days until the next change (or the series end)
    status = {"wansoft": "wansoft_final" if not odoo_start else "wansoft_history_before_odoo", "odoo": "odoo_final"}
    zero_filter = "" if KEEP_ZERO_DAYS else f"AND (ABS(c.stock_qty) > {ZERO} OR t.calendar_date = c.d)"
    cur.execute(f"""
        INSERT INTO {STAGING}
        SELECT t.calendar_date, %s, c.product_code, c.source_system, c.product_name, c.stock_qty, c.stock_value,
               IF(t.calendar_date = c.d, c.net_qty, 0),
               CASE c.source_system WHEN 'wansoft' THEN %s ELSE %s END, 1, %s
        FROM (SELECT ch.*, LEAD(ch.d) OVER (PARTITION BY ch.product_code ORDER BY ch.d) AS next_d FROM tmp_sd_changes ch) c
        JOIN dim_time t ON t.calendar_date >= c.d
                       AND t.calendar_date < COALESCE(LEAST(c.next_d, DATE_ADD(c.series_end, INTERVAL 1 DAY)),
                                                      DATE_ADD(c.series_end, INTERVAL 1 DAY))
        WHERE 1 = 1 {zero_filter}
    """, (key, status["wansoft"], status["odoo"], built_at))
    return cur.rowcount


HELPERS = ("tmp_sd_changes", "tmp_sd_odoo", "tmp_sd_capture", "tmp_sd_at_capture")


def drop_helpers(cur):
    # Regular tables, not TEMPORARY: MariaDB cannot open a temporary table twice
    # in one statement, and the Odoo steps join these tables with themselves.
    for name in HELPERS:
        cur.execute(f"DROP TABLE IF EXISTS {name}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="+", help="company_source_key values to build (default: every branch)")
    args = parser.parse_args(argv)

    yesterday = date.today() - timedelta(days=1)
    built_at = date.today().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        plan = branch_plan(cur)
        branches = [r[0] for r in fetch(cur, f"SELECT DISTINCT company_source_key FROM {MOVES} ORDER BY 1")]
        if args.only:
            branches = [b for b in branches if b in args.only]
        cur.execute(f"DROP TABLE IF EXISTS {STAGING}")
        cur.execute(DDL)
        total = 0
        for key in branches:
            started = time.time()
            odoo_start, born = plan.get(key, (None, False))
            rows = build_branch(cur, key, odoo_start, born, yesterday, built_at)
            conn.commit()
            total += rows
            print(f"  {key}: {rows:,} filas ({time.time() - started:.0f} s)")
        drop_helpers(cur)
        if args.only:
            print(f"{STAGING}: {total:,} filas (corrida parcial: no reemplaza {TABLE})")
            return 0
        cur.execute(f"DROP TABLE IF EXISTS {TABLE}_old")
        if fetch(cur, "SHOW TABLES LIKE %s", (TABLE,)):
            cur.execute(f"RENAME TABLE {TABLE} TO {TABLE}_old, {STAGING} TO {TABLE}")
            cur.execute(f"DROP TABLE {TABLE}_old")
        else:
            cur.execute(f"RENAME TABLE {STAGING} TO {TABLE}")
        print(f"{TABLE}: {total:,} filas")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
