import os

from zeep import Client
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import mysql.connector
from core.database.mysql import get_mysql_connection as get_db_connection

# Initialize SOAP client
from core.clients.wansoft_client import get_wansoft_client
client = get_wansoft_client()

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

# Rango de fechas
start_date = datetime(2025, 1, 1)
end_date = datetime(2025, 1, 1)

# Crear los DataFrames finales
final_df_inventory = pd.DataFrame()

# Loop para obtener datos de cada subsidiaria y fecha dentro del rango
current_date = start_date
while current_date <= end_date:
    for subsidiary in subsidiaries:
        try:
            # Llama al método GetInventoryByDepartment con la fecha actual
            operation_date = current_date.strftime("%Y-%m-%dT%H:%M:%S")
            response = client.service.GetInventoryByDepartment(
                subsidiaryName=subsidiary['name'],
                pwdWebService=subsidiary['password'],
                operationdate=operation_date
            )

            # Parse the response
            if response:
                # Load the XML into an ElementTree object
                root = ET.fromstring(response)
                print("XML Response:", response[0:500])  # Imprime solo los primeros 500 caracteres del XML

                # Lists to store data
                inventory_list = []

                for inventory in root.findall('.//Inventario'):
                    department = inventory.attrib
                    for detail in inventory.findall('.//DetalleInventario'):
                        detail_dict = detail.attrib
                        detail_dict.update(department)
                        detail_dict['subsidiary_name'] = subsidiary['name']
                        detail_dict['current_date'] = current_date.strftime("%Y-%m-%d")
                        inventory_list.append(detail_dict)
                        print(f"DEBUG: Inventory Detail Dict: {detail_dict}")

                # Convert lists to DataFrames
                df_inventory = pd.DataFrame(inventory_list)

                # Verificar contenido del DataFrame
                if not df_inventory.empty:
                    print(f"DEBUG: DataFrame for {subsidiary['name']} on {current_date}:")
                    print(df_inventory.head())
                else:
                    print(f"DEBUG: Empty DataFrame for {subsidiary['name']} on {current_date}")

                # Append to final DataFrames using concat
                final_df_inventory = pd.concat([final_df_inventory, df_inventory], ignore_index=True)

                print(f"Inventory for subsidiary {subsidiary['name']} on {current_date} processed.")
            else:
                print(f"No inventory received for subsidiary {subsidiary['name']} on {current_date}")

        except Exception as e:
            print(f"An error occurred while fetching data for subsidiary {subsidiary['name']} on {current_date}: {e}")

    # Incrementa la fecha actual para el siguiente ciclo
    current_date += timedelta(days=1)

# Verificar el DataFrame final antes de guardar
if not final_df_inventory.empty:
    print("Final DataFrame:")
    print(final_df_inventory.head())
else:
    print("Final DataFrame is empty.")

# Save or analyze the final DataFrame
final_df_inventory.to_csv('GetInventoryByDepartment/final_inventory_ago24.csv', index=False)

#guardo a Mysql

# Leer el archivo CSV
file_path = 'GetInventoryByDepartment/final_inventory_ago24.csv'
df = pd.read_csv(file_path)

# Conectar a la base de datos MySQL
conexion = get_db_connection(target="wansoft")
#conexion = mysql.connector.connect(
#    host='localhost',
#    user='root',
#    password='',
#    database='wansoft'
#)

cursor = conexion.cursor()

# Crear una tabla si no existe
elQuery = """
    CREATE TABLE IF NOT EXISTS GetInventoryByDepartment (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY, 
        CodigoProducto VARCHAR(255),	
        Producto VARCHAR(255),	
        UnidadDeMedida VARCHAR(255),	
        Existencia VARCHAR(255),	
        CostoPromedio VARCHAR(255),	
        Monto VARCHAR(255),	
        MontoTotal VARCHAR(255),	
        Departamento VARCHAR(255),	
        ClaveDepartamento VARCHAR(255),	
        subsidiary_name VARCHAR(255),	
        current_fecha VARCHAR(255)
    )
"""
cursor.execute(elQuery)
print(elQuery)

# Insertar los datos en la tabla MySQL
for index, row in df.iterrows():
    cursor.execute('''
        INSERT INTO GetInventoryByDepartment (CodigoProducto,	Producto,	UnidadDeMedida,	Existencia,	CostoPromedio,	Monto,	MontoTotal,	Departamento,	ClaveDepartamento,	subsidiary_name,	current_fecha
)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', tuple(row))

# Confirmar los cambios
conexion.commit()

# Cerrar la conexión
cursor.close()
conexion.close()