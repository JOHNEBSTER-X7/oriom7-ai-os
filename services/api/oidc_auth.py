"""OIDC JWT authentication for ORIOM7 API requests.

The web application performs the authorization-code + PKCE flow. This API
verifies the resulting access token against the configured issuer, audience
and JWKS endpoint before populating request.state.user_id.
"""
from __future__ import annotations
import json
import os
import time
import asyncio
from typing import Any
import httpx
import jwt
from jwt import PyJWTError
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class OIDCConfigurationError(RuntimeError): pass
class OIDCAuthenticationError(ValueError): pass

class OIDCVerifier:
    def __init__(self, issuer:str, audience:str, jwks_url:str, client_id:str, timeout:float=5.0):
        self.issuer=issuer.rstrip("/")
        self.audience=audience
        self.client_id=client_id
        self.jwks_url=jwks_url
        self.timeout=timeout
        self._keys:dict[str,dict[str,Any]]={}
        self._fetched_at=0.0
        self._lock=asyncio.Lock()

    @classmethod
    def from_env(cls):
        issuer=os.getenv("ORIOM7_OIDC_ISSUER")
        audience=os.getenv("ORIOM7_OIDC_AUDIENCE")
        jwks_url=os.getenv("ORIOM7_OIDC_JWKS_URL")
        client_id=os.getenv("ORIOM7_OIDC_CLIENT_ID")
        configured=[bool(issuer),bool(audience),bool(jwks_url),bool(client_id)]
        if not any(configured): return None
        if not all(configured): raise OIDCConfigurationError("Set ORIOM7_OIDC_ISSUER, ORIOM7_OIDC_AUDIENCE, ORIOM7_OIDC_JWKS_URL and ORIOM7_OIDC_CLIENT_ID together.")
        if not issuer.startswith("https://") or not jwks_url.startswith("https://"):
            raise OIDCConfigurationError("OIDC issuer and JWKS URL must use HTTPS.")
        return cls(issuer,audience,jwks_url,client_id)

    async def _load_keys(self,force:bool=False):
        if self._keys and not force and time.monotonic()-self._fetched_at<600: return
        async with self._lock:
            if self._keys and not force and time.monotonic()-self._fetched_at<600: return
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response=await client.get(self.jwks_url)
                    response.raise_for_status()
                    payload=response.json()
                keys=payload.get("keys",[])
                if not isinstance(keys,list) or not keys: raise ValueError("JWKS has no keys")
                self._keys={item["kid"]:item for item in keys if item.get("kid") and item.get("kty")=="RSA" and item.get("use","sig")=="sig" and item.get("alg","RS256")=="RS256"}
                if not self._keys: raise ValueError("JWKS contains no supported RS256 signing keys")
                self._fetched_at=time.monotonic()
            except Exception as exc:
                raise OIDCAuthenticationError("Unable to retrieve identity-provider signing keys") from exc

    async def _verify_for_audience(self,token:str,audience:str)->dict[str,Any]:
        try:
            header=jwt.get_unverified_header(token)
            if header.get("alg")!="RS256" or not header.get("kid"): raise OIDCAuthenticationError("Unsupported access-token signing algorithm")
            await self._load_keys()
            jwk=self._keys.get(header["kid"])
            if jwk is None:
                await self._load_keys(force=True)
                jwk=self._keys.get(header["kid"])
            if jwk is None: raise OIDCAuthenticationError("Unknown access-token signing key")
            public_key=jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
            claims=jwt.decode(token,public_key,algorithms=["RS256"],audience=audience,issuer=self.issuer,
                              options={"require":["exp","iat","sub"]},leeway=30)
            if not isinstance(claims.get("sub"),str) or not claims["sub"].strip():
                raise OIDCAuthenticationError("Access token has no valid subject")
            return claims
        except OIDCAuthenticationError: raise
        except PyJWTError as exc: raise OIDCAuthenticationError("Access token is invalid or expired") from exc
        except Exception as exc: raise OIDCAuthenticationError("Access token could not be verified") from exc

    async def verify(self,token:str)->dict[str,Any]:
        return await self._verify_for_audience(token,self.audience)

    async def verify_identity_token(self,token:str)->dict[str,Any]:
        return await self._verify_for_audience(token,self.client_id)

class OIDCAuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self,request:Request,call_next):
        authorization=request.headers.get("authorization","")
        if authorization.lower().startswith("bearer ") and not authorization[7:].strip().startswith("oriom_live_"):
            verifier=getattr(request.app.state,"oidc_verifier",None)
            if verifier is None:
                return JSONResponse({"detail":{"code":"identity_provider_not_configured","message":"ORIOM7 identity verification is not configured."}},status_code=503)
            token=authorization[7:].strip()
            try:
                claims=await verifier.verify(token)
            except OIDCAuthenticationError as exc:
                return JSONResponse({"detail":{"code":"authentication_required","message":str(exc)}},status_code=401,headers={"WWW-Authenticate":"Bearer"})
            identity_token=request.headers.get("x-oriom7-id-token")
            if identity_token:
                try:
                    identity_claims=await verifier.verify_identity_token(identity_token)
                except OIDCAuthenticationError:
                    return JSONResponse({"detail":{"code":"authentication_required","message":"Identity claims could not be verified."}},status_code=401,headers={"WWW-Authenticate":"Bearer"})
                if identity_claims.get("sub")!=claims["sub"]:
                    return JSONResponse({"detail":{"code":"authentication_required","message":"Access and identity token subjects do not match."}},status_code=401,headers={"WWW-Authenticate":"Bearer"})
                for claim in ("email","email_verified","name","preferred_username"):
                    if claim in identity_claims:claims[claim]=identity_claims[claim]
            request.state.user_id=claims["sub"]
            request.state.user_claims=claims
        return await call_next(request)
