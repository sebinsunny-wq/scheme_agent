"""
web_scraper.py
Scrapes government portals, startup sites, CSR pages for opportunities.
Uses requests + BeautifulSoup (no heavy dependencies).
"""

import os
import json
import hashlib
import logging
import time
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# OPPORTUNITY DATA MODEL
# ──────────────────────────────────────────────
@dataclass
class Opportunity:
    title: str
    description: str
    organization: str
    funding_amount: str
    deadline: str
    eligibility: str
    category: str
    sector: str
    state: str
    url: str
    source: str
    tags: str
    ai_summary: str
    date_added: str
    id: str = ""          # SHA-256 hash for dedup

    def __post_init__(self):
        if not self.id:
            raw = f"{self.title}{self.url}{self.organization}"
            self.id = hashlib.sha256(raw.encode()).hexdigest()[:16]


# ──────────────────────────────────────────────
# KEYWORD FILTERS
# ──────────────────────────────────────────────
KEYWORDS = [
    "grant", "startup challenge", "innovation call", "incubation",
    "proposal invited", "accelerator", "funding support", "fellowship",
    "seed fund", "venture support", "hackathon", "competition",
    "call for applications", "csr fund", "social innovation",
]

def text_has_keyword(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in KEYWORDS)


# ──────────────────────────────────────────────
# TARGET SITES  (add more here freely)
# ──────────────────────────────────────────────
TARGETS = [
    {
        "name": "Startup India",
        "url": "https://www.startupindia.gov.in/content/sih/en/startup-schemes.html",
        "list_selector": "article, .scheme-card, .card",
        "title_selector": "h2, h3, .card-title",
        "desc_selector": "p, .card-body",
        "link_selector": "a",
        "organization": "Startup India / DPIIT",
        "sector": "Startups",
        "state": "Central",
    },
    {
        "name": "MyScheme Portal",
        "url": "https://www.myscheme.gov.in/search?q=startup+grant",
        "list_selector": ".scheme-card, .card, article",
        "title_selector": "h3, h2, .title",
        "desc_selector": ".description, p",
        "link_selector": "a",
        "organization": "Government of India",
        "sector": "Mixed",
        "state": "Central",
    },
    {
        "name": "DST India",
        "url": "https://dst.gov.in/funding-and-grants",
        "list_selector": ".views-row, article, .item",
        "title_selector": "h2, h3, .views-field-title",
        "desc_selector": "p, .views-field-body",
        "link_selector": "a",
        "organization": "DST",
        "sector": "Science & Technology",
        "state": "Central",
    },
    {
        "name": "BIRAC",
        "url": "https://birac.nic.in/call_for_proposal.php",
        "list_selector": "table tr, .scheme, article",
        "title_selector": "td, h3, h2",
        "desc_selector": "td + td, p",
        "link_selector": "a",
        "organization": "BIRAC",
        "sector": "Biotech / Life Sciences",
        "state": "Central",
    },
    {
        "name": "Kerala Startup Mission",
        "url": "https://startupmission.kerala.gov.in/schemes",
        "list_selector": ".scheme-item, .card, article",
        "title_selector": "h3, h2",
        "desc_selector": "p",
        "link_selector": "a",
        "organization": "KSUM",
        "sector": "Startups",
        "state": "Kerala",
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120 Safari/537.36"
    )
}


# ──────────────────────────────────────────────
# CORE SCRAPE LOGIC
# ──────────────────────────────────────────────
def scrape_site(target: dict) -> list[Opportunity]:
    opportunities = []
    try:
        log.info(f"Scraping: {target['name']} → {target['url']}")
        resp = requests.get(target["url"], headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        items = soup.select(target["list_selector"])
        log.info(f"  Found {len(items)} raw items")

        for item in items[:30]:           # cap per site
            title_el = item.select_one(target["title_selector"])
            desc_el  = item.select_one(target["desc_selector"])
            link_el  = item.select_one(target["link_selector"])

            title = title_el.get_text(strip=True) if title_el else ""
            desc  = desc_el.get_text(strip=True)[:500] if desc_el else ""
            href  = link_el.get("href", "") if link_el else ""

            if not title or not text_has_keyword(f"{title} {desc}"):
                continue

            if href and not href.startswith("http"):
                base = "/".join(target["url"].split("/")[:3])
                href = base + "/" + href.lstrip("/")

            opp = Opportunity(
                title=title,
                description=desc,
                organization=target.get("organization", ""),
                funding_amount="",          # filled by AI pipeline
                deadline="",
                eligibility="",
                category="",
                sector=target.get("sector", ""),
                state=target.get("state", ""),
                url=href or target["url"],
                source=target["name"],
                tags="",
                ai_summary="",
                date_added=datetime.utcnow().strftime("%Y-%m-%d"),
            )
            opportunities.append(opp)
            log.info(f"  ✓ {title[:60]}")

    except Exception as e:
        log.error(f"Error scraping {target['name']}: {e}")

    return opportunities


def run_all_scrapers() -> list[dict]:
    all_opps = []
    seen_ids = set()

    for target in TARGETS:
        opps = scrape_site(target)
        for opp in opps:
            if opp.id not in seen_ids:
                seen_ids.add(opp.id)
                all_opps.append(asdict(opp))
        time.sleep(2)   # polite crawl delay

    log.info(f"Total unique opportunities scraped: {len(all_opps)}")
    return all_opps


if __name__ == "__main__":
    results = run_all_scrapers()
    out_path = "scraped_opportunities.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    log.info(f"Saved to {out_path}")
