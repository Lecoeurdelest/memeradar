from __future__ import annotations

import json

from backend.clients import mistral_chat_json
from backend.decoder import _coerce_json

SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "ja": "Japanese",
    "pt": "Portuguese",
    "vi": "Vietnamese",
}

_TRANSLATE_FIELDS = ("core_joke", "psychological_state", "subtext_context", "search_dense_explanations")

_SYSTEM_PROMPT = (
    "You are a professional translator specializing in internet culture and memes. "
    "Translate the given JSON fields into the target language. "
    "Preserve tone, humor, and internet slang where possible. "
    "Return ONLY a valid JSON object with the same keys."
)


async def translate_caption(
    fields: dict[str, str],
    target_lang: str,
) -> dict[str, str]:
    lang_name = SUPPORTED_LANGUAGES[target_lang]
    source = {k: fields[k] for k in _TRANSLATE_FIELDS if k in fields}
    user_msg = (
        f"Translate the following meme caption fields into {lang_name}.\n\n"
        f"{json.dumps(source, ensure_ascii=False)}"
    )
    raw = await mistral_chat_json(
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.2,
    )
    return _coerce_json(raw)
