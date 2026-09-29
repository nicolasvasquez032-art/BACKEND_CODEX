# Lógica de Negocio — TalentMatch Backend

Este documento resume la estructura y la lógica de negocio del Backend (FastAPI), la cual está construida utilizando los principios de **Clean Architecture** (Arquitectura Limpia).

## 1. Capa de Dominio (`backend/domain/entities/`)
El dominio contiene las reglas de negocio puras, sin depender de bases de datos, frameworks o HTTP. Aquí se definen los modelos de datos principales (Entidades) y sus estados válidos.

- **`user.py`**: Representa a un usuario del sistema (Candidato, Empresa o Admin). Maneja la lógica de validación de roles.
- **`candidate_profile.py`**: Perfil del candidato (habilidades, educación, experiencia). Incluye el texto extraído del CV.
- **`vacante.py`**: Representa una oferta de trabajo. Define los estados posibles mediante `VacanteEstado` (Activa, Pausada, Cerrada, Bloqueada) y contiene el vector de similitud (embedding) generado por el motor de IA.
- **`postulacion.py`**: Relación entre un candidato y una vacante. Define `PostulacionEstado` (Postulado, Entrevista, Rechazado, Contratado) y el porcentaje de compatibilidad (Score Match).
- **`notificacion.py`**: Entidad para el sistema de alertas (Firebase Cloud Messaging).
- **`password_reset_token.py`**: Manejo seguro de recuperación de cuentas.

## 2. Capa de Casos de Uso (`backend/application/use_cases/`)
Aquí residen los **Use Cases** (Casos de Uso), los cuales orquestan el comportamiento de la aplicación, ejecutando validaciones y llamando a los repositorios (BD). Están divididos por funcionalidad:

### 🔐 Autenticación y Cuentas
- `register_candidate.py` / `register_company.py`: Validan datos, encriptan la contraseña y crean usuarios/perfiles.
- `login_user.py`: Verifica credenciales y genera tokens JWT.
- `request_password_reset.py` / `confirm_password_reset.py`: Flujo de reseteo seguro de contraseña.

### 💼 Vacantes (Ofertas de Trabajo)
- `publicar_vacante.py`: Crea una nueva vacante (solo para rol EMPRESA).
- `actualizar_vacante.py`: Modifica una vacante (valida que el usuario sea el dueño).
- `cambiar_estado_vacante.py`: Permite a la empresa pausar o cerrar vacantes.
- `listar_vacantes.py`: Obtiene el listado de vacantes activas con filtros (ubicación, categoría).
- `moderar_vacante.py`: Lógica para administradores (permite bloquear vacantes indebidas).

### 📝 Postulaciones
- `postularse_a_vacante.py`: Registra que un candidato se postuló. Valida que la vacante esté activa y que no se haya postulado antes. Invoca el motor de IA para calcular el `score_match` inicial.
- `listar_postulaciones.py`: Historial de aplicaciones de un candidato o de aplicantes para una empresa.
- `cambiar_estado_postulacion.py`: Permite a la empresa avanzar al candidato (ej. a Entrevista o Contratado).

### 👤 Perfil y Currículum (CV)
- `update_candidate_profile.py` / `get_candidate_profile.py`: Gestión del perfil público del candidato.
- `upload_cv.py`: Extrae texto del PDF (usando servicios externos o librerías) y lo asocia al perfil del candidato para facilitar las búsquedas semánticas.

### 🤖 Inteligencia Artificial (Microservicio ML)
- `get_recomendaciones.py`: Orquesta la comunicación con el microservicio de IA para obtener vacantes que hagan un *match* perfecto con el perfil y CV del candidato.

### 🔔 Notificaciones
- `register_device_token.py`: Guarda el token de FCM del dispositivo.
- `get_notificaciones.py` / `mark_notificacion_read.py`: Historial de notificaciones in-app.

## Reglas de Arquitectura
1. **El Dominio es Rey**: `domain` no importa nada de `application`, `infrastructure` o `interfaces`.
2. **Los Casos de Uso Orquestan**: `use_cases` importan `domain` e interfaces de repositorios, pero no saben si se usa PostgreSQL o MongoDB.
3. **Inyección de Dependencias**: La capa de `infrastructure` (SQLAlchemy, FastAPI) inyecta las implementaciones de base de datos dentro de los casos de uso.
