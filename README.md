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

