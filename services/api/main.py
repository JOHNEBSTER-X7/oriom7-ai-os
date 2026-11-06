from contextlib import asynccontextmanager
import os

from fastapi import FastAPI

from accessibility import MemoryProfileStore, PostgresProfileStore, router as accessibility_router
from response_adaptation import router as assistant_accessibility_router
from assistant_generation import router as generation_router, catalog_router as model_catalog_router
from model_orchestration import build_orchestrator_from_env
from retrieval import (PostgresLexicalIndex, RetrievalService, build_external_search_providers_from_env, router as search_router)
from ingestion import router as ingestion_router
from semantic_index import PostgresVectorIndex, build_embedding_provider_from_env
from knowledge_graph import router as knowledge_graph_router
from research_agents import router as research_agents_router
from commercial_api import router as commercial_api_router
from account_billing import router as account_billing_router
from billing import router as billing_router
from translation_api import router as translation_router, build_translation_provider_from_env
from ocr_api import router as ocr_router, build_ocr_provider_from_env
from speech_api import router as speech_router, build_speech_provider_from_env, build_tts_provider_from_env
from voice_intelligence import router as voice_intelligence_router
from oidc_auth import OIDCAuthenticationMiddleware, OIDCVerifier, OIDCConfigurationError


@asynccontextmanager
async def lifespan(application: FastAPI):
    database_url = os.getenv("DATABASE_URL")
    environment = os.getenv("ORIOM7_ENV", "development").lower()
    pool = None
    try:
        application.state.oidc_verifier = OIDCVerifier.from_env()
        if environment == "production" and application.state.oidc_verifier is None:
            raise OIDCConfigurationError("OIDC issuer, API audience and JWKS URL are required in production.")
        if environment == "production" and os.getenv("ORIOM7_ALLOW_DEV_USER_HEADER") == "true":
            raise OIDCConfigurationError("Development identity headers must remain disabled in production.")
    except OIDCConfigurationError as exc:
        raise RuntimeError(str(exc)) from exc
    application.state.model_orchestrator = build_orchestrator_from_env()
    application.state.translation_provider = build_translation_provider_from_env()
    application.state.ocr_provider = build_ocr_provider_from_env()
    application.state.speech_provider = build_speech_provider_from_env()
    application.state.tts_provider = build_tts_provider_from_env()

    if database_url:
        try:
            import asyncpg
        except ImportError as exc:
            raise RuntimeError("Install asyncpg to use DATABASE_URL-backed profile storage.") from exc
        pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
        application.state.database_pool = pool
        application.state.accessibility_profile_store = PostgresProfileStore(pool)
        embedding_provider = build_embedding_provider_from_env()
        semantic_index = PostgresVectorIndex(pool, embedding_provider) if embedding_provider and os.getenv("ORIOM7_SEMANTIC_SEARCH_ENABLED", "false").lower() == "true" else None
        application.state.embedding_provider = embedding_provider
        application.state.retrieval_service = RetrievalService(
            PostgresLexicalIndex(pool), build_external_search_providers_from_env(), semantic_index
        )
    else:
        if environment == "production":
            raise RuntimeError("DATABASE_URL is required in production; refusing ephemeral profile storage.")
        application.state.accessibility_profile_store = MemoryProfileStore()
        application.state.embedding_provider = build_embedding_provider_from_env()
        application.state.retrieval_service = RetrievalService(None, build_external_search_providers_from_env())

    try:
        yield
    finally:
        if pool is not None:
            await pool.close()


app = FastAPI(title="ORIOM7 API", version="1.2.0", lifespan=lifespan)
app.add_middleware(OIDCAuthenticationMiddleware)
app.include_router(accessibility_router)
app.include_router(assistant_accessibility_router)
app.include_router(generation_router)
app.include_router(model_catalog_router)
app.include_router(search_router)
app.include_router(ingestion_router)
app.include_router(knowledge_graph_router)
app.include_router(research_agents_router)
app.include_router(commercial_api_router)
app.include_router(account_billing_router)
app.include_router(billing_router)
app.include_router(translation_router)
app.include_router(ocr_router)
app.include_router(speech_router)
app.include_router(voice_intelligence_router)


@app.get("/v1/status", tags=["system"])
async def status() -> dict[str, str]:
    """Return a minimal liveness response without exposing infrastructure details."""
    return {"status": "ok"}

