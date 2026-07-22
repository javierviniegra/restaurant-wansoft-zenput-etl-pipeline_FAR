"""
Purchases Pipeline Orchestrator.

Purpose:
    Run the Purchases domain pipeline in a controlled order.

This script is intentionally conservative:
    - Runs already validated scripts.
    - Stops on critical failures.
    - Does not perform dictionary promotions.
    - Does not update Odoo.
    - Does not change COMPANY_SOURCE.
    - Does not schedule itself.
    - Does not replace manual governance review.

Execution:
    python -m scripts.run_purchases_pipeline

Dry run:
    python -m scripts.run_purchases_pipeline --dry-run

Optional flags:
    python -m scripts.run_purchases_pipeline --skip-wansoft
    python -m scripts.run_purchases_pipeline --skip-odoo
    python -m scripts.run_purchases_pipeline --skip-backlog

Logging:
    A JSON run log is written to:

        logs/purchases_pipeline_runs/

    The log includes:
        - run_id
        - started_at
        - finished_at
        - pipeline status
        - step status
        - duration per step
        - return codes
        - error messages
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional


LOG_DIR = Path("logs") / "purchases_pipeline_runs"


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


def build_pipeline_steps(
    skip_odoo: bool = False,
    skip_wansoft: bool = False,
    skip_backlog: bool = False,
) -> List[PipelineStep]:
    """
    Builds the Purchases pipeline execution plan.

    Execution order:
        1. Governance validation
        2. Odoo purchase snapshots
        3. Odoo purchase receipts
        4. Purchase backlog and reference diagnostics
        5. Company source eligibility
        6. Odoo canonical load
        7. Wansoft subsidiary mapping
        8. Wansoft canonical load
        9. Canonical purchase layer validation

    The final validation step is required because the pipeline should not be
    considered successful unless the canonical purchase layer passes the
    post-load validation checks.
    """

    steps: List[PipelineStep] = []

    steps.append(
        PipelineStep(
            step_id="01",
            name="Company source governance",
            module="scripts.test_company_source_governance",
            required=True,
            group="governance",
            description=(
                "Validates COMPANY_SOURCE, Odoo company mappings, "
                "Wansoft subsidiary assumptions and internal providers."
            ),
        )
    )

    if not skip_odoo:
        steps.append(
            PipelineStep(
                step_id="02",
                name="Odoo purchase order and line ETL",
                module="scripts.test_odoo_purchase_etl",
                required=True,
                group="odoo_snapshots",
                description=(
                    "Loads odoo_purchase_order_snapshot and "
                    "odoo_purchase_order_line_snapshot."
                ),
            )
        )

        steps.append(
            PipelineStep(
                step_id="03",
                name="Odoo purchase receipt ETL",
                module="scripts.test_odoo_purchase_receipt_etl",
                required=True,
                group="odoo_snapshots",
                description=(
                    "Loads odoo_purchase_receipt_snapshot and "
                    "odoo_purchase_receipt_move_snapshot."
                ),
            )
        )

    if not skip_backlog:
        steps.append(
            PipelineStep(
                step_id="04",
                name="Purchase inventory mapping backlog",
                module="scripts.test_purchase_inventory_mapping_backlog",
                required=True,
                group="backlog",
                description=(
                    "Builds odoo_purchase_inventory_mapping_backlog "
                    "for unmapped Odoo purchase products."
                ),
            )
        )

        steps.append(
            PipelineStep(
                step_id="05",
                name="Purchase backlog product reference report",
                module="scripts.test_purchase_backlog_product_reference_report",
                required=False,
                group="backlog",
                description=(
                    "Reports whether backlog products have usable Odoo references. "
                    "This is diagnostic and does not promote products automatically."
                ),
            )
        )

    if not skip_odoo:
        steps.append(
            PipelineStep(
                step_id="06",
                name="Purchase company source eligibility",
                module="scripts.test_purchase_company_source_eligibility",
                required=True,
                group="eligibility",
                description=(
                    "Validates which Odoo purchase rows are eligible for "
                    "final canonical load based on COMPANY_SOURCE."
                ),
            )
        )

        steps.append(
            PipelineStep(
                step_id="07",
                name="Odoo canonical purchase load",
                module="scripts.test_canonical_purchase_odoo_etl",
                required=True,
                group="canonical",
                description=(
                    "Loads source_system = 'odoo' rows into canonical_purchase_* tables."
                ),
            )
        )

    if not skip_wansoft:
        steps.append(
            PipelineStep(
                step_id="08",
                name="Wansoft purchase subsidiary mapping report",
                module="scripts.test_wansoft_purchase_subsidiary_mapping_report",
                required=True,
                group="wansoft",
                description=(
                    "Validates getinputinventory_entrada.subsidiary_name "
                    "mapping to company_source_key."
                ),
            )
        )

        steps.append(
            PipelineStep(
                step_id="09",
                name="Wansoft canonical purchase load",
                module="scripts.test_canonical_purchase_wansoft_etl",
                required=True,
                group="canonical",
                description=(
                    "Loads source_system = 'wansoft' rows into canonical_purchase_* tables."
                ),
            )
        )

    steps.append(
        PipelineStep(
            step_id="10",
            name="Purchases canonical layer validation",
            module="scripts.validate_purchases_canonical_layer",
            required=True,
            group="validation",
            description=(
                "Validates source-system coexistence, Antenas source split, "
                "Wansoft final-source companies, internal provider handling, "
                "mapping distribution and canonical table counts."
            ),
        )
    )

    return steps


def print_plan(steps: List[PipelineStep]) -> None:
    """
    Prints the execution plan.
    """

    print("\n=====================================================")
    print("PURCHASES PIPELINE EXECUTION PLAN")
    print("=====================================================\n")

    for step in steps:
        required_label = "required" if step.required else "optional"

        print(f"{step.step_id}. [{step.group}] {step.name} ({required_label})")
        print(f"    module: {step.module}")

        if step.description:
            print(f"    purpose: {step.description}")

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
        "failed_or_error": failed_or_error,
        "required_failed_or_error": required_failed_or_error,
    }


def print_summary(results: List[StepResult]) -> dict:
    """
    Prints pipeline execution summary and returns summary counts.
    """

    print("\n=====================================================")
    print("PURCHASES PIPELINE SUMMARY")
    print("=====================================================\n")

    for result in results:
        print(
            f"{result.step_id}. [{result.group}] {result.name} "
            f"-> {result.status} "
            f"({result.duration_seconds}s)"
        )

        if result.error_message:
            print(f"    error: {result.error_message}")

    summary = summarise_results(results)

    print("\n-----------------------------------------------------")
    print("SUMMARY COUNTS")
    print("-----------------------------------------------------")
    print(f"total_steps: {summary['total_steps']}")
    print(f"success: {summary['success']}")
    print(f"dry_run: {summary['dry_run_steps']}")
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
        pipeline_name="purchases_pipeline",
        status=status,
        dry_run=dry_run,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=duration_seconds,
        total_steps=summary["total_steps"],
        success=summary["success"],
        dry_run_steps=summary["dry_run_steps"],
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
        description="Run the Purchases domain ETL pipeline in controlled order."
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print and simulate the pipeline without executing modules.",
    )

    parser.add_argument(
        "--skip-odoo",
        action="store_true",
        help="Skip Odoo purchase snapshot and Odoo canonical steps.",
    )

    parser.add_argument(
        "--skip-wansoft",
        action="store_true",
        help="Skip Wansoft mapping and Wansoft canonical steps.",
    )

    parser.add_argument(
        "--skip-backlog",
        action="store_true",
        help="Skip purchase backlog and reference diagnostic steps.",
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
    print("PURCHASES PIPELINE START")
    print("=====================================================")
    print(f"run_id: {run_id}")
    print(f"started_at: {pipeline_started_at}")

    steps = build_pipeline_steps(
        skip_odoo=args.skip_odoo,
        skip_wansoft=args.skip_wansoft,
        skip_backlog=args.skip_backlog,
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
    print("PURCHASES PIPELINE END")
    print("=====================================================")

    if summary["required_failed_or_error"] > 0:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())