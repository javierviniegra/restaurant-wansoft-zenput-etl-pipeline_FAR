"""
Nightly stage "Costos - cambio automático a Odoo" (owner, 2026-10-02).

Runs right after the three cost stages:
1. For each branch in COSTS_AUTO_SWITCH_TO_ODOO with no switch recorded yet,
   applies the rule in extract/costs/cost_switch.py (two consecutive days of
   plausible Odoo cost). On a hit it records the switch date in
   costs_odoo_switch and prints an [AVISO] line in the night's log.
2. For every branch switched tonight, recomputes its three cost tables from
   the switch date on (same as the manual backfill in runbook 3d: a child run
   of the cost stages with COSTS_ONLY_BRANCHES and a long enough
   COSTS_LOOKBACK_DAYS), whatever the nightly window is.
3. Publishes the routing in costs_source_by_company (one row per branch: first
   day on Odoo costs or NULL, and why), rewritten every night, so consumers
   such as Central de Reportes read the rule instead of copying it.
4. Validates every branch costed from Odoo over the nightly window (and
   switched branches from their switch date): no duplicate rows, and on
   every Odoo day the month/week accumulation grows by exactly that day's
   cost. Any problem fails the stage, so it shows in the cycle summary.
"""
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from core.config.companies import COSTS_AUTO_SWITCH_TO_ODOO, COMPANY_SOURCE
from core.config.lookback import COSTS_LOOKBACK_DAYS
from core.database.mysql import get_db_connection
from core.database.odoo import get_odoo_connection
from extract.costs.cost_routing import (
    costs_source, load_costs_odoo_start_dates, NOT_SWITCHED, publish_costs_source_table,
)
from extract.costs.cost_switch import (
    check_cost_continuity, detect, ensure_switch_table, load_switch_dates, record_switch, wansoft_subsidiary_id,
)

PROJECT_DIR = Path(__file__).resolve().parents[2]
COST_STAGES = "semana PyQ,descarga Wansoft,costo total por fecha"


def _policy_starts(conn):
    from core.config.companies import ODOO_COMPANY_SOURCE_KEY
    cur = conn.cursor()
    cur.execute("SELECT company_name, operational_start_date FROM odoo_company_migration_policy WHERE is_active = 1")
    return {ODOO_COMPANY_SOURCE_KEY.get(n): s for n, s in cur.fetchall() if ODOO_COMPANY_SOURCE_KEY.get(n)}


def _backfill(branches, since):
    """Child run of the three cost stages for these branches, from the day before `since` through yesterday."""
    days = (date.today() - since).days + 1
    env = dict(os.environ, COSTS_ONLY_BRANCHES=",".join(sorted(branches)), COSTS_LOOKBACK_DAYS=str(days),
               PYTHONIOENCODING="utf-8")
    print(f"[AVISO] Recalculando costos de {sorted(branches)} desde {since - timedelta(days=1)} ({days} días)", flush=True)
    proc = subprocess.run([sys.executable, "-m", "scripts.run_daily_cycle", "--only", COST_STAGES],
                          cwd=PROJECT_DIR, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in (proc.stdout + proc.stderr).splitlines():
        print(f"    | {line}")
    if proc.returncode != 0:
        raise RuntimeError(f"el recálculo de costos de {sorted(branches)} terminó con código {proc.returncode}")


def run_costs_switch_job():
    yesterday = date.today() - timedelta(days=1)
    conn = get_db_connection()
    try:
        ensure_switch_table(conn)
        switches = load_switch_dates(conn)
        policy = _policy_starts(conn)

        # 1) Detection
        switched_tonight = {}
        pending = [k for k in sorted(COSTS_AUTO_SWITCH_TO_ODOO) if k not in switches]
        if pending:
            odoo = get_odoo_connection()
            for key in pending:
                start = policy.get(key)
                if start is None:
                    print(f"[AVISO] {key}: sin fecha de arranque en odoo_company_migration_policy; sigue en Wansoft")
                    continue
                result = detect(key, start, conn, odoo, through=yesterday)
                if result.get("switch_date"):
                    record_switch(conn, key, result["switch_date"], result["evidence"])
                    switched_tonight[key] = result["switch_date"]
                    print(f"[AVISO] {key} cambió a costos de Odoo desde {result['switch_date']} "
                          f"(evidencia: {result['evidence']})", flush=True)
                else:
                    print(f"[✔] {key}: Odoo todavía no cumple la regla, sigue en Wansoft")
        for key, d in sorted(switches.items()):
            print(f"[✔] {key}: en costos de Odoo desde {d}")

        # 2) Backfill of tonight's switches
        if switched_tonight:
            _backfill(switched_tonight.keys(), min(switched_tonight.values()))
            cur = conn.cursor()
            for key in switched_tonight:
                cur.execute("UPDATE costs_odoo_switch SET backfilled_at = NOW() WHERE company_source_key = %s", (key,))
            conn.commit()

        # 3) Publish the routing for consumers (Central de Reportes reads it instead of copying the rules)
        for key, sid, oid, start, reason in publish_costs_source_table(conn):
            print(f"[costs_source_by_company] {key}: {reason}" + (f" desde {start}" if start else ""))

        # 4) Validation of every Odoo-costed branch
        starts = load_costs_odoo_start_dates()
        window_from = yesterday - timedelta(days=COSTS_LOOKBACK_DAYS)
        failures = []
        for key, start in sorted(starts.items()):
            if COMPANY_SOURCE.get(key) != "odoo" or start == NOT_SWITCHED or costs_source(key, yesterday, starts) != "odoo":
                continue
            sid = wansoft_subsidiary_id(key)
            if sid is None:
                continue
            from_day = start if key in switched_tonight else max(start, window_from)
            problems = check_cost_continuity(conn, sid, start, yesterday, from_day=from_day)
            if key in COSTS_AUTO_SWITCH_TO_ODOO and key in (switches | switched_tonight):
                cur = conn.cursor()
                cur.execute("UPDATE costs_odoo_switch SET validated_at = NOW(), validation_result = %s "
                            "WHERE company_source_key = %s", (("OK" if not problems else "; ".join(problems))[:500], key))
                conn.commit()
            if problems:
                failures.append(key)
                for p in problems:
                    print(f"[AVISO] {key}: {p}")
            else:
                print(f"[✔] {key}: costos sin duplicados y acumulados continuos desde {from_day}")
    finally:
        conn.close()
    if failures:
        raise RuntimeError(f"costos con problemas de continuidad o duplicados: {failures}")
