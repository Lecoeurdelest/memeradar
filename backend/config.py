import os
from pathlib import Path

from dotenv import load_dotenv


_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV_PATH)


_REQUIRED_KEYS = [
    "REDDIT_CLIENT_ID",
    "REDDIT_CLIENT_SECRET",
    "TL_API_KEY",
    "MISTRAL_API_KEY",
    "NEO4J_PASSWORD",
]


def _validate():
    missing = [k for k in _REQUIRED_KEYS if not os.getenv(k)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Copy backend/.env.example to backend/.env and fill in all required values."
        )


_validate()


REDDIT_CLIENT_ID = os.environ["REDDIT_CLIENT_ID"]
REDDIT_CLIENT_SECRET = os.environ["REDDIT_CLIENT_SECRET"]
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "memeradar/0.1")
SUBREDDIT = os.getenv("SUBREDDIT", "memes")
TIME_FILTER = os.getenv("TIME_FILTER", "year")
LIMIT = int(os.getenv("LIMIT", "1000"))

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "memeradar")

TL_API_KEY = os.environ["TL_API_KEY"]
TL_MODEL = os.getenv("TL_MODEL", "Marengo-retrieval-2.7")

MISTRAL_API_KEY = os.environ["MISTRAL_API_KEY"]
MISTRAL_CHAT_MODEL = os.getenv("MISTRAL_CHAT_MODEL", "mistral-large-latest")
MISTRAL_EMBED_MODEL = os.getenv("MISTRAL_EMBED_MODEL", "mistral-embed")
MISTRAL_VISION_MODEL = os.getenv("MISTRAL_VISION_MODEL", "pixtral-12b-2409")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.environ["NEO4J_PASSWORD"]

COGNEE_LLM_API_KEY = os.getenv("COGNEE_LLM_API_KEY", "") or MISTRAL_API_KEY

DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))

DATA_DIR.mkdir(parents=True, exist_ok=True)
(DATA_DIR / "images").mkdir(parents=True, exist_ok=True)

NEAR_DUPLICATE_THRESHOLD = float(os.getenv("NEAR_DUPLICATE_THRESHOLD", "0.92"))
UPLOAD_MAX_BYTES = int(os.getenv("UPLOAD_MAX_BYTES", str(8 * 1024 * 1024)))
UPLOAD_ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
UPLOAD_MIME_TO_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
UPLOAD_TOPK = int(os.getenv("UPLOAD_TOPK", "5"))
