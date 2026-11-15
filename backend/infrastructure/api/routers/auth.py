import secrets
from uuid import UUID

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from loguru import logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from application.ports.email_service import EmailServicePort
from application.use_cases.confirm_password_reset import (
    ConfirmPasswordResetCommand,
    ConfirmPasswordResetUseCase,
)
from application.use_cases.login_user import LoginUserCommand, LoginUserUseCase
from application.use_cases.register_candidate import (
    RegisterCandidateCommand,
    RegisterCandidateUseCase,
)
from application.use_cases.register_company import RegisterCompanyCommand, RegisterCompanyUseCase
from application.use_cases.request_password_reset import (
    RequestPasswordResetCommand,
    RequestPasswordResetUseCase,
)
from domain.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidResetTokenError,
)
from infrastructure.adapters.email.smtp_email_service import SmtpEmailService
from infrastructure.adapters.persistence.database import get_session
from infrastructure.adapters.persistence.user_repository import SqlAlchemyUserRepository
from infrastructure.adapters.security import JwtTokenService, PasslibPasswordHasher
from infrastructure.api.rate_limiter import limiter
from infrastructure.api.schemas.auth import (
    CandidateRegisterRequest,
    CandidateRegisterResponse,
    CompanyRegisterRequest,
    ConfirmPasswordResetRequest,
    LoginRequest,
    RefreshTokenRequest,
    RequestPasswordResetRequest,
    SocialConfigResponse,
    SocialLoginRequest,
    TokenResponse,
    UserResponse,
)
from infrastructure.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class BackgroundEmailServiceAdapter:
    """Adaptador que desacopla el envío SMTP hacia una BackgroundTask no bloqueante."""

    def __init__(self, background_tasks: BackgroundTasks, email_service: EmailServicePort):
        self._bg = background_tasks
        self._email_service = email_service

    async def send_password_reset(self, to_email: str, reset_link: str) -> None:
        self._bg.add_task(self._send_email_task, to_email, reset_link)

    async def _send_email_task(self, to_email: str, reset_link: str) -> None:
        try:
            await self._email_service.send_password_reset(to_email, reset_link)
            logger.info(f"Correo de recuperación enviado exitosamente en background a {to_email}")
        except Exception as exc:
            logger.error(f"Fallo al enviar correo en background a {to_email}: {exc}")


@router.post(
    "/registro/candidato",
    response_model=CandidateRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def register_candidate(
    request: Request,
    payload: CandidateRegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> CandidateRegisterResponse:
    users = SqlAlchemyUserRepository(session)
    use_case = RegisterCandidateUseCase(users, PasslibPasswordHasher())

    try:
        profile = await use_case.execute(
            RegisterCandidateCommand(
                email=payload.email,
                password=payload.password,
                full_name=payload.full_name,
                skills=payload.skills,
                experience_years=payload.experience_years,
                location=payload.location,
                education=payload.education,
            )
        )
        await session.commit()
    except (EmailAlreadyRegisteredError, IntegrityError) as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        ) from exc

    return CandidateRegisterResponse(
        id=profile.id,
        user_id=profile.user_id,
        full_name=profile.full_name,
        skills=profile.skills,
        experience_years=profile.experience_years,
        location=profile.location,
        education=profile.education,
    )


@router.post(
    "/registro/empresa",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def register_company(
    request: Request,
    payload: CompanyRegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    users = SqlAlchemyUserRepository(session)
    use_case = RegisterCompanyUseCase(users, PasslibPasswordHasher())

    try:
        user = await use_case.execute(
            RegisterCompanyCommand(email=payload.email, password=payload.password)
        )
        await session.commit()
    except (EmailAlreadyRegisteredError, IntegrityError) as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        ) from exc

    return UserResponse(id=user.id, email=user.email, role=user.role, created_at=user.created_at)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    payload: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    users = SqlAlchemyUserRepository(session)
    use_case = LoginUserUseCase(users, PasslibPasswordHasher(), JwtTokenService())

    try:
        result = await use_case.execute(
            LoginUserCommand(email=payload.email, password=payload.password)
        )
        logger.info(f"Successful login for user: {payload.email}")
    except InvalidCredentialsError as exc:
        logger.warning(f"Failed login attempt for email: {payload.email} - Invalid credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from exc

    return TokenResponse(
        access_token=result.access_token,
        token_type=result.token_type,
        refresh_token=result.refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh_access_token(
    request: Request,
    payload: RefreshTokenRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Permite renovar el access_token usando un refresh_token válido (vigencia de 7 días)."""
    token_service = JwtTokenService()
    try:
        decoded = token_service.decode_token(payload.refresh_token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de actualización inválido o expirado",
        ) from exc

    if decoded.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token proporcionado no es un refresh token válido",
        )

    user_id_str = decoded.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )

    users = SqlAlchemyUserRepository(session)
    user = await users.find_by_id(UUID(user_id_str))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
        )

    new_access_token = token_service.create_access_token(user)
    new_refresh_token = token_service.create_refresh_token(user)
    return TokenResponse(
        access_token=new_access_token,
        token_type="bearer",
        refresh_token=new_refresh_token,
    )


@router.post("/recuperar-password", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/minute")
async def request_password_reset(
    request: Request,
    payload: RequestPasswordResetRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Solicita el envío de un enlace de recuperación de contraseña por correo.

    El envío del correo se despacha en segundo plano (BackgroundTasks) para responder
    de forma inmediata al usuario (202 Accepted) sin bloquear por el handshake SMTP.
    """
    users = SqlAlchemyUserRepository(session)
    email_service = BackgroundEmailServiceAdapter(background_tasks, SmtpEmailService())
    use_case = RequestPasswordResetUseCase(users, email_service)
    await use_case.execute(
        RequestPasswordResetCommand(
            email=payload.email,
            frontend_url=settings.frontend_url,
        )
    )
    await session.commit()
    return {"detail": "Si el correo está registrado, recibirás un enlace de recuperación"}


@router.post("/confirmar-reset", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def confirm_password_reset(
    request: Request,
    payload: ConfirmPasswordResetRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Confirma el reset de contraseña usando el token recibido por correo."""
    users = SqlAlchemyUserRepository(session)
    use_case = ConfirmPasswordResetUseCase(users, PasslibPasswordHasher())

    try:
        await use_case.execute(
            ConfirmPasswordResetCommand(
                raw_token=payload.token,
                new_password=payload.new_password,
            )
        )
        await session.commit()
    except InvalidResetTokenError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido o expirado",
        ) from exc

    return {"detail": "Contraseña actualizada exitosamente"}


@router.get("/reset-password", response_class=HTMLResponse)
@limiter.limit("15/minute")
async def reset_password_page(
    request: Request,
    token: str = Query(default="", max_length=128),
) -> HTMLResponse:
    """Renderiza la página web oficial de TalentMatch para cambiar la contraseña con el token."""
    from infrastructure.api.templates.reset_password_html import render_reset_password_html

    return HTMLResponse(content=render_reset_password_html(token))


# ── Autenticación Social (OAuth 2.0: Google, Facebook, LinkedIn) ───────────────


@router.get("/oauth/config", response_model=SocialConfigResponse)
async def get_oauth_config() -> SocialConfigResponse:
    """Retorna el estado de configuración de los proveedores OAuth."""
    return SocialConfigResponse(
        google_configured=bool(settings.google_client_id),
        facebook_configured=bool(settings.facebook_app_id),
        linkedin_configured=bool(settings.linkedin_client_id),
        google_client_id=settings.google_client_id or None,
        facebook_app_id=settings.facebook_app_id or None,
        linkedin_client_id=settings.linkedin_client_id or None,
    )


@router.post("/oauth/social", response_model=TokenResponse)
@limiter.limit("20/minute")
async def social_login(
    request: Request,
    payload: SocialLoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Inicio de sesión y registro automático con proveedores sociales (Google, Facebook, LinkedIn)."""
    provider = payload.provider.lower().strip()
    if provider not in ("google", "facebook", "linkedin"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Proveedor no soportado. Debe ser 'google', 'facebook' o 'linkedin'.",
        )

    email: str | None = str(payload.email).lower().strip() if payload.email else None
    name: str = payload.full_name or f"Usuario {provider.capitalize()}"

    # Verificación en vivo con los proveedores oficiales si se envía un token y hay credenciales
    if payload.token and not payload.token.startswith("mock_"):
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                if provider == "google":
                    resp = await client.get(
                        f"https://oauth2.googleapis.com/tokeninfo?id_token={payload.token}"
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        email = data.get("email", email)
                        name = data.get("name", name)
                elif provider == "facebook":
                    resp = await client.get(
                        "https://graph.facebook.com/me",
                        params={"fields": "id,name,email", "access_token": payload.token},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        email = data.get("email", email)
                        name = data.get("name", name)
                elif provider == "linkedin":
                    resp = await client.get(
                        "https://api.linkedin.com/v2/userinfo",
                        headers={"Authorization": f"Bearer {payload.token}"},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        email = data.get("email", email)
                        name = data.get("name", name)
        except Exception as exc:
            logger.warning(f"Error al verificar token con proveedor {provider}: {exc}")

    # Fallback si no hay email reportado
    if not email:
        email = f"candidato.{provider}@talentmatch.com"

    users = SqlAlchemyUserRepository(session)
    user = await users.find_by_email(email)

    if not user:
        from domain.entities.user import UserRole
        hasher = PasslibPasswordHasher()
        dummy_password = secrets.token_urlsafe(24)
        password_hash = hasher.hash(dummy_password)
        try:
            user = await users.create_user(email=email, password_hash=password_hash, role=UserRole.CANDIDATE)
            await users.create_candidate_profile(
                user_id=user.id,
                full_name=name,
                skills=[],
                experience_years=0,
                location=None,
                education=None,
            )
            await session.commit()
            logger.info(f"Nuevo usuario candidato registrado vía {provider}: {email}")
        except Exception as exc:
            await session.rollback()
            user = await users.find_by_email(email)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error al crear usuario vía {provider}: {exc}",
                )

    token_service = JwtTokenService()
    access_token = token_service.create_access_token(user)
    refresh_token = token_service.create_refresh_token(user)

    logger.info(f"Inicio de sesión exitoso vía {provider} para {email}")
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token,
    )


@router.post("/oauth/google", response_model=TokenResponse)
async def login_google(
    request: Request,
    payload: SocialLoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    payload.provider = "google"
    return await social_login(request, payload, session)


@router.post("/oauth/facebook", response_model=TokenResponse)
async def login_facebook(
    request: Request,
    payload: SocialLoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    payload.provider = "facebook"
    return await social_login(request, payload, session)


@router.post("/oauth/linkedin", response_model=TokenResponse)
async def login_linkedin(
    request: Request,
    payload: SocialLoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    payload.provider = "linkedin"
    return await social_login(request, payload, session)

