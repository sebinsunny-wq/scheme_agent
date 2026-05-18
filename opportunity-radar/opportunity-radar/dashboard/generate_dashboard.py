"""
generate_dashboard.py
Generates a static HTML dashboard published to GitHub Pages.
No React build step required — pure HTML/CSS/JS.
"""

import json
import os
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path("docs")      # GitHub Pages serves from /docs


def card_html(opp: dict) -> str:
    title    = opp.get("Title", opp.get("title", "Untitled"))[:100]
    org      = opp.get("Organization", opp.get("organization", ""))
    category = opp.get("Category", opp.get("category", ""))
    sector   = opp.get("Sector", opp.get("sector", ""))
    deadline = opp.get("Deadline", opp.get("deadline", ""))
    amount   = opp.get("Funding Amount", opp.get("funding_amount", ""))
    url      = opp.get("URL", opp.get("url", "#"))
    summary  = opp.get("AI Summary", opp.get("ai_summary", opp.get("Description", "")))[:250]
    tags     = opp.get("Tags", opp.get("tags", ""))
    state    = opp.get("State", opp.get("state", ""))
    source   = opp.get("Source", opp.get("source", ""))

    tag_pills = "".join(
        f'<span class="tag">{t.strip()}</span>'
        for t in tags.split(",") if t.strip()
    )

    CATEGORY_COLORS = {
        "grant": "#10b981",
        "fellowship": "#6366f1",
        "accelerator": "#f59e0b",
        "incubation": "#0ea5e9",
        "innovation challenge": "#ec4899",
        "csr opportunity": "#8b5cf6",
        "competition": "#f43f5e",
        "government scheme": "#64748b",
        "research funding": "#06b6d4",
    }
    cat_color = CATEGORY_COLORS.get(category.lower(), "#64748b")

    return f"""
    <div class="card" data-category="{category}" data-sector="{sector}" data-state="{state}">
      <div class="card-accent" style="background:{cat_color}"></div>
      <div class="card-body">
        <div class="card-meta">
          <span class="badge" style="background:{cat_color}20;color:{cat_color}">{category or 'Opportunity'}</span>
          <span class="source">{source}</span>
        </div>
        <h3 class="card-title"><a href="{url}" target="_blank" rel="noopener">{title}</a></h3>
        <p class="org">🏢 {org}</p>
        <p class="summary">{summary}</p>
        <div class="card-footer">
          <div class="card-stats">
            {'<span class="stat">💰 ' + amount + '</span>' if amount else ''}
            {'<span class="stat deadline">📅 ' + deadline + '</span>' if deadline else ''}
            {'<span class="stat">📍 ' + state + '</span>' if state else ''}
          </div>
          <div class="tags">{tag_pills}</div>
        </div>
        <a href="{url}" target="_blank" rel="noopener" class="apply-btn">Apply / View →</a>
      </div>
    </div>"""


def generate(opportunities: list[dict]):
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Collect unique filter values
    categories = sorted(set(o.get("Category", o.get("category", "")) for o in opportunities if o.get("Category") or o.get("category")))
    sectors    = sorted(set(o.get("Sector",   o.get("sector",   "")) for o in opportunities if o.get("Sector")   or o.get("sector")))
    states     = sorted(set(o.get("State",    o.get("state",    "")) for o in opportunities if o.get("State")    or o.get("state")))

    cards_html = "\n".join(card_html(o) for o in opportunities)
    cat_opts   = "\n".join(f'<option value="{c}">{c}</option>' for c in categories)
    sec_opts   = "\n".join(f'<option value="{s}">{s}</option>' for s in sectors)
    sta_opts   = "\n".join(f'<option value="{s}">{s}</option>' for s in states)
    updated    = datetime.utcnow().strftime("%d %b %Y, %H:%M UTC")
    count      = len(opportunities)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OpportunityRadar — Grants, Fellowships & Startup Schemes</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg:       #0a0f1e;
    --surface:  #111827;
    --border:   #1f2937;
    --text:     #e2e8f0;
    --muted:    #94a3b8;
    --accent:   #38bdf8;
    --accent2:  #818cf8;
    --radius:   12px;
  }}
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0 }}
  body {{
    font-family: 'DM Sans', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
  }}

  /* HERO */
  .hero {{
    background: linear-gradient(135deg, #0a0f1e 0%, #0f1e3d 50%, #0a0f1e 100%);
    border-bottom: 1px solid var(--border);
    padding: 3rem 1.5rem 2rem;
    text-align: center;
    position: relative;
    overflow: hidden;
  }}
  .hero::before {{
    content: '';
    position: absolute; inset: 0;
    background: radial-gradient(ellipse 80% 60% at 50% -20%, rgba(56,189,248,.18) 0%, transparent 70%);
    pointer-events: none;
  }}
  .hero-badge {{
    display: inline-block;
    background: rgba(56,189,248,.12);
    border: 1px solid rgba(56,189,248,.3);
    color: var(--accent);
    font-size: .75rem;
    letter-spacing: .15em;
    text-transform: uppercase;
    padding: .35rem .9rem;
    border-radius: 99px;
    margin-bottom: 1.2rem;
    font-family: 'Syne', sans-serif;
  }}
  h1 {{
    font-family: 'Syne', sans-serif;
    font-size: clamp(2rem, 5vw, 3.5rem);
    font-weight: 800;
    line-height: 1.1;
    background: linear-gradient(135deg, #e2e8f0 30%, var(--accent));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 1rem;
  }}
  .hero-sub {{
    color: var(--muted);
    font-size: 1.05rem;
    max-width: 540px;
    margin: 0 auto 1.5rem;
  }}
  .stats-row {{
    display: flex;
    gap: 2rem;
    justify-content: center;
    flex-wrap: wrap;
    margin-top: 1rem;
  }}
  .stat-chip {{
    text-align: center;
  }}
  .stat-chip strong {{
    display: block;
    font-family: 'Syne', sans-serif;
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--accent);
  }}
  .stat-chip span {{
    font-size: .8rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: .08em;
  }}

  /* FILTERS */
  .toolbar {{
    position: sticky;
    top: 0;
    z-index: 10;
    background: rgba(10,15,30,.92);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--border);
    padding: 1rem 1.5rem;
    display: flex;
    gap: .75rem;
    flex-wrap: wrap;
    align-items: center;
  }}
  .toolbar input, .toolbar select {{
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text);
    border-radius: 8px;
    padding: .5rem .9rem;
    font-size: .9rem;
    font-family: inherit;
    outline: none;
    transition: border-color .2s;
  }}
  .toolbar input {{ flex: 1; min-width: 200px; }}
  .toolbar input:focus, .toolbar select:focus {{ border-color: var(--accent) }}
  .toolbar select {{ cursor: pointer }}
  #result-count {{
    margin-left: auto;
    font-size: .85rem;
    color: var(--muted);
    white-space: nowrap;
  }}

  /* GRID */
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 1.25rem;
    padding: 1.5rem;
    max-width: 1400px;
    margin: 0 auto;
  }}

  /* CARD */
  .card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    transition: transform .2s, border-color .2s, box-shadow .2s;
    position: relative;
  }}
  .card:hover {{
    transform: translateY(-3px);
    border-color: rgba(56,189,248,.35);
    box-shadow: 0 8px 32px rgba(0,0,0,.35);
  }}
  .card-accent {{
    height: 3px;
    width: 100%;
    flex-shrink: 0;
  }}
  .card-body {{ padding: 1.2rem; display: flex; flex-direction: column; gap: .6rem; flex: 1 }}
  .card-meta {{ display: flex; align-items: center; justify-content: space-between }}
  .badge {{
    font-size: .7rem;
    font-weight: 600;
    padding: .2rem .65rem;
    border-radius: 99px;
    text-transform: uppercase;
    letter-spacing: .05em;
  }}
  .source {{ font-size: .72rem; color: var(--muted) }}
  .card-title {{ font-family: 'Syne', sans-serif; font-size: 1rem; font-weight: 700; line-height: 1.35 }}
  .card-title a {{ color: var(--text); text-decoration: none }}
  .card-title a:hover {{ color: var(--accent) }}
  .org {{ font-size: .82rem; color: var(--accent2) }}
  .summary {{ font-size: .85rem; color: var(--muted); line-height: 1.55; flex: 1 }}
  .card-footer {{ margin-top: auto }}
  .card-stats {{ display: flex; gap: .5rem; flex-wrap: wrap; margin-bottom: .5rem }}
  .stat {{ font-size: .75rem; color: var(--muted) }}
  .stat.deadline {{ color: #f59e0b }}
  .tags {{ display: flex; flex-wrap: wrap; gap: .3rem }}
  .tag {{
    background: rgba(129,140,248,.12);
    color: var(--accent2);
    font-size: .68rem;
    padding: .15rem .5rem;
    border-radius: 99px;
    border: 1px solid rgba(129,140,248,.25);
  }}
  .apply-btn {{
    display: block;
    margin-top: .8rem;
    text-align: center;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    color: #0a0f1e;
    font-weight: 600;
    font-size: .85rem;
    padding: .6rem;
    border-radius: 8px;
    text-decoration: none;
    transition: opacity .2s;
  }}
  .apply-btn:hover {{ opacity: .85 }}

  .hidden {{ display: none !important }}
  .no-results {{
    grid-column: 1/-1;
    text-align: center;
    color: var(--muted);
    padding: 4rem 1rem;
    font-size: 1.1rem;
  }}

  footer {{
    text-align: center;
    color: var(--muted);
    font-size: .8rem;
    padding: 2rem 1rem;
    border-top: 1px solid var(--border);
    margin-top: 2rem;
  }}
</style>
</head>
<body>

<div class="hero">
  <div class="hero-badge">🛰 Auto-Updated Every 6 Hours</div>
  <h1>OpportunityRadar</h1>
  <p class="hero-sub">AI-curated grants, fellowships, accelerators & startup schemes — all in one place.</p>
  <div class="stats-row">
    <div class="stat-chip"><strong>{count}</strong><span>Opportunities</span></div>
    <div class="stat-chip"><strong>{len(categories)}</strong><span>Categories</span></div>
    <div class="stat-chip"><strong>{len(sectors)}</strong><span>Sectors</span></div>
    <div class="stat-chip"><strong>⚡</strong><span>Last updated {updated}</span></div>
  </div>
</div>

<div class="toolbar">
  <input type="text" id="search" placeholder="🔍  Search by title, keyword, org…">
  <select id="filter-cat">
    <option value="">All Categories</option>
    {cat_opts}
  </select>
  <select id="filter-sec">
    <option value="">All Sectors</option>
    {sec_opts}
  </select>
  <select id="filter-sta">
    <option value="">All States</option>
    {sta_opts}
  </select>
  <span id="result-count">{count} results</span>
</div>

<div class="grid" id="grid">
  {cards_html}
  <div class="no-results hidden" id="no-results">No opportunities match your filters.</div>
</div>

<footer>
  OpportunityRadar · Auto-generated · Data from public sources &amp; LinkedIn ·
  <a href="https://github.com" style="color:var(--accent)">GitHub</a>
</footer>

<script>
  const cards = document.querySelectorAll('.card');
  const searchEl = document.getElementById('search');
  const catEl = document.getElementById('filter-cat');
  const secEl = document.getElementById('filter-sec');
  const staEl = document.getElementById('filter-sta');
  const countEl = document.getElementById('result-count');
  const noRes = document.getElementById('no-results');

  function filterCards() {{
    const q   = searchEl.value.toLowerCase();
    const cat = catEl.value;
    const sec = secEl.value;
    const sta = staEl.value;
    let visible = 0;

    cards.forEach(card => {{
      const text    = card.textContent.toLowerCase();
      const cardCat = card.dataset.category;
      const cardSec = card.dataset.sector;
      const cardSta = card.dataset.state;

      const match =
        (!q   || text.includes(q)) &&
        (!cat || cardCat === cat)  &&
        (!sec || cardSec === sec)  &&
        (!sta || cardSta === sta);

      card.classList.toggle('hidden', !match);
      if (match) visible++;
    }});

    countEl.textContent = visible + ' result' + (visible !== 1 ? 's' : '');
    noRes.classList.toggle('hidden', visible > 0);
  }}

  [searchEl, catEl, secEl, staEl].forEach(el => el.addEventListener('input', filterCards));
  filterCards();
</script>
</body>
</html>"""

    out = OUTPUT_DIR / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"Dashboard written to {out} ({count} opportunities)")

    # Also write a JSON feed for embeds
    json_out = OUTPUT_DIR / "opportunities.json"
    json_out.write_text(json.dumps(opportunities, indent=2, ensure_ascii=False))
    print(f"JSON feed written to {json_out}")


if __name__ == "__main__":
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else "enriched_opportunities.json"
    with open(src) as f:
        data = json.load(f)
    generate(data)
