# 🛰 OpportunityRadar

> AI-powered system that automatically discovers, classifies, and publishes startup grants, fellowships, incubation calls, CSR opportunities, and innovation challenges — updated every 6 hours, entirely free to run.

---

## 🗺 Architecture

```
Websites + LinkedIn
        ↓
GitHub Actions (every 6h)
        ↓  scrapers/web_scraper.py
        ↓  scrapers/linkedin_scraper.py
        ↓
AI Enrichment (HuggingFace free tier)
        ↓  ai_pipeline/ai_extractor.py
        ↓
Google Sheets (master database)
        ↓  sheets_integration/sheets_writer.py
        ↓
GitHub Pages Dashboard          +   Telegram Alerts
(docs/index.html)                   telegram_bot/telegram_alerts.py
```

### Tech Stack (all free)

| Layer        | Tool                          |
|--------------|-------------------------------|
| Scraping     | BeautifulSoup + Playwright    |
| AI           | HuggingFace Inference API     |
| Database     | Google Sheets                 |
| Automation   | GitHub Actions                |
| Dashboard    | GitHub Pages (static HTML)    |
| Alerts       | Telegram Bot API              |
| Auth         | Google Service Account        |

---

## 📁 Folder Structure

```
opportunity-radar/
├── main.py                          # Master orchestrator
├── requirements.txt
├── README.md
│
├── scrapers/
│   ├── web_scraper.py               # BeautifulSoup multi-site scraper
│   └── linkedin_scraper.py          # Playwright LinkedIn scraper
│
├── ai_pipeline/
│   └── ai_extractor.py              # HuggingFace summarization + classification
│
├── sheets_integration/
│   └── sheets_writer.py             # Google Sheets read/write
│
├── telegram_bot/
│   └── telegram_alerts.py           # Telegram notifications
│
├── dashboard/
│   └── generate_dashboard.py        # Static HTML generator
│
├── docs/                            # GitHub Pages output (auto-generated)
│   ├── index.html
│   └── opportunities.json
│
└── .github/
    └── workflows/
        └── scrape_and_publish.yml   # GitHub Actions automation
```

---

## ⚡ Quick Setup (< 30 minutes)

### Step 1 — Fork & clone this repo
```bash
git clone https://github.com/YOUR_USERNAME/opportunity-radar.git
cd opportunity-radar
```

### Step 2 — Google Service Account
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project → Enable **Google Sheets API** and **Google Drive API**
3. Create a **Service Account** → Download JSON key
4. Share your Google Sheet with the service account email (`xxx@yyy.iam.gserviceaccount.com`)

### Step 3 — Telegram Bot
1. Message [@BotFather](https://t.me/BotFather) on Telegram → `/newbot`
2. Copy the `BOT_TOKEN`
3. Message [@userinfobot](https://t.me/userinfobot) to get your `CHAT_ID`

### Step 4 — HuggingFace API Key (optional but recommended)
1. Sign up at [huggingface.co](https://huggingface.co)
2. Go to Settings → Access Tokens → New Token (free tier is fine)

### Step 5 — Add GitHub Secrets
Go to your repo → **Settings → Secrets → Actions → New repository secret**

| Secret name                | Value                                      |
|----------------------------|--------------------------------------------|
| `GOOGLE_CREDENTIALS_JSON`  | Paste entire contents of service account JSON |
| `GOOGLE_SHEET_NAME`        | `OpportunityRadar`                         |
| `TELEGRAM_BOT_TOKEN`       | Your bot token from BotFather              |
| `TELEGRAM_CHAT_ID`         | Your Telegram chat/channel ID              |
| `HF_API_KEY`               | HuggingFace access token (optional)        |

### Step 6 — Enable GitHub Pages
Go to **Settings → Pages → Source → Deploy from branch → `main` → `/docs`**

Your dashboard will be live at:
`https://YOUR_USERNAME.github.io/opportunity-radar/`

### Step 7 — Trigger first run
Go to **Actions → OpportunityRadar — Scrape & Publish → Run workflow**

---

## 🔗 LinkedIn Setup (one-time)

LinkedIn scraping requires a one-time manual login to save session cookies.

```bash
# Install locally (only needed once)
pip install playwright
playwright install chromium

# Run interactive login (browser window will open)
python scrapers/linkedin_scraper.py --login
```

After login, a `linkedin_session.json` file is created.
Store its contents as a GitHub Secret named `LINKEDIN_SESSION_JSON`.

> ⚠️ LinkedIn sessions expire. Re-run `--login` every few weeks if scraping stops working.

---

## 📊 Google Sheets Structure

| Column          | Description                               |
|-----------------|-------------------------------------------|
| Title           | Opportunity name                          |
| Description     | Full text                                 |
| Organization    | Offering organization                     |
| Funding Amount  | Grant/prize amount (AI-extracted)         |
| Deadline        | Application deadline (AI-extracted)       |
| Eligibility     | Who can apply (AI-extracted)              |
| Category        | Grant / Fellowship / Accelerator / etc.   |
| Sector          | AgriTech / HealthTech / AI / etc.         |
| State           | Central / Kerala / Maharashtra / etc.     |
| URL             | Direct link                               |
| Source          | Website name or LinkedIn                  |
| Tags            | Comma-separated keywords                  |
| AI Summary      | 2-sentence AI-generated summary           |
| Date Added      | YYYY-MM-DD                                |
| ID              | SHA-256 dedup hash                        |

---

## ➕ Adding More Scraping Targets

In `scrapers/web_scraper.py`, add to the `TARGETS` list:

```python
{
    "name": "Your Source Name",
    "url": "https://example.com/grants",
    "list_selector": ".grant-card",       # CSS selector for list items
    "title_selector": "h3",              # title within each item
    "desc_selector": "p",               # description
    "link_selector": "a",               # link
    "organization": "Example Org",
    "sector": "Startups",
    "state": "Maharashtra",
},
```

---

## 🚀 Scaling Up Later

| Need                    | Upgrade path                                      |
|-------------------------|---------------------------------------------------|
| More AI accuracy        | Upgrade to GPT-4o / Claude via API               |
| More scraping sources   | Add Apify cloud scrapers                          |
| Real-time updates       | Add webhook triggers or Pub/Sub                   |
| Better DB               | Migrate from Sheets to Supabase (free tier)       |
| Full web app            | Deploy React dashboard on Vercel                  |
| Multi-user access       | Add Google Sheets sharing / Notion integration    |

---

## 🛠 Local Development

```bash
pip install -r requirements.txt
playwright install chromium

# Run just the web scraper
python scrapers/web_scraper.py

# Run AI enrichment
export HF_API_KEY=hf_xxx
python ai_pipeline/ai_extractor.py

# Generate dashboard from local data
python dashboard/generate_dashboard.py enriched_opportunities.json

# Open dashboard
open docs/index.html
```

---

## 📜 License
MIT — free to use, fork, and deploy.
