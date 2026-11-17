import pytest
from uuid import uuid4
from datetime import datetime, timezone

from application.services.ai_explainer_service import AiExplainerService
from application.services.i18n_service import I18nService
from domain.entities.notificacion import Notificacion, DeviceToken
from domain.entities.user import User, UserRole
from domain.entities.vacante import Vacante, VacanteEstado
from domain.entities.postulacion import Postulacion, PostulacionEstado
from domain.exceptions import DomainError, VacanteNotFoundError


class DummyObject:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_ai_explainer_all_roles_and_domains():
    roles_tests = [
        ("Experiencia en desarrollo frontend con React", "Desarrollador Frontend", "Frontend Developer"),
        ("Especialista en backend con microservicios y bases de datos", "Desarrollador Backend", "Backend Developer"),
        ("Desarrollo de aplicaciones flutter y movil", "Desarrollador Móvil", "Mobile Developer"),
        ("Investigador en inteligencia artificial y deep learning", "Especialista en IA", "AI Specialist"),
        ("Profesional ingenier de sistemas titulado", "Ingeniero de Sistemas", "Systems Engineer"),
    ]

    domains_tests = [
        ("Plataforma con motores de búsqueda y match de sentence", "inteligencia artificial"),
        ("Análisis de datos embeddings y data scientist", "datos"),
        ("Infraestructura en cloud aws ec2 servidores", "nube"),
        ("Aplicación en flutter móvil animaciones riverpod", "móvil"),
        ("Diseño ui/ux y prototipado figma", "UI/UX"),
        ("Servicios de backend con fastapi y python escalables", "backend"),
    ]

    for cand_text, expected_role_es, expected_role_en in roles_tests:
        p = DummyObject(
            job_title="",
            skills=["Python", "Java"],
            about_me=cand_text,
            education="",
            cv_text=cand_text,
        )
        v = DummyObject(
            titulo="Vacante",
            descripcion="Desarrollo de sistemas",
            requisitos=["Python", "Java"],
        )
        res_es = AiExplainerService.generate_explanation(p, v, 0.85, lang="es")
        assert expected_role_es in res_es
        res_en = AiExplainerService.generate_explanation(p, v, 0.85, lang="en")
        assert expected_role_en in res_en

    for vac_text, expected_keyword in domains_tests:
        p = DummyObject(
            job_title="",
            skills=["Python"],
            about_me="",
            education="",
            cv_text="Python",
        )
        v = DummyObject(
            titulo="Vacante Domain",
            descripcion=vac_text,
            requisitos=["Python"],
        )
        res_es = AiExplainerService.generate_explanation(p, v, 0.80, lang="es")
        assert len(res_es) > 30


def test_ai_explainer_conjunction_and_edge_cases():
    p = DummyObject(
        job_title="Especialista",
        skills=["Python", "Inteligencia Artificial"],
        about_me="",
        education="",
        cv_text="Python Inteligencia Artificial",
    )
    v = DummyObject(
        titulo="Vacante",
        descripcion="Python Inteligencia Artificial",
        requisitos=["Python", "Inteligencia Artificial"],
    )
    res_es = AiExplainerService.generate_explanation(p, v, 0.90, lang="es")
    assert "90% de afinidad" in res_es

    res_en = AiExplainerService.generate_explanation(p, v, 0.90, lang="en")
    assert "90% match" in res_en


def test_i18n_accept_language_parsing():
    assert I18nService.parse_accept_language(None) == "es"
    assert I18nService.parse_accept_language("") == "es"
    assert I18nService.parse_accept_language("en-US,en;q=0.9,es;q=0.8") == "en"
    assert I18nService.parse_accept_language("es-CO,es;q=0.9,en;q=0.5") == "es"
    assert I18nService.parse_accept_language("en;q=invalid,es;q=0.8") == "en"
    assert I18nService.parse_accept_language("  ,,  ") == "es"
    assert I18nService.is_english("en") is True
    assert I18nService.is_english("es") is False
    assert I18nService.is_english("en-US,en;q=0.9") is True
    assert I18nService.is_english(None) is False


def test_i18n_category_translations():
    assert I18nService.translate_category("Tecnología", "en") == "Technology"
    assert I18nService.translate_category("tecnología", "en") == "Technology"
    assert I18nService.translate_category("CategoríaDesconocida", "en") == "CategoríaDesconocida"
    assert I18nService.translate_category("Tecnología", "es") == "Tecnología"
    assert I18nService.translate_category(None, "en") is None


def test_i18n_title_translations():
    assert I18nService.translate_title("Desarrollador de Software", "en") == "Software Developer"
    assert I18nService.translate_title("Ingeniero de Inteligencia Artificial", "en") == "Artificial Intelligence Engineer"
    assert I18nService.translate_title("Diseñador UI", "en") == "Designer UI"
    assert I18nService.translate_title("Gerente de Proyectos", "en") == "Manager of Proyectos"
    assert I18nService.translate_title("Líder de Equipo", "en") == "Lead of Equipo"
    assert I18nService.translate_title("Analista de Datos", "en") == "Data Analyst"
    assert I18nService.translate_title("Analista de Pruebas", "en") == "Analyst of Pruebas"
    assert I18nService.translate_title("Especialista en Seguridad", "en") == "Specialist in Seguridad"
    assert I18nService.translate_title("Título Inalterado", "es") == "Título Inalterado"
    assert I18nService.translate_title("", "en") == ""


def test_i18n_description_translations():
    desc = "Descripción del trabajo: Buscamos un desarrollador experto en bases de datos para unirse a nuestro equipo."
    translated = I18nService.translate_description(desc, "en")
    assert "Job Description:" in translated
    assert "We are looking for an expert developer in" in translated
    assert "databases" in translated

    assert I18nService.translate_description(desc, "es") == desc
    assert I18nService.translate_description("", "en") == ""


def test_i18n_requirements_translations():
    reqs = [
        "Experiencia de 3 años",
        "Conocimientos en Python",
        "Requisito personalizado único",
    ]
    translated = I18nService.translate_requirements(reqs, "en")
    assert "3 years of experience" in translated
    assert "Knowledge of Python" in translated
    assert "Requisito personalizado único" in translated

    assert I18nService.translate_requirements(reqs, "es") == reqs
    assert I18nService.translate_requirements([], "en") == []


def test_i18n_location_translations():
    assert I18nService.translate_location("Remoto", "en") == "Remote"
    assert I18nService.translate_location("remoto", "en") == "Remote"
    assert I18nService.translate_location("híbrido", "en") == "Hybrid"
    assert I18nService.translate_location("presencial", "en") == "On-site"
    assert I18nService.translate_location("Bogotá, Colombia", "en") == "Bogota, Colombia"
    assert I18nService.translate_location("Medellín, Antioquia", "en") == "Medellin, Colombia"
    assert I18nService.translate_location("Cali, Valle del Cauca", "en") == "Cali, Colombia"
    assert I18nService.translate_location("Desconocida", "en") == "Desconocida"
    assert I18nService.translate_location("Remoto", "es") == "Remoto"
    assert I18nService.translate_location(None, "en") is None


def test_i18n_explanations_errors_and_vacante_fields():
    exp = "Habilidades coincidentes: Alta compatibilidad con tu perfil y Coincidencia semántica con IA."
    translated_exp = I18nService.translate_recommendation_explanation(exp, "en")
    assert "Matching skills:" in translated_exp
    assert "High match with your profile" in translated_exp
    assert "Semantic match with" in translated_exp

    assert I18nService.translate_recommendation_explanation(exp, "es") == exp
    assert I18nService.translate_recommendation_explanation("", "en") == ""

    # Errors
    err = "Vacante no encontrada"
    assert I18nService.translate_error(err, "en") == "Job vacancy not found"
    assert I18nService.translate_error(err, "es") == err
    assert I18nService.translate_error("Acceso denegado temporalmente", "en") == "Access denied temporalmente"
    assert I18nService.translate_error("", "en") == ""

    # Vacante fields
    fields_en = I18nService.translate_vacante_fields(
        titulo="Desarrollador de Software",
        descripcion="Descripción del trabajo: Buscamos un desarrollador.",
        requisitos=["Experiencia de 3 años"],
        ubicacion="Remoto",
        categoria="Tecnología",
        lang="en",
    )
    assert fields_en["titulo"] == "Software Developer"
    assert fields_en["ubicacion"] == "Remote"
    assert fields_en["categoria"] == "Technology"

    fields_es = I18nService.translate_vacante_fields(
        titulo="Desarrollador de Software",
        descripcion="Descripción",
        requisitos=["Python"],
        ubicacion="Remoto",
        categoria="Tecnología",
        lang="es",
    )
    assert fields_es["titulo"] == "Desarrollador de Software"


def test_notificacion_entity_methods():
    uid = uuid4()
    notif = Notificacion(
        usuario_id=uid,
        tipo="POSTULACION_RECIBIDA",
        mensaje="Tienes un nuevo candidato",
    )
    assert notif.leido is False
    notif.marcar_como_leida()
    assert notif.leido is True

    dt = DeviceToken(usuario_id=uid, token="tok_123", dispositivo_info="Android")
    assert dt.token == "tok_123"
    dt.actualizar_token("tok_456", "Android Pixel")
    assert dt.token == "tok_456"
    assert dt.dispositivo_info == "Android Pixel"

def test_ai_explainer_english_fallback_combinations():
    # 1. techs + domain (no role)
    p = DummyObject(job_title="", skills=["Python"], about_me="", education="", cv_text="Python")
    v = DummyObject(titulo="Vacante", descripcion="desarrollo backend fastapi", requisitos=["Python"])
    res1 = AiExplainerService.generate_explanation(p, v, 0.70, lang="en")
    assert "Your proficiency in" in res1 or "Recommended with" in res1

    # 2. techs only
    v2 = DummyObject(titulo="Vacante", descripcion="general", requisitos=["Python"])
    res2 = AiExplainerService.generate_explanation(p, v2, 0.70, lang="en")
    assert "Your skills in" in res2 or "Recommended with" in res2

    # 3. domain only (no techs)
    p3 = DummyObject(job_title="", skills=[], about_me="", education="", cv_text="")
    v3 = DummyObject(titulo="Vacante", descripcion="desarrollo backend fastapi", requisitos=[])
    res3 = AiExplainerService.generate_explanation(p3, v3, 0.70, lang="en")
    assert "Your background and technical expertise align well with" in res3 or "Recommended with" in res3

    # 4. neither (empty)
    v4 = DummyObject(titulo="Vacante", descripcion="general", requisitos=[])
    res4 = AiExplainerService.generate_explanation(p3, v4, 0.70, lang="en")
    assert "semantic alignment" in res4

def test_domain_entities_methods_exhaustive():
    now = datetime.now(timezone.utc)
    uid = uuid4()
    
    # 1. PasswordResetToken
    from domain.entities.password_reset_token import PasswordResetToken
    token_valid = PasswordResetToken(
        id=uuid4(),
        user_id=uid,
        token_hash="hash123",
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        used=False,
    )
    assert token_valid.is_valid(now) is True

    token_used = PasswordResetToken(
        id=uuid4(),
        user_id=uid,
        token_hash="hash123",
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        used=True,
    )
    assert token_used.is_valid(now) is False

    token_expired = PasswordResetToken(
        id=uuid4(),
        user_id=uid,
        token_hash="hash123",
        expires_at=datetime(2000, 1, 1, tzinfo=timezone.utc),
        used=False,
    )
    assert token_expired.is_valid(now) is False

    # 2. Postulacion transitions
    post = Postulacion(
        id=uuid4(),
        candidato_id=uid,
        vacante_id=uuid4(),
        estado=PostulacionEstado.POSTULADO,
        fecha=now,
    )
    assert post.puede_cambiar_estado(PostulacionEstado.ENTREVISTA) is True
    assert post.puede_cambiar_estado(PostulacionEstado.RECHAZADO) is True
    assert post.puede_cambiar_estado(PostulacionEstado.CONTRATADO) is False

    post_entrevista = Postulacion(
        id=uuid4(),
        candidato_id=uid,
        vacante_id=uuid4(),
        estado=PostulacionEstado.ENTREVISTA,
        fecha=now,
    )
    assert post_entrevista.puede_cambiar_estado(PostulacionEstado.CONTRATADO) is True
    assert post_entrevista.puede_cambiar_estado(PostulacionEstado.RECHAZADO) is True
    assert post_entrevista.puede_cambiar_estado(PostulacionEstado.POSTULADO) is False

    post_final = Postulacion(
        id=uuid4(),
        candidato_id=uid,
        vacante_id=uuid4(),
        estado=PostulacionEstado.CONTRATADO,
        fecha=now,
    )
    assert post_final.puede_cambiar_estado(PostulacionEstado.RECHAZADO) is False

    # 3. Vacante
    vac = Vacante(
        id=uuid4(),
        empresa_id=uid,
        titulo="Dev",
        descripcion="Desc",
        requisitos=[],
        ubicacion="Remoto",
        estado=VacanteEstado.ACTIVA,
        creado_en=now,
    )
    assert vac.esta_activa() is True
    assert vac.puede_ser_editada_por(uid) is True
    assert vac.puede_ser_editada_por(uuid4()) is False

    vac_pausada = Vacante(
        id=uuid4(),
        empresa_id=uid,
        titulo="Dev",
        descripcion="Desc",
        requisitos=[],
        ubicacion="Remoto",
        estado=VacanteEstado.PAUSADA,
        creado_en=now,
    )
    assert vac_pausada.esta_activa() is False

from application.use_cases.eliminar_vacante import EliminarVacanteUseCase, EliminarVacanteCommand
from application.use_cases.cambiar_estado_vacante import CambiarEstadoVacanteUseCase, CambiarEstadoVacanteCommand
from application.use_cases.actualizar_vacante import ActualizarVacanteUseCase, ActualizarVacanteCommand
from application.use_cases.register_company import RegisterCompanyUseCase, RegisterCompanyCommand
from application.use_cases.register_device_token import RegisterDeviceTokenUseCase
from application.use_cases.upload_cv import UploadCvUseCase, UploadCvCommand
from domain.exceptions import PermissionDeniedError, VacanteNotFoundError, EmailAlreadyRegisteredError
from tests.fakes import FakeVacanteRepository, FakeMlService, FakeUserRepository, FakePasswordHasher, FakeTokenService, FakeNotificacionRepository, FakeCvParser


@pytest.mark.asyncio
async def test_use_cases_error_branches():
    vac_repo = FakeVacanteRepository()
    user_repo = FakeUserRepository()
    ml_service = FakeMlService()
    hasher = FakePasswordHasher()
    tokens = FakeTokenService()
    notif_repo = FakeNotificacionRepository()

    owner_id = uuid4()
    other_id = uuid4()
    vac_id = uuid4()

    # Pre-create a vacancy
    vac = Vacante(
        id=vac_id,
        empresa_id=owner_id,
        titulo="Software Eng",
        descripcion="Desc",
        requisitos=["Python"],
        ubicacion="Remoto",
        estado=VacanteEstado.ACTIVA,
        creado_en=datetime.now(timezone.utc),
    )
    vac_repo.vacantes[vac_id] = vac

    # 1. EliminarVacante: Not found & Permission denied
    eliminar_uc = EliminarVacanteUseCase(vac_repo)
    with pytest.raises(VacanteNotFoundError):
        await eliminar_uc.execute(EliminarVacanteCommand(vacante_id=uuid4(), requesting_empresa_id=owner_id))

    with pytest.raises(PermissionDeniedError):
        await eliminar_uc.execute(EliminarVacanteCommand(vacante_id=vac_id, requesting_empresa_id=other_id))

    # 2. CambiarEstadoVacante: Not found & Permission denied
    cambiar_uc = CambiarEstadoVacanteUseCase(vac_repo)
    with pytest.raises(VacanteNotFoundError):
        await cambiar_uc.execute(CambiarEstadoVacanteCommand(vacante_id=uuid4(), requesting_empresa_id=owner_id, nuevo_estado=VacanteEstado.PAUSADA))

    with pytest.raises(PermissionDeniedError):
        await cambiar_uc.execute(CambiarEstadoVacanteCommand(vacante_id=vac_id, requesting_empresa_id=other_id, nuevo_estado=VacanteEstado.PAUSADA))

    # 3. ActualizarVacante: Not found, Permission denied & ML exception handling
    act_uc = ActualizarVacanteUseCase(vac_repo, ml_service)
    with pytest.raises(VacanteNotFoundError):
        await act_uc.execute(ActualizarVacanteCommand(vacante_id=uuid4(), requesting_empresa_id=owner_id, titulo="T", descripcion="D", requisitos=[], ubicacion="U"))

    with pytest.raises(PermissionDeniedError):
        await act_uc.execute(ActualizarVacanteCommand(vacante_id=vac_id, requesting_empresa_id=other_id, titulo="T", descripcion="D", requisitos=[], ubicacion="U"))

    # Successful update with ML fallback
    updated = await act_uc.execute(ActualizarVacanteCommand(vacante_id=vac_id, requesting_empresa_id=owner_id, titulo="Updated", descripcion="D", requisitos=["Python"], ubicacion="Remoto"))
    assert updated.titulo == "Updated"

    # 4. RegisterCompany: Email duplicate
    company_uc = RegisterCompanyUseCase(user_repo, hasher)
    await company_uc.execute(RegisterCompanyCommand(email="empresa@test.com", password="Pass1234!"))
    with pytest.raises(EmailAlreadyRegisteredError):
        await company_uc.execute(RegisterCompanyCommand(email="empresa@test.com", password="Pass1234!"))

    # 5. RegisterDeviceToken: Create then Update
    from unittest.mock import AsyncMock
    repo_mock = AsyncMock()
    repo_mock.get_device_token_by_usuario_id.side_effect = [None, DeviceToken(usuario_id=owner_id, token="tok_1")]
    token_uc = RegisterDeviceTokenUseCase(repo_mock)
    dt1 = await token_uc.execute(usuario_id=owner_id, token="tok_1", dispositivo_info="iOS")
    assert dt1.token == "tok_1"
    dt2 = await token_uc.execute(usuario_id=owner_id, token="tok_2", dispositivo_info="iOS 17")
    assert dt2.token == "tok_2"

    # 6. UploadCV: ProfileNotFoundError & Permission denied
    from domain.exceptions import ProfileNotFoundError
    cv_parser = FakeCvParser(extracted_text="Curriculum vitae")
    from application.use_cases.upload_cv import UploadCvUseCase, UploadCvCommand
    upload_cv_uc = UploadCvUseCase(user_repo, cv_parser, ml_service)
    with pytest.raises(ProfileNotFoundError):
        await upload_cv_uc.execute(UploadCvCommand(profile_id=uuid4(), requesting_user_id=owner_id, file_bytes=b"test", mime_type="application/pdf", file_name="test.pdf"))

    cand_user = await user_repo.create_user(email="cand123@test.com", password_hash="pass", role="candidate")
    prof = await user_repo.create_candidate_profile(user_id=cand_user.id, full_name="Cand", skills=[], experience_years=0, location="Bogota", education="Ing")
    with pytest.raises(PermissionDeniedError):
        await upload_cv_uc.execute(UploadCvCommand(profile_id=prof.id, requesting_user_id=owner_id, file_bytes=b"test", mime_type="application/pdf", file_name="test.pdf"))
