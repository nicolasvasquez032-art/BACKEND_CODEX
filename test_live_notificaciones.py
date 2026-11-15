import json
import urllib.request
import urllib.error
import uuid
import time

BASE_URL = "https://talentmatch-api.duckdns.org"

def api_request(method, path, data=None, token=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            if res.status == 204:
                return None
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"❌ Error HTTP {e.code} en {path}: {err_msg}")
        raise

def main():
    print("=" * 65)
    print("🧪 PRUEBA EN VIVO DEL SISTEMA DE NOTIFICACIONES & FIREBASE (FCM)")
    print(f"📡 Servidor: {BASE_URL}")
    print("=" * 65)

    # 1. Crear Candidato de prueba
    cand_id_str = uuid.uuid4().hex[:6]
    cand_email = f"candidato_fcm_{cand_id_str}@test.com"
    pwd = "Password123!*"
    print(f"\n1. Registrando Candidato: {cand_email}...")
    cand = api_request("POST", "/auth/registro/candidato", {
        "email": cand_email,
        "password": pwd,
        "full_name": f"Candidato Test FCM {cand_id_str}",
        "skills": ["Python", "FastAPI", "Docker"],
        "experience_years": 3
    })
    print(f"   ✅ Candidato registrado exitosamente (ID: {cand['id']})")

    # 2. Iniciar Sesión Candidato
    print("\n2. Obteniendo Token JWT del Candidato...")
    login_cand = api_request("POST", "/auth/login", {
        "email": cand_email,
        "password": pwd
    })
    cand_token = login_cand["access_token"]
    user_id = cand.get("user_id", cand["id"])
    print("   ✅ Token JWT generado correctamente")

    # 3. Registrar Token FCM de Dispositivo
    mock_fcm_token = f"fcm_device_token_{uuid.uuid4().hex}"
    print(f"\n3. Registrando Token FCM de Dispositivo en el Backend...")
    print(f"   Token: {mock_fcm_token[:30]}...")
    res_token = api_request("POST", "/notificaciones/token-dispositivo", {
        "token": mock_fcm_token,
        "dispositivo_info": "Google Pixel 8 - Android 14 (TalentMatch App)"
    }, token=cand_token)
    print(f"   ✅ Respuesta del servidor: {res_token.get('message')}")

    # 4. Consultar Notificaciones del Candidato
    print(f"\n4. Consultando lista de notificaciones para User ID: {user_id}...")
    notifs = api_request("GET", f"/notificaciones/usuario/{user_id}", token=cand_token)
    print(f"   ℹ️ Notificaciones actuales en bandeja: {len(notifs)}")
    for n in notifs:
        print(f"      - [{n['creado_en']}] {n['tipo']}: {n['mensaje']} (Leída: {n['leido']})")

    # 5. Crear una Empresa y publicar vacante para disparar evento de notificación
    comp_id_str = uuid.uuid4().hex[:6]
    comp_email = f"empresa_fcm_{comp_id_str}@test.com"
    print(f"\n5. Registrando Empresa ({comp_email}) y publicando vacante...")
    api_request("POST", "/auth/registro/empresa", {
        "email": comp_email,
        "password": pwd
    })
    login_comp = api_request("POST", "/auth/login", {
        "email": comp_email,
        "password": pwd
    })
    comp_token = login_comp["access_token"]

    vacante = api_request("POST", "/vacantes", {
        "titulo": "Senior Python & FastAPI Engineer",
        "descripcion": "Buscamos desarrollador senior para nuestra plataforma.",
        "requisitos": ["Python", "FastAPI", "Docker"],
        "ubicacion": "Remoto",
        "categoria": "Backend",
        "salario_min": 4000,
        "salario_max": 6000
    }, token=comp_token)
    print(f"   ✅ Vacante publicada: '{vacante['titulo']}' (ID: {vacante['id']})")

    # 6. Esperar procesamiento asíncrono y verificar notificaciones
    print("\n6. Verificando persistencia y actualización de notificaciones...")
    time.sleep(2)
    notifs_after = api_request("GET", f"/notificaciones/usuario/{user_id}", token=cand_token)
    print(f"   ✅ Notificaciones en la bandeja: {len(notifs_after)}")
    for n in notifs_after:
        print(f"      📌 [{n['creado_en']}] {n['tipo']}: {n['mensaje']} (Leída: {n['leido']})")

    # 7. Si hay notificación, marcar como leída
    if notifs_after:
        notif_id = notifs_after[0]["id"]
        print(f"\n7. Marcando notificación {notif_id} como leída...")
        api_request("PATCH", f"/notificaciones/{notif_id}/leida", token=cand_token)
        notifs_final = api_request("GET", f"/notificaciones/usuario/{user_id}", token=cand_token)
        is_read = next(n["leido"] for n in notifs_final if n["id"] == notif_id)
        print(f"   ✅ Estado actualizado exitosamente (Leída: {is_read})")

    print("\n" + "=" * 65)
    print("🎉 PRUEBA COMPLETADA EXITOSAMENTE")
    print("=" * 65)

if __name__ == "__main__":
    main()
