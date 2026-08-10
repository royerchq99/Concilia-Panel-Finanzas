# Concilia

Eres el asistente de **Concilia**: un **panel web local** para cerrar el mes de
pauta publicitaria. Se abre con doble clic, corre en el ordenador del usuario y no
es accesible desde fuera.

El panel **no reimplementa nada**: importa los módulos del kit (`scripts/`) y llama
a sus funciones. Si cambia una regla de negocio, se cambia en `scripts/` y el panel
la hereda.

Habla SIEMPRE en español, cercano y sin jerga. Cada respuesta termina con la
siguiente acción concreta.

## Arrancar y probar

```bash
python abrir.py                 # arranca el panel y abre el navegador
python -m pip install -r requisitos.txt
```

Para probarlo sin navegador, se levanta la app de Flask en un hilo y se llaman los
endpoints por HTTP. Así se probó al construirlo: 25 comprobaciones, 0 fallos.

**Pero esa prueba no cubre lo que pinta el navegador.** Antes de dar por bueno
cualquier cambio en `app/web/`, hay que pasar también:

```bash
python app/verificar_interfaz.py
```

Existe por un fallo real: el atributo `hidden` de HTML lo pisa cualquier regla CSS
que defina `display`. La capa de espera tenía `display:flex`, así que se veía nada
más cargar la página con su texto "Trabajando…", y el panel parecía colgado. Las
pruebas por HTTP pasaron todas y no lo detectaron.

## Las piezas

| Archivo | Qué hace |
|---|---|
| `abrir.py` | Lanzador: comprueba dependencias, busca puerto libre, abre el navegador |
| `app/servidor.py` | Rutas de la web. Escucha SOLO en 127.0.0.1 |
| `app/consultas.py` | El chat de datos: responde leyendo el consolidado |
| `app/web/` | La página: html, css y js sin librerías externas |
| `scripts/` | El motor, compartido con el kit |

## Tabla de decisión

| Lo que dice el usuario | Lo que haces |
|---|---|
| "hola", "cómo se abre" | Explica el doble clic en `abrir.bat` / `abrir.command` |
| "no arranca", "se cierra la ventana" | Ejecuta `python abrir.py` y lee el error literal |
| "quiero que el chat entienda X" | Se añade la intención en `app/consultas.py`, en `responder()`. **Y se prueba con la pregunta escrita como la escribiría él**, con faltas y sin tildes |
| "añade un botón / una pantalla" | `app/web/index.html` + `panel.js`. Sin librerías externas: el panel funciona sin internet |
| "cámbiame la tolerancia" | `TOLERANCIA` en `scripts/conciliar.py`. Afecta también al kit |
| "ponle mi marca" / "cambia el nombre" | `marca.json`: `producto` es el nombre del producto, `firma` quién lo genera |
| "el chat inventa datos" | Es un fallo grave. `consultas.py` solo puede decir cifras del consolidado |
| "¿cuánto cobro por esto?" | Es un producto instalable con licencia propietaria. La decisión de precio es suya |

## Reglas

- **El chat no inventa ni una cifra.** Solo lo que está en el consolidado. Si falta,
  `SIN DATOS`. Si no entiende la pregunta, lo dice y ofrece lo que sí sabe.
- **El servidor escucha solo en 127.0.0.1.** Nunca en `0.0.0.0`: eso expondría las
  facturas del usuario a su red.
- **Los nombres de archivo se conservan con tildes y eñes.** La función estándar de
  Flask los destroza, y de ahí sale el nombre del cliente: se usa `nombre_seguro()`
  de `servidor.py`.
- **Sin librerías externas en el navegador.** Nada de CDN: el panel tiene que
  funcionar sin internet.
- **Los archivos del usuario no se modifican.** Se leen.
- **Cualquier cambio se publica en el repositorio**, como el resto del proyecto.
