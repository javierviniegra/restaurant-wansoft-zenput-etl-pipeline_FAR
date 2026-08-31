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
from pipelines.jobs.zenput_forms_job import run_zenput_forms_job
from pipelines.jobs.zenput_tasks_job import run_zenput_tasks_job
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


DAILY_LEGACY_CHAIN_STEPS = [
    ("Ventas (Candado real)", run_extract_all_orders_xml_job),
    ("Inventario - entradas", run_input_inventory_job),
    ("Inventario - salidas", run_outgoing_inventory_job),
    ("Costos - semana PyQ", run_cost_report_semana_pyq_job),
    ("Costos - descarga Wansoft", run_download_costs_job),
    ("Costos - cierre global de caja", run_global_cash_closing_job),
    ("Compras - facturas/gastos", run_expenses_job),
    ("Costos - tablajería", run_tablajeria_report_job),
    ("Costos - costo total por fecha", run_total_cost_by_date_job),
    ("Zenput - forms", run_zenput_forms_job),
    ("Zenput - tasks", run_zenput_tasks_job),
]


def run_daily_legacy_chain():
    """
    Corre los scripts legacy (Wansoft: Ventas/Inventario/Costos, y Zenput:
    forms/tasks) uno tras otro, en orden, sin traslape: varios no pueden
    correr en paralelo (SOAP de Wansoft / MySQL), así que cada paso
    arranca solo cuando el anterior terminó, en vez de horarios fijos
    escalonados.

    Los pasos de Zenput llaman a los scripts legacy directamente
    (legacy/zenput/zenput_mysql_forms.py, zenput_mysql_tasks.py), sin
    pasar por el safety gate documentado en
    docs/production-orchestration-plan.md (scripts/run_zenput_pipeline.py
    --allow-legacy-writes). Incluidos aquí por decisión explícita del
    dueño del proyecto (2026-08-31).

    Un paso que falla no detiene la cadena — se registra el error y se
    sigue con el siguiente, igual que cuando cada job corría de forma
    independiente.
    """
    print("=== Wansoft daily chain: starting ===")
    for name, job in DAILY_LEGACY_CHAIN_STEPS:
        print(f"--- {name}: starting ---")
        try:
            job()
            print(f"--- {name}: done ---")
        except Exception as e:
            print(f"--- {name}: FAILED - {e} ---")
    print("=== Wansoft daily chain: finished ===")


def start():

    print("Scheduler running...")

    # Legacy Wansoft + Zenput, una sola corrida diaria a partir de la 1am,
    # en cadena secuencial (ver run_daily_legacy_chain arriba).
    # extractAllOrdersByDay.py es el Candado real (compara contra Cierre Z
    # y corrige); getAllOrdersByDay.py (el downloader con rango de fechas
    # fijo) queda deliberadamente fuera de este agendado.
    schedule_daily_at(run_daily_legacy_chain, hour=1, minute=0)

    # refresco diario de analytics_inventory_snapshot/_balance (mecánico,
    # no promueve mapeos nuevos) a la 1pm, antes del checkpoint de cutover
    schedule_daily_at(run_inventory_pipeline_job, hour=13, minute=0)

    # checkpoint T+7/T+30 de sucursales migradas a Odoo (Compras/Inventario)
    # a las 3pm, fuera del horario de los procesos diarios de arriba
    schedule_daily_at(run_odoo_cutover_validation_job, hour=15, minute=0)


if __name__ == "__main__":
    start()