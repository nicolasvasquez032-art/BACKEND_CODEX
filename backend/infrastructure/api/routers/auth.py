from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from loguru import logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

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
    RequestPasswordResetRequest,
    TokenResponse,
    UserResponse,
)
from infrastructure.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


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

    return TokenResponse(access_token=result.access_token, token_type=result.token_type)


@router.post("/recuperar-password", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/minute")
async def request_password_reset(
    request: Request,
    payload: RequestPasswordResetRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Solicita el envío de un enlace de recuperación de contraseña por correo.

    Siempre responde 202 para no revelar si el email existe en el sistema.
    """
    users = SqlAlchemyUserRepository(session)
    use_case = RequestPasswordResetUseCase(users, SmtpEmailService())
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
async def reset_password_page(token: str = Query(default="")) -> HTMLResponse:
    """Renderiza la página web oficial de TalentMatch para cambiar la contraseña con el token."""
    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TalentMatch — Restablecer contraseña</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}
    body {{
      background-color: #F4F7FC;
      background-image: 
        radial-gradient(at 0% 0%, rgba(65, 201, 226, 0.15) 0px, transparent 50%),
        radial-gradient(at 100% 100%, rgba(11, 25, 44, 0.08) 0px, transparent 50%);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px 16px;
      color: #0B192C;
    }}
    .card {{
      background: #FFFFFF;
      width: 100%;
      max-width: 440px;
      border-radius: 24px;
      padding: 38px 32px;
      box-shadow: 0 20px 45px rgba(11, 25, 44, 0.08), 0 4px 12px rgba(11, 25, 44, 0.04);
      border: 1px solid rgba(226, 232, 240, 0.9);
      position: relative;
    }}
    .brand-header {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 12px;
      margin-bottom: 26px;
    }}
    .brand-logo-icon {{
      width: 46px;
      height: 46px;
      background: linear-gradient(135deg, #008DDA, #41C9E2);
      border-radius: 14px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #FFFFFF;
      font-weight: 800;
      font-size: 22px;
      box-shadow: 0 6px 16px rgba(0, 141, 218, 0.35);
    }}
    .brand-title {{
      font-size: 25px;
      font-weight: 800;
      color: #0B192C;
      letter-spacing: -0.5px;
    }}
    .brand-title span {{
      color: #008DDA;
    }}
    h1 {{
      font-size: 21px;
      font-weight: 700;
      color: #0B192C;
      margin-bottom: 8px;
      text-align: center;
    }}
    p.subtitle {{
      font-size: 14px;
      color: #64748B;
      text-align: center;
      margin-bottom: 24px;
      line-height: 1.5;
    }}
    .form-group {{
      margin-bottom: 18px;
    }}
    label {{
      display: block;
      font-size: 13px;
      font-weight: 600;
      color: #334155;
      margin-bottom: 6px;
    }}
    .input-wrapper {{
      position: relative;
      display: flex;
      align-items: center;
    }}
    input[type="password"], input[type="text"] {{
      width: 100%;
      padding: 13px 44px 13px 14px;
      border: 1.5px solid #E2E8F0;
      border-radius: 12px;
      font-size: 14px;
      color: #0B192C;
      background: #F8FAFC;
      transition: all 0.2s ease;
      outline: none;
    }}
    input:focus {{
      background: #FFFFFF;
      border-color: #008DDA;
      box-shadow: 0 0 0 4px rgba(0, 141, 218, 0.12);
    }}
    .toggle-pwd {{
      position: absolute;
      right: 12px;
      background: none;
      border: none;
      color: #94A3B8;
      cursor: pointer;
      font-size: 18px;
      padding: 4px;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .requirements {{
      background: #F8FAFC;
      border-radius: 12px;
      padding: 12px 14px;
      margin-bottom: 22px;
      border: 1px solid #E2E8F0;
    }}
    .req-item {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12.5px;
      color: #64748B;
      margin-bottom: 5px;
      transition: color 0.2s;
    }}
    .req-item:last-child {{
      margin-bottom: 0;
    }}
    .req-item.valid {{
      color: #10B981;
      font-weight: 500;
    }}
    .req-icon {{
      font-size: 13px;
    }}
    .btn-submit {{
      width: 100%;
      background: #008DDA;
      color: #FFFFFF;
      border: none;
      padding: 14px;
      border-radius: 12px;
      font-size: 15px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s ease;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      box-shadow: 0 4px 14px rgba(0, 141, 218, 0.35);
    }}
    .btn-submit:hover:not(:disabled) {{
      background: #0077BA;
      transform: translateY(-1px);
      box-shadow: 0 6px 18px rgba(0, 141, 218, 0.4);
    }}
    .btn-submit:disabled {{
      opacity: 0.55;
      cursor: not-allowed;
      box-shadow: none;
      transform: none;
    }}
    .alert {{
      padding: 12px 14px;
      border-radius: 12px;
      font-size: 13.5px;
      margin-bottom: 18px;
      display: none;
      line-height: 1.4;
    }}
    .alert-error {{
      background: #FEF2F2;
      color: #B91C1C;
      border: 1px solid #FCA5A5;
    }}
    .state-view {{
      display: none;
      text-align: center;
      padding: 12px 0;
    }}
    .success-icon {{
      width: 72px;
      height: 72px;
      background: #D1FAE5;
      color: #10B981;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 36px;
      margin: 0 auto 18px;
      box-shadow: 0 4px 16px rgba(16, 185, 129, 0.2);
    }}
    .error-icon {{
      width: 72px;
      height: 72px;
      background: #FEE2E2;
      color: #EF4444;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 36px;
      margin: 0 auto 18px;
    }}
    .spinner {{
      border: 2.5px solid rgba(255, 255, 255, 0.3);
      border-top: 2.5px solid #ffffff;
      border-radius: 50%;
      width: 16px;
      height: 16px;
      animation: spin 0.7s linear infinite;
      display: none;
    }}
    @keyframes spin {{
      0% {{ transform: rotate(0deg); }}
      100% {{ transform: rotate(360deg); }}
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="brand-header">
      <div class="brand-logo-icon">TM</div>
      <div class="brand-title">Talent<span>Match</span></div>
    </div>

    <!-- VISTA PRINCIPAL FORMULARIO -->
    <div id="formSection">
      <h1>Restablecer contraseña</h1>
      <p class="subtitle">Escribe tu nueva contraseña para volver a ingresar a tu cuenta de TalentMatch.</p>

      <div id="alertBox" class="alert alert-error"></div>

      <form id="resetForm" onsubmit="handleSubmit(event)">
        <div class="form-group">
          <label for="newPassword">Nueva contraseña</label>
          <div class="input-wrapper">
            <input type="password" id="newPassword" placeholder="Ingresa tu nueva contraseña" required autocomplete="new-password">
            <button type="button" class="toggle-pwd" onclick="toggleVisibility('newPassword', this)">👁️</button>
          </div>
        </div>

        <div class="form-group">
          <label for="confirmPassword">Confirmar contraseña</label>
          <div class="input-wrapper">
            <input type="password" id="confirmPassword" placeholder="Confirma tu nueva contraseña" required autocomplete="new-password">
            <button type="button" class="toggle-pwd" onclick="toggleVisibility('confirmPassword', this)">👁️</button>
          </div>
        </div>

        <div class="requirements">
          <div class="req-item" id="reqLen"><span class="req-icon">○</span> Mínimo 8 caracteres</div>
          <div class="req-item" id="reqMatch"><span class="req-icon">○</span> Las contraseñas coinciden</div>
        </div>

        <button type="submit" id="submitBtn" class="btn-submit" disabled>
          <span class="spinner" id="spinner"></span>
          <span id="btnText">Cambiar Contraseña</span>
        </button>
      </form>
    </div>

    <!-- VISTA ÉXITO -->
    <div id="successView" class="state-view">
      <div class="success-icon">✓</div>
      <h1>¡Contraseña restablecida!</h1>
      <p class="subtitle">Tu clave ha sido actualizada con éxito.<br>Ya puedes abrir la aplicación de <strong>TalentMatch</strong> e iniciar sesión.</p>
    </div>

    <!-- VISTA TOKEN INVÁLIDO -->
    <div id="invalidView" class="state-view">
      <div class="error-icon">✕</div>
      <h1>Enlace expirado o inválido</h1>
      <p class="subtitle">Por seguridad, los enlaces expiran tras 1 hora o solo pueden utilizarse una vez.<br><br>Solicita uno nuevo desde la pantalla de inicio de sesión de la app.</p>
    </div>
  </div>

  <script>
    const token = "{token}";
    const formSection = document.getElementById('formSection');
    const successView = document.getElementById('successView');
    const invalidView = document.getElementById('invalidView');
    const alertBox = document.getElementById('alertBox');
    const newPwd = document.getElementById('newPassword');
    const confirmPwd = document.getElementById('confirmPassword');
    const submitBtn = document.getElementById('submitBtn');
    const spinner = document.getElementById('spinner');
    const btnText = document.getElementById('btnText');

    if (!token || token.trim() === "") {{
      formSection.style.display = 'none';
      invalidView.style.display = 'block';
    }}

    function validate() {{
      const p1 = newPwd.value;
      const p2 = confirmPwd.value;

      const isLen = p1.length >= 8;
      const isMatch = p1.length > 0 && p1 === p2;

      updateReq('reqLen', isLen);
      updateReq('reqMatch', isMatch);

      submitBtn.disabled = !(isLen && isMatch);
    }}

    function updateReq(id, valid) {{
      const el = document.getElementById(id);
      if (valid) {{
        el.classList.add('valid');
        el.querySelector('.req-icon').textContent = '✓';
      }} else {{
        el.classList.remove('valid');
        el.querySelector('.req-icon').textContent = '○';
      }}
    }}

    newPwd.addEventListener('input', validate);
    confirmPwd.addEventListener('input', validate);

    function toggleVisibility(inputId, btn) {{
      const input = document.getElementById(inputId);
      if (input.type === 'password') {{
        input.type = 'text';
        btn.textContent = '🙈';
      }} else {{
        input.type = 'password';
        btn.textContent = '👁️';
      }}
    }}

    async function handleSubmit(e) {{
      e.preventDefault();
      alertBox.style.display = 'none';
      submitBtn.disabled = true;
      spinner.style.display = 'inline-block';
      btnText.textContent = 'Actualizando...';

      try {{
        const response = await fetch('/auth/confirmar-reset', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            token: token,
            new_password: newPwd.value
          }})
        }});

        const data = await response.json();

        if (response.ok) {{
          formSection.style.display = 'none';
          successView.style.display = 'block';
        }} else {{
          alertBox.textContent = data.detail || 'Ocurrió un error. El token puede haber vencido.';
          alertBox.style.display = 'block';
          submitBtn.disabled = false;
          spinner.style.display = 'none';
          btnText.textContent = 'Cambiar Contraseña';
        }}
      }} catch (err) {{
        alertBox.textContent = 'Error de conexión con el servidor. Intenta nuevamente.';
        alertBox.style.display = 'block';
        submitBtn.disabled = false;
        spinner.style.display = 'none';
        btnText.textContent = 'Cambiar Contraseña';
      }}
    }}
  </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)
