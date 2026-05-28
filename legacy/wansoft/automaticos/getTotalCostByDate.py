import mysql.connector
from zeep import Client
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import sys
import os


# 2. Ahora sí podemos importar nuestra función
from core.database.mysql import get_db_connection

# Configuración de la conexión a MySQL
db_connection = get_db_connection(target="wansoft")
cursor = db_connection.cursor()

# Fechas de inicio y fin (puedes cambiarlas fuera del loop)
start_date_range = datetime.now() - timedelta(days=1)
end_date_range = datetime.now() - timedelta(days=1)
#start_date_range = datetime(2025, 5,1)  # Fecha inicial
#end_date_range = datetime(2025, 6, 5)    # Fecha final

# Verificar si la tabla cost_reports existe y si no, crearla
cursor.execute("""
    CREATE TABLE IF NOT EXISTS getTotalCostByDate (
        id INT AUTO_INCREMENT PRIMARY KEY,
        subsidiary_id INT,
        subsidiary_name VARCHAR(255),
        CostoTotalVenta DECIMAL(10,2),
        mes_ano VARCHAR(7),  -- Nueva columna para almacenar el mes y año en formato MM-YYYY
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
from core.config.company_filter import is_wansoft_company

subsidiaries = [
    s for s in subsidiaries
    if is_wansoft_company(s["nombreCorto"])
]
print(subsidiaries)

#--------------------Reviso integridad
start_date_range = datetime.now() - timedelta(days=31)
end_date_range = datetime.now() - timedelta(days=1)


# Loop para obtener datos de cada subsidiaria
for subsidiary in subsidiaries:
    current_date = start_date_range
    while current_date <= end_date_range:
        # Convertir la fecha actual a string
        current_date_str = current_date.strftime("%Y-%m-%dT%H:%M:%S")

        # Calcular el valor de mes-año
        mes_ano = current_date.strftime("%m-%Y")

        # Fecha de inserción (día siguiente)
        fecha = current_date #+ timedelta(days=1)
        fecha_str = fecha.strftime("%Y-%m-%d %H:%M:%S")
        fecha_str = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")

        print(current_date_str)

        try:
            # Llama al método GetCostReport_Xml con la fecha del día
            response = client.service.GetTotalCostByDate(
                subsidiaryName=subsidiary['name'],
                pwdWebService=subsidiary['password'],
                operationdate=current_date_str
            )

            # Parse the response
            if response:
                root = ET.fromstring(response)

                # Encuentra todos los nodos 'DetalleCostos' y extrae los atributos
                for cost_detail in root.findall('.//CostosTotalesDeVenta'):
                    cost_detail_dict = cost_detail.attrib
                    cost_detail_dict['subsidiary_id'] = subsidiary['id']
                    cost_detail_dict['subsidiary_name'] = subsidiary['name']
                    total_costo = float(cost_detail_dict['Total'])
                    lafecha = fecha_str.strftime("%Y-%m-%d")

                    # ----- reviso si el registro ya existe
                    cursor.execute("""
                        SELECT id,CostoTotalVenta FROM gettotalcostbydate
                        WHERE subsidiary_id = %s AND CAST(created_at as date) = %s
                    """, (subsidiary['id'], lafecha))

                    row = cursor.fetchone()
                    # -FIN-- reviso si el registro ya existe

                    if row: # Si existe el registro
                        record_id, total_db = row
                        if abs(total_costo - float(total_db)) > 0.01:
                            query = """
                                UPDATE gettotalcostbydate SET
                                CostoTotalVenta = %s,
                                mes_ano = %s
                                WHERE subsidiary_id = %s AND DATE(created_at) = %s
                            """
                            # Datos que se insertarán en la tabla
                            data = ((
                                    total_costo,
                                    mes_ano, subsidiary['id'],lafecha))
                            # Ejecutar la query para insertar los datos en MySQL
                            cursor.execute(query, data)
                            print(f"[🔁] Actualizado: {subsidiary['nombreCorto']} - {fecha_str}")
                        else:
                            print(f"[✔] Igual: {subsidiary['nombreCorto']} - {fecha_str}")
                    else: #no existe lo guardo

                        # Definir la query para insertar en MySQL
                        query = """
                        INSERT INTO getTotalCostByDate (subsidiary_id, subsidiary_name, CostoTotalVenta, mes_ano, created_at)
                        VALUES (%s, %s, %s, %s, %s)
                        """

                        # Datos que se insertarán en la tabla
                        data = (
                            cost_detail_dict['subsidiary_id'],
                            cost_detail_dict['subsidiary_name'],
                            cost_detail_dict.get('Total', 0.00),
                            mes_ano,
                            fecha_str
                        )

                        # Ejecutar la query para insertar los datos en MySQL
                        cursor.execute(query, data)

                # Confirmar la transacción en la base de datos
                db_connection.commit()

                print(f"Cost report for subsidiary {subsidiary['id']} for {current_date_str} processed and stored.")
            else:
                print(f"No cost report received for subsidiary {subsidiary['id']} for {current_date_str}")

        except Exception as e:
            print(f"An error occurred while fetching cost report for subsidiary {subsidiary['id']} for {current_date_str}: {e}")

        # Incrementa al siguiente día
        current_date += timedelta(days=1)

# Cerrar la conexión a la base de datos
cursor.close()
db_connection.close()