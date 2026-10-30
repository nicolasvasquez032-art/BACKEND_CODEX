from uuid import uuid4
import pytest

from application.use_cases.actualizar_vacante import (
    ActualizarVacanteCommand,
    ActualizarVacanteUseCase,
)
from application.use_cases.cambiar_estado_postulacion import (
    CambiarEstadoPostulacionCommand,
    CambiarEstadoPostulacionUseCase,
)
from application.use_cases.cambiar_estado_vacante import (
    CambiarEstadoVacanteCommand,
    CambiarEstadoVacanteUseCase,
)
from application.use_cases.eliminar_vacante import (
    EliminarVacanteCommand,
    EliminarVacanteUseCase,
)
from application.use_cases.listar_postulaciones import (
    ListarPostulacionesCandidatoQuery,
    ListarPostulacionesCandidatoUseCase,
    ListarPostulacionesVacanteQuery,
    ListarPostulacionesVacanteUseCase,
)
from application.use_cases.listar_vacantes import (
    ListarVacantesQuery,
    ListarVacantesUseCase,
)
from application.use_cases.postularse_a_vacante import (
    PostularseAVacanteCommand,
    PostularseAVacanteUseCase,
)
from application.use_cases.publicar_vacante import (
    PublicarVacanteCommand,
    PublicarVacanteUseCase,
)
from domain.entities.postulacion import PostulacionEstado
from domain.entities.vacante import VacanteEstado
from domain.exceptions import (
    DuplicatePostulacionError,
    InvalidEstadoTransitionError,
    PermissionDeniedError,
    PostulacionNotFoundError,
    VacanteNotFoundError,
)
from tests.fakes import (
    FakeMlService,
    FakeNotificacionRepository,
    FakePostulacionRepository,
    FakePushNotificationPort,
    FakeVacanteRepository,
)


@pytest.mark.asyncio
async def test_publicar_y_listar_vacantes():
    empresa_id = uuid4()
    vacante_repo = FakeVacanteRepository()
    ml_service = FakeMlService()
    notif_repo = FakeNotificacionRepository()
    push_port = FakePushNotificationPort()

    use_case = PublicarVacanteUseCase(vacante_repo, ml_service, notif_repo, push_port)
    vacante = await use_case.execute(
        PublicarVacanteCommand(
            empresa_id=empresa_id,
            titulo="Desarrollador Python Senior",
            descripcion="Buscamos experto en FastAPI",
            requisitos=["Python", "FastAPI"],
            ubicacion="Bogotá",
            categoria="Tecnología",
            salario_min=5000000.0,
            salario_max=8000000.0,
        )
    )

    assert vacante.titulo == "Desarrollador Python Senior"
    assert vacante.empresa_id == empresa_id
    assert vacante.estado == VacanteEstado.ACTIVA

    # Listar vacantes
    listar_use_case = ListarVacantesUseCase(vacante_repo)
    vacantes = await listar_use_case.execute(
        ListarVacantesQuery(ubicacion="Bogotá", categoria="Tecnología", offset=0, limit=10)
    )
    assert len(vacantes) == 1
    assert vacantes[0].id == vacante.id


@pytest.mark.asyncio
async def test_actualizar_y_cambiar_estado_vacante():
    empresa_id = uuid4()
    otra_empresa_id = uuid4()
    vacante_repo = FakeVacanteRepository()
    ml_service = FakeMlService()

    vacante = await vacante_repo.create(
        empresa_id=empresa_id,
        titulo="Frontend Dev",
        descripcion="React y Flutter",
        requisitos=["Flutter"],
        ubicacion="Remoto",
    )

    actualizar_use_case = ActualizarVacanteUseCase(vacante_repo, ml_service)

    # Error si no es dueño
    with pytest.raises(PermissionDeniedError):
        await actualizar_use_case.execute(
            ActualizarVacanteCommand(
                vacante_id=vacante.id,
                requesting_empresa_id=otra_empresa_id,
                titulo="Nuevo Título",
                descripcion="Nueva Desc",
                requisitos=["Dart"],
                ubicacion="Remoto",
            )
        )

    # Actualización exitosa
    actualizada = await actualizar_use_case.execute(
        ActualizarVacanteCommand(
            vacante_id=vacante.id,
            requesting_empresa_id=empresa_id,
            titulo="Frontend Lead",
            descripcion="Líder frontend",
            requisitos=["Flutter", "Dart"],
            ubicacion="Remoto",
        )
    )
    assert actualizada.titulo == "Frontend Lead"

    # Cambiar estado
    cambiar_estado_use_case = CambiarEstadoVacanteUseCase(vacante_repo)
    pausada = await cambiar_estado_use_case.execute(
        CambiarEstadoVacanteCommand(
            vacante_id=vacante.id,
            requesting_empresa_id=empresa_id,
            nuevo_estado=VacanteEstado.PAUSADA,
        )
    )
    assert pausada.estado == VacanteEstado.PAUSADA

    # Eliminar vacante
    eliminar_use_case = EliminarVacanteUseCase(vacante_repo)
    await eliminar_use_case.execute(
        EliminarVacanteCommand(
            vacante_id=vacante.id,
            requesting_empresa_id=empresa_id,
        )
    )
    assert await vacante_repo.find_by_id(vacante.id) is None


@pytest.mark.asyncio
async def test_postularse_y_gestionar_postulaciones():
    empresa_id = uuid4()
    candidato_id = uuid4()
    vacante_repo = FakeVacanteRepository()
    postulacion_repo = FakePostulacionRepository()

    vacante = await vacante_repo.create(
        empresa_id=empresa_id,
        titulo="Backend Dev",
        descripcion="Python",
        requisitos=["Python"],
        ubicacion="Bogotá",
    )

    postularse_use_case = PostularseAVacanteUseCase(postulacion_repo, vacante_repo)
    postulacion = await postularse_use_case.execute(
        PostularseAVacanteCommand(candidato_id=candidato_id, vacante_id=vacante.id)
    )

    assert postulacion.candidato_id == candidato_id
    assert postulacion.vacante_id == vacante.id
    assert postulacion.estado == PostulacionEstado.POSTULADO

    # Error al duplicar postulación
    with pytest.raises(DuplicatePostulacionError):
        await postularse_use_case.execute(
            PostularseAVacanteCommand(candidato_id=candidato_id, vacante_id=vacante.id)
        )

    # Listar postulaciones
    listar_candidato = ListarPostulacionesCandidatoUseCase(postulacion_repo)
    mis_postulaciones = await listar_candidato.execute(
        ListarPostulacionesCandidatoQuery(
            candidato_id=candidato_id,
            requesting_user_id=candidato_id,
            requesting_user_role="candidate",
        )
    )
    assert len(mis_postulaciones) == 1

    listar_vacante = ListarPostulacionesVacanteUseCase(postulacion_repo, vacante_repo)
    postulaciones_vacante = await listar_vacante.execute(
        ListarPostulacionesVacanteQuery(vacante_id=vacante.id, requesting_empresa_id=empresa_id)
    )
    assert len(postulaciones_vacante) == 1

    # Cambiar estado postulación: postulado -> entrevista
    cambiar_estado_postulacion = CambiarEstadoPostulacionUseCase(postulacion_repo, vacante_repo)
    actualizada = await cambiar_estado_postulacion.execute(
        CambiarEstadoPostulacionCommand(
            postulacion_id=postulacion.id,
            requesting_empresa_id=empresa_id,
            nuevo_estado=PostulacionEstado.ENTREVISTA,
        )
    )
    assert actualizada.estado == PostulacionEstado.ENTREVISTA

    # Error si otra empresa intenta cambiar estado
    with pytest.raises(PermissionDeniedError):
        await cambiar_estado_postulacion.execute(
            CambiarEstadoPostulacionCommand(
                postulacion_id=postulacion.id,
                requesting_empresa_id=uuid4(),
                nuevo_estado=PostulacionEstado.CONTRATADO,
            )
        )

    # Error de transición inválida (de entrevista a postulado no se puede)
    with pytest.raises(InvalidEstadoTransitionError):
        await cambiar_estado_postulacion.execute(
            CambiarEstadoPostulacionCommand(
                postulacion_id=postulacion.id,
                requesting_empresa_id=empresa_id,
                nuevo_estado=PostulacionEstado.POSTULADO,
            )
        )
