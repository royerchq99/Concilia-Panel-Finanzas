# Imagen del panel para desplegar en un servidor (EasyPanel, Coolify, Docker…).
# Para uso local NO hace falta: ahí se abre con abrir.bat / abrir.command.
FROM python:3.13-slim

# pdfplumber necesita estas dos para leer los PDFs.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libjpeg62-turbo zlib1g \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requisitos.txt .
RUN pip install --no-cache-dir -r requisitos.txt waitress

COPY app/ ./app/
COPY scripts/ ./scripts/
COPY marca.json ./

# Los datos van a un volumen: así sobreviven a cada despliegue.
ENV PANEL_DATOS=/datos
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:/app/app:/app/scripts
RUN mkdir -p /datos

EXPOSE 8760

# Comprobación de salud: EasyPanel reinicia el contenedor si deja de responder.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request,sys; \
      sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8760/salud',timeout=4).status==200 else 1)"

# Servidor de produccion (waitress), no el de desarrollo de Flask.
CMD ["python", "-m", "waitress", "--host=0.0.0.0", "--port=8760", \
     "--threads=6", "--call", "app.servidor:crear_app"]
