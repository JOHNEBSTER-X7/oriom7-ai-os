from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_developer_product_catalogue_is_explicit_about_readiness():
    response = client.get("/v1/developer/products")
    assert response.status_code == 200
    products = {item["code"]: item for item in response.json()["products"]}
    assert {"translation", "ocr", "speech", "text_to_speech", "embeddings", "multilingual_search"} <= set(products)
    assert products["embeddings"]["status"] == "preview"
    assert products["translation"]["status"] == "planned"
    assert response.json()["billing_status"] == "not_configured"

def test_embedding_api_requires_developer_key():
    response = client.post("/v1/embeddings/text", json={"input": "hello"})
    assert response.status_code == 401

def test_developer_key_creation_requires_trusted_identity():
    response = client.post("/v1/developer/keys", json={"name": "test key"})
    assert response.status_code == 401

def test_developer_api_key_is_not_mistaken_for_oidc_bearer_token():
    response=client.get("/v1/developer/usage",headers={"Authorization":"Bearer oriom_live_short"})
    assert response.status_code==401
