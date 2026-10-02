"""
Automatic switch of a branch's costs from Wansoft to Odoo (owner, 2026-10-02).

Branches in COSTS_AUTO_SWITCH_TO_ODOO (core/config/companies.py) run on Odoo
for purchases but cannot post cost of sales there yet (the October wave waits
for its opening inventory balances), so their costs stay on Wansoft until
Odoo really has data for them. Each branch switches on its own day, without
anyone editing code.

Detection rule (owner-approved):
  - look at every day from the branch's Odoo start date through yesterday;
  - a day "has Odoo cost" when Odoo's daily cost of sales (CostoTotal from
    extract/costs/odoo_cost_report.get_daily_cost) is > 0 AND lies between
    half and double the Wansoft cost stored for that day
    (gettotalcostbydate.CostoTotalVenta), so a test entry or a stray
    adjustment cannot trigger it;
  - the switch date is the FIRST of two consecutive days that both qualify.
Days before the switch date stay on Wansoft; from it on, Odoo. The switch
never goes back by itself.

This module only decides; recording the decision and routing on it are
separate steps.

    python -m extract.costs.cost_switch [--prod] [--branches "Acoxpa"] [--from 2026-06-01]

prints what the rule decides today, read-only (Odoo search_read and SELECT).
--prod reads the production warehouse (WANSOFT_DB_*) instead of the one
ENV points at.
"""
from __future__ import annotations

import argparse
import os
from datetime import date, datetime, timedelta

from core.config.companies import COMPANY_SOURCE, WANSOFT_SUBSIDIARY_SOURCE_KEY
from core.database.odoo import get_odoo_connection
from extract.costs.odoo_cost_report import get_daily_cost, resolve_odoo_company_id

MIN_RATIO = 0.5
MAX_RATIO = 2.0
CONSECUTIVE_DAYS = 2


def qualifies(odoo_cost, wansoft_cost):
    """True when this day's Odoo cost is real and plausible against Wansoft's."""
    if not odoo_cost or odoo_cost <= 0 or not wansoft_cost or wansoft_cost <= 0:
        return False
    return MIN_RATIO <= odoo_cost / wansoft_cost <= MAX_RATIO


def find_switch_date(odoo_daily, wansoft_daily, first_day, last_day):
    """
    odoo_daily / wansoft_daily: {date: cost}. Returns (switch_date, evidence)
    or (None, None). evidence lists the qualifying days with both costs.
    """
    day = first_day
    while day + timedelta(days=CONSECUTIVE_DAYS - 1) <= last_day:
        run = [day + timedelta(days=i) for i in range(CONSECUTIVE_DAYS)]
        if all(qualifies(odoo_daily.get(d), wansoft_daily.get(d)) for d in run):
            return day, [(d, odoo_daily[d], wansoft_daily[d]) for d in run]
        day += timedelta(days=1)
    return None, None


def wansoft_subsidiary_id(company_key):
    for sid, key in WANSOFT_SUBSIDIARY_SOURCE_KEY.items():
        if key == company_key:
            return int(sid)
    return None


def load_wansoft_daily(conn, subsidiary_id, first_day, last_day):
    cur = conn.cursor()
    cur.execute(
        "SELECT DATE(created_at), CostoTotalVenta FROM gettotalcostbydate "
        "WHERE subsidiary_id = %s AND created_at >= %s AND created_at < %s",
        (subsidiary_id, first_day, last_day + timedelta(days=1)),
    )
    return {d: float(v or 0) for d, v in cur.fetchall()}


def load_odoo_daily(odoo, company_key, first_day, last_day):
    uid, models, db, password = odoo
    company_id = resolve_odoo_company_id(models, uid, db, password, company_key)
    if company_id is None:
        return None
    df = get_daily_cost(models, uid, db, password, company_id, str(first_day), str(last_day))
    return {date.fromisoformat(str(r.fecha)[:10]): float(r.CostoTotal) for r in df.itertuples()}


def detect(company_key, start_date, conn, odoo, through=None):
    """Decision for one branch: dict with switch_date (or None), evidence and the days looked at."""
    last_day = through or (date.today() - timedelta(days=1))
    sid = wansoft_subsidiary_id(company_key)
    odoo_daily = load_odoo_daily(odoo, company_key, start_date, last_day)
    if sid is None or odoo_daily is None:
        return {"branch": company_key, "error": "sin id de Wansoft o de Odoo"}
    wansoft_daily = load_wansoft_daily(conn, sid, start_date, last_day)
    switch, evidence = find_switch_date(odoo_daily, wansoft_daily, start_date, last_day)
    return {
        "branch": company_key,
        "switch_date": switch,
        "evidence": evidence,
        "days": [(d, odoo_daily.get(d), wansoft_daily.get(d))
                 for d in (start_date + timedelta(days=i) for i in range((last_day - start_date).days + 1))],
    }


def _production_connection():
    import mysql.connector
    return mysql.connector.connect(
        host=os.getenv("WANSOFT_DB_HOST"), port=int(os.getenv("WANSOFT_DB_PORT") or 3306),
        user=os.getenv("WANSOFT_DB_USER"), password=os.getenv("WANSOFT_DB_PASSWORD"),
        database=os.getenv("WANSOFT_DB_NAME"),
    )


def main(argv=None):
    from core.config.companies import COSTS_AUTO_SWITCH_TO_ODOO
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--prod", action="store_true", help="read the production warehouse (WANSOFT_DB_*)")
    parser.add_argument("--branches", help="comma-separated short keys (default: COSTS_AUTO_SWITCH_TO_ODOO)")
    parser.add_argument("--from", dest="date_from", help="first day to look at (default: each branch's Odoo start date)")
    args = parser.parse_args(argv)

    if args.prod:
        conn = _production_connection()
    else:
        from core.database.mysql import get_db_connection
        conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT company_name, operational_start_date FROM odoo_company_migration_policy WHERE is_active = 1")
    from core.config.companies import ODOO_COMPANY_SOURCE_KEY
    starts = {ODOO_COMPANY_SOURCE_KEY.get(n): s for n, s in cur.fetchall() if ODOO_COMPANY_SOURCE_KEY.get(n)}

    branches = [b.strip() for b in args.branches.split(",")] if args.branches else sorted(COSTS_AUTO_SWITCH_TO_ODOO)
    odoo = get_odoo_connection()
    print(f"Regla: {CONSECUTIVE_DAYS} días seguidos con costo de Odoo > 0 y entre {MIN_RATIO}x y {MAX_RATIO}x el de Wansoft")
    for key in branches:
        if COMPANY_SOURCE.get(key) != "odoo":
            print(f"\n{key}: no es sucursal de Odoo, se ignora")
            continue
        first = date.fromisoformat(args.date_from) if args.date_from else starts.get(key)
        if first is None:
            print(f"\n{key}: sin fecha de arranque en la política")
            continue
        result = detect(key, first, conn, odoo)
        print(f"\n{key} (desde {first}):")
        if "error" in result:
            print(f"  {result['error']}")
            continue
        shown = [d for d in result["days"] if d[1] or result["switch_date"] is None or abs((d[0] - result["switch_date"]).days) <= 3]
        for d, o, w in shown[-15:]:
            mark = "  <- califica" if qualifies(o, w) else ""
            ratio = f"{o / w:.2f}x" if o and w else "-"
            print(f"  {d}  odoo={o or 0:>12,.2f}  wansoft={w or 0:>12,.2f}  {ratio:>6}{mark}")
        if result["switch_date"]:
            print(f"  => CAMBIARÍA A ODOO DESDE {result['switch_date']}")
        else:
            print("  => SIGUE EN WANSOFT (Odoo todavía no cumple la regla)")
    conn.close()


if __name__ == "__main__":
    main()
