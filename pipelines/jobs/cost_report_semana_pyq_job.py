from pipelines.jobs._helpers import run_parallel_per_company
from extract.costs.cost_report_semana_pyq import extract_cost_report_semana_pyq


def run_cost_report_semana_pyq_job():
    extract_cost_report_semana_pyq()
