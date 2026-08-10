# -*- coding: utf-8 -*-
"""
Tipo de cambio oficial COP/USD (la TRM del Banco de la República).

Se consulta el portal de datos abiertos del Gobierno de Colombia, que publica la
serie oficial. Si no responde, el kit NO inventa un tipo de cambio: devuelve None
y quien lo llama tiene que preguntárselo al usuario.

Comprobado el 2026-08-09: la TRM del 31 jul 2026 devolvió 3132.42 (HTTP 200).
"""
import json
import urllib.request
import urllib.parse

URL = "https://www.datos.gov.co/resource/32sa-8pi3.json"
TIEMPO_MAXIMO = 25


def trm_de_fecha(fecha_iso):
    """TRM vigente en una fecha 'AAAA-MM-DD'.

    Devuelve (valor, origen) donde origen explica de dónde salió la cifra,
    o (None, motivo) si no se pudo obtener.
    """
    momento = "%sT00:00:00.000" % fecha_iso
    donde = ("vigenciadesde<='%s' AND vigenciahasta>='%s'" % (momento, momento))
    url = URL + "?" + urllib.parse.urlencode({"$where": donde})

    try:
        peticion = urllib.request.Request(
            url, headers={"User-Agent": "kit-conciliacion-pautas"})
        with urllib.request.urlopen(peticion, timeout=TIEMPO_MAXIMO) as r:
            if r.status != 200:
                return None, "El servicio respondió %s" % r.status
            datos = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return None, "No se pudo consultar la TRM (%s)" % type(e).__name__

    if not datos:
        return None, "El servicio no tiene TRM para el %s" % fecha_iso

    try:
        valor = float(datos[0]["valor"])
    except (KeyError, ValueError, IndexError):
        return None, "La respuesta del servicio no traía un valor legible"

    return valor, "TRM oficial del Banco de la República para el %s" % fecha_iso


def ultimo_dia(anio, mes):
    """Último día del mes, como 'AAAA-MM-DD'. Sin librerías de calendario."""
    dias = [31, 29 if (anio % 4 == 0 and (anio % 100 != 0 or anio % 400 == 0)) else 28,
            31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return "%04d-%02d-%02d" % (anio, mes, dias[mes - 1])


def trm_de_cierre(anio, mes):
    """TRM del último día del mes que se está cerrando."""
    return trm_de_fecha(ultimo_dia(anio, mes))


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3:
        v, o = trm_de_cierre(int(sys.argv[1]), int(sys.argv[2]))
    else:
        v, o = trm_de_fecha("2026-07-31")
    print(v if v is not None else "SIN DATOS", "|", o)
