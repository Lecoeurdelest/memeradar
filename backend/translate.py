from __future__ import annotations

import json

from backend.clients import get_mistral

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
    client = get_mistral()
    source = {k: fields[k] for k in _TRANSLATE_FIELDS if k in fields}
    user_msg = (
        f"Translate the following meme caption fields into {lang_name}.\n\n"
        f"{json.dumps(source, ensure_ascii=False)}"
    )
    response = await client.chat.complete_async(
        model="mistral-large-latest",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    raw = response.choices[0].message.content.strip()
    return json.loads(raw)
