import os
import subprocess
import sys


def run_analytics_purchase_pipeline_job():
    """
    Rebuilds the Power-BI-facing Purchases analytics layer, in order:
    analytics_purchase_order_lines -> analytics_purchase_orders ->
    analytics_purchase_daily_company_product. Each reads from the
    previous (all ultimately sourced from canonical_purchase_order_snapshot,
    refreshed by purchases_pipeline_job just before this).

    Was never scheduled before 2026-09-08 -- confirmed stale that day
    (Puebla had real canonical data but zero rows in
    analytics_purchase_orders) while planning the Power BI migration away
    from getexpenses_factura (Wansoft-only) to this unified table.

    PYTHONIOENCODING=utf-8 matches the same guard used for the other
    pipeline jobs (inventory_pipeline_job, purchases_pipeline_job).
    """
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    for module in (
        "scripts.build_analytics_purchase_order_lines",
        "scripts.build_analytics_purchase_orders",
        "scripts.build_analytics_purchase_daily_company_product",
    ):
        subprocess.run([sys.executable, "-m", module], env=env)
