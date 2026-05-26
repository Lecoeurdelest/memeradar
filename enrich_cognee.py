"""Optional: enrich the Neo4j graph with Cognee's entity/relationship extraction.

Run this AFTER ingest.py. Cognee will read the corpus of irony sentences,
auto-extract entities (e.g. 'production crash', 'monday', 'manager'), and link
templates that share entities — surfacing variation lineage that flair alone misses.
"""
from __future__ import annotations

import asyncio
import json
import os

import cognee

from . import config as cfg

# Tell Cognee to write the graph into our Neo4j and use Qdrant for its own vectors
os.environ["GRAPH_DATABASE_PROVIDER"] = "neo4j"
os.environ["GRAPH_DATABASE_URL"] = cfg.NEO4J_URI
os.environ["GRAPH_DATABASE_USERNAME"] = cfg.NEO4J_USER
os.environ["GRAPH_DATABASE_PASSWORD"] = cfg.NEO4J_PASSWORD
os.environ["VECTOR_DB_PROVIDER"] = "qdrant"
os.environ["VECTOR_DB_URL"] = cfg.QDRANT_URL
os.environ["LLM_API_KEY"] = cfg.COGNEE_LLM_API_KEY


async def enrich():
    from .clients import qdrant
    # Pull every meme's irony sentence + template as a small document
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
