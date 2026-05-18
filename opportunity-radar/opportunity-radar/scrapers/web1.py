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

KEYWORDS = ["grant", "scheme", "funding", "incubator", "accelerator", "challenge", "support", "fellowship", "subsidies", "application", "program"]

def is_relevant(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in KEYWORDS)

class DeepSchemeScraper:
    def __init__(self, start_url: str, max_depth: int = 1, max_pages: int = 10):
        self.start_url = start_url
        self.base_domain = urlparse(start_url).netloc
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.visited_urls = set()
        self.extracted_schemes = []

    async def extract_content_from_frames(self, page) -> str:
        """Helper to aggregate text content across the main page and all embedded iframes."""
        text_content = await page.locator("body").inner_text()
        
        # Check all iframes (Startup India often renders grids inside frame sub-doms)
        frames = page.frames
        for frame in frames:
            try:
                frame_text = await frame.locator("body").inner_text()
                text_content += "\n" + frame_text
            except Exception:
                continue
        return text_content

    async def crawl_page(self, page, url: str, depth: int):
        if depth > self.max_depth or len(self.visited_urls) >= self.max_pages or url in self.visited_urls:
            return
        if urlparse(url).netloc != self.base_domain:
            return

        self.visited_urls.add(url)
        log.info(f"🟢 Crawling (Depth {depth}): {url}")

        try:
            # Navigate and wait for structural layout loading
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Give dynamic JavaScript / API calls up to 5 seconds to draw cards/tables
            await page.wait_for_timeout(5000)
            
            page_title = await page.title()
            combined_text = await self.extract_content_from_frames(page)

            # Strict processing check: look for list keywords or explicit card layouts
            if is_relevant(page_title) or is_relevant(combined_text[:2000]):
                log.info(f"      ↳ ✨ Extracted data layer from target content view: {page_title}")
                self.extracted_schemes.append({
                    "title": page_title.strip() if page_title.strip() else "Startup India Program Listing",
                    "link": url,  
                    "description": combined_text[:1200].strip().replace('\n', ' ') + "...",
                    "source": self.base_domain
                })

            # Gather sub-page target navigation anchors
            hrefs = await page.locator("a").eval_on_selector_all("elements => elements.map(e => e.href)")
            child_urls = []
            for href in hrefs:
                absolute_url = urljoin(url, href).split('#')[0].split('?')[0]
                if absolute_url not in self.visited_urls and urlparse(absolute_url).netloc == self.base_domain:
                    # Filter for links that smell like scheme collections or details
                    if any(k in absolute_url.lower() for k in ["program", "scheme", "content", "application"]):
                        child_urls.append(absolute_url)

            for child_url in list(set(child_urls))[:5]: 
                await self.crawl_page(page, child_url, depth + 1)

        except Exception as e:
            log.debug(f"Skipping page route {url} due to parsing boundary: {e}")

    async def run(self):
        async with async_playwright() as p:
            # 1. Advanced stealth browser argument parameters
            browser = await p.chromium.launch(
                headless=True, 
                args=[
                    '--disable-blink-features=AutomationControlled', 
                    '--disable-infobars', 
                    '--window-size=1920,1080',
                    '--no-sandbox',
                    '--disable-setuid-sandbox'
                ]
            )
            
            # 2. Complete desktop user agent virtualization
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Referer": "https://www.google.com/",
                    "Upgrade-Insecure-Requests": "1"
                }
            )
            
            page = await context.new_page()
            
            # 3. Strip automated client verification scripts
            await page.add_init_script("delete navigator.__proto__.webdriver;")
            
            # Execute crawl wrapper
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
    TARGET_LINK = "https://www.startupindia.gov.in/content/sih/en/ams-application/application-listing.html"
    
    log.info(f"Initiating Deep Dynamic Scraper entry point for: {TARGET_LINK}")
    scraper = DeepSchemeScraper(start_url=TARGET_LINK, max_depth=1, max_pages=5)
    
    try:
        opportunities = asyncio.run(scraper.run())
        log.info(f"Scraper returned {len(opportunities)} items back to master pipeline pipeline processing.")
        return opportunities
    except Exception as e:
        log.error(f"Error inside run_all_scrapers execution context: {e}")
        return []
