"""Tests unitarios para los casos de uso de vacantes y postulaciones — Sprint 2."""
import uuid

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
from application.use_cases.listar_postulaciones import (
    ListarPostulacionesCandidatoQuery,
    ListarPostulacionesCandidatoUseCase,
    ListarPostulacionesVacanteQuery,
    ListarPostulacionesVacanteUseCase,
)
from application.use_cases.listar_vacantes import ListarVacantesQuery, ListarVacantesUseCase
from application.use_cases.postularse_a_vacante import (
    PostularseAVacanteCommand,
    PostularseAVacanteUseCase,
)
from application.use_cases.publicar_vacante import PublicarVacanteCommand, PublicarVacanteUseCase
from domain.entities.postulacion import PostulacionEstado
from domain.entities.vacante import VacanteEstado
from domain.exceptions import (
    DuplicatePostulacionError,
    InvalidEstadoTransitionError,
    PermissionDeniedError,
    VacanteNotFoundError,
)
from tests.fakes import FakePostulacionRepository, FakeVacanteRepository, FakeMlService, FakeNotificacionRepository, FakePushNotificationPort


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def empresa_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture()
def candidato_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture()
def vacantes_repo() -> FakeVacanteRepository:
    return FakeVacanteRepository()


@pytest.fixture()
def postulaciones_repo() -> FakePostulacionRepository:
    return FakePostulacionRepository()


async def _crear_vacante_activa(repo: FakeVacanteRepository, empresa_id: uuid.UUID):
    return await repo.create(
        empresa_id=empresa_id,
        titulo="Desarrollador Python",
        descripcion="Se busca desarrollador con experiencia en FastAPI",
        requisitos=["Python", "FastAPI", "PostgreSQL"],
        ubicacion="Fusagasugá",
        categoria="Tecnología",
        salario_min=2_000_000,
        salario_max=4_000_000,
    )


# ── PublicarVacante ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_publicar_vacante_success(vacantes_repo, empresa_id):
    use_case = PublicarVacanteUseCase(vacantes_repo, FakeMlService(), FakeNotificacionRepository(), FakePushNotificationPort())
    vacante = await use_case.execute(
        PublicarVacanteCommand(
            empresa_id=empresa_id,
            titulo="Analista de datos",
            descripcion="Experiencia en SQL y Python",
            requisitos=["SQL", "Python"],
            ubicacion="Bogotá",
        )
    )
    assert vacante.titulo == "Analista de datos"
    assert vacante.estado == VacanteEstado.ACTIVA
    assert vacante.empresa_id == empresa_id


# ── ListarVacantes ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_listar_vacantes_filtra_por_ubicacion(vacantes_repo, empresa_id):
    await _crear_vacante_activa(vacantes_repo, empresa_id)
    await vacantes_repo.create(
        empresa_id=empresa_id, titulo="Aux contable",
        descripcion="Experiencia en contabilidad básica",
        requisitos=[], ubicacion="Bogotá", categoria=None,
        salario_min=None, salario_max=None,
    )

    use_case = ListarVacantesUseCase(vacantes_repo)
    results = await use_case.execute(ListarVacantesQuery(ubicacion="Fusagasugá"))
    assert len(results) == 1
    assert results[0].ubicacion == "Fusagasugá"


@pytest.mark.asyncio
async def test_listar_vacantes_excluye_cerradas(vacantes_repo, empresa_id):
    vacante = await _crear_vacante_activa(vacantes_repo, empresa_id)
    await vacantes_repo.change_estado(vacante.id, VacanteEstado.CERRADA)

    use_case = ListarVacantesUseCase(vacantes_repo)
    results = await use_case.execute(ListarVacantesQuery())
    assert len(results) == 0


# ── ActualizarVacante ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_actualizar_vacante_success(vacantes_repo, empresa_id):
    vacante = await _crear_vacante_activa(vacantes_repo, empresa_id)

    use_case = ActualizarVacanteUseCase(vacantes_repo, FakeMlService())
    updated = await use_case.execute(
        ActualizarVacanteCommand(
            vacante_id=vacante.id,
            requesting_empresa_id=empresa_id,
            titulo="Dev Python Senior",
            descripcion="Más de 3 años de experiencia",
            requisitos=["Python", "FastAPI", "Docker"],
            ubicacion="Fusagasugá",
        )
    )
    assert updated.titulo == "Dev Python Senior"


@pytest.mark.asyncio
async def test_actualizar_vacante_otra_empresa_raises(vacantes_repo, empresa_id):
    vacante = await _crear_vacante_activa(vacantes_repo, empresa_id)
    otra_empresa = uuid.uuid4()

    use_case = ActualizarVacanteUseCase(vacantes_repo, FakeMlService())
    with pytest.raises(PermissionDeniedError):
        await use_case.execute(
            ActualizarVacanteCommand(
                vacante_id=vacante.id,
                requesting_empresa_id=otra_empresa,
                titulo="Intento de edición",
                descripcion="No debería funcionar",
                requisitos=[],
                ubicacion="Bogotá",
            )
        )


# ── CambiarEstadoVacante ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cambiar_estado_vacante_success(vacantes_repo, empresa_id):
    vacante = await _crear_vacante_activa(vacantes_repo, empresa_id)

    use_case = CambiarEstadoVacanteUseCase(vacantes_repo)
    updated = await use_case.execute(
        CambiarEstadoVacanteCommand(
            vacante_id=vacante.id,
            requesting_empresa_id=empresa_id,
            nuevo_estado=VacanteEstado.PAUSADA,
        )
    )
    assert updated.estado == VacanteEstado.PAUSADA


# ── PostularseAVacante ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_postularse_success(vacantes_repo, postulaciones_repo, empresa_id, candidato_id):
    vacante = await _crear_vacante_activa(vacantes_repo, empresa_id)

    use_case = PostularseAVacanteUseCase(postulaciones_repo, vacantes_repo)
    postulacion = await use_case.execute(
        PostularseAVacanteCommand(candidato_id=candidato_id, vacante_id=vacante.id)
    )
    assert postulacion.candidato_id == candidato_id
    assert postulacion.estado == PostulacionEstado.POSTULADO


@pytest.mark.asyncio
async def test_postularse_duplicado_raises(vacantes_repo, postulaciones_repo, empresa_id, candidato_id):
    vacante = await _crear_vacante_activa(vacantes_repo, empresa_id)
    use_case = PostularseAVacanteUseCase(postulaciones_repo, vacantes_repo)
    cmd = PostularseAVacanteCommand(candidato_id=candidato_id, vacante_id=vacante.id)

    await use_case.execute(cmd)
    with pytest.raises(DuplicatePostulacionError):
        await use_case.execute(cmd)


@pytest.mark.asyncio
async def test_postularse_vacante_cerrada_raises(vacantes_repo, postulaciones_repo, empresa_id, candidato_id):
    vacante = await _crear_vacante_activa(vacantes_repo, empresa_id)
    await vacantes_repo.change_estado(vacante.id, VacanteEstado.CERRADA)

    use_case = PostularseAVacanteUseCase(postulaciones_repo, vacantes_repo)
    with pytest.raises(VacanteNotFoundError):
        await use_case.execute(
            PostularseAVacanteCommand(candidato_id=candidato_id, vacante_id=vacante.id)
        )


# ── CambiarEstadoPostulacion ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cambiar_estado_postulacion_flow(vacantes_repo, postulaciones_repo, empresa_id, candidato_id):
    vacante = await _crear_vacante_activa(vacantes_repo, empresa_id)
    postulacion = await postulaciones_repo.create(candidato_id=candidato_id, vacante_id=vacante.id)

    use_case = CambiarEstadoPostulacionUseCase(postulaciones_repo, vacantes_repo)

    # postulado → entrevista
    p = await use_case.execute(
        CambiarEstadoPostulacionCommand(
            postulacion_id=postulacion.id,
            requesting_empresa_id=empresa_id,
            nuevo_estado=PostulacionEstado.ENTREVISTA,
        )
    )
    assert p.estado == PostulacionEstado.ENTREVISTA

    # entrevista → contratado
    p = await use_case.execute(
        CambiarEstadoPostulacionCommand(
            postulacion_id=postulacion.id,
            requesting_empresa_id=empresa_id,
            nuevo_estado=PostulacionEstado.CONTRATADO,
        )
    )
    assert p.estado == PostulacionEstado.CONTRATADO


@pytest.mark.asyncio
async def test_cambiar_estado_postulacion_transicion_invalida(vacantes_repo, postulaciones_repo, empresa_id, candidato_id):
    vacante = await _crear_vacante_activa(vacantes_repo, empresa_id)
    postulacion = await postulaciones_repo.create(candidato_id=candidato_id, vacante_id=vacante.id)

    use_case = CambiarEstadoPostulacionUseCase(postulaciones_repo, vacantes_repo)

    # postulado → contratado (inválido, se debe pasar por entrevista)
    with pytest.raises(InvalidEstadoTransitionError):
        await use_case.execute(
            CambiarEstadoPostulacionCommand(
                postulacion_id=postulacion.id,
                requesting_empresa_id=empresa_id,
                nuevo_estado=PostulacionEstado.CONTRATADO,
            )
        )


# ── ListarPostulaciones ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_listar_postulaciones_candidato_propio(postulaciones_repo, vacantes_repo, empresa_id, candidato_id):
    vacante = await _crear_vacante_activa(vacantes_repo, empresa_id)
    await postulaciones_repo.create(candidato_id=candidato_id, vacante_id=vacante.id)

    use_case = ListarPostulacionesCandidatoUseCase(postulaciones_repo)
    results = await use_case.execute(
        ListarPostulacionesCandidatoQuery(
            candidato_id=candidato_id,
            requesting_user_id=candidato_id,
            requesting_user_role="candidate",
        )
    )
    assert len(results) == 1


@pytest.mark.asyncio
async def test_listar_postulaciones_candidato_ajeno_raises(postulaciones_repo, candidato_id):
    use_case = ListarPostulacionesCandidatoUseCase(postulaciones_repo)
    with pytest.raises(PermissionDeniedError):
        await use_case.execute(
            ListarPostulacionesCandidatoQuery(
                candidato_id=candidato_id,
                requesting_user_id=uuid.uuid4(),  # otro candidato
                requesting_user_role="candidate",
            )
        )
