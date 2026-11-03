from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="ORIOM7 API", version="1.0.0")


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=10, ge=1, le=50)


@app.get("/v1/status")
async def status() -> dict[str, str]:
    return {"status": "ok", "version": app.version}


@app.post("/v1/search")
async def search(request: SearchRequest) -> dict:
    # Explicit placeholder: replace with the hybrid retrieval planner.
    # Never present placeholder data as real search results.
    return {
        "request_id": "development-placeholder",
        "query": request.query,
        "results": [],
        "status": "not_implemented",
    }
