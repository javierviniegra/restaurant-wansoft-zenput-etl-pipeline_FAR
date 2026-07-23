"""
Smoke test for Purchases Pipeline Orchestrator.

Purpose:
    Validate that scripts/run_purchases_pipeline.py can be executed
    in dry-run mode.

This test does not execute real ETLs.

It validates:
    - the orchestrator module can be called with python -m
    - --dry-run produces output
    - the execution plan is printed
    - the process exits successfully

Execution:
    python -m scripts.test_run_purchases_pipeline
"""

from __future__ import annotations

import subprocess
import sys


def run_pipeline_dry_run() -> int:
    """
    Executes the purchases pipeline in dry-run mode as a subprocess.

    This test intentionally avoids importing internal functions from
    scripts.run_purchases_pipeline so the orchestrator can evolve without
    breaking the smoke test.
    """

    command = [
        sys.executable,
        "-m",
        "scripts.run_purchases_pipeline",
        "--dry-run",
    ]

    print("==== TEST RUN PURCHASES PIPELINE DRY RUN ====\n")
    print("Command:")
    print(" ".join(command))
    print("")

    completed = subprocess.run(
        command,
        text=True,
        capture_output=True,
    )

    print("---- STDOUT ----")
    print(completed.stdout)

    print("---- STDERR ----")
    print(completed.stderr)

    print("---- RESULT ----")
    print(f"return_code: {completed.returncode}")

    if completed.returncode != 0:
        print("\nTEST RESULT: FAILED ❌")
        return completed.returncode

    if "PURCHASES PIPELINE EXECUTION PLAN" not in completed.stdout:
        print("\nTEST RESULT: FAILED ❌")
        print("Reason: dry-run output did not include the execution plan.")
        return 1

    if "PURCHASES PIPELINE SUMMARY" not in completed.stdout:
        print("\nTEST RESULT: FAILED ❌")
        print("Reason: dry-run output did not include the pipeline summary.")
        return 1

    if "PIPELINE RESULT: COMPLETED" not in completed.stdout:
        print("\nTEST RESULT: FAILED ❌")
        print("Reason: dry-run output did not report completed pipeline.")
        return 1

    print("\nTEST RESULT: PASSED ✅")
    print("\n==== DONE ✅ ====")

    return 0


if __name__ == "__main__":
    raise SystemExit(run_pipeline_dry_run())