from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend import config
from backend.clients import close_all, ensure_collection
from backend.schemas import SearchQueryParams, SearchResponse
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
async def search_endpoint(params: Annotated[SearchQueryParams, Query()]):
    try:
        results, w = await search(
            query=params.q,
            k=params.k,
            weights=Weights(visual=params.visual_weight, irony=params.irony_weight),
            template_filter=params.template,
            psychological_state_filter=params.psychological_state,
            lang=params.lang,
        )
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"error": "search_unavailable", "detail": "vector store unreachable"},
        )

    return SearchResponse(
        query=params.q,
        count=len(results),
        weights={"visual": w.visual, "irony": w.irony},
        results=results,
    )


if _FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        return FileResponse(str(_FRONTEND_DIST / "index.html"))
