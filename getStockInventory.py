import os

import mysql.connector
from core.database.database import get_db_connection
from zeep import Client
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import html

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
    CREATE TABLE IF NOT EXISTS getstockinventory_inventario (
      `id` int(11) NOT NULL AUTO_INCREMENT,
      `Sucursal` varchar(255) DEFAULT NULL,
      `Fecha` varchar(255) DEFAULT NULL,
      `IdProducto` varchar(255) DEFAULT NULL,
      `CodigoProducto` varchar(255) DEFAULT NULL,
      `Producto` varchar(255) DEFAULT NULL,
      `IdDepartamento` varchar(255) DEFAULT NULL,
      `CodigoDepartamento` varchar(255) DEFAULT NULL,
      `Departamento` varchar(255) DEFAULT NULL,
      `IdUnidadDeMedida` varchar(255) DEFAULT NULL,
      `UnidadDeMedida` varchar(255) DEFAULT NULL,
      `Disponibilidad` varchar(255) DEFAULT NULL,
      `Balance` varchar(255) DEFAULT NULL,
      `Critico` varchar(255) DEFAULT NULL,
      PRIMARY KEY (`id`),
      INDEX idx_sucursal_fecha_producto (Sucursal, Fecha, IdProducto)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;
""")
db_connection.commit()
print("Tabla 'getstockinventory_inventario' verificada/creada.")

# Initialize SOAP client
try:
    client = Client('https://www.wansoft.net/wansoft.web/API/IntegrationService.asmx?wsdl')
except Exception as e:
    print(f"Error al inicializar el cliente SOAP (WSDL): {e}")
    exit()

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

# Función auxiliar para convertir valores a float eliminando comas
def safe_float(value, default=0.0):
    try:
        # Eliminar comas y convertir a float
        return float(value.replace(',', ''))
    except (ValueError, AttributeError):
        return default

# Procesamiento principal
for subsidiary in subsidiaries:
    current_date = start_date_range
    while current_date <= end_date_range:
        current_date_str = current_date.strftime("%Y-%m-%d")

        try:
            print(f"Consultando Inventario de {subsidiary['name']} para {current_date_str}")
            # 1. LLAMADA AL NUEVO ENDPOINT
            response = client.service.GetStockInventory_Xml(
                subsidiaryId=subsidiary['id'],
                pwdWebService=subsidiary['password'],
                operationdate=current_date_str
            )

            if response:
                # 2. PARSEO DE LA RESPUESTA SOAP (Paso 1: Obtener el sobre)
                soap_envelope = ET.fromstring(response)

                # Definir el namespace de tempuri.org que usa Wansoft
                namespaces = {'tem': 'http://tempuri.org/'}

                # Buscar el nodo <GetStockInventory_XmlResult>
                result_element = soap_envelope.find('.//tem:GetStockInventory_XmlResult', namespaces)

                if result_element is not None and result_element.text:
                    # 3. PARSEO DEL CDATA (Paso 2: Obtener el XML de adentro)
                    cdata_xml_string = result_element.text

                    # A veces el CDATA viene envuelto en <Result>
                    # y puede tener caracteres especiales
                    cdata_xml_string = html.unescape(cdata_xml_string)
                    root_cdata = ET.fromstring(cdata_xml_string)

                    # 4. PROCESAR CADA <Inventario>
                    for inventario in root_cdata.findall('Inventario'):
                        attrs = inventario.attrib

                        # Preparar datos para inserción
                        data = {
                            'Sucursal': subsidiary['name'],
                            'Fecha': current_date_str,
                            'IdProducto': attrs.get('IdProducto'),
                            'CodigoProducto': attrs.get('CodigoProducto'),
                            'Producto': attrs.get('Producto'),
                            'IdDepartamento': attrs.get('IdDepartamento'),
                            'CodigoDepartamento': attrs.get('CodigoDepartamento'),
                            'Departamento': attrs.get('Departamento'),
                            'IdUnidadDeMedida': attrs.get('IdUnidadDeMedida'),
                            'UnidadDeMedida': attrs.get('UnidadDeMedida'),
                            'Disponibilidad': attrs.get('Disponibilidad'),
                            'Balance': attrs.get('Balance'),
                            'Critico': attrs.get('Critico'),
                        }

                        # 5. LÓGICA "UPSERT" (Verificar si ya existe)
                        cursor.execute("""
                            SELECT id FROM getstockinventory_inventario
                            WHERE IdProducto = %s AND Sucursal = %s AND Fecha = %s
                        """, (data['IdProducto'], data['Sucursal'], data['Fecha']))
                        existing = cursor.fetchone()

                        if existing:
                            # Actualizar registro existente
                            update_query = """
                                UPDATE getstockinventory_inventario SET
                                    CodigoProducto = %s,
                                    Producto = %s,
                                    IdDepartamento = %s,
                                    CodigoDepartamento = %s,
                                    Departamento = %s,
                                    IdUnidadDeMedida = %s,
                                    UnidadDeMedida = %s,
                                    Disponibilidad = %s,
                                    Balance = %s,
                                    Critico = %s
                                WHERE IdProducto = %s AND Sucursal = %s AND Fecha = %s
                            """
                            cursor.execute(update_query, (
                                data['CodigoProducto'],
                                data['Producto'],
                                data['IdDepartamento'],
                                data['CodigoDepartamento'],
                                data['Departamento'],
                                data['IdUnidadDeMedida'],
                                data['UnidadDeMedida'],
                                data['Disponibilidad'],
                                data['Balance'],
                                data['Critico'],
                                # --- WHERE params ---
                                data['IdProducto'],
                                data['Sucursal'],
                                data['Fecha']
                            ))
                            # print(f"[🔁] Actualizado inventario {data['IdProducto']} en {subsidiary['name']} para {current_date_str}")
                        else:
                            # Insertar nuevo registro
                            insert_query = """
                                INSERT INTO getstockinventory_inventario (
                                    Sucursal, Fecha, IdProducto, CodigoProducto, Producto,
                                    IdDepartamento, CodigoDepartamento, Departamento,
                                    IdUnidadDeMedida, UnidadDeMedida, Disponibilidad,
                                    Balance, Critico
                                ) VALUES (
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                                )
                            """
                            cursor.execute(insert_query, (
                                data['Sucursal'],
                                data['Fecha'],
                                data['IdProducto'],
                                data['CodigoProducto'],
                                data['Producto'],
                                data['IdDepartamento'],
                                data['CodigoDepartamento'],
                                data['Departamento'],
                                data['IdUnidadDeMedida'],
                                data['UnidadDeMedida'],
                                data['Disponibilidad'],
                                data['Balance'],
                                data['Critico']
                            ))
                            # print(f"[🆕] Insertado inventario {data['IdProducto']} en {subsidiary['name']} para {current_date_str}")

                    # Hacer commit después de procesar todos los productos de ESE DÍA
                    db_connection.commit()
                    print(f"    -> [✅] Procesado {subsidiary['name']} para {current_date_str}")

                else:
                    print(f"    -> [ℹ️] Sin datos de inventario para {subsidiary['name']} ({current_date_str})")

            else:
                print(f"    -> [ℹ️] Sin respuesta para {subsidiary['name']} ({current_date_str})")

        except Exception as e:
            print(f"    -> [❌] Error en {subsidiary['name']} {current_date_str}: {str(e)[:200]}")
            # Consumir cualquier resultado pendiente
            while cursor.fetchone() is not None:
                pass
            db_connection.rollback()

        current_date += timedelta(days=1)

print("Proceso de inventario completado.")
cursor.close()
db_connection.close()