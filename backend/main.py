from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config as cfg
from .search import Weights, search

app = FastAPI(title="MemeRadar")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

images_dir = cfg.DATA_DIR / "images"
if images_dir.exists():
    app.mount("/static/images", StaticFiles(directory=str(images_dir)), name="images")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/search")
def search_endpoint(
    q: str = Query(..., min_length=1),
    k: int = Query(20, ge=1, le=100),
    visual_weight: float = Query(0.35, ge=0.0, le=1.0),
    irony_weight: float = Query(0.65, ge=0.0, le=1.0),
    template: str | None = Query(None),
):
    if not q.strip():
        raise HTTPException(400, "empty query")
    results = search(
        query=q,
        k=k,
        weights=Weights(visual=visual_weight, irony=irony_weight),
        template_filter=template,
    )
    return {"query": q, "count": len(results), "results": results}
