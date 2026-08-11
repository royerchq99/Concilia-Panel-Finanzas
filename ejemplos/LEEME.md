# El ejemplo de práctica

**Todo lo que hay aquí es inventado.** La agencia, los clientes, las campañas y los
importes no existen. Sirve para probar el kit sin tocar datos reales.

## Cómo se usa

```bash
python scripts/conciliar.py --mes Julio --anio 2026 --ejemplo
python scripts/verificar.py --mes Julio --anio 2026 --ejemplo
```

O simplemente dile al asistente: **"prueba con el ejemplo"**.

Corre primero **Junio** y después **Julio** (el Excel de pauta trae las dos
hojas) si quieres ver también la comparación con el mes anterior, la
tendencia de varios meses y el acumulado del año — con un solo mes esas tres
secciones no salen (no hay nada con qué comparar todavía, y eso también es
correcto: no se inventa una tendencia con un solo punto).

## Qué hay dentro

**`pautas/`** — dos clientes inventados, con hojas de Junio y Julio:

- `Nvo - VELARIA - 2026.xlsx` — 6 campañas en julio. Cabecera en la **fila 7**.
- `Nvo - NORTA - 2026.xlsx` — 4 campañas en julio. Cabecera en la **fila 5**.

Que las cabeceras estén en filas distintas es a propósito: los archivos reales
también varían, y el kit tiene que localizarlas buscando la celda `Campaña1`, no por
posición.

**`facturas/`** — ocho PDFs que imitan los formatos reales de cada plataforma.

## Los 17 errores plantados

El ejemplo está preparado para comprobar que el kit los encuentra. Si al ejecutarlo
no salen estos números, algo se ha roto.

### Diferencias de facturación (3)

| Campaña | Consumido | Facturado | Qué pasa |
|---|---:|---:|---|
| `nor-grado_2026-pre-gdn-cpc` | 940.000 | 1.010.000 | Le cobran **7,4 % de más** |
| `nor-posgrado_2026-pos-tiktok-cpm` | 681.500 | 655.000 | Le cobran **3,9 % de menos** |
| `vel-becas_2026-pre-tiktok-cpc` | 620.000 | 1.240.000 | **Posible factura duplicada** (ver abajo) — el aviso tiene que marcarla |

### Campañas sin pareja (4)

| Campaña | Estado esperado | Por qué |
|---|---|---|
| `vel-abierto_2026-pre-meta-cpl` | SIN FACTURA | Está en la pauta y no aparece en ningún PDF |
| `nor-posgrado_2026-pos-search-cpc` | SIN FACTURA | Pausada, sin consumido y sin factura |
| `nor-fantasma_2026-pre-search-cpc` | SIN PAUTA | Facturada en Google sin estar en ninguna pauta |
| `vel-eventos_2026-pre-meta-cpl` | SIN PAUTA | Facturada en Meta sin estar en ninguna pauta |

### Los dos huecos a propósito (2)

Son la prueba de que el kit **no rellena lo que falta**:

| Campaña | Qué falta | Qué tiene que hacer el kit |
|---|---|---|
| `vel-becas_2026-pre-tiktok-cpc` | el presupuesto planeado | Ejecución `SIN DATOS`. **No** poner un cero |
| `nor-posgrado_2026-pos-search-cpc` | el consumido | Ejecución `SIN DATOS` y no calcular desviación |

### Desviaciones de ejecución (2)

| Campaña | Planeado | Consumido | Estado esperado |
|---|---:|---:|---|
| `vel-exec_2026-pos-linkedin-cpl` | 1.200.000 | 1.455.000 | POR ENCIMA DEL PLAN (+21 %) |
| `vel-master_2026-pos-demandgen-cpc` | 2.000.000 | 1.750.000 | POR DEBAJO DEL PLAN (−12,5 %) |

### Trampas de lectura (6)

Estas no se ven en el resultado: se ven en que el resultado **sale bien a pesar de
ellas**.

1. **Nombres con las letras separadas** en la factura de Google
   (`v e l -ma s te r_ 2 0 2 6…`), como hace el PDF real. Hay que reconstruirlos.
2. **Nombres partidos en varias líneas** dentro de la tabla de TikTok, y la tabla
   dividida en dos trozos donde el segundo **no repite la cabecera**.
3. **Una campaña que aparece dos veces** en la misma factura de Google
   (`vel-master_2026-pos-search-cpc`, con 3.980.000 y 500). Hay que sumarlas: la
   pauta dice 3.980.500 y solo cuadra si se suman.
4. **Un PDF duplicado exacto** (`9900112233 (1).pdf`). Si se cuenta dos veces, el
   total se dispara.
5. **Una factura de una plataforma desconocida** (`PR-2026-4417 Publired.pdf`). El
   kit tiene que decirlo en incidencias, **no** forzarla con un lector que no es.
6. **Una factura en dólares** (LinkedIn, USD 465). Hay que convertirla con la TRM
   oficial y dejar dicho en el informe qué cambio se aplicó.
7. **Dos PDFs DISTINTOS** (`MUUS20260099887…pdf` y `MUUS20260099888…pdf`, distinto
   número de factura y distintos bytes) que facturan la misma campaña
   (`vel-becas_2026-pre-tiktok-cpc`) por el **mismo importe exacto**: 620.000. No es
   el mismo caso que el punto 4 (ahí es una copia byte a byte del mismo archivo).
   Aquí son archivos genuinamente distintos que coinciden en campaña + importe —
   el kit no los descarta solo, los suma (por eso sale como diferencia de
   facturación) y además los marca en la sección "Posibles facturas duplicadas"
   del informe para que alguien lo revise.

Y además, dentro de los Excel hay filas de **SUBTOTAL, IVA MEDIO y GRAN TOTAL**
mezcladas con los datos, como en los archivos reales. Si no se descartan, los
totales salen duplicados.

## El resultado correcto

Con estos datos, el cierre de **Julio 2026** tiene que dar exactamente:

```
12 campañas. Facturación:
   CUADRA                         5
   DESVIACION EN FACTURACION      3
   SIN FACTURA                    2
   SIN PAUTA                      2
Ejecución frente al plan:
   EN PLAN                        3
   POR DEBAJO DEL PLAN            4
   POR ENCIMA DEL PLAN            1
   SIN DATOS                      4

3 incidencias
```

Y en el informe, la sección **"Posibles facturas duplicadas"** tiene que listar
exactamente una campaña: `vel-becas_2026-pre-tiktok-cpc`.

Y `verificar.py` tiene que pasar todas sus comprobaciones.

## Volver a generarlo

Si quieres rehacer el ejemplo desde cero:

```bash
python scripts/generar_ejemplo.py
```
