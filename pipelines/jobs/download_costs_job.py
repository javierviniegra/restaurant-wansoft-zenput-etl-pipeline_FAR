from pipelines.jobs._helpers import run_parallel_per_company
from extract.costs.download_costs import extract_download_costs


def run_download_costs_job():
    extract_download_costs()