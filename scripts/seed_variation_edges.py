from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.clients import close_all, get_neo4j_driver

EDGES = [
    ("expanding_brain", "custom_'escalating_brain_x-ray'_(no_widely_recognized_template_n"),
    ("expanding_brain", "escalation_meme_(text-based_progression)"),
    ("expanding_brain", "meta-meme_(no_specific_template)"),
    ("drake_hotline_bling", "drake_hotline_bling_(or_two-panel_comparison)"),
    ("drake_hotline_bling", "unknown_(likely_drake_hotline_bling_or_two_buttons)"),
    ("woman_yelling_at_cat", "woman_yelling_at_a_cat_(or_similar_two-panel_reaction_template)"),
    ("woman_yelling_at_cat", "two_buttons_/_escalation"),
]


async def main() -> None:
    driver = get_neo4j_driver()
    created = 0
    for tmpl_a, tmpl_b in EDGES:
        query = (
            "MATCH (a:MemeTemplate {name: $a}), (b:MemeTemplate {name: $b}) "
            "MERGE (a)-[:VARIATION_OF]-(b) "
            "RETURN count(*) AS merged"
        )
        async with driver.session() as session:
            result = await session.run(query, a=tmpl_a, b=tmpl_b)
            record = await result.single()
            merged = record["merged"] if record else 0
            status = "linked" if merged else "skipped (node missing)"
            print(f"  {tmpl_a} <-> {tmpl_b}: {status}")
            created += merged
    print(f"\nDone. {created} VARIATION_OF edges created/confirmed.")
    await close_all()


if __name__ == "__main__":
    asyncio.run(main())
