from scripts.check_odoo_company_activity import check as check_odoo_company_activity
from scripts.validate_odoo_cutover import main as run_odoo_cutover_validation


def run_odoo_cutover_validation_job():
    # Reminder for branch rollouts (owner, 2026-10-12): [AVISO] when an Odoo
    # company has activity the warehouse is not configured to load. Never
    # fails the stage.
    try:
        check_odoo_company_activity()
    except Exception as exc:  # noqa: BLE001 - a reminder must not break the stage
        print(f"[AVISO] No se pudo revisar la actividad de las compañías de Odoo: {exc}")

    # A FAIL checkpoint must show as a failed stage in the cycle summary
    # (owner, 2026-10-08, bug #42); before, the exit code was ignored.
    exit_code = run_odoo_cutover_validation()
    if exit_code:
        raise RuntimeError("Odoo cutover validation: at least one checkpoint FAILED (see the lines above)")
