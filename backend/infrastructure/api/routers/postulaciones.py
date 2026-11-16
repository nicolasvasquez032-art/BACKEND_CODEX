import math
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from application.use_cases.cambiar_estado_postulacion import (
    CambiarEstadoPostulacionCommand,
    CambiarEstadoPostulacionUseCase,
)
from application.use_cases.listar_postulaciones import (
    ListarPostulacionesCandidatoQuery,
    ListarPostulacionesCandidatoUseCase,
    ListarPostulacionesVacanteQuery,
    ListarPostulacionesVacanteUseCase,
)
from application.use_cases.postularse_a_vacante import (
    PostularseAVacanteCommand,
    PostularseAVacanteUseCase,
)
from domain.entities.postulacion import PostulacionEstado
from domain.entities.user import User, UserRole
from domain.exceptions import (
    DuplicatePostulacionError,
    InvalidEstadoTransitionError,
    PermissionDeniedError,
    PostulacionNotFoundError,
    VacanteNotFoundError,
)
from infrastructure.adapters.persistence.database import get_session
from infrastructure.adapters.persistence.models import (
    CandidateProfileModel,
    ChatRoomModel,
    MessageModel,
    PostulacionModel,
    UserModel,
    VacanteModel,
)
from infrastructure.adapters.persistence.postulacion_repository import (
    SqlAlchemyPostulacionRepository,
)
from infrastructure.adapters.persistence.user_repository import SqlAlchemyUserRepository
from infrastructure.adapters.persistence.vacante_repository import SqlAlchemyVacanteRepository
from infrastructure.api.dependencies import get_current_user, require_role
from infrastructure.api.websockets_manager import manager
from infrastructure.api.schemas.postulaciones import (
    CambiarEstadoPostulacionRequest,
    PostulacionResponse,
    PostularseRequest,
)

router = APIRouter(prefix="/postulaciones", tags=["postulaciones"])


def _to_response(p) -> PostulacionResponse:
    score = p.score_match
    if score is not None and score <= 1.0:
        score = round(score * 100, 1)
    return PostulacionResponse(
        id=p.id,
        candidato_id=p.candidato_id,
        vacante_id=p.vacante_id,
        estado=p.estado,
        fecha=p.fecha,
        score_match=score,
    )


@router.post("", response_model=PostulacionResponse, status_code=status.HTTP_201_CREATED)
async def postularse(
    request: PostularseRequest,
    current_user: User = Depends(require_role(UserRole.CANDIDATE)),
    session: AsyncSession = Depends(get_session),
) -> PostulacionResponse:
    """Postula un candidato a una vacante activa (RF-03.1 y RF-03.2).

    El candidato_id se resuelve desde el JWT — el body solo necesita vacante_id.
    """
    # Resolver el profile_id del candidato autenticado desde la BD
    user_repo = SqlAlchemyUserRepository(session)
    profile = await user_repo.get_candidate_profile_by_user_id(current_user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil de candidato no encontrado para el usuario autenticado",
        )

    # Validar que el candidato haya subido su hoja de vida (CV) antes de postularse
    has_cv = bool(
        (getattr(profile, "cv_file_url", None) and str(profile.cv_file_url).strip())
        or (getattr(profile, "cv_text", None) and str(profile.cv_text).strip())
    )
    if not has_cv:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes subir tu hoja de vida (CV) antes de postularte a una vacante.",
        )

    postulaciones_repo = SqlAlchemyPostulacionRepository(session)
    vacantes_repo = SqlAlchemyVacanteRepository(session)
    use_case = PostularseAVacanteUseCase(postulaciones_repo, vacantes_repo)

    try:
        postulacion = await use_case.execute(
            PostularseAVacanteCommand(
                candidato_id=profile.id,   # ← siempre del JWT, nunca del body
                vacante_id=request.vacante_id,
            )
        )
        await session.commit()
    except VacanteNotFoundError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except DuplicatePostulacionError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una postulación para esta vacante",
        )
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una postulación para esta vacante",
        )
    except SQLAlchemyError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al guardar la postulación",
        ) from exc

    resp = _to_response(postulacion)
    vacante_model = await session.get(VacanteModel, postulacion.vacante_id)
    if vacante_model:
        resp.vacante_titulo = vacante_model.titulo
        resp.vacante_ubicacion = vacante_model.ubicacion
        resp.vacante_categoria = vacante_model.categoria
        resp.vacante_salario_min = vacante_model.salario_min
        resp.vacante_salario_max = vacante_model.salario_max
        resp.vacante_descripcion = vacante_model.descripcion
        resp.vacante_requisitos = vacante_model.requisitos
        empresa_user = await session.get(UserModel, vacante_model.empresa_id)
        if empresa_user:
            resp.empresa_nombre = empresa_user.email.split("@")[0].capitalize()
    return resp


@router.get("/me", response_model=list[PostulacionResponse])
async def listar_mis_postulaciones(
    current_user: User = Depends(require_role(UserRole.CANDIDATE)),
    session: AsyncSession = Depends(get_session),
) -> list[PostulacionResponse]:
    """Retorna el historial de postulaciones del candidato autenticado vía JWT."""
    user_repo = SqlAlchemyUserRepository(session)
    profile = await user_repo.get_candidate_profile_by_user_id(current_user.id)
    if not profile:
        return []
    return await listar_postulaciones_candidato(profile.id, current_user, session)


@router.get("/candidato/{candidato_id}", response_model=list[PostulacionResponse])
async def listar_postulaciones_candidato(
    candidato_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[PostulacionResponse]:
    """Retorna el historial de postulaciones de un candidato (RF-03.4).

    Resuelve dinámicamente si el ID provisto es un profile_id o un user_id.
    """
    user_repo = SqlAlchemyUserRepository(session)
    profile = await user_repo.get_candidate_profile_by_id(candidato_id)
    if profile is None:
        profile = await user_repo.get_candidate_profile_by_user_id(candidato_id)

    target_profile_id = profile.id if profile else candidato_id

    repo = SqlAlchemyPostulacionRepository(session)
    use_case = ListarPostulacionesCandidatoUseCase(repo)

    try:
        postulaciones = await use_case.execute(
            ListarPostulacionesCandidatoQuery(
                candidato_id=target_profile_id,
                requesting_user_id=current_user.id,
                requesting_user_role=current_user.role.value,
            )
        )
    except PermissionDeniedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    responses: list[PostulacionResponse] = []
    for p in postulaciones:
        resp = _to_response(p)
        vacante_model = await session.get(VacanteModel, p.vacante_id)
        if vacante_model:
            resp.vacante_titulo = vacante_model.titulo
            resp.vacante_ubicacion = vacante_model.ubicacion
            resp.vacante_categoria = vacante_model.categoria
            resp.vacante_salario_min = vacante_model.salario_min
            resp.vacante_salario_max = vacante_model.salario_max
            resp.vacante_descripcion = vacante_model.descripcion
            resp.vacante_requisitos = vacante_model.requisitos
            empresa_user = await session.get(UserModel, vacante_model.empresa_id)
            if empresa_user:
                resp.empresa_nombre = empresa_user.email.split("@")[0].capitalize()
        responses.append(resp)

    return responses


@router.get("/vacante/{vacante_id}", response_model=list[PostulacionResponse])
async def listar_postulaciones_vacante(
    vacante_id: UUID,
    current_user: User = Depends(require_role(UserRole.COMPANY)),
    session: AsyncSession = Depends(get_session),
) -> list[PostulacionResponse]:
    """Retorna las postulaciones de una vacante para el kanban de la empresa (RF-03.3)."""
    postulaciones_repo = SqlAlchemyPostulacionRepository(session)
    vacantes_repo = SqlAlchemyVacanteRepository(session)
    use_case = ListarPostulacionesVacanteUseCase(postulaciones_repo, vacantes_repo)

    try:
        postulaciones = await use_case.execute(
            ListarPostulacionesVacanteQuery(
                vacante_id=vacante_id,
                requesting_empresa_id=current_user.id,
            )
        )
    except VacanteNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacante no encontrada")
    except PermissionDeniedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    vacante_model = await session.get(VacanteModel, vacante_id)
    needs_commit = False

    responses: list[PostulacionResponse] = []
    for p in postulaciones:
        resp = _to_response(p)
        cand_prof = await session.get(CandidateProfileModel, p.candidato_id)
        if cand_prof:
            resp.candidato_nombre = cand_prof.full_name
            resp.candidato_job_title = cand_prof.job_title
            resp.candidato_skills = cand_prof.skills
            resp.candidato_experience_years = cand_prof.experience_years
            resp.candidato_location = cand_prof.location
            resp.candidato_phone = cand_prof.phone
            resp.candidato_user_id = cand_prof.user_id
            cand_user = await session.get(UserModel, cand_prof.user_id)
            if cand_user:
                resp.candidato_email = cand_user.email

            # Calcular score_match dinámico si no está persistido
            if resp.score_match is None and vacante_model:
                calculated_score = None
                # 1. Similitud semántica si ambos tienen embeddings
                if cand_prof.embedding is not None and vacante_model.embedding is not None:
                    try:
                        emb_c = list(cand_prof.embedding)
                        emb_v = list(vacante_model.embedding)
                        dot = sum(x * y for x, y in zip(emb_c, emb_v))
                        norm_c = math.sqrt(sum(x * x for x in emb_c))
                        norm_v = math.sqrt(sum(y * y for y in emb_v))
                        if norm_c > 0 and norm_v > 0:
                            sim = dot / (norm_c * norm_v)
                            calculated_score = round(max(50.0, min(99.0, (sim + 0.2) * 70.0)), 1)
                    except Exception:
                        pass

                # 2. Afinidad por habilidades y requisitos
                if calculated_score is None:
                    cand_has_cv = bool(
                        (cand_prof.cv_file_url and str(cand_prof.cv_file_url).strip())
                        or (cand_prof.cv_text and str(cand_prof.cv_text).strip())
                    )
                    if cand_has_cv:
                        cand_skills = {s.lower().strip() for s in (cand_prof.skills or []) if s.strip()}
                        vac_reqs = {r.lower().strip() for r in (vacante_model.requisitos or []) if r.strip()}
                        title_desc = f"{vacante_model.titulo} {vacante_model.descripcion}".lower()
                        matches = {s for s in cand_skills if s in vac_reqs or s in title_desc}
                        if matches:
                            calculated_score = round(min(98.0, max(65.0, 65.0 + 8.0 * len(matches))), 1)
                        else:
                            calculated_score = 50.0
                    else:
                        calculated_score = None

                resp.score_match = calculated_score

                # Persistir en la base de datos si hay cálculo real
                if calculated_score is not None:
                    post_model = await session.get(PostulacionModel, p.id)
                    if post_model:
                        post_model.score_match = calculated_score / 100.0
                        needs_commit = True

        responses.append(resp)

    if needs_commit:
        try:
            await session.commit()
        except Exception:
            await session.rollback()

    return responses


@router.patch("/{postulacion_id}/estado", response_model=PostulacionResponse)
async def cambiar_estado_postulacion(
    postulacion_id: UUID,
    request: CambiarEstadoPostulacionRequest,
    current_user: User = Depends(require_role(UserRole.COMPANY)),
    session: AsyncSession = Depends(get_session),
) -> PostulacionResponse:
    """Avanza el estado de una postulación en el kanban (RF-03.3)."""
    postulaciones_repo = SqlAlchemyPostulacionRepository(session)
    vacantes_repo = SqlAlchemyVacanteRepository(session)
    use_case = CambiarEstadoPostulacionUseCase(postulaciones_repo, vacantes_repo)

    try:
        postulacion = await use_case.execute(
            CambiarEstadoPostulacionCommand(
                postulacion_id=postulacion_id,
                requesting_empresa_id=current_user.id,
                nuevo_estado=request.estado,
            )
        )
        await session.commit()
    except PostulacionNotFoundError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Postulación no encontrada"
        )
    except VacanteNotFoundError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacante no encontrada")
    except PermissionDeniedError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    except InvalidEstadoTransitionError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except SQLAlchemyError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar el estado",
        ) from exc

    return _to_response(postulacion)


@router.delete("/{postulacion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_postulacion(
    postulacion_id: UUID,
    current_user: User = Depends(require_role(UserRole.CANDIDATE)),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Elimina una postulación (retirarse de una vacante).

    Solo el candidato dueño de la postulación puede eliminarla.
    """
    repo = SqlAlchemyPostulacionRepository(session)
    postulacion = await repo.find_by_id(postulacion_id)
    if not postulacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Postulación no encontrada"
        )

    # Verificar que el candidato autenticado es el dueño de la postulación
    user_repo = SqlAlchemyUserRepository(session)
    profile = await user_repo.get_candidate_profile_by_user_id(current_user.id)
    if profile is None or postulacion.candidato_id != profile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el candidato dueño puede retirar esta postulación",
        )

    await repo.delete(postulacion_id)
    await session.commit()


@router.post("/{postulacion_id}/entrevista")
async def iniciar_entrevista_postulacion(
    postulacion_id: UUID,
    current_user: User = Depends(require_role(UserRole.COMPANY)),
    session: AsyncSession = Depends(get_session),
):
    """Inicia o agenda una entrevista por videollamada para una postulación.

    Actualiza el estado de la postulación a 'entrevista', genera una sala
    segura y única de videoconferencia (Jitsi Meet) y notifica al candidato
    a través del chat en tiempo real.
    """
    postulaciones_repo = SqlAlchemyPostulacionRepository(session)
    postulacion = await postulaciones_repo.find_by_id(postulacion_id)
    if not postulacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Postulación no encontrada"
        )

    vacantes_repo = SqlAlchemyVacanteRepository(session)
    vacante = await vacantes_repo.find_by_id(postulacion.vacante_id)
    if not vacante or vacante.empresa_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo la empresa propietaria de la vacante puede agendar entrevistas",
        )

    # Avanzar estado en el Kanban a ENTREVISTA si aún está en postulado
    if postulacion.estado == PostulacionEstado.POSTULADO:
        try:
            use_case = CambiarEstadoPostulacionUseCase(postulaciones_repo, vacantes_repo)
            await use_case.execute(
                CambiarEstadoPostulacionCommand(
                    postulacion_id=postulacion_id,
                    requesting_empresa_id=current_user.id,
                    nuevo_estado=PostulacionEstado.ENTREVISTA,
                )
            )
        except Exception:
            postulacion.estado = PostulacionEstado.ENTREVISTA

    # Generar sala única de Jitsi Meet
    call_code = uuid.uuid4().hex[:10]
    room_name = f"TalentMatch-Entrevista-{call_code}"
    meeting_url = f"https://meet.jit.si/{room_name}#config.prejoinPageEnabled=false"

    # Encontrar o crear la sala de chat entre empresa y candidato
    cand_profile_res = await session.execute(
        select(CandidateProfileModel).where(CandidateProfileModel.id == postulacion.candidato_id)
    )
    cand_profile = cand_profile_res.scalar_one_or_none()
    cand_user_id = cand_profile.user_id if cand_profile else None

    chat_room_id = None
    if cand_user_id:
        room_res = await session.execute(
            select(ChatRoomModel).where(
                ChatRoomModel.empresa_id == current_user.id,
                ChatRoomModel.candidato_id == cand_user_id,
            )
        )
        chat_room = room_res.scalar_one_or_none()
        if not chat_room:
            chat_room = ChatRoomModel(
                empresa_id=current_user.id,
                candidato_id=cand_user_id,
            )
            session.add(chat_room)
            await session.commit()
            await session.refresh(chat_room)

        chat_room_id = str(chat_room.id)

        # Enviar tarjeta interactiva de videollamada al chat
        content = f"[VIDEOCALL]:{meeting_url}|Entrevista para vacante: {vacante.titulo}"
        msg = MessageModel(
            room_id=chat_room.id,
            sender_id=current_user.id,
            content=content,
        )
        session.add(msg)

        # Registrar notificación interna para el candidato
        try:
            from infrastructure.adapters.persistence.models import NotificacionModel
            notif = NotificacionModel(
                usuario_id=cand_user_id,
                tipo="entrevista",
                mensaje=f"📹 La empresa te ha convocado a una entrevista para: {vacante.titulo}",
                leido=False,
            )
            session.add(notif)
        except Exception:
            pass

        await session.commit()
        await session.refresh(msg)

        msg_payload = {
            "id": str(msg.id),
            "room_id": str(msg.room_id),
            "sender_id": str(msg.sender_id),
            "content": msg.content,
            "creado_en": str(msg.creado_en),
            "leido": msg.leido,
        }
        await manager.send_personal_message(msg_payload, cand_user_id)
        await manager.send_personal_message(msg_payload, current_user.id)

        # Enviar notificación Push vía Firebase Cloud Messaging (FCM)
        try:
            from infrastructure.adapters.fcm_adapter import RealFcmAdapter
            from infrastructure.adapters.persistence.models import DeviceTokenModel
            fcm = RealFcmAdapter()
            tokens_res = await session.execute(
                select(DeviceTokenModel.token).where(DeviceTokenModel.usuario_id == cand_user_id)
            )
            candidate_tokens = tokens_res.scalars().all()
            for dev_token in candidate_tokens:
                await fcm.send_notification(
                    token=dev_token,
                    title="📹 ¡Nueva Entrevista de Trabajo!",
                    body=f"Has sido seleccionado para entrevista en: {vacante.titulo}",
                    data={
                        "tipo": "videollamada",
                        "meeting_url": meeting_url,
                        "chat_room_id": str(chat_room_id),
                    },
                )
        except Exception as e:
            logger.warning(f"[FCM] Error enviando push de entrevista: {e}")
    else:
        await session.commit()

    return {
        "status": "success",
        "meeting_url": meeting_url,
        "room_name": room_name,
        "postulacion_id": str(postulacion_id),
        "estado": "entrevista",
        "chat_room_id": chat_room_id,
        "vacante_titulo": vacante.titulo,
    }

