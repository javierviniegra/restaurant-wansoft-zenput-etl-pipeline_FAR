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

    Since 2026-10-07 the vendor and product catalogs are rebuilt first:
    they had last been built by hand in August, so every vendor or product
    that appeared later was an "orphan" (about 5% of purchases a month).
    dim_vendor is built from the canonical layer; dim_product from the
    mapping dictionary, the canonical layer and the Odoo inventory, so new
    products enter as "pending review" and, under the owner's option 1,
    still count in the business views (catalog_status).
    """
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    for module in (
        "scripts.build_dim_vendor",
        "scripts.build_dim_product",
        "scripts.build_analytics_purchase_order_lines",
        "scripts.build_analytics_purchase_orders",
        "scripts.build_analytics_purchase_daily_company_product",
    ):
        subprocess.run([sys.executable, "-m", module], env=env, check=True)
