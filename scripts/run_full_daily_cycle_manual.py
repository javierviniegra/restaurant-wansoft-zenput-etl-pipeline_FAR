"""
Manual, sequential run of the full daily cycle (same stages the
scheduler runs on its own schedule in pipelines/scheduler.py), for
ad-hoc "simulate today's production run" validation sessions where the
scheduler is not running as a persistent process.

Runs against whatever ENV core/config/.env is currently set to
(dev, per project convention for this kind of exercise).

Stages, in order (same order/spacing rationale as pipelines/scheduler.py):
  1. Legacy Wansoft + Zenput chain (Ventas/Inventario/Costos/Compras + Zenput)
  2. Inventory pipeline (analytics_inventory_snapshot/_balance rebuild)
  3. Purchases pipeline (canonical_purchase_order_snapshot refresh)
  4. Analytics-purchase pipeline (Power BI-facing purchases layer rebuild)
  5. Odoo cutover validation checkpoint
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from pipelines.scheduler import run_daily_legacy_chain  # noqa: E402
from pipelines.jobs.inventory_pipeline_job import run_inventory_pipeline_job  # noqa: E402
from pipelines.jobs.purchases_pipeline_job import run_purchases_pipeline_job  # noqa: E402
from pipelines.jobs.analytics_purchase_pipeline_job import run_analytics_purchase_pipeline_job  # noqa: E402
from pipelines.jobs.odoo_cutover_validation_job import run_odoo_cutover_validation_job  # noqa: E402


STAGES = [
    ("legacy_chain", run_daily_legacy_chain),
    ("inventory_pipeline", run_inventory_pipeline_job),
    ("purchases_pipeline", run_purchases_pipeline_job),
    ("analytics_purchase_pipeline", run_analytics_purchase_pipeline_job),
    ("odoo_cutover_validation", run_odoo_cutover_validation_job),
]


def main():
    env = os.getenv("ENV", "prod")
    print(f"=== FULL DAILY CYCLE (manual run) -- ENV={env} -- started {datetime.now().isoformat()} ===", flush=True)

    for name, fn in STAGES:
        t0 = time.time()
        print(f"\n>>> STAGE START: {name} -- {datetime.now().isoformat()}", flush=True)
        try:
            fn()
            status = "OK"
        except Exception as e:
            status = f"FAILED - {e}"
        elapsed = time.time() - t0
        print(f">>> STAGE END: {name} -- {status} -- {elapsed:.1f}s", flush=True)

    print(f"\n=== FULL DAILY CYCLE (manual run) -- finished {datetime.now().isoformat()} ===", flush=True)


if __name__ == "__main__":
    main()
