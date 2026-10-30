import hashlib
import hmac
import pytest
from infrastructure.api.routers.pagos import verify_mp_signature

def test_verify_mp_signature_valid():
    secret = "test_webhook_secret_123"
    payment_id = "987654321"
    request_id = "req-abc-xyz"
    ts = "1700000000"

    manifest = f"id:{payment_id};request-id:{request_id};ts:{ts};"
    v1 = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    x_signature = f"ts={ts},v1={v1}"

    assert verify_mp_signature(
        x_signature=x_signature,
        x_request_id=request_id,
        data_id=payment_id,
        secret=secret,
    ) is True

def test_verify_mp_signature_tampered():
    secret = "test_webhook_secret_123"
    payment_id = "987654321"
    request_id = "req-abc-xyz"
    ts = "1700000000"

    x_signature = f"ts={ts},v1=fake_signature_abc_123"

    assert verify_mp_signature(
        x_signature=x_signature,
        x_request_id=request_id,
        data_id=payment_id,
        secret=secret,
    ) is False

def test_verify_mp_signature_empty_secret_allows_pass():
    assert verify_mp_signature(
        x_signature="ts=123,v1=abc",
        x_request_id="req-1",
        data_id="123",
        secret="",
    ) is True


import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from infrastructure.api.routers.pagos import (
    PlanProRequest,
    _get_mp_sdk,
    crear_preferencia_pro,
    mercadopago_webhook,
)
from infrastructure.config import settings


def test_get_mp_sdk_raises_when_no_token():
    with patch.object(settings, "mp_access_token", ""):
        with pytest.raises(HTTPException) as exc_info:
            _get_mp_sdk()
        assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_crear_preferencia_pro_success():
    req = PlanProRequest(empresa_id=str(uuid.uuid4()), email="test@empresa.com")
    mock_sdk = MagicMock()
    mock_sdk.preference().create.return_value = {
        "response": {"id": "pref_123", "init_point": "https://mp.com/pay"}
    }
    with patch("infrastructure.api.routers.pagos._get_mp_sdk", return_value=mock_sdk):
        res = await crear_preferencia_pro(req)
        assert res["id"] == "pref_123"
        assert res["init_point"] == "https://mp.com/pay"


@pytest.mark.asyncio
async def test_crear_preferencia_pro_error():
    req = PlanProRequest(empresa_id=str(uuid.uuid4()), email="test@empresa.com")
    mock_sdk = MagicMock()
    mock_sdk.preference().create.side_effect = RuntimeError("SDK network error")
    with patch("infrastructure.api.routers.pagos._get_mp_sdk", return_value=mock_sdk):
        with pytest.raises(HTTPException) as exc_info:
            await crear_preferencia_pro(req)
        assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_mercadopago_webhook_approved_flow():
    mock_request = MagicMock()
    empresa_id = uuid.uuid4()
    mock_request.json = AsyncMock(
        return_value={"action": "payment.created", "data": {"id": "pay_999"}}
    )
    mock_request.headers = {}
    mock_request.query_params = {}

    mock_db = AsyncMock()
    mock_sdk = MagicMock()
    mock_sdk.payment().get.return_value = {
        "response": {"status": "approved", "external_reference": str(empresa_id)}
    }

    with patch("infrastructure.api.routers.pagos._get_mp_sdk", return_value=mock_sdk), \
         patch("infrastructure.api.routers.pagos.SqlAlchemyUserRepository") as mock_repo_cls:
        mock_repo = AsyncMock()
        mock_repo_cls.return_value = mock_repo
        res = await mercadopago_webhook(request=mock_request, db=mock_db)

        assert res["status"] == "ok"
        mock_repo.mark_user_as_premium.assert_called_once_with(empresa_id)
        mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_mercadopago_webhook_invalid_signature():
    mock_request = MagicMock()
    mock_request.json = AsyncMock(
        return_value={"action": "payment.created", "data": {"id": "pay_999"}}
    )
    mock_request.headers = {"x-signature": "bad_sig", "x-request-id": "req-1"}
    mock_request.query_params = {}
    mock_db = AsyncMock()

    with patch.object(settings, "mp_webhook_secret", "secret_123"):
        res = await mercadopago_webhook(request=mock_request, db=mock_db)
        assert res["status"] == "ignored"
        assert res["reason"] == "invalid_signature"

