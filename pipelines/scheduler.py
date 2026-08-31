import time
import threading
from datetime import datetime, timedelta

from pipelines.jobs.input_inventory_job import run_input_inventory_job
from pipelines.jobs.outgoing_inventory_job import run_outgoing_inventory_job
from pipelines.jobs.extract_all_orders_xml_job import run_extract_all_orders_xml_job
from pipelines.jobs.cost_report_semana_pyq_job import run_cost_report_semana_pyq_job
from pipelines.jobs.download_costs_job import run_download_costs_job
from pipelines.jobs.global_cash_closing_job import run_global_cash_closing_job
from pipelines.jobs.expenses_job import run_expenses_job
from pipelines.jobs.tablajeria_report_job import run_tablajeria_report_job
from pipelines.jobs.total_cost_by_date_job import run_total_cost_by_date_job
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

    # Wansoft automaticos legacy, una corrida diaria de madrugada (01:00-02:20),
    # escalonados para no saturar el SOAP de Wansoft con las ~19 cuentas en paralelo.
    # extractAllOrdersByDay.py es el Candado real (compara contra Cierre Z y
    # corrige); getAllOrdersByDay.py (el downloader con rango de fechas fijo)
    # queda deliberadamente fuera de este agendado.
    schedule_daily_at(run_extract_all_orders_xml_job, hour=1, minute=0)   # Ventas (Candado)
    schedule_daily_at(run_input_inventory_job, hour=1, minute=10)         # Inventario - entradas
    schedule_daily_at(run_outgoing_inventory_job, hour=1, minute=20)      # Inventario - salidas
    schedule_daily_at(run_cost_report_semana_pyq_job, hour=1, minute=30)  # Costos - semana PyQ
    schedule_daily_at(run_download_costs_job, hour=1, minute=40)         # Costos - descarga Wansoft
    schedule_daily_at(run_global_cash_closing_job, hour=1, minute=50)     # Costos - cierre global de caja
    schedule_daily_at(run_expenses_job, hour=2, minute=0)                 # Compras - facturas/gastos
    schedule_daily_at(run_tablajeria_report_job, hour=2, minute=10)       # Costos - tablajería
    schedule_daily_at(run_total_cost_by_date_job, hour=2, minute=20)      # Costos - costo total por fecha

    # refresco diario de analytics_inventory_snapshot/_balance (mecánico,
    # no promueve mapeos nuevos) a la 1pm, antes del checkpoint de cutover
    schedule_daily_at(run_inventory_pipeline_job, hour=13, minute=0)

    # checkpoint T+7/T+30 de sucursales migradas a Odoo (Compras/Inventario)
    # a las 3pm, fuera del horario de los procesos diarios de arriba
    schedule_daily_at(run_odoo_cutover_validation_job, hour=15, minute=0)


if __name__ == "__main__":
    start()