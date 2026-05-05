import os
from datetime import datetime, timedelta
from zeep import Client

import sys
import os

# 1. Le decimos a Python que incluya la carpeta raíz en su ruta de búsqueda
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 2. Ahora sí podemos importar nuestra función
from database import get_db_connection


# In[2]:


# Inicializo el cliente SOAP
client = Client('https://www.wansoft.net/wansoft.web/API/IntegrationService.asmx?wsdl')


# In[3]:


# Defino los servicios que quiero acceder
services = [
    "GetAllOrdersByDay",
]


# In[4]:


accounts = [
    {"id": 5321, "name": "Taquería parroquia", "password": os.getenv("WANSOFT_PWD_5321")},
    {"id": 5318, "name": "Vía Vallejo", "password": os.getenv("WANSOFT_PWD_5318")},
    {"id": 6174, "name": "Playa del Carmen", "password": os.getenv("WANSOFT_PWD_6174")},
    {"id": 5396, "name": "Versalles", "password": os.getenv("WANSOFT_PWD_5396")},
    {"id":  5320, "name":  "Acoxpa", "password":  os.getenv("WANSOFT_PWD_5320") },
    {"id":  4959, "name":  "Aeropuerto", "password":  os.getenv("WANSOFT_PWD_4959") },
    {"id":  4958, "name":  "Isabel La Católica", "password":  os.getenv("WANSOFT_PWD_4958") },
    {"id":  4960, "name":  "Antenas", "password":  os.getenv("WANSOFT_PWD_4960") },
    {"id":  4961, "name":  "Viaducto", "password":  os.getenv("WANSOFT_PWD_4961") },
    {"id":  4962, "name":  "Taquería Viaducto", "password":  os.getenv("WANSOFT_PWD_4962") },
    {"id":  5319, "name":  "San Jeronimo", "password":  os.getenv("WANSOFT_PWD_5319") },
    {"id":  6560, "name":  "Tepeyac", "password":  os.getenv("WANSOFT_PWD_6560") },
    {"id":  5943, "name":  "Oceanía", "password":  os.getenv("WANSOFT_PWD_5943") },
    {"id":  6175, "name":  "Cancun", "password":  os.getenv("WANSOFT_PWD_6175") },
    {"id":  4433, "name":  "Napoles", "password":  os.getenv("WANSOFT_PWD_4433") },
    {"id":  4752, "name":  "Metepec", "password":  os.getenv("WANSOFT_PWD_4752") },
    {"id":5396, "name":"Versalles", "password":os.getenv("WANSOFT_PWD_5396")},
    {"id":12057, "name":"La Esquina Coyoacán", "password":os.getenv("WANSOFT_PWD_12057")},
    {"id":12802, "name":"CentroMyJ", "password":os.getenv("WANSOFT_PWD_12802")},
    {"id":12806, "name":"Puebla", "password":os.getenv("WANSOFT_PWD_12806")}
]


# In[5]:

base_dir = os.getenv("XML_DOWNLOAD_DIR")


# In[6]:


def create_directory(directory):
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
            print(f"Directorio creado con éxito: {directory}")
        except Exception as e:
            print(f"Error al crear el directorio: {e}")
    else:
        print(f"El directorio ya existe: {directory}")


# In[7]:


def get_service_response(service, account, date):
    try:
        # Call the appropriate SOAP method based on the service
        # llamo el servicio SOAP basado en el servicio en cuestion
        if service == "GetAllOrdersByDay":
            response = client.service.GetAllOrdersByDay_Xml(account["id"], account["password"], date.strftime("%Y-%m-%d"))
        else:
            print(f"Servicio no reconocido: {service}")
            return None
        return response
    except Exception as e:
        print(f"No se pudo descargar el servicio {service} para la cuenta {account['name']} en la fecha {date}: {e}")
        return None


# In[8]:


def save_xml(response, directory):
    try:
        with open(directory, 'w', encoding='utf-8') as file:
            file.write(response)
        print(f"Archivo guardado en {directory}")
    except Exception as e:
        print(f"Error al guardar el archivo {directory}: {e}")


# In[9]:


#funcion que me descarga los XML's
def download_xml(start_date, end_date):
    #me muevo por cada uno de los dias solicitados
    current_date = start_date
    while current_date <= end_date:
        print(f"Procesando fecha: {current_date.strftime('%Y-%m-%d')}")

        for service in services:
            service_dir = os.path.join(base_dir, service)
            create_directory(base_dir)
            create_directory(service_dir)

            for account in accounts:
                file_name = f"{account['name']}_{current_date.strftime('%Y%m%d')}.xml"
                file_path = os.path.join(service_dir, file_name)

                if not os.path.exists(file_path):
                    response = get_service_response(service, account, current_date)
                    if response:
                        save_xml(response, file_path)
                else:
                    print(f"El archivo ya existe: {file_path}")

        # Move to the next day
        current_date += timedelta(days=1)


# In[10]:


if __name__ == "__main__":
    # Defino el rango de fechas
    start_date = datetime.now() - timedelta(days=1)
    end_date = datetime.now() - timedelta(days=1)
    #start_date = datetime(2025, 7, 4)  # Fecha inicial (YYYY, MM, DD)
    #end_date = datetime(2025, 7, 4)   # Fecha final (YYYY, MM, DD)

    # comienzo con la descarga
    download_xml(start_date, end_date)

