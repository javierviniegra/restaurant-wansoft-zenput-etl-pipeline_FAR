from pipelines.jobs._helpers import run_parallel_per_company
from extract.xml.get_all_orders_by_day import extract_orders_by_day


def run_get_all_orders_by_day_job():
    extract_orders_by_day()