# ==============================================================================
# Dockerfile - Backend API (TalentMatch)
# Framework: FastAPI / Python 3.12 Slim
# Buenas prácticas: Optimización de capas, sin caché de pip, variables de entorno
# ==============================================================================

# Imagen base oficial y ligera
FROM python:3.12-slim

# Metadatos del contenedor
LABEL maintainer="Equipo TalentMatch"
LABEL description="Contenedor Backend API REST - TalentMatch"
LABEL version="1.0"

# Variables de entorno para ejecución óptima de Python en contenedores
# PYTHONDONTWRITEBYTECODE: Evita escribir archivos .pyc en disco
# PYTHONUNBUFFERED: Asegura que los logs se emitan inmediatamente a stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Capa de dependencias: se copian y compilan primero para aprovechar el caché de Docker
COPY requirements.lock pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.lock \
    && pip install --no-cache-dir --no-deps .

# Copiar el código fuente completo de la aplicación
COPY . .

# Variables de puerto y concurrencia configurables (Factores VII y VIII)
ENV PORT=8000 \
    WORKERS=1

# Comando por defecto para iniciar el servidor con soporte para escalamiento de procesos
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WORKERS:-1}"]
