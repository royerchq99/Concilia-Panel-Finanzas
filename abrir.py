# -*- coding: utf-8 -*-
"""
Arranca el panel y abre el navegador.

Se ejecuta con doble clic (o con `python abrir.py`). Levanta un servidor que
escucha SOLO en este ordenador: nadie de fuera puede entrar.

Para cerrarlo, cierra esta ventana o pulsa Ctrl+C.
"""
import os
import sys
import time
import socket
import threading
import webbrowser

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(RAIZ, "app"))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

PUERTO_PREFERIDO = 8760


def falta(modulo, instalar):
    print("")
    print("  No encuentro '%s', y hace falta para arrancar." % modulo)
    print("")
    print("  Instálalo con este comando y vuelve a intentarlo:")
    print("      python -m pip install %s" % instalar)
    print("")
    input("  Pulsa Intro para cerrar…")
    sys.exit(1)


def comprobar_dependencias():
    for modulo, paquete in (("flask", "flask"),
                            ("openpyxl", "openpyxl"),
                            ("pdfplumber", "pdfplumber")):
        try:
            __import__(modulo)
        except ImportError:
            falta(modulo, paquete)


def puerto_libre(preferido):
    for p in [preferido] + list(range(preferido + 1, preferido + 20)):
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", p))
            return p
        except OSError:
            continue
        finally:
            s.close()
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def clave_nueva():
    """Contraseña corta y fácil de dictar por teléfono."""
    import secrets
    letras = "abcdefghijkmnpqrstuvwxyz23456789"   # sin l, o, 0, 1
    return "-".join("".join(secrets.choice(letras) for _ in range(4))
                    for _ in range(3))


def main():
    compartir = "--compartir" in sys.argv

    print("")
    print("  Panel de conciliación de pautas")
    print("  " + "-" * 44)
    comprobar_dependencias()

    if compartir:
        clave = os.environ.get("PANEL_CLAVE") or clave_nueva()
        os.environ["PANEL_CLAVE"] = clave
        print("")
        print("  MODO COMPARTIDO: el panel pedirá contraseña.")
        print("")
        print("      Usuario:     lo que sea (da igual)")
        print("      Contraseña:  %s" % clave)
        print("")
        print("  Pásasela a quien vaya a entrar. Sin ella no se puede.")
        print("")

    from servidor import app

    puerto = puerto_libre(PUERTO_PREFERIDO)
    url = "http://127.0.0.1:%d/" % puerto

    print("  Abriendo en el navegador: %s" % url)
    print("")
    print("  Deja esta ventana abierta mientras trabajas.")
    print("  Para cerrar el panel, cierra esta ventana.")
    print("")

    threading.Thread(target=lambda: (time.sleep(1.2), webbrowser.open(url)),
                     daemon=True).start()

    try:
        # host fijo a 127.0.0.1: el panel NO es accesible desde la red.
        app.run(host="127.0.0.1", port=puerto, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n  Panel cerrado.")


if __name__ == "__main__":
    main()
