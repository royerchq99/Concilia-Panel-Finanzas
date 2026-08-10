# Empieza aquí

**Entra** en una página que se abre en tu navegador: arrastras los Excel de pauta y
los PDFs de factura, eliges el mes y pulsas un botón → **sale** el cierre en
pantalla, con su Excel y su PDF, y un chat al que puedes preguntarle sobre lo que
acaba de calcular.

Todo ocurre **en tu ordenador**. Tus facturas no salen de él.

---

## En 2 pasos

### 1. Instala Python (una sola vez)

Si ya lo tienes, sáltate esto.

Descárgalo de [python.org/downloads](https://python.org/downloads). En Windows,
**marca la casilla "Add Python to PATH"** en la primera pantalla del instalador. Es
la única casilla que importa.

### 2. Doble clic

| Tu sistema | El archivo |
|---|---|
| **Windows** | `abrir.bat` |
| **Mac** | `abrir.command` |

Se abre una ventana negra —déjala abierta— y el panel aparece solo en tu navegador.

La primera vez te dirá si falta alguna pieza y te dará el comando exacto para
instalarla. Cópialo, pégalo y vuelve a hacer doble clic.

---

## Cómo se usa

1. **Arrastra los Excel de pauta** al recuadro de la izquierda y **los PDFs de
   factura** al de la derecha. También puedes pulsar *Elegir archivos*.
2. **Elige el mes y el año.**
3. Pulsa **Conciliar**.

En unos segundos tienes el resultado. Desde ahí puedes:

- **Ver el informe** completo, con su botón para guardarlo en PDF.
- **Descargar el Excel** consolidado, con una fila por campaña.
- **Preguntar** en la pestaña de chat.

## ¿Sin datos a mano?

Pulsa **"Usar el ejemplo de práctica"**. Crea dos clientes inventados con **16
errores metidos a propósito** y lo deja listo para conciliar. Es la mejor forma de
ver qué hace en dos minutos, sin tocar nada real.

## Lo que le puedes preguntar al chat

```
¿Cómo fue el mes?              ¿Qué no cuadra?
¿Cuál es la mayor desviación?  ¿Qué campañas no tienen factura?
¿Qué se facturó sin pauta?     Campañas de Google
¿Cuánto ejecutó [cliente]?     ¿Qué clientes hay?
```

Responde leyendo el consolidado, así que **sus cifras son las mismas que las del
informe**. No estima ni interpreta: si un dato no está, te dice `SIN DATOS`. Y si no
entiende la pregunta, te lo dice en vez de inventarse una respuesta.

---

## Si algo falla al arrancar

| Lo que ves | Qué hacer |
|---|---|
| "No encuentro Python" | Instálalo desde python.org marcando *Add Python to PATH* |
| "No encuentro 'flask'" | La ventana te da el comando exacto. Cópialo y pégalo |
| La ventana negra se cierra sola | Ábrela desde la terminal para ver el error: `python abrir.py` |
| El navegador no se abre | Escribe a mano `http://127.0.0.1:8760` |
| "No he podido hablar con el servidor" | Se cerró la ventana negra. Vuelve a hacer doble clic |

## Lo que NO hace

- **No inventa importes.** Lo que falta sale como `SIN DATOS`, nunca como cero.
- **No modifica tus archivos.** Solo los lee.
- **No sale a internet** salvo para consultar el tipo de cambio oficial, y en esa
  consulta solo se envía una fecha.
- **No es accesible desde otro ordenador.** El panel escucha solo en el tuyo.

**Siguiente paso: doble clic en `abrir.bat` (Windows) o `abrir.command` (Mac).**
