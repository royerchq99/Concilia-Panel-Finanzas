# -*- coding: utf-8 -*-
"""
Comprueba la interfaz sin abrir un navegador.

Existe por un fallo real: el atributo `hidden` de HTML lo pisa cualquier regla CSS
que defina `display`. La capa de espera tenía `display:flex`, así que se veía nada
más cargar la página, con su texto "Trabajando…", y parecía que el panel se había
colgado. Las pruebas por HTTP no lo detectaron porque prueban la API, no lo que
pinta el navegador.

Uso:
    python app/verificar_interfaz.py
"""
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(AQUI, "web")

fallos = []


def comprobar(cond, bien, mal):
    print(("  ✓ " if cond else "  ✗ ") + (bien if cond else mal))
    if not cond:
        fallos.append(mal)
    return cond


def main():
    html = open(os.path.join(WEB, "index.html"), encoding="utf-8").read()
    css = open(os.path.join(WEB, "estilo.css"), encoding="utf-8").read()
    js = open(os.path.join(WEB, "panel.js"), encoding="utf-8").read()

    print("1. El atributo hidden funciona de verdad")
    ocultos = re.findall(r'<[^>]*\bid="([^"]+)"[^>]*\shidden', html)
    ocultos += re.findall(r'<[^>]*\shidden[^>]*\bid="([^"]+)"', html)
    ocultos = sorted(set(ocultos))
    print("     elementos que nacen ocultos: %s" % (", ".join(ocultos) or "ninguno"))

    regla = re.search(r'\[hidden\]\s*\{[^}]*display\s*:\s*none\s*!important', css)
    comprobar(bool(regla) or not ocultos,
              "existe la regla [hidden]{display:none !important}",
              "hay elementos con 'hidden' pero falta [hidden]{display:none !important} "
              "en el CSS: cualquier regla con 'display' los hará visibles")

    print()
    print("2. Los identificadores que usa el JS existen en la página")
    ids_html = set(re.findall(r'\bid="([^"]+)"', html))
    ids_js = set(re.findall(r'\$\("#([A-Za-z0-9_-]+)"\)', js))
    # El JS también crea elementos sobre la marcha: con .id = "x" y con
    # innerHTML, donde el atributo puede ir entre comillas simples.
    creados = set(re.findall(r'\.id\s*=\s*["\']([A-Za-z0-9_-]+)["\']', js))
    creados |= set(re.findall(r'''\bid=[\\]?['"]([A-Za-z0-9_-]+)[\\]?['"]''', js))
    faltan = sorted(ids_js - ids_html - creados)
    comprobar(not faltan,
              "los %d identificadores del JS existen" % len(ids_js),
              "el JS busca elementos que no están en el HTML: %s" % ", ".join(faltan))

    print()
    print("3. Las clases que usa el JS están definidas en el CSS")
    clases_css = set(re.findall(r'\.([a-zA-Z][\w-]*)', css))
    usadas = set()
    for patron in (r'classList\.(?:add|toggle|remove)\("([\w-]+)"',
                   r'className\s*=\s*"([\w -]+)"'):
        for m in re.findall(patron, js):
            usadas.update(m.split())
    huerfanas = sorted(c for c in usadas - clases_css if c)
    comprobar(not huerfanas,
              "las %d clases usadas por el JS existen en el CSS" % len(usadas),
              "el JS usa clases sin estilo: %s" % ", ".join(huerfanas))

    print()
    print("3b. Ninguna clase del JS choca con una regla que la oculte")
    # Existe por un fallo real: los mensajes del chat se creaban con
    # class="msj panel", y '.panel' es la clase de las secciones, que lleva
    # display:none. Las respuestas se generaban bien y quedaban invisibles.
    ocultadoras = set()
    # Sin quitar los comentarios, el selector llega pegado al comentario que
    # tiene encima y nunca coincide. Este verificador ya falló una vez por esto.
    css_limpio = re.sub(r'/\*.*?\*/', " ", css, flags=re.S)
    for m in re.finditer(r'([^{}]+)\{([^}]*)\}', css_limpio):
        selectores, cuerpo = m.group(1), m.group(2)
        if not re.search(r'display\s*:\s*none', cuerpo):
            continue
        for sel in selectores.split(","):
            sel = sel.strip()
            # Solo el caso peligroso: una clase suelta, sin combinar con otra.
            mm = re.fullmatch(r'\.([a-zA-Z][\w-]*)', sel)
            if mm:
                ocultadoras.add(mm.group(1))
    # Las clases no siempre se aplican con un literal completo: en el fallo real
    # era `d.className = "msj " + quien`, y 'quien' valía "panel". Por eso se
    # miran TODOS los textos sueltos del JS y se avisa si alguno coincide con el
    # nombre de una clase que el CSS oculta.
    textos = set(re.findall(r'"([a-zA-Z][\w-]*)"', js))
    textos |= set(re.findall(r"'([a-zA-Z][\w-]*)'", js))
    choques = sorted((usadas | textos) & ocultadoras)
    comprobar(not choques,
              "ninguna de las clases del JS está oculta por otra regla",
              "el JS usa como clase un nombre que el CSS oculta con display:none: "
              "%s. Los elementos se crearían y no se verían." % ", ".join(choques))

    print()
    print("4. Nada externo: el panel funciona sin internet")
    externos = re.findall(r'(?:src|href)="(https?://[^"]+)"', html)
    externos += re.findall(r'@import\s+url\(["\']?(https?://[^)"\']+)', css)
    comprobar(not externos, "sin recursos externos",
              "la página carga cosas de internet: %s" % ", ".join(externos))

    print()
    print("5. Las rutas que llama el JS existen en el servidor")
    servidor = open(os.path.join(AQUI, "servidor.py"), encoding="utf-8").read()
    rutas_srv = set(re.findall(r'@app\.(?:get|post|route)\("([^"]+)"', servidor))
    llamadas = set(re.findall(r'pedir\("(/[^"?]+)', js))
    llamadas |= set(re.findall(r'\.src\s*=\s*"(/[^"?]+)', js))

    def cubierta(ruta):
        for r in rutas_srv:
            patron = "^" + re.sub(r"<[^>]+>", "[^/]+", r) + "$"
            if re.match(patron, ruta):
                return True
        return False

    rotas = sorted(r for r in llamadas if not cubierta(r))
    comprobar(not rotas, "las %d rutas que llama el JS existen" % len(llamadas),
              "el JS llama a rutas que el servidor no tiene: %s" % ", ".join(rotas))

    print()
    if fallos:
        print("%d COMPROBACIONES FALLARON" % len(fallos))
        return 1
    print("LA INTERFAZ ESTÁ BIEN.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
