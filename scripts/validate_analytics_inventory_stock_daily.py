"""
Validate analytics_inventory_stock_daily (read-only; design:
docs/analytics-inventory-unified-design.md, Table 2 and build order step 4).

Checks:
- per branch: rows, first and last day, source systems, built_at;
- no gaps: every branch x product x source series has one row per day from its
  first day to its last, and ends on yesterday (the Wansoft series of a branch
  migrated to Odoo ends the day before its Odoo start);
- Wansoft branches: stock of the last day = analytics_inventory_balance;
- Odoo branches: stock on the latest capture day = odoo_inventory_quant_daily
  (internal locations, product code through analytics_odoo_product_code).

Only SELECTs; safe against production from the dev PC:

    $env:ENV = 'prod'; python -m scripts.validate_analytics_inventory_stock_daily
"""
import argparse
from datetime import date, timedelta

import pandas as pd

from core.database.mysql import get_db_connection
from scripts.build_analytics_inventory_stock_daily import QUANTS, CODES, TABLE, branch_plan

TOLERANCE = 0.001


def query_df(conn, sql, params=None):
    cur = conn.cursor()
    cur.execute(sql, params or ())
    cols = [c[0] for c in cur.description]
    rows = cur.fetchall()
    cur.close()
    return pd.DataFrame(rows, columns=cols)


def check_gaps(conn, plan, yesterday):
    series = query_df(conn, f"""
        SELECT company_source_key, source_system, product_code,
               MIN(stock_date) AS first_d, MAX(stock_date) AS last_d, COUNT(*) AS n
        FROM {TABLE} GROUP BY company_source_key, source_system, product_code
    """)
    series["expected"] = (pd.to_datetime(series["last_d"]) - pd.to_datetime(series["first_d"])).dt.days + 1
    gaps = series[series["n"] != series["expected"]]

    def expected_end(row):
        odoo_start, born = plan.get(row.company_source_key, (None, False))
        if row.source_system == "wansoft" and odoo_start:
            return min(odoo_start - timedelta(days=1), yesterday)
        return yesterday

    series["expected_end"] = series.apply(expected_end, axis=1)
    short = series[series["last_d"] != series["expected_end"]]
    print(f"\n[1] Series branch x product x source: {len(series):,}; with gaps: {len(gaps):,}; "
          f"not ending on the expected day: {len(short):,}")
    if len(gaps):
        print(gaps.head(20).to_string(index=False))
    if len(short):
        print(short.groupby(["company_source_key", "source_system", "expected_end", "last_d"])
              .size().rename("series").reset_index().to_string(index=False))
    return len(gaps) == 0 and len(short) == 0


def check_wansoft_balance(conn, plan):
    keys = [k for k in query_df(conn, f"SELECT DISTINCT company_source_key FROM {TABLE} "
                                      "WHERE source_system = 'wansoft'")["company_source_key"]
            if k not in plan]
    print(f"\n[2] Wansoft branches: last day vs analytics_inventory_balance ({len(keys)} branches)")
    ok = True
    for key in keys:
        df = query_df(conn, f"""
            SELECT COALESCE(s.product_code, b.wansoft_code) AS product_code,
                   s.stock_qty, b.current_balance_qty
            FROM (SELECT product_code, stock_qty FROM {TABLE}
                  WHERE company_source_key = %s AND source_system = 'wansoft'
                    AND stock_date = (SELECT MAX(stock_date) FROM {TABLE}
                                      WHERE company_source_key = %s AND source_system = 'wansoft')) s
            LEFT JOIN analytics_inventory_balance b
                   ON b.company_source_key = %s AND b.source_system = 'wansoft' AND b.wansoft_code = s.product_code
            UNION ALL
            SELECT b.wansoft_code, NULL, b.current_balance_qty
            FROM analytics_inventory_balance b
            WHERE b.company_source_key = %s AND b.source_system = 'wansoft' AND b.include_in_business_views = 1
              AND ABS(b.current_balance_qty) > {TOLERANCE}
              AND NOT EXISTS (SELECT 1 FROM {TABLE} s WHERE s.company_source_key = b.company_source_key
                              AND s.source_system = 'wansoft' AND s.product_code = b.wansoft_code)
        """, (key, key, key, key))
        daily = df["stock_qty"].astype(float).fillna(0)
        bal = df["current_balance_qty"].astype(float).fillna(0)
        diff = df[(daily - bal).abs() > TOLERANCE]
        ok &= diff.empty
        print(f"  {key}: {len(df) - len(diff):,}/{len(df):,} equal"
              + (f"; differ: {len(diff)} (e.g. {diff.head(3).to_dict('records')})" if len(diff) else ""))
    return ok


def check_odoo_capture(conn, plan, yesterday):
    print("\n[3] Odoo branches: stock on the latest capture day vs odoo_inventory_quant_daily (internal)")
    ok = True
    for key in sorted(plan):
        capture = query_df(conn, f"SELECT MAX(stock_date) AS d FROM {QUANTS} "
                                 "WHERE company_source_key = %s AND stock_date <= %s", (key, yesterday))["d"][0]
        if capture is None:
            print(f"  {key}: no capture")
            continue
        df = query_df(conn, f"""
            SELECT a.product_code, s.stock_qty, c.qty
            FROM (SELECT product_code FROM {TABLE} WHERE company_source_key = %s AND source_system = 'odoo'
                    AND stock_date = %s
                  UNION
                  SELECT COALESCE(m.wansoft_code, CONCAT('ODOO-', q.odoo_product_id)) FROM {QUANTS} q
                  LEFT JOIN {CODES} m ON m.odoo_product_id = q.odoo_product_id
                  WHERE q.company_source_key = %s AND q.stock_date = %s AND q.location_usage = 'internal') a
            LEFT JOIN {TABLE} s ON s.company_source_key = %s AND s.source_system = 'odoo'
                   AND s.stock_date = %s AND s.product_code = a.product_code
            LEFT JOIN (SELECT COALESCE(m.wansoft_code, CONCAT('ODOO-', q.odoo_product_id)) AS product_code,
                              SUM(q.quantity) AS qty
                       FROM {QUANTS} q LEFT JOIN {CODES} m ON m.odoo_product_id = q.odoo_product_id
                       WHERE q.company_source_key = %s AND q.stock_date = %s AND q.location_usage = 'internal'
                       GROUP BY 1) c ON c.product_code = a.product_code
        """, (key, capture, key, capture, key, capture, key, capture))
        diff = df[(df["stock_qty"].astype(float).fillna(0) - df["qty"].astype(float).fillna(0)).abs() > TOLERANCE]
        ok &= diff.empty
        print(f"  {key} ({capture}): {len(df) - len(diff):,}/{len(df):,} equal"
              + (f"; differ: {len(diff)} (e.g. {diff.head(3).to_dict('records')})" if len(diff) else ""))
    return ok


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--yesterday", type=date.fromisoformat,
                        help="last day the table should reach (default: yesterday)")
    args = parser.parse_args(argv)
    yesterday = args.yesterday or date.today() - timedelta(days=1)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        plan = branch_plan(cur)
        cur.close()
        summary = query_df(conn, f"""
            SELECT company_source_key, GROUP_CONCAT(DISTINCT source_system) AS sources, COUNT(*) AS filas,
                   MIN(stock_date) AS desde, MAX(stock_date) AS hasta, MAX(built_at) AS built_at
            FROM {TABLE} GROUP BY company_source_key
        """)
        print(f"{TABLE}: {summary['filas'].sum():,} rows, {len(summary)} branches (expected last day {yesterday})")
        print(summary.to_string(index=False))
        results = [check_gaps(conn, plan, yesterday), check_wansoft_balance(conn, plan),
                   check_odoo_capture(conn, plan, yesterday)]
        print("\nRESULT:", "OK" if all(results) else "DIFFERENCES (see above)")
        return 0 if all(results) else 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
