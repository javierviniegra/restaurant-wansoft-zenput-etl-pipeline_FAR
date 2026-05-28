from pipelines.jobs._helpers import run_parallel_per_company
from extract.inventory.input_inventory import extract_input_inventory


def run_input_inventory_job():
    extract_input_inventory()
