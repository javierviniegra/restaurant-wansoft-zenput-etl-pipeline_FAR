"""
Costs-domain routing, per branch AND per day.

Rule (owner, 2026-09-29): a branch that operates on Odoo takes its costs from
Odoo (extract/costs/odoo_cost_report.py) from its Odoo start date on, and from
Wansoft's cost report before it; branches still on Wansoft always use Wansoft.
COSTS_WANSOFT_TEMPORARY_EXCEPTIONS (core/config/companies.py) keeps listed
branches on Wansoft regardless (Antenas: its Odoo cost data is broken by the
pilot-era tests while that database is repaired).

Why per day and not per branch: the cost scripts re-check the last
COSTS_LOOKBACK_DAYS every night. The day after a branch's cutover, a
per-branch switch would recompute its pre-cutover days from Odoo, whose data
before the start date is pilot noise or empty, overwriting good Wansoft
snapshots. Start dates come from odoo_company_migration_policy, the same
table the purchases layer uses.

Branches in COSTS_AUTO_SWITCH_TO_ODOO (2026-10-02) take Odoo costs only from
the switch date that extract/costs/cost_switch.py detected and recorded in
costs_odoo_switch (never before their policy start date); until a switch is
recorded they stay on Wansoft.
"""
import os
from datetime import date, datetime, timedelta

from core.config.companies import (
    COMPANY_SOURCE,
    COSTS_AUTO_SWITCH_TO_ODOO,
    COSTS_WANSOFT_TEMPORARY_EXCEPTIONS,
    ODOO_COMPANY_SOURCE_KEY,
)
from core.database.mysql import get_db_connection

# Start date of an auto-switch branch with no switch detected yet: no day is on Odoo.
NOT_SWITCHED = date.max

# Odoo's cost of a day comes from that day's customer invoices, and those keep
# being created for up to ~2 weeks, the rest at the month-end closing
# (measured 2026-10-05 on September: 40-70% invoiced one day later, 70-100%
# after 7 days, 92-100% after 14, all of it by the close). So the Odoo side
# re-reads the whole current month every night and, during the first
# ODOO_COSTS_PREVIOUS_MONTH_DAYS days of a month, the whole previous month too,
# so the closing always reaches the stored costs.
ODOO_COSTS_PREVIOUS_MONTH_DAYS = 10


def odoo_costs_window_start(window_start, today=None):
    """First day the Odoo-sourced costs are recomputed tonight; never later than window_start."""
    today = today or datetime.now()
    first = datetime(today.year, today.month, 1)
    if today.day <= ODOO_COSTS_PREVIOUS_MONTH_DAYS:
        first = (first - timedelta(days=1)).replace(day=1)
    return min(window_start, first)


def load_costs_odoo_start_dates():
    """{company_source_key: first day on Odoo costs}: the policy start date, or the detected switch date."""
    from extract.costs.cost_switch import load_switch_dates
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT company_name, operational_start_date FROM odoo_company_migration_policy WHERE is_active = 1"
        )
        rows = cur.fetchall()
        switches = load_switch_dates(conn)
    finally:
        conn.close()
    start_dates = {}
    for company_name, start in rows:
        key = ODOO_COMPANY_SOURCE_KEY.get(company_name)
        if key and start:
            start_dates[key] = start
    for key in COSTS_AUTO_SWITCH_TO_ODOO:
        switch = switches.get(key)
        policy_start = start_dates.get(key)
        if switch is None or policy_start is None:
            start_dates[key] = NOT_SWITCHED
        else:
            start_dates[key] = max(switch, policy_start)
    return start_dates


COSTS_SOURCE_TABLE_DDL = """
    CREATE TABLE IF NOT EXISTS costs_source_by_company (
        company_source_key VARCHAR(100) NOT NULL PRIMARY KEY,
        wansoft_subsidiary_id INT NULL,
        odoo_company_id INT NULL,
        odoo_cost_start_date DATE NULL,
        reason VARCHAR(30) NOT NULL,
        updated_at DATETIME NOT NULL
    )
"""


def costs_source_rows(start_dates, odoo_company_ids):
    """
    One row per branch with the rule costs_source() applies: the first day its
    cost comes from Odoo (None = always Wansoft) and why:
      wansoft             branch on Wansoft (COMPANY_SOURCE)
      exception           COSTS_WANSOFT_TEMPORARY_EXCEPTIONS (Antenas)
      auto_switch_pending COSTS_AUTO_SWITCH_TO_ODOO, Odoo has no cost data yet
      switched            COSTS_AUTO_SWITCH_TO_ODOO, switch recorded in costs_odoo_switch
      policy              odoo_company_migration_policy start date
      no_policy           Odoo branch without a policy row (stays on Wansoft)
    """
    from core.config.companies import WANSOFT_SUBSIDIARY_SOURCE_KEY
    sid_by_key = {k: int(s) for s, k in WANSOFT_SUBSIDIARY_SOURCE_KEY.items()}
    rows = []
    for key in sorted(set(COMPANY_SOURCE) | set(sid_by_key)):
        start = start_dates.get(key)
        if COMPANY_SOURCE.get(key, "wansoft") != "odoo":
            start, reason = None, "wansoft"
        elif key in COSTS_WANSOFT_TEMPORARY_EXCEPTIONS:
            start, reason = None, "exception"
        elif key in COSTS_AUTO_SWITCH_TO_ODOO:
            reason = "auto_switch_pending" if start in (None, NOT_SWITCHED) else "switched"
            start = None if reason == "auto_switch_pending" else start
        elif start is None:
            reason = "no_policy"
        else:
            reason = "policy"
        rows.append((key, sid_by_key.get(key), odoo_company_ids.get(key), start, reason))
    return rows


def publish_costs_source_table(conn):
    """Rewrites costs_source_by_company (read by Central de Reportes) from the current routing."""
    cur = conn.cursor()
    cur.execute(COSTS_SOURCE_TABLE_DDL)
    cur.execute("SELECT company_name, odoo_company_id FROM odoo_company_migration_policy WHERE is_active = 1")
    odoo_ids = {ODOO_COMPANY_SOURCE_KEY.get(n): i for n, i in cur.fetchall() if ODOO_COMPANY_SOURCE_KEY.get(n)}
    rows = costs_source_rows(load_costs_odoo_start_dates(), odoo_ids)
    cur.execute("DELETE FROM costs_source_by_company")
    cur.executemany(
        "INSERT INTO costs_source_by_company (company_source_key, wansoft_subsidiary_id, odoo_company_id, "
        "odoo_cost_start_date, reason, updated_at) VALUES (%s, %s, %s, %s, %s, NOW())", rows)
    conn.commit()
    return rows


def costs_source(company_key, day, start_dates):
    """'odoo' or 'wansoft' for this branch's cost on `day` (date or datetime)."""
    if isinstance(day, datetime):
        day = day.date()
    if COMPANY_SOURCE.get(company_key, "wansoft") != "odoo":
        return "wansoft"
    if company_key in COSTS_WANSOFT_TEMPORARY_EXCEPTIONS:
        return "wansoft"
    start = start_dates.get(company_key)
    if start is None:
        # An Odoo branch must have a migration policy row; without it we cannot
        # tell where its history ends, so keep Wansoft rather than guess.
        print(f"[⚠] Sin fecha de arranque en odoo_company_migration_policy para {company_key}: costos desde Wansoft")
        return "wansoft"
    return "odoo" if day >= start else "wansoft"


def split_subsidiaries(subsidiaries, window_start, window_end, start_dates):
    """
    (wansoft_list, odoo_list): a branch is in a list if any day of the window uses that source.

    COSTS_ONLY_BRANCHES (optional env var, comma-separated short keys) limits a
    run to those branches: used for one-off backfills with a long
    COSTS_LOOKBACK_DAYS, e.g. Puebla and CentroMyJ at the cutover, without
    re-asking Wansoft for months of every other branch. Unset in the nightly run.
    """
    only = {b.strip() for b in os.getenv("COSTS_ONLY_BRANCHES", "").split(",") if b.strip()}
    if only:
        subsidiaries = [s for s in subsidiaries if s["nombreCorto"] in only]
        print(f"[COSTS_ONLY_BRANCHES] limitado a: {sorted(s['nombreCorto'] for s in subsidiaries)}")
    wansoft, odoo = [], []
    for s in subsidiaries:
        if costs_source(s["nombreCorto"], window_start, start_dates) == "wansoft":
            wansoft.append(s)
        if costs_source(s["nombreCorto"], window_end, start_dates) == "odoo":
            odoo.append(s)
    return wansoft, odoo
