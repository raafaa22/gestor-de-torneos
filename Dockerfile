# Imagen base con Python 3.12
FROM python:3.12-slim

# Config Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo
WORKDIR /app

# Dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential pkg-config default-libmysqlclient-dev gettext \
    && rm -rf /var/lib/apt/lists/*

# Instalar requirements primero (mejor cache)
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copiamos el resto del código (aunque durante desarrollo montaremos un volumen)
COPY . /app/

# Comando por defecto: migrar y levantar server
CMD sh -c "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"
