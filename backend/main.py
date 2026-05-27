from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend import config
from backend.clients import close_all, ensure_collection
from backend.schemas import SearchResponse
from backend.search import Weights, search


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_collection()
    yield
    await close_all()


app = FastAPI(title="MemeRadar", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

images_dir = config.DATA_DIR / "images"
if images_dir.exists():
    app.mount("/static/images", StaticFiles(directory=str(images_dir)), name="images")

_FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/search", response_model=SearchResponse)
async def search_endpoint(
    q: str = Query(..., min_length=1, max_length=400),
    k: int = Query(20, ge=1, le=100),
    visual_weight: float = Query(0.35, ge=0.0, le=1.0),
    irony_weight: float = Query(0.65, ge=0.0, le=1.0),
    template: str | None = Query(None),
    psychological_state: str | None = Query(None),
):
    if visual_weight + irony_weight <= 0:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="visual_weight + irony_weight must be > 0")

    results, w = await search(
        query=q,
        k=k,
        weights=Weights(visual=visual_weight, irony=irony_weight),
        template_filter=template,
        psychological_state_filter=psychological_state,
    )

    return SearchResponse(
        query=q,
        count=len(results),
        weights={"visual": w.visual, "irony": w.irony},
        results=results,
    )


# Serve frontend SPA — must be last
if _FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        return FileResponse(str(_FRONTEND_DIST / "index.html"))
