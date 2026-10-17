# TalentMatch Backend

Backend for TalentMatch, implemented with FastAPI, PostgreSQL + pgvector, and a separate ML service.

## Architecture

Both services follow Hexagonal / Clean Architecture:

- `domain`: pure business entities and rules.
- `application`: use cases and ports.
- `infrastructure`: FastAPI routers, persistence adapters, configuration, and external clients.

The domain and application layers must not import FastAPI, SQLAlchemy, pgvector, sentence-transformers, or HTTP clients.

## Services

- `backend`: transactional API for auth, profiles, jobs, applications, notifications, and admin metrics.
- `ml_service`: internal API for embeddings and recommendations.

## Local Development

```bash
docker compose up --build
```

Backend API:

- `http://localhost:8000/docs`

ML service:

- `http://localhost:8001/docs`

## Flujo de Trabajo (Git Flow)

Este proyecto utiliza una estrategia de 3 ramas para asegurar la calidad del código:
- `desarrollo`: Rama donde se integran las nuevas funcionalidades y correcciones.
- `pre-produccion`: Rama de pruebas (staging) antes de los lanzamientos.
- `produccion`: Rama principal (equivalente a main) que contiene el código estable desplegado.

## CI/CD y Despliegue en AWS EC2

El pipeline en `.github/workflows/deploy.yml` compila y despliega automáticamente:
- **`talentmatch-backend`** (Puerto 8000)
- **`talentmatch-ml-service`** (Puerto 8001)

## Respaldos Automáticos de Base de Datos

En el directorio `scripts/` se incluyen herramientas automatizadas de mantenimiento:
- **`backup_db.sh`**: Ejecuta `pg_dump` con compresión `.sql.gz`, rotación automática de respaldos (por defecto 7 días) y soporte opcional de subida a **AWS S3**.
- **`restore_db.sh`**: Permite restaurar de forma segura un respaldo previo.
- **Cronjob diario (02:00 AM UTC):** Configurado automáticamente en el servidor EC2 durante el despliegue.
