import os

from pipelines.jobs.sales_job import run_sales_job
from pipelines.jobs.inventory_job import run_inventory_job
from pipelines.jobs.extract_all_orders_xml_job import run_extract_all_orders_xml_job
from pipelines.jobs.cost_report_semana_pyq_job import run_cost_report_semana_pyq_job
from pipelines.jobs.download_costs_job import run_download_costs_job
from pipelines.jobs.zenput_tasks_job import run_zenput_tasks_job
from pipelines.jobs.zenput_forms_job import run_zenput_forms_job

from core.config.env_loader import load_environment
load_environment()


if __name__ == "__main__":

    print("==== TEST JOBS DEV START ====\n")

    # Activa uno por uno al principio:
    # run_sales_job()
    # run_inventory_job()
    # run_extract_all_orders_xml_job()
    # run_cost_report_semana_pyq_job()
    # run_download_costs_job()
    # run_zenput_tasks_job()
    run_zenput_forms_job()

    print("\n==== TEST JOBS DEV END ✅ ====")