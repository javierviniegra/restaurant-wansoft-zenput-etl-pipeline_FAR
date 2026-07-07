import os

import mysql.connector
from zeep import Client
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from core.database.mysql import get_mysql_connection as get_db_connection

# Fechas de inicio y fin (puedes cambiarlas fuera del loop)
#start_date_range = datetime.now() - timedelta(days=1)
#end_date_range = datetime.now() - timedelta(days=1)
start_date_range = datetime(2022, 8,1)  # Fecha inicial
end_date_range = datetime(2025, 7, 31)    # Fecha final

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
#db_connection = mysql.connector.connect(
#    host='localhost',
#    user='root',
#    password='',
#    database='wansoft'
#)
cursor = db_connection.cursor(buffered=True)

# Verificar si la tabla cost_reports existe y si no, crearla
cursor.execute("""
    CREATE TABLE IF NOT EXISTS getglobalcashclosing (
        id INT AUTO_INCREMENT PRIMARY KEY,
        subsidiary_id INT,
        subsidiary_name VARCHAR(255),
        fecha_corte DATETIME,
        usuario VARCHAR(255),
        subtotal DECIMAL(10, 2),
        iva DECIMAL(10, 2),
        ieps DECIMAL(10, 2),
        total_ventas DECIMAL(10, 2),
        efectivo_por_ventas DECIMAL(10, 2),
        efectivo_por_propina DECIMAL(10, 2),
        fondo_de_caja DECIMAL(10, 2),
        efectivo_real DECIMAL(10, 2),
        no_ordenes INT,
        no_platillos INT,
        total_personas INT,
        promedio_platillos_orden DECIMAL(10, 2),
        promedio_por_orden DECIMAL(10, 2),
        promedio_por_persona DECIMAL(10, 2),
        total_ordenes_para_llevar INT,
        total_mesas_atendidas INT,
        total_ordenes_a_domicilio INT,
        total_ordenes_recoger INT,
        no_cortesias_en_cuentas INT,
        cortesias_en_cuentas DECIMAL(10, 2),
        no_cortesias_en_platillos INT,
        cortesias_en_platillos DECIMAL(10, 2),
        no_cancelaciones_en_cuentas INT,
        cancelaciones_en_cuentas DECIMAL(10, 2),
        no_cancelaciones_en_platillos INT,
        cancelaciones_en_platillos DECIMAL(10, 2),
        no_descuentos_en_cuentas INT,
        descuentos_en_cuentas DECIMAL(10, 2),
        no_descuentos_en_platillos INT,
        descuentos_en_platillos DECIMAL(10, 2),
        no_anulaciones_en_cuentas INT,
        anulaciones_en_cuentas DECIMAL(10, 2),
        no_anulaciones_en_platillos INT,
        anulaciones_en_platillos DECIMAL(10, 2),
        no_dxu_platillos INT,
        dxu_platillos DECIMAL(10, 2),
        no_descuentos_megapuntos INT,
        descuentos_megapuntos DECIMAL(10, 2),
        no_promociones INT,
        promociones DECIMAL(10, 2),
        no_cupones INT,
        cupones DECIMAL(10, 2),
        mes_ano VARCHAR(7),  -- Formato MM-YYYY
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
db_connection.commit()

# Initialize SOAP client
from core.clients.wansoft_client import get_wansoft_client
client = get_wansoft_client()


# Funciones de ayuda
def safe_float(value, default=0.0):
    try:
        return float(value.replace(',', '')) if value else default
    except (ValueError, TypeError):
        return default


def safe_int(value, default=0):
    try:
        return int(value) if value else default
    except (ValueError, TypeError):
        return default


def parse_datetime(date_str):
    try:
        return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
    except:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except:
            return None


# Procesar cada sucursal
for subsidiary in subsidiaries:
    current_date = start_date_range
    while current_date <= end_date_range:
        current_date_str = current_date.strftime("%Y-%m-%d")

        try:
            print(f"Consultando {subsidiary['name']} para {current_date_str}")
            response = client.service.GetGlobalCashClosing_Xml(
                subsidiaryId=subsidiary['id'],
                pwdWebService=subsidiary['password'],
                operationDate=current_date_str
            )

            if not response:
                print(f"  Sin respuesta para {subsidiary['name']} ({current_date_str})")
                current_date += timedelta(days=1)
                continue

            # Parsear XML
            root = ET.fromstring(response)
            mes_ano = current_date.strftime("%m-%Y")

            # Procesar cada corte
            for corte in root.findall('.//Corte'):
                fecha_corte = corte.attrib.get('Fecha')
                usuario = corte.attrib.get('Usuario')

                # Extraer datos de ventas
                ventas = corte.find('Ventas')
                subtotal = safe_float(ventas.attrib.get('Subtotal', '0.0')) if ventas is not None else 0.0
                iva = safe_float(ventas.attrib.get('IVA', '0.0')) if ventas is not None else 0.0
                ieps = safe_float(ventas.attrib.get('IEPS', '0.0')) if ventas is not None else 0.0
                total_ventas = safe_float(ventas.attrib.get('Total', '0.0')) if ventas is not None else 0.0

                # Extraer formas de pago
                formas_pago = corte.find('FormasDePago/FormaDePago')
                efectivo_por_ventas = safe_float(
                    formas_pago.attrib.get('PorVentas', '0.0')) if formas_pago is not None else 0.0
                efectivo_por_propina = safe_float(
                    formas_pago.attrib.get('PorPropina', '0.0')) if formas_pago is not None else 0.0

                # Extraer control de efectivo
                control_efectivo = corte.find('ControlDelEfectivo')
                fondo_de_caja = safe_float(
                    control_efectivo.attrib.get('FondoDeCaja', '0.0')) if control_efectivo is not None else 0.0
                efectivo_real = safe_float(
                    control_efectivo.attrib.get('EfectivoReal', '0.0')) if control_efectivo is not None else 0.0

                # Extraer información operativa
                info_operativa = corte.find('InformacionOperativa')


                # Función para extraer atributos
                def get_attr(attr, default='0'):
                    return info_operativa.attrib.get(attr, default) if info_operativa is not None else default


                # Preparar datos
                data = {
                    'fecha_corte':datetime.strptime(fecha_corte, "%Y-%m-%dT%H:%M:%S"),
                    'usuario': usuario,
                    'subtotal': subtotal,
                    'iva': iva,
                    'ieps': ieps,
                    'total_ventas': total_ventas,
                    'efectivo_por_ventas': efectivo_por_ventas,
                    'efectivo_por_propina': efectivo_por_propina,
                    'fondo_de_caja': fondo_de_caja,
                    'efectivo_real': efectivo_real,
                    'no_ordenes': safe_int(get_attr('NoDeOrdenes')),
                    'no_platillos': safe_int(get_attr('NoDePlatillos')),
                    'total_personas': safe_int(get_attr('TotalDePersonas')),
                    'promedio_platillos_orden': safe_float(get_attr('PromedioPlatillosOrden')),
                    'promedio_por_orden': safe_float(get_attr('PromedioPorOrden')),
                    'promedio_por_persona': safe_float(get_attr('PromedioPorPersona')),
                    'total_ordenes_para_llevar': safe_int(get_attr('TotalOrdenesParaLlevar')),
                    'total_mesas_atendidas': safe_int(get_attr('TotalDeMesasAtendidas')),
                    'total_ordenes_a_domicilio': safe_int(get_attr('TotalDeOrdenesADomicilio')),
                    'total_ordenes_recoger': safe_int(get_attr('TotalOrdenesRecoger')),
                    'no_cortesias_en_cuentas': safe_int(get_attr('NoCortesiasEnCuentas')),
                    'cortesias_en_cuentas': safe_float(get_attr('CortesiasEnCuentas')),
                    'no_cortesias_en_platillos': safe_int(get_attr('NoCortesiasEnPlatillos')),
                    'cortesias_en_platillos': safe_float(get_attr('CortesiasEnPlatillos')),
                    'no_cancelaciones_en_cuentas': safe_int(get_attr('NoCancelacionDeCuentas')),
                    'cancelaciones_en_cuentas': safe_float(get_attr('CancelacionDeCuentas')),
                    'no_cancelaciones_en_platillos': safe_int(get_attr('NoCancelacionDePlatillos')),
                    'cancelaciones_en_platillos': safe_float(get_attr('CancelacionDePlatillos')),
                    'no_descuentos_en_cuentas': safe_int(get_attr('NoDescuentosEnCuentas')),
                    'descuentos_en_cuentas': safe_float(get_attr('DescuentosEnCuentas')),
                    'no_descuentos_en_platillos': safe_int(get_attr('NoDescuentosEnPlatillos')),
                    'descuentos_en_platillos': safe_float(get_attr('DescuentosEnPlatillos')),
                    'no_anulaciones_en_cuentas': safe_int(get_attr('NoAnulacionesEnCuentas')),
                    'anulaciones_en_cuentas': safe_float(get_attr('AnulacionesEnCuentas')),
                    'no_anulaciones_en_platillos': safe_int(get_attr('NoAnulacionesEnPlatillos')),
                    'anulaciones_en_platillos': safe_float(get_attr('AnulacionesEnPlatillos')),
                    'no_dxu_platillos': safe_int(get_attr('NoDXUPlatillos')),
                    'dxu_platillos': safe_float(get_attr('DXUPlatillos')),
                    'no_descuentos_megapuntos': safe_int(get_attr('NoDescuentosMegapuntos')),
                    'descuentos_megapuntos': safe_float(get_attr('DescuentosMegapuntos')),
                    'no_promociones': safe_int(get_attr('NoPromociones')),
                    'promociones': safe_float(get_attr('Promociones')),
                    'no_cupones': safe_int(get_attr('NoCupones')),
                    'cupones': safe_float(get_attr('Cupones')),
                    'mes_ano': mes_ano
                }

                # Verificar si ya existe
                cursor.execute("""
                    SELECT id, total_ventas, iva, subtotal, fecha_corte 
                    FROM getglobalcashclosing
                    WHERE subsidiary_id = %s AND fecha_corte = %s
                """, (subsidiary['id'], data['fecha_corte']))
                row = cursor.fetchone()
                print(row)

                if row:
                    # Actualizar si hay cambios
                    record_id, total_db, iva_db, subtotal_db, fecha_db = row
                    if (
                            abs(data['total_ventas'] - float(total_db)) > 0.01 or
                            str(data['fecha_corte']) != str(fecha_db)  or
                            abs(data['iva'] - float(iva_db)) > 0.01 or
                            abs(data['subtotal'] - float(subtotal_db)) > 0.01
                    ):
                        update_query = """
                            UPDATE getglobalcashclosing SET
                                usuario = %s,
                                subtotal = %s,
                                iva = %s,
                                ieps = %s,
                                total_ventas = %s,
                                efectivo_por_ventas = %s,
                                efectivo_por_propina = %s,
                                fondo_de_caja = %s,
                                efectivo_real = %s,
                                no_ordenes = %s,
                                no_platillos = %s,
                                total_personas = %s,
                                promedio_platillos_orden = %s,
                                promedio_por_orden = %s,
                                promedio_por_persona = %s,
                                total_ordenes_para_llevar = %s,
                                total_mesas_atendidas = %s,
                                total_ordenes_a_domicilio = %s,
                                total_ordenes_recoger = %s,
                                no_cortesias_en_cuentas = %s,
                                cortesias_en_cuentas = %s,
                                no_cortesias_en_platillos = %s,
                                cortesias_en_platillos = %s,
                                no_cancelaciones_en_cuentas = %s,
                                cancelaciones_en_cuentas = %s,
                                no_cancelaciones_en_platillos = %s,
                                cancelaciones_en_platillos = %s,
                                no_descuentos_en_cuentas = %s,
                                descuentos_en_cuentas = %s,
                                no_descuentos_en_platillos = %s,
                                descuentos_en_platillos = %s,
                                no_anulaciones_en_cuentas = %s,
                                anulaciones_en_cuentas = %s,
                                no_anulaciones_en_platillos = %s,
                                anulaciones_en_platillos = %s,
                                no_dxu_platillos = %s,
                                dxu_platillos = %s,
                                no_descuentos_megapuntos = %s,
                                descuentos_megapuntos = %s,
                                no_promociones = %s,
                                promociones = %s,
                                no_cupones = %s,
                                cupones = %s,
                                mes_ano = %s
                            WHERE id = %s
                        """
                        update_data = (
                            data['usuario'],
                            data['subtotal'],
                            data['iva'],
                            data['ieps'],
                            data['total_ventas'],
                            data['efectivo_por_ventas'],
                            data['efectivo_por_propina'],
                            data['fondo_de_caja'],
                            data['efectivo_real'],
                            data['no_ordenes'],
                            data['no_platillos'],
                            data['total_personas'],
                            data['promedio_platillos_orden'],
                            data['promedio_por_orden'],
                            data['promedio_por_persona'],
                            data['total_ordenes_para_llevar'],
                            data['total_mesas_atendidas'],
                            data['total_ordenes_a_domicilio'],
                            data['total_ordenes_recoger'],
                            data['no_cortesias_en_cuentas'],
                            data['cortesias_en_cuentas'],
                            data['no_cortesias_en_platillos'],
                            data['cortesias_en_platillos'],
                            data['no_cancelaciones_en_cuentas'],
                            data['cancelaciones_en_cuentas'],
                            data['no_cancelaciones_en_platillos'],
                            data['cancelaciones_en_platillos'],
                            data['no_descuentos_en_cuentas'],
                            data['descuentos_en_cuentas'],
                            data['no_descuentos_en_platillos'],
                            data['descuentos_en_platillos'],
                            data['no_anulaciones_en_cuentas'],
                            data['anulaciones_en_cuentas'],
                            data['no_anulaciones_en_platillos'],
                            data['anulaciones_en_platillos'],
                            data['no_dxu_platillos'],
                            data['dxu_platillos'],
                            data['no_descuentos_megapuntos'],
                            data['descuentos_megapuntos'],
                            data['no_promociones'],
                            data['promociones'],
                            data['no_cupones'],
                            data['cupones'],
                            data['mes_ano'],
                            record_id
                        )
                        cursor.execute(update_query, update_data)
                        print(f"  [🔁] Actualizado: {data['fecha_corte']}")
                    else:
                        print(f"  [✔] Sin cambios: {data['fecha_corte']}")
                else:
                    # Insertar nuevo registro
                    insert_query = """
                        INSERT INTO getglobalcashclosing (
                            subsidiary_id, subsidiary_name, fecha_corte, usuario, subtotal, iva, ieps, total_ventas,
                            efectivo_por_ventas, efectivo_por_propina, fondo_de_caja, efectivo_real, no_ordenes,
                            no_platillos, total_personas, promedio_platillos_orden, promedio_por_orden,
                            promedio_por_persona, total_ordenes_para_llevar, total_mesas_atendidas,
                            total_ordenes_a_domicilio, total_ordenes_recoger, no_cortesias_en_cuentas,
                            cortesias_en_cuentas, no_cortesias_en_platillos, cortesias_en_platillos,
                            no_cancelaciones_en_cuentas, cancelaciones_en_cuentas, no_cancelaciones_en_platillos,
                            cancelaciones_en_platillos, no_descuentos_en_cuentas, descuentos_en_cuentas,
                            no_descuentos_en_platillos, descuentos_en_platillos, no_anulaciones_en_cuentas,
                            anulaciones_en_cuentas, no_anulaciones_en_platillos, anulaciones_en_platillos,
                            no_dxu_platillos, dxu_platillos, no_descuentos_megapuntos, descuentos_megapuntos,
                            no_promociones, promociones, no_cupones, cupones, mes_ano
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                                %s, %s, %s, %s, %s, %s, %s)
                    """
                    insert_data = (
                        subsidiary['id'],
                        subsidiary['name'],
                        data['fecha_corte'],
                        data['usuario'],
                        data['subtotal'],
                        data['iva'],
                        data['ieps'],
                        data['total_ventas'],
                        data['efectivo_por_ventas'],
                        data['efectivo_por_propina'],
                        data['fondo_de_caja'],
                        data['efectivo_real'],
                        data['no_ordenes'],
                        data['no_platillos'],
                        data['total_personas'],
                        data['promedio_platillos_orden'],
                        data['promedio_por_orden'],
                        data['promedio_por_persona'],
                        data['total_ordenes_para_llevar'],
                        data['total_mesas_atendidas'],
                        data['total_ordenes_a_domicilio'],
                        data['total_ordenes_recoger'],
                        data['no_cortesias_en_cuentas'],
                        data['cortesias_en_cuentas'],
                        data['no_cortesias_en_platillos'],
                        data['cortesias_en_platillos'],
                        data['no_cancelaciones_en_cuentas'],
                        data['cancelaciones_en_cuentas'],
                        data['no_cancelaciones_en_platillos'],
                        data['cancelaciones_en_platillos'],
                        data['no_descuentos_en_cuentas'],
                        data['descuentos_en_cuentas'],
                        data['no_descuentos_en_platillos'],
                        data['descuentos_en_platillos'],
                        data['no_anulaciones_en_cuentas'],
                        data['anulaciones_en_cuentas'],
                        data['no_anulaciones_en_platillos'],
                        data['anulaciones_en_platillos'],
                        data['no_dxu_platillos'],
                        data['dxu_platillos'],
                        data['no_descuentos_megapuntos'],
                        data['descuentos_megapuntos'],
                        data['no_promociones'],
                        data['promociones'],
                        data['no_cupones'],
                        data['cupones'],
                        data['mes_ano']
                    )
                    cursor.execute(insert_query, insert_data)
                    print(f"  [🆕] Insertado: {data['fecha_corte']}")

                db_connection.commit()

        except Exception as e:
            print(f"  [❌] Error: {str(e)[:200]}")
            try:
                db_connection.rollback()
            except:
                pass

        current_date += timedelta(days=1)

# Cerrar conexiones
cursor.close()
db_connection.close()
print("Proceso completado")