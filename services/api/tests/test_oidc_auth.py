import pytest
from oidc_auth import OIDCConfigurationError, OIDCVerifier

def test_oidc_verifier_is_optional_when_not_configured(monkeypatch):
    for name in ("ORIOM7_OIDC_ISSUER","ORIOM7_OIDC_AUDIENCE","ORIOM7_OIDC_JWKS_URL","ORIOM7_OIDC_CLIENT_ID"):
        monkeypatch.delenv(name,raising=False)
    assert OIDCVerifier.from_env() is None

def test_oidc_verifier_requires_complete_configuration(monkeypatch):
    monkeypatch.setenv("ORIOM7_OIDC_ISSUER","https://issuer.example")
    monkeypatch.setenv("ORIOM7_OIDC_AUDIENCE","oriom7-api")
    monkeypatch.delenv("ORIOM7_OIDC_JWKS_URL",raising=False)
    with pytest.raises(OIDCConfigurationError):
        OIDCVerifier.from_env()

def test_oidc_verifier_rejects_http_issuer(monkeypatch):
    monkeypatch.setenv("ORIOM7_OIDC_ISSUER","http://issuer.example")
    monkeypatch.setenv("ORIOM7_OIDC_AUDIENCE","oriom7-api")
    monkeypatch.setenv("ORIOM7_OIDC_JWKS_URL","https://issuer.example/jwks")
    monkeypatch.setenv("ORIOM7_OIDC_CLIENT_ID","oriom7-web")
    with pytest.raises(OIDCConfigurationError):
        OIDCVerifier.from_env()
