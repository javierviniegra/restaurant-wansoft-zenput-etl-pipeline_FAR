import os

from zeep import Client
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import mysql.connector
from core.database.mysql import get_mysql_connection as get_db_connection

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

# Rango de fechas
start_date = datetime(2025, 1, 1)
end_date = datetime(2025, 1, 31)

# Crear los DataFrames finales
final_df_expenses = pd.DataFrame()

# Loop para obtener datos de cada subsidiaria y fecha dentro del rango
current_date = start_date
while current_date <= end_date:
    for subsidiary in subsidiaries:
        try:

            # Llama al método GetExpensesByInputDate con la fecha actual
            operation_date = current_date.strftime("%Y-%m-%dT%H:%M:%S")
            response = client.service.GetExpensesByInputDate_Xml(
                subsidiaryId=int(subsidiary['id']),
                pwdWebService=subsidiary['password'],
                inputdate=operation_date
            )

            # Parse the response
            if response:
                root = ET.fromstring(response)
                print("XML Response:", response[0:500])  # Imprime solo los primeros 500 caracteres del XML

                # Lists to store data
                expenses_list = []

                for expense in root.findall('.//Factura'):
                    expense_dict = expense.attrib
                    expense_dict['subsidiary_name'] = subsidiary['name']
                    expense_dict['current_date'] = current_date.strftime("%Y-%m-%d")
                    expenses_list.append(expense_dict)
                    print(f"DEBUG: Expense Detail Dict: {expense_dict}")

                # Convert lists to DataFrames
                df_expenses = pd.DataFrame(expenses_list)

                # Verificar contenido del DataFrame
                if not df_expenses.empty:
                    print(f"DEBUG: DataFrame for {subsidiary['name']} on {current_date}:")
                    print(df_expenses.head())
                else:
                    print(f"DEBUG: Empty DataFrame for {subsidiary['name']} on {current_date}")

                # Append to final DataFrames using concat
                final_df_expenses = pd.concat([final_df_expenses, df_expenses], ignore_index=True)

                print(f"Expenses for subsidiary {subsidiary['name']} on {current_date} processed.")
            else:
                print(f"No expenses received for subsidiary {subsidiary['name']} on {current_date}")

        except Exception as e:
            print(f"An error occurred while fetching data for subsidiary {subsidiary['name']} on {current_date}: {e}")

    # Incrementa la fecha actual para el siguiente ciclo
    current_date += timedelta(days=1)

# Verificar el DataFrame final antes de guardar
if not final_df_expenses.empty:
    print("Final DataFrame:")
    print(final_df_expenses.head())
else:
    print("Final DataFrame is empty.")

# Guardar a un archivo CSV
final_df_expenses.to_csv('GetExpensesByInputDate/final_expenses_sep24.csv', index=False)

# Guardar en MySQL
# Leer el archivo CSV
file_path = 'GetExpensesByInputDate/final_expenses_sep24.csv'
df = pd.read_csv(file_path)

# Conectar a la base de datos MySQL
conexion = get_db_connection(target="wansoft")

cursor = conexion.cursor()

# Crear una tabla si no existe
elQuery = """
    CREATE TABLE IF NOT EXISTS GetExpensesByInputDate (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY, 
        IdDocumento VARCHAR(255), 
        Folio VARCHAR(255), 
        RFCProveedor VARCHAR(255), 
        NombreProveedor VARCHAR(255), 
        ClaveProveedor VARCHAR(255), 
        CuentaContableProveedor VARCHAR(255), 
        Subtotal VARCHAR(255), 
        IVA VARCHAR(255), 
        IEPS VARCHAR(255), 
        Total VARCHAR(255), 
        FechaDeExpedicion VARCHAR(255), 
        FechaDeExpiracion VARCHAR(255), 
        TerminosDePago VARCHAR(255), 
        Cuenta VARCHAR(255), 
        Subcuenta VARCHAR(255), 
        Estatus VARCHAR(255), 
        TotalDeudor VARCHAR(255), 
        TipoDeEgreso VARCHAR(255), 
        UUID VARCHAR(255),
        IdOrdenCompra VARCHAR(255), 
        FolioOrdenCompra VARCHAR(255), 
        FechaDeRegistro VARCHAR(255), 
        DiasCredito VARCHAR(255),
        ColoniaProveedor VARCHAR(255),
        CiudadProveedor VARCHAR(255),
        CPProveedor VARCHAR(255),
        TelefonoProveedor VARCHAR(255),
        CorreoProveedor VARCHAR(255),
        CalleProveedor VARCHAR(255),
        NumeroIntProveedor VARCHAR(255),
        NumeroExtProveedor VARCHAR(255),
        subsidiary_name VARCHAR(255),
        current_fecha VARCHAR(255)
    )
"""
cursor.execute(elQuery)

# Insertar los datos en la tabla MySQL
for index, row in df.iterrows():
    # Convertir NaN a cadena vacía y asegurarse que todos los valores sean strings
    row = row.fillna("").astype(str)

    # Crear el query SQL como una variable
    elQuery = '''
            INSERT INTO GetExpensesByInputDate (IdDocumento, Folio, RFCProveedor, NombreProveedor, ClaveProveedor, CuentaContableProveedor, Subtotal, IVA, IEPS, Total, FechaDeExpedicion, FechaDeExpiracion, TerminosDePago, Cuenta, Subcuenta, Estatus, TotalDeudor, TipoDeEgreso, UUID, IdOrdenCompra, FolioOrdenCompra, FechaDeRegistro, DiasCredito, ColoniaProveedor, CiudadProveedor, CPProveedor, TelefonoProveedor, CorreoProveedor, CalleProveedor, NumeroIntProveedor, NumeroExtProveedor, subsidiary_name, current_fecha)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''

    # Imprimir el query y los valores para pruebas
    print(f"Query: {elQuery}")
    print(f"Values: {tuple(row)}")

    cursor.execute(elQuery, tuple(row))

# Confirmar los cambios
conexion.commit()

# Cerrar la conexión
cursor.close()
conexion.close()
