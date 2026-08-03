"""
Zenput Pipeline Orchestrator.

Purpose:
    Provide a safe orchestration wrapper for the existing Zenput legacy scripts.

This script is intentionally conservative.

By default:
    - It runs in dry-run mode.
    - It does not execute legacy Zenput ETLs.
    - It does not call the Zenput API.
    - It does not write to MySQL.
    - It does not update last_run_timestamp.txt.

Real execution requires explicit flags:
    python -m scripts.run_zenput_pipeline --execute --allow-legacy-writes

This protects the project from accidental execution because the existing
legacy scripts write to MySQL and may update the local timestamp file.

Current legacy scripts:
    legacy.zenput.zenput_mysql_forms
    legacy.zenput.zenput_mysql_tasks

Read-only validator:
    scripts.validate_zenput_location_mapping

Logging:
    logs/zenput_pipeline_runs/

Important:
    This wrapper does not replace the legacy scripts yet.
    It provides a controlled execution boundary around them.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional


LOG_DIR = Path("logs") / "zenput_pipeline_runs"


@dataclass
class PipelineStep:
    """
    Represents one Zenput pipeline step.
    """

    step_id: str
    name: str
    module: str
    required: bool = True
    group: str = "general"
    description: str = ""
    read_only: bool = False
    writes_database: bool = False
    writes_file: bool = False
    legacy: bool = False
    enabled: bool = True
    skip_if_missing: bool = False


@dataclass
class StepResult:
    """
    Stores one Zenput pipeline step result.
    """

    step_id: str
    name: str
    module: str
    group: str
    required: bool
    read_only: bool
    writes_database: bool
    writes_file: bool
    legacy: bool
    status: str
    started_at: str
    finished_at: str
    duration_seconds: float
    return_code: Optional[int]
    error_message: Optional[str] = None


@dataclass
class PipelineRunLog:
    """
    Stores the full Zenput pipeline run log.
    """

    run_id: str
    pipeline_name: str
    status: str
    dry_run: bool
    execute: bool
    allow_legacy_writes: bool
    started_at: str
    finished_at: str
    duration_seconds: float
    total_steps: int
    success: int
    dry_run_steps: int
    skipped: int
    failed_or_error: int
    required_failed_or_error: int
    steps: List[StepResult]


def now_iso():
    """
    Returns current local timestamp as string.
    """

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_timestamp_for_filename():
    """
    Returns timestamp format safe for Windows filenames.
    """

    return datetime.now().strftime("%Y%m%d_%H%M%S")


def module_exists(module_name):
    """
    Returns True if a Python module can be discovered.
    """

    return importlib.util.find_spec(module_name) is not None


def build_pipeline_steps(
    include_forms=True,
    include_tasks=True,
    include_location_validation=True,
    include_output_validation=True,
):
    """
    Builds the Zenput pipeline execution plan.

    Current safe order:
        01. Zenput location mapping validation
        02. Zenput forms legacy ETL
        03. Zenput tasks legacy ETL
        04. Zenput output validation

    The location mapping validator is read-only.
    The forms and tasks scripts are legacy write-enabled scripts.
    The output validator is read-only and should be required as the final gate.

    In dry-run mode, all steps are simulated.
    In real execution, write-enabled legacy steps require:
        --execute --allow-legacy-writes
    """

    steps = []

    if include_location_validation:
        steps.append(
            PipelineStep(
                step_id="01",
                name="Zenput location mapping validation",
                module="scripts.validate_zenput_location_mapping",
                required=True,
                group="validation",
                description=(
                    "Read-only validation of submissions.location_name against "
                    "core.config.zenput."
                ),
                read_only=True,
                writes_database=False,
                writes_file=False,
                legacy=False,
            )
        )

    if include_forms:
        steps.append(
            PipelineStep(
                step_id=f"{len(steps) + 1:02d}",
                name="Zenput forms legacy ETL",
                module="legacy.zenput.zenput_mysql_forms",
                required=True,
                group="forms",
                description=(
                    "Legacy ETL for Zenput form templates, submissions and "
                    "submission answers. This writes to MySQL target zenput."
                ),
                read_only=False,
                writes_database=True,
                writes_file=False,
                legacy=True,
            )
        )

    if include_tasks:
        steps.append(
            PipelineStep(
                step_id=f"{len(steps) + 1:02d}",
                name="Zenput tasks legacy ETL",
                module="legacy.zenput.zenput_mysql_tasks",
                required=True,
                group="tasks",
                description=(
                    "Legacy ETL for Zenput tasks. This writes to MySQL target "
                    "zenput and may update last_run_timestamp.txt."
                ),
                read_only=False,
                writes_database=True,
                writes_file=True,
                legacy=True,
            )
        )

    if include_output_validation:
        steps.append(
            PipelineStep(
                step_id=f"{len(steps) + 1:02d}",
                name="Zenput output validation",
                module="scripts.validate_zenput_outputs",
                required=True,
                group="validation",
                description=(
                    "Read-only validation of Zenput output tables, location mapping, "
                    "Zenput-only locations, timestamp file and legacy pipeline protection."
                ),
                read_only=True,
                writes_database=False,
                writes_file=False,
                legacy=False,
            )
        )

    return steps


def print_plan(steps):
    """
    Prints the execution plan.
    """

    print("\n=====================================================")
    print("ZENPUT PIPELINE EXECUTION PLAN")
    print("=====================================================\n")

    for step in steps:
        required_label = "required" if step.required else "optional"
        read_only_label = "read-only" if step.read_only else "write-enabled"
        legacy_label = "legacy" if step.legacy else "modern"

        print(
            f"{step.step_id}. [{step.group}] {step.name} "
            f"({required_label}, {read_only_label}, {legacy_label})"
        )
        print(f"    module: {step.module}")

        if step.description:
            print(f"    purpose: {step.description}")

        print(f"    writes_database: {step.writes_database}")
        print(f"    writes_file: {step.writes_file}")

        if step.skip_if_missing:
            print("    missing-module behaviour: skip if module is not available")

        print("")


def print_safety_notice(execute, allow_legacy_writes):
    """
    Prints safety information for Zenput execution.
    """

    print("\n=====================================================")
    print("ZENPUT PIPELINE SAFETY NOTICE")
    print("=====================================================\n")

    print("Default behaviour:")
    print("    dry-run only")
    print("    no legacy ETL execution")
    print("    no Zenput API calls")
    print("    no MySQL writes")
    print("    no last_run_timestamp.txt update")
    print("")

    print("Current flags:")
    print(f"    execute: {execute}")
    print(f"    allow_legacy_writes: {allow_legacy_writes}")
    print("")

    if execute and allow_legacy_writes:
        print("Real execution is explicitly enabled.")
        print("Legacy scripts may write to MySQL and update local timestamp state.")
    elif execute and not allow_legacy_writes:
        print("Real execution was requested but legacy writes were not allowed.")
        print("The pipeline will fail before executing write-enabled legacy steps.")
    else:
        print("Dry-run mode is active.")
        print("Write-enabled legacy steps will be simulated only.")


def run_module_step(step, dry_run=True):
    """
    Runs or simulates one pipeline step.
    """

    started_at = now_iso()
    start_time = time.time()

    print("\n-----------------------------------------------------")
    print(f"START STEP {step.step_id}: {step.name}")
    print("-----------------------------------------------------")
    print(f"module: {step.module}")
    print(f"group: {step.group}")
    print(f"required: {step.required}")
    print(f"read_only: {step.read_only}")
    print(f"writes_database: {step.writes_database}")
    print(f"writes_file: {step.writes_file}")
    print(f"legacy: {step.legacy}")
    print(f"started_at: {started_at}")

    if step.skip_if_missing and not module_exists(step.module):
        finished_at = now_iso()
        duration_seconds = round(time.time() - start_time, 2)
        message = f"Module not found and skip_if_missing=True: {step.module}"

        print("status: SKIPPED")
        print(f"reason: {message}")
        print(f"finished_at: {finished_at}")
        print(f"duration_seconds: {duration_seconds}")

        return StepResult(
            step_id=step.step_id,
            name=step.name,
            module=step.module,
            group=step.group,
            required=step.required,
            read_only=step.read_only,
            writes_database=step.writes_database,
            writes_file=step.writes_file,
            legacy=step.legacy,
            status="SKIPPED",
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=duration_seconds,
            return_code=None,
            error_message=message,
        )

    if dry_run:
        finished_at = now_iso()
        duration_seconds = round(time.time() - start_time, 2)

        print("status: DRY_RUN")
        print("note: step was not executed.")
        print(f"finished_at: {finished_at}")
        print(f"duration_seconds: {duration_seconds}")

        return StepResult(
            step_id=step.step_id,
            name=step.name,
            module=step.module,
            group=step.group,
            required=step.required,
            read_only=step.read_only,
            writes_database=step.writes_database,
            writes_file=step.writes_file,
            legacy=step.legacy,
            status="DRY_RUN",
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=duration_seconds,
            return_code=None,
            error_message=None,
        )

    command = [
        sys.executable,
        "-m",
        step.module,
    ]

    try:
        completed = subprocess.run(
            command,
            check=False,
            text=True,
        )

        finished_at = now_iso()
        duration_seconds = round(time.time() - start_time, 2)

        if completed.returncode == 0:
            status = "SUCCESS"
            error_message = None
        else:
            status = "FAILED"
            error_message = f"Step returned non-zero exit code: {completed.returncode}"

        print(f"status: {status}")
        print(f"return_code: {completed.returncode}")
        print(f"finished_at: {finished_at}")
        print(f"duration_seconds: {duration_seconds}")

        return StepResult(
            step_id=step.step_id,
            name=step.name,
            module=step.module,
            group=step.group,
            required=step.required,
            read_only=step.read_only,
            writes_database=step.writes_database,
            writes_file=step.writes_file,
            legacy=step.legacy,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=duration_seconds,
            return_code=completed.returncode,
            error_message=error_message,
        )

    except Exception as exc:
        finished_at = now_iso()
        duration_seconds = round(time.time() - start_time, 2)

        print("status: ERROR")
        print(f"error: {exc}")
        print(f"finished_at: {finished_at}")
        print(f"duration_seconds: {duration_seconds}")

        return StepResult(
            step_id=step.step_id,
            name=step.name,
            module=step.module,
            group=step.group,
            required=step.required,
            read_only=step.read_only,
            writes_database=step.writes_database,
            writes_file=step.writes_file,
            legacy=step.legacy,
            status="ERROR",
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=duration_seconds,
            return_code=None,
            error_message=str(exc),
        )


def summarise_results(results):
    """
    Builds summary counts from step results.
    """

    total = len(results)
    success = len([r for r in results if r.status == "SUCCESS"])
    dry_run_steps = len([r for r in results if r.status == "DRY_RUN"])
    skipped = len([r for r in results if r.status == "SKIPPED"])
    failed_or_error = len([r for r in results if r.status in {"FAILED", "ERROR"}])
    required_failed_or_error = len(
        [
            r
            for r in results
            if r.required and r.status in {"FAILED", "ERROR"}
        ]
    )

    return {
        "total_steps": total,
        "success": success,
        "dry_run_steps": dry_run_steps,
        "skipped": skipped,
        "failed_or_error": failed_or_error,
        "required_failed_or_error": required_failed_or_error,
    }


def print_summary(results):
    """
    Prints pipeline execution summary.
    """

    print("\n=====================================================")
    print("ZENPUT PIPELINE SUMMARY")
    print("=====================================================\n")

    for result in results:
        print(
            f"{result.step_id}. [{result.group}] {result.name} "
            f"-> {result.status} "
            f"({result.duration_seconds}s)"
        )

        if result.error_message:
            print(f"    note: {result.error_message}")

    summary = summarise_results(results)

    print("\n-----------------------------------------------------")
    print("SUMMARY COUNTS")
    print("-----------------------------------------------------")
    print(f"total_steps: {summary['total_steps']}")
    print(f"success: {summary['success']}")
    print(f"dry_run: {summary['dry_run_steps']}")
    print(f"skipped: {summary['skipped']}")
    print(f"failed_or_error: {summary['failed_or_error']}")
    print(f"required_failed_or_error: {summary['required_failed_or_error']}")

    if summary["required_failed_or_error"] > 0:
        print("\nPIPELINE RESULT: FAILED")
    else:
        print("\nPIPELINE RESULT: COMPLETED")

    return summary


def build_run_log(
    run_id,
    dry_run,
    execute,
    allow_legacy_writes,
    started_at,
    finished_at,
    duration_seconds,
    results,
    summary,
):
    """
    Builds the in-memory run log object.
    """

    status = (
        "FAILED"
        if summary["required_failed_or_error"] > 0
        else "COMPLETED"
    )

    return PipelineRunLog(
        run_id=run_id,
        pipeline_name="zenput_pipeline",
        status=status,
        dry_run=dry_run,
        execute=execute,
        allow_legacy_writes=allow_legacy_writes,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=duration_seconds,
        total_steps=summary["total_steps"],
        success=summary["success"],
        dry_run_steps=summary["dry_run_steps"],
        skipped=summary["skipped"],
        failed_or_error=summary["failed_or_error"],
        required_failed_or_error=summary["required_failed_or_error"],
        steps=results,
    )


def write_run_log(run_log):
    """
    Writes the pipeline run log to a JSON file.
    """

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = safe_timestamp_for_filename()
    log_file = LOG_DIR / f"{timestamp}_{run_log.run_id}.json"

    payload = asdict(run_log)

    with open(log_file, "w", encoding="utf-8") as file:
        json.dump(
            payload,
            file,
            indent=2,
            ensure_ascii=False,
        )

    return log_file


def parse_args():
    """
    Parses command-line arguments.
    """

    parser = argparse.ArgumentParser(
        description="Run the Zenput pipeline wrapper safely."
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help=(
            "Execute enabled steps. Without this flag, the pipeline runs in "
            "dry-run mode."
        ),
    )

    parser.add_argument(
        "--allow-legacy-writes",
        action="store_true",
        help=(
            "Required together with --execute to run write-enabled legacy "
            "Zenput scripts."
        ),
    )

    parser.add_argument(
        "--forms-only",
        action="store_true",
        help="Include only the Zenput forms legacy step plus validation.",
    )

    parser.add_argument(
        "--tasks-only",
        action="store_true",
        help="Include only the Zenput tasks legacy step plus validation.",
    )

    parser.add_argument(
        "--validation-only",
        action="store_true",
        help=(
            "Execute only read-only Zenput validators. "
            "This excludes write-enabled legacy forms and tasks ETLs."
        ),
    )

    parser.add_argument(
        "--skip-location-validation",
        action="store_true",
        help="Skip read-only Zenput location mapping validation.",
    )

    parser.add_argument(
        "--continue-on-optional-failure",
        action="store_true",
        help=(
            "Reserved for future optional steps. Required step failures always "
            "stop the pipeline."
        ),
    )

    return parser.parse_args()


def main():
    """
    Main Zenput pipeline entrypoint.
    """

    args = parse_args()

    execute = bool(args.execute)
    allow_legacy_writes = bool(args.allow_legacy_writes)
    dry_run = not execute

    include_forms = True
    include_tasks = True

    if args.forms_only and args.tasks_only:
        print("ERROR: --forms-only and --tasks-only cannot be used together.")
        return 1

    if args.validation_only and (args.forms_only or args.tasks_only):
        print("ERROR: --validation-only cannot be combined with --forms-only or --tasks-only.")
        return 1

    if args.validation_only:
        include_forms = False
        include_tasks = False

    elif args.forms_only:
        include_forms = True
        include_tasks = False

    elif args.tasks_only:
        include_forms = False
        include_tasks = True
        
    run_id = str(uuid.uuid4())
    pipeline_started_at = now_iso()
    pipeline_start_time = time.time()

    print("=====================================================")
    print("ZENPUT PIPELINE START")
    print("=====================================================")
    print(f"run_id: {run_id}")
    print(f"started_at: {pipeline_started_at}")

    print_safety_notice(
        execute=execute,
        allow_legacy_writes=allow_legacy_writes,
    )

    steps = build_pipeline_steps(
        include_forms=include_forms,
        include_tasks=include_tasks,
        include_location_validation=not args.skip_location_validation,
    )

    print_plan(steps)

    has_write_enabled_steps = any(
        step.writes_database or step.writes_file
        for step in steps
    )

    if execute and has_write_enabled_steps and not allow_legacy_writes:
        print("\nERROR: Real execution includes write-enabled legacy steps.")
        print("To execute legacy Zenput ETLs, use:")
        print("    --execute --allow-legacy-writes")
        print("")
        print("No steps were executed.")

        pipeline_finished_at = now_iso()
        pipeline_duration_seconds = round(time.time() - pipeline_start_time, 2)

        failed_result = StepResult(
            step_id="00",
            name="Safety gate",
            module="scripts.run_zenput_pipeline",
            group="safety",
            required=True,
            read_only=True,
            writes_database=False,
            writes_file=False,
            legacy=False,
            status="FAILED",
            started_at=pipeline_started_at,
            finished_at=pipeline_finished_at,
            duration_seconds=pipeline_duration_seconds,
            return_code=1,
            error_message=(
                "Execution blocked because write-enabled legacy steps require "
                "--allow-legacy-writes."
            ),
        )

        results = [failed_result]
        summary = print_summary(results)

        run_log = build_run_log(
            run_id=run_id,
            dry_run=dry_run,
            execute=execute,
            allow_legacy_writes=allow_legacy_writes,
            started_at=pipeline_started_at,
            finished_at=pipeline_finished_at,
            duration_seconds=pipeline_duration_seconds,
            results=results,
            summary=summary,
        )

        log_file = write_run_log(run_log)

        print("\n-----------------------------------------------------")
        print("RUN LOG")
        print("-----------------------------------------------------")
        print(f"run_id: {run_id}")
        print(f"log_file: {log_file}")

        return 1

    results = []

    for step in steps:
        step_dry_run = dry_run

        result = run_module_step(
            step=step,
            dry_run=step_dry_run,
        )

        results.append(result)

        if result.status in {"FAILED", "ERROR"}:
            if step.required:
                print("\nRequired step failed. Stopping pipeline.")
                break

            if not args.continue_on_optional_failure:
                print("\nOptional step failed. Stopping pipeline.")
                break

            print("\nOptional step failed. Continuing because flag was enabled.")

    summary = print_summary(results)

    pipeline_finished_at = now_iso()
    pipeline_duration_seconds = round(time.time() - pipeline_start_time, 2)

    run_log = build_run_log(
        run_id=run_id,
        dry_run=dry_run,
        execute=execute,
        allow_legacy_writes=allow_legacy_writes,
        started_at=pipeline_started_at,
        finished_at=pipeline_finished_at,
        duration_seconds=pipeline_duration_seconds,
        results=results,
        summary=summary,
    )

    log_file = write_run_log(run_log)

    print("\n-----------------------------------------------------")
    print("RUN LOG")
    print("-----------------------------------------------------")
    print(f"run_id: {run_id}")
    print(f"log_file: {log_file}")

    print(f"\nfinished_at: {pipeline_finished_at}")
    print(f"duration_seconds: {pipeline_duration_seconds}")
    print("=====================================================")
    print("ZENPUT PIPELINE END")
    print("=====================================================")

    if summary["required_failed_or_error"] > 0:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())