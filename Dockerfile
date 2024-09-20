# Usa una imagen base de Python
FROM python:3.9-slim

# Instalar las dependencias del sistema necesarias para OpenCV y ZBar
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    zbar-tools \
    libzbar0

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia los archivos y carpetas necesarios al contenedor
COPY ./app /app/app
COPY ./temp /app/temp
COPY ./main.py /app/main.py

# Instala las dependencias de Python (si tienes un archivo requirements.txt)
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Exponer el puerto en el que correrá la aplicación (por defecto FastAPI corre en el puerto 80)
EXPOSE 80

# Comando para ejecutar la aplicación (ajusta según tu aplicación)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
