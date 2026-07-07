import mysql.connector
from mysql.connector import Error
from zeep import Client
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import sys
import os


# 2. Ahora sí podemos importar nuestra función
from core.database.mysql import get_db_connection

# Fechas de inicio y fin (puedes cambiarlas fuera del loop)
start_date_range = datetime.now() - timedelta(days=1)
end_date_range = datetime.now() - timedelta(days=1)
#start_date_range = datetime(2025, 1, 1)
#end_date_range = datetime(2025, 4, 20)

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
from core.config.company_filter import is_wansoft_company

subsidiaries = [
    s for s in subsidiaries
    if is_wansoft_company(s["nombreCorto"])
]

# Configuración de la conexión a MySQL
db_connection = get_db_connection(target="wansoft")
cursor = db_connection.cursor()

# Verificar si la tabla cost_reports existe y si no, crearla
cursor.execute("""
CREATE TABLE IF NOT EXISTS getOutgoingInventory_Salida (
    id INT AUTO_INCREMENT PRIMARY KEY,
    subsidiary_name VARCHAR(255), -- Nombre de la subsidiaria (parámetro externo)
    IdSalida VARCHAR(50), -- ID de la salida
    IdEntrada VARCHAR(50), -- ID de la entrada
    IdAlmacen INT, -- ID del almacén
    Almacen VARCHAR(255), -- Nombre del almacén
    CuentaContableAlmacen VARCHAR(255), -- Cuenta contable del almacén
    CuentaContableDepartamento VARCHAR(255), -- Cuenta contable del departamento
    Departamento VARCHAR(255), -- Nombre del departamento
    IdProducto INT, -- ID del producto
    CodigoProducto VARCHAR(50), -- Código del producto
    NombreProducto VARCHAR(255), -- Nombre del producto
    CodigoUnidadDeMedida VARCHAR(50), -- Código de unidad de medida
    IdUnidadDeMedida INT, -- ID de unidad de medida
    UnidadDeMedida VARCHAR(50), -- Unidad de medida
    TipoSalida VARCHAR(50), -- Tipo de salida
    Cantidad DECIMAL(15,10), -- Cantidad
    CostoUnitario DECIMAL(15,4), -- Costo unitario
    Caducidad DATE, -- Fecha de caducidad (puede venir vacío)
    FechaSalida DATETIME, -- Fecha de salida
    IdTransferencia VARCHAR(50), -- ID de transferencia
    FolioTransferencia VARCHAR(50), -- Folio de transferencia
    Orden VARCHAR(50), -- Orden
    Fecha DATE, -- Fecha
    IdDetalleVenta VARCHAR(50), -- ID del detalle de la venta
    IdUsuario VARCHAR(50), -- ID del usuario
    NombreUsuario VARCHAR(255), -- Nombre del usuario
    FechaReal DATE, -- Fecha real
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- Fecha de creación del registro
);
""")
db_connection.commit()

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

def generate_insert_queries(salidas_xml, subsidiary_name):
    """
    Genera y muestra los queries INSERT para las salidas de inventario y sus detalles.
    Args:
        salidas_xml (str): Contenido del XML.
        subsidiary_name (str): Nombre de la subsidiaria.
    Returns:
        tuple: (query_list, params_list)
    """
    # Parsear el XML
    salidas = salidas_xml.findall(".//Salida")
    # Lista para almacenar las consultas y parámetros
    query_list = []
    params_list = []
    # Consulta INSERT para la tabla getOutgoingInventory_Salida
    query = """
        INSERT INTO getOutgoingInventory_Salida (
            subsidiary_name,
            IdSalida,
            IdEntrada,
            IdAlmacen,
            Almacen,
            CuentaContableAlmacen,
            CuentaContableDepartamento,
            Departamento,
            IdProducto,
            CodigoProducto,
            NombreProducto,
            CodigoUnidadDeMedida,
            IdUnidadDeMedida,
            UnidadDeMedida,
            TipoSalida,
            Cantidad,
            CostoUnitario,
            Caducidad,
            FechaSalida,
            IdTransferencia,
            FolioTransferencia,
            Orden,
            Fecha,
            IdDetalleVenta,
            IdUsuario,
            NombreUsuario,
            FechaReal
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        );
    """
    for salida in salidas:
        # Extraer datos del XML/JSON
        IdSalida = salida.get("IdSalida")
        IdEntrada = salida.get("IdEntrada")
        IdAlmacen = int(salida.get("IdAlmacen", 0))
        Almacen = salida.get("Almacen")
        CuentaContableAlmacen = salida.get("CuentaContableAlmacen")
        CuentaContableDepartamento = salida.get("CuentaContableDepartamento")
        Departamento = salida.get("Departamento")
        
        IdProducto = int(salida.get("IdProducto", 0))
        CodigoProducto = salida.get("CodigoProducto")
        NombreProducto = salida.get("NombreProducto")
        
        CodigoUnidadDeMedida = salida.get("CodigoUnidadDeMedida")
        IdUnidadDeMedida = int(salida.get("IdUnidadDeMedida", 0))
        UnidadDeMedida = salida.get("UnidadDeMedida")
        
        TipoSalida = salida.get("TipoSalida")
        Cantidad = float(salida.get("Cantidad", 0))
        CostoUnitario = float(salida.get("CostoUnitario", 0))
        
        Caducidad = salida.get("Caducidad") or None
        FechaSalida = salida.get("FechaSalida")
        
        IdTransferencia = salida.get("IdTransferencia") or None
        FolioTransferencia = salida.get("FolioTransferencia")
        
        Orden = salida.get("Orden")
        Fecha = salida.get("Fecha")
        IdDetalleVenta = salida.get("IdDetalleVenta")
        
        IdUsuario = salida.get("IdUsuario") or None
        NombreUsuario = salida.get("NombreUsuario")
        FechaReal = salida.get("FechaReal")
        # Preparar parámetros para la consulta
        params = (
            subsidiary_name,
            IdSalida,
            IdEntrada,
            IdAlmacen,
            Almacen,
            CuentaContableAlmacen,
            CuentaContableDepartamento,
            Departamento,
            IdProducto,
            CodigoProducto,
            NombreProducto,
            CodigoUnidadDeMedida,
            IdUnidadDeMedida,
            UnidadDeMedida,
            TipoSalida,
            Cantidad,
            CostoUnitario,
            Caducidad,
            FechaSalida,
            IdTransferencia,
            FolioTransferencia,
            Orden,
            Fecha,
            IdDetalleVenta,
            IdUsuario,
            NombreUsuario,
            FechaReal
        )
        cursor.execute(query, params)
        # Agregar la consulta y los parámetros a las listas
        query_list.append(query)
        params_list.append(params)
    #confirmo los cambios en la BD    
    db_connection.commit()
    return query, params

def print_sql_queries(query_orden, params_orden):
    """Imprime los queries SQL en formato ejecutable"""
    print("\n" + "="*80)
    print("QUERY PARA ORDEN PRINCIPAL:")
    print_sql_query(query_orden, params_orden)
    
def print_sql_query(query, params):
    """Función auxiliar para formatear un query con sus parámetros"""
    if not params:
        print(query + ";")
        return
    
    # Convertir parámetros a formato SQL
    converted = []
    for p in params:
        if p is None:
            converted.append("NULL")
        elif isinstance(p, (int, float)):
            converted.append(str(p))
        elif isinstance(p, datetime):
            converted.append(f"'{p.strftime('%Y-%m-%d %H:%M:%S')}'")
        else:
            escaped = str(p).replace("'", "''")
            converted.append(f"'{escaped}'")
    
    # Formatear query final
    parts = query.split('%s')
    final_query = parts[0]
    for i in range(1, len(parts)):
        final_query += converted[i-1] + parts[i]
    
    print(final_query + ";")

def get_from_soap(client, subsidiaries, start_date, end_date):
    """Obtiene el inventario de salida del servicio SOAP"""
    current_date = start_date
    while current_date <= end_date:
        current_date_str = current_date.strftime("%Y-%m-%d")
        
        for subsidiary in subsidiaries:
            print(f"Procesando {subsidiary['name']} - {current_date_str}")
            
            try:
                # Llamar al servicio SOAP
                response = client.service.GetOutgoingInventory_Xml(
                    subsidiaryId=subsidiary['id'],
                    pwdWebService=subsidiary['password'],
                    operationdate=current_date_str
                )
                if response:
                    # Procesar la respuesta XML
                    root = ET.fromstring(response)
                    
                    for salidas in root.findall('.//Salidas'):
                        # Generar los queries
                        query_inventario, params_inventario = generate_insert_queries(
                            salidas, subsidiary['id']
                        )
                        #print("El query: " + query_inventario)
                        #print_sql_queries(query_inventario, params_inventario)
                    print(f"Datos procesados correctamente para {subsidiary['name']} - {current_date_str}")
                else:
                    print(f"No se recibió respuesta para {subsidiary['name']} - {current_date_str}")
            
            except Exception as e:
                print(f"Error en SOAP para {subsidiary['name']} - {current_date_str}: {e}")
                if 'db_connection' in locals():
                    db_connection.rollback()
        
        current_date += timedelta(days=1)

# Para usar el servicio SOAP
get_from_soap(client, subsidiaries, start_date_range, end_date_range)

# Cerrar la conexión a la base de datos
cursor.close()
db_connection.close()