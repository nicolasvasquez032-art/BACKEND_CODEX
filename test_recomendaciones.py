import urllib.request
import urllib.error
import urllib.parse
import json
import uuid
import time

BACKEND_URL = "http://localhost:8000"
ML_URL = "http://localhost:8001"

def request(method, url, data=None, headers=None):
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
        
    # urlencode if data is a dict and Content-Type is application/x-www-form-urlencoded
    if headers and headers.get("Content-Type") == "application/x-www-form-urlencoded":
        encoded = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(url, data=encoded, headers=req_headers, method=method)
    else:
        encoded = json.dumps(data).encode("utf-8") if data else None
        req = urllib.request.Request(url, data=encoded, headers=req_headers, method=method)
        
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTPError: {e.code} - {e.read().decode()}")
        raise

def test_flow():
    # 1. Health checks
    print("Checking health...")
    print("Backend:", request("GET", f"{BACKEND_URL}/health"))
    print("ML Service:", request("GET", f"{ML_URL}/health"))
    
    # 2. Registrar candidato
    candidate_email = f"candidato_{uuid.uuid4().hex[:6]}@test.com"
    password = "password123"
    print(f"Registrando candidato {candidate_email}...")
    candidate = request("POST", f"{BACKEND_URL}/auth/registro/candidato", data={
        "email": candidate_email,
        "password": password,
        "full_name": "Test Candidate",
        "skills": [],
        "experience_years": 0
    })
    print("Candidato registrado:", candidate)
    
    # 3. Registrar empresa
    company_email = f"empresa_{uuid.uuid4().hex[:6]}@test.com"
    print(f"Registrando empresa {company_email}...")
    company = request("POST", f"{BACKEND_URL}/auth/registro/empresa", data={
        "email": company_email,
        "password": password
    })
    print("Empresa registrada:", company)
    
    # 4. Login candidato
    print("Login candidato...")
    login_cand = request("POST", f"{BACKEND_URL}/auth/login", data={
        "email": candidate_email,
        "password": password
    })
    candidate_headers = {"Authorization": f"Bearer {login_cand['access_token']}"}
    
    # 5. Login empresa
    print("Login empresa...")
    login_comp = request("POST", f"{BACKEND_URL}/auth/login", data={
        "email": company_email,
        "password": password
    })
    company_headers = {"Authorization": f"Bearer {login_comp['access_token']}"}
    
    # 6. Actualizar perfil candidato
    print("Actualizando perfil del candidato...")
    perfil = request("PUT", f"{BACKEND_URL}/perfiles/{candidate['id']}", data={
        "full_name": "Juan Perez",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Machine Learning"],
        "experience_years": 5,
        "location": "Remoto",
        "education": "Ingeniero de Sistemas"
    }, headers=candidate_headers)
    print("Perfil actualizado:", perfil["id"])
    
    # 7. Publicar vacante que hace match
    print("Publicando vacante 1 (Backend Python)...")
    vacante_match = request("POST", f"{BACKEND_URL}/vacantes", data={
        "titulo": "Senior Backend Developer - Python",
        "descripcion": "Buscamos un desarrollador experto en Python y bases de datos para unirse a nuestro equipo. El candidato ideal tiene experiencia con Fastapi.",
        "requisitos": ["Python", "FastAPI", "PostgreSQL", "Docker", "Experiencia de 4+ años"],
        "ubicacion": "Remoto",
        "categoria": "Desarrollo",
        "salario_min": 3000,
        "salario_max": 5000
    }, headers=company_headers)
    print("Vacante publicada:", vacante_match["id"])
    
    # 8. Publicar vacante sin match
    print("Publicando vacante 2 (Frontend React)...")
    vacante_no_match = request("POST", f"{BACKEND_URL}/vacantes", data={
        "titulo": "Frontend Developer - React",
        "descripcion": "Buscamos desarrollador Frontend con experiencia en diseño de interfaces y componentes.",
        "requisitos": ["React", "JavaScript", "CSS", "Tailwind", "Experiencia de 2 años"],
        "ubicacion": "Madrid",
        "categoria": "Desarrollo",
        "salario_min": 2000,
        "salario_max": 3500
    }, headers=company_headers)
    print("Vacante publicada:", vacante_no_match["id"])
    
    # 9. Obtener recomendaciones
    print("Obteniendo recomendaciones para el candidato (esperando 2 segs para el procesamiento asincrónico si lo hubiera)...")
    time.sleep(2)
    recomendaciones = request("GET", f"{BACKEND_URL}/recomendaciones/candidato/{candidate['id']}", headers=candidate_headers)
    print(f"Recomendaciones ({len(recomendaciones)}):")
    for rec in recomendaciones:
        print(f"- {rec['titulo']} (Score: {rec['score_similitud']:.4f}): {rec['explicacion']}")
        
if __name__ == "__main__":
    test_flow()
