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
from datetime import date, datetime

from core.config.companies import (
    COMPANY_SOURCE,
    COSTS_AUTO_SWITCH_TO_ODOO,
    COSTS_WANSOFT_TEMPORARY_EXCEPTIONS,
    ODOO_COMPANY_SOURCE_KEY,
)
from core.database.mysql import get_db_connection

# Start date of an auto-switch branch with no switch detected yet: no day is on Odoo.
NOT_SWITCHED = date.max


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
