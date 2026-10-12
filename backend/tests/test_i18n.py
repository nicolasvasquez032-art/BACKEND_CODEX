import pytest
from application.services.i18n_service import I18nService


def test_parse_accept_language_english():
    assert I18nService.parse_accept_language("en") == "en"
    assert I18nService.parse_accept_language("en-US") == "en"
    assert I18nService.parse_accept_language("en-US,en;q=0.9,es;q=0.8") == "en"
    assert I18nService.is_english("en") is True
    assert I18nService.is_english("en-US") is True


def test_parse_accept_language_spanish_default():
    assert I18nService.parse_accept_language("es") == "es"
    assert I18nService.parse_accept_language("es-CO,es;q=0.9,en;q=0.8") == "es"
    assert I18nService.parse_accept_language(None) == "es"
    assert I18nService.parse_accept_language("") == "es"
    assert I18nService.is_english("es") is False
    assert I18nService.is_english(None) is False


def test_translate_category():
    assert I18nService.translate_category("Ingeniería de Software", "en") == "Software Engineering"
    assert I18nService.translate_category("Tecnología", "en") == "Technology"
    assert I18nService.translate_category("Tecnología", "es") == "Tecnología"
    assert I18nService.translate_category("Tecnología", None) == "Tecnología"


def test_translate_title():
    assert (
        I18nService.translate_title("Ingeniero de Inteligencia Artificial", "en")
        == "Artificial Intelligence Engineer"
    )
    assert I18nService.translate_title("Desarrollador Flutter Senior", "en") == "Senior Flutter Developer"
    assert I18nService.translate_title("Desarrollador Backend", "en") == "Backend Developer"
    assert I18nService.translate_title("Desarrollador Backend", "es") == "Desarrollador Backend"


def test_translate_requirements():
    reqs = ["Trabajo en equipo", "Experiencia de 3 años", "Conocimientos en Python"]
    translated = I18nService.translate_requirements(reqs, "en")
    assert translated == ["Teamwork", "3 years of experience", "Knowledge of Python"]

    # Con +
    reqs_plus = ["Experiencia de 4+ años"]
    assert I18nService.translate_requirements(reqs_plus, "en") == ["4+ years of experience"]

    # In Spanish, remains unchanged
    assert I18nService.translate_requirements(reqs, "es") == reqs


def test_translate_location():
    assert I18nService.translate_location("Remoto", "en") == "Remote"
    assert I18nService.translate_location("Híbrido", "en") == "Hybrid"
    assert I18nService.translate_location("Medellín, Antioquia", "en") == "Medellin, Colombia"
    assert I18nService.translate_location("Remoto", "es") == "Remoto"


def test_translate_recommendation_explanation():
    expl = "Habilidades coincidentes: Python, Flutter. Alta compatibilidad con tu perfil."
    translated = I18nService.translate_recommendation_explanation(expl, "en")
    assert "Matching skills:" in translated
    assert "High match with your profile" in translated

    # Spanish unchanged
    assert I18nService.translate_recommendation_explanation(expl, "es") == expl


def test_translate_error():
    assert I18nService.translate_error("Vacante no encontrada", "en") == "Job vacancy not found"
    assert I18nService.translate_error("Acceso denegado", "en") == "Access denied"
    assert I18nService.translate_error("Vacante no encontrada", "es") == "Vacante no encontrada"


def test_translate_vacante_fields():
    translated = I18nService.translate_vacante_fields(
        titulo="Desarrollador Flutter Senior",
        descripcion="Únete para liderar el equipo móvil de TalentMatch. Buscamos experto en animaciones, Haptic Feedback y Riverpod.",
        requisitos=["Trabajo en equipo", "Experiencia de 4+ años"],
        ubicacion="Remoto",
        categoria="Tecnología",
        lang="en",
    )
    assert translated["titulo"] == "Senior Flutter Developer"
    assert "Join us to lead" in translated["descripcion"]
    assert translated["requisitos"] == ["Teamwork", "4+ years of experience"]
    assert translated["ubicacion"] == "Remote"
    assert translated["categoria"] == "Technology"

    # En español se conservan los valores originales
    original = I18nService.translate_vacante_fields(
        titulo="Desarrollador Flutter Senior",
        descripcion="Únete para liderar el equipo móvil de TalentMatch.",
        requisitos=["Trabajo en equipo"],
        ubicacion="Remoto",
        categoria="Tecnología",
        lang="es",
    )
    assert original["titulo"] == "Desarrollador Flutter Senior"
    assert original["ubicacion"] == "Remoto"
    assert original["categoria"] == "Tecnología"


from unittest.mock import AsyncMock
from httpx import ASGITransport, AsyncClient
from infrastructure.adapters.persistence.database import get_session
from infrastructure.api.app import create_app


@pytest.mark.asyncio
async def test_endpoint_accept_language_error_localization():
    fake_id = "00000000-0000-0000-0000-000000000000"
    app = create_app()

    mock_session = AsyncMock()
    mock_session.get.return_value = None

    async def mock_get_session():
        yield mock_session

    app.dependency_overrides[get_session] = mock_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Solicitud en inglés
        resp_en = await client.get(
            f"/vacantes/{fake_id}",
            headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        assert resp_en.status_code == 404
        assert resp_en.json()["detail"] == "Job vacancy not found"

        # Solicitud en español
        resp_es = await client.get(
            f"/vacantes/{fake_id}",
            headers={"Accept-Language": "es-CO,es;q=0.9"},
        )
        assert resp_es.status_code == 404
        assert resp_es.json()["detail"] == "Vacante no encontrada"

        # Solicitud sin encabezado (debe ser español por defecto)
        resp_default = await client.get(f"/vacantes/{fake_id}")
        assert resp_default.status_code == 404
        assert resp_default.json()["detail"] == "Vacante no encontrada"

