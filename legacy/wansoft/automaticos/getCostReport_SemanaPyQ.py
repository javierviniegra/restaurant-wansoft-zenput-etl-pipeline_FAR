import mysql.connector
from zeep import Client
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import pandas as pd

import sys
import os

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# 2. Ahora sí podemos importar nuestra función
from core.database.mysql import get_db_connection

# Variables Globales

# List of subsidiaries and their credentials
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
from core.config.company_filter import is_wansoft_company

wansoft_subsidiaries = [
    s for s in subsidiaries
    if is_wansoft_company(s["nombreCorto"])
]
odoo_subsidiaries = [
    s for s in subsidiaries
    if not is_wansoft_company(s["nombreCorto"])
]

# Conexion a Base de Datos

# Configuración de la conexión a MySQL
db_connection = get_db_connection(target="wansoft")
cursor = db_connection.cursor()

# Verificar si la tabla cost_reports existe y si no, crearla
cursor.execute("""
    CREATE TABLE IF NOT EXISTS costeomensual_semanapyq (
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

# Conexion a la API

# Initialize SOAP client
from core.clients.wansoft_client import get_wansoft_client
client = get_wansoft_client()


# Función auxiliar para convertir valores a float eliminando comas
def safe_float(value, default=0.0):
    try:
        # Eliminar comas y convertir a float
        return float(value.replace(',', ''))
    except (ValueError, AttributeError):
        return default

#--------------------Reviso integridad
start_date_range = datetime.now() - timedelta(days=31)
end_date_range = datetime.now() - timedelta(days=1)

# Loop para obtener datos de cada subsidiaria (fuente Wansoft)
for subsidiary in wansoft_subsidiaries:
    current_date = start_date_range
    current_day = start_date_range.day
    contador = 1  # para saber si ya llevo 7 dias
    while current_date <= end_date_range:
        # Calcular las fechas de inicio y fin del mes
        if contador > 7:
            current_day = current_date.day
            contador = 1
        # Calcular el lunes anterior más cercano
        days_since_monday = current_date.weekday()  # weekday() devuelve 0 para lunes, 1 para martes, ..., 6 para domingo
        start_date = current_date - timedelta(days=days_since_monday)

        end_date = end_date_range

        # Convertir las fechas a strings
        start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%S")
        end_date_str = end_date.strftime("%Y-%m-%dT%H:%M:%S")
        current_date_str = current_date.strftime("%Y-%m-%d")

        # Calcular el valor de mes-año en formato "MM-YYYY"
        mes_ano = start_date.strftime("%m-%Y")
        fecha = current_date + timedelta(days=1)
        fecha_str = fecha.strftime("%Y-%m-%d %H:%M:%S")
        fecha_str = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")

        print(start_date_str)

        try:
            # Llama al método GetCostReport_Xml con el rango de fechas del mes
            response = client.service.GetCostReport_Xml(
                subsidiaryId=subsidiary['id'],
                pwdWebService=subsidiary['password'],
                #startDate = current_date.replace(day=1),
                #endDate = start_date.strftime("%Y-%m-%dT%H:%M:%S")
                startDate=start_date_str,
                endDate=current_date_str
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
                        SELECT id,CostoTotal,CostoDeProductosVendidos FROM costeomensual_semanapyq
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
                                UPDATE costeomensual_semanapyq
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
                        INSERT INTO costeomensual_semanapyq (subsidiary_id, subsidiary_name, CostoTotal, CostoDeProductosVendidos,
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
        contador += 1

# Loop para obtener datos de cada subsidiaria (fuente Odoo)
# CostoTotal/CostoDeProductosVendidos/CostoDeMerma se calculan semana-a-la-fecha
# (lunes de esa semana -> la fecha), igual que el lado Wansoft. El resto de las
# columnas (CostoDeCortesias, CostoDeCancelaciones, CostoDeRobo, CostoDeConsumo,
# AjustePorSobrantes, CostoIdealDeProductosPendientesDeRebaja, UtilidadMarginal)
# no tienen equivalente confiable en la contabilidad de Odoo actual y se dejan
# en NULL para estas filas (no se aproximan). Cortesias/Cancelaciones/
# Anulaciones "de venta" (valor crudo, no ponderado por costo) se cubren
# aparte via getGlobalCashClosing.py sobre la tabla getglobalcashclosing,
# no en este reporte.
if odoo_subsidiaries:
    from core.database.odoo import get_odoo_connection
    from extract.costs.odoo_cost_report import resolve_odoo_company_id, get_daily_cost

    odoo_uid, odoo_models, odoo_db, odoo_password = get_odoo_connection()

    for subsidiary in odoo_subsidiaries:
        odoo_company_id = resolve_odoo_company_id(
            odoo_models, odoo_uid, odoo_db, odoo_password, subsidiary["nombreCorto"]
        )
        if odoo_company_id is None:
            print(f"[⚠] No se pudo resolver company_id de Odoo para {subsidiary['nombreCorto']}")
            continue

        # Traer un poco antes del rango para poder calcular semana-a-la-fecha
        # del primer día del rango sin perder los días previos de esa semana.
        fetch_start = (start_date_range - timedelta(days=7)).strftime("%Y-%m-%d")
        fetch_end = end_date_range.strftime("%Y-%m-%d")
        df_daily = get_daily_cost(odoo_models, odoo_uid, odoo_db, odoo_password, odoo_company_id, fetch_start, fetch_end)

        if df_daily.empty:
            continue

        df_daily["fecha_dt"] = pd.to_datetime(df_daily["fecha"])
        df_daily["iso_year"] = df_daily["fecha_dt"].dt.isocalendar().year
        df_daily["iso_week"] = df_daily["fecha_dt"].dt.isocalendar().week
        df_daily = df_daily.sort_values("fecha_dt")
        df_daily["CostoTotal_wtd"] = df_daily.groupby(["iso_year", "iso_week"])["CostoTotal"].cumsum()
        df_daily["CostoDeProductosVendidos_wtd"] = df_daily.groupby(["iso_year", "iso_week"])["CostoDeProductosVendidos"].cumsum()
        df_daily["CostoDeMerma_wtd"] = df_daily.groupby(["iso_year", "iso_week"])["CostoDeMerma"].cumsum()

        current_date = start_date_range
        while current_date <= end_date_range:
            lafecha = current_date.strftime("%Y-%m-%d")
            mes_ano = current_date.strftime("%m-%Y")
            row_match = df_daily[df_daily["fecha"] == lafecha]

            if row_match.empty:
                current_date += timedelta(days=1)
                continue

            total_costo = float(row_match.iloc[0]["CostoTotal_wtd"])
            total_productos_costo = float(row_match.iloc[0]["CostoDeProductosVendidos_wtd"])
            costo_merma = float(row_match.iloc[0]["CostoDeMerma_wtd"])

            cursor.execute("""
                SELECT id, CostoTotal, CostoDeProductosVendidos FROM costeomensual_semanapyq
                WHERE subsidiary_id = %s AND DATE(created_at) = %s
            """, (subsidiary["id"], lafecha))
            existing_row = cursor.fetchone()

            if existing_row:
                record_id, total_db, productos_db = existing_row
                if (abs(total_costo - float(total_db)) > 0.01) or (abs(total_productos_costo - float(productos_db)) > 0.01):
                    cursor.execute("""
                        UPDATE costeomensual_semanapyq
                        SET
                            subsidiary_name = %s,
                            CostoTotal = %s,
                            CostoDeProductosVendidos = %s,
                            CostoDeMerma = %s,
                            mes_ano = %s
                        WHERE DATE(created_at) = %s AND subsidiary_id = %s
                    """, (subsidiary["name"], total_costo, total_productos_costo, costo_merma, mes_ano, lafecha, subsidiary["id"]))
                    print(f"[🔁] Actualizado (Odoo): {subsidiary['nombreCorto']} - {lafecha}")
                else:
                    print(f"[✔] Igual (Odoo): {subsidiary['nombreCorto']} - {lafecha}")
            else:
                cursor.execute("""
                    INSERT INTO costeomensual_semanapyq
                        (subsidiary_id, subsidiary_name, CostoTotal, CostoDeProductosVendidos, CostoDeMerma, mes_ano, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (subsidiary["id"], subsidiary["name"], total_costo, total_productos_costo, costo_merma, mes_ano, lafecha))
                print(f"[🆕] Insertado (Odoo): {subsidiary['nombreCorto']} - {lafecha}")

            db_connection.commit()
            current_date += timedelta(days=1)

# Cerrar la conexión a la base de datos
cursor.close()
db_connection.close()