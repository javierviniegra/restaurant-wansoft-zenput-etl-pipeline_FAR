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
# Ventana de 31 dias (antes 1 dia): un dia solo revisa "ayer", asi que una
# corrida perdida (server down, error) deja un hueco permanente -- la causa
# mas probable de los huecos historicos de 13 meses y 3-4 anios ya
# documentados y reparados a mano. 31 dias re-revisa suficiente historial
# reciente para auto-repararse solo. Alineado con getInputInventory.py.
# Decision confirmada por el dueno del proyecto (2026-08-27), tras la
# ventana temporal de 90 dias usada para el Paso 18.22 (ya cerrada).
start_date_range = datetime.now() - timedelta(days=31)
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

def generate_insert_queries(salidas_xml, subsidiary_name, current_date_str):
    """
    Inserta o actualiza las salidas de inventario, verificando primero si el
    registro ya existe (por IdSalida) -- igual que getInputInventory.py.
    Antes hacia INSERT puro sin verificar, lo que duplicaba cada registro en
    cada corrida diaria dentro de la ventana de 31 dias que se re-procesa
    (bug real, encontrado 2026-09-08 comparando dev vs productivo: dev
    traia ~3x los registros de productivo).

    La tabla no tiene indice en IdSalida (36M+ filas -- agregarlo tumbo el
    MySQL local de XAMPP, buffer pool de solo 16MB, 2026-09-08), asi que en
    vez de una consulta por cada registro (miles por dia, cada una
    escaneando la sucursal completa), se hace UNA sola consulta por
    (sucursal, fecha) usando el indice existente en subsidiary_name, y la
    comparacion contra lo ya insertado se hace en memoria con un dict.
    Args:
        salidas_xml (str): Contenido del XML.
        subsidiary_name (str): Nombre de la subsidiaria.
        current_date_str (str): Fecha del dia que se esta procesando
            (YYYY-MM-DD), para acotar la consulta de pre-carga.
    Returns:
        tuple: (query, ultimos params) -- mantenido por compatibilidad con
        el llamador, que no usa el valor mas que para imprimir si se quiere.
    """
    # Parsear el XML
    salidas = salidas_xml.findall(".//Salida")

    if not salidas:
        return None, None

    preload_query = """
        SELECT IdSalida, Cantidad, CostoUnitario, TipoSalida
        FROM getOutgoingInventory_Salida
        WHERE subsidiary_name = %s AND Fecha = %s
    """
    cursor.execute(preload_query, (subsidiary_name, current_date_str))
    existing_by_id = {
        row[0]: (row[1], row[2], row[3])
        for row in cursor.fetchall()
    }

    insert_query = """
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

    update_query = """
        UPDATE getOutgoingInventory_Salida SET
            IdEntrada=%s, IdAlmacen=%s, Almacen=%s, CuentaContableAlmacen=%s,
            CuentaContableDepartamento=%s, Departamento=%s, IdProducto=%s,
            CodigoProducto=%s, NombreProducto=%s, CodigoUnidadDeMedida=%s,
            IdUnidadDeMedida=%s, UnidadDeMedida=%s, TipoSalida=%s, Cantidad=%s,
            CostoUnitario=%s, Caducidad=%s, FechaSalida=%s, IdTransferencia=%s,
            FolioTransferencia=%s, Orden=%s, Fecha=%s, IdDetalleVenta=%s,
            IdUsuario=%s, NombreUsuario=%s, FechaReal=%s
        WHERE IdSalida=%s AND subsidiary_name=%s
    """

    last_params = None

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

        row = existing_by_id.get(IdSalida)

        detail_fields = (
            IdEntrada, IdAlmacen, Almacen, CuentaContableAlmacen,
            CuentaContableDepartamento, Departamento, IdProducto,
            CodigoProducto, NombreProducto, CodigoUnidadDeMedida,
            IdUnidadDeMedida, UnidadDeMedida, TipoSalida, Cantidad,
            CostoUnitario, Caducidad, FechaSalida, IdTransferencia,
            FolioTransferencia, Orden, Fecha, IdDetalleVenta,
            IdUsuario, NombreUsuario, FechaReal,
        )

        if row:
            cantidad_db, costo_unitario_db, tipo_salida_db = row
            if (
                abs(float(cantidad_db) - Cantidad) > 0.01 or
                abs(float(costo_unitario_db) - CostoUnitario) > 0.01 or
                tipo_salida_db != TipoSalida
            ):
                update_params = detail_fields + (IdSalida, subsidiary_name)
                cursor.execute(update_query, update_params)
                print(f"[🔁] Actualizado: {IdSalida}")
                last_params = update_params
            else:
                print(f"[✔] Sin cambios: {IdSalida}")
        else:
            insert_params = (subsidiary_name, IdSalida) + detail_fields
            cursor.execute(insert_query, insert_params)
            print(f"[🆕] Insertado: {IdSalida}")
            last_params = insert_params

        # Reflejar el insert/update en el dict en memoria: si el mismo
        # IdSalida vuelve a aparecer mas adelante en este mismo lote (visto
        # 2026-09-09, Aeropuerto 2026-08-30 -- Wansoft repitio registros
        # dentro de la misma llamada), debe verse como existente, no
        # volver a insertarse como si fuera nuevo.
        existing_by_id[IdSalida] = (Cantidad, CostoUnitario, TipoSalida)

    #confirmo los cambios en la BD
    db_connection.commit()
    return insert_query, last_params

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
                            salidas, subsidiary['id'], current_date_str
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