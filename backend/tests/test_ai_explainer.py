from dataclasses import dataclass
from application.services.ai_explainer_service import AiExplainerService


@dataclass
class DummyPerfil:
    job_title: str
    skills: list[str]
    about_me: str
    education: str
    cv_text: str


@dataclass
class DummyVacante:
    titulo: str
    descripcion: str
    requisitos: list[str]


def test_ai_explainer_full_stack_match_spanish():
    perfil = DummyPerfil(
        job_title="",
        skills=["Python"],
        about_me="Desarrollador Full Stack apasionado por software escalable.",
        education="Ingeniería de Sistemas",
        cv_text="Desarrollador Full Stack con experiencia en Python, Java, Dart, Flutter y bases de datos SQL y NoSQL.",
    )
    vacante = DummyVacante(
        titulo="Empresas de tecnología y startups",
        descripcion="Buscamos un desarrollador para diseño y mantenimiento de aplicaciones web y móviles.",
        requisitos=["Conocimientos en Java, Python, JavaScript o Dart. Manejo de bases de datos SQL y NoSQL."],
    )

    exp = AiExplainerService.generate_explanation(perfil, vacante, 0.6657, lang="es")
    assert "67% de afinidad" in exp
    assert "Desarrollador Full Stack" in exp
    assert "web y móviles" in exp
    assert "Python" in exp
    assert "Java" in exp


def test_ai_explainer_full_stack_match_english():
    perfil = DummyPerfil(
        job_title="",
        skills=["Python"],
        about_me="",
        education="Computer Science",
        cv_text="Full Stack developer with experience in Python, Java, Dart and Flutter.",
    )
    vacante = DummyVacante(
        titulo="Empresas de tecnología y startups",
        descripcion="Software developer for web and mobile solutions.",
        requisitos=["Java, Python, Dart."],
    )

    exp = AiExplainerService.generate_explanation(perfil, vacante, 0.6657, lang="en")
    assert "67% match" in exp
    assert "Full Stack Developer" in exp
    assert "Python" in exp
    assert "Java" in exp


def test_ai_explainer_empty_perfil_fallback():
    perfil = DummyPerfil(job_title="", skills=[], about_me="", education="", cv_text="")
    vacante = DummyVacante(titulo="Vacante General", descripcion="Descripción general.", requisitos=[])

    exp = AiExplainerService.generate_explanation(perfil, vacante, 0.55, lang="es")
    assert "55% de afinidad" in exp
    assert len(exp) > 20
