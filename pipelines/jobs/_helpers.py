import threading
from core.config.companies import CUENTAS_SUCURSALES


def run_parallel_per_company(worker_func, job_name="JOB"):
    print(f"=== Starting job: {job_name} ===")
    threads = []

    for _, company_name, _ in CUENTAS_SUCURSALES:
        t = threading.Thread(target=worker_func, args=(company_name,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    print(f"=== Finished job: {job_name} ✅ ===")