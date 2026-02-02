# Kalshi Market Scraper — OpenClaw Skill

> **The official Kalshi API (<https://trading-api.readme.io/reference>) is the
> preferred method for production data access.** This skill is for ad-hoc use.

## Overview

OpenClaw plugin that scrapes live prediction market data from Kalshi.com.
Kalshi is a React SPA — Selenium renders the page in a headless browser
before extracting data.

## Exposed Functions

### `browse(url, max_markets)`

List markets from a Kalshi category page.

**Parameters:**
- `url` (str) — Category page URL. Default: `https://kalshi.com/category/politics`
- `max_markets` (int) — Max results. Default: `20`

**Returns:** List of `{"title": str, "url": str}`.

### `market(url)`

Scrape a single Kalshi market page.

**Parameters:**
- `url` (str) — Full market URL.

**Returns:**
```json
{
  "title": "...",
  "outcomes": [{"label": "Yes", "price_cents": 47, "raw": "47¢"}],
  "status": "ok",
  "error": null
}
```

## Categories

- `https://kalshi.com/category/politics`
- `https://kalshi.com/category/economics`
- `https://kalshi.com/category/crypto`
- `https://kalshi.com/category/climate`
- `https://kalshi.com/category/culture`
- `https://kalshi.com/category/companies`
- `https://kalshi.com/category/financials`
- `https://kalshi.com/sports/all-sports`
