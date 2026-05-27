from __future__ import annotations

import asyncio
import json
import os

import cognee

from . import config as cfg

os.environ["GRAPH_DATABASE_PROVIDER"] = "neo4j"
os.environ["GRAPH_DATABASE_URL"] = cfg.NEO4J_URI
os.environ["GRAPH_DATABASE_USERNAME"] = cfg.NEO4J_USER
os.environ["GRAPH_DATABASE_PASSWORD"] = cfg.NEO4J_PASSWORD
os.environ["VECTOR_DB_PROVIDER"] = "qdrant"
os.environ["VECTOR_DB_URL"] = cfg.QDRANT_URL
os.environ["LLM_API_KEY"] = cfg.COGNEE_LLM_API_KEY


async def enrich():
    from .clients import qdrant
    scroll, _ = qdrant.scroll(cfg.COLLECTION, limit=10_000, with_payload=True, with_vectors=False)
    docs = [
        f"Template: {p.payload['template']}. Joke: {p.payload['irony']}"
        for p in scroll
    ]
    await cognee.add(docs, dataset_name="memeradar")
    await cognee.cognify(["memeradar"])
    print(f"cognified {len(docs)} meme contexts into the knowledge graph")


if __name__ == "__main__":
    asyncio.run(enrich())
