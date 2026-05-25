import mysql.connector
from zeep import Client
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import sys
import os

from dotenv import load_dotenv
# 1. Le decimos a Python que incluya la carpeta raíz en su ruta de búsqueda
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ── cargar .env desde carpeta padre ──────────────
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(dotenv_path)

# 2. Ahora sí podemos importar nuestra función
from core.database.mysql import get_db_connection

# Configuración de la conexión a MySQL
db_connection = get_db_connection(target="wansoft")
#db_connection = mysql.connector.connect(
#    host='localhost',
#    user='root',
#    password='',
#    database='wansoft'
#)
cursor = db_connection.cursor()

# Definir rango de fechas
start_date_range = datetime.now() - timedelta(days=31)
end_date_range = datetime.now() - timedelta(days=1)

# Verificar si la tabla cost_reports existe y si no, crearla
cursor.execute("""
    CREATE TABLE IF NOT EXISTS gettablajeriareport (
        id INT AUTO_INCREMENT PRIMARY KEY,
        subsidiary_id INT,
        subsidiary_name VARCHAR(255),
        InputDate DATE,
        UserName VARCHAR(255),
        QuantityOfBaseProduct DECIMAL(15,10),
        ProductBase VARCHAR(255),
        ProductBaseCost DECIMAL(15,4),
        UnitOfMeasureOfBaseProduct VARCHAR(50),
        QuantityDecrease DECIMAL(15,10),
        Warehouse VARCHAR(255),
        QuantityOfGeneratedProduct DECIMAL(15,10),
        GeneratedProduct VARCHAR(255),
        UnitCostOfGeneratedProduct DECIMAL(15,10),
        totalCostOfGeneratedProduct DECIMAL(15,10),
        RegistrationDate DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
db_connection.commit()

# Initialize SOAP client
client = Client('https://www.wansoft.net/wansoft.web/API/IntegrationService.asmx?wsdl')

# List of subsidiaries and their credentials
subsidiaries = [
    {"id":5320, "nombreCorto":"Acoxpa", "password": os.getenv("WANSOFT_PWD_5320"),  'name': "Fonda Argentina - Acoxpa"},
    {"id":4959, "nombreCorto":"Aeropuerto", "password": os.getenv("WANSOFT_PWD_4959"),  'name': "Fonda Argentina - Aeropuerto"},
    {"id":4958, "nombreCorto":"Isabel La Católica", "password": os.getenv("WANSOFT_PWD_4958"),  'name': "Fonda Argentina - Isabel La Católica"},
    {"id":4960, "nombreCorto":"Antenas", "password": os.getenv("WANSOFT_PWD_4960"),  'name': "Fonda Argentina - Antenas"},
    {"id":5321, "nombreCorto":"Taquería parroquia", "password": os.getenv("WANSOFT_PWD_5321"),  'name': "Fonda Argentina – Taquería Parroquía"},
    {"id":5318, "nombreCorto":"Vía Vallejo", "password": os.getenv("WANSOFT_PWD_5318"),  'name': "Fonda Argentina – Vía Vallejo"},
    {"id":4961, "nombreCorto":"Viaducto", "password": os.getenv("WANSOFT_PWD_4961"),  'name': "Fonda Argentina - Viaducto"},
    {"id":4962, "nombreCorto":"Taquería Viaducto", "password": os.getenv("WANSOFT_PWD_4962"),  'name': "Fonda Argentina - Taqueria Viaducto"},
    {"id":5319, "nombreCorto":"San Jeronimo", "password": os.getenv("WANSOFT_PWD_5319"),  'name': "Fonda Argentina – San Jerónimo"},
    {"id":6560, "nombreCorto":"Tepeyac", "password": os.getenv("WANSOFT_PWD_6560"),  'name': "Fonda Argentina - Tepeyac"},
    {"id":7697, "nombreCorto":"Taq San Fernando", "password": os.getenv("WANSOFT_PWD_7697"),  'name': "Fonda Argentina - Taqueria San Fernando"},
    {"id":6174, "nombreCorto":"Playa del Carmen", "password": os.getenv("WANSOFT_PWD_6174"),  'name': "Fonda Argentina - Playa del Carmen"},
    {"id":5943, "nombreCorto":"Oceanía", "password": os.getenv("WANSOFT_PWD_5943"),  'name': "Fonda Argentina - Oceanía"},
    {"id":6175, "nombreCorto":"Cancun", "password": os.getenv("WANSOFT_PWD_6175"),  'name': "Fonda Argentina - Cancún"},
    {"id":4433, "nombreCorto":"Napoles", "password": os.getenv("WANSOFT_PWD_4433"),  'name': "Fonda Argentina - Nápoles"},
    {"id":4752, "nombreCorto":"Metepec", "password": os.getenv("WANSOFT_PWD_4752"),  'name': "Fonda Argentina - Tollocan"},
    {"id":5396, "nombreCorto":"Versalles", "password": os.getenv("WANSOFT_PWD_5396"),  'name': "Fonda Argentina - Taquería Exhibimex"},
    {"id":12057, "nombreCorto": "La Esquina Coyoacán", "name":"Fonda Argentina - Coyoacan", "password": os.getenv("WANSOFT_PWD_12057")},
    {"id":12802, "nombreCorto": "CentroMyJ", "name":"Fonda Argentina - Centro Mario y July", "password": os.getenv("WANSOFT_PWD_12802")},
    {"id":12806, "nombreCorto": "Puebla", "name":"Fonda Argentina - Puebla", "password": os.getenv("WANSOFT_PWD_12806")}
]
print(subsidiaries)


# Funciones auxiliares para conversión
def safe_float(value, default=0.0):
    try:
        return float(value) if value else default
    except:
        return default


def safe_date(date_str):
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        return None


# Procesamiento principal
for subsidiary in subsidiaries:
    current_date = start_date_range
    while current_date <= end_date_range:
        current_date_str = current_date.strftime("%Y-%m-%d")

        try:
            print(f"Consultando tablajería de {subsidiary['name']} para {current_date_str}")
            response = client.service.GetTablajeriaReport_Xml(
                subsidiaryId=subsidiary['id'],
                pwdWebService=subsidiary['password'],
                operationdate=current_date_str
            )
            print(response)

            if response:
                # Extraer el XML de la respuesta SOAP
                root_soap = ET.fromstring(response)

                if True:

                    # Procesar cada registro de tablajería
                    for tablajeria in root_soap.findall('.//Tablajeria'):
                        attrs = tablajeria.attrib

                        # Preparar datos
                        data = {
                            'subsidiary_id': subsidiary['id'],
                            'subsidiary_name': subsidiary['name'],
                            'InputDate': safe_date(attrs.get('InputDate')),
                            'UserName': attrs.get('UserName'),
                            'QuantityOfBaseProduct': safe_float(attrs.get('QuantityOfBaseProduct')),
                            'ProductBase': attrs.get('ProductBase'),
                            'ProductBaseCost': safe_float(attrs.get('ProductBaseCost')),
                            'UnitOfMeasureOfBaseProduct': attrs.get('UnitOfMeasureOfBaseProduct'),
                            'QuantityDecrease': safe_float(attrs.get('QuantityDecrease')),
                            'Warehouse': attrs.get('Warehouse'),
                            'QuantityOfGeneratedProduct': safe_float(attrs.get('QuantityOfGeneratedProduct')),
                            'GeneratedProduct': attrs.get('GeneratedProduct'),
                            'UnitCostOfGeneratedProduct': safe_float(attrs.get('UnitCostOfGeneratedProduct')),
                            'totalCostOfGeneratedProduct': safe_float(attrs.get('totalCostOfGeneratedProduct')),
                            'RegistrationDate': safe_date(attrs.get('RegistrationDate'))
                        }

                        # Verificar si ya existe
                        cursor.execute("""
                            SELECT id 
                            FROM gettablajeriareport 
                            WHERE InputDate = %s 
                                AND ProductBase = %s 
                                AND GeneratedProduct = %s 
                                AND subsidiary_id = %s
                                AND QuantityOfBaseProduct = %s
                                AND QuantityDecrease = %s
                                AND QuantityOfGeneratedProduct = %s
                        """, (
                            data['InputDate'],
                            data['ProductBase'],
                            data['GeneratedProduct'],
                            subsidiary['id'],
                            data['QuantityOfBaseProduct'],
                            data['QuantityDecrease'],
                            data['QuantityOfGeneratedProduct']
                        ))
                        existing = cursor.fetchone()

                        if existing:
                            # Actualizar registro existente
                            update_query = """
                                UPDATE gettablajeriareport SET
                                    UserName = %s,
                                    QuantityOfBaseProduct = %s,
                                    ProductBaseCost = %s,
                                    UnitOfMeasureOfBaseProduct = %s,
                                    QuantityDecrease = %s,
                                    Warehouse = %s,
                                    QuantityOfGeneratedProduct = %s,
                                    UnitCostOfGeneratedProduct = %s,
                                    totalCostOfGeneratedProduct = %s,
                                    RegistrationDate = %s
                                WHERE id = %s
                            """
                            cursor.execute(update_query, (
                                data['UserName'],
                                data['QuantityOfBaseProduct'],
                                data['ProductBaseCost'],
                                data['UnitOfMeasureOfBaseProduct'],
                                data['QuantityDecrease'],
                                data['Warehouse'],
                                data['QuantityOfGeneratedProduct'],
                                data['UnitCostOfGeneratedProduct'],
                                data['totalCostOfGeneratedProduct'],
                                data['RegistrationDate'],
                                existing[0]
                            ))
                            print(
                                f"[🔁] Actualizado registro de tablajería en {subsidiary['name']} para {data['InputDate']}")
                        else:
                            # Insertar nuevo registro
                            insert_query = """
                                INSERT INTO gettablajeriareport (
                                    subsidiary_id, subsidiary_name, InputDate, UserName, 
                                    QuantityOfBaseProduct, ProductBase, ProductBaseCost, 
                                    UnitOfMeasureOfBaseProduct, QuantityDecrease, Warehouse, 
                                    QuantityOfGeneratedProduct, GeneratedProduct, 
                                    UnitCostOfGeneratedProduct, totalCostOfGeneratedProduct, 
                                    RegistrationDate
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """
                            cursor.execute(insert_query, (
                                data['subsidiary_id'],
                                data['subsidiary_name'],
                                data['InputDate'],
                                data['UserName'],
                                data['QuantityOfBaseProduct'],
                                data['ProductBase'],
                                data['ProductBaseCost'],
                                data['UnitOfMeasureOfBaseProduct'],
                                data['QuantityDecrease'],
                                data['Warehouse'],
                                data['QuantityOfGeneratedProduct'],
                                data['GeneratedProduct'],
                                data['UnitCostOfGeneratedProduct'],
                                data['totalCostOfGeneratedProduct'],
                                data['RegistrationDate']
                            ))
                            print(
                                f"[🆕] Insertado registro de tablajería en {subsidiary['name']} para {data['InputDate']}")

                        db_connection.commit()
            else:
                print(f"Sin respuesta para {subsidiary['name']} ({current_date_str})")

        except Exception as e:
            print(f"Error en {subsidiary['name']} {current_date_str}: {str(e)[:200]}")
            # Consumir cualquier resultado pendiente
            while cursor.fetchone() is not None:
                pass
            db_connection.rollback()

        current_date += timedelta(days=1)

cursor.close()
db_connection.close()