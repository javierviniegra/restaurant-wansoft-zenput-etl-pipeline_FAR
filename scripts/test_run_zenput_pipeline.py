"""
Smoke test for Zenput Pipeline Orchestrator.

Purpose:
    Validate that scripts/run_zenput_pipeline.py behaves safely.

This test validates two important behaviours:

1. Default dry-run:
    - The Zenput pipeline runs without executing legacy ETLs.
    - The execution plan is printed.
    - The pipeline summary is printed.
    - The pipeline completes successfully.
    - A JSON run log is generated.

2. Safety gate:
    - Running with --execute but without --allow-legacy-writes must fail.
    - No legacy scripts should be executed.
    - The output must explain that write-enabled legacy steps are blocked.
    - The pipeline result must be FAILED.

Execution:
    python -m scripts.test_run_zenput_pipeline

Important:
    This test does not call the Zenput API.
    This test does not write to MySQL.
    This test does not update last_run_timestamp.txt.
"""

from __future__ import annotations

import subprocess
import sys


def run_command(command):
    """
    Runs a subprocess command and returns the completed process.
    """

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
    print("")

    return completed


def validate_dry_run():
    """
    Validates the default safe dry-run behaviour.

    Expected:
        return_code = 0
        output contains execution plan
        output contains summary
        output reports completed pipeline
        output includes run log section
        output reports all three steps as DRY_RUN
    """

    print("=====================================================")
    print("TEST 1: ZENPUT PIPELINE DEFAULT DRY-RUN")
    print("=====================================================\n")

    command = [
        sys.executable,
        "-m",
        "scripts.run_zenput_pipeline",
    ]

    completed = run_command(command)

    if completed.returncode != 0:
        print("TEST 1 RESULT: FAILED")
        print("Reason: default dry-run returned a non-zero exit code.")
        return False

    required_markers = [
        "ZENPUT PIPELINE EXECUTION PLAN",
        "ZENPUT PIPELINE SUMMARY",
        "PIPELINE RESULT: COMPLETED",
        "RUN LOG",
        "Zenput location mapping validation -> DRY_RUN",
        "Zenput forms legacy ETL -> DRY_RUN",
        "Zenput tasks legacy ETL -> DRY_RUN",
        "Zenput output validation -> DRY_RUN",
    ]

    for marker in required_markers:
        if marker not in completed.stdout:
            print("TEST 1 RESULT: FAILED")
            print(f"Reason: expected marker not found: {marker}")
            return False

    blocked_markers = [
        "PIPELINE RESULT: FAILED",
        "ERROR: Real execution includes write-enabled legacy steps.",
    ]

    for marker in blocked_markers:
        if marker in completed.stdout:
            print("TEST 1 RESULT: FAILED")
            print(f"Reason: unexpected marker found in dry-run output: {marker}")
            return False

    print("TEST 1 RESULT: PASSED")
    return True


def validate_safety_gate():
    """
    Validates that real execution is blocked unless legacy writes are allowed.

    Expected:
        return_code != 0
        output contains safety gate error
        output reports FAILED
        output does not execute legacy steps
    """

    print("\n=====================================================")
    print("TEST 2: ZENPUT PIPELINE SAFETY GATE")
    print("=====================================================\n")

    command = [
        sys.executable,
        "-m",
        "scripts.run_zenput_pipeline",
        "--execute",
    ]

    completed = run_command(command)

    if completed.returncode == 0:
        print("TEST 2 RESULT: FAILED")
        print("Reason: safety gate should return a non-zero exit code.")
        return False

    required_markers = [
        "ERROR: Real execution includes write-enabled legacy steps.",
        "--execute --allow-legacy-writes",
        "No steps were executed.",
        "Safety gate -> FAILED",
        "PIPELINE RESULT: FAILED",
        "RUN LOG",
    ]

    for marker in required_markers:
        if marker not in completed.stdout:
            print("TEST 2 RESULT: FAILED")
            print(f"Reason: expected safety marker not found: {marker}")
            return False

    forbidden_markers = [
        "Zenput forms legacy ETL -> SUCCESS",
        "Zenput tasks legacy ETL -> SUCCESS",
    ]

    for marker in forbidden_markers:
        if marker in completed.stdout:
            print("TEST 2 RESULT: FAILED")
            print(f"Reason: legacy step appears to have executed: {marker}")
            return False

    print("TEST 2 RESULT: PASSED")
    return True


def main():
    """
    Runs all Zenput pipeline smoke tests.
    """

    print("==== TEST RUN ZENPUT PIPELINE ====\n")

    dry_run_passed = validate_dry_run()
    safety_gate_passed = validate_safety_gate()

    print("\n=====================================================")
    print("FINAL TEST SUMMARY")
    print("=====================================================")
    print(f"default_dry_run: {'PASS' if dry_run_passed else 'FAIL'}")
    print(f"safety_gate: {'PASS' if safety_gate_passed else 'FAIL'}")

    if dry_run_passed and safety_gate_passed:
        print("\nTEST RESULT: PASSED")
        print("\n==== DONE ====")
        return 0

    print("\nTEST RESULT: FAILED")
    print("\n==== DONE ====")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())