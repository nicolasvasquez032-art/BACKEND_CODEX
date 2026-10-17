# ==============================================================================
# Dockerfile - ML Service (TalentMatch)
# Microservicio de Inteligencia Artificial y Embeddings Semánticos
# Framework: FastAPI / Sentence-Transformers / Python 3.12 Slim
# ==============================================================================

# Imagen base oficial y ligera
FROM python:3.12-slim

# Metadatos del contenedor
LABEL maintainer="Equipo TalentMatch"
LABEL description="Microservicio de Recomendación y Embeddings ML - TalentMatch"
LABEL version="1.0"

# Variables de entorno para ejecución óptima de Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Capa de dependencias: aisladas y fijadas con requirements.lock (Factor II)
COPY requirements.lock pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.lock \
    && pip install --no-cache-dir --no-deps .

# Pre-descarga de pesos del modelo NLP en la imagen para arranque instantáneo (Factor IX: Disposability)
ENV EMBEDDING_MODEL_NAME="sentence-transformers/all-MiniLM-L6-v2"
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Copiar el código fuente del microservicio
COPY . .

# Exponer los puertos del microservicio (8000 por defecto, 8001 para producción)
EXPOSE 8000
EXPOSE 8001

# Variable de puerto y concurrencia configurables (Factores VII y VIII)
ENV PORT=8000 \
    WORKERS=1

# Comando de ejecución con Uvicorn
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WORKERS:-1}"]
