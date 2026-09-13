import pytest
from httpx import AsyncClient
from uuid import UUID

from tests.utils import random_email


@pytest.mark.asyncio
async def test_notificacion_al_publicar_vacante(async_client: AsyncClient):
    # 1. Registrar empresa y hacer login
    empresa_email = random_email()
    password = "Password123*"
    reg_resp = await async_client.post(
        "/auth/registro/empresa",
        json={
            "email": empresa_email,
            "password": password,
            "nombre": "Empresa Test Notif",
            "sitio_web": "http://testnotif.com",
            "sector": "TI"
        }
    )
    if reg_resp.status_code != 201:
        print(f"Register failed: {reg_resp.status_code} - {reg_resp.text}")
    resp = await async_client.post(
        "/auth/login",
        json={"email": empresa_email, "password": password}
    )
    if resp.status_code != 200:
        print(f"Login failed: {resp.status_code} - {resp.text}")
    token_empresa = resp.json()["access_token"]
    headers_empresa = {"Authorization": f"Bearer {token_empresa}"}

    # 2. Registrar candidato, hacer login y configurar perfil
    candidato_email = random_email()
    candidato_reg_resp = await async_client.post(
        "/auth/registro/candidato",
        json={
            "email": candidato_email,
            "password": password,
            "full_name": "Candidato Notif",
            "skills": ["Python", "FastAPI"],
            "experience_years": 2,
            "location": "Bogotá"
        }
    )
    if candidato_reg_resp.status_code != 201:
        print(f"Candidate register failed: {candidato_reg_resp.status_code} - {candidato_reg_resp.text}")
    resp = await async_client.post(
        "/auth/login",
        json={"email": candidato_email, "password": password}
    )
    token_candidato = resp.json()["access_token"]
    headers_candidato = {"Authorization": f"Bearer {token_candidato}"}
    perfil_id = candidato_reg_resp.json()["id"]
    resp = await async_client.put(
        f"/perfiles/{perfil_id}",
        headers=headers_candidato,
        json={
            "full_name": "Candidato Notif",
            "skills": ["Python", "FastAPI", "PostgreSQL"],
            "experience_years": 5,
            "location": "Remoto",
            "education": "Ingeniero"
        }
    )
    assert resp.status_code == 200
    
    # 3. Registrar token de dispositivo para el candidato
    import uuid
    device_token = f"token-test-{uuid.uuid4()}"
    resp = await async_client.post(
        "/notificaciones/token-dispositivo",
        headers=headers_candidato,
        json={
            "token": device_token,
            "dispositivo_info": "iPhone 12"
        }
    )
    assert resp.status_code == 200

    # 4. Publicar vacante afín (desde empresa)
    resp = await async_client.post(
        "/vacantes",
        headers=headers_empresa,
        json={
            "titulo": "Desarrollador Python Senior",
            "descripcion": "Buscamos experto en Python y FastAPI.",
            "requisitos": ["Python", "FastAPI", "PostgreSQL"],
            "ubicacion": "Remoto",
            "categoria": "Backend",
            "salario_min": 3000,
            "salario_max": 5000,
            "latitud": 40.4168,
            "longitud": -3.7038
        }
    )
    assert resp.status_code == 201

    # 5. Comprobar notificaciones del candidato
    # Como la vacante se publica asíncronamente en el use_case, el await de get_match_candidatos se hace en el flujo.
    # Por lo tanto las notificaciones ya deberían estar generadas.
    candidato_user_id = candidato_reg_resp.json()["user_id"]

    resp = await async_client.get(
        f"/notificaciones/usuario/{candidato_user_id}",
        headers=headers_candidato
    )
    assert resp.status_code == 200
    notificaciones = resp.json()
    assert len(notificaciones) > 0
    assert notificaciones[0]["tipo"] == "NUEVA_VACANTE"
    assert notificaciones[0]["leido"] == False

    # 6. Marcar como leída
    notif_id = notificaciones[0]["id"]
    resp = await async_client.patch(
        f"/notificaciones/{notif_id}/leida",
        headers=headers_candidato
    )
    assert resp.status_code == 200
    
    resp = await async_client.get(
        f"/notificaciones/usuario/{candidato_user_id}",
        headers=headers_candidato
    )
    assert resp.json()[0]["leido"] == True
