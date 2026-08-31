"""
Inventory Pipeline Orchestrator.

Purpose:
    Run the Inventory domain pipeline in a controlled order.

This script is intentionally conservative:
    - Runs already validated inventory scripts.
    - Stops on critical failures.
    - Rebuilds analytics_inventory_snapshot / analytics_inventory_balance
      (final steps) using the inventory mapping dictionary as it currently
      stands -- it reads dictionary state, it never writes to it.
    - Does not perform dictionary promotions automatically.
    - Does not update Odoo.
    - Does not change COMPANY_SOURCE.
    - Does not replace manual governance review.

Scheduling:
    Wired into pipelines/scheduler.py for a daily automatic run (see
    pipelines/jobs/inventory_pipeline_job.py) so analytics_inventory_balance
    doesn't go stale between manual runs -- confirmed 2026-08-31 that
    nothing was scheduling this before, and some branches' balances were
    5-11 days old as a result. Promoting NEW dictionary entries (closing
    the not_found backlog) stays a separate, manual, human-reviewed step
    (scripts/test_promote_inventory_not_found_*.py) -- this pipeline does
    not touch that.

Execution:
    python -m scripts.run_inventory_pipeline

Dry run:
    python -m scripts.run_inventory_pipeline --dry-run

Optional flags:
    python -m scripts.run_inventory_pipeline --skip-diagnostics
    python -m scripts.run_inventory_pipeline --include-bridge-reports
    python -m scripts.run_inventory_pipeline --include-future-validation

Logging:
    A JSON run log is written to:

        logs/inventory_pipeline_runs/

Important:
    Dictionary promotion scripts are intentionally not part of the default pipeline.
    Promotions must remain controlled and explicitly approved.
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


LOG_DIR = Path("logs") / "inventory_pipeline_runs"


@dataclass
class PipelineStep:
    """
    Represents one executable pipeline step.
    """

    step_id: str
    name: str
    module: str
    required: bool = True
    group: str = "general"
    description: str = ""
    skip_if_missing: bool = False


@dataclass
class StepResult:
    """
    Stores the result of one pipeline step execution.
    """

    step_id: str
    name: str
    module: str
    group: str
    required: bool
    status: str
    started_at: str
    finished_at: str
    duration_seconds: float
    return_code: Optional[int]
    error_message: Optional[str] = None


@dataclass
class PipelineRunLog:
    """
    Stores the complete pipeline execution log.
    """

    run_id: str
    pipeline_name: str
    status: str
    dry_run: bool
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


def now_iso() -> str:
    """
    Returns current local timestamp as string.
    """

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_timestamp_for_filename() -> str:
    """
    Returns timestamp format safe for Windows filenames.
    """

    return datetime.now().strftime("%Y%m%d_%H%M%S")


def module_exists(module_name: str) -> bool:
    """
    Returns True when a Python module can be discovered.
    """

    return importlib.util.find_spec(module_name) is not None


def build_pipeline_steps(
    skip_diagnostics: bool = False,
    include_bridge_reports: bool = False,
    include_future_validation: bool = False,
) -> List[PipelineStep]:
    """
    Builds the Inventory pipeline execution plan.

    Default execution order:
        1. Odoo inventory scope classification
        2. Odoo inventory scope refinement
        3. Odoo inventory ETL
        4. Inventory dictionary lookup validation
        5. Inventory dictionary application validation
        6. Inventory not_found analyzer
        7. Inventory not_found priority backlog
        8. Inventory output validation

    Safety rules:
        - Odoo remains read-only.
        - Dictionary promotions are intentionally excluded from this orchestrator.
        - Bridge reports are optional diagnostics only.
        - Inventory scope refinement is required before Odoo inventory ETL because
          the ETL consumes refined_inventory_scope, not only inventory_scope.
    """

    steps: List[PipelineStep] = []

    steps.append(
        PipelineStep(
            step_id="01",
            name="Odoo inventory scope classification",
            module="scripts.test_odoo_inventory_scope_classification",
            required=True,
            group="scope",
            description=(
                "Classifies Odoo inventory products into base business scopes "
                "before scope refinement and inventory ETL execution."
            ),
        )
    )

    steps.append(
        PipelineStep(
            step_id="02",
            name="Odoo inventory scope refinement",
            module="scripts.test_refine_odoo_inventory_scope",
            required=True,
            group="scope",
            description=(
                "Refines base Odoo inventory scopes into refined_inventory_scope "
                "values such as shared_cross_company, review_scope, bodegon, "
                "empanadas and restaurantes. This step is required before the "
                "Odoo inventory ETL because the ETL filters by refined_inventory_scope."
            ),
        )
    )

    steps.append(
        PipelineStep(
            step_id="03",
            name="Odoo inventory ETL",
            module="scripts.test_odoo_inventory_etl",
            required=True,
            group="inventory_snapshot",
            description=(
                "Loads odoo_inventory_snapshot and odoo_inventory_backlog "
                "using refined scope-aware dictionary logic."
            ),
        )
    )

    steps.append(
        PipelineStep(
            step_id="04",
            name="Inventory dictionary lookup validation",
            module="scripts.test_inventory_dictionary_lookup",
            required=True,
            group="dictionary",
            description=(
                "Validates dictionary lookup logic without promoting products."
            ),
        )
    )

    steps.append(
        PipelineStep(
            step_id="05",
            name="Inventory dictionary application validation",
            module="scripts.test_apply_inventory_dictionary",
            required=True,
            group="dictionary",
            description=(
                "Validates application of inventory dictionary logic to inventory rows."
            ),
        )
    )

    if not skip_diagnostics:
        steps.append(
            PipelineStep(
                step_id="06",
                name="Inventory not_found analyzer",
                module="scripts.test_inventory_not_found_analyzer",
                required=True,
                group="diagnostics",
                description=(
                    "Analyzes residual inventory products with not_found mapping status."
                ),
            )
        )

        steps.append(
            PipelineStep(
                step_id="07",
                name="Inventory not_found priority backlog",
                module="scripts.test_inventory_not_found_priority_backlog",
                required=False,
                group="diagnostics",
                description=(
                    "Builds or validates priority backlog diagnostics for unresolved "
                    "inventory products. This is diagnostic only."
                ),
            )
        )

    if include_bridge_reports:
        steps.append(
            PipelineStep(
                step_id=f"{len(steps) + 1:02d}",
                name="Inventory not_found P1 bridge report",
                module="scripts.test_inventory_not_found_p1_bridge",
                required=False,
                group="bridge_reports",
                description=(
                    "Optional diagnostic bridge report for P1 not_found candidates. "
                    "Does not promote dictionary rows."
                ),
            )
        )

        steps.append(
            PipelineStep(
                step_id=f"{len(steps) + 1:02d}",
                name="Inventory not_found P2 bridge report",
                module="scripts.test_inventory_not_found_p2_bridge",
                required=False,
                group="bridge_reports",
                description=(
                    "Optional diagnostic bridge report for P2 not_found candidates. "
                    "Does not promote dictionary rows."
                ),
            )
        )

        steps.append(
            PipelineStep(
                step_id=f"{len(steps) + 1:02d}",
                name="Inventory not_found residual bridge report",
                module="scripts.test_inventory_not_found_residual_bridge",
                required=False,
                group="bridge_reports",
                description=(
                    "Optional diagnostic bridge report for residual not_found candidates. "
                    "Does not promote dictionary rows."
                ),
            )
        )

    steps.append(
        PipelineStep(
            step_id=f"{len(steps) + 1:02d}",
            name="Build analytics inventory snapshot",
            module="scripts.build_analytics_inventory_snapshot",
            required=True,
            group="analytics_build",
            description=(
                "Rebuilds analytics_inventory_snapshot from the current Odoo "
                "inventory ETL output and the already-approved inventory "
                "mapping dictionary. Reads the dictionary as-is; does not "
                "promote or modify any dictionary rows."
            ),
        )
    )

    steps.append(
        PipelineStep(
            step_id=f"{len(steps) + 1:02d}",
            name="Build analytics inventory balance",
            module="scripts.build_analytics_inventory_balance",
            required=True,
            group="analytics_build",
            description=(
                "Rebuilds analytics_inventory_balance (current stock balance per "
                "company/product, Wansoft and Odoo sides) from "
                "analytics_inventory_snapshot and the Wansoft entrada/salida "
                "tables. This is the table BI and the Odoo cutover checkpoint "
                "read as the current inventory position -- without this step "
                "the pipeline validated everything upstream but never "
                "refreshed the number anyone actually looks at."
            ),
        )
    )

    steps.append(
        PipelineStep(
            step_id=f"{len(steps) + 1:02d}",
            name="Inventory output validation",
            module="scripts.validate_inventory_outputs",
            required=True,
            group="validation",
            description=(
                "Validates inventory outputs, required tables, scope distribution, "
                "snapshot mapping distribution, backlog visibility, dictionary coverage "
                "and controlled promotion policy."
            ),
        )
    )

    return steps


def print_plan(steps: List[PipelineStep]) -> None:
    """
    Prints the execution plan.
    """

    print("\n=====================================================")
    print("INVENTORY PIPELINE EXECUTION PLAN")
    print("=====================================================\n")

    for step in steps:
        required_label = "required" if step.required else "optional"

        print(f"{step.step_id}. [{step.group}] {step.name} ({required_label})")
        print(f"    module: {step.module}")

        if step.description:
            print(f"    purpose: {step.description}")

        if step.skip_if_missing:
            print("    missing-module behaviour: skip if module is not available")

        print("")


def run_module_step(step: PipelineStep, dry_run: bool = False) -> StepResult:
    """
    Runs one pipeline step using python -m <module>.
    """

    started_at = now_iso()
    start_time = time.time()

    print("\n-----------------------------------------------------")
    print(f"START STEP {step.step_id}: {step.name}")
    print("-----------------------------------------------------")
    print(f"module: {step.module}")
    print(f"required: {step.required}")
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
        print(f"finished_at: {finished_at}")
        print(f"duration_seconds: {duration_seconds}")

        return StepResult(
            step_id=step.step_id,
            name=step.name,
            module=step.module,
            group=step.group,
            required=step.required,
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
            status="ERROR",
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=duration_seconds,
            return_code=None,
            error_message=str(exc),
        )


def summarise_results(results: List[StepResult]) -> dict:
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


def print_summary(results: List[StepResult]) -> dict:
    """
    Prints pipeline execution summary and returns summary counts.
    """

    print("\n=====================================================")
    print("INVENTORY PIPELINE SUMMARY")
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
    run_id: str,
    dry_run: bool,
    started_at: str,
    finished_at: str,
    duration_seconds: float,
    results: List[StepResult],
    summary: dict,
) -> PipelineRunLog:
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
        pipeline_name="inventory_pipeline",
        status=status,
        dry_run=dry_run,
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


def write_run_log(run_log: PipelineRunLog) -> Path:
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


def parse_args() -> argparse.Namespace:
    """
    Parses command-line arguments.
    """

    parser = argparse.ArgumentParser(
        description="Run the Inventory domain ETL pipeline in controlled order."
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print and simulate the pipeline without executing modules.",
    )

    parser.add_argument(
        "--skip-diagnostics",
        action="store_true",
        help="Skip inventory diagnostic and backlog review steps.",
    )

    parser.add_argument(
        "--include-bridge-reports",
        action="store_true",
        help=(
            "Include optional bridge report diagnostics. "
            "These do not promote dictionary rows."
        ),
    )

    parser.add_argument(
        "--continue-on-optional-failure",
        action="store_true",
        help=(
            "Continue when optional steps fail. "
            "Required step failures always stop the pipeline."
        ),
    )

    return parser.parse_args()


def main() -> int:
    """
    Main pipeline entrypoint.
    """

    args = parse_args()

    run_id = str(uuid.uuid4())
    pipeline_started_at = now_iso()
    pipeline_start_time = time.time()

    print("=====================================================")
    print("INVENTORY PIPELINE START")
    print("=====================================================")
    print(f"run_id: {run_id}")
    print(f"started_at: {pipeline_started_at}")

    steps = build_pipeline_steps(
        skip_diagnostics=args.skip_diagnostics,
        include_bridge_reports=args.include_bridge_reports,
    )

    print_plan(steps)

    results: List[StepResult] = []

    for step in steps:
        result = run_module_step(
            step=step,
            dry_run=args.dry_run,
        )

        results.append(result)

        if result.status in {"FAILED", "ERROR"}:
            if step.required:
                print("\nRequired step failed. Stopping pipeline.")
                break

            if not args.continue_on_optional_failure:
                print("\nOptional step failed. Stopping pipeline.")
                print(
                    "Use --continue-on-optional-failure to continue "
                    "after optional step failures."
                )
                break

            print("\nOptional step failed. Continuing because flag was enabled.")

    summary = print_summary(results)

    pipeline_finished_at = now_iso()
    pipeline_duration_seconds = round(time.time() - pipeline_start_time, 2)

    run_log = build_run_log(
        run_id=run_id,
        dry_run=args.dry_run,
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
    print("INVENTORY PIPELINE END")
    print("=====================================================")

    if summary["required_failed_or_error"] > 0:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())