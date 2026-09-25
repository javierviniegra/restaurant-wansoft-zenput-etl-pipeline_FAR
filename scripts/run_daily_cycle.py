"""Runs the whole daily cycle once, in order, and exits non-zero if any stage failed.

Usage (from the project root):
    python -m scripts.run_daily_cycle                     # every stage; the weekly job only on Sundays
    python -m scripts.run_daily_cycle --list              # print the stage names and exit
    python -m scripts.run_daily_cycle --only cutover,Inventory   # stages whose name contains any of these
"""
import argparse
import sys
import time
import traceback
from datetime import datetime

from pipelines.scheduler import DAILY_LEGACY_CHAIN_STEPS
from pipelines.jobs.inventory_pipeline_job import run_inventory_pipeline_job
from pipelines.jobs.purchases_pipeline_job import run_purchases_pipeline_job
from pipelines.jobs.analytics_purchase_pipeline_job import run_analytics_purchase_pipeline_job
from pipelines.jobs.odoo_cutover_validation_job import run_odoo_cutover_validation_job
from pipelines.jobs.product_mapping_backlog_job import run_product_mapping_backlog_job


def build_stages(today=None):
    today = today or datetime.now()
    stages = list(DAILY_LEGACY_CHAIN_STEPS) + [
        ("Inventory pipeline", run_inventory_pipeline_job),
        ("Purchases pipeline", run_purchases_pipeline_job),
        ("Analytics purchase pipeline", run_analytics_purchase_pipeline_job),
        ("Odoo cutover validation", run_odoo_cutover_validation_job),
    ]
    if today.weekday() == 6:
        stages.append(("Product mapping backlog (weekly)", run_product_mapping_backlog_job))
    return stages


def run_stages(stages):
    results = []
    for name, job in stages:
        started = time.time()
        print(f"##### [{datetime.now():%H:%M:%S}] START {name}", flush=True)
        try:
            job()
            status = "OK"
        except (Exception, SystemExit) as exc:
            status = f"FAILED {type(exc).__name__}: {exc}"
            traceback.print_exc()
        seconds = time.time() - started
        print(f"##### [{datetime.now():%H:%M:%S}] END {name} -> {status} ({seconds:.0f}s)", flush=True)
        results.append((name, status, seconds))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", action="store_true", help="print the stage names and exit")
    parser.add_argument("--only", help="comma-separated fragments; run only stages whose name contains one")
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    stages = build_stages()
    if args.only:
        fragments = [f.strip().lower() for f in args.only.split(",") if f.strip()]
        stages = [s for s in stages if any(f in s[0].lower() for f in fragments)]
    if args.list:
        for name, _ in stages:
            print(name)
        return 0

    started = time.time()
    print(f"##### CYCLE START {datetime.now():%Y-%m-%d %H:%M:%S} ({len(stages)} stages)", flush=True)
    results = run_stages(stages)
    failed = [r for r in results if r[1] != "OK"]
    for name, status, seconds in results:
        print(f"  {status.split(':')[0]:<8} {name} ({seconds:.0f}s)")
    print(f"##### CYCLE DONE in {(time.time() - started) / 60:.1f} min, {len(failed)} failed", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
