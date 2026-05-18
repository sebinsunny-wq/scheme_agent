"""
main.py
Master orchestrator — called by GitHub Actions every 6 hours.

Pipeline:
  1. Scrape websites (BeautifulSoup)
  2. Scrape LinkedIn (if session available)
  3. Enrich with AI (HuggingFace / rule-based)
  4. Write new records to Google Sheets
  5. Send Telegram alerts for new + expiring opportunities
  6. Generate static dashboard HTML
"""

import json
import logging
import sys
import os
from pathlib import Path

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def step(name: str):
    log.info(f"\n{'='*60}")
    log.info(f"  STEP: {name}")
    log.info(f"{'='*60}")


def main():
    # ── 1. Web scraping ──────────────────────────────────────
    step("Web Scraping")
    try:
        from scrapers.web1 import run_all_scrapers
        web_opps = run_all_scrapers()
        log.info(f"Web scraper: {len(web_opps)} opportunities")
    except Exception as e:
        log.error(f"Web scraper failed: {e}")
        web_opps = []

    # ── 2. LinkedIn scraping (optional) ──────────────────────
    step("LinkedIn Scraping")
    linkedin_opps = []
    linkedin_session = Path("linkedin_session.json")
    if linkedin_session.exists():
        try:
            import asyncio
            from scrapers.linkedin_scraper import scrape_linkedin
            from playwright.async_api import async_playwright
            async def _run():
                async with async_playwright() as pw:
                    return await scrape_linkedin(pw)
            linkedin_opps = asyncio.run(_run())
            log.info(f"LinkedIn scraper: {len(linkedin_opps)} opportunities")
        except Exception as e:
            log.warning(f"LinkedIn scraper skipped: {e}")
    else:
        log.info("No LinkedIn session — skipping (run linkedin_scraper.py --login locally first)")

    # ── 3. Merge all opportunities ────────────────────────────
    step("Merging Sources")
    all_raw = web_opps + linkedin_opps
    log.info(f"Total raw opportunities: {len(all_raw)}")

    if not all_raw:
        log.warning("No opportunities found — exiting early")
        sys.exit(0)

    with open("scraped_opportunities.json", "w") as f:
        json.dump(all_raw, f, indent=2, ensure_ascii=False)

    # ── 4. AI enrichment ─────────────────────────────────────
    step("AI Enrichment")
    try:
        from ai_pipeline.ai_extractor import run_pipeline
        enriched = run_pipeline(
            input_file="scraped_opportunities.json",
            output_file="enriched_opportunities.json",
        )
    except Exception as e:
        log.error(f"AI pipeline failed: {e}")
        enriched = all_raw      # fallback to raw

    # ── 5. Write to Google Sheets ─────────────────────────────
    step("Google Sheets Update")
    new_count = 0
    try:
        from sheets_integration.sheets_writer import write_opportunities, get_all_opportunities
        new_count = write_opportunities(enriched)
        all_in_sheet = get_all_opportunities()
        total_count  = len(all_in_sheet)
        log.info(f"Sheet update: {new_count} new, {total_count} total")
    except Exception as e:
        log.error(f"Google Sheets write failed: {e}")
        all_in_sheet = enriched
        total_count  = len(enriched)

    # ── 6. Telegram alerts ────────────────────────────────────
    step("Telegram Alerts")
    try:
        from telegram_bot.telegram_alerts import (
            send_new_opportunity_alerts,
            send_deadline_warnings,
            send_daily_digest,
        )
        new_opps = enriched[:new_count] if new_count else []
        send_new_opportunity_alerts(new_opps[:10])   # cap at 10 per run
        send_deadline_warnings(all_in_sheet)

        # Daily digest on first run of the day (hour 0 UTC)
        from datetime import datetime
        if datetime.utcnow().hour < 7:
            send_daily_digest(new_count, total_count)
    except Exception as e:
        log.error(f"Telegram alerts failed: {e}")

    # ── 7. Generate static HTML dashboard ────────────────────
    step("Static Dashboard Generation")
    try:
        from dashboard.generate_dashboard import generate
        generate(all_in_sheet[:200])       # show latest 200
        log.info("Dashboard HTML generated → dashboard/index.html")
    except Exception as e:
        log.error(f"Dashboard generation failed: {e}")

    step("DONE")
    log.info(f"Run complete: {new_count} new, {total_count} total opportunities tracked")


if __name__ == "__main__":
    main()
