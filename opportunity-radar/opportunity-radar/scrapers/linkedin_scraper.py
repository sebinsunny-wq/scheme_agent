"""
linkedin_scraper.py
Uses Playwright to scrape LinkedIn keyword feeds.
Run ONCE interactively to save session cookies, then headlessly in CI.

Usage:
  First run (saves session):   python linkedin_scraper.py --login
  Subsequent runs (headless):  python linkedin_scraper.py
"""

import os
import json
import asyncio
import logging
import argparse
import hashlib
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PWTimeout

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SESSION_FILE = Path("linkedin_session.json")
OUTPUT_FILE  = Path("linkedin_opportunities.json")

SEARCH_KEYWORDS = [
    "startup grant India",
    "innovation challenge apply",
    "incubation call applications",
    "fellowship opportunity India",
    "accelerator program apply",
    "CSR funding startup",
    "seed grant proposal invited",
]

FILTER_KEYWORDS = [
    "grant", "challenge", "incubat", "fellowship", "accelerat",
    "funding", "proposal", "apply", "opportunity", "hackathon",
    "call for", "programme", "scheme",
]


def is_relevant(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in FILTER_KEYWORDS)


def make_id(text: str, url: str) -> str:
    return hashlib.sha256(f"{text[:80]}{url}".encode()).hexdigest()[:16]


async def save_session(browser_context):
    cookies = await browser_context.cookies()
    storage = await browser_context.storage_state()
    SESSION_FILE.write_text(json.dumps(storage, indent=2))
    log.info(f"Session saved to {SESSION_FILE}")


async def login_flow(playwright):
    """Interactive login — run once locally."""
    browser = await playwright.chromium.launch(headless=False, slow_mo=100)
    ctx = await browser.new_context()
    page = await ctx.new_page()

    await page.goto("https://www.linkedin.com/login")
    log.info("🔐 Please log in manually in the browser window...")
    log.info("   Waiting up to 120 seconds for you to complete login...")

    try:
        await page.wait_for_url("**/feed/**", timeout=120_000)
        log.info("✅ Login detected — saving session")
        await save_session(ctx)
    except PWTimeout:
        log.error("Timed out waiting for login. Try again.")
    finally:
        await browser.close()


async def scrape_linkedin(playwright) -> list[dict]:
    """Headless scrape using saved session."""
    if not SESSION_FILE.exists():
        log.error("No session file found. Run with --login first.")
        return []

    storage_state = json.loads(SESSION_FILE.read_text())
    browser = await playwright.chromium.launch(headless=True)
    ctx = await browser.new_context(storage_state=storage_state)
    page = await ctx.new_page()

    opportunities = []
    seen = set()

    for keyword in SEARCH_KEYWORDS:
        encoded = keyword.replace(" ", "%20")
        url = f"https://www.linkedin.com/search/results/content/?keywords={encoded}&sortBy=date_posted"

        log.info(f"Searching LinkedIn: '{keyword}'")
        try:
            await page.goto(url, timeout=30_000)
            await page.wait_for_timeout(3000)

            # Scroll to load more posts
            for _ in range(3):
                await page.keyboard.press("End")
                await page.wait_for_timeout(2000)

            posts = await page.query_selector_all(".search-results__list .reusable-search__result-container")
            log.info(f"  Found {len(posts)} posts")

            for post in posts[:20]:
                try:
                    text_el = await post.query_selector(".feed-shared-update-v2__description, .search-result__snippet")
                    link_el = await post.query_selector("a.app-aware-link")
                    author_el = await post.query_selector(".entity-result__title-text, .update-components-actor__name")

                    text   = await text_el.inner_text() if text_el else ""
                    href   = await link_el.get_attribute("href") if link_el else ""
                    author = await author_el.inner_text() if author_el else "LinkedIn User"

                    if not text or not is_relevant(text):
                        continue

                    post_id = make_id(text, href)
                    if post_id in seen:
                        continue
                    seen.add(post_id)

                    opportunities.append({
                        "id": post_id,
                        "title": text[:120].strip(),
                        "description": text[:500].strip(),
                        "organization": author.strip(),
                        "funding_amount": "",
                        "deadline": "",
                        "eligibility": "",
                        "category": "",
                        "sector": "Mixed",
                        "state": "",
                        "url": href,
                        "source": "LinkedIn",
                        "tags": f"linkedin,{keyword.split()[0]}",
                        "ai_summary": "",
                        "date_added": datetime.utcnow().strftime("%Y-%m-%d"),
                    })
                    log.info(f"  ✓ {text[:60]}")
                except Exception as e:
                    log.warning(f"  Post parse error: {e}")

        except PWTimeout:
            log.error(f"  Timeout on keyword '{keyword}'")
        except Exception as e:
            log.error(f"  Error: {e}")

        await page.wait_for_timeout(4000)   # rate-limit courtesy

    await browser.close()
    log.info(f"LinkedIn scrape complete — {len(opportunities)} opportunities")
    return opportunities


async def main(login: bool):
    async with async_playwright() as pw:
        if login:
            await login_flow(pw)
        else:
            results = await scrape_linkedin(pw)
            OUTPUT_FILE.write_text(json.dumps(results, indent=2, ensure_ascii=False))
            log.info(f"Saved {len(results)} results to {OUTPUT_FILE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--login", action="store_true", help="Interactive login to save session")
    args = parser.parse_args()
    asyncio.run(main(login=args.login))
