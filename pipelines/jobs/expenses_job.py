from pipelines.jobs._helpers import run_parallel_per_company
from extract.costs.expenses import extract_expenses


def run_expenses_job():
    extract_expenses()