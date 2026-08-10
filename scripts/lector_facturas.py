# -*- coding: utf-8 -*-
"""
Lee las facturas en PDF de Google Ads, Meta, TikTok y LinkedIn.

Cada plataforma tiene su formato y ninguno se parece al otro. Lo que sí comparten
es la regla de la llave: el nombre de campaña se compara SIN espacios ni saltos de
línea, porque los PDFs los insertan al extraer el texto.

Si un PDF no se reconoce como ninguna de las cuatro, NO se adivina: se devuelve
como incidencia para que el usuario lo mire.
"""
import os
import re
import glob
import hashlib
import unicodedata

import pdfplumber


def llave(nombre):
    """Llave de cruce: sin espacios ni saltos de línea, en minúsculas."""
    return re.sub(r"\s+", "", str(nombre)).lower()


def huella(ruta):
    """Huella del archivo, para detectar copias tipo 'factura (1).pdf'."""
    h = hashlib.md5()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()


def numero_es(txt):
    """Formato colombiano/español: 48.357 o 1.234.567,89 -> float."""
    t = re.sub(r"[^\d,.\-]", "", str(txt))
    if not t:
        return None
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        t = t.replace(",", ".")
    elif t.count(".") > 1:
        t = t.replace(".", "")
    elif "." in t:
        entera, dec = t.rsplit(".", 1)
        if len(dec) == 3:       # 48.357 son miles, no decimales
            t = entera + dec
    try:
        return float(t)
    except ValueError:
        return None


def numero_en(txt):
    """Formato anglosajón: 1,301,220.48 -> float."""
    t = re.sub(r"[^\d,.\-]", "", str(txt)).replace(",", "")
    try:
        return float(t)
    except ValueError:
        return None


# --------------------------------------------------------------------------
# Detección de plataforma
# --------------------------------------------------------------------------
def detectar(texto_primera_pagina):
    t = texto_primera_pagina.lower()
    if "google llc" in t or "google ads" in t:
        return "Google"
    if "tiktok" in t or "musical.ly" in t or "bytedance" in t:
        return "TikTok"
    if "linkedin" in t:
        return "LinkedIn"
    if "meta platforms" in t or "meta anuncios" in t or "recibo para" in t:
        return "Meta"
    return None


# --------------------------------------------------------------------------
# Google Ads
# --------------------------------------------------------------------------
LINEA_GOOGLE = re.compile(r"^(.+?)\s+([\d,]+)\s+(Clics|Impresiones)\s+(-?[\d,]+)$")
DESCARTA_GOOGLE = ("subtotal", "total", "impuesto", "costos operativos", "tarifa",
                   "descripción", "importe")


def leer_google(pdf, archivo):
    lineas, incidencias = [], []
    cuenta = None
    for pagina in pdf.pages:
        texto = pagina.extract_text() or ""
        for cruda in texto.split("\n"):
            ln = cruda.strip()

            m = re.match(r"^Cuenta:\s*(.+)$", ln)
            if m:
                cuenta = m.group(1).strip()
                continue

            # Créditos de meses anteriores: van a su propia columna, no al facturado.
            if ln.startswith("Actividad no válida") or ln.startswith("Crédito por"):
                continue

            m = LINEA_GOOGLE.match(ln)
            if not m or cuenta is None:
                continue
            nombre = m.group(1).strip()
            if nombre.lower().startswith(DESCARTA_GOOGLE):
                continue
            importe = numero_en(m.group(4))
            if importe is None:
                continue
            lineas.append({
                "plataforma": "Google", "cliente_factura": cuenta,
                "campana": re.sub(r"\s+", "", nombre), "importe": importe,
                "credito": 0.0, "divisa": "COP", "archivo": archivo,
            })

    # Créditos por "Actividad no válida", agregados por campaña.
    for pagina in pdf.pages:
        texto = pagina.extract_text() or ""
        filas = texto.split("\n")
        for i, cruda in enumerate(filas):
            if "Nombre de la campaña:" not in cruda:
                continue
            m = re.search(r"Nombre de la campaña:\s*(.+?)(?:\s*\.\.\.)?\s*$", cruda)
            if not m:
                continue
            nombre = re.sub(r"\s+", "", m.group(1))
            valor = None
            for j in range(max(0, i - 3), min(len(filas), i + 3)):
                if re.match(r"^-[\d,]+$", filas[j].strip()):
                    valor = numero_en(filas[j].strip())
                    break
            if valor is not None:
                lineas.append({
                    "plataforma": "Google", "cliente_factura": cuenta or "",
                    "campana": nombre, "importe": 0.0, "credito": valor,
                    "divisa": "COP", "archivo": archivo, "parcial": True,
                })
    return lineas, incidencias


# --------------------------------------------------------------------------
# Meta  (un recibo por transacción, no una factura mensual)
# --------------------------------------------------------------------------
def sin_tildes(texto):
    """Compara etiquetas sin depender de tildes ni eñes.

    Hace falta porque no todos los PDFs incrustan bien los acentos: la misma
    etiqueta puede llegar como 'Campañas' o como 'Campanas'.
    """
    t = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in t if not unicodedata.combining(c)).lower().strip()


def leer_meta(pdf, archivo):
    lineas, incidencias = [], []
    texto = "\n".join((p.extract_text() or "") for p in pdf.pages)
    filas = [l.strip() for l in texto.split("\n")]

    cuenta = ""
    for l in filas:
        m = re.match(r"^Recibo para\s+(.+)$", l)
        if m:
            cuenta = m.group(1).strip()
            break

    # Tras la etiqueta "Campañas" viene el nombre y luego el importe.
    i = None
    for j, l in enumerate(filas):
        if sin_tildes(l) == "campanas":
            i = j
            break
    if i is None:
        return [], [{"archivo": archivo, "tipo": "Meta sin bloque de campañas",
                     "detalle": "No se encontró la etiqueta 'Campañas' en el recibo"}]

    nombre = None
    for l in filas[i + 1:i + 4]:
        if l and not l.startswith("$") and "Impresiones" not in l:
            nombre = l
            break
    if not nombre:
        return [], [{"archivo": archivo, "tipo": "Meta sin nombre de campaña",
                     "detalle": "Tras 'Campañas' no venía un nombre reconocible"}]

    importe = None
    for l in filas[i + 1:i + 6]:
        if l.startswith("$"):
            importe = numero_es(l)
            break
    if importe is None:
        return [], [{"archivo": archivo, "tipo": "Meta sin importe",
                     "detalle": "No se encontró el importe del recibo"}]

    lineas.append({
        "plataforma": "Meta", "cliente_factura": cuenta,
        "campana": re.sub(r"\s+", "", nombre), "importe": importe,
        "credito": 0.0, "divisa": "COP", "archivo": archivo,
    })
    return lineas, incidencias


# --------------------------------------------------------------------------
# TikTok  (la tabla de "Consumption Details")
# --------------------------------------------------------------------------
def leer_tiktok(pdf, archivo):
    lineas, incidencias = [], []
    # pdfplumber suele partir la tabla de consumo en varios trozos, y los trozos
    # que vienen después del primero NO repiten la cabecera. Se recuerda la última
    # cabecera válida y se aplica a los trozos siguientes con el mismo ancho.
    mapa, ancho_mapa = None, None

    for pagina in pdf.pages:
        for tabla in pagina.extract_tables():
            if not tabla or not tabla[0]:
                continue
            cabecera = [(c or "").replace("\n", " ").strip().lower() for c in tabla[0]]

            def col(*claves):
                for k in claves:
                    for j, c in enumerate(cabecera):
                        if k in c:
                            return j
                return None

            # El nombre de campaña viene en 'Campaign Name'. En algunos formatos
            # de TikTok la columna se llama 'Description': se acepta como
            # alternativa, nunca a la vez.
            c_camp = col("campaign name", "campaign", "description")
            c_adv = col("advertiser name", "advertiser")
            c_imp = col("cash consumption", "total consumption", "amount")

            if c_camp is not None and c_imp is not None:
                mapa = (c_camp, c_adv, c_imp)
                ancho_mapa = len(tabla[0])
                filas = tabla[1:]
            elif mapa is not None and len(tabla[0]) == ancho_mapa:
                # Trozo de continuación: sin cabecera, con las mismas columnas.
                c_camp, c_adv, c_imp = mapa
                filas = tabla
            else:
                continue

            for fila in filas:
                if c_camp >= len(fila) or fila[c_camp] is None:
                    continue
                nombre = re.sub(r"\s+", "", str(fila[c_camp]))
                if not nombre or nombre.lower().startswith(("subtotal", "total")):
                    continue
                importe = numero_en(fila[c_imp]) if c_imp < len(fila) else None
                if importe is None:
                    continue
                anunciante = ""
                if c_adv is not None and c_adv < len(fila) and fila[c_adv]:
                    anunciante = re.sub(r"\s+", " ", str(fila[c_adv])).strip()
                lineas.append({
                    "plataforma": "TikTok", "cliente_factura": anunciante,
                    "campana": nombre, "importe": importe, "credito": 0.0,
                    "divisa": "COP", "archivo": archivo,
                })
    if not lineas:
        incidencias.append({"archivo": archivo, "tipo": "TikTok sin detalle",
                            "detalle": "No se encontró la tabla 'Consumption Details'"})
    return lineas, incidencias


# --------------------------------------------------------------------------
# LinkedIn  (factura en USD; el nombre puede ir en la línea siguiente)
# --------------------------------------------------------------------------
def leer_linkedin(pdf, archivo):
    lineas, incidencias = [], []
    texto = "\n".join((p.extract_text() or "") for p in pdf.pages)
    filas = [l.rstrip() for l in texto.split("\n")]

    divisa = "USD"
    m = re.search(r"Currency\s*:\s*([A-Z]{3})", texto)
    if m:
        divisa = m.group(1)

    cliente = ""
    m = re.search(r"PO Number or I/O Number\s*:\s*(.+)", texto)
    if m:
        cliente = m.group(1).strip()

    for i, ln in enumerate(filas):
        m = re.match(r"^\s*(\d+)\s+Campaign:\s*(.*)$", ln)
        if not m:
            continue
        resto = m.group(2).strip()

        # Caso A: nombre e importes en la misma línea.
        mm = re.match(r"^(\S+)\s+([\d.,]+)\s+\d+\s+([\d.,]+)\s+([\d.,]+)\s*$", resto)
        if mm:
            nombre, importe = mm.group(1), numero_en(mm.group(3))
        else:
            # Caso B: la línea trae solo los importes; el nombre viene debajo.
            importe = None
            mm = re.match(r"^([\d.,]+)\s+\d+\s+([\d.,]+)\s+([\d.,]+)\s*$", resto)
            if mm:
                importe = numero_en(mm.group(2))
            nombre = None
            for siguiente in filas[i + 1:i + 3]:
                cand = siguiente.strip()
                cand = re.sub(r"\s+[\d.,]+%?\s*$", "", cand).strip()
                if cand and not cand.lower().startswith(
                        ("sponsored", "billing", "cpm", "campaign")):
                    nombre = cand.split()[0]
                    break
        if not nombre or importe is None:
            incidencias.append({
                "archivo": archivo, "tipo": "LinkedIn línea ilegible",
                "detalle": "Línea %s del detalle: %r" % (m.group(1), ln[:70])})
            continue

        lineas.append({
            "plataforma": "LinkedIn", "cliente_factura": cliente,
            "campana": re.sub(r"\s+", "", nombre), "importe": importe,
            "credito": 0.0, "divisa": divisa, "archivo": archivo,
        })
    return lineas, incidencias


LECTORES = {"Google": leer_google, "Meta": leer_meta,
            "TikTok": leer_tiktok, "LinkedIn": leer_linkedin}


def leer_archivo(ruta):
    archivo = os.path.basename(ruta)
    try:
        with pdfplumber.open(ruta) as pdf:
            if not pdf.pages:
                return [], [{"archivo": archivo, "tipo": "PDF vacío",
                             "detalle": "El archivo no tiene páginas"}]
            primera = pdf.pages[0].extract_text() or ""
            if not primera.strip():
                return [], [{"archivo": archivo, "tipo": "PDF sin texto",
                             "detalle": "Parece un escaneo (una foto del documento). "
                                        "Este kit no lee facturas escaneadas."}]
            plataforma = detectar(primera)
            if plataforma is None:
                return [], [{"archivo": archivo, "tipo": "Plataforma no reconocida",
                             "detalle": "No es Google, Meta, TikTok ni LinkedIn. "
                                        "Primera línea: %r" % primera.split("\n")[0][:60]}]
            return LECTORES[plataforma](pdf, archivo)
    except Exception as e:
        return [], [{"archivo": archivo, "tipo": "Error al leer",
                     "detalle": "%s: %s" % (type(e).__name__, e)}]


def leer_carpeta(carpeta):
    """Lee todas las facturas de una carpeta, ignorando copias exactas."""
    lineas, incidencias, vistas = [], [], {}
    rutas = sorted(glob.glob(os.path.join(carpeta, "*.pdf")))
    if not rutas:
        return [], [{"archivo": "(carpeta)", "tipo": "Carpeta vacía",
                     "detalle": "No hay ningún .pdf en %s" % carpeta}]

    for ruta in rutas:
        archivo = os.path.basename(ruta)
        h = huella(ruta)
        if h in vistas:
            incidencias.append({
                "archivo": archivo, "tipo": "Duplicado exacto",
                "detalle": "Copia idéntica de '%s'. Se ignora para no contar dos "
                           "veces el mismo gasto." % vistas[h]})
            continue
        vistas[h] = archivo
        l, inc = leer_archivo(ruta)
        lineas.extend(l)
        incidencias.extend(inc)
    return lineas, incidencias
