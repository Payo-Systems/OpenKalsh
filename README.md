# OpenKalsh

Selenium-based scraper for [Kalshi.com](https://kalshi.com) prediction markets, packaged as a drop-in [OpenClaw](https://github.com/openclaw/openclaw) skill.

> **Disclaimer:** The official [Kalshi API](https://trading-api.readme.io/reference) is the preferred method for programmatic data access. This scraper is for ad-hoc visual validation only. Respect Kalshi's Terms of Service.

## Installation

Clone or copy this repo directly into your OpenClaw `skills/` directory:

```bash
cd <your-workspace>/skills
git clone https://github.com/Payo-Systems/OpenKalsh.git kalshi-scraper
```

Or into the global skills directory:

```bash
cd ~/.openclaw/skills
git clone https://github.com/Payo-Systems/OpenKalsh.git kalshi-scraper
```

OpenClaw discovers it automatically on the next session.

### Dependencies

```bash
pip install selenium webdriver-manager
```

If no Chrome/Chromium is on your system:

```bash
pip install playwright
python3 -m playwright install chromium
```

### Verify

```bash
python3 main.py browse --url "https://kalshi.com/category/politics" --max 3
```

### Optional: openclaw.json

```json
{
  "skills": {
    "entries": {
      "kalshi-scraper": {
        "enabled": true
      }
    }
  }
}
```

## Skill Structure

```
skill.yaml          # OpenClaw manifest
main.py             # Entrypoint — exposes browse() and market()
SKILL.md            # Skill docs
scripts/
  scrape_markets.py # Scraper (headless Selenium)
```

## Usage

### Browse markets by category

```bash
python3 main.py browse --url "https://kalshi.com/category/politics" --max 5
```

Categories: `politics`, `economics`, `crypto`, `climate`, `culture`, `companies`, `financials`.
Sports: `https://kalshi.com/sports/all-sports`.

### Scrape a single market

```bash
python3 main.py market "https://kalshi.com/markets/kxfedchairnom/fed-chair-nominee/kxfedchairnom-29"
```

### Output

Browse returns a JSON array:

```json
[
  { "title": "Fed decision in March?", "url": "https://kalshi.com/markets/..." }
]
```

Market returns a JSON object:

```json
{
  "title": "Who will Trump nominate as Fed Chair?",
  "outcomes": [
    { "label": "Kevin Warsh", "price_cents": 98, "raw": "98%" },
    { "label": "Judy Shelton", "price_cents": 2, "raw": "2%" }
  ],
  "status": "ok",
  "error": null
}
```

### Flags

| Flag              | Description                           |
|-------------------|---------------------------------------|
| `--no-headless`   | Launch visible browser for debugging. |
| `--chrome-binary` | Override Chrome binary path.          |
| `--chromedriver`  | Override chromedriver binary path.     |

You can also use the full CLI via the scraper directly:

```bash
python3 scripts/scrape_markets.py browse --max 10
python3 scripts/scrape_markets.py market "<URL>"
```
