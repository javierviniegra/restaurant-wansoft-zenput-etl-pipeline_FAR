from pipelines.jobs._helpers import run_parallel_per_company
from extract.sales.wansoft_sales import extract_sales


def run_sales_job():
    extract_sales()