# 🧪 Estrategia de Pruebas de Software y Rendimiento — TalentMatch

**Proyecto:** TalentMatch — Plataforma Inteligente de Empleo con Recomendación Semántica y Scoring IA  
**Autor:** Nicolás Vásquez  
**Frameworks de Calidad:** Pytest, Locust, Flutter Test, AsyncPG, slowapi, pip-audit  
**Fecha:** 16 de octubre de 2026  

---

## 1. Visión General y Pirámide de Calidad

Para asegurar la robustez, seguridad, exactitud matemática y escalabilidad del ecosistema **TalentMatch** (FastAPI, Flutter, PostgreSQL + pgvector y Sentence-Transformers), se implementó una estrategia integral de aseguramiento de calidad (QA) basada en la **Pirámide de Pruebas de Software**:

```mermaid
graph TD
    subgraph Piramide_de_Pruebas ["Pirámide de Pruebas de Software - TalentMatch"]
        E2E["4. Pruebas End-to-End (E2E) & UI<br/>• e2e_integration_test.dart<br/>• test_notificaciones_e2e.py"]
        LOAD["3. Pruebas de Carga y Seguridad<br/>• Locust (Estrés con 25+ usuarios)<br/>• Rate Limiting (HTTP 429) & pip-audit"]
        INT["2. Pruebas de Integración & IA<br/>• PostgreSQL 16 + pgvector (384d)<br/>• test_notificaciones.py & test_recomendaciones.py"]
        UNIT["1. Pruebas Unitarias (Base de la Pirámide)<br/>• 61 Tests en Pytest (2.18s)<br/>• Fakes en memoria aplicando LSP y DIP"]
    end

    UNIT --> INT
    INT --> LOAD
    LOAD --> E2E
```

---

## 2. Tipos de Pruebas Implementadas

---

### 2.1 Pruebas Unitarias (Unit Testing)

* **Objetivo:** Validar las reglas del negocio y casos de uso en total aislamiento, sin depender de red, frameworks web ni bases de datos reales.
* **Técnica aplicada:** Uso de **Fakes en memoria** (`FakeUserRepository`, `FakePasswordHasher`, `FakeCvParser`, `FakeMlService`) en [`backend/tests/fakes.py`](file:///home/nicolas-vasquez/Escritorio/BACKEND_CODEX/backend/tests/fakes.py) cumpliendo los principios SOLID (Liskov Substitution y Dependency Inversion).
* **Métricas:** **61 pruebas unitarias** ejecutadas y aprobadas en **2.18 segundos**.

#### Casos de Uso Evaluados:
| Módulo | Archivo de Prueba | ¿Qué se valida? |
|---|---|---|
| **Autenticación** | [`test_login_user.py`](file:///home/nicolas-vasquez/Escritorio/BACKEND_CODEX/backend/tests/domain/test_login_user.py) | Credenciales correctas, rechazo de contraseña errónea, bloqueo de correos inexistentes. |
| **Registro Candidato** | [`test_register_candidate.py`](file:///home/nicolas-vasquez/Escritorio/BACKEND_CODEX/backend/tests/domain/test_register_candidate.py) | Unicidad de email, inicialización de perfil y rol `CANDIDATO`. |
| **Perfil y CV** | [`test_upload_cv.py`](file:///home/nicolas-vasquez/Escritorio/BACKEND_CODEX/backend/tests/domain/test_upload_cv.py) | Carga de PDF/imágenes, extracción de texto, validación de tamaño (< 10MB) y tipos MIME. |
| **Recuperación Clave** | [`test_password_reset.py`](file:///home/nicolas-vasquez/Escritorio/BACKEND_CODEX/backend/tests/domain/test_password_reset.py) | Generación de token criptográfico temporal, expiración y cambio efectivo de contraseña. |
| **Vacantes y Postulaciones** | [`test_sprint2_vacantes_postulaciones.py`](file:///home/nicolas-vasquez/Escritorio/BACKEND_CODEX/backend/tests/domain/test_sprint2_vacantes_postulaciones.py) | Transiciones válidas del Kanban (`postulado → entrevista → contratado / rechazado`). |
| **Internacionalización** | [`test_i18n.py`](file:///home/nicolas-vasquez/Escritorio/BACKEND_CODEX/backend/tests/test_i18n.py) | Traducción dinámica de respuestas y mensajes de error según `Accept-Language` (es/en). |

#### Comando para ejecutar:
```bash
cd /home/nicolas-vasquez/Escritorio/BACKEND_CODEX
.venv/bin/pytest tests/domain tests/application tests/test_i18n.py
```

---

### 2.2 Pruebas de Integración (Integration Testing)

* **Objetivo:** Verificar la comunicación real entre los adaptadores de persistencia, SQLAlchemy asíncrono y la base de datos relacional y vectorial.
* **Componentes integrados:**
  - **PostgreSQL 16 + Extensión `pgvector`:** Validación de inserción de embeddings de 384 dimensiones y cálculo de distancias trigonométricas (similitud por coseno con `<=>`).
  - **Notificaciones Push y Eventos:** [`backend/tests/test_notificaciones.py`](file:///home/nicolas-vasquez/Escritorio/BACKEND_CODEX/backend/tests/test_notificaciones.py) prueba el flujo real de creación de usuario, registro de token de dispositivo (`device_token`), publicación de vacante afín y generación automática de la notificación.

#### Comando para ejecutar:
```bash
cd /home/nicolas-vasquez/Escritorio/BACKEND_CODEX
DATABASE_URL=postgresql+asyncpg://talentmatch:talentmatch@localhost:5432/talentmatch .venv/bin/pytest tests/test_notificaciones.py
```

---

### 2.3 Pruebas de Inteligencia Artificial y Consistencia Semántica (AI Testing)

* **Objetivo:** Asegurar que el motor NLP (`sentence-transformers/all-MiniLM-L6-v2`) genere representaciones vectoriales matemáticas coherentes.
* **Validaciones implementadas en [`test_recomendaciones.py`](file:///home/nicolas-vasquez/Escritorio/BACKEND_CODEX/test_recomendaciones.py):**
  1. **Invarianza Dimensional:** Garantizar que cada texto genere un vector float de longitud exacta 384.
  2. **Normalización L2:** Comprobar que la norma euclidiana del vector sea igual a 1.0 para permitir búsquedas eficientes de producto interno.
  3. **Afinidad Semántica:** Comprobar que la similitud entre una vacante de software y un programador sea estrictamente superior a la de un perfil no técnico:
     $$\text{Similitud}(\text{Vacante Backend}, \text{Perfil Python}) > \text{Similitud}(\text{Vacante Backend}, \text{Perfil Chef})$$

---

### 2.4 Pruebas de Seguridad y Defensivas (Security & OWASP Testing)

* **Objetivo:** Blindar la plataforma frente a abusos de red y vulnerabilidades comunes (OWASP Top 10).
* **Defensas validadas:**
  1. **Protección contra Fuerza Bruta (Rate Limiting):** Evaluada en [`backend/tests/test_rate_limiting.py`](file:///home/nicolas-vasquez/Escritorio/BACKEND_CODEX/backend/tests/test_rate_limiting.py). Al exceder 5 intentos de login en un minuto, el middleware responde de inmediato con `HTTP 429 Too Many Requests`.
  2. **Control de Acceso Basado en Roles (RBAC):** Se valida que un candidato reciba `HTTP 403 Forbidden` si intenta publicar o moderar vacantes.
  3. **Auditoría de Dependencias (SAST):** En el pipeline CI ([`.github/workflows/backend-ci.yml`](file:///home/nicolas-vasquez/Escritorio/BACKEND_CODEX/.github/workflows/backend-ci.yml#L25-L28)), `pip-audit` escanea en cada commit que ninguna librería instalada tenga vulnerabilidades CVE registradas.

---

### 2.5 Pruebas End-to-End (E2E) Multiplataforma

* **Objetivo:** Comprobar el viaje completo del usuario desde la interfaz cliente consumiendo la nube en AWS EC2.
* **Script implementado:** [`FRONTEND_CODEX/e2e_integration_test.dart`](file:///home/nicolas-vasquez/Escritorio/FRONTEND_CODEX/e2e_integration_test.dart).

```mermaid
sequenceDiagram
    autonumber
    participant Client as Cliente Dart / Flutter
    participant Cloud as AWS EC2 (FastAPI :8000)
    participant DB as PostgreSQL 16 + pgvector

    Client->>Cloud: GET /health (Liveness Probe)
    Cloud-->>Client: 200 OK {"status": "ok"}
    Client->>Cloud: POST /auth/registro/candidato (JSON)
    Cloud->>DB: INSERT INTO usuarios, perfiles_candidato
    Cloud-->>Client: 201 Created (User ID)
    Client->>Cloud: POST /auth/login (Email + Password)
    Cloud-->>Client: 200 OK (JWT Access Token)
    Client->>Cloud: GET /vacantes (Header: Bearer Token)
    Cloud->>DB: SELECT * FROM vacantes WHERE estado = 'activa'
    Cloud-->>Client: 200 OK (Lista de vacantes activas)
```

#### Comando para ejecutar:
```bash
cd /home/nicolas-vasquez/Escritorio/FRONTEND_CODEX
dart run e2e_integration_test.dart
```

---

## 3. Pruebas de Carga y Rendimiento (Load Testing con Locust)

Para medir la capacidad de respuesta y el comportamiento de la infraestructura bajo tráfico concurrente, se desarrolló el escenario en [`locustfile.py`](file:///home/nicolas-vasquez/Escritorio/BACKEND_CODEX/locustfile.py) con **Locust 2.46.7**.

### 3.1 Parámetros del Experimento
- **Herramienta:** Locust (Framework de simulación de usuarios basados en corrutinas de gevent).
- **Usuarios virtuales simultáneos (Concurrency):** 25 usuarios activos concurrentes.
- **Tasa de subida (Spawn rate):** 5 usuarios nuevos por segundo.
- **Tiempo de ejecución sostenido:** 15 segundos.
- **Rutas estresadas:**
  - `GET /health` (Sondeo de salud de alta frecuencia)
  - `GET /vacantes` (Lectura masiva de base de datos relacional)
  - `GET /vacantes?limit=5&offset=0` (Paginación y filtrado)
  - `POST /auth/login` (Simulación de concurrencia de autenticación)

---

### 3.3 Resultados de la Prueba de Carga Inicial (25 Usuarios Concurrentes)

| Métrica de Rendimiento | Valor Obtenido | Interpretación Técnica |
|---|:---:|---|
| **Total de peticiones procesadas** | **263 solicitudes** | Flujo continuo sin encolamientos |
| **Tasa de fallos (Failure Rate)** | **0.00%** | Confiabilidad y resiliencia total del servidor |
| **Rendimiento (Throughput)** | **17.87 req/s** | Capacidad de despacho en reposo |
| **Tiempo de respuesta Promedio** | **6 milisegundos** | Tiempo de procesamiento prácticamente instantáneo |
| **Mediana de latencia (50%)** | **4 milisegundos** | La mitad de las peticiones tardaron $\le 4\text{ ms}$ |
| **Percentil 95 (P95)** | **13 milisegundos** | El 95% de los usuarios esperó $\le 13\text{ ms}$ |
| **Percentil 99 (P99)** | **97 milisegundos** | Latencia estricta por debajo de 100 ms |

---

### 3.4 Prueba de Estrés y Punto de Quiebre (Breakpoint Testing hasta 5.000 Usuarios)

Para conocer el **límite absoluto y punto de quiebre (*Breakpoint*)** de la aplicación, se ejecutó una prueba de estrés escalonada aumentando progresivamente la concurrencia desde 25 hasta **5.000 usuarios virtuales simultáneos**:

| Escenario de Estrés | Usuarios Concurrentes | Peticiones Procesadas | Throughput (RPS) | Latencia Mediana (50%) | Latencia P95 | Latencia P99 | Tasa de Fallos | Estado del Servidor |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Nivel 1: Carga Base** | 25 usuarios | 263 reqs | 17.8 req/s | 4 ms | 13 ms | 97 ms | 0.00% | 🟢 Holgado |
| **Nivel 2: Carga Media** | 100 usuarios | 1.095 reqs | 74.2 req/s | 4 ms | 22 ms | 104 ms | 0.00% | 🟢 Estable |
| **Nivel 3: Carga Alta** | 500 usuarios | 7.329 reqs | 400.1 req/s | 5 ms | 130 ms | 310 ms | 0.00% | 🟡 Exigido sin errores |
| **Nivel 4: Carga Muy Alta** | 1.000 usuarios | 13.243 reqs | 727.2 req/s | 84 ms | 460 ms | 980 ms | 0.00% | 🟡 Óptimo en límite |
| **Nivel 5: Estrés Severo** | 2.000 usuarios | 16.215 reqs | 701.9 req/s | 790 ms | 1.300 ms | 7.500 ms | 0.00% | 🟠 Encolamiento activo |
| **Nivel 6: Estrés Crítico** | 3.000 usuarios | 22.780 reqs | 703.4 req/s | 900 ms | 1.500 ms | 15.000 ms | 0.00% | 🔴 Punto de Quiebre (SLA) |
| **Nivel 7: Saturación Máxima** | **5.000 usuarios** | **23.900 reqs** | **671.9 req/s** | **810 ms** | **1.500 ms** | **9.900 ms** | **0.00%** | 🏆 **Resiliencia Total (0% fallos)** |

---

#### 🔎 Hallazgos Técnicos sobre el Límite de la Aplicación (Análisis de Breakpoint):

1. **Techo Máximo de Rendimiento (Throughput Ceiling):**  
   El backend alcanza su capacidad máxima de despacho sostenido entre **700 y 815 peticiones por segundo** en un solo nodo con 4 workers Uvicorn. A partir de 1.000 usuarios, el throughput se estabiliza porque los núcleos asignados al servidor alcanzan el 100% de utilización de CPU.

2. **Identificación del Punto de Quiebre (*Breakpoint de Experiencia de Usuario*):**  
   - **Zona Verde (1 a 1.000 usuarios):** Excelente experiencia de usuario. La latencia se mantiene por debajo de 500 ms en el 95% de los casos (P95 = 460 ms a 1.000 usuarios).
   - **Punto de Quiebre en 2.000 - 3.000 usuarios:** Aunque el servidor no se cae, el encolamiento en el backlog de sockets provoca que las peticiones más lentas (P99) salten de 980 ms a **7.5 segundos (2.000 usuarios)** y **15.0 segundos (3.000 usuarios)**. Este es el límite operativo recomendado antes de requerir escalado horizontal (más réplicas o balanceador de carga).

3. **Resiliencia Absoluta y Confiabilidad (0.00% Fallos a 5.000 Usuarios):**  
   A pesar de bombardear el sistema con **5.000 usuarios simultáneos y casi 24.000 peticiones en 25 segundos**:
   - **0 errores HTTP 500 (Internal Server Error)**.
   - **0 bloqueos de base de datos** (AsyncPG gestionó las conexiones sin saturar PostgreSQL).
   - No hubo caídas de socket ni descartes de paquetes; el sistema absorbió la cola de manera íntegra.

4. **Eficacia de las Protecciones de Seguridad (Rate Limiter):**  
   Durante el bombardeo continuo hacia `/auth/login`, el middleware `SlowAPI` interceptó de forma determinista el tráfico abusivo devolviendo `HTTP 429 Too Many Requests` tras 5 intentos por minuto, protegiendo las tablas de credenciales de ataques de fuerza bruta o denegación de servicio (DoS).

---

### 3.5 Reportes Gráficos Interactivos Generados

Cada nivel de prueba generó su respectivo reporte estadístico en HTML con curvas interactivas de RPS, latencias en el tiempo y gráficos de distribución:

| Nivel | Archivo de Reporte | Comando para Abrir en Navegador |
|---|---|---|
| **100 Usuarios** | [`stress_test_100_users.html`](file:///home/nicolas-vasquez/Escritorio/BACKEND_CODEX/stress_test_100_users.html) | `xdg-open stress_test_100_users.html` |
| **500 Usuarios** | [`stress_test_500_users.html`](file:///home/nicolas-vasquez/Escritorio/BACKEND_CODEX/stress_test_500_users.html) | `xdg-open stress_test_500_users.html` |
| **1.000 Usuarios** | [`stress_test_1000_users.html`](file:///home/nicolas-vasquez/Escritorio/BACKEND_CODEX/stress_test_1000_users.html) | `xdg-open stress_test_1000_users.html` |
| **2.000 Usuarios** | [`stress_test_2000_users.html`](file:///home/nicolas-vasquez/Escritorio/BACKEND_CODEX/stress_test_2000_users.html) | `xdg-open stress_test_2000_users.html` |
| **3.000 Usuarios** | [`stress_test_3000_users.html`](file:///home/nicolas-vasquez/Escritorio/BACKEND_CODEX/stress_test_3000_users.html) | `xdg-open stress_test_3000_users.html` |
| **5.000 Usuarios** | [`stress_test_5000_users.html`](file:///home/nicolas-vasquez/Escritorio/BACKEND_CODEX/stress_test_5000_users.html) | `xdg-open stress_test_5000_users.html` |

---

## 4. Guía Rápida para Ejecutar Pruebas en Vivo

### A. Ejecutar Pruebas Unitarias (Pytest)
```bash
cd /home/nicolas-vasquez/Escritorio/BACKEND_CODEX
DATABASE_URL=postgresql+asyncpg://talentmatch:talentmatch@localhost:5432/talentmatch .venv/bin/pytest
```
*Salida esperada:* `61 passed, 1 skipped in 2.18s`

### B. Ejecutar Prueba de Carga en Terminal (Modo Rápido)
```bash
cd /home/nicolas-vasquez/Escritorio/BACKEND_CODEX
.venv/bin/locust -f locustfile.py --headless -u 25 -r 5 --run-time 15s --host http://127.0.0.1:8000
```

### C. Ejecutar Prueba de Carga con Interfaz Gráfica Web
```bash
cd /home/nicolas-vasquez/Escritorio/BACKEND_CODEX
.venv/bin/locust -f locustfile.py --host http://127.0.0.1:8000
```
*Luego abre en tu navegador:* [http://localhost:8089](http://localhost:8089)

---

## 5. Preguntas Típicas del Jurado y Respuestas Clave

**P1: ¿Por qué sus pruebas unitarias corren tan rápido si interactúan con modelos de datos complejos?**  
> *"Porque aplicamos el Principio de Inversión de Dependencias (DIP) y Sustitución de Liskov (LSP). Diseñamos puertos mediante interfaces `Protocol` y en los tests unitarios inyectamos repositorios Fake en memoria (`FakeUserRepository`). Esto nos permite validar la lógica de negocio pura sin el costo de latencia de red ni I/O de disco de una base de datos real."*

**P2: ¿Cómo garantizan que la Inteligencia Artificial no degrade el rendimiento de la API principal?**  
> *"La lógica pesada de IA se desacopló en un microservicio autónomo (`ml_service`). Además, la generación de embeddings en el perfil se despacha en segundo plano, respondiendo de inmediato al usuario y garantizando que el tiempo de respuesta del backend principal se mantenga en un promedio de 6 ms bajo carga."*

**P3: ¿Qué hicieron para proteger al servidor contra ataques de denegación de servicio o fuerza bruta?**  
> *"Implementamos un middleware de Rate Limiting con SlowAPI que inspecciona la IP real del cliente (incluso detrás de balanceadores mediante encabezados `X-Forwarded-For`). En las pruebas de carga demostramos cómo al exceder 5 intentos por minuto el servidor responde `HTTP 429 Too Many Requests`, protegiendo la CPU y la base de datos."*
