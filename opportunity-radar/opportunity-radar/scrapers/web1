import os
import json
import asyncio
import logging
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# Keywords to validate if a page or text is relevant to schemes/grants
KEYWORDS = ["grant", "scheme", "funding", "incubator", "accelerator", "challenge", "support", "fellowship", "subsidies"]

def is_relevant(text: str) -> bool:
    """Check if the text contains any target keywords."""
    t = text.lower()
    return any(kw in t for kw in KEYWORDS)

class DeepSchemeScraper:
    def __init__(self, start_url: str, max_depth: int = 2, max_pages: int = 20):
        self.start_url = start_url
        self.base_domain = urlparse(start_url).netloc
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.visited_urls = set()
        self.extracted_schemes = []

    async def crawl_page(self, page, url: str, depth: int):
        # Guard rails for crawling depth, limits, and duplication
        if depth > self.max_depth or len(self.visited_urls) >= self.max_pages or url in self.visited_urls:
            return
        
        # Ensure we stay on the same domain to prevent wandering off to external sites
        if urlparse(url).netloc != self.base_domain:
            return

        self.visited_urls.add(url)
        log.info(f"🟢 Crawling (Depth {depth}): {url}")

        try:
            # Navigate using Playwright to evaluate Javascript
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Extract page title and full inner text content
            page_title = await page.title()
            page_text = await page.locator("body").inner_text()

            # Contextual Extraction: If this specific page looks like a scheme details page, save it
            if is_relevant(page_title) or is_relevant(page_text[:1000]):
                log.info(f"      ↳ ✨ Found potential scheme page: {page_title}")
                self.extracted_schemes.append({
                    "title": page_title.strip(),
                    "url": url,
                    "description": page_text[:800].strip().replace('\n', ' ') + "...",
                    "source": self.base_domain
                })

            # Sub-page Discovery: Gather all anchor links on the current page
            hrefs = await page.locator("a").eval_on_selector_all("elements => elements.map(e => e.href)")
            
            # Clean and filter links for the next depth level
            child_urls = []
            for href in hrefs:
                absolute_url = urljoin(url, href).split('#')[0].split('?')[0] # strip fragments & queries
                if absolute_url not in self.visited_urls and urlparse(absolute_url).netloc == self.base_domain:
                    child_urls.append(absolute_url)

            # Recursively crawl discovered sub-pages
            for child_url in list(set(child_urls))[:10]: # Cap branching factor to avoid exploding queue
                await self.crawl_page(page, child_url, depth + 1)

        except Exception as e:
            log.error(f"🔴 Error crawling {url}: {e}")

    async def run(self):
        async with async_playwright() as p:
            # Launch headless browser mimicking a standard user desktop
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            
            await self.crawl_page(page, self.start_url, depth=1)
            await browser.close()
            
        return self.extracted_schemes

# --- Execution block for your Colab Cell ---
if __name__ == "__main__":
    # Change this link to whatever portal you want to deep-crawl
    TARGET_LINK = "https://startupmission.kerala.gov.in/schemes" 
    
    log.info("Starting recursive deep scraper...")
    scraper = DeepSchemeScraper(start_url=TARGET_LINK, max_depth=2, max_pages=15)
    
    # Run the async loop inside environment
    import nest_asyncio
    nest_asyncio.apply() # Required to run async loops inside Jupyter/Colab notebooks
    
    results = asyncio.run(scraper.run())
    
    # Save results directly to a JSON file
    output_file = "discovered_schemes.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    log.info(f"🎉 Completed! Extracted {len(results)} schemes. Saved to {output_file}")
