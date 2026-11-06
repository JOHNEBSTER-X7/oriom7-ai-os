import json
import time
import hmac
import hashlib
from fastapi.testclient import TestClient
from main import app
from billing import _verify_signature, stripe_ready

client=TestClient(app)

def test_stripe_not_ready_without_credentials(monkeypatch):
    for name in ("STRIPE_SECRET_KEY","STRIPE_WEBHOOK_SECRET","ORIOM7_STRIPE_PRICE_BUILDER_MONTHLY","ORIOM7_STRIPE_PRICE_BUSINESS_MONTHLY"):
        monkeypatch.delenv(name,raising=False)
    assert stripe_ready() is False

def test_stripe_webhook_signature_validation():
    body=b'{"id":"evt_test","type":"test.event"}'
    timestamp=int(time.time())
    secret="whsec_test"
    digest=hmac.new(secret.encode(),str(timestamp).encode()+b"."+body,hashlib.sha256).hexdigest()
    assert _verify_signature(body,f"t={timestamp},v1={digest}",secret)
    assert not _verify_signature(body,f"t={timestamp},v1=invalid",secret)

def test_webhook_requires_secret(monkeypatch):
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET",raising=False)
    response=client.post("/v1/billing/webhook",content=b"{}")
    assert response.status_code==503

def test_webhook_rejects_invalid_signature(monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET","whsec_test")
    response=client.post("/v1/billing/webhook",content=json.dumps({"id":"evt_1","type":"test"}),headers={"stripe-signature":"t=1,v1=invalid"})
    assert response.status_code==400

def test_checkout_requires_authenticated_identity(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY","sk_test_example")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET","whsec_example")
    monkeypatch.setenv("ORIOM7_STRIPE_PRICE_BUILDER_MONTHLY","price_builder")
    monkeypatch.setenv("ORIOM7_STRIPE_PRICE_BUSINESS_MONTHLY","price_business")
    response=client.post("/v1/account/checkout",json={"plan_code":"builder"})
    assert response.status_code==401
