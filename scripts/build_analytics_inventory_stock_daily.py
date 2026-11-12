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

Odoo value correction (owner, 2026-11-12): Odoo's FIFO valuation broke in
Antenas (selling with no stock + manual adjustments at an already inflated
cost: unit costs up to 1.5 trillion pesos, its stock at -1.7 trillion). An
Odoo row whose value is surely wrong gets stock_value = stock_qty x a real
unit price; Odoo's own value stays in stock_value_source and value_method
says which one stock_value is. Surely wrong (WRONG_VALUE_SQL): |unit value|
> 100,000, a value whose sign is opposite to the quantity, or a zero value on
a non-zero quantity. The price, in order: the branch's average
purchase-receipt cost of the last 90 days (purchase_price), the same over
every Odoo branch (purchase_price_group), the average incoming cost of any
other kind in another Odoo branch (other_branch_cost, e.g. preparations);
with none, stock_value is NULL (no_price). Rows that only look odd (unit value
outside 0.2x-5x of the purchase price, which can also be a wrong purchase)
are listed but not corrected. Yesterday's list, corrected or not, is
rewritten every night in odoo_stock_value_exceptions, for the Odoo
implementer, and the log prints one [AVISO] per branch.

Rows of a day with zero stock and no movement are not stored unless
KEEP_ZERO_DAYS (a missing row means zero; see the decision in the design doc).

    python -m scripts.build_analytics_inventory_stock_daily --full          # first load / start over
    python -m scripts.build_analytics_inventory_stock_daily                 # nightly update
    python -m scripts.build_analytics_inventory_stock_daily --only Napoles  # some branches (either mode)

Runs inside MySQL, one branch at a time. --full builds a new table that
replaces the old one at the end (readers never see it empty; with --only it
stays as the _new table). The nightly update rewrites, in the live table, each
branch's Wansoft days from the oldest day the movements' nightly window touched
and its whole (short) Odoo series.
"""
import argparse
import time
from datetime import date, timedelta

from core.config.companies import get_company_source_key
from core.database.mysql import get_db_connection
from scripts.build_analytics_inventory_movements import DEFAULT_WINDOW_DAYS as MOVEMENTS_WINDOW_DAYS

TABLE = "analytics_inventory_stock_daily"
STAGING = f"{TABLE}_new"
MOVES = "analytics_inventory_movements"
QUANTS = "odoo_inventory_quant_daily"
CODES = "analytics_odoo_product_code"
KEEP_ZERO_DAYS = True  # owner, 2026-10-26: every day, zero-stock days included (18.1 M rows measured)
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
        stock_value_source        DECIMAL(18,4) NULL,
        value_method              VARCHAR(30)   NOT NULL DEFAULT 'source',
        PRIMARY KEY (company_source_key, product_code, stock_date),
        KEY idx_stock_daily_date (stock_date, company_source_key)
    )
"""

# Columns added on 2026-11-12 to a live table built before (MariaDB adds them instantly).
NEW_COLUMNS = (
    "stock_value_source DECIMAL(18,4) NULL",
    "value_method VARCHAR(30) NOT NULL DEFAULT 'source'",
)
INSERT_COLUMNS = ("stock_date, company_source_key, product_code, source_system, product_name, stock_qty, stock_value, "
                  "moved_qty, final_source_status, include_in_business_views, built_at, stock_value_source")

EXCEPTIONS = "odoo_stock_value_exceptions"
EXCEPTIONS_DDL = f"""
    CREATE TABLE IF NOT EXISTS {EXCEPTIONS} (
        company_source_key  VARCHAR(100)  NOT NULL,
        product_code        VARCHAR(60)   NOT NULL,
        product_name        VARCHAR(255)  NULL,
        stock_date          DATE          NOT NULL,
        stock_qty           DECIMAL(18,6) NOT NULL,
        stock_value_source  DECIMAL(18,4) NULL,
        unit_value_source   DECIMAL(30,4) NULL,
        unit_price          DECIMAL(18,6) NULL,
        stock_value         DECIMAL(18,4) NULL,
        value_method        VARCHAR(30)   NOT NULL,
        reason              VARCHAR(60)   NOT NULL,
        built_at            DATETIME      NOT NULL,
        PRIMARY KEY (company_source_key, product_code)
    )
"""
UNIT_VALUE_LIMIT = 100000
PRICE_WINDOW_DAYS = 90
# An Odoo row whose value is surely wrong (s = the stock table row; v = Odoo's value).
WRONG_VALUE_SQL = f"""(ABS(s.stock_qty) > {ZERO} AND (
    ABS(s.stock_value_source) > {UNIT_VALUE_LIMIT} * ABS(s.stock_qty)
    OR SIGN(s.stock_value_source) = -SIGN(s.stock_qty)
    OR ABS(COALESCE(s.stock_value_source, 0)) < 0.005))"""
WRONG_REASON_SQL = f"""CASE
    WHEN ABS(s.stock_value_source) > {UNIT_VALUE_LIMIT} * ABS(s.stock_qty) THEN 'costo unitario mayor a 100,000'
    WHEN SIGN(s.stock_value_source) = -SIGN(s.stock_qty) THEN 'valor con signo contrario a la existencia'
    ELSE 'valor cero con existencia' END"""


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


def load_nets(cur, key, source, until, business_only, since=None):
    """tmp_sd_nets: per product x day, the net quantity and cost of the stock-moving rows."""
    cur.execute("DROP TABLE IF EXISTS tmp_sd_nets")
    cur.execute("""
        CREATE TABLE tmp_sd_nets (
            product_code VARCHAR(60) NOT NULL, d DATE NOT NULL, net_qty DECIMAL(18,6) NOT NULL,
            net_value DECIMAL(18,4) NOT NULL, product_name VARCHAR(255) NULL,
            PRIMARY KEY (product_code, d)
        ) ENGINE=InnoDB
    """)
    cur.execute(f"""
        INSERT INTO tmp_sd_nets
        SELECT product_code, movement_date, SUM(quantity), SUM(COALESCE(total_cost, 0)), MAX(product_name)
        FROM {MOVES}
        WHERE company_source_key = %s AND source_system = %s AND counts_in_stock = 1 AND product_code IS NOT NULL
          AND movement_date <= %s {"AND include_in_business_views = 1" if business_only else ""}
          {"AND movement_date >= %s" if since else ""}
        GROUP BY product_code, movement_date
    """, (key, source, until) + ((since,) if since else ()))


RUNNING_QTY = "SUM(COALESCE(n.net_qty, 0)) OVER (PARTITION BY p.product_code ORDER BY t.calendar_date)"
RUNNING_VALUE = "SUM(COALESCE(n.net_value, 0)) OVER (PARTITION BY p.product_code ORDER BY t.calendar_date)"


def insert_days(cur, target, key, source, status, first_day_sql, last_day, keep_from, stock_sql, value_sql, built_at):
    """
    The grid product x day (each product from its first day to last_day) joined
    to the day's net by exact key, then a running sum per product. Expanding a
    grid of products x calendar days is cheap; joining every change to a range of
    days was a block-nested-loop join (1.75 billion comparisons for Napoles).
    keep_from drops the days before it after the running sum (the Odoo side
    starts at the branch's start date but sums every earlier move).
    """
    zero_filter = "" if KEEP_ZERO_DAYS else f"AND (ABS(x.stock_qty) > {ZERO} OR x.moved_qty <> 0)"
    cur.execute(f"""
        INSERT INTO {target} ({INSERT_COLUMNS})
        SELECT x.stock_date, %s, x.product_code, %s, x.product_name, x.stock_qty, x.stock_value, x.moved_qty,
               %s, 1, %s, x.stock_value
        FROM (
            SELECT t.calendar_date AS stock_date, p.product_code, p.product_name,
                   {stock_sql} AS stock_qty,
                   {value_sql} AS stock_value,
                   COALESCE(n.net_qty, 0) AS moved_qty
            FROM tmp_sd_products p
            JOIN dim_time t ON t.calendar_date BETWEEN {first_day_sql} AND %s
            LEFT JOIN tmp_sd_nets n ON n.product_code = p.product_code AND n.d = t.calendar_date
        ) x
        WHERE x.stock_date >= %s {zero_filter}
    """, (key, source, status, built_at, last_day, keep_from))
    return cur.rowcount


def build_branch(cur, key, odoo_start, born_on_odoo, yesterday, built_at, target=STAGING, wansoft_from=None):
    """
    Insert the branch's days into `target`; returns rows inserted.
    wansoft_from (nightly): rebuild the Wansoft series only from that day, starting
    from the stock of the day before already stored in `target`.
    """
    rows = 0
    running = RUNNING_QTY

    # ---- Wansoft series: running sum, up to the day before the Odoo start
    if not born_on_odoo:
        # Capped at yesterday: a policy row may be loaded before its start date.
        wansoft_end = min(odoo_start - timedelta(days=1), yesterday) if odoo_start else yesterday
        if wansoft_from is None or wansoft_from <= wansoft_end:
            load_nets(cur, key, "wansoft", wansoft_end, business_only=True, since=wansoft_from)
            cur.execute("DROP TABLE IF EXISTS tmp_sd_products")
            if wansoft_from is None:
                cur.execute("""
                    CREATE TABLE tmp_sd_products ENGINE=InnoDB AS
                    SELECT product_code, MIN(d) AS first_d, MAX(product_name) AS product_name,
                           CAST(0 AS DECIMAL(18,6)) AS seed_qty, CAST(0 AS DECIMAL(18,4)) AS seed_value
                    FROM tmp_sd_nets GROUP BY product_code
                """)
            else:
                # The stored stock of the day before is the starting point; products
                # that first appear in the window start at their first movement.
                day_before = wansoft_from - timedelta(days=1)
                cur.execute(f"""
                    CREATE TABLE tmp_sd_products ENGINE=InnoDB AS
                    SELECT a.product_code, IF(s.product_code IS NULL, n.first_d, %s) AS first_d,
                           COALESCE(n.product_name, s.product_name) AS product_name,
                           COALESCE(s.stock_qty, 0) AS seed_qty, COALESCE(s.stock_value, 0) AS seed_value
                    FROM (SELECT product_code FROM {target}
                          WHERE company_source_key = %s AND source_system = 'wansoft' AND stock_date = %s
                          UNION SELECT product_code FROM tmp_sd_nets) a
                    LEFT JOIN (SELECT product_code, product_name, stock_qty, stock_value FROM {target}
                               WHERE company_source_key = %s AND source_system = 'wansoft' AND stock_date = %s) s
                           ON s.product_code = a.product_code
                    LEFT JOIN (SELECT product_code, MIN(d) AS first_d, MAX(product_name) AS product_name
                               FROM tmp_sd_nets GROUP BY product_code) n ON n.product_code = a.product_code
                """, (wansoft_from, key, day_before, key, day_before))
            status = "wansoft_history_before_odoo" if odoo_start else "wansoft_final"
            rows += insert_days(cur, target, key, "wansoft", status, "p.first_d", wansoft_end, date(2000, 1, 1),
                                f"p.seed_qty + {running}", f"p.seed_value + {RUNNING_VALUE}", built_at)

    # ---- Odoo series: backwards from the latest capture of the branch
    if odoo_start or born_on_odoo:
        capture = fetch(cur, f"SELECT MAX(stock_date) FROM {QUANTS} WHERE company_source_key = %s AND stock_date <= %s",
                        (key, yesterday))[0][0]
        load_nets(cur, key, "odoo", yesterday, business_only=False)  # every Odoo move: the sum starts at the beginning
        cur.execute("DROP TABLE IF EXISTS tmp_sd_capture")
        cur.execute(f"""
            CREATE TABLE tmp_sd_capture ENGINE=InnoDB AS
            SELECT COALESCE(c.wansoft_code, CONCAT('ODOO-', q.odoo_product_id)) AS product_code,
                   SUM(q.quantity) AS qty, MAX(q.product_name) AS product_name
            FROM {QUANTS} q LEFT JOIN {CODES} c ON c.odoo_product_id = q.odoo_product_id
            WHERE q.company_source_key = %s AND q.stock_date = %s AND q.location_usage = 'internal'
            GROUP BY 1
        """, (key, capture))
        series_start = (fetch(cur, "SELECT MIN(d) FROM tmp_sd_nets")[0][0] or capture or yesterday) if born_on_odoo else odoo_start
        cur.execute("DROP TABLE IF EXISTS tmp_sd_products")
        # Products with moves start at their first move (the running sum needs it);
        # products Odoo holds without any move start at the series start.
        cur.execute("""
            CREATE TABLE tmp_sd_products ENGINE=InnoDB AS
            SELECT a.product_code, LEAST(COALESCE(n.first_d, %s), %s) AS first_d,
                   COALESCE(n.product_name, c.product_name) AS product_name,
                   COALESCE(c.qty, 0) AS cap_qty, COALESCE(f.fwd_at_capture, 0) AS fwd_at_capture
            FROM (SELECT product_code FROM tmp_sd_nets UNION SELECT product_code FROM tmp_sd_capture) a
            LEFT JOIN (SELECT product_code, MIN(d) AS first_d, MAX(product_name) AS product_name
                       FROM tmp_sd_nets GROUP BY product_code) n ON n.product_code = a.product_code
            LEFT JOIN tmp_sd_capture c ON c.product_code = a.product_code
            LEFT JOIN (SELECT product_code, SUM(net_qty) AS fwd_at_capture FROM tmp_sd_nets
                       WHERE d <= %s GROUP BY product_code) f ON f.product_code = a.product_code
        """, (series_start, series_start, capture or date.min))
        # stock(D) = capture + forward(D) - forward(capture); with no capture, the forward sum
        stock = running if capture is None else f"p.cap_qty + {running} - p.fwd_at_capture"
        rows += insert_days(cur, target, key, "odoo", "odoo_final", "p.first_d", yesterday, series_start, stock,
                            RUNNING_VALUE, built_at)
        correct_odoo_values(cur, target, key, yesterday, built_at)
    return rows


def correct_odoo_values(cur, target, key, yesterday, built_at):
    """
    The Odoo value correction of the module docstring for one branch: prices
    into tmp_sd_price, then stock_value of the surely wrong rows of `target`
    rewritten, then yesterday's list in odoo_stock_value_exceptions.
    """
    since = yesterday - timedelta(days=PRICE_WINDOW_DAYS - 1)
    cur.execute("DROP TABLE IF EXISTS tmp_sd_price")
    cur.execute(f"""
        CREATE TABLE tmp_sd_price ENGINE=InnoDB AS
        SELECT p.product_code,
               COALESCE(b.price, g.price, o.price) AS price,
               CASE WHEN b.price IS NOT NULL THEN 'purchase_price'
                    WHEN g.price IS NOT NULL THEN 'purchase_price_group'
                    WHEN o.price IS NOT NULL THEN 'other_branch_cost' ELSE 'no_price' END AS method,
               b.price AS branch_price, g.price AS group_price
        FROM (SELECT DISTINCT product_code FROM {target} WHERE company_source_key = %s AND source_system = 'odoo') p
        LEFT JOIN (SELECT product_code, SUM(total_cost) / SUM(quantity) AS price FROM {MOVES}
                   WHERE company_source_key = %s AND source_system = 'odoo' AND movement_type = 'purchase_receipt'
                     AND quantity > 0 AND total_cost > 0 AND movement_date BETWEEN %s AND %s
                   GROUP BY product_code) b ON b.product_code = p.product_code
        LEFT JOIN (SELECT product_code, SUM(total_cost) / SUM(quantity) AS price FROM {MOVES}
                   WHERE source_system = 'odoo' AND movement_type = 'purchase_receipt'
                     AND quantity > 0 AND total_cost > 0 AND movement_date BETWEEN %s AND %s
                   GROUP BY product_code) g ON g.product_code = p.product_code
        LEFT JOIN (SELECT product_code, SUM(total_cost) / SUM(quantity) AS price FROM {MOVES}
                   WHERE source_system = 'odoo' AND company_source_key <> %s AND counts_in_stock = 1
                     AND quantity > 0 AND total_cost > 0 AND total_cost < {UNIT_VALUE_LIMIT} * quantity
                     AND movement_date BETWEEN %s AND %s
                   GROUP BY product_code) o ON o.product_code = p.product_code
    """, (key, key, since, yesterday, since, yesterday, key, since, yesterday))
    cur.execute("ALTER TABLE tmp_sd_price ADD PRIMARY KEY (product_code)")
    cur.execute(f"""
        UPDATE {target} s JOIN tmp_sd_price p ON p.product_code = s.product_code
        SET s.stock_value = IF(p.price IS NULL, NULL, ROUND(s.stock_qty * p.price, 4)), s.value_method = p.method
        WHERE s.company_source_key = %s AND s.source_system = 'odoo' AND {WRONG_VALUE_SQL}
    """, (key,))
    corrected = cur.rowcount

    cur.execute(EXCEPTIONS_DDL)
    cur.execute(f"DELETE FROM {EXCEPTIONS} WHERE company_source_key = %s", (key,))
    ratio = "s.stock_value_source / s.stock_qty / COALESCE(p.branch_price, p.group_price)"
    cur.execute(f"""
        INSERT INTO {EXCEPTIONS} (company_source_key, product_code, product_name, stock_date, stock_qty,
               stock_value_source, unit_value_source, unit_price, stock_value, value_method, reason, built_at)
        SELECT s.company_source_key, s.product_code, s.product_name, s.stock_date, s.stock_qty,
               s.stock_value_source, ROUND(s.stock_value_source / s.stock_qty, 4), p.price, s.stock_value,
               s.value_method,
               IF({WRONG_VALUE_SQL}, {WRONG_REASON_SQL}, 'revisar: costo fuera de 0.2x-5x de su compra'), %s
        FROM {target} s JOIN tmp_sd_price p ON p.product_code = s.product_code
        WHERE s.company_source_key = %s AND s.source_system = 'odoo' AND s.stock_date = %s
          AND ({WRONG_VALUE_SQL} OR (ABS(s.stock_qty) > {ZERO} AND COALESCE(p.branch_price, p.group_price) > 0
               AND ({ratio} > 5 OR {ratio} < 0.2)))
    """, (built_at, key, yesterday))
    listed = cur.rowcount
    if listed:
        cur.execute(f"""SELECT SUM(value_method <> 'source'), SUM(value_method = 'no_price'),
                               COALESCE(SUM(stock_value_source), 0), COALESCE(SUM(stock_value), 0)
                        FROM {EXCEPTIONS} WHERE company_source_key = %s""", (key,))
        fixed, no_price, before, after = cur.fetchone()
        print(f"[AVISO] valor de inventario de Odoo corregido en {key}: {int(fixed or 0)} productos al {yesterday} "
              f"({int(no_price or 0)} sin precio), {listed - int(fixed or 0)} solo por revisar; "
              f"valor de Odoo {float(before):,.2f} -> corregido {float(after):,.2f} "
              f"(lista en {EXCEPTIONS}; {corrected:,} días-producto corregidos en la serie)")


HELPERS = ("tmp_sd_nets", "tmp_sd_products", "tmp_sd_capture", "tmp_sd_price")


def ensure_new_columns(cur):
    """The live table built before 2026-11-12 gets the value-correction columns (no-op afterwards)."""
    for column in NEW_COLUMNS:
        cur.execute(f"ALTER TABLE {TABLE} ADD COLUMN IF NOT EXISTS {column}")


def drop_helpers(cur):
    # Regular tables, not TEMPORARY: MariaDB cannot open a temporary table twice
    # in one statement, and the Odoo steps join these tables with themselves.
    for name in HELPERS:
        cur.execute(f"DROP TABLE IF EXISTS {name}")


def nightly_branch(cur, key, odoo_start, born, yesterday, built_at):
    """
    Update the live table in place for one branch: the Wansoft series from the
    oldest day touched by movements captured in the movements' nightly window (or
    the day after the last stored day), the Odoo series rebuilt whole (it is
    short: from October 2026 for the migrated branches, from June for Puebla and
    CentroMyJ, and its days move with every new capture).
    """
    wansoft_from = None
    if not born:
        last_built = fetch(cur, f"SELECT MAX(stock_date) FROM {TABLE} WHERE company_source_key = %s "
                                f"AND source_system = 'wansoft'", (key,))[0][0]
        touched = fetch(cur, f"""
            SELECT MIN(movement_date) FROM {MOVES}
            WHERE company_source_key = %s AND source_system = 'wansoft' AND counts_in_stock = 1
              AND include_in_business_views = 1 AND captured_date >= %s""",
                        (key, date.today() - timedelta(days=MOVEMENTS_WINDOW_DAYS)))[0][0]
        if last_built is not None:
            wansoft_from = min(d for d in (touched, last_built + timedelta(days=1)) if d is not None)
            cur.execute(f"DELETE FROM {TABLE} WHERE company_source_key = %s AND source_system = 'wansoft' "
                        f"AND stock_date >= %s", (key, wansoft_from))
        else:
            cur.execute(f"DELETE FROM {TABLE} WHERE company_source_key = %s AND source_system = 'wansoft'", (key,))
        if odoo_start:
            # Late cutover: the policy row may land after nights that already stored
            # the start day onwards as Wansoft; those days belong to Odoo now, and
            # the history before them is no longer final (no-ops once applied). Days
            # after yesterday are dropped too (a series is never built into the future).
            cur.execute(f"DELETE FROM {TABLE} WHERE company_source_key = %s AND source_system = 'wansoft' "
                        f"AND stock_date >= %s", (key, min(odoo_start, yesterday + timedelta(days=1))))
            cur.execute(f"UPDATE {TABLE} SET final_source_status = 'wansoft_history_before_odoo' "
                        f"WHERE company_source_key = %s AND source_system = 'wansoft' "
                        f"AND final_source_status = 'wansoft_final'", (key,))
    if odoo_start or born:
        cur.execute(f"DELETE FROM {TABLE} WHERE company_source_key = %s AND source_system = 'odoo'", (key,))
    rows = build_branch(cur, key, odoo_start, born, yesterday, built_at, target=TABLE, wansoft_from=wansoft_from)
    return rows, wansoft_from


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="+", help="company_source_key values to build (default: every branch)")
    parser.add_argument("--full", action="store_true",
                        help="rebuild everything into a new table and swap it in (first load, or to start over); "
                             "without it, the nightly update of the live table")
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
        if not args.full:
            if not fetch(cur, "SHOW TABLES LIKE %s", (TABLE,)):
                raise SystemExit(f"{TABLE} does not exist yet: run once with --full")
            ensure_new_columns(cur)
            total = 0
            for key in branches:
                started = time.time()
                odoo_start, born = plan.get(key, (None, False))
                rows, since = nightly_branch(cur, key, odoo_start, born, yesterday, built_at)
                conn.commit()
                total += rows
                print(f"  {key}: {rows:,} filas desde {since or 'el inicio'} ({time.time() - started:.0f} s)")
            drop_helpers(cur)
            print(f"{TABLE}: {total:,} filas reescritas (actualización nocturna)")
            return 0
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
