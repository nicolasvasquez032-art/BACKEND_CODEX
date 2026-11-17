import html
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from infrastructure.api.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_download_cv_path_traversal_blocked(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Intento de path traversal
        resp = await client.get("/api/v1/cvs/download/..%2F..%2Fetc%2Fpasswd")
        assert resp.status_code in (400, 404)

        resp2 = await client.get("/api/v1/cvs/download/invalid_file.txt")
        assert resp2.status_code in (400, 404)


@pytest.mark.asyncio
async def test_download_cv_not_found(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/cvs/download/nonexistent_test_cv_12345.pdf")
        assert resp.status_code == 404
        assert "no encontrado" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_download_cv_success(app, tmp_path):
    upload_dir = Path("uploads/cvs")
    upload_dir.mkdir(parents=True, exist_ok=True)
    test_pdf = upload_dir / "test_sonar_dummy_cv.pdf"
    test_pdf.write_bytes(b"%PDF-1.4 dummy pdf content for test")

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/cvs/download/test_sonar_dummy_cv.pdf")
            assert resp.status_code == 200
            assert resp.content == b"%PDF-1.4 dummy pdf content for test"
            assert resp.headers["content-type"] == "application/pdf"
    finally:
        if test_pdf.exists():
            test_pdf.unlink()


@pytest.mark.asyncio
async def test_oauth_callback_xss_protection(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Enviar payload malicioso de XSS en parámetro error
        xss_payload = "<script>alert(1)</script>"
        resp = await client.get(
            f"/auth/oauth/google/callback?error={xss_payload}",
            follow_redirects=False,
        )
        assert resp.status_code == 400
        # Verificar que el tag <script> NO esté presente sin escapar
        assert "<script>alert(1)</script>" not in resp.text
        assert "&lt;script&gt;" in resp.text or "<script>" not in resp.text


@pytest.mark.asyncio
async def test_oauth_linkedin_demo_flow(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/auth/oauth/linkedin/authorize?session_id=test_session_123")
        assert resp.status_code == 200
        assert "LinkedIn" in resp.text
        assert "TalentMatch" in resp.text
        assert "Permitir" in resp.text

