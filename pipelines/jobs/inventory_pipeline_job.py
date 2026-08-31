import os
import subprocess
import sys


def run_inventory_pipeline_job():
    """
    Runs the Inventory pipeline (scope + Odoo ETL + dictionary lookup +
    analytics_inventory_snapshot / analytics_inventory_balance rebuild +
    not_found backlog diagnostics), as a subprocess.

    Diagnostics are NOT skipped here: mapping unmapped Odoo products to a
    Wansoft code often crosses into other areas' catalogs and isn't
    retroactive, so it stays a periodic manual review, not something this
    pipeline auto-corrects (see validate_odoo_cutover.py,
    AUTO_CORRECTABLE_DOMAINS -- Inventory alerts only). Keeping the
    backlog reports current daily means that review, whenever it happens,
    isn't working off stale data.

    PYTHONIOENCODING=utf-8 avoids a pre-existing crash: some step scripts
    print an emoji on completion, which raises UnicodeEncodeError under
    the default Windows console codepage even though the actual work
    already finished successfully.
    """
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    subprocess.run(
        [sys.executable, "-m", "scripts.run_inventory_pipeline"],
        env=env,
    )
