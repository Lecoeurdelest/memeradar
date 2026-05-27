import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION = os.getenv("QDRANT_COLLECTION", "memeradar")

TL_API_KEY = os.environ["TL_API_KEY"]
TL_MODEL = os.getenv("TL_MODEL", "Marengo-retrieval-2.7")
TL_VECTOR_DIM = 1024

MISTRAL_API_KEY = os.environ["MISTRAL_API_KEY"]
MISTRAL_CHAT_MODEL = os.getenv("MISTRAL_CHAT_MODEL", "mistral-large-latest")
MISTRAL_EMBED_MODEL = os.getenv("MISTRAL_EMBED_MODEL", "mistral-embed")
MISTRAL_EMBED_DIM = 1024

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ["NEO4J_PASSWORD"]

COGNEE_LLM_API_KEY = os.getenv("COGNEE_LLM_API_KEY", MISTRAL_API_KEY)

DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
META_FILE = DATA_DIR / "memes.json"

PUBLIC_IMAGE_BASE = os.getenv("PUBLIC_IMAGE_BASE", "http://localhost:8000/static/images")
