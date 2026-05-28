from pipelines.jobs._helpers import run_parallel_per_company
from extract.costs.global_cash_closing import extract_global_cash_closing


def run_global_cash_closing_job():
    extract_global_cash_closing()