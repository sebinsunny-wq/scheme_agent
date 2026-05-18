"""
telegram_alerts.py
Sends Telegram notifications for new opportunities and approaching deadlines.

Setup:
1. Create bot via @BotFather → get BOT_TOKEN
2. Get your CHAT_ID by messaging @userinfobot
3. Store both as GitHub Secrets: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
"""

import os
import json
import logging
import re
from datetime import datetime, timedelta

import requests

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID",   "")

# Deadline warning window
DEADLINE_WARN_DAYS = int(os.environ.get("DEADLINE_WARN_DAYS", "7"))

# Categories that always get priority alerts
PRIORITY_KEYWORDS = ["ai", "deeptech", "ai/deeptech", "research funding", "fellowship"]


def send_message(text: str, parse_mode: str = "Markdown") -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        log.warning("Telegram credentials not set — skipping alert")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id":    CHAT_ID,
        "text":       text[:4096],          # Telegram message limit
        "parse_mode": parse_mode,
        "disable_web_page_preview": False,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        log.info("Telegram message sent ✅")
        return True
    except Exception as e:
        log.error(f"Telegram send error: {e}")
        return False


def format_new_opportunity(opp: dict) -> str:
    title    = opp.get("title", "Untitled")[:100]
    org      = opp.get("organization", "Unknown")
    category = opp.get("category", "")
    deadline = opp.get("deadline", "Not specified")
    amount   = opp.get("funding_amount", "")
    url      = opp.get("url", "")
    summary  = opp.get("ai_summary", opp.get("description", ""))[:300]
    sector   = opp.get("sector", "")
    tags     = opp.get("tags", "")

    is_priority = any(kw in (category + sector + tags).lower() for kw in PRIORITY_KEYWORDS)
    icon = "🚀" if is_priority else "📢"

    msg = f"""{icon} *New Opportunity Detected!*

📌 *{title}*
🏢 {org}
🏷️ {category} | {sector}
💰 {amount or 'Not specified'}
📅 Deadline: {deadline}

{summary}

🔗 [View Opportunity]({url})

#OpportunityRadar #{category.replace(' ', '')}"""
    return msg


def format_deadline_warning(opp: dict, days_left: int) -> str:
    title    = opp.get("title", "Untitled")[:100]
    deadline = opp.get("deadline", "")
    url      = opp.get("url", "")
    amount   = opp.get("funding_amount", "Not specified")

    urgency = "⚠️" if days_left > 3 else "🚨"

    msg = f"""{urgency} *Deadline Approaching!*

📌 *{title}*
⏰ Only *{days_left} days* left to apply!
📅 Deadline: {deadline}
💰 Funding: {amount}

🔗 [Apply Now]({url})"""
    return msg


def try_parse_deadline(deadline_str: str) -> datetime | None:
    """Attempt to parse various date formats."""
    if not deadline_str:
        return None

    formats = [
        "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y",
        "%B %d, %Y", "%b %d, %Y",
        "%d %B %Y", "%d %b %Y",
        "%d/%m/%y",
    ]
    # Clean up prefix text like "deadline: 30 June 2025"
    cleaned = re.sub(r"(?i)(deadline|last date|apply by|closes on)[:\s]+", "", deadline_str).strip()

    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


def send_new_opportunity_alerts(new_opps: list[dict]) -> int:
    """Send one alert per new opportunity. Returns count sent."""
    sent = 0
    for opp in new_opps:
        msg = format_new_opportunity(opp)
        if send_message(msg):
            sent += 1
    log.info(f"Sent {sent}/{len(new_opps)} new opportunity alerts")
    return sent


def send_deadline_warnings(all_opps: list[dict]) -> int:
    """Scan all opportunities and warn for upcoming deadlines."""
    now  = datetime.utcnow()
    sent = 0
    for opp in all_opps:
        dt = try_parse_deadline(opp.get("deadline", ""))
        if not dt:
            continue
        days_left = (dt - now).days
        if 0 <= days_left <= DEADLINE_WARN_DAYS:
            msg = format_deadline_warning(opp, days_left)
            if send_message(msg):
                sent += 1
    log.info(f"Sent {sent} deadline warning alerts")
    return sent


def send_daily_digest(new_count: int, total_count: int):
    msg = f"""📊 *Daily OpportunityRadar Digest*

✅ New today: *{new_count}*
📦 Total tracked: *{total_count}*
🕐 Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

Stay ahead of every grant, challenge & fellowship! 🎯"""
    send_message(msg)


if __name__ == "__main__":
    import sys
    # Test: python telegram_alerts.py enriched_opportunities.json
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            opps = json.load(f)
        send_new_opportunity_alerts(opps[:3])     # alert first 3 as test
        send_deadline_warnings(opps)
    else:
        send_message("🤖 OpportunityRadar bot is live and monitoring!")
