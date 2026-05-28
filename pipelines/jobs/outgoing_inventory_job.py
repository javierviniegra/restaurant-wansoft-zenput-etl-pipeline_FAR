from pipelines.jobs._helpers import run_parallel_per_company
from extract.inventory.outgoing_inventory import extract_outgoing_inventory


def run_outgoing_inventory_job():
    extract_outgoing_inventory()