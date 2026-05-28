import time
import threading

from pipelines.jobs.inventory_job import run_inventory
from pipelines.jobs.sales_job import run_sales


def schedule_job(job, delay_seconds):

    def loop():
        while True:
            time.sleep(delay_seconds)
            threading.Thread(target=job).start()

    threading.Thread(target=loop).start()


def start():

    print("Scheduler running...")

    # ejemplo (ajústalo a tu horario real)
    schedule_job(run_inventory, 3600)   # cada hora
    schedule_job(run_sales, 600)       # cada 10 min


if __name__ == "__main__":
    start()