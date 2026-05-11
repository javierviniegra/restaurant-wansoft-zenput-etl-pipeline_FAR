import os

import mysql.connector
from zeep import Client
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import sys

from dotenv import load_dotenv
# 1. Le decimos a Python que incluya la carpeta raíz en su ruta de búsqueda
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ── cargar .env desde carpeta padre ──────────────
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(dotenv_path)

# 2. Ahora sí podemos importar nuestra función
from config.database import get_db_connection

# Configuración de la conexión a MySQL
db_connection = get_db_connection(target="wansoft")
cursor = db_connection.cursor()

# Fechas de inicio y fin (puedes cambiarlas fuera del loop)
start_date_range = datetime.now() - timedelta(days=30)  # Fecha inicial
end_date_range = datetime.now() - timedelta(days=1)    # Fecha final
#start_date_range = datetime(2025, 6,3)  # Fecha inicial
#end_date_range = datetime(2025, 6, 3)    # Fecha final

# Verificar si la tabla cost_reports existe y si no, crearla
cursor.execute("""
    CREATE TABLE IF NOT EXISTS costeoMensual (
        id INT AUTO_INCREMENT PRIMARY KEY,
        subsidiary_id INT,
        subsidiary_name VARCHAR(255),
        CostoTotal DECIMAL(10,2),
        CostoDeProductosVendidos DECIMAL(10,2),
        CostoIdealDeProductosPendientesDeRebaja DECIMAL(10,2),
        CostoDeCortesías DECIMAL(10,2),
        CostoDeCancelaciones DECIMAL(10,2),
        CostoDeMerma DECIMAL(10,2),
        CostoDeDesperdicio DECIMAL(10,2),
        CostoDeRobo DECIMAL(10,2),
        CostoDeConsumo DECIMAL(10,2),
        AjustePorSobrantes DECIMAL(10,2),
        UtilidadMarginal DECIMAL(10,2),
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
print(subsidiaries)

# Loop para obtener datos de cada subsidiaria
for subsidiary in subsidiaries:
    current_date = start_date_range
    while current_date <= end_date_range:
        # Calcular las fechas de inicio y fin del mes
        #start_date = current_date.replace(day=1)
        #next_month = start_date.month % 12 + 1
        #year_increment = 1 if next_month == 1 else 0
        #end_date = (start_date.replace(month=next_month, year=start_date.year + year_increment) - timedelta(days=1))
        start_date = current_date#.replace(day=1)
        end_date = end_date_range #(start_date.replace(month=next_month, year=start_date.year + year_increment) - timedelta(days=1))

        # Asegurarse de que la fecha de fin no exceda el rango total deseado
        if end_date > end_date_range:
            end_date = end_date_range

        # Convertir las fechas a strings
        start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%S")
        end_date_str = end_date.strftime("%Y-%m-%dT%H:%M:%S")

        fecha = current_date# - timedelta(days=1)
        fecha_str = fecha.strftime("%Y-%m-%d %H:%M:%S")
        fecha_str = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")

        # Calcular el valor de mes-año en formato "MM-YYYY"
        mes_ano = fecha.strftime("%m-%Y")

        try:
            # Llama al método GetCostReport_Xml con el rango de fechas del mes
            response = client.service.GetCostReport_Xml(
                subsidiaryId=subsidiary['id'],
                pwdWebService=subsidiary['password'],
                startDate = current_date.replace(day=1),
                endDate = start_date.strftime("%Y-%m-%dT%H:%M:%S")
            )

            # Parse the response
            if response:
                root = ET.fromstring(response)

                # Encuentra todos los nodos 'DetalleCostos' y extrae los atributos
                for cost_detail in root.findall('.//DetalleCostos'):
                    cost_detail_dict = cost_detail.attrib
                    cost_detail_dict['subsidiary_id'] = subsidiary['id']
                    cost_detail_dict['subsidiary_name'] = subsidiary['name']
                    total_costo = float(cost_detail_dict['CostoTotal'])
                    total_productos_costo = float(cost_detail_dict['CostoDeProductosVendidos'])

                    # ----- reviso si el registro ya existe
                    cursor.execute("""
                        SELECT id,CostoTotal,CostoDeProductosVendidos FROM costeoMensual
                        WHERE subsidiary_id = %s AND DATE(created_at) = %s
                    """, (subsidiary['id'], fecha.strftime("%Y-%m-%d")))

                    row = cursor.fetchone()
                    # -FIN-- reviso si el registro ya existe

                    if row: # Si existe el registro
                        record_id, total_db, productos_db = row
                        print(f"El costo total descargado es: {total_costo}, el costo de productos vendidos descargado es: {total_productos_costo}y el de la bd es {total_db}")
                        if ((abs(total_costo - float(total_db)) > 0.01) or (abs(total_productos_costo - float(productos_db)) > 0.01)):
                            # Definir la query para insertar en MySQL
                            query = """
                                UPDATE costeoMensual
                                SET
                                    subsidiary_name = %s,
                                    CostoTotal = %s,
                                    CostoDeProductosVendidos = %s,
                                    CostoIdealDeProductosPendientesDeRebaja = %s,
                                    CostoDeCortesías = %s,
                                    CostoDeCancelaciones = %s,
                                    CostoDeMerma = %s,
                                    CostoDeDesperdicio = %s,
                                    CostoDeRobo = %s,
                                    CostoDeConsumo = %s,
                                    AjustePorSobrantes = %s,
                                    UtilidadMarginal = %s,
                                    mes_ano = %s
                                    WHERE CAST(created_at as date) = %s and subsidiary_id = %s
                            """

                            # Datos que se actualizarán en la tabla
                            data = (
                                cost_detail_dict['subsidiary_name'],
                                cost_detail_dict['CostoTotal'],
                                cost_detail_dict['CostoDeProductosVendidos'],
                                cost_detail_dict['CostoIdealDeProductosPendientesDeRebaja'],
                                cost_detail_dict['CostoDeCortesías'],
                                cost_detail_dict['CostoDeCancelaciones'],
                                cost_detail_dict['CostoDeMerma'],
                                cost_detail_dict['CostoDeDesperdicio'],
                                cost_detail_dict['CostoDeRobo'],
                                cost_detail_dict['CostoDeConsumo'],
                                cost_detail_dict['AjustePorSobrantes'],
                                cost_detail_dict['UtilidadMarginal'],
                                mes_ano, # Insertar el valor de mes-año calculado
                                fecha.strftime("%Y-%m-%d"),
                                cost_detail_dict['subsidiary_id']
                            )

                            # Ejecutar la query para actualizar los datos en MySQL
                            cursor.execute(query, data)

                            query_debug = query % tuple(repr(d) for d in data)
                            print("Query final:", query_debug)

                            print(f"[🔁] Actualizado: {subsidiary['nombreCorto']} - {fecha_str}")
                        else:
                            print(f"[✔] Igual: {subsidiary['nombreCorto']} - {fecha_str}")
                    else: #no existe lo guardo
                        print(f"[⚠] No existe en DB - {subsidiary['nombreCorto']} ({fecha_str})")
                        # Definir la query para insertar en MySQL
                        query = """
                        INSERT INTO costeoMensual (subsidiary_id, subsidiary_name, CostoTotal, CostoDeProductosVendidos,
                        CostoIdealDeProductosPendientesDeRebaja, CostoDeCortesías, CostoDeCancelaciones, CostoDeMerma,
                        CostoDeDesperdicio, CostoDeRobo, CostoDeConsumo, AjustePorSobrantes, UtilidadMarginal, mes_ano, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """

                        # Datos que se insertarán en la tabla
                        data = (
                            cost_detail_dict['subsidiary_id'],
                            cost_detail_dict['subsidiary_name'],
                            cost_detail_dict.get('CostoTotal', 0.00),
                            cost_detail_dict.get('CostoDeProductosVendidos', 0.00),
                            cost_detail_dict.get('CostoIdealDeProductosPendientesDeRebaja', 0.00),
                            cost_detail_dict.get('CostoDeCortesías', 0.00),
                            cost_detail_dict.get('CostoDeCancelaciones', 0.00),
                            cost_detail_dict.get('CostoDeMerma', 0.00),
                            cost_detail_dict.get('CostoDeDesperdicio', 0.00),
                            cost_detail_dict.get('CostoDeRobo', 0.00),
                            cost_detail_dict.get('CostoDeConsumo', 0.00),
                            cost_detail_dict.get('AjustePorSobrantes', 0.00),
                            cost_detail_dict.get('UtilidadMarginal', 0.00),
                            mes_ano,  # Insertar el valor de mes-año calculado
                            fecha_str
                        )

                        # Ejecutar la query para insertar los datos en MySQL
                        cursor.execute(query, data)

                    # Confirmar la transacción en la base de datos
                    db_connection.commit()

                    print(f"Cost report for subsidiary {subsidiary['id']} from {start_date_str} to {end_date_str} processed and stored.")
            else:
                print(f"No cost report received for subsidiary {subsidiary['id']} from {start_date_str} to {end_date_str}")

        except Exception as e:
            print(f"An error occurred while fetching cost report for subsidiary {subsidiary['id']} from {start_date_str} to {end_date_str}: {e}")

        # Incrementa el current_date al siguiente mes
        #current_date = (start_date.replace(month=next_month, year=start_date.year + year_increment))
        current_date = current_date + timedelta(days=1)

# Cerrar la conexión a la base de datos
cursor.close()
db_connection.close()
