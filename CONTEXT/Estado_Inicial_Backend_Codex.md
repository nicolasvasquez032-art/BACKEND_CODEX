# Estado inicial del backend TalentMatch

Este archivo resume lo que se construyó en el primer arranque del backend para que un nuevo chat de Codex pueda retomar el trabajo sin perder contexto.

## Qué se hizo

- Se inicializó el repositorio local `BACKEND_CODEX`.
- Se configuró el remoto:
  - `https://github.com/nicolasvasquez032-art/BACKEND_CODEX.git`
- Se creó el commit local:
  - `12779ac Initial backend architecture`
- Se dejó una base inicial de backend siguiendo la especificación principal:
  - `CONTEXT/TalentMatch_Especificacion_Agente_IA (1).md`

## Decisiones técnicas tomadas

- Se usó arquitectura Hexagonal / Clean Architecture.
- Se eligieron nombres Python-friendly:
  - `backend/`
  - `ml_service/`
- Los puertos/interfaces usan nombres técnicos en inglés por convención.
- Las entidades y nombres de negocio se mantienen alineados con el dominio de TalentMatch.
- El backend principal y el servicio ML están separados desde el inicio.

## Estructura creada

```text
BACKEND_CODEX/
├── backend/
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   ├── alembic/
│   ├── tests/
│   └── main.py
├── ml_service/
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   └── main.py
├── docker-compose.yml
├── README.md
└── .github/workflows/backend-ci.yml
```

## Funcionalidad incluida

- Backend FastAPI inicial.
- Endpoints base:
  - `GET /health`
  - `POST /auth/registro/candidato`
  - `POST /auth/registro/empresa`
  - `POST /auth/login`
- Entidades iniciales:
  - `User`
  - `CandidateProfile`
- Casos de uso iniciales:
  - registrar candidato
  - registrar empresa
  - login
- Puertos iniciales:
  - repositorio de usuarios
  - hasher de contraseñas
  - servicio de tokens
- Adaptadores iniciales:
  - SQLAlchemy para persistencia
  - Passlib/bcrypt para contraseñas
  - JWT con `python-jose`
- Migración Alembic inicial para:
  - `usuarios`
  - `perfiles_candidato`
- Esqueleto de `ml_service` con endpoints internos de embeddings:
  - `POST /ml/embedding/candidato`
  - `POST /ml/embedding/vacante`
- Docker Compose con:
  - PostgreSQL + pgvector
  - backend
  - ml_service

## Verificaciones realizadas

- Se compiló la sintaxis de `backend/` y `ml_service/` correctamente usando el Python empaquetado de Codex.
- Se verificó que `domain/` y `application/` no importan FastAPI, SQLAlchemy, sentence-transformers ni clientes externos.
- No se ejecutaron tests con `pytest` porque el entorno Windows actual no tiene `pytest` instalado.

## Cómo retomar

En Ubuntu, después de clonar el repositorio:

```bash
git clone https://github.com/nicolasvasquez032-art/BACKEND_CODEX.git
cd BACKEND_CODEX
```

El nuevo chat de Codex debe leer primero:

1. `CONTEXT/TalentMatch_Especificacion_Agente_IA (1).md`
2. `CONTEXT/Estado_Inicial_Backend_Codex.md`
3. `README.md`

Siguiente objetivo recomendado:

1. Instalar dependencias o levantar con Docker.
2. Validar `docker compose up --build`.
3. Ejecutar migraciones Alembic.
4. Correr `pytest`.
5. Continuar Sprint 1 con perfiles, carga de CV y recuperación de contraseña.

