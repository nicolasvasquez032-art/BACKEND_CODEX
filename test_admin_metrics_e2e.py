import json
import subprocess
import time
import urllib.request
import urllib.error
import uuid

BACKEND_URL = "http://localhost:8000"


def request(method, url, data=None, headers=None):
    if headers is None:
        headers = {}
    if data is not None:
        data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as res:
        response_data = res.read().decode("utf-8")
        if response_data:
            return json.loads(response_data)
        return None


def test_admin_flow():
    print("Iniciando prueba E2E del Panel Administrativo...")
    
    # 1. Registrar un usuario que convertiremos en Admin
    admin_email = f"admin_{uuid.uuid4().hex[:6]}@test.com"
    password = "AdminPassword123!"
    
    print(f"Registrando admin (como empresa inicialmente): {admin_email}")
    request("POST", f"{BACKEND_URL}/auth/registro/empresa", data={
        "email": admin_email,
        "password": password
    })
    
    # 2. Actualizar el rol en base de datos usando psql
    print("Actualizando rol a 'admin' en la Base de Datos...")
    subprocess.run([
        "sg", "docker", "-c",
        f"docker compose exec postgres psql -U talentmatch -d talentmatch -c \"UPDATE usuarios SET role = 'ADMIN' WHERE email = '{admin_email}';\""
    ], check=True, stdout=subprocess.DEVNULL)
    
    # 3. Iniciar sesión como Admin
    print("Iniciando sesión como Admin...")
    login_res = request("POST", f"{BACKEND_URL}/auth/login", data={
        "email": admin_email,
        "password": password
    })
    admin_headers = {"Authorization": f"Bearer {login_res['access_token']}"}
    
    # 4. Probar endpoints de métricas
    print("Consultando métricas de resumen...")
    resumen = request("GET", f"{BACKEND_URL}/admin/metricas/resumen", headers=admin_headers)
    print(f"Resumen: {resumen}")
    assert "total_candidatos" in resumen
    
    print("Consultando sectores con demanda...")
    sectores = request("GET", f"{BACKEND_URL}/admin/metricas/sectores-demanda", headers=admin_headers)
    print(f"Sectores con demanda: {sectores}")
    
    print("Consultando tiempo de contratación...")
    tiempo = request("GET", f"{BACKEND_URL}/admin/metricas/tiempo-contratacion", headers=admin_headers)
    print(f"Tiempo promedio: {tiempo}")
    
    print("Consultando efectividad de recomendación...")
    efectividad = request("GET", f"{BACKEND_URL}/admin/metricas/efectividad-recomendacion", headers=admin_headers)
    print(f"Efectividad: {efectividad}")
    
    print("¡Prueba E2E de Panel Administrativo completada con éxito!")


if __name__ == "__main__":
    # Esperar a que los servicios estén listos
    time.sleep(2)
    test_admin_flow()
