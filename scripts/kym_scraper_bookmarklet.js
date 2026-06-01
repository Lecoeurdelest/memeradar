/**
 * KYM Meme Scraper Bookmarklet
 *
 * Usage:
 *   1. Open https://knowyourmeme.com/memes in Chrome (with VPN)
 *   2. Paste this entire script into the DevTools console (F12 → Console)
 *   3. It will auto-scrape listing pages 3-10, visit each detail page, and download results as JSON
 *
 * To create a bookmarklet, minify this and prefix with "javascript:"
 */

(async function kymScraper() {
  "use strict";

  const BASE = "https://knowyourmeme.com";
  const START_PAGE = 1; // Scans from page 1; EXISTING_URLS filters out duplicates
  const MAX_PAGES = 15;
  const SLEEP_MS = 800; // Polite delay between requests
  const MAX_ENTRIES = 100; // How many new entries to scrape

  const RESULTS = [];
  const SEEN = new Set();

  function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  function parseHTML(html) {
    const doc = new DOMParser().parseFromString(html, "text/html");
    return doc;
  }

  function getMeta(doc, label) {
    for (const dt of doc.querySelectorAll("dt")) {
      if (dt.textContent.trim().toLowerCase().startsWith(label.toLowerCase())) {
        const dd = dt.nextElementSibling;
        if (dd) return dd.textContent.trim();
      }
    }
    return null;
  }

  function getSection(doc, name) {
    for (const h of doc.querySelectorAll("h2,h3")) {
      if (h.textContent.trim().toLowerCase() === name.toLowerCase()) {
        const parts = [];
        let n = h.nextElementSibling;
        while (n && !["H1", "H2"].includes(n.tagName)) {
          if (["P", "BLOCKQUOTE", "UL", "OL"].includes(n.tagName)) {
            const t = n.textContent.trim();
            if (t) parts.push(t);
          }
          n = n.nextElementSibling;
        }
        return parts.join("\n\n") || null;
      }
    }
    return null;
  }

  async function fetchPage(url) {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status} for ${url}`);
    return parseHTML(await resp.text());
  }

  const SKIP_SLUGS = new Set([
    "new",
    "submissions",
    "confirmed",
    "newsworthy",
    "deadpool",
    "memes",
    "page",
    "people",
    "events",
    "subcultures",
    "sites",
    "search",
    "random",
    "trending",
    "top",
    "popular",
  ]);

  async function scrapeListing(pageNum) {
    const url =
      pageNum === 1 ? `${BASE}/memes` : `${BASE}/memes?page=${pageNum}`;
    console.log(`[LISTING] Page ${pageNum}...`);
    const doc = await fetchPage(url);
    const entries = [];
    const seen = new Set();
    for (const a of doc.querySelectorAll('a[href*="/memes/"]')) {
      const href = a.getAttribute("href");
      if (!href || !href.startsWith("/memes/")) continue;
      // Real entry cards have thumbnail images inside the link
      if (!a.querySelector("img")) continue;
      // Must be /memes/slug format (one path segment only)
      const parts = href.replace(/^\/memes\/|\/$/g, "").split("/");
      if (parts.length !== 1) continue;
      // Skip known nav/filter slugs
      if (SKIP_SLUGS.has(parts[0].toLowerCase())) continue;

      const h3 = a.querySelector("h3");
      const title = h3 ? h3.textContent.trim() : (a.textContent || "").trim();
      if (!title || title.length < 3) continue;

      const fullUrl = BASE + href.replace(/\/$/, "");
      if (!seen.has(fullUrl)) {
        seen.add(fullUrl);
        entries.push({ url: fullUrl, title, listing_page: pageNum });
      }
    }
    console.log(`  -> ${entries.length} entries`);
    return entries;
  }

  async function scrapeDetail(url, listingPage) {
    console.log(`  [DETAIL] ${url}`);
    const doc = await fetchPage(url);
    const ogImg = doc.querySelector('meta[property="og:image"]');
    const titleEl =
      doc.querySelector("h1.entry-title") ||
      doc.querySelector("h1.content-title") ||
      doc.querySelector("article h1");
    return {
      url,
      title: titleEl ? titleEl.textContent.trim() : "",
      status: getMeta(doc, "Status"),
      type: getMeta(doc, "Type"),
      year: getMeta(doc, "Year"),
      origin_label: getMeta(doc, "Origin"),
      about: getSection(doc, "About") || getSection(doc, "Overview"),
      origin: getSection(doc, "Origin") || getMeta(doc, "Origin"),
      image_url: ogImg ? ogImg.getAttribute("content") : null,
      listing_page: listingPage,
    };
  }

  // Main loop
  console.log("=== KYM SCRAPER STARTING ===");
  console.log(
    `Target: pages ${START_PAGE}-${MAX_PAGES}, max ${MAX_ENTRIES} entries`,
  );

  for (let pg = START_PAGE; pg <= MAX_PAGES; pg++) {
    if (RESULTS.length >= MAX_ENTRIES) break;

    let entries;
    try {
      entries = await scrapeListing(pg);
    } catch (e) {
      console.error(`Failed to scrape listing page ${pg}:`, e);
      continue;
    }

    if (!entries.length) {
      console.log(`No entries on page ${pg}, stopping.`);
      break;
    }

    for (const entry of entries) {
      if (RESULTS.length >= MAX_ENTRIES) break;
      if (SEEN.has(entry.url)) continue;
      if (typeof EXISTING_URLS !== "undefined" && EXISTING_URLS.has(entry.url))
        continue;
      SEEN.add(entry.url);

      try {
        const detail = await scrapeDetail(entry.url, entry.listing_page);
        RESULTS.push(detail);
        console.log(`    [${RESULTS.length}/${MAX_ENTRIES}] ${detail.title}`);
      } catch (e) {
        console.error(`    Failed: ${entry.url}`, e);
      }

      await sleep(SLEEP_MS);
    }

    console.log(`  (Page ${pg} done. Total: ${RESULTS.length})`);
  }

  // Download results
  const json = JSON.stringify(RESULTS, null, 2);
  const blob = new Blob([json], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `kym_scraped_${START_PAGE}_to_${MAX_PAGES}_${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(a.href);

  // Expose globally for manual retrieval
  window.__KYM_RESULTS__ = RESULTS;

  console.log(`=== DONE: ${RESULTS.length} entries downloaded ===`);
  console.log(
    "If download was blocked, run: copy(JSON.stringify(__KYM_RESULTS__, null, 2))",
  );
})();
