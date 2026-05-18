import os
import json
import asyncio
import logging
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright
import nest_asyncio

# Apply nest_asyncio to allow the loop to run seamlessly in Google Colab
nest_asyncio.apply()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

KEYWORDS = ["grant", "scheme", "funding", "incubator", "accelerator", "challenge", "support", "fellowship", "subsidies"]

def is_relevant(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in KEYWORDS)

class DeepSchemeScraper:
    def __init__(self, start_url: str, max_depth: int = 2, max_pages: int = 15):
        self.start_url = start_url
        self.base_domain = urlparse(start_url).netloc
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.visited_urls = set()
        self.extracted_schemes = []

    async def crawl_page(self, page, url: str, depth: int):
        if depth > self.max_depth or len(self.visited_urls) >= self.max_pages or url in self.visited_urls:
            return
        if urlparse(url).netloc != self.base_domain:
            return

        self.visited_urls.add(url)
        log.info(f"🟢 Crawling (Depth {depth}): {url}")

        try:
            await page.goto(url, wait_until="networkidle", timeout=20000)
            page_title = await page.title()
            page_text = await page.locator("body").inner_text()

            if is_relevant(page_title) or is_relevant(page_text[:1000]):
                # Map extracted data keys to fit the rest of the AI/Sheets pipeline structure
                self.extracted_schemes.append({
                    "title": page_title.strip(),
                    "link": url,  # Using 'link' matching expected pipeline fields
                    "description": page_text[:800].strip().replace('\n', ' ') + "...",
                    "source": self.base_domain
                })

            hrefs = await page.locator("a").eval_on_selector_all("elements => elements.map(e => e.href)")
            child_urls = []
            for href in hrefs:
                absolute_url = urljoin(url, href).split('#')[0].split('?')[0]
                if absolute_url not in self.visited_urls and urlparse(absolute_url).netloc == self.base_domain:
                    child_urls.append(absolute_url)

            for child_url in list(set(child_urls))[:8]: 
                await self.crawl_page(page, child_url, depth + 1)

        except Exception as e:
            log.debug(f"Skipping {url} due to parsing limit/error: {e}")

    async def run(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
            page = await context.new_page()
            await self.crawl_page(page, self.start_url, depth=1)
            await browser.close()
        return self.extracted_schemes

# ─────────────────────────────────────────────────────────
#  PIPELINE ENTRY POINT (What main.py looks for)
# ─────────────────────────────────────────────────────────
def run_all_scrapers():
    """
    Master orchestrator wrapper execution function. 
    Returns an array of scraped opportunity objects.
    """
    # Define your target entry link here
    TARGET_LINK = "https://startupmission.kerala.gov.in/schemes"
    
    log.info(f"Initiating Deep Dynamic Scraper entry point for: {TARGET_LINK}")
    scraper = DeepSchemeScraper(start_url=TARGET_LINK, max_depth=2, max_pages=15)
    
    # Run the asynchronous crawl synchronously for the pipeline
    try:
        opportunities = asyncio.run(scraper.run())
        return opportunities
    except Exception as e:
        log.error(f"Error inside run_all_scrapers execution context: {e}")
        return []
