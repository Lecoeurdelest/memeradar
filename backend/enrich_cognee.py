from __future__ import annotations

import asyncio
import os

import cognee

from backend import config
from backend.clients import close_all, neo4j_merge_variation, scroll_all_payloads


os.environ["LLM_API_KEY"] = config.COGNEE_LLM_API_KEY


async def build_corpus() -> tuple[str, list[str]]:
    payloads = await scroll_all_payloads()
    entries = []
    templates = set()
    for p in payloads:
        template = p.get("template", "unknown")
        templates.add(template)
        entries.append(
            f"Template: {template}. "
            f"{p.get('search_dense_explanations', '')} "
            f"Core joke: {p.get('core_joke', '')}"
        )
    return "\n\n".join(entries), sorted(templates)


async def find_variations(templates: list[str]) -> int:
    linked = 0
    for i, tmpl_a in enumerate(templates):
        try:
            results = await cognee.search("INSIGHTS", query_text=tmpl_a)
        except Exception:
            try:
                results = await cognee.search(query_text=tmpl_a)
            except Exception:
                continue
        result_text = " ".join(str(r) for r in results).lower()
        for tmpl_b in templates[i + 1:]:
            if tmpl_b.lower() in result_text:
                await neo4j_merge_variation(tmpl_a, tmpl_b)
                linked += 1
    return linked


async def run() -> None:
    try:
        await cognee.prune.prune_data()
        await cognee.prune.prune_system(metadata=True)
    except Exception:
        pass

    corpus, templates = await build_corpus()
    print(f"Built corpus from {len(templates)} templates")

    await cognee.add(corpus, dataset_name="memeradar")
    await cognee.cognify()

    linked = await find_variations(templates)
    print(f"Enrichment complete: {linked} VARIATION_OF edges created")

    await close_all()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
