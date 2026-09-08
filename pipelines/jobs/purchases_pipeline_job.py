import os
import subprocess
import sys


def run_purchases_pipeline_job():
    """
    Runs the Purchases pipeline (Odoo purchase snapshot + canonical load,
    Wansoft canonical load, backlog/reference diagnostics, final canonical
    validation), as a subprocess.

    Was never scheduled before 2026-09-07 -- canonical_purchase_order_snapshot's
    Odoo-sourced rows went stale (last refreshed 2026-08-31) while the
    Wansoft-sourced raw tables kept updating daily, making any dev-vs-prod
    comparison for Odoo-migrated branches meaningless until this ran again.

    PYTHONIOENCODING=utf-8 avoids a pre-existing crash: some step scripts
    print an emoji on completion, which raises UnicodeEncodeError under
    the default Windows console codepage even though the actual work
    already finished successfully (same issue already fixed for the
    Inventory pipeline and the Wansoft automaticos legacy scripts).
    """
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    subprocess.run(
        [sys.executable, "-m", "scripts.run_purchases_pipeline"],
        env=env,
    )
