import asyncio
from backend.clients import get_neo4j_driver

async def check():
    driver = get_neo4j_driver()
    async with driver.session() as s:
        r = await s.run("MATCH (m:Meme) WHERE NOT (m)-[:USES_TEMPLATE]->() RETURN count(m) AS n")
        print("Memes missing template:", (await r.single())["n"])

        r = await s.run("MATCH (m:Meme) WHERE NOT (m)-[:HAS_CAPTION]->() RETURN count(m) AS n")
        print("Memes missing any caption:", (await r.single())["n"])

        r = await s.run("MATCH (c:MemeCaption) RETURN c.lang AS lang, count(c) AS n ORDER BY lang")
        rows = await r.data()
        print("Captions per language:")
        for row in rows:
            print(f"  {row['lang']}: {row['n']} / 100")

    await driver.close()

asyncio.run(check())
