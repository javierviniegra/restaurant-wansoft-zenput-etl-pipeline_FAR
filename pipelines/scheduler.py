import time
import threading
from datetime import datetime, timedelta

from pipelines.jobs.input_inventory_job import run_input_inventory_job
from pipelines.jobs.outgoing_inventory_job import run_outgoing_inventory_job
from pipelines.jobs.sales_job import run_sales_job
from pipelines.jobs.odoo_cutover_validation_job import run_odoo_cutover_validation_job
from pipelines.jobs.inventory_pipeline_job import run_inventory_pipeline_job


def schedule_job(job, delay_seconds):

    def loop():
        while True:
            time.sleep(delay_seconds)
            threading.Thread(target=job).start()

    threading.Thread(target=loop).start()


def schedule_daily_at(job, hour, minute=0):
    """
    Corre `job` una vez al día a la hora local `hour:minute` (24h),
    sin importar a qué hora arrancó el scheduler.
    """

    def seconds_until_next_run():
        now = datetime.now()
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        return (next_run - now).total_seconds()

    def loop():
        while True:
            time.sleep(seconds_until_next_run())
            threading.Thread(target=job).start()

    threading.Thread(target=loop).start()


def start():

    print("Scheduler running...")

    # ejemplo (ajústalo a tu horario real)
    schedule_job(run_input_inventory_job, 3600)     # cada hora
    schedule_job(run_outgoing_inventory_job, 3600)  # cada hora
    schedule_job(run_sales_job, 600)       # cada 10 min

    # refresco diario de analytics_inventory_snapshot/_balance (mecánico,
    # no promueve mapeos nuevos) a la 1pm, antes del checkpoint de cutover
    schedule_daily_at(run_inventory_pipeline_job, hour=13, minute=0)

    # checkpoint T+7/T+30 de sucursales migradas a Odoo (Compras/Inventario)
    # a las 3pm, fuera del horario de los procesos diarios de arriba
    schedule_daily_at(run_odoo_cutover_validation_job, hour=15, minute=0)


if __name__ == "__main__":
    start()