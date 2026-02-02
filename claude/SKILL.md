---
name: kalshi-scraper
description: Scrape live prediction market data from Kalshi.com using Selenium. Handles Kalshi's React SPA by rendering the page in a headless browser and extracting market titles, outcome labels, and prices as structured JSON.
version: 1.0.0
---

# Kalshi Market Scraper

> **The official Kalshi API (<https://trading-api.readme.io/reference>) is the
> preferred method for programmatic, high-frequency, or production data access.**
> This skill is for ad-hoc visual validation only.

## Context

Kalshi is a React SPA. Market data is rendered client-side by JavaScript.
A plain HTTP request returns an empty shell. This skill uses Selenium to
drive a real headless browser, wait for React to hydrate, then extract data.

## Prerequisites

```bash
pip install selenium webdriver-manager
```

If no Chrome/Chromium is on PATH, install via Playwright:

```bash
pip install playwright && python3 -m playwright install chromium
```

## How to Run

The script is at `scripts/scrape_markets.py` relative to the repo root.

### Browse markets by category

```bash
python3 scripts/scrape_markets.py browse --url "https://kalshi.com/category/politics" --max 5
```

Categories: `politics`, `economics`, `crypto`, `climate`, `culture`, `companies`, `financials`.
Sports: `https://kalshi.com/sports/all-sports`.

### Scrape a single market

```bash
python3 scripts/scrape_markets.py market "https://kalshi.com/markets/kxfedchairnom/fed-chair-nominee/kxfedchairnom-29"
```

### Optional flags

- `--no-headless` — visible browser for debugging
- `--chrome-binary PATH` — override Chrome binary
- `--chromedriver PATH` — override chromedriver binary

## Output

Both commands emit JSON to stdout. Errors go to stderr as a JSON object.

### Browse output

```json
[
  { "title": "Fed decision in March?", "url": "https://kalshi.com/markets/..." }
]
```

### Market output

```json
{
  "url": "...",
  "title": "Who will Trump nominate as Fed Chair?",
  "outcomes": [
    { "label": "Kevin Warsh", "price_cents": 98, "raw": "98%" },
    { "label": "Judy Shelton", "price_cents": 2, "raw": "2%" }
  ],
  "status": "ok",
  "error": null
}
```

## Agent Instructions

1. Install deps if missing.
2. Run `browse` (with a category URL) or `market` via Bash.
3. Parse JSON stdout.
4. Present data to user as a table or summary.
5. If `"status": "no_outcomes_found"`, recommend the official Kalshi API.
