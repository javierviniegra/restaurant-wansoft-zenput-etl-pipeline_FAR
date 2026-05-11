import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# 1. Obtenemos la ruta absoluta de la carpeta donde está ESTE archivo (database.py)
# Como database.py estará en la raíz, BASE_DIR será la raíz de tu proyecto.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Construimos la ruta exacta al archivo .env
ENV_PATH = os.path.join(BASE_DIR, '.env')

# 3. Le decimos explícitamente a dotenv que cargue ESE archivo
load_dotenv(dotenv_path=ENV_PATH)

def get_db_connection(target="wansoft"):
    """
    Crea y retorna una conexión a MySQL dependiendo del objetivo.
    target: 'wansoft' o 'zenput'
    """
    try:
        if target == "zenput":
            connection = mysql.connector.connect(
                host=os.getenv("DB_HOST_ZENPUT"),
                user=os.getenv("DB_USER_ZENPUT"),
                password=os.getenv("DB_PASS_ZENPUT"),
                database=os.getenv("DB_NAME_ZENPUT")
            )
        else:
            # Por defecto conecta a Wansoft
            connection = mysql.connector.connect(
                host=os.getenv("DB_HOST_WANSOFT"),
                user=os.getenv("DB_USER_WANSOFT"),
                password=os.getenv("DB_PASS_WANSOFT"),
                database=os.getenv("DB_NAME_WANSOFT")
            )
        return connection
    except Error as e:
        print(f"❌ Error conectando a la BD {target}: {e}")
        return None