# -*- coding: utf-8 -*-
"""
El chat de datos: responde preguntas leyendo el consolidado que se acaba de
calcular. Sin modelo de lenguaje, sin internet y sin coste.

Regla dura: solo se dicen cifras que están en el consolidado. Nada se estima, nada
se interpreta y nada se rellena. Si algo no está, se responde igual que el informe:
SIN DATOS.

Cuando no entiende una pregunta, lo dice y ofrece lo que sí sabe responder. Nunca
contesta algo aproximado por quedar bien.
"""
import re
import unicodedata


def sin_tildes(texto):
    t = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in t if not unicodedata.combining(c))


def norm(texto):
    return re.sub(r"\s+", " ", sin_tildes(texto)).strip().lower()


def dinero(v):
    if v is None:
        return "SIN DATOS"
    return "{:,.0f}".format(v).replace(",", ".")


def pct(v):
    return "SIN DATOS" if v is None else "%+.1f %%" % (v * 100)


PLATAFORMAS = ["google", "meta", "tiktok", "linkedin", "masivo"]

AYUDA = [
    "cómo fue el mes",
    "qué no cuadra",
    "cuánto ejecutó [cliente]",
    "campañas de [plataforma]",
    "cuál es la mayor desviación",
    "qué campañas no tienen factura",
    "qué se facturó sin pauta",
    "cuántas campañas hay",
]


class Consultas(object):
    """Responde sobre un cierre ya calculado."""

    def __init__(self, filas, contexto):
        self.filas = filas or []
        self.contexto = contexto or {}

    # ------------------------------------------------------------ utilidades
    def _suma(self, filas, campo):
        vals = [f[campo] for f in filas if f.get(campo) is not None]
        return sum(vals) if vals else None

    def _clientes(self):
        return sorted({f["cliente"] for f in self.filas if f.get("cliente")})

    def _busca_cliente(self, pregunta):
        p = norm(pregunta)
        mejor, largo = None, 0
        for c in self._clientes():
            n = norm(c)
            if n and n in p and len(n) > largo:
                mejor, largo = c, len(n)
        return mejor

    def _busca_plataforma(self, pregunta):
        p = norm(pregunta)
        for pl in PLATAFORMAS:
            if pl in p:
                return pl
        return None

    def _de_plataforma(self, plataforma):
        out = []
        for f in self.filas:
            pf = norm(f.get("plataforma_factura") or "")
            pp = norm(f.get("plataforma_pauta") or "")
            if plataforma in pf or plataforma in pp:
                out.append(f)
        return out

    def _en_juego(self, f):
        if f.get("facturado") is None or f.get("consumido") is None:
            return 0.0
        return abs(f["facturado"] - f["consumido"])

    def _tabla(self, filas, columnas=None):
        columnas = columnas or ["campana", "cliente", "consumido", "facturado",
                                "estado"]
        cab = {"campana": "Campaña", "cliente": "Cliente", "producto": "Producto",
               "plan": "Presupuesto", "consumido": "Consumido",
               "facturado": "Facturado", "estado": "Estado facturación",
               "estado_ejec": "Ejecución", "plataforma_factura": "Plataforma"}
        filas_out = []
        for f in filas:
            fila = []
            for c in columnas:
                v = f.get(c)
                if c in ("plan", "consumido", "facturado"):
                    fila.append(dinero(v))
                else:
                    fila.append("—" if v is None else str(v))
            filas_out.append(fila)
        return {"cabeceras": [cab.get(c, c) for c in columnas], "filas": filas_out}

    # ------------------------------------------------------------ respuestas
    def resumen(self):
        n = len(self.filas)
        if not n:
            return self._sin_cierre()
        plan = self._suma(self.filas, "plan")
        cons = self._suma(self.filas, "consumido")
        fact = self._suma(self.filas, "facturado")
        cuenta = {}
        for f in self.filas:
            cuenta[f["estado"]] = cuenta.get(f["estado"], 0) + 1
        comparables = cuenta.get("CUADRA", 0) + cuenta.get("DESVIACION EN FACTURACION", 0)

        t = ["**%s %s** · %d campañas de %d clientes."
             % (self.contexto.get("mes", ""), self.contexto.get("anio", ""),
                n, len(self._clientes()))]
        t.append("")
        t.append("- Presupuesto: **%s**" % dinero(plan))
        t.append("- Consumido: **%s**" % dinero(cons))
        t.append("- Facturado: **%s**" % dinero(fact))
        t.append("")
        if comparables:
            t.append("De las **%d campañas que se pueden comparar**, **%d cuadran** "
                     "con su factura y **%d tienen diferencias**."
                     % (comparables, cuenta.get("CUADRA", 0),
                        cuenta.get("DESVIACION EN FACTURACION", 0)))
        else:
            t.append("Ninguna campaña tiene pauta y factura a la vez, así que no se "
                     "pudo comparar nada. Suele significar que falta algún archivo.")
        if cuenta.get("SIN FACTURA"):
            t.append("Hay **%d sin factura** y **%d facturadas sin pauta**."
                     % (cuenta.get("SIN FACTURA", 0), cuenta.get("SIN PAUTA", 0)))
        return {"texto": "\n".join(t)}

    def por_cliente(self, cliente):
        filas = [f for f in self.filas if f.get("cliente") == cliente]
        if not filas:
            return {"texto": "No encuentro campañas de **%s** en este cierre." % cliente}
        plan = self._suma(filas, "plan")
        cons = self._suma(filas, "consumido")
        fact = self._suma(filas, "facturado")
        ok = sum(1 for f in filas if f["estado"] == "CUADRA")
        desv = [f for f in filas if f["estado"] == "DESVIACION EN FACTURACION"]

        t = ["**%s** · %d campañas" % (cliente, len(filas)), ""]
        t.append("- Presupuesto: **%s**" % dinero(plan))
        t.append("- Consumido: **%s**" % dinero(cons))
        t.append("- Facturado: **%s**" % dinero(fact))
        if plan and cons:
            t.append("- Ejecución sobre el plan: **%s**" % pct((cons - plan) / plan))
        t.append("")
        t.append("**%d cuadran** con su factura." % ok)
        if desv:
            t.append("**%d tienen diferencia de facturación.**" % len(desv))
        return {"texto": "\n".join(t),
                "tabla": self._tabla(sorted(filas, key=self._en_juego, reverse=True)[:25])}

    def desviaciones(self):
        d = [f for f in self.filas if f["estado"] == "DESVIACION EN FACTURACION"]
        if not d:
            return {"texto": "**Ninguna campaña se sale de la tolerancia del 1 %.** "
                             "Todo lo facturado coincide con lo ejecutado."}
        d.sort(key=self._en_juego, reverse=True)
        total = sum(self._en_juego(f) for f in d)
        t = ["**%d campañas** con diferencia entre lo consumido y lo facturado, "
             "por un total de **%s**." % (len(d), dinero(total)), "",
             "Ordenadas por dinero en juego, no por porcentaje:"]
        return {"texto": "\n".join(t), "tabla": self._tabla(d[:25])}

    def mayor_desviacion(self):
        d = [f for f in self.filas if f["estado"] == "DESVIACION EN FACTURACION"]
        if not d:
            return {"texto": "No hay ninguna campaña fuera de tolerancia."}
        f = max(d, key=self._en_juego)
        t = ["La mayor diferencia es **%s**" % f["campana"],
             "" ,
             "- Cliente: **%s**" % (f.get("cliente") or "sin pauta"),
             "- Consumido: **%s**" % dinero(f["consumido"]),
             "- Facturado: **%s**" % dinero(f["facturado"]),
             "- Diferencia: **%s** (%s)"
             % (dinero(self._en_juego(f)), pct(f.get("desv_facturacion")))]
        return {"texto": "\n".join(t)}

    def por_plataforma(self, plataforma):
        filas = self._de_plataforma(plataforma)
        if not filas:
            return {"texto": "No hay campañas de **%s** en este cierre." % plataforma}
        cons = self._suma(filas, "consumido")
        fact = self._suma(filas, "facturado")
        ok = sum(1 for f in filas if f["estado"] == "CUADRA")
        t = ["**%s** · %d campañas" % (plataforma.capitalize(), len(filas)), "",
             "- Consumido: **%s**" % dinero(cons),
             "- Facturado: **%s**" % dinero(fact),
             "- Cuadran: **%d de %d**" % (ok, len(filas))]
        return {"texto": "\n".join(t),
                "tabla": self._tabla(sorted(filas, key=self._en_juego,
                                            reverse=True)[:25])}

    def sin_factura(self):
        filas = [f for f in self.filas if f["estado"] == "SIN FACTURA"]
        if not filas:
            return {"texto": "**Todas las campañas con pauta tienen su factura.**"}
        cons = self._suma(filas, "consumido")
        t = ["**%d campañas ejecutadas sin factura**, por **%s**."
             % (len(filas), dinero(cons)), "",
             "Están en la pauta pero no aparecen en ningún PDF. O falta la factura, "
             "o esas campañas no se han facturado todavía."]
        return {"texto": "\n".join(t),
                "tabla": self._tabla(filas[:25],
                                     ["campana", "cliente", "plataforma_pauta",
                                      "plan", "consumido"])}

    def sin_pauta(self):
        filas = [f for f in self.filas if f["estado"] == "SIN PAUTA"]
        if not filas:
            return {"texto": "**Todo lo facturado está en alguna pauta.**"}
        fact = self._suma(filas, "facturado")
        porpl = {}
        for f in filas:
            p = f.get("plataforma_factura") or "—"
            porpl[p] = porpl.get(p, 0) + 1
        detalle = ", ".join("%s (%d)" % (p, n) for p, n in sorted(porpl.items()))
        t = ["**%d campañas facturadas que no están en ninguna pauta**, por **%s**."
             % (len(filas), dinero(fact)), "",
             "Por plataforma: %s." % detalle, "",
             "Normalmente significa que **falta el Excel de pauta** de esos clientes."]
        return {"texto": "\n".join(t),
                "tabla": self._tabla(sorted(filas, key=lambda f: -(f.get("facturado") or 0))[:25],
                                     ["campana", "plataforma_factura", "facturado"])}

    def recuentos(self):
        if not self.filas:
            return self._sin_cierre()
        cf, ce = {}, {}
        for f in self.filas:
            cf[f["estado"]] = cf.get(f["estado"], 0) + 1
            ce[f["estado_ejec"]] = ce.get(f["estado_ejec"], 0) + 1
        t = ["**%d campañas en total.**" % len(self.filas), "", "**Facturación:**"]
        for k, v in sorted(cf.items(), key=lambda x: -x[1]):
            t.append("- %s: **%d**" % (k, v))
        t.append("")
        t.append("**Ejecución frente al plan:**")
        for k, v in sorted(ce.items(), key=lambda x: -x[1]):
            t.append("- %s: **%d**" % (k, v))
        return {"texto": "\n".join(t)}

    def lista_clientes(self):
        cl = self._clientes()
        if not cl:
            return {"texto": "No hay ningún cliente con pauta en este cierre."}
        t = ["**%d clientes** en este cierre:" % len(cl), ""]
        for c in cl:
            filas = [f for f in self.filas if f.get("cliente") == c]
            t.append("- **%s** — %d campañas, %s consumido"
                     % (c, len(filas), dinero(self._suma(filas, "consumido"))))
        return {"texto": "\n".join(t)}

    def _sin_cierre(self):
        return {"texto": "Todavía no hay ningún cierre calculado. Sube los archivos, "
                         "elige el mes y pulsa **Conciliar**."}

    def _no_entiendo(self, pregunta):
        t = ["No he entendido la pregunta, y prefiero decírtelo antes que darte una "
             "cifra que no te sirva.", "", "Esto sí sé responderlo:"]
        for a in AYUDA:
            t.append("- %s" % a)
        cl = self._clientes()
        if cl:
            t.append("")
            t.append("Clientes de este cierre: %s." % ", ".join(cl[:8]))
        return {"texto": "\n".join(t)}

    # ------------------------------------------------------------ despacho
    def responder(self, pregunta):
        if not self.filas:
            return self._sin_cierre()
        p = norm(pregunta)
        if not p:
            return self._no_entiendo(pregunta)

        # Ayuda
        if any(k in p for k in ("que puedes hacer", "ayuda", "que sabes",
                                "como funciona", "que puedo preguntar")):
            return self._no_entiendo(pregunta)

        # Clientes
        if any(k in p for k in ("que clientes", "cuantos clientes", "lista de clientes",
                                "los clientes")):
            return self.lista_clientes()

        # Recuentos
        if any(k in p for k in ("cuantas campanas", "cuantas hay", "recuento",
                                "cuantos estados", "numero de campanas")):
            return self.recuentos()

        # Mayor desviación
        if any(k in p for k in ("mayor desviacion", "la peor", "la mas grande",
                                "mayor diferencia", "peor campana")):
            return self.mayor_desviacion()

        # Sin factura
        if any(k in p for k in ("sin factura", "no tienen factura", "falta factura",
                                "no facturad", "que falta por facturar")):
            return self.sin_factura()

        # Sin pauta
        if any(k in p for k in ("sin pauta", "no estan en la pauta", "sin plan",
                                "facturado sin", "huerfan")):
            return self.sin_pauta()

        # Desviaciones
        if any(k in p for k in ("no cuadra", "desviacion", "diferencia", "mal cobrad",
                                "cobraron de mas", "cobraron mal", "que reviso",
                                "que hay que mirar", "problemas")):
            return self.desviaciones()

        # Plataforma
        pl = self._busca_plataforma(p)
        if pl:
            return self.por_plataforma(pl)

        # Cliente
        cl = self._busca_cliente(p)
        if cl:
            return self.por_cliente(cl)

        # Resumen
        if any(k in p for k in ("resumen", "como fue", "como va", "total", "cierre",
                                "en general", "que tal", "estado del mes")):
            return self.resumen()

        return self._no_entiendo(pregunta)
