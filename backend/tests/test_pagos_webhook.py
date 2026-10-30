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
