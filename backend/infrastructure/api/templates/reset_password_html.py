"""Plantilla HTML oficial para restablecer contraseña de TalentMatch.
Diseño idéntico a la pantalla de Login oficial de Flutter.
"""

def render_reset_password_html(token: str) -> str:
    html = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TalentMatch — Restablecer contraseña</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
  <style>
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    body {
      background-color: #F4F7FC;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 32px 16px;
      position: relative;
      overflow-x: hidden;
      color: #10265F;
    }
    /* Background Glows (exactamente como en LoginScreen de Flutter) */
    .glow-top {
      position: fixed;
      top: -100px;
      left: -100px;
      width: 320px;
      height: 320px;
      background: rgba(21, 88, 214, 0.15);
      border-radius: 50%;
      filter: blur(45px);
      pointer-events: none;
      z-index: 0;
    }
    .glow-bottom {
      position: fixed;
      bottom: -60px;
      right: -60px;
      width: 280px;
      height: 280px;
      background: rgba(101, 70, 199, 0.15);
      border-radius: 50%;
      filter: blur(45px);
      pointer-events: none;
      z-index: 0;
    }
    .main-container {
      width: 100%;
      max-width: 430px;
      display: flex;
      flex-direction: column;
      align-items: center;
      position: relative;
      z-index: 1;
    }
    /* Logotipo circular oficial */
    .logo-container {
      background: #FFFFFF;
      padding: 16px;
      border-radius: 50%;
      box-shadow: 0 10px 20px rgba(16, 38, 95, 0.05);
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 24px;
    }
    .brand-logo-card {
      width: 54px;
      height: 54px;
      background: #FFFFFF;
      border-radius: 16px;
      box-shadow: 0 4px 10px rgba(16, 38, 95, 0.08);
      padding: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .brand-logo-card img {
      width: 100%;
      height: 100%;
      object-fit: contain;
    }
    .brand-title {
      font-size: 28px;
      font-weight: 900;
      color: #10265F;
      letter-spacing: -0.5px;
      text-align: center;
      margin-bottom: 4px;
    }
    .brand-subtitle {
      font-size: 14px;
      color: #758095;
      font-weight: 500;
      text-align: center;
      margin-bottom: 36px;
    }
    /* Card Glassmorphism oficial */
    .card {
      background: rgba(255, 255, 255, 0.65);
      backdrop-filter: blur(25px);
      -webkit-backdrop-filter: blur(25px);
      border-radius: 24px;
      border: 1.5px solid #FFFFFF;
      box-shadow: 0 15px 30px rgba(16, 38, 95, 0.03);
      padding: 26px 24px;
      width: 100%;
    }
    .card-title {
      font-size: 22px;
      font-weight: 800;
      color: #10265F;
      margin-bottom: 8px;
    }
    .card-desc {
      font-size: 13px;
      color: #758095;
      line-height: 1.45;
      margin-bottom: 22px;
    }
    .form-group {
      margin-bottom: 16px;
    }
    .field-label {
      display: block;
      font-size: 12px;
      font-weight: 600;
      color: #10265F;
      margin-bottom: 6px;
    }
    .input-wrapper {
      position: relative;
      display: flex;
      align-items: center;
    }
    .input-icon {
      position: absolute;
      left: 14px;
      color: #758095;
      width: 20px;
      height: 20px;
      pointer-events: none;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .input-field {
      width: 100%;
      height: 52px;
      background: rgba(255, 255, 255, 0.9);
      border: 1px solid rgba(16, 38, 95, 0.07);
      border-radius: 12px;
      padding: 0 46px 0 44px;
      font-size: 14px;
      color: #14213D;
      outline: none;
      transition: all 0.2s ease;
    }
    .input-field::placeholder {
      color: #9CA3AF;
      letter-spacing: 1px;
    }
    .input-field:focus {
      background: #FFFFFF;
      border-color: #1558D6;
      box-shadow: 0 0 0 3px rgba(21, 88, 214, 0.12);
    }
    .toggle-pwd {
      position: absolute;
      right: 12px;
      background: none;
      border: none;
      color: #758095;
      cursor: pointer;
      width: 28px;
      height: 28px;
      padding: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 6px;
    }
    .toggle-pwd svg {
      width: 20px;
      height: 20px;
    }
    .requirements {
      background: rgba(255, 255, 255, 0.8);
      border-radius: 12px;
      padding: 12px 14px;
      margin-bottom: 22px;
      border: 1px solid rgba(16, 38, 95, 0.05);
    }
    .req-item {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      color: #758095;
      margin-bottom: 4px;
      font-weight: 500;
      transition: color 0.2s;
    }
    .req-item:last-child {
      margin-bottom: 0;
    }
    .req-item.valid {
      color: #18A477;
    }
    .req-icon {
      font-size: 13px;
    }
    .btn-gradient {
      width: 100%;
      height: 52px;
      background: linear-gradient(to right, #1667DC, #1558D6);
      border: none;
      border-radius: 13px;
      color: #FFFFFF;
      font-size: 16px;
      font-weight: 700;
      cursor: pointer;
      box-shadow: 0 8px 18px rgba(21, 88, 214, 0.28);
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      transition: all 0.2s ease;
    }
    .btn-gradient:hover:not(:disabled) {
      transform: translateY(-1px);
      box-shadow: 0 10px 22px rgba(21, 88, 214, 0.35);
    }
    .btn-gradient:disabled {
      opacity: 0.55;
      cursor: not-allowed;
      transform: none;
      box-shadow: none;
    }
    .alert-box {
      padding: 12px 14px;
      border-radius: 12px;
      font-size: 13px;
      margin-bottom: 18px;
      display: none;
      line-height: 1.4;
      background: #FEF2F2;
      color: #B91C1C;
      border: 1px solid #FCA5A5;
    }
    .state-view {
      display: none;
      text-align: center;
      padding: 16px 0;
    }
    .success-icon-badge {
      width: 72px;
      height: 72px;
      background: #E8F8EF;
      color: #18A477;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 18px;
      box-shadow: 0 8px 20px rgba(24, 164, 119, 0.2);
    }
    .success-icon-badge svg {
      width: 38px;
      height: 38px;
    }
    .error-icon-badge {
      width: 72px;
      height: 72px;
      background: #FEE2E2;
      color: #EF4444;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 18px;
    }
    .error-icon-badge svg {
      width: 36px;
      height: 36px;
    }
    .spinner {
      border: 2.5px solid rgba(255, 255, 255, 0.3);
      border-top: 2.5px solid #ffffff;
      border-radius: 50%;
      width: 18px;
      height: 18px;
      animation: spin 0.7s linear infinite;
      display: none;
    }
    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
    .footer-note {
      margin-top: 28px;
      text-align: center;
      font-size: 13px;
      color: #758095;
    }
    .footer-note strong {
      color: #1558D6;
    }
  </style>
</head>
<body>
  <div class="glow-top"></div>
  <div class="glow-bottom"></div>

  <div class="main-container">
    <!-- ── Logotipo Oficial TalentMatch ── -->
    <div class="logo-container">
      <div class="brand-logo-card">
        <img src="data:image/png;base64,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" alt="TalentMatch Logo">
      </div>
    </div>
    
    <div class="brand-title">TalentMatch</div>
    <div class="brand-subtitle">Empleo inteligente para tu futuro</div>

    <!-- ── Card Glassmorphism ── -->
    <div class="card">
      <!-- VISTA FORMULARIO -->
      <div id="formSection">
        <div class="card-title">Restablecer contraseña</div>
        <div class="card-desc">Ingresa tu nueva contraseña para recuperar el acceso a tu cuenta.</div>

        <div id="alertBox" class="alert-box"></div>

        <form id="resetForm" onsubmit="handleSubmit(event)">
          <div class="form-group">
            <label class="field-label" for="newPassword">Nueva contraseña</label>
            <div class="input-wrapper">
              <div class="input-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
              </div>
              <input type="password" id="newPassword" class="input-field" placeholder="••••••••" required autocomplete="new-password">
              <button type="button" class="toggle-pwd" onclick="toggleVisibility('newPassword', this)" aria-label="Ver contraseña">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>
              </button>
            </div>
          </div>

          <div class="form-group">
            <label class="field-label" for="confirmPassword">Confirmar contraseña</label>
            <div class="input-wrapper">
              <div class="input-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
              </div>
              <input type="password" id="confirmPassword" class="input-field" placeholder="••••••••" required autocomplete="new-password">
              <button type="button" class="toggle-pwd" onclick="toggleVisibility('confirmPassword', this)" aria-label="Ver contraseña">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>
              </button>
            </div>
          </div>

          <div class="requirements">
            <div class="req-item" id="reqLen"><span class="req-icon">○</span> Mínimo 8 caracteres</div>
            <div class="req-item" id="reqMatch"><span class="req-icon">○</span> Las contraseñas coinciden</div>
          </div>

          <button type="submit" id="submitBtn" class="btn-gradient" disabled>
            <span class="spinner" id="spinner"></span>
            <span id="btnText">Restablecer contraseña</span>
          </button>
        </form>
      </div>

      <!-- VISTA ÉXITO -->
      <div id="successView" class="state-view">
        <div class="success-icon-badge">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
        </div>
        <div class="card-title" style="text-align: center;">¡Contraseña restablecida!</div>
        <div class="card-desc" style="text-align: center; margin-bottom: 20px;">Tu clave se ha actualizado con éxito.<br><br>Ya puedes volver a la app de <strong>TalentMatch</strong> e iniciar sesión normalmente.</div>
      </div>

      <!-- VISTA TOKEN INVÁLIDO -->
      <div id="invalidView" class="state-view">
        <div class="error-icon-badge">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
        </div>
        <div class="card-title" style="text-align: center;">Enlace expirado o inválido</div>
        <div class="card-desc" style="text-align: center;">Por seguridad, los enlaces de recuperación solo pueden usarse una vez y vencen tras 1 hora.<br><br>Solicita uno nuevo desde la pantalla de inicio de sesión de la app.</div>
      </div>
    </div>

    <div class="footer-note">
      ¿Recordaste tu contraseña? <strong>Abre tu app e inicia sesión</strong>
    </div>
  </div>

  <script>
    const token = "__TOKEN__";
    const formSection = document.getElementById('formSection');
    const successView = document.getElementById('successView');
    const invalidView = document.getElementById('invalidView');
    const alertBox = document.getElementById('alertBox');
    const newPwd = document.getElementById('newPassword');
    const confirmPwd = document.getElementById('confirmPassword');
    const submitBtn = document.getElementById('submitBtn');
    const spinner = document.getElementById('spinner');
    const btnText = document.getElementById('btnText');

    if (!token || token.trim() === "") {
      formSection.style.display = 'none';
      invalidView.style.display = 'block';
    }

    function validate() {
      const p1 = newPwd.value;
      const p2 = confirmPwd.value;

      const isLen = p1.length >= 8;
      const isMatch = p1.length > 0 && p1 === p2;

      updateReq('reqLen', isLen);
      updateReq('reqMatch', isMatch);

      submitBtn.disabled = !(isLen && isMatch);
    }

    function updateReq(id, valid) {
      const el = document.getElementById(id);
      if (valid) {
        el.classList.add('valid');
        el.querySelector('.req-icon').textContent = '✓';
      } else {
        el.classList.remove('valid');
        el.querySelector('.req-icon').textContent = '○';
      }
    }

    newPwd.addEventListener('input', validate);
    confirmPwd.addEventListener('input', validate);

    const eyeOpenSvg = '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle>';
    const eyeSlashSvg = '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line>';

    function toggleVisibility(inputId, btn) {
      const input = document.getElementById(inputId);
      const svg = btn.querySelector('svg');
      if (input.type === 'password') {
        input.type = 'text';
        svg.innerHTML = eyeOpenSvg;
      } else {
        input.type = 'password';
        svg.innerHTML = eyeSlashSvg;
      }
    }

    async function handleSubmit(e) {
      e.preventDefault();
      alertBox.style.display = 'none';
      submitBtn.disabled = true;
      spinner.style.display = 'inline-block';
      btnText.textContent = 'Actualizando...';

      try {
        const response = await fetch('/auth/confirmar-reset', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            token: token,
            new_password: newPwd.value
          })
        });

        const data = await response.json();

        if (response.ok) {
          formSection.style.display = 'none';
          successView.style.display = 'block';
        } else {
          alertBox.textContent = data.detail || 'Ocurrió un error. El token puede haber vencido.';
          alertBox.style.display = 'block';
          submitBtn.disabled = false;
          spinner.style.display = 'none';
          btnText.textContent = 'Restablecer contraseña';
        }
      } catch (err) {
        alertBox.textContent = 'Error de conexión con el servidor. Intenta nuevamente.';
        alertBox.style.display = 'block';
        submitBtn.disabled = false;
        spinner.style.display = 'none';
        btnText.textContent = 'Restablecer contraseña';
      }
    }
  </script>
</body>
</html>"""
    import re

    # Sanitizar estrictamente el token para prevenir XSS reflejado (CWE-79 / OWASP A03)
    # Solo caracteres seguros URL-safe (letras, números, guión y guión bajo) son permitidos
    safe_token = re.sub(r"[^A-Za-z0-9_-]", "", token)
    return html.replace("__TOKEN__", safe_token)
