import os

import mysql.connector
from mysql.connector import Error
import numpy as np
import pandas as pd
import requests
from datetime import datetime
from datetime import timedelta
import json

import sys

from dotenv import load_dotenv
# 1. Le decimos a Python que incluya la carpeta raíz en su ruta de búsqueda
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ── cargar .env desde carpeta padre ──────────────
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(dotenv_path)

# 2. Ahora sí podemos importar nuestra función
from core.database.database import get_db_connection
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

# ## Acceso a la base de datos


# Diccionario de Endpoints de la API de Zenput
ZENPUT_API_ENDPOINTS = {
    'list_form_templates': "https://www.zenput.com/api/v1/forms/list_templates/?start=0&limit=20",
    'get_submissions': "https://www.zenput.com/api/v3/submissions?form_template_id={}"
}

# Configuración de la API de Zenput
ZENPUT_API_TOKEN = os.getenv("ZENPUT_API_TOKEN")  # Asegúrate de configurar esta variable de entorno con tu token real

# Headers de autenticación (sin cambios)
ZENPUT_HEADERS = {
    "accept": "application/json",
    "X-API-TOKEN": ZENPUT_API_TOKEN  # Usa tu token real
}


# # Formularios


# --- 2. FUNCIONES PARA PLANTILLAS DE FORMULARIOS (SIN CAMBIOS) ---
def setup_forms_table():
    # ... (código de la función sin cambios)
    try:
        connection = get_db_connection(target="zenput")
        cursor = connection.cursor()
        create_table_query = """
        CREATE TABLE IF NOT EXISTS form_templates (
            form_id INT PRIMARY KEY, title VARCHAR(255), num_submissions INT, date_created DATETIME,
            date_last_submitted DATETIME, creator_full_name VARCHAR(255), category_name VARCHAR(255),
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        );"""
        cursor.execute(create_table_query)
        print("✅ Tabla 'form_templates' verificada/creada.")
    except Error as e:
        print(f"❌ Error al configurar la tabla de formularios: {e}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()


def upsert_form_templates(form_data):
    # ... (código de la función sin cambios)
    if not form_data:
        print("ℹ️ No hay plantillas de formularios para procesar.")
        return

    def parse_zenput_date(date_dict):
        if not date_dict or '$date' not in date_dict: return None
        return datetime.fromtimestamp(date_dict['$date'] / 1000)

    try:
        connection = get_db_connection(target="zenput")
        cursor = connection.cursor()
        query = """
            INSERT INTO form_templates (form_id, title, num_submissions, date_created, date_last_submitted, creator_full_name, category_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                title = VALUES(title), num_submissions = VALUES(num_submissions), date_last_submitted = VALUES(date_last_submitted),
                creator_full_name = VALUES(creator_full_name), category_name = VALUES(category_name);
        """
        data_to_insert = [(form.get('id'), form.get('title'), form.get('num_submissions'),
                           parse_zenput_date(form.get('date_created')),
                           parse_zenput_date(form.get('date_last_submitted')), form.get('creator_full_name'),
                           form.get('category_name')) for form in form_data]
        cursor.executemany(query, data_to_insert)
        connection.commit()
        print(f"✅ Se procesaron {cursor.rowcount} registros en 'form_templates'.")
    except Error as e:
        print(f"❌ Error al guardar datos de formularios: {e}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()


# --- 3. NUEVAS FUNCIONES PARA SUBMISSIONS Y RESPUESTAS ---

def setup_submissions_tables():
    """Crea las tablas para 'submissions' y 'submission_answers' si no existen."""
    try:
        connection = get_db_connection(target="zenput")
        cursor = connection.cursor()

        # Tabla para la metadata de cada submission
        create_submissions_table = """
        CREATE TABLE IF NOT EXISTS submissions (
            submission_id VARCHAR(255) PRIMARY KEY,
            form_template_id INT,
            location_name VARCHAR(255),
            user_display_name VARCHAR(255),
            date_submitted DATETIME,
            time_to_complete INT,
            FOREIGN KEY (form_template_id) REFERENCES form_templates(form_id)
        );
        """

        # Tabla para cada respuesta individual dentro de una submission
        create_answers_table = """
        CREATE TABLE IF NOT EXISTS submission_answers (
            answer_id INT AUTO_INCREMENT PRIMARY KEY,
            submission_id VARCHAR(255),
            field_id INT,
            title TEXT,
            field_type VARCHAR(50),
            value_as_string TEXT,
            FOREIGN KEY (submission_id) REFERENCES submissions(submission_id)
        );
        """
        cursor.execute(create_submissions_table)
        cursor.execute(create_answers_table)
        print("✅ Tablas 'submissions' y 'submission_answers' verificadas/creadas.")

    except Error as e:
        print(f"❌ Error al configurar las tablas de submissions: {e}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()


def get_answer_value(answer):
    """Extrae el valor de una respuesta, sin importar su tipo, y lo convierte a string."""
    field_type = answer.get('field_type')
    value = answer.get(f"{field_type}_value")
    if value is None:
        return None
    # Si el valor es una lista (ej. en fotos), lo convertimos a un string JSON
    if isinstance(value, list) or isinstance(value, dict):
        return json.dumps(value)
    return str(value)


def upsert_submissions_and_answers(submissions_data, form_id):
    """Guarda los datos de submissions y sus respuestas en las tablas correspondientes."""
    if not submissions_data:
        return

    submissions_to_insert = []
    answers_to_insert = []

    for sub in submissions_data:
        smetadata = sub.get('smetadata', {})
        location = smetadata.get('location', {})
        created_by = smetadata.get('created_by', {})

        # Prepara los datos para la tabla 'submissions'
        submissions_to_insert.append((
            sub.get('id'),
            form_id,
            location.get('name'),
            created_by.get('display_name'),
            smetadata.get('date_submitted'),
            smetadata.get('time_to_complete')
        ))

        # Prepara los datos para la tabla 'submission_answers'
        for ans in sub.get('answers', []):
            if ans.get('is_answered'):
                answers_to_insert.append((
                    sub.get('id'),
                    ans.get('field_id'),
                    ans.get('title'),
                    ans.get('field_type'),
                    get_answer_value(ans)  # Usamos la función auxiliar
                ))

    try:
        connection = get_db_connection(target="zenput")
        cursor = connection.cursor()

        # Upsert para la tabla 'submissions'
        sub_query = """
            INSERT INTO submissions (submission_id, form_template_id, location_name, user_display_name, date_submitted, time_to_complete)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                location_name = VALUES(location_name), user_display_name = VALUES(user_display_name), 
                date_submitted = VALUES(date_submitted), time_to_complete = VALUES(time_to_complete);
        """
        cursor.executemany(sub_query, submissions_to_insert)
        print(f"  - Se procesaron {cursor.rowcount} registros en 'submissions'.")

        # Para las respuestas, es más simple borrar las antiguas e insertar las nuevas para un submission dado.
        # Esto evita lógica compleja de updates y mantiene la consistencia.
        submission_ids_to_update = [s[0] for s in submissions_to_insert]
        if submission_ids_to_update:
            # Creamos placeholders (%s) para cada ID
            placeholders = ', '.join(['%s'] * len(submission_ids_to_update))
            cursor.execute(f"DELETE FROM submission_answers WHERE submission_id IN ({placeholders})",
                           tuple(submission_ids_to_update))

        ans_query = """
            INSERT INTO submission_answers (submission_id, field_id, title, field_type, value_as_string)
            VALUES (%s, %s, %s, %s, %s);
        """
        cursor.executemany(ans_query, answers_to_insert)
        print(f"  - Se procesaron {cursor.rowcount} registros en 'submission_answers'.")

        connection.commit()

    except Error as e:
        print(f"❌ Error al guardar submissions y respuestas: {e}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()


# --- 4. ORQUESTADOR PRINCIPAL ---

def main():
    """Función principal que orquesta todo el proceso ETL."""
    print("🚀 Iniciando Proceso ETL Completo de Zenput...")

    # --- Parte 1: Sincronizar Plantillas de Formularios ---
    print("\n--- Fase 1: Sincronizando Plantillas de Formularios ---")
    setup_forms_table()

    url_templates = ZENPUT_API_ENDPOINTS.get('list_form_templates')
    try:
        response = requests.get(url_templates, headers=ZENPUT_HEADERS)
        response.raise_for_status()
        form_templates = response.json().get('results', [])
        print(f"👍 Se encontraron {len(form_templates)} plantillas de formularios.")
        upsert_form_templates(form_templates)
    except Exception as e:
        print(f"❌ Falló la descarga de plantillas de formularios. Abortando. Error: {e}")
        return  # Si no podemos obtener los formularios, no continuamos.

    # --- Parte 2: Sincronizar Submissions para cada Formulario ---
    print("\n--- Fase 2: Sincronizando Submissions por Formulario ---")
    setup_submissions_tables()

    if not form_templates:
        print("ℹ️ No hay formularios para procesar. Finalizando.")
        return

    for form in form_templates:
        form_id = form.get('id')
        form_title = form.get('title')
        print(f"\n Procesando formulario: '{form_title}' (ID: {form_id})")

        all_submissions = []
        # Construimos la URL inicial para las submissions de este formulario
        next_page_url = ZENPUT_API_ENDPOINTS.get('get_submissions').format(form_id)

        # Bucle para manejar la paginación
        while next_page_url:
            try:
                print(f"  - Descargando desde: {next_page_url}")
                response = requests.get(next_page_url, headers=ZENPUT_HEADERS)
                response.raise_for_status()
                data = response.json()

                all_submissions.extend(data.get('data', []))

                # Obtenemos la URL de la siguiente página
                next_page_url = data.get('meta', {}).get('next')

            except Exception as e:
                print(f"❌ Error descargando submissions para el form_id {form_id}. Saltando al siguiente. Error: {e}")
                next_page_url = None  # Detenemos el bucle para este formulario si hay un error

        print(f"  - Total de {len(all_submissions)} submissions encontradas para este formulario.")
        # Guardamos los datos de submissions y respuestas en la base de datos
        upsert_submissions_and_answers(all_submissions, form_id)

    print("\n🏁 Proceso ETL finalizado.")


if __name__ == '__main__':
    main()