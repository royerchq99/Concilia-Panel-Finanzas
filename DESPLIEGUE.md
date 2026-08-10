# Poner Concilia en internet

Guía para dejarlo funcionando en un **VPS con EasyPanel**, con tu dominio y HTTPS.

Si solo quieres usarlo en tu ordenador, **no necesitas nada de esto**: doble clic en
`abrir.bat` y listo.

---

## Antes de empezar: lo que tienes que saber

**El panel comparte una sola carpeta de archivos.** No tiene cuentas de usuario: todo
el que entre con la contraseña ve los mismos archivos y los mismos resultados.

Eso está bien para **una persona o un equipo que trabaja junto**. No sirve para dar
acceso a varios clientes distintos por la misma dirección: el segundo vería las
facturas del primero.

**La solución con EasyPanel es fácil:** una instancia por cliente. Se duplica el
servicio, se le pone otro subdominio y otra contraseña, y quedan aislados de verdad
porque cada uno tiene su propio volumen.

| Un servicio por… | Dirección | Aislamiento |
|---|---|---|
| Tú | `concilia.app.tudominio.com` | — |
| Cliente A | `clientea.tudominio.com` | Volumen propio |
| Cliente B | `clienteb.tudominio.com` | Volumen propio |

Y lo otro que conviene tener claro: **si el panel vive en tu servidor, las facturas de
tus clientes pasan a estar bajo tu custodia.** Eso son obligaciones de protección de
datos reales. Cuando cada uno lo tiene en su ordenador, no las tienes.

---

## Paso 1 · El DNS en Porkbun

Necesitas la **IP de tu VPS** (te la da Hostinger en el panel del servidor).

En Porkbun: tu dominio → **DNS** → añade un registro por cada subdominio:

| Type | Host | Answer | TTL |
|---|---|---|---|
| `A` | `concilia.app` | la IP de tu VPS | 600 |

Eso crea `concilia.app.tudominio.com`. Repite con otro host (`clientea.app`,
`clienteb.app`…) para
cada instancia.

Si quieres usar el dominio a secas (`tudominio.com`), el Host va vacío o con `@`.

**El DNS tarda.** Normalmente unos minutos, a veces un par de horas. Comprueba desde
tu ordenador:

```bash
nslookup concilia.app.tudominio.com
```

Cuando responda con la IP de tu VPS, sigue. **No conectes el dominio en EasyPanel
antes de eso**: el certificado HTTPS fallará y tendrás que reintentarlo.

---

## Paso 2 · Crear el servicio en EasyPanel

1. Entra en EasyPanel y crea un **Project** (o usa uno que tengas).
2. Dentro, **+ Service → App**. Ponle un nombre: `concilia`.

### Source

| Campo | Valor |
|---|---|
| Tipo | **GitHub** |
| Owner / Repo | `royerchq99/Concilia-Panel-Finanzas` |
| Branch | `main` |
| Build path | `/` |

El repositorio es público, así que no hace falta conectar credenciales de GitHub.

### Build

Elige **Dockerfile**. El archivo ya está en el repositorio y EasyPanel lo detecta
solo. No toques nada más aquí.

### Environment

Añade estas variables:

```
PANEL_CLAVE=pon-aqui-una-contrasena-larga
PANEL_USUARIO=Marbel
PANEL_DATOS=/datos
```

| Variable | Para qué |
|---|---|
| `PANEL_CLAVE` | **La contraseña de entrada.** Obligatoria: sin ella el panel **no arranca** en modo servidor. Que sea larga y que no la uses en otro sitio |
| `PANEL_USUARIO` | El nombre de usuario. **Opcional**: si lo dejas fuera, solo se comprueba la contraseña y el usuario da igual |
| `PANEL_DATOS` | Dónde viven los archivos. Tiene que coincidir con el volumen |

Las mayúsculas del usuario **no importan**: `Marbel`, `marbel` o `MARBEL` valen
igual. La contraseña sí distingue mayúsculas.

> **El panel se niega a arrancar sin `PANEL_CLAVE`.** Si te la dejas, verás en los
> logs `NO ARRANCO SIN CONTRASEÑA` y el contenedor no levantará. Es a propósito:
> antes bastaba olvidar esa variable para dejar las facturas abiertas a internet.

### Volumes

Esto es lo que hace que **los archivos no se borren en cada despliegue**:

| Type | Name | Mount path |
|---|---|---|
| Volume | `datos` | `/datos` |

### Domains

Añade tu dominio:

| Campo | Valor |
|---|---|
| Host | `concilia.app.tudominio.com` |
| Port | `8760` |
| HTTPS | **activado** |

El puerto **8760** es el que expone el contenedor. Si pones otro, no funcionará.

EasyPanel pide el certificado a Let's Encrypt solo, en cuanto el DNS apunte bien.

### Deploy

Pulsa **Deploy** y mira los logs. La primera construcción tarda unos minutos porque
descarga Python y las librerías.

---

## Paso 3 · Comprobar que funciona

En orden, y sin saltarte ninguno:

```bash
# 1. ¿El contenedor responde? (esto NO pide contraseña, es la comprobación de salud)
curl https://concilia.app.tudominio.com/salud
# Tiene que devolver: {"estado":"ok"}

# 2. ¿La contraseña protege de verdad?
curl -i https://concilia.app.tudominio.com/ | head -1
# Tiene que devolver: HTTP/2 401

# 3. ¿Entra con usuario y contraseña?
curl -u Marbel:TU_CONTRASENA https://concilia.app.tudominio.com/api/estado
# Tiene que devolver un JSON con los meses

# 4. ¿Rechaza a un usuario que no es?
curl -o /dev/null -s -w "%{http_code}
" -u otro:TU_CONTRASENA https://concilia.app.tudominio.com/
# Tiene que devolver: 401
```

Si los tres pasan, abre `https://concilia.app.tudominio.com` en el navegador, mete la
contraseña, pulsa **"Usar el ejemplo de práctica"** y luego **Conciliar**. Tienen que
salir 6 que cuadran, 2 con desviación, 2 sin factura y 2 sin pauta.

### Si el paso 1 falla

Mira los logs del servicio en EasyPanel:

| Lo que ves en los logs | Qué pasa |
|---|---|
| `NO ARRANCO SIN CONTRASEÑA` | Falta la variable `PANEL_CLAVE`. Añádela y vuelve a desplegar |
| `ModuleNotFoundError` | La construcción no terminó bien. Vuelve a desplegar |
| El contenedor se reinicia solo | La comprobación de salud falla. Comprueba que el puerto del dominio es `8760` |
| `Address already in use` | Otro servicio usa ese puerto en el mismo proyecto |
| Certificado HTTPS fallido | El DNS todavía no apuntaba. Espera y vuelve a pedirlo en EasyPanel |

---

## Paso 4 · Una instancia por cliente

Para cada cliente, repite el Paso 2 cambiando tres cosas:

1. **Nombre del servicio**: `concilia-clientea`
2. **`PANEL_CLAVE`** y **`PANEL_USUARIO`**: distintos para cada cliente
3. **Domains**: `clientea.tudominio.com` (y su registro `A` en Porkbun)

El volumen se crea nuevo y separado. Cada cliente tiene sus archivos y sus
resultados, sin verse entre ellos.

---

## Actualizar el panel

Cuando cambie algo en el repositorio, en EasyPanel pulsas **Deploy** otra vez. Los
datos del volumen no se tocan.

Si activas **Auto Deploy** en el servicio, se actualiza solo con cada `push` a `main`.

---

## Qué NO lleva esta versión

Está aquí para que nadie se lleve una sorpresa:

- **No hay cuentas de usuario de verdad.** Un usuario y una contraseña compartidos por instancia, no una cuenta por persona.
- **No hay histórico.** Cada cierre pisa al anterior del mismo mes.
- **No hay copias de seguridad automáticas.** El volumen vive en tu VPS: si quieres
  respaldo, configúralo en Hostinger.
- **No borra los archivos subidos solo.** Se quedan en el volumen hasta que pulses
  *Vaciar*. Si son de un cliente, acuérdate de vaciarlo al terminar el mes.

---

## Nota sobre esta guía

El `Dockerfile` está escrito y revisado, y el modo servidor —el servidor de
producción, el volumen, la contraseña y la comprobación de salud— **está probado y
funcionando**.

Lo que no se pudo probar en el equipo donde se construyó es la **construcción de la
imagen**, porque esa red intercepta las conexiones seguras y `pip` no puede descargar
dentro del contenedor. En un VPS normal eso no pasa. Por eso el Paso 3 empieza
comprobando `/salud`: si responde, la imagen se construyó bien.
