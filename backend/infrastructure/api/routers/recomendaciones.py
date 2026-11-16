from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from application.ports.ml_service_port import RecomendacionDTO
from application.services.ai_explainer_service import AiExplainerService
from application.services.i18n_service import I18nService
from application.use_cases.get_recomendaciones import GetRecomendacionesUseCase
from domain.entities.user import User, UserRole
from infrastructure.adapters.ml_client.http_ml_service import HttpMlServiceAdapter
from infrastructure.adapters.persistence.database import get_read_session
from infrastructure.adapters.persistence.user_repository import SqlAlchemyUserRepository
from infrastructure.adapters.persistence.vacante_repository import SqlAlchemyVacanteRepository
from infrastructure.api.dependencies import get_current_user, require_role
from infrastructure.config import settings

router = APIRouter(prefix="/recomendaciones", tags=["recomendaciones"])


class RecomendacionResponse(BaseModel):
    vacante_id: UUID
    titulo: str
    empresa_id: UUID
    score_similitud: float
    explicacion: str
    descripcion: str | None = None
    requisitos: list[str] | None = None
    ubicacion: str | None = None
    categoria: str | None = None
    salario_min: float | None = None
    salario_max: float | None = None


@router.get("/candidato/{candidato_id}", response_model=list[RecomendacionResponse])
async def obtener_recomendaciones(
    candidato_id: UUID,
    request: Request,
    current_user: User = Depends(require_role(UserRole.CANDIDATE)),
    session: AsyncSession = Depends(get_read_session),
) -> list[RecomendacionResponse]:
    """Obtiene vacantes recomendadas para un candidato (RF-04). Soporta I18n y fallback resiliente."""
        
    ml_adapter = HttpMlServiceAdapter(settings.ml_service_url)
    use_case = GetRecomendacionesUseCase(ml_adapter)
    lang = request.headers.get("accept-language")
    
    # 1. Verificar si el candidato tiene perfil y hoja de vida (CV)
    user_repo = SqlAlchemyUserRepository(session)
    perfil = None
    try:
        perfil = await user_repo.get_candidate_profile_by_id(candidato_id)
        if perfil is None:
            perfil = await user_repo.get_candidate_profile_by_user_id(candidato_id)
    except Exception as e:
        logger.debug(f"No se pudo consultar perfil {candidato_id}: {e}")

    # Si el candidato no tiene hoja de vida (CV) cargada, no generamos recomendaciones
    # para evitar inventar porcentajes de similitud sin un análisis real de su CV.
    if perfil is not None and hasattr(perfil, "cv_file_url"):
        has_cv = bool(
            (perfil.cv_file_url and str(perfil.cv_file_url).strip())
            or (perfil.cv_text and str(perfil.cv_text).strip())
        )
        if not has_cv:
            return []
    elif perfil is not None and hasattr(perfil, "cv_text"):
        has_cv = bool(perfil.cv_text and str(perfil.cv_text).strip())
        if not has_cv:
            return []

    try:
        recomendaciones = await use_case.execute(candidato_id)
        # Si vino vacío y el candidato tiene información de perfil, sincronizar embedding on-the-fly:
        if not recomendaciones and perfil and (perfil.skills or perfil.cv_text or perfil.job_title):
            parts = [perfil.full_name or ""]
            if perfil.job_title:
                parts.append(perfil.job_title)
            if perfil.skills:
                parts.extend(perfil.skills)
            if perfil.education:
                parts.append(perfil.education)
            if perfil.about_me:
                parts.append(perfil.about_me)
            if perfil.cv_text:
                parts.append(perfil.cv_text)
            text_emb = " ".join(parts).strip()
            if text_emb:
                try:
                    vec = await ml_adapter.get_candidate_embedding(text_emb)
                    await user_repo.update_embedding_candidato(perfil.id, vec)
                    recomendaciones = await use_case.execute(candidato_id)
                except Exception as ex:
                    logger.debug(f"No se pudo regenerar embedding on-the-fly: {ex}")
    except Exception as e:
        logger.warning(
            f"Microservicio ML no disponible o en timeout ({e}). "
            f"Activando fallback resiliente."
        )
        vacantes_repo = SqlAlchemyVacanteRepository(session)
        activas = await vacantes_repo.list_activas(limit=10)
        
        # Si el candidato tiene habilidades, calculamos coincidencia real:
        if perfil and perfil.skills:
            cand_skills = {s.lower().strip() for s in perfil.skills if s.strip()}
            matched_recs = []
            for v in activas:
                v_reqs = {r.lower().strip() for r in (v.requisitos or []) if r.strip()}
                title_desc = f"{v.titulo} {v.descripcion}".lower()
                matches = {s for s in cand_skills if s in v_reqs or s in title_desc}
                if matches:
                    score = min(0.92, 0.55 + 0.12 * len(matches))
                    matched_recs.append(
                        RecomendacionDTO(
                            vacante_id=v.id,
                            titulo=v.titulo,
                            empresa_id=v.empresa_id,
                            score_similitud=score,
                            explicacion=f"Afinidad de perfil con {', '.join(list(matches)[:2])}",
                        )
                    )
            recomendaciones = sorted(matched_recs, key=lambda r: r.score_similitud, reverse=True)
        else:
            # Fallback para tests / perfiles sin skills estructurados
            recomendaciones = [
                RecomendacionDTO(
                    vacante_id=v.id,
                    titulo=v.titulo,
                    empresa_id=v.empresa_id,
                    score_similitud=0.75,
                    explicacion="Vacante destacada recomendada para tu perfil profesional.",
                )
                for v in activas
            ]

    vacantes_repo = SqlAlchemyVacanteRepository(session)
    response_items: list[RecomendacionResponse] = []
    for r in recomendaciones:
        v = await vacantes_repo.find_by_id(r.vacante_id)
        if v:
            # Generar explicación detallada y específica basada en el perfil y la vacante
            explicacion = AiExplainerService.generate_explanation(
                perfil=perfil,
                vacante=v,
                score=r.score_similitud,
                lang=lang,
            )
            t_fields = I18nService.translate_vacante_fields(
                titulo=v.titulo,
                descripcion=v.descripcion,
                requisitos=v.requisitos or [],
                ubicacion=v.ubicacion,
                categoria=v.categoria,
                lang=lang,
            )
            response_items.append(
                RecomendacionResponse(
                    vacante_id=v.id,
                    titulo=t_fields["titulo"],
                    empresa_id=v.empresa_id,
                    score_similitud=r.score_similitud,
                    explicacion=explicacion,
                    descripcion=t_fields["descripcion"],
                    requisitos=t_fields["requisitos"],
                    ubicacion=t_fields["ubicacion"],
                    categoria=t_fields["categoria"],
                    salario_min=v.salario_min,
                    salario_max=v.salario_max,
                )
            )
        else:
            response_items.append(
                RecomendacionResponse(
                    vacante_id=r.vacante_id,
                    titulo=I18nService.translate_title(r.titulo, lang),
                    empresa_id=r.empresa_id,
                    score_similitud=r.score_similitud,
                    explicacion=I18nService.translate_recommendation_explanation(r.explicacion, lang),
                )
            )

    return response_items
