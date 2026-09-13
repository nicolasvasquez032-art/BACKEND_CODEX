import urllib.request
import urllib.error
import urllib.parse
import json
import uuid
import time

BACKEND_URL = "http://localhost:8000"

def request(method, url, data=None, headers=None):
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
        
    if headers and headers.get("Content-Type") == "application/x-www-form-urlencoded":
        encoded = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(url, data=encoded, headers=req_headers, method=method)
    else:
        encoded = json.dumps(data).encode("utf-8") if data else None
        req = urllib.request.Request(url, data=encoded, headers=req_headers, method=method)
        
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            if res.status == 204:
                return None
            return json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTPError: {e.code} - {e.read().decode()}")
        raise

def test_notificaciones_flow():
    print("Iniciando prueba E2E de notificaciones y geolocalización...")

    # 1. Registrar empresa
    company_email = f"empresa_{uuid.uuid4().hex[:6]}@test.com"
    password = "password123"
    print(f"Registrando empresa {company_email}...")
    company = request("POST", f"{BACKEND_URL}/auth/registro/empresa", data={
        "email": company_email,
        "password": password
    })
    
    # Login empresa
    login_comp = request("POST", f"{BACKEND_URL}/auth/login", data={
        "email": company_email,
        "password": password
    })
    company_headers = {"Authorization": f"Bearer {login_comp['access_token']}"}

    # 2. Registrar candidato
    candidate_email = f"candidato_{uuid.uuid4().hex[:6]}@test.com"
    print(f"Registrando candidato {candidate_email}...")
    candidate = request("POST", f"{BACKEND_URL}/auth/registro/candidato", data={
        "email": candidate_email,
        "password": password,
        "full_name": "Test Candidate Notif",
        "skills": [],
        "experience_years": 0
    })
    
    # Login candidato
    login_cand = request("POST", f"{BACKEND_URL}/auth/login", data={
        "email": candidate_email,
        "password": password
    })
    candidate_headers = {"Authorization": f"Bearer {login_cand['access_token']}"}

    # 3. Actualizar perfil candidato (Backend Engineer)
    print("Actualizando perfil del candidato...")
    request("PUT", f"{BACKEND_URL}/perfiles/{candidate['id']}", data={
        "full_name": "Test Candidate Notif",
        "skills": ["Go", "FastAPI", "Python", "Microservicios"],
        "experience_years": 4,
        "location": "Ciudad de México",
        "education": "Ingeniero"
    }, headers=candidate_headers)

    # 4. Registrar Token de Dispositivo para Notificaciones
    print("Registrando token de dispositivo FCM (mock)...")
    token_fcm = f"token-fcm-test-{uuid.uuid4().hex[:6]}"
    request("POST", f"{BACKEND_URL}/notificaciones/token-dispositivo", data={
        "token": token_fcm,
        "dispositivo_info": "Android 14"
    }, headers=candidate_headers)

    # 5. Publicar Vacante que haga match (Go Backend Developer con lat/long)
    print("Publicando vacante con Geolocalización...")
    vacante = request("POST", f"{BACKEND_URL}/vacantes", data={
        "titulo": "Go Backend Developer",
        "descripcion": "Buscamos un desarrollador en Go y microservicios.",
        "requisitos": ["Go", "Microservicios", "Docker"],
        "ubicacion": "Ciudad de México, CDMX",
        "categoria": "Backend",
        "latitud": 19.4326,
        "longitud": -99.1332
    }, headers=company_headers)
    print(f"Vacante publicada: {vacante['titulo']} (Lat: {vacante['latitud']}, Long: {vacante['longitud']})")

    # Esperar un poco para que el match se procese
    print("Esperando 2 segundos para procesamiento de notificaciones...")
    time.sleep(2)

    print(f"Candidato User ID: {candidate['user_id']}")
    
    # 6. Consultar Notificaciones del Candidato
    print("Consultando notificaciones...")
    try:
        notificaciones = request("GET", f"{BACKEND_URL}/notificaciones/usuario/{candidate['user_id']}", headers=candidate_headers)
    except urllib.error.HTTPError as e:
        print(f"Error {e.code} al consultar notificaciones para usuario {candidate['user_id']}.")
        raise
    print(f"Notificaciones recibidas: {len(notificaciones)}")
    
    for n in notificaciones:
        print(f" - [{n['creado_en']}] {n['tipo']}: {n['mensaje']} (Leída: {n['leido']})")
        
    if notificaciones:
        print(f"Marcando notificación {notificaciones[0]['id']} como leída...")
        request("PATCH", f"{BACKEND_URL}/notificaciones/{notificaciones[0]['id']}/leida", headers=candidate_headers)
        
        # Verificar que se marcó como leída
        notificaciones_upd = request("GET", f"{BACKEND_URL}/notificaciones/usuario/{candidate['id']}", headers=candidate_headers)
        leida = next(n['leido'] for n in notificaciones_upd if n['id'] == notificaciones[0]['id'])
        print(f"Estado de notificación actualizada (Leída: {leida})")

if __name__ == "__main__":
    test_notificaciones_flow()
