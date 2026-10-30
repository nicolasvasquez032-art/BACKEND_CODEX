from uuid import uuid4
import pytest
from unittest.mock import AsyncMock

from application.ports.admin_ports import AdminMetricasRepositoryPort
from application.ports.ml_service_port import RecomendacionDTO
from application.use_cases.get_admin_metrics import (
    GetEfectividadRecomendacionUseCase,
    GetMetricasResumenUseCase,
    GetSectoresDemandaUseCase,
    GetTiempoContratacionUseCase,
)
from application.use_cases.get_candidate_profile import (
    GetCandidateProfileCommand,
    GetCandidateProfileUseCase,
)
from application.use_cases.get_notificaciones import GetNotificacionesUseCase
from application.use_cases.get_recomendaciones import GetRecomendacionesUseCase
from application.use_cases.moderar_vacante import ModerarVacanteUseCase
from application.use_cases.update_candidate_profile import (
    UpdateCandidateProfileCommand,
    UpdateCandidateProfileUseCase,
)
from domain.entities.vacante import VacanteEstado
from domain.exceptions import PermissionDeniedError, ProfileNotFoundError
from tests.fakes import (
    FakeMlService,
    FakeUserRepository,
    FakeVacanteRepository,
)


@pytest.mark.asyncio
async def test_perfiles_candidato_get_and_update():
    user_repo = FakeUserRepository()
    ml_service = FakeMlService()

    user_id = uuid4()
    otro_user_id = uuid4()
    profile = await user_repo.create_candidate_profile(
        user_id=user_id,
        full_name="Nicolas Gomez",
        skills=["Python", "Flutter"],
        experience_years=3,
        location="Bogotá",
        education="Ingeniero",
    )

    get_use_case = GetCandidateProfileUseCase(user_repo)

    # 1. Candidato dueño puede ver su perfil
    result = await get_use_case.execute(
        GetCandidateProfileCommand(
            profile_id=profile.id,
            requesting_user_id=user_id,
            requesting_user_role="candidate",
        )
    )
    assert result.full_name == "Nicolas Gomez"

    # 2. Empresa puede ver el perfil
    company_view = await get_use_case.execute(
        GetCandidateProfileCommand(
            profile_id=profile.id,
            requesting_user_id=otro_user_id,
            requesting_user_role="company",
        )
    )
    assert company_view.id == profile.id

    # 3. Otro candidato no puede ver el perfil
    with pytest.raises(PermissionDeniedError):
        await get_use_case.execute(
            GetCandidateProfileCommand(
                profile_id=profile.id,
                requesting_user_id=otro_user_id,
                requesting_user_role="candidate",
            )
        )

    # 4. Perfil inexistente lanza ProfileNotFoundError
    with pytest.raises(ProfileNotFoundError):
        await get_use_case.execute(
            GetCandidateProfileCommand(
                profile_id=uuid4(),
                requesting_user_id=user_id,
                requesting_user_role="candidate",
            )
        )

    # 5. Actualizar perfil como dueño
    update_use_case = UpdateCandidateProfileUseCase(user_repo, ml_service)
    updated = await update_use_case.execute(
        UpdateCandidateProfileCommand(
            profile_id=profile.id,
            requesting_user_id=user_id,
            full_name="Nicolas Gomez Updated",
            skills=["Python", "Flutter", "AWS"],
            experience_years=4,
            location="Medellín",
            education="Especialista",
            phone="3101234567",
            portfolio_url="https://nicolas.dev",
            about_me="Dev senior",
            job_title="Tech Lead",
        )
    )
    assert updated.full_name == "Nicolas Gomez Updated"
    assert updated.experience_years == 4
    assert "AWS" in updated.skills

    # 6. Actualizar perfil intentado por otro usuario falla
    with pytest.raises(PermissionDeniedError):
        await update_use_case.execute(
            UpdateCandidateProfileCommand(
                profile_id=profile.id,
                requesting_user_id=otro_user_id,
                full_name="Hack",
                skills=[],
                experience_years=0,
            )
        )


@pytest.mark.asyncio
async def test_moderar_vacante_y_recomendaciones():
    vacante_repo = FakeVacanteRepository()
    vacante = await vacante_repo.create(
        empresa_id=uuid4(),
        titulo="Dev Java",
        descripcion="Desc",
        requisitos=[],
        ubicacion="Remoto",
    )

    moderar_use_case = ModerarVacanteUseCase(vacante_repo)
    moderada = await moderar_use_case.execute(vacante.id, VacanteEstado.CERRADA)
    assert moderada.estado == VacanteEstado.CERRADA

    # Recomendaciones Use Case
    ml_mock = AsyncMock()
    ml_mock.get_recomendaciones.return_value = [
        RecomendacionDTO(
            vacante_id=uuid4(),
            titulo="Data Scientist",
            empresa_id=uuid4(),
            score_similitud=0.92,
            explicacion="Afinidad en Python",
        )
    ]
    rec_use_case = GetRecomendacionesUseCase(ml_mock)
    recs = await rec_use_case.execute(uuid4())
    assert len(recs) == 1
    assert recs[0].titulo == "Data Scientist"


@pytest.mark.asyncio
async def test_admin_metricas_y_notificaciones():
    mock_metrics_repo = AsyncMock(spec=AdminMetricasRepositoryPort)
    mock_metrics_repo.get_total_candidatos.return_value = 150
    mock_metrics_repo.get_total_vacantes_activas.return_value = 35
    mock_metrics_repo.get_total_postulaciones.return_value = 420
    mock_metrics_repo.get_sectores_demanda.return_value = [{"sector": "Tecnología", "total": 25}]
    mock_metrics_repo.get_tiempo_promedio_contratacion_dias.return_value = 14.5
    mock_metrics_repo.get_efectividad_recomendacion.return_value = 85.0

    resumen = await GetMetricasResumenUseCase(mock_metrics_repo).execute()
    assert resumen.total_candidatos == 150
    assert resumen.total_vacantes_activas == 35
    assert resumen.total_postulaciones == 420

    sectores = await GetSectoresDemandaUseCase(mock_metrics_repo).execute()
    assert len(sectores) == 1
    assert sectores[0]["sector"] == "Tecnología"

    tiempo = await GetTiempoContratacionUseCase(mock_metrics_repo).execute()
    assert tiempo == 14.5

    efectividad = await GetEfectividadRecomendacionUseCase(mock_metrics_repo).execute()
    assert efectividad == 85.0

    # Notificaciones Use Case
    notif_repo = AsyncMock()
    notif_repo.get_notificaciones_by_usuario.return_value = ["notif1", "notif2"]
    notifs = await GetNotificacionesUseCase(notif_repo).execute(uuid4())
    assert len(notifs) == 2
