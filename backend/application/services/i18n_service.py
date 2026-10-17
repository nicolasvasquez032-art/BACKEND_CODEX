"""Servicio de internacionalización (I18n) para TalentMatch.

Proporciona traducción reactiva y normalización de idioma basada en el encabezado
HTTP Accept-Language para vacantes, recomendaciones IA y mensajes de error.
"""

from __future__ import annotations

import re
from typing import Any


class I18nService:
    # ── Mapeos de Categorías (ES -> EN) ──────────────────────────────────────
    CATEGORIES_ES_TO_EN: dict[str, str] = {
        "Ingeniería de Software": "Software Engineering",
        "Tecnología": "Technology",
        "Datos": "Data",
        "Diseño": "Design",
        "Infraestructura": "Infrastructure",
        "Desarrollo": "Development",
        "Ventas": "Sales",
        "Marketing": "Marketing",
        "Finanzas": "Finance",
        "Recursos Humanos": "Human Resources",
        "Operaciones": "Operations",
        "Ciberseguridad": "Cybersecurity",
        "Producto": "Product",
        "Gestión": "Management",
        "Soporte": "Technical Support",
        "Legal": "Legal",
        "Salud": "Healthcare",
        "Educación": "Education",
        "Administración": "Administration",
        "Atención al Cliente": "Customer Service",
        "Inteligencia Artificial": "Artificial Intelligence",
        "Sin categoría": "Uncategorized",
    }

    # ── Mapeos de Títulos (ES -> EN) ─────────────────────────────────────────
    TITLES_ES_TO_EN: dict[str, str] = {
        "Ingeniero de Inteligencia Artificial": "Artificial Intelligence Engineer",
        "Desarrollador Flutter Senior": "Senior Flutter Developer",
        "Especialista Cloud AWS": "AWS Cloud Specialist",
        "Diseñador UI/UX": "UI/UX Designer",
        "Data Scientist Jr": "Junior Data Scientist",
        "Empresas de tecnología y startups": "Tech & Startups Software Engineer",
        "Desarrollador Backend": "Backend Developer",
        "Desarrollador Frontend": "Frontend Developer",
        "Desarrollador Full Stack": "Full Stack Developer",
        "Desarrollador Fullstack": "Full Stack Developer",
        "Desarrollador Móvil": "Mobile Developer",
        "Ingeniero de Software": "Software Engineer",
        "Ingeniero de Datos": "Data Engineer",
        "Ingeniero DevOps": "DevOps Engineer",
        "Arquitecto Cloud": "Cloud Architect",
        "Arquitecto de Software": "Software Architect",
        "Líder Técnico": "Tech Lead",
        "Gerente de Producto": "Product Manager",
        "Gerente de Proyecto": "Project Manager",
        "Analista de Datos": "Data Analyst",
        "Analista de Ciberseguridad": "Cybersecurity Analyst",
        "Ingeniero de QA / Testing": "QA / Testing Engineer",
        "Desarrollador Web": "Web Developer",
        "Administrador de Sistemas": "Systems Administrator",
        "Soporte Técnico": "Technical Support",
    }

    # ── Mapeos de Descripciones Conocidas ────────────────────────────────────
    DESCRIPTIONS_ES_TO_EN: dict[str, str] = {
        "Diseña motores de búsqueda y Match usando Sentence-Transformers para emparejar empresas con candidatos en tiempo récord.": (
            "Design search and Match engines using Sentence-Transformers to pair companies with candidates in record time."
        ),
        "Únete para liderar el equipo móvil de TalentMatch. Buscamos experto en animaciones, Haptic Feedback y Riverpod.": (
            "Join us to lead TalentMatch's mobile team. We are looking for an expert in animations, Haptic Feedback, and Riverpod."
        ),
        "Mantenimiento de instancias EC2, arquitecturas escalables y soporte en crisis cuando los servidores se quedan sin memoria.": (
            "Maintenance of EC2 instances, scalable architectures, and incident support when servers run out of memory."
        ),
        "Asegúrate de que nuestra aplicación genere un WOW en los usuarios con diseños fluidos y estéticos.": (
            "Ensure our application generates a WOW effect for users with fluid and aesthetic designs."
        ),
        "Analiza las interacciones de los usuarios y mejora los embeddings de nuestra plataforma de reclutamiento.": (
            "Analyze user interactions and improve the embeddings of our recruitment platform."
        ),
        "Descripción del trabajo: Buscamos un desarrollador de software para formar parte de un equipo dinámico enfocado en la creación y mejora de soluciones tecnológicas innovadoras. La persona seleccionada participará en el diseño, desarrollo, pruebas y mantenimiento de aplicaciones web y móviles, trabajando en conjunto con otros desarrolladores y áreas de la empresa.": (
            "Job Description: We are looking for a software developer to join a dynamic team focused on creating and improving innovative technology solutions. The selected person will participate in the design, development, testing, and maintenance of web and mobile applications, collaborating with fellow developers and company departments."
        ),
        "Buscamos un desarrollador experto en Python y bases de datos para unirse a nuestro equipo. El candidato ideal tiene experiencia con Fastapi.": (
            "We are looking for an expert Python and database developer to join our team. The ideal candidate has experience with FastAPI."
        ),
        "Buscamos desarrollador Frontend con experiencia en diseño de interfaces y componentes.": (
            "We are looking for a Frontend developer with experience in interface and component design."
        ),
    }

    # ── Mapeos de Requisitos Conocidos ───────────────────────────────────────
    REQUIREMENTS_ES_TO_EN: dict[str, str] = {
        "Conocimientos en Java, Python, JavaScript o Dart. Manejo de bases de datos SQL y NoSQL. Conocimiento": (
            "Knowledge of Java, Python, JavaScript, or Dart. SQL and NoSQL database management."
        ),
        "Diseño Centrado en el Usuario": "User-Centered Design",
        "Trabajo en equipo": "Teamwork",
        "Resolución de problemas": "Problem solving",
        "Comunicación asertiva": "Effective communication",
        "Liderazgo": "Leadership",
        "Pensamiento crítico": "Critical thinking",
        "Proactivo": "Proactive",
        "Proactiva": "Proactive",
        "Disponibilidad inmediata": "Immediate availability",
        "Nivel de inglés avanzado": "Advanced English level",
        "Nivel de inglés intermedio": "Intermediate English level",
        "Nivel de inglés conversacional": "Conversational English",
        "Experiencia de 4+ años": "4+ years of experience",
        "Experiencia de 2 años": "2 years of experience",
        "Experiencia de 3 años": "3 years of experience",
        "Experiencia de 5 años": "5 years of experience",
    }

    # ── Mapeos de Errores y Notificaciones ───────────────────────────────────
    ERRORS_ES_TO_EN: dict[str, str] = {
        "Vacante no encontrada": "Job vacancy not found",
        "Acceso denegado": "Access denied",
        "Error al guardar la vacante": "Error saving job vacancy",
        "Error al actualizar la vacante": "Error updating job vacancy",
        "Error al cambiar el estado": "Error changing status",
        "Error al eliminar la vacante": "Error deleting job vacancy",
        "Perfil no encontrado": "Profile not found",
        "Perfil de candidato no encontrado para el usuario autenticado": (
            "Candidate profile not found for authenticated user"
        ),
        "Solo los candidatos pueden editar perfiles": "Only candidates can edit profiles",
        "Solo los candidatos pueden subir su CV": "Only candidates can upload their CV",
        "El archivo excede el límite de 5MB.": "File exceeds 5MB limit.",
        "Error al guardar el CV": "Error saving CV",
        "Error al guardar los cambios": "Error saving changes",
        "Postulación no encontrada": "Application not found",
        "Ya existe una postulación para esta vacante": "An application already exists for this vacancy",
        "Error al guardar la postulación": "Error saving application",
        "Solo el candidato dueño puede retirar esta postulación": (
            "Only the applicant can withdraw this application"
        ),
        "No autorizado para ver estas notificaciones": "Not authorized to view these notifications",
        "No se pudo validar las credenciales": "Could not validate credentials",
        "No tienes permisos para realizar esta acción": "You do not have permission to perform this action",
        "Token inválido o expirado": "Invalid or expired token",
        "Error al actualizar el estado": "Error updating status",
        "Ha ocurrido un error interno en el servidor. El equipo técnico ha sido notificado.": (
            "An internal server error occurred. The technical team has been notified."
        ),
        "El servicio de pagos no está configurado. Contacta al administrador.": (
            "Payment service is not configured. Please contact the administrator."
        ),
        "Demasiados intentos. Por favor, espera un momento antes de reintentar.": (
            "Too many requests. Please wait a moment before trying again."
        ),
    }

    @classmethod
    def parse_accept_language(cls, header: str | None) -> str:
        """Determina el idioma preferido ('es' o 'en') a partir de un header Accept-Language.

        Ejemplos:
          'en-US,en;q=0.9,es;q=0.8' -> 'en'
          'es-CO,es;q=0.9,en;q=0.8' -> 'es'
          'en'                      -> 'en'
          None                      -> 'es'
        """
        if not header or not header.strip():
            return "es"

        try:
            # Separar y evaluar ponderaciones (q-values)
            locales: list[tuple[str, float]] = []
            for item in header.split(","):
                part = item.strip()
                if not part:
                    continue
                if ";q=" in part:
                    lang_tag, q_str = part.split(";q=", 1)
                    try:
                        q_val = float(q_str.strip())
                    except ValueError:
                        q_val = 1.0
                else:
                    lang_tag = part
                    q_val = 1.0

                lang_tag = lang_tag.strip().lower()
                locales.append((lang_tag, q_val))

            if not locales:
                return "es"

            # Ordenar por prioridad q de mayor a menor
            locales.sort(key=lambda x: x[1], reverse=True)
            top_lang = locales[0][0]

            if top_lang.startswith("en"):
                return "en"
            return "es"
        except Exception:
            return "es"

    @classmethod
    def is_english(cls, lang: str | None) -> bool:
        """Retorna True si el idioma solicitado o el header es inglés."""
        if not lang:
            return False
        # Si es un header completo o un código de idioma
        if "," in lang or ";q=" in lang:
            return cls.parse_accept_language(lang) == "en"
        return lang.strip().lower().startswith("en")

    @classmethod
    def translate_category(cls, category: str | None, lang: str | None = None) -> str | None:
        """Traduce una categoría si el idioma solicitado es inglés."""
        if not category or not cls.is_english(lang):
            return category

        trimmed = category.strip()
        if trimmed in cls.CATEGORIES_ES_TO_EN:
            return cls.CATEGORIES_ES_TO_EN[trimmed]

        for k, v in cls.CATEGORIES_ES_TO_EN.items():
            if k.lower() == trimmed.lower():
                return v

        return category

    @classmethod
    def translate_title(cls, title: str, lang: str | None = None) -> str:
        """Traduce el título de una vacante si el idioma solicitado es inglés."""
        if not title or not cls.is_english(lang):
            return title

        trimmed = title.strip()
        if trimmed in cls.TITLES_ES_TO_EN:
            return cls.TITLES_ES_TO_EN[trimmed]

        for k, v in cls.TITLES_ES_TO_EN.items():
            if k.lower() == trimmed.lower():
                return v

        # Transformaciones heurísticas por expresiones regulares
        res = title
        res = re.sub(r"\bIngeniero(a)? de Inteligencia Artificial\b", "AI Engineer", res, flags=re.IGNORECASE)
        res = re.sub(r"\bDesarrollador(a)? de Software\b", "Software Developer", res, flags=re.IGNORECASE)
        res = re.sub(r"\bDesarrollador(a)?\b", "Developer", res, flags=re.IGNORECASE)
        res = re.sub(r"\bIngeniero(a)? de\b", "Engineer -", res, flags=re.IGNORECASE)
        res = re.sub(r"\bIngeniero(a)?\b", "Engineer", res, flags=re.IGNORECASE)
        res = re.sub(r"\bDiseñador(a)?\b", "Designer", res, flags=re.IGNORECASE)
        res = re.sub(r"\bEspecialista en\b", "Specialist in", res, flags=re.IGNORECASE)
        res = re.sub(r"\bEspecialista\b", "Specialist", res, flags=re.IGNORECASE)
        res = re.sub(r"\bGerente de\b", "Manager of", res, flags=re.IGNORECASE)
        res = re.sub(r"\bLíder de\b", "Lead of", res, flags=re.IGNORECASE)
        res = re.sub(r"\bAnalista de\b", "Analyst of", res, flags=re.IGNORECASE)
        return res

    @classmethod
    def translate_description(cls, description: str, lang: str | None = None) -> str:
        """Traduce la descripción de una vacante si el idioma solicitado es inglés."""
        if not description or not cls.is_english(lang):
            return description

        trimmed = description.strip()
        if trimmed in cls.DESCRIPTIONS_ES_TO_EN:
            return cls.DESCRIPTIONS_ES_TO_EN[trimmed]

        for k, v in cls.DESCRIPTIONS_ES_TO_EN.items():
            if k.lower() == trimmed.lower():
                return v

        res = description
        res = res.replace("Descripción del trabajo:", "Job Description:")
        res = res.replace("Buscamos un desarrollador de software para formar parte de un equipo dinámico", "We are looking for a software developer to join a dynamic team")
        res = res.replace("Buscamos un desarrollador experto en", "We are looking for an expert developer in")
        res = res.replace("Buscamos un desarrollador", "We are looking for a developer")
        res = res.replace("Buscamos desarrollador", "We are looking for a developer")
        res = res.replace("Buscamos ", "We are looking for ")
        res = res.replace("Únete para liderar", "Join us to lead")
        res = res.replace("Únete a nuestro equipo", "Join our team")
        res = res.replace("en tiempo récord", "in record time")
        res = res.replace("bases de datos", "databases")
        res = res.replace("aplicaciones web y móviles", "web and mobile applications")
        res = res.replace("trabajando en conjunto con", "working alongside")
        res = res.replace("para unirse a nuestro equipo", "to join our team")
        return res

    @classmethod
    def translate_requirements(cls, requirements: list[str], lang: str | None = None) -> list[str]:
        """Traduce la lista de requisitos si el idioma solicitado es inglés."""
        if not requirements or not cls.is_english(lang):
            return requirements

        result: list[str] = []
        for req in requirements:
            trimmed = req.strip()
            if trimmed in cls.REQUIREMENTS_ES_TO_EN:
                result.append(cls.REQUIREMENTS_ES_TO_EN[trimmed])
                continue

            # "Experiencia de X años"
            exp_match = re.match(r"^Experiencia de (\d+)\+? años?$", trimmed, re.IGNORECASE)
            if exp_match:
                result.append(f"{exp_match.group(1)}+ years of experience")
                continue

            # "Conocimientos en X"
            if trimmed.lower().startswith("conocimientos en "):
                result.append(f"Knowledge of {trimmed[17:]}")
                continue

            # "Manejo de X"
            if trimmed.lower().startswith("manejo de "):
                result.append(f"Proficiency in {trimmed[10:]}")
                continue

            result.append(req)

        return result

    @classmethod
    def translate_location(cls, location: str, lang: str | None = None) -> str:
        """Traduce la modalidad/ubicación si el idioma solicitado es inglés."""
        if not location or not cls.is_english(lang):
            return location

        trimmed = location.strip()
        lowered = trimmed.lower()
        if lowered == "remoto":
            return "Remote"
        if lowered in ("híbrido", "hibrido"):
            return "Hybrid"
        if lowered in ("presencial", "en sitio"):
            return "On-site"

        res = location
        res = res.replace("Medellín, Antioquia", "Medellin, Colombia")
        res = res.replace("Bogotá, Colombia", "Bogota, Colombia")
        res = res.replace("Cali, Valle del Cauca", "Cali, Colombia")
        res = res.replace("Barranquilla, Atlántico", "Barranquilla, Colombia")
        res = res.replace("Bucaramanga, Santander", "Bucaramanga, Colombia")
        res = res.replace("Fusagasugá, Cundinamarca", "Fusagasuga, Colombia")
        return res

    @classmethod
    def translate_recommendation_explanation(cls, explanation: str, lang: str | None = None) -> str:
        """Traduce las explicaciones del algoritmo de recomendación de IA."""
        if not explanation or not cls.is_english(lang):
            return explanation

        res = explanation
        if res.startswith("Habilidades coincidentes:"):
            res = res.replace("Habilidades coincidentes:", "Matching skills:", 1)
        if "Alta compatibilidad con tu perfil" in res:
            res = res.replace("Alta compatibilidad con tu perfil", "High match with your profile")
        if "Coincidencia semántica con" in res:
            res = res.replace("Coincidencia semántica con", "Semantic match with")
        if "Fuerte afinidad semántica con tus habilidades" in res:
            res = res.replace("Fuerte afinidad semántica con tus habilidades", "Strong semantic match with your skills")
        if "Perfil recomendado por afinidad técnica en IA y ML" in res:
            res = res.replace(
                "Perfil recomendado por afinidad técnica en IA y ML",
                "Recommended profile based on technical affinity in AI & ML",
            )

        return res

    @classmethod
    def translate_error(cls, detail: str, lang: str | None = None) -> str:
        """Traduce un mensaje de error o excepción hacia inglés si es solicitado."""
        if not detail or not cls.is_english(lang):
            return detail

        # Búsqueda exacta
        trimmed = detail.strip()
        if trimmed in cls.ERRORS_ES_TO_EN:
            return cls.ERRORS_ES_TO_EN[trimmed]

        for es_msg, en_msg in cls.ERRORS_ES_TO_EN.items():
            if es_msg.lower() in trimmed.lower():
                return trimmed.replace(es_msg, en_msg)

        return detail

    @classmethod
    def translate_vacante_fields(
        cls,
        titulo: str,
        descripcion: str,
        requisitos: list[str],
        ubicacion: str,
        categoria: str | None,
        lang: str | None = None,
    ) -> dict[str, Any]:
        """Traduce de forma unificada los campos localizables de una vacante."""
        if not cls.is_english(lang):
            return {
                "titulo": titulo,
                "descripcion": descripcion,
                "requisitos": requisitos,
                "ubicacion": ubicacion,
                "categoria": categoria,
            }

        return {
            "titulo": cls.translate_title(titulo, lang),
            "descripcion": cls.translate_description(descripcion, lang),
            "requisitos": cls.translate_requirements(requisitos, lang),
            "ubicacion": cls.translate_location(ubicacion, lang),
            "categoria": cls.translate_category(categoria, lang),
        }
