# -*- coding: utf-8 -*-
"""
El servidor de Rox Panel Finanzas.

Escucha SOLO en 127.0.0.1: la página no es accesible desde la red, ni desde otro
ordenador. Los archivos que sube el usuario no salen de su equipo.

Reutiliza el motor del kit tal cual (lector_pautas, lector_facturas, trm,
conciliar). No duplica ni una regla de negocio.
"""
import os
import re
import sys
import json
import shutil
import unicodedata
import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, send_from_directory, send_file

import lector_pautas
import lector_facturas
import conciliar as motor
import trm as modulo_trm
from consultas import Consultas

WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

# En un servidor, los datos van a un volumen que sobrevive a los despliegues.
# En local, a las carpetas de siempre. Se controla con PANEL_DATOS.
DATOS = os.environ.get("PANEL_DATOS", "").strip() or RAIZ
ENTRADA = os.path.join(DATOS, "entrada")
EJEMPLOS = os.path.join(DATOS, "ejemplos")
WORKSPACE = os.path.join(DATOS, "workspace")

for _d in (os.path.join(ENTRADA, "pautas"), os.path.join(ENTRADA, "facturas"),
           os.path.join(EJEMPLOS, "pautas"), os.path.join(EJEMPLOS, "facturas"),
           WORKSPACE):
    if not os.path.isdir(_d):
        os.makedirs(_d, exist_ok=True)

EXT_PAUTAS = (".xlsx", ".xlsm")
EXT_FACTURAS = (".pdf",)
LIMITE_MB = 200

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = LIMITE_MB * 1024 * 1024

# Último cierre calculado, para que el chat pueda responder sobre él.
ESTADO = {"filas": [], "contexto": {}, "incidencias": [], "sello": None}


# --------------------------------------------------------------- contraseña
# En local no hace falta: solo tú puedes entrar. Pero si el panel se publica en
# internet, la dirección es pública y sin contraseña entraría cualquiera.
CLAVE = os.environ.get("PANEL_CLAVE", "").strip()

# Opcional. Si se deja vacío, el usuario da igual y solo cuenta la contraseña.
USUARIO = os.environ.get("PANEL_USUARIO", "").strip()


def _igual(a, b):
    """Compara sin delatar cuántas letras se acertaron por el tiempo que tarda."""
    import hmac
    return hmac.compare_digest(str(a or ""), str(b or ""))


@app.before_request
def pedir_clave():
    if not CLAVE:
        return None
    # La comprobación de salud del servidor no lleva contraseña: si la pidiera,
    # el contenedor se reiniciaría solo cada pocos segundos.
    if request.path == "/salud":
        return None

    auth = request.authorization
    if auth and _igual(auth.password, CLAVE):
        # El usuario solo se comprueba si se ha configurado uno, y sin distinguir
        # mayúsculas: escribir 'marbel' o 'Marbel' tiene que valer igual. El
        # secreto es la contraseña, no el nombre.
        if not USUARIO or _igual(str(auth.username or "").strip().lower(),
                                 USUARIO.lower()):
            return None

    from flask import Response
    return Response(
        "Este panel está protegido con contraseña.", 401,
        {"WWW-Authenticate": 'Basic realm="Concilia"'})


@app.get("/salud")
def salud():
    """Le dice al servidor que el panel sigue vivo. Sin datos dentro."""
    return jsonify(estado="ok")


def crear_app():
    """Punto de entrada para el servidor de producción (waitress).

    Se niega a arrancar sin contraseña. En local no hace falta —solo tú puedes
    entrar—, pero esta función solo la llama el servidor de producción, que
    escucha hacia fuera. Sin esta comprobación basta con olvidar una variable
    de entorno para dejar las facturas de un cliente abiertas a internet.
    """
    if not CLAVE:
        raise RuntimeError(
            "\n\n"
            "  NO ARRANCO SIN CONTRASEÑA.\n\n"
            "  Este modo escucha hacia fuera, así que sin contraseña cualquiera\n"
            "  que sepa la dirección vería las facturas.\n\n"
            "  Añade la variable de entorno PANEL_CLAVE con una contraseña larga\n"
            "  y vuelve a desplegar.\n\n"
            "  (Para usar el panel en tu ordenador no necesitas nada de esto:\n"
            "   abre abrir.bat o abrir.command.)\n")
    return app


# --------------------------------------------------------------- utilidades
def nombre_seguro(nombre):
    """Sanea el nombre conservando tildes y eñes.

    La función estándar de Flask elimina todo lo que no sea ASCII, y eso
    destrozaría el nombre del cliente: 'Nvo - Diseño - 2026.xlsx' se quedaría en
    'Nvo_-_Diseo_-_2026.xlsx'. Aquí solo se quitan rutas y caracteres peligrosos.
    """
    nombre = os.path.basename(str(nombre).replace("\\", "/"))
    nombre = unicodedata.normalize("NFC", nombre)
    nombre = "".join(c for c in nombre if unicodedata.category(c)[0] != "C")
    nombre = re.sub(r'[<>:"/\\|?*]', "_", nombre).strip(" .")
    return nombre[:180] or "archivo"


def carpeta(tipo, ejemplo=False):
    base = EJEMPLOS if ejemplo else ENTRADA
    return os.path.join(base, "pautas" if tipo == "pautas" else "facturas")


def listar(tipo, ejemplo=False):
    d = carpeta(tipo, ejemplo)
    if not os.path.isdir(d):
        return []
    ext = EXT_PAUTAS if tipo == "pautas" else EXT_FACTURAS
    out = []
    for n in sorted(os.listdir(d)):
        if n.startswith("~$") or not n.lower().endswith(ext):
            continue
        r = os.path.join(d, n)
        out.append({"nombre": n, "kb": max(1, os.path.getsize(r) // 1024)})
    return out


def marca():
    try:
        with open(os.path.join(RAIZ, "marca.json"), encoding="utf-8") as f:
            d = json.load(f)
        return (d.get("firma") or "").strip()
    except Exception:
        return ""


# --------------------------------------------------------------- páginas
@app.get("/")
def inicio():
    return send_from_directory(WEB, "index.html")


@app.get("/web/<path:archivo>")
def estaticos(archivo):
    return send_from_directory(WEB, archivo)


# --------------------------------------------------------------- API
@app.get("/api/estado")
def api_estado():
    hoy = datetime.date.today()
    return jsonify({
        "marca": marca(),
        "meses": lector_pautas.MESES,
        "anio_sugerido": hoy.year,
        "pautas": listar("pautas"),
        "facturas": listar("facturas"),
        "ejemplo_listo": bool(listar("pautas", True) and listar("facturas", True)),
        "hay_cierre": bool(ESTADO["filas"]),
        "sello": ESTADO["sello"],
    })


@app.post("/api/subir")
def api_subir():
    tipo = request.form.get("tipo", "pautas")
    if tipo not in ("pautas", "facturas"):
        return jsonify(error="Tipo de archivo desconocido"), 400

    destino = carpeta(tipo)
    if not os.path.isdir(destino):
        os.makedirs(destino)

    ext = EXT_PAUTAS if tipo == "pautas" else EXT_FACTURAS
    guardados, rechazados = [], []

    for f in request.files.getlist("archivos"):
        if not f or not f.filename:
            continue
        nombre = nombre_seguro(f.filename)
        if not nombre.lower().endswith(ext):
            rechazados.append({
                "nombre": nombre,
                "motivo": "En %s solo entran %s" % (tipo, " o ".join(ext))})
            continue
        f.save(os.path.join(destino, nombre))
        guardados.append(nombre)

    return jsonify(guardados=guardados, rechazados=rechazados,
                   pautas=listar("pautas"), facturas=listar("facturas"))


@app.post("/api/vaciar")
def api_vaciar():
    tipo = request.json.get("tipo") if request.is_json else None
    tipos = [tipo] if tipo in ("pautas", "facturas") else ["pautas", "facturas"]
    borrados = 0
    for t in tipos:
        d = carpeta(t)
        if not os.path.isdir(d):
            continue
        for n in os.listdir(d):
            if n == ".gitkeep":
                continue
            try:
                os.remove(os.path.join(d, n))
                borrados += 1
            except OSError:
                pass
    return jsonify(borrados=borrados, pautas=listar("pautas"),
                   facturas=listar("facturas"))


@app.post("/api/quitar")
def api_quitar():
    """Borra UN archivo, no toda la carpeta. `vaciar` sigue existiendo para
    borrar todo de golpe; esto es para quitar uno que se subió por error."""
    datos = request.get_json(silent=True) or {}
    tipo = datos.get("tipo")
    if tipo not in ("pautas", "facturas"):
        return jsonify(error="Tipo de archivo desconocido"), 400
    nombre = nombre_seguro(datos.get("nombre") or "")
    if not nombre:
        return jsonify(error="No sé qué archivo quieres quitar"), 400

    destino = carpeta(tipo)
    ruta = os.path.join(destino, nombre)
    # nombre_seguro() ya quita rutas y ".."; esto es una segunda comprobación
    # para no borrar nada fuera de su carpeta.
    if os.path.dirname(os.path.abspath(ruta)) != os.path.abspath(destino):
        return jsonify(error="Nombre de archivo no válido"), 400
    if not os.path.isfile(ruta):
        return jsonify(error="Ese archivo ya no está"), 404
    os.remove(ruta)
    return jsonify(pautas=listar("pautas"), facturas=listar("facturas"))


@app.post("/api/ejemplo")
def api_ejemplo():
    """Genera el caso de práctica inventado y lo deja listo para conciliar."""
    try:
        import generar_ejemplo
        # En el servidor los ejemplos viven en el volumen, no junto al código.
        generar_ejemplo.EJ = EJEMPLOS
        generar_ejemplo.PAUTAS = os.path.join(EJEMPLOS, "pautas")
        generar_ejemplo.FACTURAS = os.path.join(EJEMPLOS, "facturas")
        generar_ejemplo.main()
    except ImportError:
        return jsonify(error="Falta la librería fpdf2 para crear el ejemplo. "
                             "Instálala con: python -m pip install fpdf2"), 500
    except Exception as e:
        return jsonify(error="No se pudo crear el ejemplo: %s" % e), 500
    return jsonify(pautas=listar("pautas", True), facturas=listar("facturas", True))


@app.post("/api/conciliar")
def api_conciliar():
    datos = request.get_json(silent=True) or {}
    mes = datos.get("mes")
    anio = datos.get("anio")
    usar_ejemplo = bool(datos.get("ejemplo"))
    trm_manual = datos.get("trm")

    if mes not in lector_pautas.MESES:
        return jsonify(error="Elige un mes de la lista."), 400
    try:
        anio = int(anio)
    except (TypeError, ValueError):
        return jsonify(error="El año tiene que ser un número, por ejemplo 2026."), 400
    if not (2000 <= anio <= 2100):
        return jsonify(error="Ese año no parece correcto."), 400

    dir_p = carpeta("pautas", usar_ejemplo)
    dir_f = carpeta("facturas", usar_ejemplo)

    if not listar("pautas", usar_ejemplo):
        return jsonify(error="No hay ningún Excel de pauta. Sube al menos uno, o "
                             "usa el ejemplo de práctica."), 400
    if not listar("facturas", usar_ejemplo):
        return jsonify(error="No hay ninguna factura en PDF. Sube al menos una, o "
                             "usa el ejemplo de práctica."), 400

    filas_pauta, inc_p = lector_pautas.leer_carpeta(dir_p, mes)
    lineas_fact, inc_f = lector_facturas.leer_carpeta(dir_f)
    reales = [l for l in lineas_fact if not l.get("parcial")]

    if not filas_pauta and not reales:
        detalle = "; ".join("%s: %s" % (i["archivo"], i["detalle"])
                            for i in (inc_p + inc_f)[:4])
        return jsonify(error="No se pudo leer nada. %s" % (detalle or "")), 400

    # Tipo de cambio, solo si hace falta.
    otras = sorted({l["divisa"] for l in reales if l["divisa"] != "COP"})
    valor_trm, origen_trm = None, "No hizo falta: todo estaba en COP"
    aviso_trm = None
    if otras:
        if trm_manual:
            try:
                valor_trm = float(trm_manual)
                origen_trm = "Aportada a mano: %.2f" % valor_trm
            except (TypeError, ValueError):
                return jsonify(error="El tipo de cambio tiene que ser un número."), 400
        else:
            valor_trm, origen_trm = modulo_trm.trm_de_cierre(
                anio, lector_pautas.MESES.index(mes) + 1)
        if valor_trm is None:
            aviso_trm = ("Hay facturas en %s y no se pudo obtener el tipo de cambio "
                         "(%s). Esas campañas quedan SIN DATOS. Puedes escribir el "
                         "tipo de cambio a mano y volver a conciliar."
                         % (", ".join(otras), origen_trm))

    filas, inc_c = motor.conciliar(filas_pauta, lineas_fact, valor_trm, origen_trm)
    incidencias = inc_p + inc_f + inc_c

    contexto = {
        "mes": mes, "anio": anio,
        "hoy": datetime.date.today().strftime("%d/%m/%Y"),
        "Mes conciliado": "%s %s" % (mes, anio),
        "Origen de los datos": "ejemplo de práctica" if usar_ejemplo
                               else "archivos subidos por el usuario",
        "Campañas de pauta leídas": len(filas_pauta),
        "Líneas de factura leídas": len(reales),
        "Tolerancia": "1 % — por debajo de esa diferencia se considera que cuadra",
        "Tipo de cambio": origen_trm if valor_trm is None
                          else "%.2f COP/USD — %s" % (valor_trm, origen_trm),
        "Créditos": "Los créditos por actividad no válida van en columna aparte, "
                    "no restados del facturado",
        "Regla de los huecos": "Lo que falta se marca SIN DATOS. No se estima nunca",
    }

    if not os.path.isdir(WORKSPACE):
        os.makedirs(WORKSPACE)
    mes_num = lector_pautas.MESES.index(mes) + 1
    sello = "%04d-%02d" % (anio, mes_num)

    # Mismo cálculo que hace conciliar.py en su línea de comandos: sin esto el
    # informe del panel se queda sin comparación, tendencia ni acumulado
    # aunque el motor ya los sabe hacer.
    mes_ant, anio_ant = (mes_num - 1, anio) if mes_num > 1 else (12, anio - 1)
    sello_ant = "%04d-%02d" % (anio_ant, mes_ant)
    resumen_ant = motor.leer_resumen_mes(
        os.path.join(WORKSPACE, "%s-consolidado-pautas.xlsx" % sello_ant))
    anterior = ({cl: v["facturado"] for cl, v in resumen_ant.items()}
                if resumen_ant else None)
    contexto["Comparación con el mes anterior"] = (
        "%s-consolidado-pautas.xlsx (columna Facturado de 'Resumen por cliente')"
        % sello_ant if anterior else
        "No hay consolidado de %s en workspace/, no se compara" % sello_ant)

    historico = []
    for a_h, m_h in reversed(motor.meses_hacia_atras(anio, mes_num, 6)):
        sello_h = "%04d-%02d" % (a_h, m_h)
        resumen_h = motor.leer_resumen_mes(
            os.path.join(WORKSPACE, "%s-consolidado-pautas.xlsx" % sello_h))
        if resumen_h:
            historico.append((sello_h, resumen_h))

    acumulado = None
    meses_previos = list(range(1, mes_num))
    if meses_previos:
        acumulado = {}
        for m_a in meses_previos:
            sello_a = "%04d-%02d" % (anio, m_a)
            resumen_a = motor.leer_resumen_mes(
                os.path.join(WORKSPACE, "%s-consolidado-pautas.xlsx" % sello_a))
            if not resumen_a:
                continue
            for cl, v in resumen_a.items():
                d = acumulado.setdefault(
                    cl, {"consumido": 0.0, "facturado": 0.0, "meses": 0})
                d["consumido"] += v["consumido"] or 0.0
                d["facturado"] += v["facturado"] or 0.0
                d["meses"] += 1

    ruta_x = motor.escribir_excel(
        os.path.join(WORKSPACE, "%s-consolidado-pautas.xlsx" % sello),
        filas, incidencias, contexto)
    ruta_h = motor.escribir_html(
        os.path.join(WORKSPACE, "%s-informe-conciliacion.html" % sello),
        filas, incidencias, contexto, anterior, historico, acumulado)

    ESTADO["filas"] = filas
    ESTADO["contexto"] = contexto
    ESTADO["incidencias"] = incidencias
    ESTADO["sello"] = sello

    cf, ce = {}, {}
    for f in filas:
        cf[f["estado"]] = cf.get(f["estado"], 0) + 1
        ce[f["estado_ejec"]] = ce.get(f["estado_ejec"], 0) + 1

    def suma(campo):
        v = [f[campo] for f in filas if f.get(campo) is not None]
        return sum(v) if v else None

    comparables = cf.get("CUADRA", 0) + cf.get("DESVIACION EN FACTURACION", 0)
    duplicados = [f for f in filas if f.get("posible_duplicado")]
    return jsonify({
        "sello": sello,
        "campanas": len(filas),
        "clientes": len({f["cliente"] for f in filas if f.get("cliente")}),
        "presupuesto": suma("plan"),
        "consumido": suma("consumido"),
        "facturado": suma("facturado"),
        "facturacion": cf,
        "ejecucion": ce,
        "comparables": comparables,
        "cuadran": cf.get("CUADRA", 0),
        "incidencias": [{"archivo": i.get("archivo"), "tipo": i.get("tipo"),
                         "detalle": i.get("detalle")} for i in incidencias],
        "duplicados": [{"campana": f["campana"], "cliente": f.get("cliente"),
                        "facturado": f.get("facturado"),
                        "archivos": f.get("archivos_duplicados", [])}
                       for f in duplicados],
        "tiene_historico": bool(historico),
        "aviso_trm": aviso_trm,
        "excel": os.path.basename(ruta_x),
        "informe": os.path.basename(ruta_h),
    })


@app.get("/api/informe")
def api_informe():
    if not ESTADO["sello"]:
        return "Todavía no hay ningún cierre.", 404
    ruta = os.path.join(WORKSPACE, "%s-informe-conciliacion.html" % ESTADO["sello"])
    if not os.path.exists(ruta):
        return "No encuentro el informe.", 404
    return send_file(ruta)


@app.get("/api/descargar/<cual>")
def api_descargar(cual):
    if not ESTADO["sello"]:
        return jsonify(error="Todavía no hay ningún cierre"), 404
    nombres = {"excel": "%s-consolidado-pautas.xlsx" % ESTADO["sello"],
               "informe": "%s-informe-conciliacion.html" % ESTADO["sello"]}
    if cual not in nombres:
        return jsonify(error="No sé qué archivo quieres"), 400
    ruta = os.path.join(WORKSPACE, nombres[cual])
    if not os.path.exists(ruta):
        return jsonify(error="Ese archivo ya no está en workspace/"), 404
    return send_file(ruta, as_attachment=True, download_name=nombres[cual])


@app.post("/api/chat")
def api_chat():
    datos = request.get_json(silent=True) or {}
    pregunta = (datos.get("pregunta") or "").strip()
    respuesta = Consultas(ESTADO["filas"], ESTADO["contexto"]).responder(pregunta)
    return jsonify(respuesta)


@app.errorhandler(413)
def demasiado_grande(_):
    return jsonify(error="Los archivos pesan más de %d MB juntos. Súbelos por "
                         "tandas." % LIMITE_MB), 413
