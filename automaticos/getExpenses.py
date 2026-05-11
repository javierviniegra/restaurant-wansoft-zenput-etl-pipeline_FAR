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
from config.database import get_db_connection

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
    CREATE TABLE IF NOT EXISTS getexpenses_factura (
       `id` int(11) NOT NULL,
      `Sucursal` varchar(255) DEFAULT NULL,
      `Factura_Id` varchar(255) DEFAULT NULL,
      `IdDocumento` varchar(255) DEFAULT NULL,
      `Folio` varchar(255) DEFAULT NULL,
      `RFCProveedor` varchar(255) DEFAULT NULL,
      `NombreProveedor` varchar(255) DEFAULT NULL,
      `ClaveProveedor` varchar(255) DEFAULT NULL,
      `CuentaContableProveedor` varchar(255) DEFAULT NULL,
      `Subtotal` varchar(255) DEFAULT NULL,
      `IVA` varchar(255) DEFAULT NULL,
      `IEPS` varchar(255) DEFAULT NULL,
      `Total` varchar(255) DEFAULT NULL,
      `FechaDeExpedicion` varchar(255) DEFAULT NULL,
      `FechaDeExpiracion` varchar(255) DEFAULT NULL,
      `TerminosDePago` varchar(255) DEFAULT NULL,
      `Cuenta` varchar(255) DEFAULT NULL,
      `Subcuenta` varchar(255) DEFAULT NULL,
      `Estatus` varchar(255) DEFAULT NULL,
      `TotalDeudor` varchar(255) DEFAULT NULL,
      `TipoDeEgreso` varchar(255) DEFAULT NULL,
      `UUID` varchar(255) DEFAULT NULL,
      `IdOrdenCompra` varchar(255) DEFAULT NULL,
      `FolioOrdenCompra` varchar(255) DEFAULT NULL,
      `FechaDeRegistro` varchar(255) DEFAULT NULL,
      `DiasCredito` varchar(255) DEFAULT NULL,
      `ColoniaProveedor` varchar(255) DEFAULT NULL,
      `CiudadProveedor` varchar(255) DEFAULT NULL,
      `CPProveedor` varchar(255) DEFAULT NULL,
      `TelefonoProveedor` varchar(255) DEFAULT NULL,
      `CorreoProveedor` varchar(255) DEFAULT NULL,
      `CalleProveedor` varchar(255) DEFAULT NULL,
      `NumeroIntProveedor` varchar(255) DEFAULT NULL,
      `NumeroExtProveedor` varchar(255) DEFAULT NULL,
      `Discount` varchar(255) DEFAULT NULL,
      `Retentions` varchar(255) DEFAULT NULL,
      `Egresos_Id` varchar(255) DEFAULT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;
""")
db_connection.commit()

# Initialize SOAP client
client = Client('https://www.wansoft.net/wansoft.web/API/IntegrationService.asmx?wsdl')

# List of subsidiaries and their credentials
subsidiaries = [
    {"id":5320, "nombreCorto":"Acoxpa", "password":os.getenv("WANSOFT_PWD_5320"),  'name': "Fonda Argentina - Acoxpa"},
    {"id":4959, "nombreCorto":"Aeropuerto", "password":os.getenv("WANSOFT_PWD_4959"),  'name': "Fonda Argentina - Aeropuerto"},
    {"id":4958, "nombreCorto":"Isabel La Católica", "password":os.getenv("WANSOFT_PWD_4958"),  'name': "Fonda Argentina - Isabel La Católica"},
    {"id":4960, "nombreCorto":"Antenas", "password":os.getenv("WANSOFT_PWD_4960"),  'name': "Fonda Argentina - Antenas"},
    {"id":5321, "nombreCorto":"Taquería parroquia", "password":os.getenv("WANSOFT_PWD_5321"),  'name': "Fonda Argentina – Taquería Parroquía"},
    {"id":5318, "nombreCorto":"Vía Vallejo", "password":os.getenv("WANSOFT_PWD_5318"),  'name': "Fonda Argentina – Vía Vallejo"},
    {"id":4961, "nombreCorto":"Viaducto", "password":os.getenv("WANSOFT_PWD_4961"),  'name': "Fonda Argentina - Viaducto"},
    {"id":4962, "nombreCorto":"Taquería Viaducto", "password":os.getenv("WANSOFT_PWD_4962"),  'name': "Fonda Argentina - Taqueria Viaducto"},
    {"id":5319, "nombreCorto":"San Jeronimo", "password":os.getenv("WANSOFT_PWD_5319"),  'name': "Fonda Argentina – San Jerónimo"},
    {"id":6560, "nombreCorto":"Tepeyac", "password":os.getenv("WANSOFT_PWD_6560"),  'name': "Fonda Argentina - Tepeyac"},
    {"id":7697, "nombreCorto":"Taq San Fernando", "password":os.getenv("WANSOFT_PWD_7697"),  'name': "Fonda Argentina - Taqueria San Fernando"},
    {"id":6174, "nombreCorto":"Playa del Carmen", "password":os.getenv("WANSOFT_PWD_6174"),  'name': "Fonda Argentina - Playa del Carmen"},
    {"id":5943, "nombreCorto":"Oceanía", "password":os.getenv("WANSOFT_PWD_5943"),  'name': "Fonda Argentina - Oceanía"},
    {"id":6175, "nombreCorto":"Cancun", "password":os.getenv("WANSOFT_PWD_6175"),  'name': "Fonda Argentina - Cancún"},
    {"id":4433, "nombreCorto":"Napoles", "password":os.getenv("WANSOFT_PWD_4433"),  'name': "Fonda Argentina - Nápoles"},
    {"id":4752, "nombreCorto":"Metepec", "password":os.getenv("WANSOFT_PWD_4752"),  'name': "Fonda Argentina - Tollocan"},
    {"id":5396, "nombreCorto":"Versalles", "password":os.getenv("WANSOFT_PWD_5396"),  'name': "Fonda Argentina - Taquería Exhibimex"},
    {"id":12057, "nombreCorto": "La Esquina Coyoacán", "name":"Fonda Argentina - Coyoacan", "password":os.getenv("WANSOFT_PWD_12057")},
    {"id":12802, "nombreCorto": "CentroMyJ", "name":"Fonda Argentina - Centro Mario y July", "password":os.getenv("WANSOFT_PWD_12802")},
    {"id":12806, "nombreCorto": "Puebla", "name":"Fonda Argentina - Puebla", "password":os.getenv("WANSOFT_PWD_12806")},
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
            print(f"Consultando gastos de {subsidiary['name']} para {current_date_str}")
            response = client.service.GetExpenses_Xml(
                subsidiaryId=subsidiary['id'],
                pwdWebService=subsidiary['password'],
                operationdate=current_date_str
            )

            if response:
                # Extraer el XML de la respuesta SOAP
                root_soap = ET.fromstring(response)
                #result_element = root_soap.find('.//{http://tempuri.org/}GetExpenses_XmlResult')

                if True:# result_element is not None and result_element.text:
                    # Procesar el XML interno
                    #expenses_xml = unescape(result_element.text)
                    #root_expenses = ET.fromstring(expenses_xml)

                    # Procesar cada factura
                    for factura in root_soap.findall('.//Factura'):
                        attrs = factura.attrib

                        # Preparar datos para inserción
                        data = {
                            'Sucursal': subsidiary['name'],
                            'Factura_Id': None,  # No está en el XML
                            'IdDocumento': attrs.get('IdDocumento'),
                            'Folio': attrs.get('Folio'),
                            'RFCProveedor': attrs.get('RFCProveedor'),
                            'NombreProveedor': attrs.get('NombreProveedor'),
                            'ClaveProveedor': attrs.get('ClaveProveedor'),
                            'CuentaContableProveedor': attrs.get('CuentaContableProveedor'),
                            'Subtotal': attrs.get('Subtotal'),
                            'IVA': attrs.get('IVA'),
                            'IEPS': attrs.get('IEPS'),
                            'Total': attrs.get('Total'),
                            'FechaDeExpedicion': attrs.get('FechaDeExpedicion'),
                            'FechaDeExpiracion': attrs.get('FechaDeExpiracion'),
                            'TerminosDePago': attrs.get('TerminosDePago'),
                            'Cuenta': attrs.get('Cuenta'),
                            'Subcuenta': attrs.get('Subcuenta'),
                            'Estatus': attrs.get('Estatus'),
                            'TotalDeudor': attrs.get('TotalDeudor'),
                            'TipoDeEgreso': attrs.get('TipoDeEgreso'),
                            'UUID': attrs.get('UUID'),
                            'IdOrdenCompra': attrs.get('IdOrdenCompra'),
                            'FolioOrdenCompra': attrs.get('FolioOrdenCompra'),
                            'FechaDeRegistro': attrs.get('FechaDeRegistro'),
                            'DiasCredito': attrs.get('DiasCredito'),
                            'ColoniaProveedor': attrs.get('ColoniaProveedor'),
                            'CiudadProveedor': attrs.get('CiudadProveedor'),
                            'CPProveedor': attrs.get('CPProveedor'),
                            'TelefonoProveedor': attrs.get('TelefonoProveedor'),
                            'CorreoProveedor': attrs.get('CorreoProveedor'),
                            'CalleProveedor': attrs.get('CalleProveedor'),
                            'NumeroIntProveedor': attrs.get('NumeroIntProveedor'),
                            'NumeroExtProveedor': attrs.get('NumeroExtProveedor'),
                            'Discount': attrs.get('Discount'),
                            'Retentions': attrs.get('Retentions'),
                            'Egresos_Id': None  # No está en el XML
                        }

                        # Verificar si ya existe
                        cursor.execute("""
                            SELECT id FROM getexpenses_factura
                            WHERE IdDocumento = %s AND Sucursal = %s
                        """, (data['IdDocumento'], subsidiary['name']))
                        existing = cursor.fetchone()

                        if existing:
                            # Actualizar registro existente
                            update_query = """
                                UPDATE getexpenses_factura SET
                                    Folio = %s,
                                    RFCProveedor = %s,
                                    NombreProveedor = %s,
                                    ClaveProveedor = %s,
                                    CuentaContableProveedor = %s,
                                    Subtotal = %s,
                                    IVA = %s,
                                    IEPS = %s,
                                    Total = %s,
                                    FechaDeExpedicion = %s,
                                    FechaDeExpiracion = %s,
                                    TerminosDePago = %s,
                                    Cuenta = %s,
                                    Subcuenta = %s,
                                    Estatus = %s,
                                    TotalDeudor = %s,
                                    TipoDeEgreso = %s,
                                    UUID = %s,
                                    IdOrdenCompra = %s,
                                    FolioOrdenCompra = %s,
                                    FechaDeRegistro = %s,
                                    DiasCredito = %s,
                                    ColoniaProveedor = %s,
                                    CiudadProveedor = %s,
                                    CPProveedor = %s,
                                    TelefonoProveedor = %s,
                                    CorreoProveedor = %s,
                                    CalleProveedor = %s,
                                    NumeroIntProveedor = %s,
                                    NumeroExtProveedor = %s,
                                    Discount = %s,
                                    Retentions = %s
                                WHERE IdDocumento = %s AND Sucursal = %s
                            """
                            cursor.execute(update_query, (
                                data['Folio'],
                                data['RFCProveedor'],
                                data['NombreProveedor'],
                                data['ClaveProveedor'],
                                data['CuentaContableProveedor'],
                                data['Subtotal'],
                                data['IVA'],
                                data['IEPS'],
                                data['Total'],
                                data['FechaDeExpedicion'],
                                data['FechaDeExpiracion'],
                                data['TerminosDePago'],
                                data['Cuenta'],
                                data['Subcuenta'],
                                data['Estatus'],
                                data['TotalDeudor'],
                                data['TipoDeEgreso'],
                                data['UUID'],
                                data['IdOrdenCompra'],
                                data['FolioOrdenCompra'],
                                data['FechaDeRegistro'],
                                data['DiasCredito'],
                                data['ColoniaProveedor'],
                                data['CiudadProveedor'],
                                data['CPProveedor'],
                                data['TelefonoProveedor'],
                                data['CorreoProveedor'],
                                data['CalleProveedor'],
                                data['NumeroIntProveedor'],
                                data['NumeroExtProveedor'],
                                data['Discount'],
                                data['Retentions'],
                                data['IdDocumento'],
                                subsidiary['name']
                            ))
                            print(f"[🔁] Actualizado factura {data['IdDocumento']} en {subsidiary['name']}")
                        else:
                            # Insertar nuevo registro
                            insert_query = """
                                INSERT INTO getexpenses_factura (
                                    Sucursal, Factura_Id, IdDocumento, Folio, RFCProveedor, 
                                    NombreProveedor, ClaveProveedor, CuentaContableProveedor, 
                                    Subtotal, IVA, IEPS, Total, FechaDeExpedicion, 
                                    FechaDeExpiracion, TerminosDePago, Cuenta, Subcuenta, 
                                    Estatus, TotalDeudor, TipoDeEgreso, UUID, IdOrdenCompra, 
                                    FolioOrdenCompra, FechaDeRegistro, DiasCredito, 
                                    ColoniaProveedor, CiudadProveedor, CPProveedor, 
                                    TelefonoProveedor, CorreoProveedor, CalleProveedor, 
                                    NumeroIntProveedor, NumeroExtProveedor, Discount, 
                                    Retentions, Egresos_Id
                                ) VALUES (
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                                )
                            """
                            cursor.execute(insert_query, (
                                data['Sucursal'],
                                data['Factura_Id'],
                                data['IdDocumento'],
                                data['Folio'],
                                data['RFCProveedor'],
                                data['NombreProveedor'],
                                data['ClaveProveedor'],
                                data['CuentaContableProveedor'],
                                data['Subtotal'],
                                data['IVA'],
                                data['IEPS'],
                                data['Total'],
                                data['FechaDeExpedicion'],
                                data['FechaDeExpiracion'],
                                data['TerminosDePago'],
                                data['Cuenta'],
                                data['Subcuenta'],
                                data['Estatus'],
                                data['TotalDeudor'],
                                data['TipoDeEgreso'],
                                data['UUID'],
                                data['IdOrdenCompra'],
                                data['FolioOrdenCompra'],
                                data['FechaDeRegistro'],
                                data['DiasCredito'],
                                data['ColoniaProveedor'],
                                data['CiudadProveedor'],
                                data['CPProveedor'],
                                data['TelefonoProveedor'],
                                data['CorreoProveedor'],
                                data['CalleProveedor'],
                                data['NumeroIntProveedor'],
                                data['NumeroExtProveedor'],
                                data['Discount'],
                                data['Retentions'],
                                data['Egresos_Id']
                            ))
                            print(f"[🆕] Insertado factura {data['IdDocumento']} en {subsidiary['name']}")

                        db_connection.commit()
            else:
                print(f"Sin respuesta para {subsidiary['name']} ({current_date_str})")

        except Exception as e:
            print(f"Error en {subsidiary['name']} {current_date_str}: {str(e)[:200]}")  # Limitar a 200 caracteres
            # Consumir cualquier resultado pendiente
            while cursor.fetchone() is not None:
                pass
            db_connection.rollback()

        current_date += timedelta(days=1)

cursor.close()
db_connection.close()