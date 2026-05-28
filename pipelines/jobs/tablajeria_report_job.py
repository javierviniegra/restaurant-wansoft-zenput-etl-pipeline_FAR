from pipelines.jobs._helpers import run_parallel_per_company
from extract.costs.tablajeria_report import extract_tablajeria_report


def run_tablajeria_report_job():
    extract_tablajeria_report()