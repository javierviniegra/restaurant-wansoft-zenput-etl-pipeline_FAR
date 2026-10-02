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
never goes back by itself; to undo it, delete the branch's row from
costs_odoo_switch (the next night recomputes the window from Wansoft).

Month/week to date across a mid-period switch (owner, 2026-10-02, "D1"):
the accumulated rows on Odoo days add the Wansoft accumulation of the same
period up to the day before the switch (wansoft_period_base), so a month
reads Wansoft days 1..switch-1 + Odoo days switch..D, each day exactly once.
check_cost_continuity proves it: no duplicate rows, and on every Odoo day the
accumulated value grows by exactly that day's cost.

Pieces: detect() decides; record_switch()/load_switch_dates() persist it
(extract/costs/cost_routing.py routes on it); pipelines/jobs/costs_switch_job.py
runs it nightly, backfills and validates.

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


SWITCH_TABLE_DDL = """
    CREATE TABLE IF NOT EXISTS costs_odoo_switch (
        company_source_key VARCHAR(100) NOT NULL PRIMARY KEY,
        switch_date DATE NOT NULL,
        detected_at DATETIME NOT NULL,
        evidence VARCHAR(500),
        backfilled_at DATETIME NULL,
        validated_at DATETIME NULL,
        validation_result VARCHAR(500) NULL
    )
"""


def ensure_switch_table(conn):
    cur = conn.cursor()
    cur.execute(SWITCH_TABLE_DDL)
    conn.commit()


def load_switch_dates(conn):
    """{company_source_key: switch_date}; empty if the table does not exist yet."""
    cur = conn.cursor()
    try:
        cur.execute("SELECT company_source_key, switch_date FROM costs_odoo_switch")
    except Exception:
        return {}
    return {k: d for k, d in cur.fetchall()}


def record_switch(conn, company_key, switch_date, evidence):
    text = "; ".join(f"{d}: odoo {o:,.2f} / wansoft {w:,.2f}" for d, o, w in evidence)[:500]
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO costs_odoo_switch (company_source_key, switch_date, detected_at, evidence) VALUES (%s, %s, NOW(), %s)",
        (company_key, switch_date, text),
    )
    conn.commit()


def _as_date(value):
    return value.date() if isinstance(value, datetime) else value


def wansoft_period_base(cursor, table, subsidiary_id, odoo_start, day):
    """
    Wansoft's accumulated (CostoTotal without consumo, CostoDeProductosVendidos,
    CostoDeMerma) for the part of `day`'s month or ISO week before odoo_start;
    zeros when odoo_start opens the period. `day` is an Odoo-sourced day.

    costeomensual: the row dated odoo_start - 1 holds month-to-date through it.
    costeomensual_semanapyq: its rows are dated one day after the last day they
    cover (Monday..created_date-1), so the row dated odoo_start holds the week
    through odoo_start - 1.
    """
    day, odoo_start = _as_date(day), _as_date(odoo_start)
    if table == "costeomensual":
        if odoo_start <= day.replace(day=1):
            return 0.0, 0.0, 0.0
        base_row_date = odoo_start - timedelta(days=1)
    elif table == "costeomensual_semanapyq":
        if odoo_start <= day - timedelta(days=day.weekday()):
            return 0.0, 0.0, 0.0
        base_row_date = odoo_start
    else:
        raise ValueError(table)
    cursor.execute(
        f"SELECT CostoTotal - COALESCE(CostoDeConsumo, 0), CostoDeProductosVendidos, COALESCE(CostoDeMerma, 0) "
        f"FROM {table} WHERE subsidiary_id = %s AND DATE(created_at) = %s",
        (subsidiary_id, base_row_date),
    )
    rows = cursor.fetchall()  # fetchall: the caller's cursor must be left with no unread result
    row = rows[0] if rows else None
    if row is None:
        print(f"[AVISO] {table}: falta el acumulado de Wansoft del {base_row_date} (sucursal {subsidiary_id}); "
              f"el acumulado de Odoo de {day} queda sin la parte anterior al cambio")
        return 0.0, 0.0, 0.0
    return tuple(float(v or 0) for v in row)


def check_cost_continuity(conn, subsidiary_id, odoo_start, through, from_day=None):
    """
    Problems (list of strings, empty = fine) for one branch from odoo_start's
    month through `through`: duplicate (branch, day) rows in the three cost
    tables, and Odoo days whose accumulated month/week value does not grow by
    exactly that day's cost (gettotalcostbydate) -- a day counted twice, a
    reset at the switch or a missing piece would all show up here.
    from_day (optional) starts the check later than odoo_start, e.g. only the
    nightly window of a branch that has been on Odoo for months.
    """
    odoo_start, through = _as_date(odoo_start), _as_date(through)
    if from_day is not None:
        odoo_start = max(odoo_start, _as_date(from_day))
    problems = []
    cur = conn.cursor()
    since = odoo_start.replace(day=1) - timedelta(days=7)
    for table in ("costeomensual", "costeomensual_semanapyq", "gettotalcostbydate"):
        cur.execute(f"SELECT DATE(created_at), COUNT(*) FROM {table} WHERE subsidiary_id = %s AND created_at >= %s "
                    f"GROUP BY DATE(created_at) HAVING COUNT(*) > 1", (subsidiary_id, since))
        for d, n in cur.fetchall():
            problems.append(f"{table}: {n} renglones el {d}")

    cur.execute("SELECT DATE(created_at), CostoTotalVenta FROM gettotalcostbydate WHERE subsidiary_id = %s "
                "AND created_at >= %s AND created_at < %s", (subsidiary_id, odoo_start, through + timedelta(days=1)))
    daily = {d: float(v or 0) for d, v in cur.fetchall()}

    def accumulated(table, first, last):
        cur.execute(f"SELECT DATE(created_at), CostoTotal - COALESCE(CostoDeConsumo, 0) FROM {table} "
                    f"WHERE subsidiary_id = %s AND created_at >= %s AND created_at < %s",
                    (subsidiary_id, first, last + timedelta(days=1)))
        return {d: float(v or 0) for d, v in cur.fetchall()}

    month = accumulated("costeomensual", odoo_start.replace(day=1), through)
    week = accumulated("costeomensual_semanapyq", odoo_start - timedelta(days=8), through + timedelta(days=1))
    day = odoo_start
    while day <= through:
        if day in daily:
            # Month: row of `day` minus the row of the previous day in the same month (0 on day 1).
            prev = day - timedelta(days=1)
            prev_value = 0.0 if day.day == 1 else month.get(prev)
            if day in month and prev_value is not None and abs(month[day] - prev_value - daily[day]) > 1.0:
                problems.append(f"mensual {day}: sube {month[day] - prev_value:,.2f} y el costo del día es {daily[day]:,.2f}")
            if day not in month and daily[day] > 0:
                problems.append(f"mensual {day}: falta el renglón (hay costo del día {daily[day]:,.2f})")
            # Week (rows dated +1 day): row day+1 minus row day (0 when `day` is Monday).
            cur_row, prev_row = day + timedelta(days=1), day
            prev_w = 0.0 if day.weekday() == 0 else week.get(prev_row)
            if cur_row in week and prev_w is not None and abs(week[cur_row] - prev_w - daily[day]) > 1.0:
                problems.append(f"semanal {day}: sube {week[cur_row] - prev_w:,.2f} y el costo del día es {daily[day]:,.2f}")
        day += timedelta(days=1)
    return problems


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
