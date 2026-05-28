from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import pytesseract
from PIL import Image

from backend.clients import mistral_chat_json
from backend.schemas import MemeDecodeSchema


class DecodeError(Exception):
    pass


DECODE_PROMPT = (
    "You are a meme analyst. Given the meme's post title, OCR-extracted text, "
    "and subreddit, return a JSON object with exactly these keys:\n"
    '- "core_joke": string (max 400 chars) — the central joke or humorous observation\n'
    '- "psychological_state": string (max 120 chars) — the emotional/mental state depicted\n'
    '- "subtext_context": string (max 240 chars) — the cultural or situational subtext\n'
    '- "search_dense_explanations": string (40-800 chars) — detailed searchable explanation '
    "of the meme's humor, context, and cultural significance\n"
    '- "template": string (max 64 chars) — the meme template name '
    "(e.g. 'Distracted Boyfriend', 'Drake Hotline Bling', 'Expanding Brain')\n\n"
    "Title: {title}\n"
    "OCR Text: {ocr_text}\n"
    "Subreddit: r/{subreddit}\n\n"
    "Return ONLY valid JSON. No markdown fences, no preamble."
)


def _coerce_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", raw, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass

    brace_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    raise DecodeError(f"Cannot extract JSON from response: {raw[:200]}")


def _run_tesseract(image_path: Path) -> str:
    img = Image.open(image_path)
    img = img.convert("RGB")
    return pytesseract.image_to_string(img).strip()


async def extract_text(image_path: Path) -> str:
    try:
        text = await asyncio.to_thread(_run_tesseract, image_path)
        return text if text else ""
    except Exception:
        return ""


async def decode_meme(
    title: str,
    ocr_text: str,
    subreddit: str,
) -> tuple[MemeDecodeSchema, str]:
    prompt = DECODE_PROMPT.format(
        title=title,
        ocr_text=ocr_text or "(no text)",
        subreddit=subreddit,
    )

    raw = await mistral_chat_json(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=600,
    )

    data = _coerce_json(raw)

    template = str(data.pop("template", "unknown"))[:64]

    FIELD_LIMITS = {
        "core_joke": 400,
        "psychological_state": 120,
        "subtext_context": 240,
        "search_dense_explanations": 800,
    }
    for field, limit in FIELD_LIMITS.items():
        if field in data and isinstance(data[field], str) and len(data[field]) > limit:
            data[field] = data[field][:limit]

    try:
        schema = MemeDecodeSchema(**data)
    except Exception as e:
        raise DecodeError(f"Schema validation failed: {e}") from e

    return schema, template
