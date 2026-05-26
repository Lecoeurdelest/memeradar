"""Thin wrappers around vendor SDKs. One responsibility per function."""
from __future__ import annotations

import pytesseract
from mistralai import Mistral
from neo4j import GraphDatabase
from PIL import Image
from qdrant_client import QdrantClient, models
from twelvelabs import TwelveLabs

from . import config as cfg

# ---------- singletons ----------
qdrant = QdrantClient(url=cfg.QDRANT_URL, api_key=cfg.QDRANT_API_KEY)
tl = TwelveLabs(api_key=cfg.TL_API_KEY)
mistral = Mistral(api_key=cfg.MISTRAL_API_KEY)
neo4j_driver = GraphDatabase.driver(cfg.NEO4J_URI, auth=(cfg.NEO4J_USER, cfg.NEO4J_PASSWORD))


# ---------- OCR ----------
def ocr_image(path: str) -> str:
    """Extract text from a meme image. Empty string if Tesseract finds nothing."""
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            return pytesseract.image_to_string(im).strip()
    except Exception as e:
        print(f"  ocr failed for {path}: {e}")
        return ""


# ---------- Mistral ----------
IRONY_SYSTEM = (
    "You analyze internet memes. Given a meme's post title and OCR-extracted text, "
    "return ONE sentence (max 25 words) describing the underlying joke, irony, or "
    "emotional context. No preamble, no quotes, no hashtags. Output ONLY the sentence."
)


def mistral_irony(post_title: str, ocr_text: str) -> str:
    """Use Mistral chat to compress title + OCR into a single irony/context sentence."""
    user = f"POST TITLE: {post_title}\nOCR TEXT: {ocr_text or '(no text)'}"
    resp = mistral.chat.complete(
        model=cfg.MISTRAL_CHAT_MODEL,
        messages=[
            {"role": "system", "content": IRONY_SYSTEM},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        max_tokens=80,
    )
    return resp.choices[0].message.content.strip()


def mistral_embed(text: str) -> list[float]:
    """Dense text embedding (1024-d)."""
    resp = mistral.embeddings.create(model=cfg.MISTRAL_EMBED_MODEL, inputs=[text])
    return resp.data[0].embedding


# ---------- Twelve Labs ----------
def tl_image_embedding(image_url: str) -> list[float]:
    """1024-d Marengo-retrieval image embedding."""
    res = tl.embed.create(model_name=cfg.TL_MODEL, image_url=image_url)
    return res.image_embedding.segments[0].embeddings_float


def tl_text_embedding(text: str) -> list[float]:
    """Marengo text embedding — lives in the SAME vector space as image embeddings."""
    res = tl.embed.create(model_name=cfg.TL_MODEL, text=text)
    return res.text_embedding.segments[0].embeddings_float


# ---------- Neo4j ----------
TEMPLATE_MERGE = """
MERGE (t:MemeTemplate {name: $template})
ON CREATE SET t.created_at = timestamp()
MERGE (m:Meme {id: $meme_id})
SET m.title = $title, m.upvotes = $upvotes, m.permalink = $permalink,
    m.irony = $irony, m.image_path = $image_path
MERGE (m)-[:USES_TEMPLATE]->(t)
"""

VARIATION_LINK = """
MATCH (a:MemeTemplate {name: $a}), (b:MemeTemplate {name: $b})
MERGE (a)-[:VARIATION_OF]-(b)
"""

LINEAGE_QUERY = """
MATCH (m:Meme {id: $meme_id})-[:USES_TEMPLATE]->(t:MemeTemplate)
OPTIONAL MATCH (t)-[:VARIATION_OF*1..2]-(sib:MemeTemplate)
RETURN t.name AS template, collect(DISTINCT sib.name) AS variants
"""


def neo4j_upsert_meme(meme_id: str, template: str, title: str, upvotes: int,
                      permalink: str, irony: str, image_path: str) -> None:
    with neo4j_driver.session() as s:
        s.run(TEMPLATE_MERGE, meme_id=meme_id, template=template, title=title,
              upvotes=upvotes, permalink=permalink, irony=irony, image_path=image_path)


def neo4j_lineage(meme_id: str) -> dict:
    with neo4j_driver.session() as s:
        rec = s.run(LINEAGE_QUERY, meme_id=meme_id).single()
        if not rec:
            return {"template": None, "variants": []}
        return {"template": rec["template"], "variants": rec["variants"]}


# ---------- Qdrant ----------
def ensure_collection() -> None:
    if qdrant.collection_exists(cfg.COLLECTION):
        return
    qdrant.create_collection(
        collection_name=cfg.COLLECTION,
        vectors_config={
            "visual": models.VectorParams(size=cfg.TL_VECTOR_DIM, distance=models.Distance.COSINE),
            "irony": models.VectorParams(size=cfg.MISTRAL_EMBED_DIM, distance=models.Distance.COSINE),
        },
    )
    # payload indexes for fast filtering
    qdrant.create_payload_index(cfg.COLLECTION, "template", models.PayloadSchemaType.KEYWORD)
    qdrant.create_payload_index(cfg.COLLECTION, "upvotes", models.PayloadSchemaType.INTEGER)
