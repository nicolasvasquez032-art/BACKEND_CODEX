"""Servicio de generación de explicaciones contextuales de IA para recomendaciones laborales.

Analiza de forma semántica el perfil profesional del candidato (CV extraído,
habilidades estructuradas, titular y formación) en contraste con los requisitos,
descripción y responsabilidades de la vacante para formular una justificación
precisa y específica de por qué se recomienda la posición.
"""

from __future__ import annotations

import re
from typing import Any


class AiExplainerService:
    # Catálogo de tecnologías clave y sus expresiones regulares de detección
    TECH_CATALOG: list[tuple[str, str, str]] = [
        # (Etiqueta ES, Etiqueta EN, regex)
        ("Python", "Python", r"\bpython\b"),
        ("FastAPI", "FastAPI", r"\bfastapi\b"),
        ("Django", "Django", r"\bdjango\b"),
        ("Flask", "Flask", r"\bflask\b"),
        ("Java", "Java", r"\bjava\b"),
        ("Spring Boot", "Spring Boot", r"\bspring\b"),
        ("Dart/Flutter", "Dart/Flutter", r"\b(dart|flutter)\b"),
        ("JavaScript", "JavaScript", r"\bjavascript\b"),
        ("TypeScript", "TypeScript", r"\btypescript\b"),
        ("C#/.NET", "C#/.NET", r"\b(c#|\.net)\b"),
        ("Next.js", "Next.js", r"\bnext\.?js\b"),
        ("Angular", "Angular", r"\bangular\b"),
        ("React", "React", r"\breact\b"),
        ("bases de datos SQL y NoSQL", "SQL & NoSQL databases", r"\b(sql|nosql|postgresql|mongodb|mysql)\b"),
        ("Docker", "Docker", r"\bdocker\b"),
        ("Redis", "Redis", r"\bredis\b"),
        ("AWS", "AWS", r"\b(aws|ec2|cloud)\b"),
        ("Linux", "Linux", r"\blinux\b"),
        ("Git", "Git", r"\bgit\b"),
        ("Sentence-Transformers", "Sentence-Transformers", r"\bsentence[- ]transformers\b"),
        ("Inteligencia Artificial", "Artificial Intelligence & ML", r"\b(inteligencia artificial|machine learning|ia|pytorch|tensorflow)\b"),
        ("UI/UX & Figma", "UI/UX Design & Figma", r"\b(ui/ux|figma|diseño)\b"),
        ("Clean Architecture", "Clean Architecture", r"\bclean architecture\b"),
        ("APIs RESTful", "RESTful APIs", r"\b(apis? rest(ful)?|rest)\b"),
    ]

    @classmethod
    def generate_explanation(
        cls,
        perfil: Any,
        vacante: Any,
        score: float,
        lang: str | None = None,
    ) -> str:
        """Genera una explicación detallada y contextualizada del match de IA."""
        is_en = bool(lang and lang.strip().lower().startswith("en"))
        pct = round(score * 100)

        # 1. Extraer y preparar textos del candidato
        cand_cv = getattr(perfil, "cv_text", "") or ""
        cand_skills = getattr(perfil, "skills", []) or []
        cand_job_title = getattr(perfil, "job_title", "") or ""
        cand_about = getattr(perfil, "about_me", "") or ""
        cand_edu = getattr(perfil, "education", "") or ""

        cand_full = f"{cand_job_title} {' '.join(cand_skills)} {cand_about} {cand_edu} {cand_cv}".lower()

        # 2. Extraer y preparar textos de la vacante
        vac_titulo = getattr(vacante, "titulo", "") or ""
        vac_desc = getattr(vacante, "descripcion", "") or ""
        vac_reqs = getattr(vacante, "requisitos", []) or []
        vac_full = f"{vac_titulo} {vac_desc} {' '.join(vac_reqs)}".lower()

        # 3. Identificar Rol del candidato
        role_es = None
        role_en = None
        if cand_job_title.strip():
            role_es = cand_job_title.strip()
            role_en = cand_job_title.strip()
        elif "full stack" in cand_full:
            role_es = "Desarrollador Full Stack"
            role_en = "Full Stack Developer"
        elif "backend" in cand_full:
            role_es = "Desarrollador Backend"
            role_en = "Backend Developer"
        elif "frontend" in cand_full:
            role_es = "Desarrollador Frontend"
            role_en = "Frontend Developer"
        elif "flutter" in cand_full or "móvil" in cand_full or "movil" in cand_full:
            role_es = "Desarrollador Móvil"
            role_en = "Mobile Developer"
        elif "inteligencia artificial" in cand_full or "ia aplicada" in cand_full:
            role_es = "Especialista en IA"
            role_en = "AI Specialist"
        elif "ingenier" in cand_full:
            role_es = "Ingeniero de Sistemas"
            role_en = "Systems Engineer"

        # 4. Detectar tecnologías y habilidades coincidentes
        matched_es: list[str] = []
        matched_en: list[str] = []
        for label_es, label_en, pattern in cls.TECH_CATALOG:
            in_cand = bool(re.search(pattern, cand_full, re.IGNORECASE))
            in_vac = bool(re.search(pattern, vac_full, re.IGNORECASE))
            if in_cand and in_vac:
                if label_es not in matched_es:
                    matched_es.append(label_es)
                if label_en not in matched_en:
                    matched_en.append(label_en)

        # 5. Detectar dominio o enfoque funcional de la vacante
        domain_es = None
        domain_en = None
        if re.search(r"aplicaciones web y m[oó]viles|web y m[oó]vil", vac_full):
            domain_es = "el desarrollo de soluciones web y móviles"
            domain_en = "web and mobile solutions development"
        elif re.search(r"inteligencia artificial|motores de b[uú]squeda|match|sentence", vac_full):
            domain_es = "la ingeniería de inteligencia artificial y motores de matching"
            domain_en = "artificial intelligence engineering and matching engines"
        elif re.search(r"data scientist|datos|embeddings|interacciones", vac_full):
            domain_es = "el análisis de datos y optimización de modelos"
            domain_en = "data analysis and model optimization"
        elif re.search(r"cloud|aws|ec2|infraestructura|servidores", vac_full):
            domain_es = "la infraestructura en la nube y alta disponibilidad"
            domain_en = "cloud infrastructure and high availability"
        elif re.search(r"flutter|m[oó]vil|animaciones|riverpod", vac_full):
            domain_es = "el desarrollo avanzado en el ecosistema móvil"
            domain_en = "advanced mobile ecosystem development"
        elif re.search(r"ui/ux|figma|dise[ñn]o", vac_full):
            domain_es = "el diseño de experiencias de usuario (UI/UX) y producto digital"
            domain_en = "UI/UX user experience and digital product design"
        elif re.search(r"backend|fastapi|python|spring", vac_full):
            domain_es = "el desarrollo de servicios backend y APIs escalables"
            domain_en = "scalable backend services and API development"

        # Formatear lista de tecnologías gramaticalmente
        def _format_list(items: list[str], is_english: bool) -> str:
            if not items:
                return ""
            if len(items) == 1:
                return items[0]
            if is_english:
                return ", ".join(items[:-1]) + ", and " + items[-1]
            last = items[-1]
            conj = " e " if last.lower().startswith("i") or last.lower().startswith("hi") else " y "
            return ", ".join(items[:-1]) + conj + last

        # 6. Construcción de la justificación
        if is_en:
            techs_str = _format_list(matched_en[:4], is_english=True)
            parts = [f"Recommended with {pct}% match:"]
            if role_en and domain_en and techs_str:
                parts.append(
                    f"Your background as a {role_en} directly matches {domain_en} required for this role, supported by your experience in {techs_str}."
                )
            elif techs_str and domain_en:
                parts.append(
                    f"Your proficiency in {techs_str} directly meets the requirements for {domain_en} in this position."
                )
            elif techs_str:
                parts.append(
                    f"Your skills in {techs_str} strongly align with the technical requirements of this role."
                )
            elif domain_en:
                parts.append(
                    f"Your background and technical expertise align well with {domain_en} sought in this position."
                )
            else:
                parts.append(
                    "Your professional profile and verified background show strong semantic alignment with the responsibilities of this vacancy."
                )
            return " ".join(parts)
        else:
            techs_str = _format_list(matched_es[:4], is_english=False)
            parts = [f"Recomendada con un {pct}% de afinidad:"]
            if role_es and domain_es and techs_str:
                parts.append(
                    f"Tu perfil como {role_es} coincide directamente con {domain_es} solicitado en esta vacante, respaldado por tu dominio en {techs_str}."
                )
            elif techs_str and domain_es:
                parts.append(
                    f"Tu experiencia en {techs_str} cubre directamente los requerimientos de {domain_es} para este cargo."
                )
            elif techs_str:
                parts.append(
                    f"Tus conocimientos en {techs_str} presentan una alta coincidencia con los requisitos técnicos exigidos."
                )
            elif domain_es:
                parts.append(
                    f"Tu perfil profesional y experiencia se alinean estrechamente con {domain_es} requerido en este puesto."
                )
            else:
                parts.append(
                    "Tu trayectoria profesional y habilidades técnicas demuestran una alta compatibilidad con las funciones de este cargo."
                )
            return " ".join(parts)
