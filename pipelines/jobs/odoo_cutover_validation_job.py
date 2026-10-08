from scripts.validate_odoo_cutover import main as run_odoo_cutover_validation


def run_odoo_cutover_validation_job():
    # A FAIL checkpoint must show as a failed stage in the cycle summary
    # (owner, 2026-10-08, bug #42); before, the exit code was ignored.
    exit_code = run_odoo_cutover_validation()
    if exit_code:
        raise RuntimeError("Odoo cutover validation: at least one checkpoint FAILED (see the lines above)")
