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

def test_oidc_verifies_access_and_identity_token_audiences(monkeypatch):
    import asyncio
    import time
    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    public_jwk=jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key(),as_dict=True)
    public_jwk.update({"kid":"test-key","use":"sig","alg":"RS256"})
    verifier=OIDCVerifier("https://issuer.example","oriom7-api","https://issuer.example/jwks","oriom7-web")

    async def fake_load_keys(force=False):
        verifier._keys={"test-key":public_jwk}
        verifier._fetched_at=time.monotonic()
    verifier._load_keys=fake_load_keys

    now=int(time.time())
    claims={"iss":"https://issuer.example","sub":"subject-123","iat":now,"exp":now+300}
    access=jwt.encode({**claims,"aud":"oriom7-api"},private_key,algorithm="RS256",headers={"kid":"test-key"})
    identity=jwt.encode({**claims,"aud":"oriom7-web","email":"dev@example.com","email_verified":True},private_key,algorithm="RS256",headers={"kid":"test-key"})
    assert asyncio.run(verifier.verify(access))["sub"]=="subject-123"
    assert asyncio.run(verifier.verify_identity_token(identity))["email_verified"] is True
