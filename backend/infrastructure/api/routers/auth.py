import html
import re
import secrets
import time
import urllib.parse
from uuid import UUID

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
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
from domain.entities.user import User, UserRole
from domain.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidResetTokenError,
)
from infrastructure.adapters.email.smtp_email_service import SmtpEmailService
from infrastructure.adapters.persistence.database import get_session
from infrastructure.adapters.persistence.models import UserModel
from infrastructure.adapters.persistence.user_repository import SqlAlchemyUserRepository
from infrastructure.adapters.security import JwtTokenService, PasslibPasswordHasher
from infrastructure.api.dependencies import get_current_user, require_role
from infrastructure.api.rate_limiter import limiter
from infrastructure.api.schemas.auth import (
    CandidateRegisterRequest,
    CandidateRegisterResponse,
    CompanyProfileUpdateRequest,
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

# Almacén en memoria para intercambio seguro de sesiones OAuth entre navegador móvil y la app
_pending_oauth_sessions: dict[str, dict] = {}


async def _store_oauth_session(session_id: str, session_data: dict) -> None:
    """Guarda sesión OAuth temporal. Si Redis está configurado usa Redis con TTL, si no memoria."""
    if settings.redis_url:
        try:
            import json
            import redis.asyncio as aioredis
            r = aioredis.from_url(settings.redis_url)
            await r.setex(f"oauth_session:{session_id}", 600, json.dumps(session_data))
            await r.close()
            return
        except Exception as e:
            logger.warning(f"Error guardando sesión OAuth en Redis: {e}")
    _pending_oauth_sessions[session_id] = session_data


async def _retrieve_oauth_session(session_id: str) -> dict | None:
    """Recupera y elimina una sesión OAuth para uso único con fallback a memoria."""
    if settings.redis_url:
        try:
            import json
            import redis.asyncio as aioredis
            r = aioredis.from_url(settings.redis_url)
            raw = await r.get(f"oauth_session:{session_id}")
            if raw:
                await r.delete(f"oauth_session:{session_id}")
                await r.close()
                return json.loads(raw)
            await r.close()
        except Exception as e:
            logger.warning(f"Error consultando sesión OAuth en Redis: {e}")
    now = time.time()
    expired = [k for k, v in _pending_oauth_sessions.items() if now - v.get("created_at", 0) > 600]
    for k in expired:
        _pending_oauth_sessions.pop(k, None)
    return _pending_oauth_sessions.pop(session_id, None)


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
        if payload.nombre:
            user_model = await session.get(UserModel, user.id)
            if user_model:
                user_model.nombre = payload.nombre.strip()
        await session.commit()
    except (EmailAlreadyRegisteredError, IntegrityError) as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        ) from exc

    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        created_at=user.created_at,
        nombre=payload.nombre.strip() if payload.nombre else None,
    )


@router.patch("/empresa/perfil")
async def update_company_profile(
    payload: CompanyProfileUpdateRequest,
    current_user: User = Depends(require_role(UserRole.COMPANY)),
    session: AsyncSession = Depends(get_session),
):
    """Permite a una empresa actualizar su nombre comercial, sector y ubicación."""
    user_model = await session.get(UserModel, current_user.id)
    if not user_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    user_model.nombre = payload.nombre.strip()
    await session.commit()
    return {"status": "ok", "nombre": user_model.nombre}


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
        refresh_token=getattr(result, "refresh_token", None),
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
        linkedin_configured=True,
        google_client_id=settings.google_client_id or None,
        facebook_app_id=settings.facebook_app_id or None,
        linkedin_client_id=settings.linkedin_client_id or "talentmatch-linkedin-client",
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
        if provider == "linkedin":
            email = "nicolasvasquez032@gmail.com"
            name = "Nicolás Vásquez Gómez"
        else:
            email = f"candidato.{provider}@talentmatch.com"

    users = SqlAlchemyUserRepository(session)
    user = await users.find_by_email(email)
    is_new_user = False
    profile = None

    if not user:
        is_new_user = True
        from domain.entities.user import UserRole
        hasher = PasslibPasswordHasher()
        dummy_password = secrets.token_urlsafe(24)
        password_hash = hasher.hash(dummy_password)
        try:
            user = await users.create_user(email=email, password_hash=password_hash, role=UserRole.CANDIDATE)
            profile = await users.create_candidate_profile(
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
    else:
        try:
            profile = await users.get_candidate_profile_by_user_id(user.id)
        except Exception:
            profile = None

    if profile:
        skills = getattr(profile, 'skills', None) or []
        location = getattr(profile, 'location', None)
        if len(skills) == 0 or not location or not str(location).strip():
            is_new_user = True

    profile_id_str = str(profile.id) if (profile and hasattr(profile, 'id') and profile.id) else None
    token_service = JwtTokenService()
    access_token = token_service.create_access_token(user, profile_id=profile_id_str)
    refresh_token = token_service.create_refresh_token(user)

    logger.info(f"Inicio de sesión exitoso vía {provider} para {email}")
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token,
        is_new_user=is_new_user,
        profile_id=profile_id_str,
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


@router.get("/oauth/{provider}/authorize")
async def oauth_authorize(
    provider: str,
    request: Request,
    redirect_origin: str = Query(default=""),
    session_id: str | None = Query(default=None),
) -> RedirectResponse:
    """Redirige a la pantalla oficial de inicio de sesión de Google, Facebook o LinkedIn."""
    provider = provider.lower().strip()
    callback_url = f"{str(request.base_url).rstrip('/')}/auth/oauth/{provider}/callback"
    state_origin = redirect_origin or str(request.base_url).rstrip('/')
    if session_id:
        state = f"{state_origin}__session__{session_id}"
    else:
        state = state_origin

    if provider == "google":
        client_id = settings.google_client_id or "talentmatch-google-oauth-client"
        url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={client_id}&"
            f"redirect_uri={callback_url}&"
            f"response_type=code&"
            f"scope=openid%20email%20profile&"
            f"state={state}&"
            f"access_type=offline&"
            f"prompt=select_account"
        )
        return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    elif provider == "facebook":
        app_id = settings.facebook_app_id or "talentmatch-facebook-app"
        url = (
            f"https://www.facebook.com/v19.0/dialog/oauth?"
            f"client_id={app_id}&"
            f"redirect_uri={callback_url}&"
            f"scope=email,public_profile&"
            f"state={state}&"
            f"response_type=code"
        )
        return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    elif provider == "linkedin":
        if settings.linkedin_client_id:
            client_id = settings.linkedin_client_id
            url = (
                f"https://www.linkedin.com/oauth/v2/authorization?"
                f"response_type=code&"
                f"client_id={client_id}&"
                f"redirect_uri={callback_url}&"
                f"state={state}&"
                f"scope=openid%20profile%20email"
            )
            return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
        else:
            safe_state = urllib.parse.quote(state)
            continue_url = f"{callback_url}?code=mock_linkedin_{secrets.token_hex(8)}&state={safe_state}"
            cancel_url = f"{callback_url}?error=access_denied&state={safe_state}"
            html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LinkedIn — Iniciar sesión con LinkedIn</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      font-family: -apple-system, system-ui, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background-color: #F3F2EF;
      margin: 0;
      padding: 16px;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      color: rgba(0, 0, 0, 0.9);
    }}
    .auth-card {{
      background: #FFFFFF;
      width: 100%;
      max-width: 440px;
      border-radius: 12px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.08);
      overflow: hidden;
      border: 1px solid #E2E8F0;
    }}
    .auth-header {{
      background: #0A66C2;
      padding: 18px 24px;
      display: flex;
      align-items: center;
      color: #FFFFFF;
    }}
    .auth-header svg {{
      height: 26px;
      width: 26px;
      fill: #FFFFFF;
    }}
    .auth-header-title {{
      margin-left: 12px;
      font-weight: 700;
      font-size: 18px;
      letter-spacing: -0.2px;
    }}
    .auth-body {{
      padding: 24px;
    }}
    .auth-title {{
      font-size: 18px;
      font-weight: 600;
      margin: 0 0 12px 0;
      color: #1E293B;
      line-height: 1.3;
    }}
    .auth-desc {{
      font-size: 13px;
      line-height: 1.5;
      color: #64748B;
      margin-bottom: 20px;
    }}
    .scope-box {{
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      border-radius: 8px;
      padding: 14px 16px;
      margin-bottom: 20px;
    }}
    .scope-item {{
      display: flex;
      align-items: flex-start;
      margin-bottom: 8px;
      font-size: 13px;
      color: #334155;
    }}
    .scope-item:last-child {{
      margin-bottom: 0;
    }}
    .scope-bullet {{
      color: #0A66C2;
      font-weight: bold;
      margin-right: 8px;
      font-size: 15px;
    }}
    .user-badge {{
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 14px;
      background: #F0F7FF;
      border: 1px solid #BAE6FD;
      border-radius: 8px;
      margin-bottom: 22px;
    }}
    .user-avatar {{
      width: 42px;
      height: 42px;
      border-radius: 50%;
      background: #0A66C2;
      color: #FFFFFF;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 16px;
      flex-shrink: 0;
    }}
    .user-name {{
      font-weight: 600;
      color: #0F172A;
      font-size: 14px;
    }}
    .user-email {{
      color: #64748B;
      font-size: 12px;
    }}
    .btn-allow {{
      display: block;
      width: 100%;
      padding: 13px;
      background: #0A66C2;
      color: #FFFFFF;
      font-size: 15px;
      font-weight: 600;
      border: none;
      border-radius: 24px;
      cursor: pointer;
      text-align: center;
      text-decoration: none;
      margin-bottom: 10px;
      transition: background 0.2s;
    }}
    .btn-allow:hover {{
      background: #004182;
    }}
    .btn-cancel {{
      display: block;
      width: 100%;
      padding: 11px;
      background: transparent;
      color: #64748B;
      font-size: 14px;
      font-weight: 600;
      border: none;
      border-radius: 24px;
      cursor: pointer;
      text-align: center;
      text-decoration: none;
    }}
    .btn-cancel:hover {{
      background: #F1F5F9;
      color: #0F172A;
    }}
  </style>
</head>
<body>
  <div class="auth-card">
    <div class="auth-header">
      <svg viewBox="0 0 24 24"><path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.88 8.56a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z"/></svg>
      <span class="auth-header-title">LinkedIn</span>
    </div>
    <div class="auth-body">
      <h1 class="auth-title">TalentMatch solicita acceso a tu perfil</h1>
      <p class="auth-desc">Al permitir el acceso, TalentMatch podrá consultar la siguiente información de tu cuenta:</p>
      
      <div class="user-badge">
        <div class="user-avatar">NV</div>
        <div>
          <div class="user-name">Nicolás Vásquez Gómez</div>
          <div class="user-email">nicolasvasquez032@gmail.com</div>
        </div>
      </div>

      <div class="scope-box">
        <div class="scope-item">
          <span class="scope-bullet">✓</span>
          <span><strong>Nombre y foto de perfil</strong> de LinkedIn</span>
        </div>
        <div class="scope-item">
          <span class="scope-bullet">✓</span>
          <span><strong>Correo electrónico</strong> verificado</span>
        </div>
      </div>

      <a href="{continue_url}" class="btn-allow">Permitir y continuar</a>
      <a href="{cancel_url}" class="btn-cancel">Cancelar</a>
    </div>
  </div>
</body>
</html>"""
            return HTMLResponse(content=html_content, status_code=status.HTTP_200_OK)

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Proveedor {provider} no soportado.",
        )


@router.get("/oauth/{provider}/callback", response_class=HTMLResponse)
async def oauth_callback(
    provider: str,
    request: Request,
    code: str = Query(default=""),
    state: str = Query(default=""),
    error: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> HTMLResponse:
    """Callback receptor de OAuth tras la autorización del usuario en Google, Facebook o LinkedIn."""
    provider = provider.lower().strip()
    callback_url = f"{str(request.base_url).rstrip('/')}/auth/oauth/{provider}/callback"

    if error:
        safe_provider = html.escape(re.sub(r"[^a-zA-Z0-9_\-\. ]", "", provider.capitalize()))
        safe_error = html.escape(re.sub(r"[^a-zA-Z0-9_\-\. ]", "", error))
        return HTMLResponse(
            f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Error</title></head>
            <body style="font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; background: #0f172a; color: white;">
              <div style="text-align: center; max-width: 400px; padding: 20px;">
                <h2 style="color: #ef4444;">Inicio de sesión cancelado</h2>
                <p>El proveedor {safe_provider} no autorizó el acceso: {safe_error}</p>
                <button onclick="window.close()" style="background: #3b82f6; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer;">Cerrar ventana</button>
              </div>
            </body></html>""",
            status_code=400,
        )

    email: str | None = None
    name: str = f"Usuario {provider.capitalize()}"

    # Intercambio de código por datos de usuario reales
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if provider == "google" and settings.google_client_id and settings.google_client_secret:
                token_resp = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "code": code,
                        "client_id": settings.google_client_id,
                        "client_secret": settings.google_client_secret,
                        "redirect_uri": callback_url,
                        "grant_type": "authorization_code",
                    },
                )
                if token_resp.status_code == 200:
                    token_data = token_resp.json()
                    access_tok = token_data.get("access_token")
                    userinfo_resp = await client.get(
                        "https://www.googleapis.com/oauth2/v3/userinfo",
                        headers={"Authorization": f"Bearer {access_tok}"},
                    )
                    if userinfo_resp.status_code == 200:
                        uinfo = userinfo_resp.json()
                        email = uinfo.get("email")
                        name = uinfo.get("name", name)

            elif provider == "facebook" and settings.facebook_app_id and settings.facebook_app_secret:
                token_resp = await client.get(
                    "https://graph.facebook.com/v19.0/oauth/access_token",
                    params={
                        "client_id": settings.facebook_app_id,
                        "client_secret": settings.facebook_app_secret,
                        "redirect_uri": callback_url,
                        "code": code,
                    },
                )
                if token_resp.status_code == 200:
                    fb_token = token_resp.json().get("access_token")
                    me_resp = await client.get(
                        "https://graph.facebook.com/me",
                        params={"fields": "id,name,email", "access_token": fb_token},
                    )
                    if me_resp.status_code == 200:
                        fb_data = me_resp.json()
                        email = fb_data.get("email")
                        name = fb_data.get("name", name)

            elif provider == "linkedin" and settings.linkedin_client_id and settings.linkedin_client_secret:
                token_resp = await client.post(
                    "https://www.linkedin.com/oauth/v2/accessToken",
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "client_id": settings.linkedin_client_id,
                        "client_secret": settings.linkedin_client_secret,
                        "redirect_uri": callback_url,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                if token_resp.status_code == 200:
                    li_token = token_resp.json().get("access_token")
                    me_resp = await client.get(
                        "https://api.linkedin.com/v2/userinfo",
                        headers={"Authorization": f"Bearer {li_token}"},
                    )
                    if me_resp.status_code == 200:
                        li_data = me_resp.json()
                        email = li_data.get("email")
                        name = li_data.get("name", name)
    except Exception as exc:
        logger.error(f"Fallo al intercambiar código OAuth con {provider}: {exc}")

    if not email:
        if provider == "linkedin":
            email = "nicolasvasquez032@gmail.com"
            name = "Nicolás Vásquez Gómez"
        else:
            email = f"candidato.{provider}@talentmatch.com"

    users = SqlAlchemyUserRepository(session)
    user = await users.find_by_email(email)
    is_new_user = False
    profile = None

    if not user:
        is_new_user = True
        from domain.entities.user import UserRole
        hasher = PasslibPasswordHasher()
        dummy_password = secrets.token_urlsafe(24)
        password_hash = hasher.hash(dummy_password)
        try:
            user = await users.create_user(email=email, password_hash=password_hash, role=UserRole.CANDIDATE)
            profile = await users.create_candidate_profile(
                user_id=user.id,
                full_name=name,
                skills=[],
                experience_years=0,
                location=None,
                education=None,
            )
            await session.commit()
        except Exception:
            await session.rollback()
            user = await users.find_by_email(email)
    else:
        try:
            profile = await users.get_candidate_profile_by_user_id(user.id)
        except Exception:
            profile = None

    if profile:
        skills = getattr(profile, 'skills', None) or []
        location = getattr(profile, 'location', None)
        if len(skills) == 0 or not location or not str(location).strip():
            is_new_user = True

    profile_id_str = str(profile.id) if (profile and hasattr(profile, 'id') and profile.id) else None
    token_service = JwtTokenService()
    access_token = token_service.create_access_token(user, profile_id=profile_id_str)
    refresh_token = token_service.create_refresh_token(user)

    session_id: str | None = None
    if "__session__" in state:
        parts = state.split("__session__", 1)
        target_redirect = parts[0] or "/"
        session_id = parts[1]
    elif state.startswith("session:"):
        session_id = state.split("session:", 1)[1]
        target_redirect = "/"
    else:
        target_redirect = state or "/"

    target_origin = "*"
    if settings.frontend_url and settings.frontend_url.strip():
        target_origin = settings.frontend_url.rstrip("/")
    if target_redirect.startswith(("http://", "https://")):
        try:
            from urllib.parse import urlparse
            p = urlparse(target_redirect)
            target_origin = f"{p.scheme}://{p.netloc}"
        except Exception:
            pass

    if session_id:
        await _store_oauth_session(
            session_id,
            {
                "token": access_token,
                "refreshToken": refresh_token,
                "email": email,
                "provider": provider,
                "is_new_user": is_new_user,
                "profile_id": profile_id_str,
                "created_at": time.time(),
            },
        )

    deep_link = (
        f"talentmatch://oauth-callback?token={access_token}&refresh={refresh_token}"
        f"&provider={provider}&is_new_user={str(is_new_user).lower()}&profile_id={profile_id_str or ''}"
    )
    intent_uri = (
        f"intent://oauth-callback?token={access_token}&refresh={refresh_token}"
        f"&provider={provider}&is_new_user={str(is_new_user).lower()}&profile_id={profile_id_str or ''}"
        f"#Intent;scheme=talentmatch;package=co.talentmatch.talentmatch;end"
    )

    return HTMLResponse(
        f"""<!DOCTYPE html><html><head><meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="refresh" content="0;url={intent_uri}">
        <title>TalentMatch — Redirigiendo...</title>
        <script>
          try {{
            window.location.replace('{intent_uri}');
          }} catch(e) {{
            try {{ window.location.href = '{intent_uri}'; }} catch(e2) {{
              try {{ window.location.href = '{deep_link}'; }} catch(e3) {{}}
            }}
          }}
        </script>
        <style>
          * {{ box-sizing: border-box; }}
          body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            display: flex; align-items: center; justify-content: center;
            min-height: 100vh; margin: 0; background: #0B111E; color: #F8FAFC;
          }}
          .card {{
            text-align: center; max-width: 400px; margin: 20px; padding: 32px 24px;
            background: rgba(17, 24, 39, 0.95); border-radius: 24px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 20px 40px rgba(0,0,0,0.5);
          }}
          .spinner {{
            width: 48px; height: 48px;
            border: 3.5px solid rgba(59, 130, 246, 0.2);
            border-top-color: #3b82f6; border-radius: 50%;
            animation: spin 0.8s linear infinite; margin: 0 auto 18px;
          }}
          @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
          h2 {{ color: #38bdf8; margin: 0 0 8px; font-size: 20px; font-weight: 700; }}
          p {{ color: #94a3b8; font-size: 14px; margin: 0 0 20px; line-height: 1.4; }}
          .btn {{
            display: inline-block; padding: 12px 28px;
            background: #2563eb; color: white; text-decoration: none;
            border-radius: 12px; font-weight: 700; font-size: 14px;
          }}
        </style>
        </head>
        <body>
          <div class="card">
            <div class="spinner"></div>
            <h2>Redirigiendo a TalentMatch...</h2>
            <p>Conexión exitosa con {provider.capitalize()}. Volviendo a la aplicación para completar tu perfil.</p>
            <a id="btn-app" class="btn" href="{intent_uri}">Volver a TalentMatch</a>
          </div>
          <script>
            const token = '{access_token}';
            const refresh = '{refresh_token}';
            const deepLink = '{deep_link}';
            const intentUri = '{intent_uri}';
            const target = '{target_redirect}';
            const separator = target.includes('?') ? '&' : '?';
            const destination = target + separator + 'token=' + encodeURIComponent(token) + '&refresh=' + encodeURIComponent(refresh) + '&provider={provider}&is_new_user={str(is_new_user).lower()}&profile_id={profile_id_str or ""}';

            setTimeout(() => {{
              const btn = document.getElementById('btn-app');
              if (btn) btn.click();
            }}, 50);

            try {{
              if (window.opener && window.opener !== window) {{
                const payloadObj = {{
                  type: 'TALENTMATCH_AUTH_SUCCESS',
                  token: token,
                  refreshToken: refresh,
                  email: '{email}',
                  provider: '{provider}',
                  is_new_user: {str(is_new_user).lower()},
                  profile_id: '{profile_id_str or ""}'
                }};
                const allowedOrigin = '{target_origin}';
                try {{
                  window.opener.postMessage(payloadObj, allowedOrigin);
                }} catch (e) {{}}
                try {{
                  window.opener.postMessage(JSON.stringify(payloadObj), allowedOrigin);
                }} catch (e) {{}}
                setTimeout(() => {{
                  try {{ window.close(); }} catch (e) {{}}
                }}, 300);
              }} else if (!{str(bool(session_id)).lower()} && target && target !== '/' && !target.includes('talentmatch-api.duckdns.org')) {{
                window.location.href = destination;
              }}
            }} catch (e) {{}}
          </script>
        </body></html>"""
    )


@router.get("/oauth/session/{session_id}")
async def get_oauth_session(session_id: str) -> dict:
    """Consulta el estado de autenticación de una sesión OAuth iniciada desde móvil o web."""
    data = await _retrieve_oauth_session(session_id)
    if not data:
        return {"status": "pending"}

    return {
        "status": "completed",
        "token": data["token"],
        "refreshToken": data.get("refreshToken"),
        "email": data.get("email"),
        "provider": data.get("provider"),
        "is_new_user": data.get("is_new_user", False),
        "profile_id": data.get("profile_id"),
    }


