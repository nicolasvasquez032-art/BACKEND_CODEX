# TalentMatch — Especificación Técnica del Proyecto

> Este documento es el contexto de referencia para un agente de IA (asistente de programación) que va a construir el sistema TalentMatch. Contiene el contexto del negocio, los requerimientos funcionales y no funcionales, los casos de uso, el modelo de datos y el stack tecnológico definido. Úsalo como fuente de verdad antes de generar código.

---

## 1. Contexto del proyecto

**Nombre del producto:** TalentMatch

**Problemática que resuelve:** los jóvenes y recién graduados de la región de Fusagasugá (Colombia) tienen dificultad para acceder a empleo formal. Las bolsas de empleo actuales —incluso las que ya tienen app móvil— funcionan de forma reactiva: el candidato debe buscar manualmente, y el matching se hace por coincidencia exacta de palabras clave, dejando fuera candidatos con perfiles válidos pero descritos con otros términos (habilidades transferibles, sinónimos, experiencia informal).

**Propuesta de valor:** una aplicación móvil de bolsa de empleo que usa un motor de recomendación por IA (embeddings semánticos) para conectar candidatos con vacantes según similitud de significado, no de texto exacto. El sistema explica al usuario por qué se le recomienda cada vacante, y notifica de forma proactiva (push) solo cuando la compatibilidad supera un umbral relevante.

**Diferenciador frente a competidores (LinkedIn, Computrabajo, Magneto, etc.):**
1. Matching semántico (embeddings) en vez de coincidencia por palabra exacta.
2. Explicabilidad del resultado — se muestra qué habilidades/términos coincidieron.
3. Proactividad dirigida — solo notifica cuando el score de compatibilidad es relevante, no cada vez que se publica algo nuevo.

**Sector:** Empleabilidad / Talento humano, con enfoque social en empleo juvenil.

---

## 2. Actores del sistema

| Actor | Descripción | Necesidad principal |
|---|---|---|
| **Candidato** | Joven o recién graduado que busca empleo | Encontrar vacantes compatibles con su perfil real, sin depender de coincidencia exacta de palabras |
| **Empresa / Reclutador** | Organización que publica vacantes | Reducir tiempo y ruido en el proceso de selección, recibir candidatos preseleccionados |
| **Administrador** | Municipio o universidad que supervisa la plataforma | Medir el impacto de empleabilidad en la región, moderar contenido |

---

## 3. Requerimientos funcionales

### RF-01 — Gestión de cuentas y perfil
- RF-01.1: El sistema debe permitir el registro de candidatos con correo y contraseña.
- RF-01.2: El sistema debe permitir el registro de empresas con datos de la organización.
- RF-01.3: El sistema debe permitir el inicio de sesión con JWT y manejo de sesión persistente en el dispositivo móvil.
- RF-01.4: El sistema debe permitir la recuperación de contraseña vía correo electrónico.
- RF-01.5: El candidato debe poder crear y editar su perfil: nombre, habilidades, experiencia (años), ubicación, educación.
- RF-01.6: El candidato debe poder subir su CV en formato PDF o como foto (con extracción de texto vía OCR si es imagen).
- RF-01.7: El sistema debe soportar tres roles diferenciados: candidato, empresa, administrador, cada uno con permisos distintos.

### RF-02 — Gestión de vacantes
- RF-02.1: La empresa debe poder publicar una vacante con: título, descripción, requisitos, ubicación, rango salarial.
- RF-02.2: El candidato debe poder ver el listado de vacantes activas, con filtros básicos (ubicación, categoría).
- RF-02.3: La empresa debe poder cerrar o pausar una vacante publicada.
- RF-02.4: El sistema debe generar automáticamente un embedding semántico de cada vacante al crearla o editarla.

### RF-03 — Postulaciones
- RF-03.1: El candidato debe poder postularse a una vacante con una sola acción (un toque).
- RF-03.2: El sistema debe impedir postulaciones duplicadas del mismo candidato a la misma vacante.
- RF-03.3: La empresa debe poder ver el estado de las postulaciones recibidas en un flujo tipo kanban: postulado → entrevista → rechazado/contratado.
- RF-03.4: El candidato debe poder ver el historial y estado de sus propias postulaciones.

### RF-04 — Motor de recomendación (núcleo del sistema)
- RF-04.1: El sistema debe generar un embedding semántico del perfil del candidato (a partir de su CV y habilidades declaradas).
- RF-04.2: El sistema debe calcular la similitud (distancia coseno) entre el embedding del candidato y el de cada vacante activa.
- RF-04.3: El sistema debe combinar el score semántico con filtros duros (ubicación, disponibilidad, nivel de estudios mínimo) para descartar recomendaciones inviables, aunque el score semántico sea alto.
- RF-04.4: El sistema debe mostrar al candidato una lista de vacantes recomendadas, ordenadas por score de compatibilidad.
- RF-04.5: El sistema debe explicar el resultado de cada recomendación, mostrando qué habilidades o términos coincidieron entre el perfil y la vacante.
- RF-04.6: El motor de recomendación debe ejecutarse como un microservicio independiente del backend transaccional, comunicado por API REST/HTTP.

### RF-05 — Notificaciones y geolocalización
- RF-05.1: El sistema debe enviar una notificación push (vía Firebase Cloud Messaging) al candidato cuando exista una vacante nueva cuyo score de compatibilidad supere un umbral configurable.
- RF-05.2: El sistema debe guardar el token de dispositivo de cada usuario para poder dirigir las notificaciones.
- RF-05.3: El candidato debe poder ver vacantes cercanas en un mapa (usando OpenStreetMap + Nominatim, no Google Maps, para evitar costos).
- RF-05.4: El sistema debe solicitar y gestionar el permiso de ubicación del dispositivo.
- RF-05.5: El usuario debe poder configurar qué tipos de notificaciones desea recibir.

### RF-06 — Panel administrativo
- RF-06.1: El administrador debe poder ver un dashboard web con métricas generales: total de candidatos, vacantes activas, postulaciones.
- RF-06.2: El sistema debe mostrar los sectores/categorías con mayor demanda laboral.
- RF-06.3: El sistema debe calcular y mostrar el tiempo promedio de contratación (desde postulación hasta contratación).
- RF-06.4: El sistema debe mostrar la efectividad del motor de recomendación (% de contrataciones que se originaron desde una recomendación).
- RF-06.5: El administrador debe poder moderar vacantes o perfiles reportados (aprobar/rechazar).

---

## 4. Requerimientos no funcionales (mapeados a ISO/IEC 25010)

| Característica ISO 25010 | Requisito concreto | Métrica objetivo |
|---|---|---|
| **Adecuación funcional** | El motor recomienda vacantes con score de similitud ≥ 0.6 | % de recomendaciones relevantes según validación manual (muestra de 50 casos) |
| **Eficiencia de desempeño** | Cálculo de recomendaciones en menos de 1.5 segundos para 1000 vacantes activas | Tiempo de respuesta p95, medido con k6/Locust |
| **Usabilidad** | El candidato entiende por qué se le recomienda una vacante sin explicación adicional | Encuesta SUS con 10-15 usuarios reales |
| **Fiabilidad** | El sistema debe estar disponible ≥ 99% en horario laboral | Uptime monitoreado (ej. UptimeRobot) |
| **Seguridad** | CVs y datos personales cifrados en tránsito y en reposo; acceso solo por rol (JWT) | 0 vulnerabilidades críticas en escaneo OWASP Top 10 (OWASP ZAP) |
| **Mantenibilidad** | Módulo de ML desacoplado del backend principal; cobertura de pruebas unitarias ≥ 70% | Cobertura medida con pytest + coverage.py |
| **Portabilidad** | Despliegue reproducible en cualquier entorno vía contenedores | Docker Compose funcional en menos de 10 minutos desde cero |
| **Compatibilidad** | API REST documentada con OpenAPI 3.0 para integraciones futuras | Validación automática contra especificación Swagger |

### Otros no funcionales relevantes
- El sistema debe operar bajo un modelo de costos sin dependencias de pago obligatorias (por eso se usa OpenStreetMap en vez de Google Maps, y `sentence-transformers` open-source en vez de un servicio de embeddings de pago).
- El sistema debe soportar operación con conectividad intermitente en el lado del cliente móvil (dispositivos de gama media, zonas con cobertura variable).
- El sistema debe minimizar el consumo de datos móviles y batería, evitando recalcular embeddings innecesariamente (los embeddings se almacenan, no se regeneran en cada consulta).

---

## 5. Casos de uso

### CU-01: Registrar perfil de candidato
**Actor:** Candidato
**Flujo principal:**
1. El candidato abre la app y selecciona "Registrarme".
2. Ingresa correo y contraseña.
3. Completa su perfil: nombre, ubicación, habilidades, experiencia.
4. Sube su CV (PDF o foto).
5. El sistema extrae el texto del CV y genera el embedding del perfil en segundo plano.
**Postcondición:** el candidato queda habilitado para recibir recomendaciones.

### CU-02: Publicar una vacante
**Actor:** Empresa
**Flujo principal:**
1. La empresa inicia sesión y selecciona "Publicar vacante".
2. Completa título, descripción, requisitos, ubicación, salario.
3. El sistema genera el embedding de la vacante.
4. La vacante queda visible para los candidatos y entra al cálculo de recomendaciones.

### CU-03: Recibir recomendación de vacante
**Actor:** Candidato / Sistema
**Flujo principal:**
1. El microservicio ML calcula la similitud entre el embedding del candidato y las vacantes activas.
2. El sistema combina el score semántico con los filtros duros (ubicación, disponibilidad).
3. Si el score supera el umbral configurado, el sistema dispara una notificación push vía FCM.
4. El candidato abre la notificación y ve la vacante recomendada junto con la explicación (qué habilidades coincidieron).

### CU-04: Postularse a una vacante
**Actor:** Candidato
**Flujo principal:**
1. El candidato ve el listado o una recomendación de vacante.
2. Selecciona "Postularme".
3. El sistema valida que no exista una postulación previa a la misma vacante.
4. Se crea el registro de postulación en estado "postulado".
5. La empresa ve la nueva postulación en su panel.

### CU-05: Gestionar el estado de una postulación
**Actor:** Empresa
**Flujo principal:**
1. La empresa revisa las postulaciones recibidas para una vacante.
2. Cambia el estado de una postulación: entrevista, rechazado o contratado.
3. El candidato ve reflejado el cambio de estado en su historial.

### CU-06: Consultar métricas de empleabilidad
**Actor:** Administrador
**Flujo principal:**
1. El administrador inicia sesión en el panel web.
2. Consulta el dashboard con: sectores con más demanda, tiempo promedio de contratación, efectividad del motor de recomendación.

---

## 6. Modelo de datos (resumen)

Ver diagrama entidad-relación adjunto (`TalentMatch_ER.png`) para el detalle visual completo. Entidades principales:

- **USUARIOS** (id, tipo, email, password_hash, creado_en)
- **PERFILES_CANDIDATO** (id, usuario_id FK, nombre, cv_texto, habilidades[], experiencia_anios, ubicacion, embedding vector(384))
- **VACANTES** (id, empresa_id FK, titulo, descripcion, requisitos[], ubicacion, estado, embedding vector(384), creado_en)
- **POSTULACIONES** (id, candidato_id FK, vacante_id FK, estado, score_match, fecha) — con restricción de unicidad (candidato_id, vacante_id)
- **NOTIFICACIONES** (id, usuario_id FK, tipo, mensaje, leido, creado_en)

**Relaciones:**
- USUARIOS 1:0..1 PERFILES_CANDIDATO
- USUARIOS 1:N VACANTES (como empresa)
- USUARIOS 1:N NOTIFICACIONES
- PERFILES_CANDIDATO 1:N POSTULACIONES
- VACANTES 1:N POSTULACIONES

---

## 7. Arquitectura de despliegue y stack tecnológico

> Nota: esta sección describe los servicios y tecnologías a nivel de despliegue (qué corre dónde y con qué). La organización interna de cada servicio (capas, dependencias) se define en la sección 8 — Arquitectura Hexagonal / Clean Architecture.

```
App móvil (Flutter) → Backend principal (FastAPI) → Microservicio ML (FastAPI + sentence-transformers)
                              ↓                              ↓
                       PostgreSQL + pgvector (embeddings, datos relacionales)
```

| Componente | Tecnología | Justificación |
|---|---|---|
| App móvil | **Flutter** | Un solo código base para Android e iOS, compila a nativo (buen rendimiento en listas/animaciones), respaldado por Google |
| Backend principal | **Python + FastAPI** | Asíncrono nativo, alta concurrencia, documentación OpenAPI automática |
| Microservicio ML | **Python + FastAPI + sentence-transformers** (modelo `all-MiniLM-L6-v2`) | Ecosistema más completo para IA/ML, desacoplado del backend transaccional |
| Base de datos | **PostgreSQL + extensión pgvector** | Permite manejar datos relacionales y embeddings vectoriales en un solo motor, con integridad referencial fuerte (crítico porque el dominio es relacional: candidato–postulación–vacante) |
| Notificaciones push | **Firebase Cloud Messaging (FCM)** | Estándar de industria, gratuito, cubre Android e iOS |
| Mapas / geolocalización | **OpenStreetMap + Nominatim** (paquete `flutter_map`) | Gratuito y open-source, sin riesgo de facturación por cuenta de Google Cloud |
| Autenticación | **JWT** con control de acceso por rol | Candidato, empresa, administrador |
| Infraestructura | **Docker Compose** | Reproducibilidad del entorno, portabilidad |
| CI | **GitHub Actions** | Build y test automático en cada push |
| Documentación de API | **OpenAPI / Swagger** (autogenerado por FastAPI) | Facilita integración app–backend y futuras integraciones externas |

**Nota sobre MongoDB (descartado):** se evaluó MongoDB + Atlas Vector Search como alternativa a PostgreSQL + pgvector, pero se descartó porque el dominio del negocio es fundamentalmente relacional (relaciones estrictas candidato–vacante–postulación con necesidad de integridad referencial), y MongoDB obligaría a modelar esas relaciones manualmente sin las garantías nativas que da un motor relacional.

---

## 8. Arquitectura de software: Hexagonal / Clean Architecture

El backend principal y el microservicio ML deben implementarse siguiendo **arquitectura hexagonal (puertos y adaptadores)**, alineada con los principios de Clean Architecture. El objetivo es que la lógica de negocio (dominio) no dependa de frameworks, bases de datos, ni de detalles de infraestructura — esas dependencias se invierten a través de interfaces (puertos).

### 8.1 Capas

| Capa | Responsabilidad | Ejemplos en este proyecto |
|---|---|---|
| **Dominio (Domain / Core)** | Entidades de negocio puras y reglas de negocio, sin dependencias externas | `Candidato`, `Vacante`, `Postulacion`, reglas como "no permitir postulación duplicada", "el score híbrido combina semántica + filtros duros" |
| **Aplicación (Application / Use Cases)** | Orquesta los casos de uso, coordina entidades de dominio y puertos | `RegistrarCandidato`, `PublicarVacante`, `PostularseAVacante`, `GenerarRecomendaciones`, `CambiarEstadoPostulacion` |
| **Puertos (Ports)** | Interfaces que el dominio/aplicación define y que la infraestructura implementa | `CandidatoRepositoryPort`, `VacanteRepositoryPort`, `EmbeddingServicePort`, `NotificacionPort` |
| **Adaptadores de entrada (Driving/Primary Adapters)** | Traducen una petición externa hacia un caso de uso | Controladores REST de FastAPI, handlers de la app Flutter que consumen la API |
| **Adaptadores de salida (Driven/Secondary Adapters)** | Implementan los puertos usando tecnología concreta | Repositorio PostgreSQL (SQLAlchemy) implementando `CandidatoRepositoryPort`, cliente HTTP hacia el microservicio ML implementando `EmbeddingServicePort`, cliente FCM implementando `NotificacionPort` |

### 8.2 Regla de dependencia

Las dependencias solo pueden apuntar **hacia adentro**: infraestructura → aplicación → dominio. El dominio nunca importa nada de FastAPI, SQLAlchemy, pgvector, ni de ningún framework. Si el dominio necesita persistir o consultar datos, lo hace a través de un puerto (interfaz), nunca llamando directamente a un ORM o a un cliente HTTP.

### 8.3 Estructura de carpetas sugerida (backend principal, FastAPI)

```
backend/
├── domain/
│   ├── entities/          # Candidato, Vacante, Postulacion, Notificacion
│   └── services/          # Reglas de negocio puras (ej. validar_postulacion_unica)
├── application/
│   ├── use_cases/         # RegistrarCandidato, PublicarVacante, PostularseAVacante...
│   └── ports/             # Interfaces: CandidatoRepositoryPort, EmbeddingServicePort, NotificacionPort
├── infrastructure/
│   ├── adapters/
│   │   ├── persistence/   # Implementaciones con SQLAlchemy + pgvector
│   │   ├── ml_client/     # Cliente HTTP hacia el microservicio ML (implementa EmbeddingServicePort)
│   │   └── fcm_client/    # Cliente Firebase Cloud Messaging (implementa NotificacionPort)
│   └── api/
│       ├── routers/       # Controladores FastAPI (adaptador de entrada)
│       └── schemas/       # DTOs / Pydantic models para request-response
└── main.py                 # Composición de dependencias (inyección de adaptadores en los casos de uso)
```

### 8.4 Estructura equivalente para el microservicio ML

```
ml-service/
├── domain/
│   └── entities/           # PerfilTexto, VacanteTexto, ResultadoSimilitud
├── application/
│   ├── use_cases/          # GenerarEmbedding, CalcularSimilitud, RankearRecomendaciones
│   └── ports/               # EmbeddingModelPort, VectorStorePort
├── infrastructure/
│   ├── adapters/
│   │   ├── sentence_transformers_adapter.py   # Implementa EmbeddingModelPort
│   │   └── pgvector_adapter.py                # Implementa VectorStorePort
│   └── api/
│       └── routers/          # Endpoints internos /ml/embedding, /ml/recomendaciones
└── main.py
```

### 8.5 Cómo aplica en la app Flutter

Aunque la arquitectura hexagonal nace del lado del backend, la app móvil debe reflejar el mismo espíritu de separación de capas (a veces llamado "Clean Architecture en Flutter"):

```
lib/
├── domain/         # Entidades (Candidato, Vacante) y contratos de repositorio (abstract class)
├── application/    # Casos de uso / providers-notifiers que orquestan la lógica de pantalla
├── data/           # Implementaciones concretas: cliente HTTP hacia el backend, mapeo DTO ↔ entidad
└── presentation/   # Widgets, pantallas, navegación
```

La capa `presentation` no debe llamar directamente a `http` o a Firebase — pasa siempre por `application` → `domain`, con `data` como implementación concreta de los contratos definidos en `domain`.

### 8.6 Por qué esto importa para el proyecto (para la sustentación)

- Permite cambiar de PostgreSQL a otro motor, o de `sentence-transformers` a otro proveedor de embeddings, sin tocar la lógica de negocio ni los casos de uso — solo se reemplaza el adaptador.
- Facilita las pruebas unitarias del dominio y de los casos de uso (RNF de mantenibilidad, cobertura ≥ 70%), porque se pueden usar implementaciones falsas (mocks) de los puertos sin levantar una base de datos real.
- Es coherente con la separación que ya se había definido entre backend principal y microservicio ML (sección 7) — la arquitectura hexagonal formaliza esa misma filosofía de desacoplamiento a nivel interno de cada servicio, no solo entre servicios.

---

## 9. Endpoints principales esperados (backend principal)

```
POST   /auth/registro
POST   /auth/login
POST   /auth/recuperar-password

GET    /perfiles/{id}
PUT    /perfiles/{id}
POST   /perfiles/{id}/cv

GET    /vacantes
POST   /vacantes
PUT    /vacantes/{id}
PATCH  /vacantes/{id}/estado

POST   /postulaciones
GET    /postulaciones/candidato/{candidato_id}
GET    /postulaciones/vacante/{vacante_id}
PATCH  /postulaciones/{id}/estado

GET    /recomendaciones/candidato/{candidato_id}

POST   /notificaciones/token-dispositivo
GET    /notificaciones/usuario/{usuario_id}

GET    /admin/metricas/resumen
GET    /admin/metricas/sectores-demanda
GET    /admin/metricas/tiempo-contratacion
GET    /admin/metricas/efectividad-recomendacion
```

## 10. Endpoint del microservicio ML (interno, no expuesto a la app)

```
POST   /ml/embedding/candidato   → recibe texto de perfil/CV, devuelve vector
POST   /ml/embedding/vacante     → recibe texto de vacante, devuelve vector
POST   /ml/recomendaciones       → recibe candidato_id, devuelve lista de vacantes rankeadas con score y explicación
```

---

## 11. Riesgos conocidos a mitigar en la implementación

- **Sesgo algorítmico:** el modelo de embeddings puede aprender patrones sesgados si el histórico de datos lo tiene. Mitigación: auditoría periódica de recomendaciones por grupo demográfico.
- **Cold start:** perfiles o vacantes nuevas con poco texto generan embeddings de baja calidad. Mitigación: fallback a filtros por categoría mientras se acumula información.
- **Privacidad de datos sensibles:** CVs contienen datos personales (posible edad/género inferible). Mitigación: minimización de datos almacenados, cifrado en reposo, y evitar exponer campos innecesarios en las respuestas de la API.

---

## 12. Alcance por sprint (referencia de planificación, metodología Scrum)

1. **Sprint 1:** Autenticación y perfil (registro, login, perfil, CV, recuperación de contraseña).
2. **Sprint 2:** Gestión de vacantes (publicar, listar, postular, seguimiento de estados).
3. **Sprint 3:** Motor de recomendación (embeddings, pgvector, similitud, explicabilidad, score híbrido).
4. **Sprint 4:** Notificaciones push y geolocalización (FCM, mapa, permisos).
5. **Sprint 5:** Panel administrativo (dashboard, métricas, moderación).

---

## 13. Instrucciones para el agente de IA

Al generar código para este proyecto:
- **Arquitectura obligatoria:** implementa el backend principal y el microservicio ML siguiendo estrictamente arquitectura hexagonal / Clean Architecture, según la sección 8. No coloques lógica de negocio dentro de un controlador FastAPI ni dentro de una clase de acceso a datos — esa lógica pertenece al dominio o a los casos de uso.
- **Regla de dependencia:** nunca importes SQLAlchemy, pgvector, FastAPI, `sentence-transformers`, ni ningún cliente HTTP dentro de las carpetas `domain/` o `application/`. Esas dependencias solo existen dentro de `infrastructure/`, implementando los puertos definidos en `application/ports/`.
- **Inyección de dependencias:** los casos de uso reciben los puertos por constructor (o por parámetro), nunca instancian directamente un adaptador concreto. La composición (qué adaptador concreto se usa) ocurre en el punto de entrada (`main.py` o el router de FastAPI), no dentro del caso de uso.
- Respeta la separación entre backend principal y microservicio ML — no mezcles la lógica de negocio transaccional con la lógica de generación de embeddings; ambos son servicios independientes, cada uno con su propia arquitectura hexagonal interna.
- Usa PostgreSQL con pgvector para cualquier funcionalidad que involucre embeddings; no introduzcas una base de datos NoSQL adicional.
- Todo endpoint que exponga datos personales del candidato (CV, ubicación) debe pasar por el middleware de autenticación JWT y validar el rol correspondiente.
- Al generar la lógica de recomendación, siempre combina el score semántico con los filtros duros (RF-04.3) — nunca devuelvas una recomendación que viole un filtro obligatorio (ej. ubicación incompatible) aunque el score semántico sea alto. Esta regla vive en el dominio o en el caso de uso `GenerarRecomendaciones`, no en el adaptador.
- Sigue las convenciones de nombres en español para las entidades de negocio (como aparecen en la sección 6); mantener el código en inglés es aceptable para nombres de funciones/variables internas si así se prefiere, pero sé consistente.
- Prioriza cobertura de pruebas unitarias en el dominio y en los casos de uso (motor de recomendación y manejo de postulaciones) — la arquitectura hexagonal existe precisamente para que estas pruebas no dependan de una base de datos real, usando implementaciones falsas (mocks/fakes) de los puertos.
