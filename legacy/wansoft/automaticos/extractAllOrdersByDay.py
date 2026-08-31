import mysql.connector
from mysql.connector import Error
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from zeep import Client
import html
import sys
import os

# 2. Ahora sí podemos importar nuestra función
from core.database.mysql import get_db_connection


# ─────────────────────────────────────────────
# CONFIGURACIÓN DE EJECUCIÓN  ← solo editas aquí
# ─────────────────────────────────────────────
#
# MODO = "hoy"    → toma la fecha de hoy como punto de partida
# MODO = "fecha"  → usa la fecha que definas en FECHA_MANUAL
#
# DIAS_A_REVISAR  → cuántos días hacia atrás revisar (incluye el día base)
#                   ejemplos:
#                   1 → solo el día base
#                   3 → día base + 2 días anteriores
#                   5 → día base + 4 días anteriores
#
# CARGAR_PAGOS    → True  = SOLO ejecuta la carga de pagos por rango de fechas
#                   False = ejecuta el candado normal (verificación + sincronización)
#
# Nota: CARGAR_PAGOS y el candado son mutuamente excluyentes.

MODO                = "hoy"         # "hoy" | "fecha"
FECHA_MANUAL        = "2026-03-10"  # solo se usa si MODO = "fecha" (YYYY-MM-DD)
DIAS_A_REVISAR      = 10            # número de días a revisar hacia atrás

CARGAR_PAGOS        = False         # True → solo carga pagos | False → candado normal
PAGOS_FECHA_INICIO  = "2026-04-07"  # rango inicio para carga de pagos (YYYY-MM-DD)
PAGOS_FECHA_FIN     = "2026-04-08"  # rango fin   para carga de pagos (YYYY-MM-DD)


# ─────────────────────────────────────────────
# CONFIGURACIÓN DE CONEXIÓN
# ─────────────────────────────────────────────

conexion = get_db_connection(target="wansoft")

#conexion = mysql.connector.connect(
#    host='localhost',
#    user='root',
#    password='',
#    database='wansoft'
#)
cursor = conexion.cursor()



# Initialize SOAP client
from core.clients.wansoft_client import get_wansoft_client
client = get_wansoft_client()

# Directorio donde viven los XML descargados
from core.config.paths import get_xml_download_dir
directorio_xml = get_xml_download_dir()


# Definición de cuentas de sucursales
cuentas_sucursales = [
    ("5320", "Acoxpa", os.getenv("WANSOFT_PWD_5320")),
    ("4959", "Aeropuerto", os.getenv("WANSOFT_PWD_4959")),
    ("4958", "Isabel La Católica", os.getenv("WANSOFT_PWD_4958")),
    ("4960", "Antenas", os.getenv("WANSOFT_PWD_4960")),
    ("5321", "Taquería parroquia", os.getenv("WANSOFT_PWD_5321")),
    ("5318", "Vía Vallejo", os.getenv("WANSOFT_PWD_5318")),
    ("4961", "Viaducto", os.getenv("WANSOFT_PWD_4961")),
    ("4962", "Taquería Viaducto", os.getenv("WANSOFT_PWD_4962")),
    ("5319", "San Jeronimo", os.getenv("WANSOFT_PWD_5319")),
    ("6560", "Tepeyac", os.getenv("WANSOFT_PWD_6560")),
    ("6174", "Playa del Carmen", os.getenv("WANSOFT_PWD_6174")),
    ("5943", "Oceanía", os.getenv("WANSOFT_PWD_5943")),
    ("6175", "Cancun", os.getenv("WANSOFT_PWD_6175")),
    ("4433", "Napoles", os.getenv("WANSOFT_PWD_4433")),
    ("4752", "Metepec", os.getenv("WANSOFT_PWD_4752")),
    ("5396", "Versalles", os.getenv("WANSOFT_PWD_5396")),
    ("12057", "La Esquina Coyoacán", os.getenv("WANSOFT_PWD_12057")),
    ("12802", "CentroMyJ", os.getenv("WANSOFT_PWD_12802")),
    ("12806", "Puebla", os.getenv("WANSOFT_PWD_12806"))
]

from core.config.company_filter import is_wansoft_company

cuentas_sucursales = [
    cuenta for cuenta in cuentas_sucursales
    if is_wansoft_company(cuenta[1])
]

## ─────────────────────────────────────────────
# UTILIDADES DE BASE DE DATOS
# ─────────────────────────────────────────────

def ejecutar_query(query):
    """Ejecuta una query de escritura en MySQL."""
    try:
        cursor.execute(query)
        conexion.commit()
    except Error as e:
        print(f"    [ERROR MySQL] {e}")


def obtener_total_bd(sucursal, fecha):
    """
    Suma los Total de _new_Venta para una sucursal y fecha.
    Usa CAST(Fecha AS DATE) como acordamos.
    Retorna float o None si no hay registros.
    """
    query = """
        SELECT SUM(CAST(Total AS DECIMAL(12,2)))
        FROM GetAllOrdenesByDay_new_Venta
        WHERE Sucursal = %s
          AND CAST(Fecha AS DATE) = %s
    """
    try:
        cursor.execute(query, (sucursal, fecha.strftime('%Y-%m-%d')))
        resultado = cursor.fetchone()[0]
        return float(resultado) if resultado is not None else None
    except Error as e:
        print(f"    [ERROR MySQL al leer total] {e}")
        return None


def eliminar_registros_dia(sucursal, fecha):
    """
    Borra los registros de las 4 tablas para una sucursal y fecha.
    - _new_Venta        filtra por CAST(Fecha AS DATE)
    - _new_DetalleVenta filtra por CAST(Hora  AS DATE)
    - _new_Modificador  filtra por CAST(Hora  AS DATE)
    - _new_Pago         filtra por CAST(Fecha AS DATE)
    """
    fecha_str = fecha.strftime('%Y-%m-%d')
    tablas = [
        ("GetAllOrdenesByDay_new_Venta", "CAST(Fecha AS DATE)"),
        ("GetAllOrdenesByDay_new_DetalleVenta", "CAST(Hora  AS DATE)"),
        ("GetAllOrdenesByDay_new_Modificador", "CAST(Hora  AS DATE)"),
        ("GetAllOrdenesByDay_new_Pago", "CAST(Fecha AS DATE)"),
    ]
    for tabla, filtro_fecha in tablas:
        query = f"""
            DELETE FROM {tabla}
            WHERE Sucursal = %s
              AND {filtro_fecha} = %s
        """
        try:
            cursor.execute(query, (sucursal, fecha_str))
            filas = cursor.rowcount
            conexion.commit()
            print(f"    [DELETE] {tabla}: {filas} registros eliminados")
        except Error as e:
            print(f"    [ERROR DELETE {tabla}] {e}")


# ─────────────────────────────────────────────
# UTILIDADES DE XML / SOAP
# ─────────────────────────────────────────────

def obtener_total_oficial(id_sucursal, password, fecha):
    """
    Llama a GetGlobalCashClosing_Xml y extrae el Total de <Ventas>.
    Retorna float o None si falla.
    """
    try:
        respuesta_raw = client.service.GetGlobalCashClosing_Xml(
            id_sucursal,
            password,
            fecha.strftime('%Y-%m-%d')
        )
        xml_str = html.unescape(respuesta_raw)
        root = ET.fromstring(xml_str)

        ventas_node = root.find('.//Ventas')
        if ventas_node is None:
            print(f"    [AVISO] No se encontró nodo <Ventas> en CashClosing")
            return None

        total_str = ventas_node.get('Total', '').replace(',', '')
        return float(total_str) if total_str else None

    except Exception as e:
        print(f"    [ERROR CashClosing SOAP] {e}")
        return None


def xml_es_valido(ruta_archivo):
    """
    Verifica que el archivo exista, no esté vacío
    y contenga al menos una <Venta>.
    """
    if not os.path.exists(ruta_archivo):
        return False
    if os.path.getsize(ruta_archivo) == 0:
        return False
    try:
        tree = ET.parse(ruta_archivo)
        root = tree.getroot()
        ventas = root.findall('Ventas/Venta')
        return len(ventas) > 0
    except ET.ParseError:
        return False


def descargar_xml(id_sucursal, password, sucursal, fecha, ruta_destino):
    """
    Descarga el XML de GetAllOrdersByDay_Xml y lo guarda en ruta_destino.
    Retorna True si la descarga fue exitosa y el archivo tiene ventas.
    """
    try:
        print(f"    [DESCARGA] Solicitando XML a Wansoft...")
        respuesta = client.service.GetAllOrdersByDay_Xml(
            id_sucursal,
            password,
            fecha.strftime('%Y-%m-%d')
        )
        if not respuesta or respuesta.strip() == '':
            print(f"    [AVISO] Wansoft devolvió respuesta vacía")
            return False

        with open(ruta_destino, 'w', encoding='utf-8') as f:
            f.write(respuesta)

        if xml_es_valido(ruta_destino):
            print(f"    [DESCARGA] XML guardado correctamente: {ruta_destino}")
            return True
        else:
            print(f"    [AVISO] XML descargado pero sin registros <Venta>")
            return False

    except Exception as e:
        print(f"    [ERROR DESCARGA] {e}")
        return False


def asegurar_xml_disponible(id_sucursal, password, sucursal, fecha):
    """
    Verifica que el XML local exista y sea válido.
    Si no, intenta re-descargarlo.
    Retorna la ruta del XML si está disponible, None si no.
    """
    nombre_archivo = f"{sucursal}_{fecha.strftime('%Y%m%d')}.xml"
    ruta_xml = os.path.join(directorio_xml+"/getAllOrdersByDay", nombre_archivo)

    if xml_es_valido(ruta_xml):
        return ruta_xml

    print(f"    [PASO 1] XML no válido o inexistente — re-descargando...")
    descarga_ok = descargar_xml(id_sucursal, password, sucursal, fecha, ruta_xml)

    if descarga_ok:
        return ruta_xml

    print(f"    [SALTAR] No se pudo obtener XML para {sucursal} {fecha.strftime('%Y-%m-%d')}")
    return None


# ─────────────────────────────────────────────
# FUNCIONES DE INSERCIÓN
# ─────────────────────────────────────────────

def escapar_sql(valor):
    if valor is None:
        return "NULL"
    return "'" + str(valor).replace("'", "''") + "'"


def generar_query(tabla, campos):
    columnas = ", ".join(campos.keys())
    valores = ", ".join([escapar_sql(v) for v in campos.values()])
    return f"INSERT IGNORE INTO {tabla} ({columnas}) VALUES ({valores});"


def obtener_campos_venta(venta, sucursal):
    return {
        "Sucursal": sucursal, "Movimento": venta.get("Movimento"),
        "Orden": venta.get("Orden"), "Mesa": venta.get("Mesa"),
        "Fecha": venta.get("Fecha"), "Mesero": venta.get("Mesero"),
        "Subtotal": venta.get("Subtotal"), "IVA": venta.get("IVA"),
        "IEPS": venta.get("IEPS"), "Total": venta.get("Total"),
        "Terminal": venta.get("Terminal"), "Personas": venta.get("Personas"),
        "Descuento": venta.get("Descuento"), "Impuesto": venta.get("Impuesto"),
        "MontoDescontado": venta.get("MontoDescontado"),
        "TipoOrden": venta.get("TipoOrden"),
        "HoraApertura": venta.get("HoraApertura"),
        "HoraCierre": venta.get("HoraCierre"),
        "Moneda": venta.get("Moneda"),
        "CodigoCliente": venta.get("CodigoCliente"),
        "Estatus": venta.get("Estatus"),
    }


def obtener_campos_detalle(detalle, sucursal, movimiento_id):
    return {
        "Sucursal": sucursal, "Movimiento_Id": movimiento_id,
        "Descripcion": detalle.get("Descripcion"),
        "Cantidad": detalle.get("Cantidad"),
        "PrecioUnitario": detalle.get("PrecioUnitario"),
        "Descuento": detalle.get("Descuento"),
        "Subtotal": detalle.get("Subtotal"), "IVA": detalle.get("IVA"),
        "IEPS": detalle.get("IEPS"), "Total": detalle.get("Total"),
        "Modificador": detalle.get("Modificador"), "Hora": detalle.get("Hora"),
        "Costo": detalle.get("Costo"), "TipoGrupo": detalle.get("TipoGrupo"),
        "CodigoTipoGrupo": detalle.get("CodigoTipoGrupo"),
        "CuentaContableTipoGrupo": detalle.get("CuentaContableTipoGrupo"),
        "Grupo": detalle.get("Grupo"), "CodigoGrupo": detalle.get("CodigoGrupo"),
        "CuentaContableGrupo": detalle.get("CuentaContableGrupo"),
        "CodigoPlatillo": detalle.get("CodigoPlatillo"),
        "CuentaContablePlatillo": detalle.get("CuentaContablePlatillo"),
        "Platillo": detalle.get("Platillo"), "ConIVA": detalle.get("ConIVA"),
        "ComandaId": detalle.get("ComandaId"),
        "TipoPlatilloId": detalle.get("TipoPlatilloId"),
        "TipoPromocionId": detalle.get("TipoPromocionId"),
        "Cortesia": detalle.get("Cortesia"),
    }


def obtener_campos_modificador(mod, sucursal, movimiento_id):
    return {
        "Sucursal": sucursal, "Movimiento_Id": movimiento_id,
        "Descripcion": mod.get("Descripcion"),
        "Cantidad": mod.get("Cantidad"),
        "PrecioUnitario": mod.get("PrecioUnitario"),
        "Descuento": mod.get("Descuento"),
        "Subtotal": mod.get("Subtotal"), "IVA": mod.get("IVA"),
        "IEPS": mod.get("IEPS"), "Total": mod.get("Total"),
        "Modificador": mod.get("Modificador"), "Hora": mod.get("Hora"),
        "Costo": mod.get("Costo"), "TipoGrupo": mod.get("TipoGrupo"),
        "CodigoTipoGrupo": mod.get("CodigoTipoGrupo"),
        "CuentaContableTipoGrupo": mod.get("CuentaContableTipoGrupo"),
        "Grupo": mod.get("Grupo"), "CodigoGrupo": mod.get("CodigoGrupo"),
        "CuentaContableGrupo": mod.get("CuentaContableGrupo"),
        "CodigoPlatillo": mod.get("CodigoPlatillo"),
        "CuentaContablePlatillo": mod.get("CuentaContablePlatillo"),
        "Platillo": mod.get("Platillo"), "ConIVA": mod.get("ConIVA"),
        "ComandaId": mod.get("ComandaId"),
        "TipoPlatilloId": mod.get("TipoPlatilloId"),
        "TipoPromocionId": mod.get("TipoPromocionId"),
    }


def obtener_campos_pago(pago, sucursal, movimiento_id, fecha_venta):
    return {
        "Sucursal": sucursal,
        "Movimiento_Id": movimiento_id,
        "Fecha": fecha_venta,  # viene de venta.get("Fecha")
        "IdMetodoDePago": pago.get("IdMetodoDePago"),
        "MetodoDePago": pago.get("MetodoDePago"),
        "CodigoMetodoDePago": pago.get("CodigoMetodoDePago"),
        "ClaveSATMetodoDePago": pago.get("ClaveSATMetodoDePago"),
        "CuentaContableMetodoDePago": pago.get("CuentaContableMetodoDePago"),
        "Terminal": pago.get("Terminal"),
        "Total": pago.get("Total"),
        "Propina": pago.get("Propina"),
        "Equivalencia": pago.get("Equivalencia"),
        "Moneda": pago.get("Moneda"),
        "MontoRecibidoEnMoneda": pago.get("MontoRecibidoEnMoneda"),
        "PagoAnticipadoId": pago.get("PagoAnticipadoId"),
    }


def insertar_venta_completa(venta, sucursal):
    """Inserta una venta con sus detalles, modificadores y pagos."""
    movimiento_id = venta.get("Movimento")
    fecha_venta = venta.get("Fecha")

    ejecutar_query(generar_query(
        "GetAllOrdenesByDay_new_Venta",
        obtener_campos_venta(venta, sucursal)
    ))

    for detalle in venta.findall("DetallesVenta/DetalleVenta"):
        ejecutar_query(generar_query(
            "GetAllOrdenesByDay_new_DetalleVenta",
            obtener_campos_detalle(detalle, sucursal, movimiento_id)
        ))
        for mod in detalle.findall("Modificadores/Modificador"):
            ejecutar_query(generar_query(
                "GetAllOrdenesByDay_new_Modificador",
                obtener_campos_modificador(mod, sucursal, movimiento_id)
            ))

    for pago in venta.findall("Pagos/Pago"):
        ejecutar_query(generar_query(
            "GetAllOrdenesByDay_new_Pago",
            obtener_campos_pago(pago, sucursal, movimiento_id, fecha_venta)
        ))


def reescribir_desde_xml(archivo_xml, sucursal):
    """Lee el XML y reinserta todas las ventas del día."""
    with open(archivo_xml, 'r', encoding='utf-8') as f:
        contenido = f.read()
    root = ET.fromstring(contenido)
    ventas = root.findall('Ventas/Venta')
    print(f"    [INSERCIÓN] Reescribiendo {len(ventas)} ventas...")
    for venta in ventas:
        insertar_venta_completa(venta, sucursal)
    print(f"    [INSERCIÓN] Completada")


# ─────────────────────────────────────────────
# CARGA DE PAGOS (modo CARGAR_PAGOS = True)
# ─────────────────────────────────────────────

def insertar_pagos_desde_xml(archivo_xml, sucursal):
    """
    Recorre todas las <Venta> del XML y para cada una
    inserta sus <Pago> en _new_Pago usando INSERT IGNORE.
    La Fecha se extrae del atributo Fecha de cada <Venta>.
    """
    with open(archivo_xml, 'r', encoding='utf-8') as f:
        contenido = f.read()
    root = ET.fromstring(contenido)
    ventas = root.findall('Ventas/Venta')

    total_pagos = 0
    for venta in ventas:
        movimiento_id = venta.get("Movimento")
        fecha_venta = venta.get("Fecha")  # ej. "2026-02-18T00:00:00"
        pagos = venta.findall("Pagos/Pago")

        for pago in pagos:
            ejecutar_query(generar_query(
                "GetAllOrdenesByDay_new_Pago",
                obtener_campos_pago(pago, sucursal, movimiento_id, fecha_venta)
            ))
            total_pagos += 1

    return total_pagos


def cargar_pagos_por_rango(fecha_inicio, fecha_fin):
    """
    Para cada sucursal y cada fecha en el rango [fecha_inicio, fecha_fin]:
      1. Verifica XML local — si no existe o está vacío → re-descarga
      2. Extrae e inserta los pagos de cada venta con INSERT IGNORE
    """
    print("=" * 60)
    print(f"CARGA DE PAGOS — iniciando")
    print(f"Rango: {fecha_inicio.strftime('%Y-%m-%d')} → {fecha_fin.strftime('%Y-%m-%d')}")
    print("=" * 60)

    dias_total = (fecha_fin - fecha_inicio).days + 1
    dias_rango = [fecha_inicio + timedelta(days=n) for n in range(dias_total)]

    for cuenta in cuentas_sucursales:
        id_sucursal, sucursal, password = cuenta

        print(f"\n{'─' * 60}")
        print(f"SUCURSAL: {sucursal} (id={id_sucursal})")
        print(f"{'─' * 60}")

        pagos_sucursal = 0

        for fecha in dias_rango:
            fecha_str = fecha.strftime('%Y-%m-%d')
            print(f"\n  Fecha: {fecha_str}")

            # ── PASO 1: asegurar XML disponible ──────────────────────
            ruta_xml = asegurar_xml_disponible(
                id_sucursal, password, sucursal, fecha
            )
            if ruta_xml is None:
                print(f"  [SALTAR] Sin XML disponible para {sucursal} {fecha_str}")
                continue

            print(f"  [PASO 1] XML OK → {os.path.basename(ruta_xml)}")

            # ── PASO 2: insertar pagos ────────────────────────────────
            try:
                n_pagos = insertar_pagos_desde_xml(ruta_xml, sucursal)
                pagos_sucursal += n_pagos
                print(f"  [PAGOS]  {n_pagos} registros insertados (INSERT IGNORE)")
            except Exception as e:
                print(f"  [ERROR]  Al procesar pagos de {fecha_str}: {e}")

        print(f"\n  Total pagos insertados para {sucursal}: {pagos_sucursal}")

    print(f"\n{'=' * 60}")
    print("CARGA DE PAGOS — completada")
    print("=" * 60)


# ─────────────────────────────────────────────
# CANDADO PRINCIPAL (modo CARGAR_PAGOS = False)
# ─────────────────────────────────────────────

def verificar_y_sincronizar(fecha_referencia=None, dias_atras=5, es_modo_hoy=False):
    """
    Para cada sucursal, revisa los últimos `dias_atras` días
    y sincroniza MySQL si el total no coincide con el Cierre Z.

    Parámetros:
        fecha_referencia : datetime — fecha base (default: hoy)
        dias_atras       : int     — cuántos días revisar
        es_modo_hoy      : bool    — si True, el día más reciente (n=1)
                           se carga sin validar contra Cierre Z
                           porque el día puede estar aún abierto
    """
    if fecha_referencia is None:
        fecha_referencia = datetime.now()

    print("=" * 60)
    print(f"CANDADO — iniciando verificación")
    print(f"Fecha referencia : {fecha_referencia.strftime('%Y-%m-%d')}")
    print(f"Días a revisar   : {dias_atras}")
    print("=" * 60)

    for cuenta in cuentas_sucursales:
        id_sucursal, sucursal, password = cuenta

        print(f"\n{'─' * 60}")
        print(f"SUCURSAL: {sucursal} (id={id_sucursal})")
        print(f"{'─' * 60}")

        for n in range(1, dias_atras + 1):
            fecha = fecha_referencia - timedelta(days=n)
            fecha_str = fecha.strftime('%Y-%m-%d')
            es_dia_reciente = (n == 1 and es_modo_hoy)
            print(f"\n  Fecha: {fecha_str}" + (" (día en curso — sin validación Cierre Z)" if es_dia_reciente else ""))

            # ── PASO 1: verificar XML local ───────────────────────────
            ruta_xml = asegurar_xml_disponible(
                id_sucursal, password, sucursal, fecha
            )
            if ruta_xml is None:
                continue

            print(f"  [PASO 1] XML local OK")

            # ── Día más reciente en modo "hoy": solo asegurar XML ─────
            # El día puede estar aún abierto, no tiene Cierre Z confiable
            if es_dia_reciente:
                total_bd = obtener_total_bd(sucursal, fecha)
                if total_bd is None:
                    print(f"  [PASO 2] Sin datos en BD — cargando desde XML...")
                    reescribir_desde_xml(ruta_xml, sucursal)
                else:
                    print(f"  [PASO 2] Ya hay datos en BD (${total_bd:,.2f}) — sin acción")
                continue

            # ── PASO 2: obtener Total Oficial (Cierre Z) ──────────────
            total_oficial = obtener_total_oficial(id_sucursal, password, fecha)
            if total_oficial is None:
                print(f"  [SALTAR] No se pudo obtener CashClosing para {sucursal} {fecha_str}")
                continue
            print(f"  [PASO 2] Total oficial (Cierre Z): ${total_oficial:,.2f}")

            # ── PASO 3: obtener Total en BD ───────────────────────────
            total_bd = obtener_total_bd(sucursal, fecha)
            if total_bd is not None:
                print(f"  [PASO 3] Total en BD            : ${total_bd:,.2f}")
            else:
                print(f"  [PASO 3] Sin datos en BD (NULL)")

            # ── PASO 4: comparar ──────────────────────────────────────
            diferencia = abs(total_oficial - (total_bd or 0))

            if total_bd is not None and diferencia < 0.01:
                print(f"  [PASO 4] ✓ Totales coinciden — sin acción necesaria")
                continue

            print(f"  [PASO 4] ✗ Diferencia: ${diferencia:,.2f} — sincronizando...")

            # ── Forzar re-descarga antes de corregir ──────────────────
            # El XML local (usado en PASO 1) puede ser una copia vieja;
            # si se detectó diferencia, hay que corregir con datos frescos
            # de Wansoft, no repetir la misma fuente que pudo originar
            # el desfase.
            print(f"  [PASO 4] Forzando re-descarga desde Wansoft antes de corregir...")
            redescarga_ok = descargar_xml(id_sucursal, password, sucursal, fecha, ruta_xml)
            if not redescarga_ok:
                print(f"  [ALERTA] No se pudo re-descargar XML fresco — usando copia local existente")

            # ── Eliminar y reescribir ─────────────────────────────────
            eliminar_registros_dia(sucursal, fecha)
            reescribir_desde_xml(ruta_xml, sucursal)

            # ── Verificación post-escritura ───────────────────────────
            total_bd_nuevo = obtener_total_bd(sucursal, fecha)
            if total_bd_nuevo is not None:
                dif_final = abs(total_oficial - total_bd_nuevo)
                if dif_final < 0.01:
                    print(f"  [OK] Sincronización exitosa — Total BD: ${total_bd_nuevo:,.2f}")
                else:
                    print(f"  [ALERTA] Aún hay diferencia de ${dif_final:,.2f} tras reescritura")
            else:
                print(f"  [ALERTA] No se pudo verificar el total post-escritura")

    print(f"\n{'=' * 60}")
    print("CANDADO — verificación completada")
    print("=" * 60)


# ─────────────────────────────────────────────
# PUNTO DE ENTRADA
# ─────────────────────────────────────────────

if __name__ == "__main__":

    if CARGAR_PAGOS:
        # ── Modo: solo carga de pagos por rango ──────────────────────
        print(f"Modo: CARGA DE PAGOS")
        try:
            f_inicio = datetime.strptime(PAGOS_FECHA_INICIO, "%Y-%m-%d")
            f_fin = datetime.strptime(PAGOS_FECHA_FIN, "%Y-%m-%d")
        except ValueError as e:
            print(f"[ERROR] Formato de fecha incorrecto en PAGOS_FECHA_INICIO / PAGOS_FECHA_FIN")
            print(f"        Usa YYYY-MM-DD. Detalle: {e}")
            exit(1)

        if f_inicio > f_fin:
            print(f"[ERROR] PAGOS_FECHA_INICIO ({PAGOS_FECHA_INICIO}) "
                  f"es mayor que PAGOS_FECHA_FIN ({PAGOS_FECHA_FIN})")
            exit(1)

        cargar_pagos_por_rango(f_inicio, f_fin)

    else:
        # ── Modo: candado normal ──────────────────────────────────────
        if MODO == "fecha":
            try:
                fecha_base = datetime.strptime(FECHA_MANUAL, "%Y-%m-%d") + timedelta(days=1)
                print(f"Modo: FECHA MANUAL → {FECHA_MANUAL}")
            except ValueError:
                print(f"[ERROR] FECHA_MANUAL tiene formato incorrecto: '{FECHA_MANUAL}'")
                print("        Usa el formato YYYY-MM-DD, por ejemplo: '2026-04-06'")
                exit(1)
            verificar_y_sincronizar(
                fecha_referencia=fecha_base,
                dias_atras=DIAS_A_REVISAR,
                es_modo_hoy=False  # fecha manual → siempre valida Cierre Z
            )
        else:
            fecha_base = datetime.now()
            print(f"Modo: HOY → {fecha_base.strftime('%Y-%m-%d')}")
            verificar_y_sincronizar(
                fecha_referencia=fecha_base,
                dias_atras=DIAS_A_REVISAR,
                es_modo_hoy=True  # modo hoy → día más reciente sin Cierre Z
            )

        print(f"Días a revisar: {DIAS_A_REVISAR}")

    # ── Cerrar conexión ───────────────────────────────────────────────
    if conexion.is_connected():
        conexion.close()
        print("\nConexión a MySQL cerrada.")