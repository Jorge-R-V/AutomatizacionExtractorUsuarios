# Usar una imagen oficial de Python ligera
FROM python:3.11-slim

# Evitar que Python genere archivos .pyc y forzar el log output directo
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DOCKER=1

# Instalar dependencias del sistema operativo (para Selenium y utilidades)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    # Dependencias de Chromium para Selenium en modo headless
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar los requirements primero para aprovechar la caché de Docker
COPY requirements.txt /app/

# Instalar librerías de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código de la aplicación
COPY . /app/

# Exponer el puerto 5000 para el servidor web de Flask
EXPOSE 5000

# Arrancar la aplicación Web
CMD ["python", "app.py"]
