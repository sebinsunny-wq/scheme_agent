"""
sheets_writer.py
Writes enriched opportunities to Google Sheets.

Auth: Google Service Account JSON (stored as GOOGLE_CREDENTIALS_JSON secret in GitHub).

Sheet columns (must match COLUMNS list exactly):
Title | Description | Organization | Funding Amount | Deadline |
Eligibility | Category | Sector | State | URL | Source |
Tags | AI Summary | Date Added | ID
"""

import os
import json
import logging
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_NAME = os.environ.get("GOOGLE_SHEET_NAME", "OpportunityRadar")
WORKSHEET  = os.environ.get("GOOGLE_WORKSHEET",  "Opportunities")

COLUMNS = [
    "Title", "Description", "Organization", "Funding Amount",
    "Deadline", "Eligibility", "Category", "Sector", "State",
    "URL", "Source", "Tags", "AI Summary", "Date Added", "ID",
]

COL_MAP = {col: i for i, col in enumerate(COLUMNS)}


# ──────────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────────
def get_client() -> gspread.Client:
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise EnvironmentError("GOOGLE_CREDENTIALS_JSON environment variable not set.")

    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def get_or_create_worksheet(client: gspread.Client) -> gspread.Worksheet:
    try:
        sh = client.open(SHEET_NAME)
    except gspread.SpreadsheetNotFound:
        log.info(f"Creating new spreadsheet: {SHEET_NAME}")
        sh = client.create(SHEET_NAME)
        sh.share(None, perm_type="anyone", role="reader")   # public read

    try:
        ws = sh.worksheet(WORKSHEET)
    except gspread.WorksheetNotFound:
        log.info(f"Creating worksheet: {WORKSHEET}")
        ws = sh.add_worksheet(title=WORKSHEET, rows=5000, cols=len(COLUMNS))
        ws.append_row(COLUMNS, value_input_option="RAW")

    return ws


# ──────────────────────────────────────────────
# DEDUP CHECK
# ──────────────────────────────────────────────
def get_existing_ids(ws: gspread.Worksheet) -> set:
    try:
        id_col_index = COL_MAP["ID"] + 1   # gspread is 1-indexed
        values = ws.col_values(id_col_index)
        return set(values[1:])             # skip header
    except Exception as e:
        log.warning(f"Could not read existing IDs: {e}")
        return set()


# ──────────────────────────────────────────────
# WRITE
# ──────────────────────────────────────────────
def opp_to_row(opp: dict) -> list:
    return [
        opp.get("title",          "")[:500],
        opp.get("description",    "")[:1000],
        opp.get("organization",   ""),
        opp.get("funding_amount", ""),
        opp.get("deadline",       ""),
        opp.get("eligibility",    ""),
        opp.get("category",       ""),
        opp.get("sector",         ""),
        opp.get("state",          ""),
        opp.get("url",            ""),
        opp.get("source",         ""),
        opp.get("tags",           ""),
        opp.get("ai_summary",     "")[:1000],
        opp.get("date_added",     datetime.utcnow().strftime("%Y-%m-%d")),
        opp.get("id",             ""),
    ]


def write_opportunities(opps: list[dict],
                        enriched_file: str = "enriched_opportunities.json") -> int:
    """Push new opportunities to Google Sheets. Returns count of new rows added."""

    if not opps:
        with open(enriched_file) as f:
            opps = json.load(f)

    client = get_client()
    ws     = get_or_create_worksheet(client)
    existing = get_existing_ids(ws)

    new_rows = []
    for opp in opps:
        if opp.get("id") in existing:
            log.debug(f"Skipping duplicate: {opp.get('id')}")
            continue
        new_rows.append(opp_to_row(opp))

    if new_rows:
        ws.append_rows(new_rows, value_input_option="USER_ENTERED")
        log.info(f"✅ Added {len(new_rows)} new opportunities to Google Sheets")
    else:
        log.info("No new opportunities to add (all duplicates)")

    return len(new_rows)


def get_all_opportunities() -> list[dict]:
    """Read all rows from the sheet and return as list of dicts."""
    client = get_client()
    ws     = get_or_create_worksheet(client)
    records = ws.get_all_records()
    return records


if __name__ == "__main__":
    import sys
    input_file = sys.argv[1] if len(sys.argv) > 1 else "enriched_opportunities.json"
    with open(input_file) as f:
        data = json.load(f)
    count = write_opportunities(data)
    log.info(f"Done. {count} rows added.")
