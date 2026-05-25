import mysql.connector
from zeep import Client
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from xml.sax.saxutils import unescape

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

# Conexión a MySQL
db_connection = get_db_connection(target="wansoft")
#db_connection = mysql.connector.connect(
#    host='localhost',
#    user='root',
#    password='',
#    database='wansoft'
#)
cursor = db_connection.cursor()

# 2. Crear tabla si no existe
cursor.execute("""
CREATE TABLE IF NOT EXISTS getinputinventory_entrada (
    id INT AUTO_INCREMENT PRIMARY KEY,
    subsidiary_name VARCHAR(255),
    IdEntrada VARCHAR(50),
    ClaveAlmacen VARCHAR(50),
    Almacen VARCHAR(255),
    IdAlmacen INT,
    CuentaContableAlmacen VARCHAR(255),
    CodigoDepartamento VARCHAR(255),
    Departamento VARCHAR(255),
    CuentaContableDepartamento VARCHAR(255),
    IdProducto INT,
    CodigoProducto VARCHAR(50),
    NombreProducto VARCHAR(255),
    CodigoUnidadDeMedida VARCHAR(50),
    IdUnidadDeMedida INT,
    UnidadDeMedida VARCHAR(50),
    TipoEntrada VARCHAR(50),
    Cantidad DECIMAL(15,10),
    CostoUnitario DECIMAL(15,4),
    ProductoConIVA TINYINT(1),
    Caducidad DATE,
    FechaEntrada DATETIME,
    Factura VARCHAR(50),
    FechaFactura DATE,
    RFCProveedor VARCHAR(50),
    ClaveProveedor VARCHAR(50),
    NombreProveedor VARCHAR(255),
    IdTransferencia INT,
    FolioTransferencia VARCHAR(50),
    IdOrdenCompra INT,
    FolioOrdenCompra VARCHAR(50),
    RFCProveedorOrdenCompra VARCHAR(50),
    ProveedorOrdenCompra VARCHAR(255),
    IdDocumento INT,
    IdUsuario INT,
    NombreUsuario VARCHAR(255),
    FechaReal DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
db_connection.commit()

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

db_connection.commit()

# Initialize SOAP client
client = Client('https://www.wansoft.net/wansoft.web/API/IntegrationService.asmx?wsdl')

# 5. Rango de fechas
start_date_range = datetime.now() - timedelta(days=31)
end_date_range = datetime.now() - timedelta(days=1)

# Funciones de conversión
def parse_float(val): return float(val) if val else 0.0
def parse_int(val): return int(val) if val and val.isdigit() else None
def parse_bool(val): return 1 if val == 'True' else 0
def parse_date(val): return val if val else None

for sub in subsidiaries:
    current_date = start_date_range
    while current_date <= end_date_range:
        try:
            print(f"Consultando {sub['name']} para fecha {current_date.strftime('%Y-%m-%d')}")
            response = client.service.GetInputInventory_Xml(
                subsidiaryId=sub['id'],
                pwdWebService=sub['password'],
                operationdate=current_date.strftime("%Y-%m-%d")
            )

            if not response:
                print(f"[⚠] Sin datos para {sub['id']} el {current_date.strftime('%Y-%m-%d')}")
            else:
                root = ET.fromstring(response)

                for entrada in root.findall(".//Entrada"):
                    attrs = entrada.attrib
                    id_entrada = attrs.get("IdEntrada")
                    tipo_entrada = attrs.get("TipoEntrada")
                    cantidad = parse_float(attrs.get("Cantidad"))
                    costo_unitario = parse_float(attrs.get("CostoUnitario"))


                    cursor.execute("""
                                    SELECT Cantidad, CostoUnitario, TipoEntrada
                                    FROM getinputinventory_entrada
                                    WHERE IdEntrada = %s AND subsidiary_name = %s
                                """, (id_entrada, sub['id']))
                    row = cursor.fetchone()  # Recupera con el mismo cursor

                    if row:
                        cantidad_db, costo_unitario_db, tipo_entrada_db = row
                        if (
                            abs(float(cantidad_db) - cantidad) > 0.01 or
                            abs(float(costo_unitario_db) - costo_unitario) > 0.01 or
                            tipo_entrada_db != tipo_entrada
                        ):
                            # Actualizar si hay cambios
                            update_query = """
                                UPDATE getinputinventory_entrada SET
                                    ClaveAlmacen=%s, Almacen=%s, IdAlmacen=%s,
                                    CuentaContableAlmacen=%s, CodigoDepartamento=%s, Departamento=%s,
                                    CuentaContableDepartamento=%s, IdProducto=%s, CodigoProducto=%s,
                                    NombreProducto=%s, CodigoUnidadDeMedida=%s, IdUnidadDeMedida=%s,
                                    UnidadDeMedida=%s, TipoEntrada=%s, Cantidad=%s,
                                    CostoUnitario=%s, ProductoConIVA=%s, Caducidad=%s,
                                    FechaEntrada=%s, Factura=%s, FechaFactura=%s,
                                    RFCProveedor=%s, ClaveProveedor=%s, NombreProveedor=%s,
                                    IdTransferencia=%s, FolioTransferencia=%s, IdOrdenCompra=%s,
                                    FolioOrdenCompra=%s, RFCProveedorOrdenCompra=%s, ProveedorOrdenCompra=%s,
                                    IdDocumento=%s, IdUsuario=%s, NombreUsuario=%s, FechaReal=%s
                                WHERE IdEntrada=%s AND subsidiary_name=%s
                            """
                            update_data = (
                                attrs.get("ClaveAlmacen"), attrs.get("Almacen"), parse_int(attrs.get("IdAlmacen")),
                                attrs.get("CuentaContableAlmacen"), attrs.get("CodigoDepartamento"), attrs.get("Departamento"),
                                attrs.get("CuentaContableDepartamento"), parse_int(attrs.get("IdProducto")), attrs.get("CodigoProducto"),
                                attrs.get("NombreProducto"), attrs.get("CodigoUnidadDeMedida"), parse_int(attrs.get("IdUnidadDeMedida")),
                                attrs.get("UnidadDeMedida"), tipo_entrada, cantidad,
                                costo_unitario, parse_bool(attrs.get("ProductoConIVA")), parse_date(attrs.get("Caducidad")),
                                parse_date(attrs.get("FechaEntrada")), attrs.get("Factura"), parse_date(attrs.get("FechaFactura")),
                                attrs.get("RFCProveedor"), attrs.get("ClaveProveedor"), attrs.get("NombreProveedor"),
                                parse_int(attrs.get("IdTransferencia")), attrs.get("FolioTransferencia"), parse_int(attrs.get("IdOrdenCompra")),
                                attrs.get("FolioOrdenCompra"), attrs.get("RFCProveedorOrdenCompra"), attrs.get("ProveedorOrdenCompra"),
                                parse_int(attrs.get("IdDocumento")), parse_int(attrs.get("IdUsuario")), attrs.get("NombreUsuario"), parse_date(attrs.get("FechaReal")),
                                id_entrada, sub['id']
                            )
                            cursor.execute(update_query, update_data)
                            print(f"[🔁] Actualizado: {id_entrada}")
                        else:
                            print(f"[✔] Sin cambios: {id_entrada}")
                    else:
                        # Insertar nuevo registro
                        insert_query = """
                            INSERT INTO getinputinventory_entrada (
                                subsidiary_name, IdEntrada, ClaveAlmacen, Almacen, IdAlmacen,
                                CuentaContableAlmacen, CodigoDepartamento, Departamento, CuentaContableDepartamento,
                                IdProducto, CodigoProducto, NombreProducto, CodigoUnidadDeMedida, IdUnidadDeMedida,
                                UnidadDeMedida, TipoEntrada, Cantidad, CostoUnitario, ProductoConIVA, Caducidad,
                                FechaEntrada, Factura, FechaFactura, RFCProveedor, ClaveProveedor, NombreProveedor,
                                IdTransferencia, FolioTransferencia, IdOrdenCompra, FolioOrdenCompra, RFCProveedorOrdenCompra,
                                ProveedorOrdenCompra, IdDocumento, IdUsuario, NombreUsuario, FechaReal
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                      %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        insert_data = (
                            sub['id'], id_entrada, attrs.get("ClaveAlmacen"), attrs.get("Almacen"), parse_int(attrs.get("IdAlmacen")),
                            attrs.get("CuentaContableAlmacen"), attrs.get("CodigoDepartamento"), attrs.get("Departamento"), attrs.get("CuentaContableDepartamento"),
                            parse_int(attrs.get("IdProducto")), attrs.get("CodigoProducto"), attrs.get("NombreProducto"), attrs.get("CodigoUnidadDeMedida"), parse_int(attrs.get("IdUnidadDeMedida")),
                            attrs.get("UnidadDeMedida"), tipo_entrada, cantidad, costo_unitario, parse_bool(attrs.get("ProductoConIVA")), parse_date(attrs.get("Caducidad")),
                            parse_date(attrs.get("FechaEntrada")), attrs.get("Factura"), parse_date(attrs.get("FechaFactura")),
                            attrs.get("RFCProveedor"), attrs.get("ClaveProveedor"), attrs.get("NombreProveedor"),
                            parse_int(attrs.get("IdTransferencia")), attrs.get("FolioTransferencia"), parse_int(attrs.get("IdOrdenCompra")),
                            attrs.get("FolioOrdenCompra"), attrs.get("RFCProveedorOrdenCompra"), attrs.get("ProveedorOrdenCompra"),
                            parse_int(attrs.get("IdDocumento")), parse_int(attrs.get("IdUsuario")), attrs.get("NombreUsuario"), parse_date(attrs.get("FechaReal"))
                        )
                        cursor.execute(insert_query, insert_data)
                        print(f"[🆕] Insertado: {id_entrada}")

                    db_connection.commit()
        except Exception as e:
            print(f"[❌] Error en {sub['nombreCorto']} {current_date.strftime('%Y-%m-%d')}: {e}")

        current_date += timedelta(days=1)

cursor.close()
db_connection.close()