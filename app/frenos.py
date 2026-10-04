"""Freno de intentos para el login (auditoría de seguridad del 04/10/2026).

Antes se podían probar contraseñas sin límite. Ahora, por cada tipo de intento
(`que`: "login", "olvide"...):

- 5 fallos desde la misma conexión en 15 minutos → esa conexión espera 15 min.
- 20 fallos en total en 15 minutos, vengan de donde vengan (o contra la misma
  cuenta, si se pasa `cuenta`) → se frena para todos 15 min. Es lo que para a
  quien prueba desde muchas IP a la vez. Roger nunca se queda fuera del todo:
  la puerta de Jarvis (/entrada) entra con un pase firmado y no pasa por aquí.
- Cada fallo tarda 1 segundo más en contestar.

Se guarda en memoria (waitress corre un solo proceso). Si el panel se reinicia,
los contadores vuelven a cero: es aceptable, un reinicio tarda más que el freno.

La IP sale de `X-Real-Ip`: detrás de EasyPanel todas las visitas llegan desde el
proxy, y su Traefik NO manda X-Forwarded-For pero SÍ X-Real-Ip con la IP de cada
visitante (comprobado en producción en Fidelidad el 01/10/2026). El panel solo es
alcanzable a través de ese proxy.

Este archivo es IGUAL en todos los paneles: si se cambia, se cambia en todos.
"""
import threading
import time

from flask import request

POR_CONEXION = 5
EN_TOTAL = 20
VENTANA = 15 * 60
PAUSA_FALLO = 1.0

_cerrojo = threading.Lock()
_fallos = {}


def ip():
    return (request.headers.get("X-Real-Ip") or request.remote_addr or "?").strip()


def _vivos(clave, ahora):
    lista = [t for t in _fallos.get(clave, ()) if ahora - t < VENTANA]
    if lista:
        _fallos[clave] = lista
    else:
        _fallos.pop(clave, None)
    return lista


def _claves(que, cuenta):
    claves = [f"{que}:ip:{ip()}", f"{que}:todos"]
    if cuenta:
        claves.append(f"{que}:cuenta:{cuenta.strip().lower()}")
    return claves


def bloqueado(que="login", cuenta=None):
    """True si hay que frenar este intento (antes de comprobar la clave)."""
    ahora = time.time()
    con_ip, todos, *de_cuenta = _claves(que, cuenta)
    with _cerrojo:
        if len(_vivos(con_ip, ahora)) >= POR_CONEXION:
            return True
        if len(_vivos(todos, ahora)) >= EN_TOTAL:
            return True
        return bool(de_cuenta) and len(_vivos(de_cuenta[0], ahora)) >= POR_CONEXION * 2


def fallo(que="login", cuenta=None):
    ahora = time.time()
    with _cerrojo:
        if len(_fallos) > 5000:   # que nadie llene la memoria inventando IPs
            for k in list(_fallos):
                _vivos(k, ahora)
        for k in _claves(que, cuenta):
            _vivos(k, ahora).append(ahora)
            _fallos.setdefault(k, [ahora])
    time.sleep(PAUSA_FALLO)


def acierto(que="login"):
    with _cerrojo:
        _fallos.pop(f"{que}:ip:{ip()}", None)


def destino_seguro(valor, respaldo):
    """Solo rutas de este mismo panel: '/algo', nunca 'https://otra-web' ni '//otra-web'."""
    valor = (valor or "").strip()
    if valor.startswith("/") and not valor.startswith("//") and "\\" not in valor:
        return valor
    return respaldo


AVISO = "Demasiados intentos fallidos. Esperá 15 minutos y probá otra vez."
