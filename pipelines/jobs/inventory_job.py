"""
Inventory Job Orchestrator
"""
from pipelines.jobs._helpers import run_parallel_per_company
from extract.inventory.wansoft_inventory import extract_inventory


def run_inventory_job():
    extract_inventory()
