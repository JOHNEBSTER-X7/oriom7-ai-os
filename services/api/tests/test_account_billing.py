from fastapi.testclient import TestClient
from main import app

client=TestClient(app)

def test_plan_catalogue_is_explicitly_unconfigured():
 response=client.get("/v1/account/plans")
 assert response.status_code==200
 body=response.json()
 assert body["billing_status"]=="not_configured"
 assert body["checkout_enabled"] is False
 assert {p["plan_code"] for p in body["plans"]}=={"starter","builder","business","enterprise"}
 assert body["plans"][1]["price_minor"] is None

def test_private_account_routes_require_trusted_identity():
 for path in ("/v1/account/profile","/v1/account/subscription","/v1/account/invoices","/v1/account/organisations","/v1/account/usage"):
  assert client.get(path).status_code==401

def test_organisation_creation_requires_trusted_identity():
 response=client.post("/v1/account/organisations",json={"name":"Example Team","slug":"example-team"})
 assert response.status_code==401
