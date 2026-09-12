# Sprint 1 — TalentMatch Backend (continuación)

## Objetivo

Completar el Sprint 1 de la especificación: **Autenticación y Perfil**.  
Lo que ya existe cubre registro y login. Lo que **falta** es:

1. **Recuperación de contraseña** vía correo (RF-01.4)
2. **Editar perfil del candidato** (RF-01.5) — `PUT /perfiles/{id}`
3. **Subir CV** — PDF con extracción de texto y foto/imagen con OCR (RF-01.6) — `POST /perfiles/{id}/cv`
4. **Leer perfil** — `GET /perfiles/{id}`
5. **Tests unitarios** del dominio y casos de uso (RNF mantenibilidad ≥ 70%)

---

## Lo que ya existe (no se toca)

| Archivo | Estado |
|---|---|
| `domain/entities/user.py` | ✅ Completo |
| `domain/entities/candidate_profile.py` | ✅ Completo |
| `domain/exceptions.py` | ✅ Completo (se extiende) |
| `application/ports/user_repository.py` | ✅ Completo (se extiende) |
| `application/ports/password_hasher.py` | ✅ Completo |
| `application/ports/token_service.py` | ✅ Completo |
| `application/use_cases/register_candidate.py` | ✅ Completo |
| `application/use_cases/register_company.py` | ✅ Completo |
| `application/use_cases/login_user.py` | ✅ Completo |
| `infrastructure/adapters/persistence/models.py` | ✅ Completo (se extiende) |
| `infrastructure/adapters/persistence/user_repository.py` | ✅ Completo (se extiende) |
| `infrastructure/api/routers/auth.py` | ✅ Completo |
| `infrastructure/api/schemas/auth.py` | ✅ Completo |
| `infrastructure/config.py` | ✅ Completo (se extiende) |

---

## Cambios propuestos

---

### 1. Dominio — Excepciones nuevas

#### [MODIFY] [`exceptions.py`](file:///c:/Users/Nicol/OneDrive/Desktop/TALENTMATCH/BACKEND_CODEX/backend/domain/exceptions.py)
- Añadir: `ProfileNotFoundError`, `UserNotFoundError`, `CVProcessingError`

---

### 2. Dominio — Entidad `PasswordResetToken`

#### [NEW] [`domain/entities/password_reset_token.py`](file:///c:/Users/Nicol/OneDrive/Desktop/TALENTMATCH/BACKEND_CODEX/backend/domain/entities/password_reset_token.py)
- Entidad pura con: `id`, `user_id`, `token_hash`, `expires_at`, `used`

---

### 3. Aplicación — Nuevos puertos

#### [NEW] [`application/ports/email_service.py`](file:///c:/Users/Nicol/OneDrive/Desktop/TALENTMATCH/BACKEND_CODEX/backend/application/ports/email_service.py)
- `EmailServicePort`: protocolo con `send_password_reset(to_email, reset_link)`

#### [NEW] [`application/ports/cv_parser.py`](file:///c:/Users/Nicol/OneDrive/Desktop/TALENTMATCH/BACKEND_CODEX/backend/application/ports/cv_parser.py)
- `CvParserPort`: protocolo con `extract_text(file_bytes, mime_type) -> str`

#### [MODIFY] [`application/ports/user_repository.py`](file:///c:/Users/Nicol/OneDrive/Desktop/TALENTMATCH/BACKEND_CODEX/backend/application/ports/user_repository.py)
- Añadir métodos: `update_candidate_profile(...)`, `update_cv_text(profile_id, cv_text)`, `get_candidate_profile_by_id(...)`
- Añadir: `create_password_reset_token(...)`, `find_password_reset_token(token_hash)`, `mark_token_used(token_id)`, `update_user_password(...)`

---

### 4. Aplicación — Nuevos casos de uso

#### [NEW] [`application/use_cases/request_password_reset.py`](file:///c:/Users/Nicol/OneDrive/Desktop/TALENTMATCH/BACKEND_CODEX/backend/application/use_cases/request_password_reset.py)
- Genera token seguro, lo guarda hasheado (SHA-256), envía el link por correo vía `EmailServicePort`

#### [NEW] [`application/use_cases/confirm_password_reset.py`](file:///c:/Users/Nicol/OneDrive/Desktop/TALENTMATCH/BACKEND_CODEX/backend/application/use_cases/confirm_password_reset.py)
- Valida el token (existe, no expirado, no usado), hashea la nueva contraseña, actualiza el usuario, marca el token como usado

#### [NEW] [`application/use_cases/update_candidate_profile.py`](file:///c:/Users/Nicol/OneDrive/Desktop/TALENTMATCH/BACKEND_CODEX/backend/application/use_cases/update_candidate_profile.py)
- Solo el dueño del perfil (candidato autenticado) puede editar su propio perfil

#### [NEW] [`application/use_cases/upload_cv.py`](file:///c:/Users/Nicol/OneDrive/Desktop/TALENTMATCH/BACKEND_CODEX/backend/application/use_cases/upload_cv.py)
- Recibe bytes del archivo + mime type, delega extracción a `CvParserPort`, guarda el texto resultante en el perfil

#### [NEW] [`application/use_cases/get_candidate_profile.py`](file:///c:/Users/Nicol/OneDrive/Desktop/TALENTMATCH/BACKEND_CODEX/backend/application/use_cases/get_candidate_profile.py)
- Busca perfil por `profile_id` o `user_id`

---

### 5. Infraestructura — Modelo de BD nuevo

#### [MODIFY] [`infrastructure/adapters/persistence/models.py`](file:///c:/Users/Nicol/OneDrive/Desktop/TALENTMATCH/BACKEND_CODEX/backend/infrastructure/adapters/persistence/models.py)
- Añadir `PasswordResetTokenModel` (tabla `password_reset_tokens`)

#### [MODIFY] [`infrastructure/adapters/persistence/user_repository.py`](file:///c:/Users/Nicol/OneDrive/Desktop/TALENTMATCH/BACKEND_CODEX/backend/infrastructure/adapters/persistence/user_repository.py)
- Implementar los métodos nuevos del puerto

---

### 6. Infraestructura — Adaptadores nuevos

#### [NEW] `infrastructure/adapters/email/` — Adaptador de email
- `smtp_email_service.py`: implementa `EmailServicePort` con `aiosmtplib` (SMTP async)
- Configurable con variables de entorno: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM`

#### [NEW] `infrastructure/adapters/cv_parser/` — Adaptador de parseo de CV
- `pdf_parser.py`: usa `pdfplumber` para extraer texto de PDF
- `ocr_parser.py`: usa `pytesseract` + `Pillow` para extraer texto de imagen (JPG/PNG)
- `composite_parser.py`: selecciona el parser correcto según el mime type

---

### 7. Infraestructura — API

#### [NEW] [`infrastructure/api/routers/profiles.py`](file:///c:/Users/Nicol/OneDrive/Desktop/TALENTMATCH/BACKEND_CODEX/backend/infrastructure/api/routers/profiles.py)
- `GET /perfiles/{profile_id}` — requiere JWT (candidato dueño o empresa o admin)
- `PUT /perfiles/{profile_id}` — requiere JWT candidato dueño
- `POST /perfiles/{profile_id}/cv` — requiere JWT candidato dueño, acepta `multipart/form-data`

#### [MODIFY] [`infrastructure/api/routers/auth.py`](file:///c:/Users/Nicol/OneDrive/Desktop/TALENTMATCH/BACKEND_CODEX/backend/infrastructure/api/routers/auth.py)
- Añadir: `POST /auth/recuperar-password` (solicitar reset)
- Añadir: `POST /auth/confirmar-reset` (confirmar con token + nueva contraseña)

#### [NEW] `infrastructure/api/schemas/profiles.py`
- `ProfileUpdateRequest`, `ProfileResponse`, `CVUploadResponse`

#### [MODIFY] [`infrastructure/api/dependencies.py`](file:///c:/Users/Nicol/OneDrive/Desktop/TALENTMATCH/BACKEND_CODEX/backend/infrastructure/api/dependencies.py)
- Añadir dependencia `get_current_user` que valida JWT y devuelve el `User` autenticado

#### [MODIFY] [`infrastructure/config.py`](file:///c:/Users/Nicol/OneDrive/Desktop/TALENTMATCH/BACKEND_CODEX/backend/infrastructure/config.py)
- Añadir campos: `smtp_host`, `smtp_port`, `smtp_user`, `smtp_password`, `email_from`, `frontend_url` (para el link de reset)

---

### 8. Migración Alembic

#### [NEW] `alembic/versions/0002_add_password_reset_tokens.py`
- Crea la tabla `password_reset_tokens`

---

### 9. Tests unitarios

#### [NEW] `tests/domain/` — Tests de dominio puro (sin BD, sin frameworks)
- `test_register_candidate.py` — mock del repositorio y hasher
- `test_login_user.py` — mock del repositorio, hasher y token service
- `test_request_password_reset.py` — mock del repositorio y email service
- `test_confirm_password_reset.py` — mock del repositorio y hasher
- `test_update_candidate_profile.py` — mock del repositorio
- `test_upload_cv.py` — mock del repositorio y cv parser

---

## Dependencias a añadir en `pyproject.toml`

```toml
aiosmtplib = ">=3.0"      # SMTP async para emails
pdfplumber = ">=0.11"     # Extracción de texto de PDF
pytesseract = ">=0.3"     # OCR para imágenes
Pillow = ">=10.0"         # Soporte de imágenes para pytesseract
python-multipart = ">=0.0.9"  # Soporte multipart/form-data en FastAPI
```

> **Nota:** `pytesseract` requiere que Tesseract OCR esté instalado en el sistema operativo del servidor (incluido en el Dockerfile).

---

## Plan de verificación

- Los tests unitarios corren con `pytest` **sin base de datos** (usan fakes/mocks de los puertos).
- La sintaxis de todos los archivos nuevos se verifica con `python -m py_compile`.
- Los imports se validan: `domain/` y `application/` no importan FastAPI, SQLAlchemy, etc.
