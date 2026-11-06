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


@asynccontextmanager
async def lifespan(application: FastAPI):
    database_url = os.getenv("DATABASE_URL")
    environment = os.getenv("ORIOM7_ENV", "development").lower()
    pool = None
    application.state.model_orchestrator = build_orchestrator_from_env()

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


app = FastAPI(title="ORIOM7 API", version="1.1.0", lifespan=lifespan)
app.include_router(accessibility_router)
app.include_router(assistant_accessibility_router)
app.include_router(generation_router)
app.include_router(model_catalog_router)
app.include_router(search_router)
app.include_router(ingestion_router)
app.include_router(knowledge_graph_router)
app.include_router(research_agents_router)
app.include_router(commercial_api_router)


@app.get("/v1/status", tags=["system"])
async def status() -> dict[str, str]:
    """Return a minimal liveness response without exposing infrastructure details."""
    return {"status": "ok"}

