import mysql.connector
from mysql.connector import Error
import numpy as np
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone
import json
import time

import sys
import os

# 1. Le decimos a Python que incluya la carpeta raíz en su ruta de búsqueda
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 2. Ahora sí podemos importar nuestra función
from database import get_db_connection

# # Primeros Pasos

# ## Otras Variables

# la Hora de hoy
HoraHoy = datetime.now()

# Defino el rango de fechas
start_date = datetime.now() - timedelta(days=1)
end_date = datetime.now() - timedelta(days=1)
# start_date = datetime(2025, 1, 1)  # Fecha inicial
# end_date = datetime(2025, 9, 9)  # Fecha final

subsidiaries = [
    {"id": 5320, "nombreCorto": "Acoxpa", "password": os.getenv("WANSOFT_PWD_5320"), 'name': "Fonda Argentina - Acoxpa"},
    {"id": 4959, "nombreCorto": "Aeropuerto", "password": os.getenv("WANSOFT_PWD_4959"), 'name': "Fonda Argentina - Aeropuerto"},
    {"id": 4958, "nombreCorto": "Isabel La Católica", "password": os.getenv("WANSOFT_PWD_4958"),
     'name': "Fonda Argentina - Isabel La Católica"},
    {"id": 4960, "nombreCorto": "Antenas", "password": os.getenv("WANSOFT_PWD_4960"), 'name': "Fonda Argentina - Antenas"},
    {"id": 5321, "nombreCorto": "Taquería parroquia", "password": os.getenv("WANSOFT_PWD_5321"),
     'name': "Fonda Argentina – Taquería Parroquía"},
    {"id": 5318, "nombreCorto": "Vía Vallejo", "password": os.getenv("WANSOFT_PWD_5318"), 'name': "Fonda Argentina – Vía Vallejo"},
    {"id": 4961, "nombreCorto": "Viaducto", "password": os.getenv("WANSOFT_PWD_4961"), 'name': "Fonda Argentina - Viaducto"},
    {"id": 4962, "nombreCorto": "Taquería Viaducto", "password": os.getenv("WANSOFT_PWD_4962"),
     'name': "Fonda Argentina - Taqueria Viaducto"},
    {"id": 5319, "nombreCorto": "San Jeronimo", "password": os.getenv("WANSOFT_PWD_5319"), 'name': "Fonda Argentina – San Jerónimo"},
    {"id": 6560, "nombreCorto": "Tepeyac", "password": os.getenv("WANSOFT_PWD_6560"), 'name': "Fonda Argentina - Tepeyac"},
    {"id": 7697, "nombreCorto": "Taq San Fernando", "password": os.getenv("WANSOFT_PWD_7697"),
     'name': "Fonda Argentina - Taqueria San Fernando"},
    {"id": 6174, "nombreCorto": "Playa del Carmen", "password": os.getenv("WANSOFT_PWD_6174"),
     'name': "Fonda Argentina - Playa del Carmen"},
    {"id": 5943, "nombreCorto": "Oceanía", "password": os.getenv("WANSOFT_PWD_5943"), 'name': "Fonda Argentina - Oceanía"},
    {"id": 6175, "nombreCorto": "Cancun", "password": os.getenv("WANSOFT_PWD_6175"), 'name': "Fonda Argentina - Cancún"},
    {"id": 4433, "nombreCorto": "Napoles", "password": os.getenv("WANSOFT_PWD_4433"), 'name': "Fonda Argentina - Nápoles"},
    {"id": 4752, "nombreCorto": "Metepec", "password": os.getenv("WANSOFT_PWD_4752"), 'name': "Fonda Argentina - Tollocan"},
    {"id": 5396, "nombreCorto": "Versalles", "password": os.getenv("WANSOFT_PWD_5396"), 'name': "Fonda Argentina - Taquería Exhibimex"},
    {"id":12057, "nombreCorto": "La Esquina Coyoacán", "name":"Fonda Argentina - Coyoacan", "password": os.getenv("WANSOFT_PWD_12057")},
    {"id":12802, "nombreCorto": "CentroMyJ", "name":"Fonda Argentina - Centro Mario y July", "password": os.getenv("WANSOFT_PWD_12802")},
    {"id":12806, "nombreCorto": "Puebla", "name":"Fonda Argentina - Puebla", "password": os.getenv("WANSOFT_PWD_12806")}
]

# Convertir la lista de diccionarios en un DataFrame
dfSubsidiaries = pd.DataFrame(subsidiaries)
# dfSubsidiaries # En .py, usa print(dfSubsidiaries) para ver la salida

# # Inicialización de Variables

# --- 1. CONFIGURACIÓN ---
# Diccionario de Endpoints solo para tareas
ZENPUT_API_ENDPOINTS = {
    'list_tasks': "https://www.zenput.com/api/v1/tasks/list_tasks"
}

# Configuración de la API de Zenput
ZENPUT_API_TOKEN =  os.getenv("ZENPUT_API_TOKEN")  # Asegúrate de configurar esta variable de entorno con tu token real

ZENPUT_HEADERS = {
    "accept": "application/json",
    # ¡OJO! La API v2 (tareas) podría requerir 'Authorization': 'Bearer TU_TOKEN'
    # en lugar de X-API-TOKEN. Si 'list_tasks' da error 401/403, prueba a cambiar esto.
    "X-API-TOKEN": ZENPUT_API_TOKEN  # Usa tu token real
}

# # Formularios


# --- NUEVO: Archivo para guardar el timestamp ---
TIMESTAMP_FILE = 'last_run_timestamp.txt'


# --- 2. FUNCIONES DE MANEJO DE TIMESTAMPS ---

def get_last_run_timestamp(filepath):
    """Lee el último timestamp guardado. Devuelve epoch si no existe."""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                timestamp_str = f.read().strip()
                # Intentamos parsear como ISO 8601 UTC
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            print("ℹ️ No se encontró archivo de timestamp. Se descargarán todas las tareas.")
            # Devuelve una fecha muy antigua (epoch UTC)
            return datetime(1970, 1, 1, tzinfo=timezone.utc)
    except Exception as e:
        print(f"⚠️ Error leyendo timestamp: {e}. Se descargarán todas las tareas.")
        return datetime(1970, 1, 1, tzinfo=timezone.utc)


def save_current_timestamp(filepath, timestamp_dt):
    """Guarda el timestamp actual (en UTC ISO 8601) en el archivo."""
    try:
        # Aseguramos que sea UTC y formateamos
        timestamp_utc = timestamp_dt.astimezone(timezone.utc)
        timestamp_str = timestamp_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
        with open(filepath, 'w') as f:
            f.write(timestamp_str)
        print(f"✅ Timestamp guardado: {timestamp_str}")
    except Exception as e:
        print(f"❌ Error guardando timestamp: {e}")


# --- 3. FUNCIONES PARA TAREAS (setup_tasks_table, parse_zenput_date, upsert_tasks sin cambios) ---
# ... (El código de setup_tasks_table es el mismo) ...
# ... (El código de parse_zenput_date es el mismo) ...
# ... (El código de upsert_tasks con todos los campos es el mismo) ...

def setup_tasks_table():
    """Asegura que la tabla para las tareas exista con todos los campos."""
    try:
        connection = get_db_connection(target="zenput")
        cursor = connection.cursor()
        create_table_query = """
        CREATE TABLE IF NOT EXISTS zenput_tasks (
            task_id INT PRIMARY KEY, title TEXT, description TEXT, company_id INT, account_id INT, account_name VARCHAR(255), account_address TEXT,
            account_city VARCHAR(100), account_state VARCHAR(100), account_zipcode VARCHAR(20), account_country VARCHAR(10), account_lat DECIMAL(10, 8), account_lon DECIMAL(11, 8),
            status_id INT, status_type VARCHAR(50), status_name VARCHAR(50), reply_type VARCHAR(50), reporter_id INT, reporter_display_name VARCHAR(255),
            assignee_id INT, assignee_display_name VARCHAR(255), date_created DATETIME, date_modified DATETIME, date_start DATETIME, date_due DATETIME,
            time_zone VARCHAR(100), is_active BOOLEAN, is_closed BOOLEAN, project_id INT, fulfillment_type VARCHAR(50), fulfillment_date_completed DATETIME,
            fulfillment_date_submitted DATETIME, fulfillment_user_id INT, fulfillment_user_display_name VARCHAR(255),
            fulfillment_fields JSON, date_submitted DATETIME, deleted BOOLEAN, num_comments INT, is_completed_late BOOLEAN, current_state VARCHAR(50),
            subscribers JSON, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ); """
        cursor.execute(create_table_query)
        print("✅ Tabla 'zenput_tasks' (extendida) verificada/creada.")
    except Error as e:
        print(f"❌ Error al configurar la tabla de tareas extendida: {e}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close();
            connection.close()


def parse_zenput_date(date_dict):
    """Convierte el formato de fecha de Zenput a datetime."""
    if not date_dict or '$date' not in date_dict: return None
    try:
        timestamp_ms = date_dict['$date']
        if isinstance(timestamp_ms, (int, float)):
            return datetime.fromtimestamp(timestamp_ms / 1000)
        else:
            print(f"⚠️ Advertencia: Timestamp no válido: {timestamp_ms}");
            return None
    except Exception as e:
        print(f"⚠️ Error parseando fecha: {date_dict} - {e}");
        return None


def upsert_tasks(tasks_data):
    """Inserta o actualiza tareas con todos los campos disponibles y logging de error mejorado."""
    if not tasks_data:
        print("ℹ️ No hay tareas nuevas/actualizadas para procesar.");
        return 0

    data_to_insert = []
    # (El bucle for para preparar data_to_insert sigue igual que antes)
    for task in tasks_data:
        company = task.get('company', {});
        account = task.get('account');
        status = task.get('status', {});
        reply = task.get('reply', {});
        reporter = task.get('reporter', {});
        assignee = task.get('assignee', {});
        project = task.get('project');
        fulfillment = task.get('fulfillment')
        fulfillment_user = {};
        fulfillment_fields_json = None;
        fulfillment_type = None
        fulfillment_date_completed = None;
        fulfillment_date_submitted = None
        fulfillment_user_id = None;
        fulfillment_user_display_name = None
        if fulfillment:
            fulfillment_user = fulfillment.get('user', {});
            fulfillment_fields = fulfillment.get('fields')
            fulfillment_fields_json = json.dumps(fulfillment_fields) if fulfillment_fields else None
            fulfillment_type = fulfillment.get('type')
            fulfillment_date_completed = parse_zenput_date(fulfillment.get('date_completed'))
            fulfillment_date_submitted = parse_zenput_date(fulfillment.get('date_submitted'))
            fulfillment_user_id = fulfillment_user.get('id')
            fulfillment_user_display_name = fulfillment_user.get('display_name')
        subscribers_json = json.dumps(task.get('subscribers')) if task.get('subscribers') else None
        data_to_insert.append((
            task.get('id'), task.get('title'), task.get('description'), company.get('id'),
            account.get('id') if account else None, account.get('name') if account else None,
            account.get('address') if account else None,
            account.get('city') if account else None, account.get('state') if account else None,
            account.get('zipcode') if account else None, account.get('country') if account else None,
            account.get('lat') if account else None, account.get('lon') if account else None,
            status.get('id'), status.get('type'), status.get('name'), reply.get('type'), reporter.get('id'),
            reporter.get('display_name'),
            assignee.get('id'), assignee.get('display_name'), parse_zenput_date(task.get('date_created')),
            parse_zenput_date(task.get('date_modified')), parse_zenput_date(task.get('date_start')),
            parse_zenput_date(task.get('date_due')),
            task.get('time_zone'), task.get('is_active'), task.get('is_closed'), project.get('id') if project else None,
            fulfillment_type, fulfillment_date_completed,
            fulfillment_date_submitted, fulfillment_user_id, fulfillment_user_display_name,
            fulfillment_fields_json, parse_zenput_date(task.get('date_submitted')), task.get('deleted'),
            task.get('num_comments'), task.get('is_completed_late'), task.get('current_state'),
            subscribers_json
        ))

    processed_count = 0
    connection = None  # Definir fuera del try para usar en finally
    cursor = None  # Definir fuera del try para usar en finally
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        query = """ INSERT INTO zenput_tasks (
                task_id, title, description, company_id, account_id, account_name, account_address, account_city, account_state, account_zipcode, account_country, account_lat, account_lon,
                status_id, status_type, status_name, reply_type, reporter_id, reporter_display_name, assignee_id, assignee_display_name, date_created, date_modified, date_start, date_due,
                time_zone, is_active, is_closed, project_id, fulfillment_type, fulfillment_date_completed, fulfillment_date_submitted, fulfillment_user_id, fulfillment_user_display_name,
                fulfillment_fields, date_submitted, deleted, num_comments, is_completed_late, current_state, subscribers
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) 
            ON DUPLICATE KEY UPDATE
                title=VALUES(title), description=VALUES(description), company_id=VALUES(company_id), account_id=VALUES(account_id), account_name=VALUES(account_name), account_address=VALUES(account_address), account_city=VALUES(account_city), account_state=VALUES(account_state), account_zipcode=VALUES(account_zipcode), account_country=VALUES(account_country), account_lat=VALUES(account_lat), account_lon=VALUES(account_lon),
                status_id=VALUES(status_id), status_type=VALUES(status_type), status_name=VALUES(status_name), reply_type=VALUES(reply_type), reporter_id=VALUES(reporter_id), reporter_display_name=VALUES(reporter_display_name), assignee_id=VALUES(assignee_id), assignee_display_name=VALUES(assignee_display_name), date_created=VALUES(date_created), date_modified=VALUES(date_modified), date_start=VALUES(date_start), date_due=VALUES(date_due),
                time_zone=VALUES(time_zone), is_active=VALUES(is_active), is_closed=VALUES(is_closed), project_id=VALUES(project_id), fulfillment_type=VALUES(fulfillment_type), fulfillment_date_completed=VALUES(fulfillment_date_completed), fulfillment_date_submitted=VALUES(fulfillment_date_submitted), fulfillment_user_id=VALUES(fulfillment_user_id), fulfillment_user_display_name=VALUES(fulfillment_user_display_name),
                fulfillment_fields=VALUES(fulfillment_fields), date_submitted=VALUES(date_submitted), deleted=VALUES(deleted), num_comments=VALUES(num_comments), is_completed_late=VALUES(is_completed_late), current_state=VALUES(current_state), subscribers=VALUES(subscribers); """

        # Convertimos task_id a string o None ANTES de ejecutar
        data_tuples = []
        for t in data_to_insert:
            # Reemplaza valores booleanos de Python con 0/1 para MySQL si es necesario
            processed_tuple = [
                (1 if v is True else (0 if v is False else v)) for v in t[1:]  # Excluye task_id
            ]
            task_id_str = str(t[0]) if t[0] is not None else None
            data_tuples.append((task_id_str, *processed_tuple))

        # --- LOGGING DETALLADO ---
        print(f"ℹ️ Intentando ejecutar 'executemany' con {len(data_tuples)} registros.")
        cursor.executemany(query, data_tuples)
        # -------------------------

        connection.commit()
        processed_count = cursor.rowcount
        print(f"✅ Se procesaron {processed_count} registros en 'zenput_tasks' (extendida).")

    except mysql.connector.Error as db_err:  # Captura errores específicos de MySQL
        print(f"❌❌ ERROR DE BASE DE DATOS al guardar tareas: {db_err}")
        # Opcional: Imprimir algunos datos que causaron el error si es útil
        # print("Primeros datos que intentaron guardarse:", data_tuples[:2])
        raise  # Lanzamos el error para que sincronizar_tareas sepa que falló
    except Exception as e:  # Captura otros errores inesperados
        print(f"❌ Error inesperado durante upsert_tasks: {e}")
        raise  # Lanza el error
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

    return processed_count


# --- 4. FUNCIÓN sincronizar_tareas ACTUALIZADA ---
def sincronizar_tareas():
    """Descarga TODAS las tareas usando paginación con 'start' y 'limit'."""
    print("\n--- Iniciando Sincronización COMPLETA de Tareas ---")
    run_start_time = datetime.now(timezone.utc)  # Guardamos hora de inicio

    # Ya no necesitamos leer el timestamp anterior
    # last_success_time = get_last_run_timestamp(TIMESTAMP_FILE)
    # updated_since_str = last_success_time.strftime('%Y-%m-%dT%H:%M:%SZ')

    setup_tasks_table()

    # Parámetros solo con limit (start se manejará en el bucle)
    params = {
        'limit': 100  # Puedes aumentar esto hasta 10000 si quieres menos llamadas
    }

    page_limit = params.get('limit', 100)
    start_offset = 0  # Usaremos 'start' como el offset
    total_count_reported = -1
    all_tasks = []

    base_url = ZENPUT_API_ENDPOINTS.get('list_tasks')
    if not base_url:
        print("❌ No se encontró la URL para 'list_tasks'.");
        return

    is_first_page = True
    success = False

    try:
        print(f"📥 Descargando TODAS las tareas (límite por página: {page_limit})...")

        while True:
            current_params = params.copy()
            current_params['start'] = start_offset  # Usamos 'start' para el offset

            response = requests.get(base_url, headers=ZENPUT_HEADERS, params=current_params)
            # Imprimimos menos para reducir ruido en logs largos
            if start_offset % (10 * page_limit) == 0:  # Imprime cada 10 páginas
                print(f"  - Descargando con start={start_offset}, Código: {response.status_code}")

            if response.status_code == 429:
                print("⚠️ Límite de tasa. Esperando 60s...");
                time.sleep(60);
                continue

            response.raise_for_status()

            try:
                data = response.json()
            except requests.exceptions.JSONDecodeError:
                print(f"❌ ERROR DE JSON: Código: {response.status_code}. Texto: '{response.text}'");
                break

            if is_first_page:
                total_count_reported = data.get('count', -1)
                print(
                    f"  - Conteo total reportado (info): {total_count_reported if total_count_reported != -1 else 'No disponible'}")
                is_first_page = False
                if total_count_reported == 0:
                    print("  - API reporta 0 tareas en total. Deteniendo.")
                    break

            page_tasks = data.get('results', [])

            if not page_tasks:
                print(
                    f"  - No se encontraron más tareas (start={start_offset}, 'results' vacío). Paginación completada.");
                break

            all_tasks.extend(page_tasks)

            # Condición de parada: Si recibimos menos tareas que el límite
            if len(page_tasks) < page_limit:
                print(
                    f"  - Recibidas {len(page_tasks)} tareas (< {page_limit}). Última página alcanzada (start={start_offset}).")
                break

            start_offset += page_limit  # Incrementamos 'start' para la siguiente página
            time.sleep(0.2)  # Pausa muy corta

        print(f"👍 Descarga finalizada. Se encontraron {len(all_tasks)} tareas en total.")

        if all_tasks:
            print(f"💾 Guardando/Actualizando {len(all_tasks)} tareas en la base de datos...")
            processed_count = upsert_tasks(all_tasks)
            print(f"✅ Guardado completado. Filas afectadas: {processed_count}")
            success = True  # Si upsert no lanzó error, consideramos éxito
        else:
            print("ℹ️ No hay tareas para guardar.");
            success = True

    except Exception as e:
        print(f"❌❌ ERROR CRÍTICO: {e}")
        import traceback;
        traceback.print_exc();
        success = False
    finally:
        # Ya no guardamos timestamp porque siempre hacemos full refresh
        # if success:
        #    save_current_timestamp(TIMESTAMP_FILE, run_start_time)
        # else:
        #    print("❌ Proceso no completado exitosamente.")
        if not success:
            print("❌ Proceso no completado exitosamente.")


# --- 5. ORQUESTADOR PRINCIPAL (Sin cambios) ---
def main():
    print("🚀 Iniciando Proceso ETL de Tareas de Zenput...")
    sincronizar_tareas()  # Ya no necesita 'dias_atras'
    print("\n🏁 Proceso ETL de Tareas finalizado.")


if __name__ == '__main__':
    main()