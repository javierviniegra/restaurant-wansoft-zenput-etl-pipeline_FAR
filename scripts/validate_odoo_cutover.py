"""
Odoo cutover post-migration checkpoint.

Purpose:
    When a branch's Purchases/Inventory source switches from Wansoft to
    Odoo (COMPANY_SOURCE == "odoo", operational_start_date reached), Odoo's
    own data can still be settling for the first few weeks (late captures,
    batch/PEPS cost recognition lag -- the same pattern already confirmed
    during the Costs acceptance gate, see PROJECT_CONTEXT_REPORT.md Section
    9). This script re-checks each recently migrated branch a fixed number
    of days after cutover, comparing dev (MySQL canonical/analytics tables)
    against a fresh, independent, live read of Odoo -- not against any
    cached snapshot -- and re-runs the relevant pipeline automatically if
    they disagree beyond tolerance.

Design:
    - Checkpoints: 7 days and 30 days after operational_start_date.
    - Each (company, domain, checkpoint) combination is checked exactly
      once, ever (tracked in odoo_cutover_validation_log via a UNIQUE key).
      This is a settling checkpoint, not a daily reconciliation loop --
      the daily "did today's numbers land correctly" job for Sales already
      exists separately (legacy/wansoft/automaticos/extractAllOrdersByDay.py).
    - A company only qualifies once it is both COMPANY_SOURCE == "odoo"
      (the authoritative source switch) AND has an is_active = 1 row in
      odoo_company_migration_policy (the authoritative "rollout actually
      turned on" flag -- e.g. Puebla is COMPANY_SOURCE == "odoo" but
      is_active = 0, so it is correctly skipped until activated).
    - Purchases comparison: canonical_purchase_order_snapshot vs a live
      purchase.order query (state not in cancel/draft, per the canceled-
      orders bug fixed during the gate).
    - Inventory comparison: analytics_inventory_balance vs a live
      stock.quant query, both scoped to the branch's odoo_company_id.
    - On a Purchases FAIL, triggers run_purchases_pipeline as a subprocess
      (a full, idempotent, already-validated canonical rebuild) and logs
      the outcome. It does not re-validate after correction in the same
      run -- the next scheduled checkpoint (or a manual re-run) confirms.
    - On an Inventory FAIL, does NOT auto-correct -- see
      AUTO_CORRECTABLE_DOMAINS below for why. It logs
      correction_status = 'manual_review_required' instead.

Run:
    python -m scripts.validate_odoo_cutover

Scheduling:
    Wired into pipelines/scheduler.py at 15:00 daily (off-peak, does not
    overlap the frequent daily jobs), via
    pipelines/jobs/odoo_cutover_validation_job.py.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.config.companies import COMPANY_SOURCE, get_company_source_key
from core.database.mysql import get_db_connection
from core.database.odoo import get_odoo_connection


CHECKPOINT_DAYS = (7, 30)

# Purchases: FAIL auto-triggers run_purchases_pipeline (confirmed safe --
# it's a full, idempotent, already-validated rebuild of the canonical layer).
# Inventory: alert only. run_inventory_pipeline.py deliberately stops before
# build_analytics_inventory_snapshot.py / build_analytics_inventory_balance.py
# -- the project keeps that final build manual because it depends on
# dictionary/mapping promotion decisions that need human review (see its
# module docstring: "Does not perform dictionary promotions automatically
# ... Does not replace manual governance review"). Auto-triggering the
# analytics build here would silently bypass that review gate, so an
# Inventory FAIL is logged with correction_status = 'manual_review_required'
# instead of being corrected.
AUTO_CORRECTABLE_DOMAINS = {"purchases"}

# Wider than the ~0.0001 rate used for same-source-system table reconciliation
# (validate_analytics_inventory_balance.py) because this compares two
# genuinely independent reads (dev vs live Odoo) shortly after cutover, when
# Odoo's own recognition lag is expected. Purchases noise of 3-6% and
# Inventory noise were both observed as normal during the acceptance gate;
# these rates leave headroom above that before triggering a correction.
PURCHASE_TOLERANCE_RATE = Decimal("0.08")
INVENTORY_TOLERANCE_RATE = Decimal("0.05")

LOG_TABLE = "odoo_cutover_validation_log"


@dataclass
class CompanyCutover:
    odoo_company_id: int
    odoo_company_name: str
    company_source_key: str
    operational_start_date: date


def ensure_log_table(conn: Any) -> None:
    cur = conn.cursor()
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {LOG_TABLE} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            company_source_key VARCHAR(100) NOT NULL,
            odoo_company_id BIGINT NOT NULL,
            domain VARCHAR(20) NOT NULL,
            checkpoint_days INT NOT NULL,
            operational_start_date DATE NOT NULL,
            checked_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            dev_value DECIMAL(18,4),
            odoo_value DECIMAL(18,4),
            difference DECIMAL(18,4),
            tolerance DECIMAL(18,4),
            status VARCHAR(10) NOT NULL,
            correction_triggered TINYINT(1) NOT NULL DEFAULT 0,
            correction_status VARCHAR(20),
            notes VARCHAR(500),
            UNIQUE KEY uq_cutover_check (company_source_key, domain, checkpoint_days)
        )
        """
    )
    conn.commit()
    cur.close()


def get_active_odoo_companies() -> List[CompanyCutover]:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT odoo_company_id, company_name, operational_start_date
        FROM odoo_company_migration_policy
        WHERE is_active = 1
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    companies: List[CompanyCutover] = []
    for odoo_company_id, odoo_company_name, operational_start_date in rows:
        company_source_key = get_company_source_key(odoo_company_name)
        if company_source_key is None:
            continue  # internal provider / out-of-scope company
        if COMPANY_SOURCE.get(company_source_key) != "odoo":
            continue  # policy row exists ahead of the actual source switch
        companies.append(
            CompanyCutover(
                odoo_company_id=int(odoo_company_id),
                odoo_company_name=odoo_company_name,
                company_source_key=company_source_key,
                operational_start_date=operational_start_date,
            )
        )
    return companies


def already_checked(conn: Any, company_source_key: str, domain: str, checkpoint_days: int) -> bool:
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT 1 FROM {LOG_TABLE}
        WHERE company_source_key = %s AND domain = %s AND checkpoint_days = %s
        """,
        (company_source_key, domain, checkpoint_days),
    )
    found = cur.fetchone() is not None
    cur.close()
    return found


def check_purchases(company: CompanyCutover) -> Dict[str, Any]:
    today = date.today()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COALESCE(SUM(amount_total), 0)
        FROM canonical_purchase_order_snapshot
        WHERE company_source_key = %s
          AND source_system = 'odoo'
          AND order_date >= %s
          AND order_date < %s
        """,
        (company.company_source_key, company.operational_start_date, today),
    )
    dev_total = Decimal(str(cur.fetchone()[0] or 0))
    cur.close()
    conn.close()

    uid, models, db, password = get_odoo_connection()
    domain_filter = [
        ["company_id", "=", company.odoo_company_id],
        ["date_order", ">=", company.operational_start_date.strftime("%Y-%m-%d")],
        ["date_order", "<", today.strftime("%Y-%m-%d")],
        ["state", "not in", ["cancel", "draft"]],
    ]
    order_ids = models.execute_kw(db, uid, password, "purchase.order", "search", [domain_filter])
    odoo_total = Decimal("0")
    if order_ids:
        orders = models.execute_kw(
            db, uid, password, "purchase.order", "read", [order_ids], {"fields": ["amount_total"]}
        )
        odoo_total = sum((Decimal(str(o["amount_total"])) for o in orders), Decimal("0"))

    return _evaluate(dev_total, odoo_total, PURCHASE_TOLERANCE_RATE)


def check_inventory(company: CompanyCutover) -> Dict[str, Any]:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COALESCE(SUM(current_balance_qty), 0)
        FROM analytics_inventory_balance
        WHERE company_source_key = %s AND source_system = 'odoo'
        """,
        (company.company_source_key,),
    )
    dev_total = Decimal(str(cur.fetchone()[0] or 0))

    # Scope the live comparison to the same product universe dev already
    # covers (mapped to a Wansoft code AND final_odoo_enabled). Most
    # branches have a large backlog of Odoo products with no Wansoft
    # mapping yet (see inventory_not_found_analysis.csv) -- that is a
    # known, separately tracked mapping backlog, not a sync/freshness
    # problem this checkpoint should flag or "correct" by re-running the
    # pipeline. Confirmed on Antenas: 321 distinct products with real
    # stock in Odoo, only 42 mapped -- comparing against all 321 produced
    # a false ~12x gap.
    cur.execute(
        """
        SELECT DISTINCT odoo_product_id
        FROM analytics_inventory_snapshot
        WHERE company_source_key = %s
          AND company_mapping_status = 'final_odoo_enabled'
          AND include_in_business_views = 1
          AND odoo_product_id IS NOT NULL
        """,
        (company.company_source_key,),
    )
    mapped_product_ids = [int(row[0]) for row in cur.fetchall() if row[0] is not None]
    cur.close()
    conn.close()

    if not mapped_product_ids:
        return _evaluate(dev_total, Decimal("0"), INVENTORY_TOLERANCE_RATE)

    uid, models, db, password = get_odoo_connection()
    # location_id.usage == 'internal' excludes partner/virtual locations
    # (e.g. "Vendors"/"Customers"), which carry negative counterpart
    # quantities in Odoo's double-entry stock model and are not part of
    # analytics_inventory_balance's scope (is_internal_location on the
    # dev side). Without this filter the comparison is not apples-to-apples.
    domain_filter = [
        ["company_id", "=", company.odoo_company_id],
        ["location_id.usage", "=", "internal"],
        ["product_id", "in", mapped_product_ids],
    ]
    quant_ids = models.execute_kw(db, uid, password, "stock.quant", "search", [domain_filter])
    odoo_total = Decimal("0")
    if quant_ids:
        quants = models.execute_kw(
            db, uid, password, "stock.quant", "read", [quant_ids], {"fields": ["quantity"]}
        )
        odoo_total = sum((Decimal(str(q["quantity"])) for q in quants), Decimal("0"))

    return _evaluate(dev_total, odoo_total, INVENTORY_TOLERANCE_RATE)


def _evaluate(dev_total: Decimal, odoo_total: Decimal, tolerance_rate: Decimal) -> Dict[str, Any]:
    difference = abs(dev_total - odoo_total)
    tolerance = max(odoo_total.copy_abs(), Decimal("1")) * tolerance_rate
    status = "PASS" if difference <= tolerance else "FAIL"
    return {
        "dev_value": dev_total,
        "odoo_value": odoo_total,
        "difference": difference,
        "tolerance": tolerance,
        "status": status,
    }


def trigger_correction(domain: str) -> str:
    import os

    module = "scripts.run_purchases_pipeline" if domain == "purchases" else "scripts.run_inventory_pipeline"
    print(f"    [CORRECCION] Ejecutando {module}...")
    # Force UTF-8 for the child process's stdout/stderr. The pipeline step
    # scripts print emoji (e.g. "DONE ✅") on completion; without this, a
    # subprocess whose output is captured can fall back to the system
    # codepage (cp1252 on Windows), crash on that print, and get reported
    # as a failed step even though the actual ETL work already finished.
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    result = subprocess.run([sys.executable, "-m", module], capture_output=True, text=True, env=env)
    if result.returncode == 0:
        print(f"    [CORRECCION] {module} completado OK")
        return "success"
    print(f"    [CORRECCION] {module} terminó con error (code={result.returncode})")
    print(result.stdout[-2000:])
    print(result.stderr[-2000:])
    return "failed"


def log_result(
    conn: Any,
    company: CompanyCutover,
    domain: str,
    checkpoint_days: int,
    evaluation: Dict[str, Any],
    correction_triggered: bool,
    correction_status: Optional[str],
) -> None:
    cur = conn.cursor()
    cur.execute(
        f"""
        INSERT INTO {LOG_TABLE} (
            company_source_key, odoo_company_id, domain, checkpoint_days,
            operational_start_date, dev_value, odoo_value, difference,
            tolerance, status, correction_triggered, correction_status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            company.company_source_key,
            company.odoo_company_id,
            domain,
            checkpoint_days,
            company.operational_start_date,
            evaluation["dev_value"],
            evaluation["odoo_value"],
            evaluation["difference"],
            evaluation["tolerance"],
            evaluation["status"],
            int(correction_triggered),
            correction_status,
        ),
    )
    conn.commit()
    cur.close()


def run_checkpoint(company: CompanyCutover, domain: str, checkpoint_days: int) -> None:
    log_conn = get_db_connection()
    try:
        if already_checked(log_conn, company.company_source_key, domain, checkpoint_days):
            return

        days_since_cutover = (date.today() - company.operational_start_date).days
        if days_since_cutover < checkpoint_days:
            return

        print(
            f"\n  [{company.company_source_key}] domain={domain} "
            f"checkpoint=T+{checkpoint_days}d (cutover {company.operational_start_date}, "
            f"{days_since_cutover} días transcurridos)"
        )

        evaluation = check_purchases(company) if domain == "purchases" else check_inventory(company)
        print(
            f"    dev={evaluation['dev_value']} odoo={evaluation['odoo_value']} "
            f"diff={evaluation['difference']} tolerance={evaluation['tolerance']} "
            f"-> {evaluation['status']}"
        )

        correction_triggered = False
        correction_status = None
        if evaluation["status"] == "FAIL":
            if domain in AUTO_CORRECTABLE_DOMAINS:
                correction_triggered = True
                correction_status = trigger_correction(domain)
            else:
                correction_status = "manual_review_required"
                print(
                    f"    [ALERTA] {domain} fuera de tolerancia -- requiere revisión manual, "
                    f"no se dispara corrección automática (ver ALERT_ONLY_DOMAINS)."
                )

        log_result(log_conn, company, domain, checkpoint_days, evaluation, correction_triggered, correction_status)
    finally:
        log_conn.close()


def main() -> int:
    print("=====================================================")
    print("ODOO CUTOVER CHECKPOINT VALIDATION")
    print(f"Fecha de ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=====================================================")

    setup_conn = get_db_connection()
    ensure_log_table(setup_conn)
    setup_conn.close()

    companies = get_active_odoo_companies()
    print(f"Sucursales elegibles (COMPANY_SOURCE=odoo y policy activa): {len(companies)}")
    for company in companies:
        print(f"  - {company.company_source_key} (Odoo: {company.odoo_company_name}, "
              f"cutover {company.operational_start_date})")

    any_fail = False
    for company in companies:
        for checkpoint_days in CHECKPOINT_DAYS:
            for domain in ("purchases", "inventory"):
                run_checkpoint(company, domain, checkpoint_days)

    summary_conn = get_db_connection()
    cur = summary_conn.cursor()
    cur.execute(
        f"""
        SELECT status, COUNT(*) FROM {LOG_TABLE}
        WHERE checked_at >= CURDATE()
        GROUP BY status
        """
    )
    today_counts = dict(cur.fetchall())
    cur.close()
    summary_conn.close()

    print("\n=====================================================")
    print("RESUMEN DEL DÍA")
    print("=====================================================")
    print(f"Checkpoints evaluados hoy: {sum(today_counts.values())}")
    print(f"  PASS: {today_counts.get('PASS', 0)}")
    print(f"  FAIL: {today_counts.get('FAIL', 0)}")

    any_fail = today_counts.get("FAIL", 0) > 0
    return 1 if any_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
