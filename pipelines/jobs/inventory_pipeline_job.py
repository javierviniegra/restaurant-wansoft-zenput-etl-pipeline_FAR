import os
import subprocess
import sys


def run_inventory_pipeline_job():
    """
    Runs the Inventory pipeline (scope + Odoo ETL + dictionary lookup +
    analytics_inventory_snapshot / analytics_inventory_balance rebuild)
    as a subprocess, skipping the diagnostic-only not_found backlog steps
    (those are for human review, not needed for the daily refresh).

    PYTHONIOENCODING=utf-8 avoids a pre-existing crash: some step scripts
    print an emoji on completion, which raises UnicodeEncodeError under
    the default Windows console codepage even though the actual work
    already finished successfully.
    """
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    subprocess.run(
        [sys.executable, "-m", "scripts.run_inventory_pipeline", "--skip-diagnostics"],
        env=env,
    )
