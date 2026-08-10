# Rox Panel Finanzas

Panel para cerrar el mes de inversión publicitaria de varios clientes a la vez,
cruzando lo que se planeó, lo que se ejecutó y lo que facturaron los medios.

> **Entra** en una página que se abre en tu navegador: arrastras los Excel de pauta y
> los PDFs de factura, eliges el mes y pulsas un botón → **sale** el cierre en
> pantalla, con su Excel y su PDF descargables, y un chat al que puedes preguntarle
> sobre lo que acaba de calcular.

**Todo en local.** Es una página web, pero corre en tu ordenador: tus facturas no
salen de él y el panel no es accesible desde ningún otro equipo.

---

## El problema que resuelve

Cerrar la pauta de un mes significa abrir el Excel de cada cliente, meterse en la
hoja del mes, sacar campaña por campaña el presupuesto y lo consumido, y después
abrir las facturas de Google, Meta, TikTok y LinkedIn para comprobar que lo cobrado
coincide.

Con quince clientes y cuatro plataformas son horas. Y en ese trabajo se escapan
cosas que nadie ve a ojo: un PDF descargado dos veces que suma doble, una campaña
facturada que no estaba en ninguna pauta, un cobro un 7 % por encima de lo ejecutado.

---

## Instalación

| Requisito | Cómo conseguirlo |
|---|---|
| **Python 3.9 o superior** | [python.org/downloads](https://python.org/downloads) — en Windows marca *"Add Python to PATH"* |

Y ya. **Sin claves de API, sin suscripciones, sin servidor, sin base de datos.** Las
librerías las instala el propio panel si faltan, y te dice el comando exacto.

### Arrancar

| Sistema | Qué hacer |
|---|---|
| **Windows** | Doble clic en `abrir.bat` |
| **Mac** | Doble clic en `abrir.command` |
| **Cualquiera** | `python abrir.py` |

Se abre una ventana de consola —hay que dejarla abierta— y el navegador se abre solo
en `http://127.0.0.1:8760`. Si ese puerto está ocupado, busca otro libre.

Para instalar todo de golpe:

```bash
python -m pip install -r requisitos.txt
```

---

## Las cuatro pantallas

### 1 · Cerrar el mes

Dos zonas donde arrastrar archivos: **Excel de pauta** y **facturas en PDF**. Los
nombres se conservan tal cual, con tildes y eñes incluidas — importante, porque el
nombre del archivo Excel es el que identifica al cliente.

Eliges mes y año, pulsas **Conciliar**. Hay un botón para vaciar y empezar otro mes,
y otro para cargar el **ejemplo de práctica**.

### 2 · Resultado

El veredicto arriba —qué porcentaje de campañas conciliables cuadran—, las cifras
del mes, los recuentos por estado y las incidencias. Desde aquí se descargan el
Excel y el informe.

### 3 · Informe

El informe completo embebido, con su propio botón para guardarlo en PDF.

### 4 · Preguntar

El chat sobre el cierre. Ver más abajo.

---

## El chat

Responde **leyendo el consolidado** que se acaba de calcular. Sin modelo de
lenguaje, sin internet y sin coste: las respuestas son instantáneas y sus cifras son
exactamente las del informe.

Entiende, entre otras:

| Pregunta | Respuesta |
|---|---|
| *¿Cómo fue el mes?* | Resumen con las tres cifras y el recuento |
| *¿Qué no cuadra?* | Las campañas con diferencia de facturación, por importe |
| *¿Cuál es la mayor desviación?* | La campaña con más dinero en juego |
| *¿Qué campañas no tienen factura?* | Las `SIN FACTURA`, con su importe |
| *¿Qué se facturó sin pauta?* | Las `SIN PAUTA`, agrupadas por plataforma |
| *Campañas de Google* | Filtra por plataforma |
| *¿Cuánto ejecutó [cliente]?* | Las cifras de ese cliente |
| *¿Qué clientes hay?* | La lista con sus totales |

**Reglas del chat**, que son las del kit:

- Solo dice cifras que están en el consolidado. **No estima, no interpreta, no
  rellena.**
- Si un dato falta, responde `SIN DATOS`, igual que el informe.
- **Si no entiende la pregunta, lo dice** y ofrece lo que sí sabe responder. Nunca
  contesta algo aproximado por quedar bien.

---

## Cómo funciona por dentro

El panel **no reimplementa nada**: importa y llama a los mismos módulos del kit, ya
probados. Por eso sus resultados son idénticos a los del kit para los mismos
archivos — está comprobado con el ejemplo de práctica, que lleva 16 errores
plantados y da el mismo recuento en los dos.

```
Rox-Panel-Finanzas/
├── abrir.py / abrir.bat / abrir.command   El lanzador
├── app/
│   ├── servidor.py       Las rutas de la web
│   ├── consultas.py      El chat de datos
│   └── web/              La página: html, css y js, sin librerías externas
├── scripts/              El motor, compartido con el kit
│   ├── lector_pautas.py      Lee los Excel
│   ├── lector_facturas.py    Lee los PDFs de las 4 plataformas
│   ├── trm.py                Consulta el tipo de cambio oficial
│   ├── conciliar.py          Cruza, calcula y escribe los entregables
│   ├── verificar.py          Comprueba el resultado
│   └── generar_ejemplo.py    Crea el caso de práctica inventado
├── entrada/              Lo que subes por la web acaba aquí
├── ejemplos/             El caso de práctica (se genera, no viaja)
└── workspace/            Los resultados
```

### Las tres cifras y los dos estados

| Cifra | De dónde sale |
|---|---|
| **Presupuesto planeado** | columna del Excel de pauta |
| **Consumido** | columna del mismo Excel |
| **Facturado** | la línea correspondiente del PDF |

Se cruzan por el **nombre técnico de la campaña**, en minúsculas y sin espacios
(los PDFs de Google separan las letras y los de TikTok parten los nombres; quitando
los espacios en los dos lados, casan).

Cada campaña recibe **dos estados**: uno de **facturación** (¿me cobraron lo que
gasté? — lo urgente) y otro de **ejecución** (¿gasté lo que dije? — informativo).
Tolerancia: **1 %**.

Los detalles completos —las cuatro plataformas, el tipo de cambio, los créditos por
actividad no válida— están en el README del kit, en
[Rox-Kit-Finanzas](https://github.com/royerchq99/Rox-Kit-Finanzas).

---

## Ponerle tu marca

Edita `marca.json`:

```json
{ "firma": "Tu Agencia", "pie": "" }
```

Aparece en la cabecera del panel y en el informe. Déjalo vacío para marca blanca.

---

## Seguridad y privacidad

- **El servidor escucha solo en `127.0.0.1`.** No es accesible desde la red local ni
  desde internet, ni siquiera desde otro ordenador de la misma oficina.
- **Tus archivos no salen del equipo.** Se guardan en `entrada/` y se leen desde ahí.
- **No hay cuentas ni contraseñas** porque no hacen falta: solo tú tienes acceso.
- La única salida a internet es la consulta del tipo de cambio oficial, y **solo
  envía una fecha**.

---

## Si algo falla

| Lo que ves | Qué pasa |
|---|---|
| "No encuentro Python" | Instálalo marcando *Add Python to PATH* |
| "No encuentro 'flask'" | La consola te da el comando exacto para instalarlo |
| El navegador no se abre | Escribe a mano `http://127.0.0.1:8760` |
| "No he podido hablar con el servidor" | Se cerró la ventana de consola. Vuelve a arrancar |
| "No hay ningún Excel de pauta" | Falta subir archivos, o usa el ejemplo de práctica |
| "No hay hoja 'Julio'" | Ese Excel no tiene ese mes. Aparece en incidencias |
| "Plataforma no reconocida" | Una factura que no es de las cuatro conocidas |
| Muchas campañas **SIN PAUTA** | Faltan Excel de pauta de esos clientes |
| "No se pudo obtener la TRM" | Aparece un campo para escribir el tipo de cambio a mano |
| Los archivos pesan más de 200 MB | Súbelos por tandas |

---

## Licencia

© 2026 **Rox Solutions**. Todos los derechos reservados. Ver [LICENSE](LICENSE).

Puedes usarlo y adaptarlo dentro de tu organización, y los informes que genera son
tuyos sin restricción. No puedes revenderlo, redistribuirlo ni ofrecerlo como
servicio a terceros.

Se entrega sin garantía. Es una herramienta de apoyo para conciliar cifras: **no
sustituye la revisión contable de una persona cualificada.**
