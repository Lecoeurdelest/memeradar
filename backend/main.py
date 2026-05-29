from __future__ import annotations

import asyncio
import hashlib
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated
from uuid import NAMESPACE_URL, uuid5

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend import config
from backend.clients import (
    close_all,
    ensure_collection,
    ensure_sha256_index,
    qdrant_scroll_by_sha256,
    tl_embed_image_file,
)
from backend.ingest import ingest_upload
from backend.schemas import (
    MemeHit,
    SearchQueryParams,
    SearchResponse,
    UploadCheckResponse,
    UploadIngestRequest,
)
from backend.search import Weights, query_by_visual_vector, search
from backend.clients import neo4j_lineage


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_collection()
    await ensure_sha256_index()
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


def _hit_from_payload(point_id: str, payload: dict, score: float, lineage: dict) -> dict:
    return {
        "id": point_id,
        "score": score,
        "title": payload.get("title", ""),
        "image_url": payload.get("image_url", ""),
        "permalink": payload.get("permalink", ""),
        "upvotes": payload.get("upvotes", 0),
        "template": payload.get("template", ""),
        "core_joke": payload.get("core_joke", ""),
        "psychological_state": payload.get("psychological_state", ""),
        "subtext_context": payload.get("subtext_context", ""),
        "lang": "en",
        "lineage": lineage,
    }


async def _safe_lineage(reddit_id: str) -> dict:
    try:
        return await neo4j_lineage(reddit_id)
    except Exception:
        return {"template": None, "variants": []}


@app.post("/upload/check", response_model=UploadCheckResponse)
async def upload_check(file: UploadFile = File(...)):
    if file.content_type not in config.UPLOAD_ALLOWED_MIME:
        raise HTTPException(status_code=400, detail=f"unsupported content_type: {file.content_type}")

    body = await file.read()
    if len(body) == 0:
        raise HTTPException(status_code=400, detail="empty upload")
    if len(body) > config.UPLOAD_MAX_BYTES:
        raise HTTPException(status_code=400, detail=f"file too large: max {config.UPLOAD_MAX_BYTES} bytes")

    sha = await asyncio.to_thread(lambda: hashlib.sha256(body).hexdigest())
    ext = config.UPLOAD_MIME_TO_EXT[file.content_type]
    stored = config.DATA_DIR / "images" / f"{sha}{ext}"
    if not stored.exists():
        await asyncio.to_thread(stored.write_bytes, body)
    stored_url = f"/static/images/{stored.name}"

    existing = await qdrant_scroll_by_sha256(sha)
    if existing is not None:
        lineage = await _safe_lineage(existing["payload"].get("reddit_id", ""))
        hit = _hit_from_payload(existing["id"], existing["payload"], 1.0, lineage)
        return UploadCheckResponse(
            image_sha256=sha,
            stored_path=stored_url,
            is_exact_duplicate=True,
            is_likely_duplicate=True,
            best_score=1.0,
            matches=[MemeHit(**hit)],
        )

    try:
        visual_vec = await tl_embed_image_file(stored)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"visual embedding failed: {exc}")

    matches = await query_by_visual_vector(visual_vec=visual_vec, k=config.UPLOAD_TOPK)
    best = matches[0]["score"] if matches else 0.0
    return UploadCheckResponse(
        image_sha256=sha,
        stored_path=stored_url,
        is_exact_duplicate=False,
        is_likely_duplicate=best >= config.NEAR_DUPLICATE_THRESHOLD,
        best_score=best,
        matches=[MemeHit(**m) for m in matches],
    )


@app.post("/upload/ingest", response_model=MemeHit)
async def upload_ingest(body: UploadIngestRequest):
    sha = body.image_sha256
    candidates = list((config.DATA_DIR / "images").glob(f"{sha}.*"))
    if not candidates:
        raise HTTPException(status_code=404, detail="image not found; call /upload/check first")
    image_path = candidates[0]

    existing = await qdrant_scroll_by_sha256(sha)
    if existing is not None:
        lineage = await _safe_lineage(existing["payload"].get("reddit_id", ""))
        return MemeHit(**_hit_from_payload(existing["id"], existing["payload"], 1.0, lineage))

    try:
        point_id, ok = await ingest_upload(image_path, sha, body.title)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ingest failed: {exc}")
    if not ok:
        raise HTTPException(status_code=502, detail="ingest quarantined; check server logs")

    reddit_id = f"upload:{sha}"
    fresh = await qdrant_scroll_by_sha256(sha)
    payload = fresh["payload"] if fresh else {}
    lineage = await _safe_lineage(reddit_id)
    return MemeHit(**_hit_from_payload(point_id, payload, 1.0, lineage))


if _FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        return FileResponse(str(_FRONTEND_DIST / "index.html"))
