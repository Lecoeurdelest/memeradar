from __future__ import annotations

import base64
import io
from pathlib import Path

import httpx
from mistralai import Mistral
from neo4j import AsyncGraphDatabase
from PIL import Image
from qdrant_client import AsyncQdrantClient, models

from backend import config


TL_EMBED_SUPPORTED_MIME = {"image/jpeg", "image/png"}


_qdrant: AsyncQdrantClient | None = None
_mistral: Mistral | None = None
_neo4j_driver = None
_tl_client: httpx.AsyncClient | None = None

MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def get_qdrant() -> AsyncQdrantClient:
    global _qdrant
    if _qdrant is None:
        _qdrant = AsyncQdrantClient(
            url=config.QDRANT_URL,
            api_key=config.QDRANT_API_KEY or None,
        )
    return _qdrant


def get_mistral() -> Mistral:
    global _mistral
    if _mistral is None:
        _mistral = Mistral(api_key=config.MISTRAL_API_KEY)
    return _mistral


def get_neo4j_driver():
    global _neo4j_driver
    if _neo4j_driver is None:
        _neo4j_driver = AsyncGraphDatabase.driver(
            config.NEO4J_URI,
            auth=(config.NEO4J_USER, config.NEO4J_PASSWORD),
        )
    return _neo4j_driver


def get_tl_client() -> httpx.AsyncClient:
    global _tl_client
    if _tl_client is None:
        _tl_client = httpx.AsyncClient(
            base_url="https://api.twelvelabs.io/v1.3",
            headers={"x-api-key": config.TL_API_KEY},
            timeout=120.0,
        )
    return _tl_client


TL_VECTOR_DIM = 1024
MISTRAL_VECTOR_DIM = 1024


async def ensure_collection() -> None:
    client = get_qdrant()
    exists = await client.collection_exists(config.QDRANT_COLLECTION)
    if exists:
        return
    await client.create_collection(
        collection_name=config.QDRANT_COLLECTION,
        vectors_config={
            "visual": models.VectorParams(size=TL_VECTOR_DIM, distance=models.Distance.COSINE),
            "irony": models.VectorParams(size=MISTRAL_VECTOR_DIM, distance=models.Distance.COSINE),
        },
    )
    for field_name, field_type in [
        ("template", models.PayloadSchemaType.KEYWORD),
        ("psychological_state", models.PayloadSchemaType.KEYWORD),
        ("subtext_context", models.PayloadSchemaType.KEYWORD),
        ("source_subreddit", models.PayloadSchemaType.KEYWORD),
        ("upvotes", models.PayloadSchemaType.INTEGER),
        ("image_sha256", models.PayloadSchemaType.KEYWORD),
    ]:
        await client.create_payload_index(
            config.QDRANT_COLLECTION, field_name, field_type,
        )


async def ensure_sha256_index() -> None:
    client = get_qdrant()
    try:
        await client.create_payload_index(
            config.QDRANT_COLLECTION,
            "image_sha256",
            models.PayloadSchemaType.KEYWORD,
        )
    except Exception:
        pass


async def ensure_mutation_indexes() -> None:
    client = get_qdrant()
    specs = [
        ("template", models.PayloadSchemaType.KEYWORD),
        ("indexed_at", models.PayloadSchemaType.INTEGER),
        ("template_drift_score", models.PayloadSchemaType.FLOAT),
        ("trending_mutation", models.PayloadSchemaType.BOOL),
    ]
    for field_name, field_type in specs:
        try:
            await client.create_payload_index(config.QDRANT_COLLECTION, field_name, field_type)
        except Exception:
            pass


async def qdrant_distinct_templates(batch: int = 256) -> list[str]:
    client = get_qdrant()
    seen: set[str] = set()
    offset = None
    while True:
        points, next_offset = await client.scroll(
            collection_name=config.QDRANT_COLLECTION,
            limit=batch,
            offset=offset,
            with_payload=["template"],
            with_vectors=False,
        )
        for p in points:
            template = (p.payload or {}).get("template")
            if template:
                seen.add(template)
        if next_offset is None:
            break
        offset = next_offset
    return sorted(seen)


async def qdrant_scroll_template_members(template: str, batch: int) -> list[dict]:
    client = get_qdrant()
    members: list[dict] = []
    offset = None
    template_filter = models.Filter(
        must=[models.FieldCondition(key="template", match=models.MatchValue(value=template))]
    )
    while True:
        points, next_offset = await client.scroll(
            collection_name=config.QDRANT_COLLECTION,
            scroll_filter=template_filter,
            limit=batch,
            offset=offset,
            with_payload=["indexed_at"],
            with_vectors=["visual"],
        )
        for p in points:
            vectors = p.vector if isinstance(p.vector, dict) else {}
            members.append({
                "id": str(p.id),
                "visual": vectors.get("visual"),
                "indexed_at": (p.payload or {}).get("indexed_at"),
            })
        if next_offset is None:
            break
        offset = next_offset
    return members


async def qdrant_set_payload_fields(point_id: str, fields: dict) -> None:
    client = get_qdrant()
    await client.set_payload(
        collection_name=config.QDRANT_COLLECTION,
        payload=fields,
        points=[point_id],
    )


async def qdrant_scroll_by_sha256(sha256: str) -> dict | None:
    client = get_qdrant()
    points, _ = await client.scroll(
        collection_name=config.QDRANT_COLLECTION,
        scroll_filter=models.Filter(
            must=[models.FieldCondition(key="image_sha256", match=models.MatchValue(value=sha256))]
        ),
        limit=1,
        with_payload=True,
        with_vectors=False,
    )
    if not points:
        return None
    p = points[0]
    return {"id": str(p.id), "payload": p.payload}


async def tl_embed_image_file(image_path: Path) -> list[float]:
    client = get_tl_client()
    ext = image_path.suffix.lower()
    mime = MIME_MAP.get(ext, "image/jpeg")
    image_bytes = image_path.read_bytes()
    upload_name = image_path.name
    if mime not in TL_EMBED_SUPPORTED_MIME:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        image_bytes = buf.getvalue()
        mime = "image/png"
        upload_name = f"{image_path.stem}.png"
    response = await client.post(
        "/embed",
        data={"model_name": config.TL_MODEL},
        files={"image_file": (upload_name, image_bytes, mime)},
    )
    response.raise_for_status()
    data = response.json()
    img = data.get("image_embedding") or data.get("video_embedding") or data
    segs = img.get("segments") if isinstance(img, dict) else None
    if not segs:
        raise RuntimeError(f"twelvelabs response missing segments: keys={list(data.keys())} body={str(data)[:400]}")
    seg = segs[0]
    vec = seg.get("float") or seg.get("embeddings_float") or seg.get("embedding")
    if not vec:
        raise RuntimeError(f"twelvelabs segment missing vector: keys={list(seg.keys())}")
    return vec


async def tl_embed_text(text: str) -> list[float]:
    client = get_tl_client()
    response = await client.post(
        "/embed",
        files=[
            ("model_name", (None, config.TL_MODEL)),
            ("text", (None, text)),
        ],
    )
    response.raise_for_status()
    data = response.json()
    seg = data["text_embedding"]["segments"][0]
    return seg.get("float", seg.get("embeddings_float"))


async def mistral_embed(text: str) -> list[float]:
    client = get_mistral()
    response = await client.embeddings.create_async(
        model=config.MISTRAL_EMBED_MODEL,
        inputs=[text],
    )
    return list(response.data[0].embedding)


VISION_DESCRIBE_PROMPT = (
    "You are analyzing a meme image. In 2-4 sentences, describe what is literally visible: "
    "characters, expressions, setting, any visible text, layout/panels, and notable visual style. "
    "Be concrete and concise. Plain text only, no preamble."
)


async def mistral_vision_describe(image_path: Path) -> str:
    ext = image_path.suffix.lower()
    mime = MIME_MAP.get(ext, "image/jpeg")
    image_bytes = image_path.read_bytes()
    if mime not in {"image/jpeg", "image/png"}:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        image_bytes = buf.getvalue()
        mime = "image/png"
    b64 = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime};base64,{b64}"
    client = get_mistral()
    response = await client.chat.complete_async(
        model=config.MISTRAL_VISION_MODEL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": VISION_DESCRIBE_PROMPT},
                {"type": "image_url", "image_url": data_url},
            ],
        }],
        temperature=0.2,
        max_tokens=300,
    )
    return (response.choices[0].message.content or "").strip()


async def mistral_chat_json(
    messages: list[dict],
    temperature: float,
    max_tokens: int | None = None,
) -> str:
    client = get_mistral()
    response = await client.chat.complete_async(
        model=config.MISTRAL_CHAT_MODEL,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


async def qdrant_upsert_point(
    point_id: str,
    visual_vec: list[float],
    irony_vec: list[float],
    payload: dict,
) -> None:
    client = get_qdrant()
    await client.upsert(
        collection_name=config.QDRANT_COLLECTION,
        points=[
            models.PointStruct(
                id=point_id,
                vector={"visual": visual_vec, "irony": irony_vec},
                payload=payload,
            )
        ],
    )


async def neo4j_upsert_meme(
    meme_id: str,
    template: str,
    title: str,
    upvotes: int,
    permalink: str,
    core_joke: str,
    image_path: str,
) -> None:
    driver = get_neo4j_driver()
    query = (
        "MERGE (t:MemeTemplate {name: $template}) "
        "ON CREATE SET t.created_at = timestamp() "
        "MERGE (m:Meme {id: $meme_id}) "
        "SET m.title = $title, m.upvotes = $upvotes, m.permalink = $permalink, "
        "    m.core_joke = $core_joke, m.image_path = $image_path "
        "MERGE (m)-[:USES_TEMPLATE]->(t)"
    )
    async with driver.session() as session:
        result = await session.run(
            query,
            meme_id=meme_id,
            template=template,
            title=title,
            upvotes=upvotes,
            permalink=permalink,
            core_joke=core_joke,
            image_path=image_path,
        )
        await result.consume()


async def neo4j_merge_variation(template_a: str, template_b: str) -> None:
    driver = get_neo4j_driver()
    query = (
        "MATCH (a:MemeTemplate {name: $a}), (b:MemeTemplate {name: $b}) "
        "MERGE (a)-[:VARIATION_OF]-(b)"
    )
    async with driver.session() as session:
        result = await session.run(query, a=template_a, b=template_b)
        await result.consume()


async def neo4j_upsert_caption(
    meme_id: str,
    lang: str,
    core_joke: str,
    psychological_state: str,
    subtext_context: str,
    search_dense_explanations: str,
) -> None:
    driver = get_neo4j_driver()
    query = (
        "MATCH (m:Meme {id: $meme_id}) "
        "MERGE (c:MemeCaption {meme_id: $meme_id, lang: $lang}) "
        "SET c.core_joke = $core_joke, "
        "    c.psychological_state = $psychological_state, "
        "    c.subtext_context = $subtext_context, "
        "    c.search_dense_explanations = $search_dense_explanations, "
        "    c.updated_at = timestamp() "
        "MERGE (m)-[:HAS_CAPTION]->(c)"
    )
    async with driver.session() as session:
        result = await session.run(
            query,
            meme_id=meme_id,
            lang=lang,
            core_joke=core_joke,
            psychological_state=psychological_state,
            subtext_context=subtext_context,
            search_dense_explanations=search_dense_explanations,
        )
        await result.consume()


async def neo4j_get_caption(meme_id: str, lang: str) -> dict | None:
    driver = get_neo4j_driver()
    query = (
        "MATCH (m:Meme {id: $meme_id})-[:HAS_CAPTION]->(c:MemeCaption {lang: $lang}) "
        "RETURN c.core_joke AS core_joke, "
        "       c.psychological_state AS psychological_state, "
        "       c.subtext_context AS subtext_context"
    )
    async with driver.session() as session:
        result = await session.run(query, meme_id=meme_id, lang=lang)
        record = await result.single()
        if not record:
            return None
        return {
            "core_joke": record["core_joke"],
            "psychological_state": record["psychological_state"],
            "subtext_context": record["subtext_context"],
        }


async def neo4j_lineage(meme_id: str) -> dict:
    driver = get_neo4j_driver()
    query = (
        "MATCH (m:Meme {id: $meme_id})-[:USES_TEMPLATE]->(t:MemeTemplate) "
        "OPTIONAL MATCH (t)-[:VARIATION_OF*0..2]-(sib:MemeTemplate) "
        "WHERE sib <> t "
        "RETURN t.name AS template, collect(DISTINCT sib.name) AS variants"
    )
    async with driver.session() as session:
        result = await session.run(query, meme_id=meme_id)
        record = await result.single()
        if not record:
            return {"template": None, "variants": []}
        return {"template": record["template"], "variants": record["variants"]}


async def neo4j_get_template_centroid(template: str) -> dict | None:
    driver = get_neo4j_driver()
    query = (
        "MATCH (t:MemeTemplate {name: $template}) "
        "RETURN t.centroid_visual AS centroid_visual, "
        "       t.historical_centroid_visual AS historical_centroid_visual, "
        "       t.velocity AS velocity, "
        "       t.centroid_computed_at AS centroid_computed_at"
    )
    async with driver.session() as session:
        result = await session.run(query, template=template)
        record = await result.single()
        if not record:
            return None
        return {
            "centroid_visual": record["centroid_visual"],
            "historical_centroid_visual": record["historical_centroid_visual"],
            "velocity": record["velocity"],
            "centroid_computed_at": record["centroid_computed_at"],
        }


async def neo4j_set_template_centroid(
    template: str,
    centroid_visual: list[float] | None,
    historical_centroid_visual: list[float] | None,
    velocity: float,
    computed_at: int,
    member_count: int,
) -> None:
    driver = get_neo4j_driver()
    query = (
        "MERGE (t:MemeTemplate {name: $template}) "
        "ON CREATE SET t.created_at = timestamp() "
        "SET t.centroid_visual = $centroid_visual, "
        "    t.historical_centroid_visual = $historical_centroid_visual, "
        "    t.velocity = $velocity, "
        "    t.centroid_computed_at = $computed_at, "
        "    t.member_count = $member_count"
    )
    async with driver.session() as session:
        result = await session.run(
            query,
            template=template,
            centroid_visual=centroid_visual,
            historical_centroid_visual=historical_centroid_visual,
            velocity=velocity,
            computed_at=computed_at,
            member_count=member_count,
        )
        await result.consume()


async def neo4j_list_template_metrics() -> list[dict]:
    driver = get_neo4j_driver()
    query = (
        "MATCH (t:MemeTemplate) "
        "WHERE t.centroid_computed_at IS NOT NULL "
        "RETURN t.name AS template, "
        "       coalesce(t.velocity, 0.0) AS velocity, "
        "       coalesce(t.member_count, 0) AS member_count "
        "ORDER BY velocity DESC, template ASC"
    )
    async with driver.session() as session:
        result = await session.run(query)
        records = [r async for r in result]
        return [
            {
                "template": r["template"],
                "velocity": r["velocity"],
                "member_count": r["member_count"],
            }
            for r in records
        ]


async def scroll_all_payloads() -> list[dict]:
    client = get_qdrant()
    results = []
    offset = None
    while True:
        points, next_offset = await client.scroll(
            collection_name=config.QDRANT_COLLECTION,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        results.extend([p.payload for p in points])
        if next_offset is None:
            break
        offset = next_offset
    return results


async def close_all() -> None:
    global _qdrant, _neo4j_driver, _tl_client
    if _qdrant:
        await _qdrant.close()
        _qdrant = None
    if _neo4j_driver:
        await _neo4j_driver.close()
        _neo4j_driver = None
    if _tl_client:
        await _tl_client.aclose()
        _tl_client = None
