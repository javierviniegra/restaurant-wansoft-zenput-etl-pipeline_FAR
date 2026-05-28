from pipelines.jobs._helpers import run_parallel_per_company
from extract.xml.extract_all_orders_xml import extract_all_orders_xml


def run_extract_all_orders_xml_job():
    extract_all_orders_xml()