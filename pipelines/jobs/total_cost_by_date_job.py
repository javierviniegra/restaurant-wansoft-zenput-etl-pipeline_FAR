from pipelines.jobs._helpers import run_parallel_per_company
from extract.costs.total_cost_by_date import extract_total_cost_by_date


def run_total_cost_by_date_job():
    extract_total_cost_by_date()
