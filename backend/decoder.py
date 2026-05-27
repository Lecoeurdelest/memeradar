from __future__ import annotations

from . import clients as c


def decode_meme(post_title: str, ocr_text: str) -> dict:
    irony = c.mistral_irony(post_title, ocr_text)
    return {
        "core_joke": irony,
        "psychological_state": "",
        "subtext_context": "",
        "search_dense_explanations": irony,
    }
