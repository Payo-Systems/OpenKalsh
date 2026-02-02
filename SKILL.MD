---
name: kalshi-scraper
description: Scrape live prediction market data from Kalshi.com using Selenium. Handles Kalshi's React SPA by rendering the page in a headless browser and extracting market titles, outcome labels, and prices as structured JSON.
version: 1.0.0
---

# Kalshi Market Scraper

## Disclaimer

> **The official Kalshi API (<https://trading-api.readme.io/reference>) is the
> preferred method for programmatic, high-frequency, or production data access.**
> This skill is designed for **ad-hoc visual validation** and one-off research
> only. Always respect Kalshi's Terms of Service and `robots.txt`. Do not use
> this for automated trading, bulk harvesting, or any activity that violates
> their policies.

## Why Selenium?

Kalshi is a **Single Page Application (SPA)** built with React. The market
data (titles, prices, outcome buttons) is rendered client-side by JavaScript
after the initial HTML shell loads. A simple HTTP request (e.g. `requests.get`)
returns only the empty app shell and none of the actual market content.

Selenium drives a real Chromium browser, waits for React to mount and
hydrate the DOM, and only then extracts the visible data--making it the
correct tool for this job.

## Prerequisites

The agent must ensure the following Python packages are installed before
running the scraper:

```bash
pip install selenium webdriver-manager
```

A Chromium-based browser must also be available on the system. The script
auto-detects Chrome/Chromium from:

1. System PATH (`google-chrome`, `chromium-browser`, `chromium`)
2. Playwright-managed Chromium (`~/.cache/ms-playwright/chromium-*/`)

If no system Chrome exists, install one via Playwright:

```bash
pip install playwright && python -m playwright install chromium
```

A matching ChromeDriver is also required. The script checks:

1. System PATH for `chromedriver`
2. `/tmp/chromedriver-linux64/chromedriver` (manual download location)
3. Falls back to `webdriver-manager` auto-download

You can also specify paths explicitly with `--chrome-binary` and
`--chromedriver` flags.

**Note:** On minimal server environments, `libasound2` may be missing.
If Chrome crashes on startup, set `LD_LIBRARY_PATH` to include the
library or install it via your package manager.

## Script Location

```
scripts/scrape_markets.py
```

## Commands

### 1. Browse markets

List market cards from a Kalshi category page. Returns a JSON array of
objects, each containing `title` and `url`.

```bash
python3 scripts/scrape_markets.py browse --url "https://kalshi.com/category/politics" --max 5
```

Optional flags:

| Flag    | Default                          | Description                    |
|---------|----------------------------------|--------------------------------|
| `--url` | `https://kalshi.com/browse`      | Category page URL.             |
| `--max` | `20`                             | Maximum number of markets.     |

Available category URLs:

- `https://kalshi.com/category/politics`
- `https://kalshi.com/category/economics`
- `https://kalshi.com/category/crypto`
- `https://kalshi.com/category/climate`
- `https://kalshi.com/category/culture`
- `https://kalshi.com/category/companies`
- `https://kalshi.com/category/financials`
- `https://kalshi.com/sports/all-sports`

Expected output shape:

```json
[
  {
    "title": "Fed decision in March?",
    "url": "https://kalshi.com/markets/kxfeddecision/fed-meeting/kxfeddecision-26mar"
  }
]
```

### 2. Scrape a single market

Fetch detailed outcome and pricing data for one market page. Works with
both **binary markets** (Yes/No with cent prices) and **multi-outcome
markets** (named candidates with percentage prices).

```bash
python3 scripts/scrape_markets.py market "<URL>"
```

Example -- multi-outcome market:

```bash
python3 scripts/scrape_markets.py market "https://kalshi.com/markets/kxfedchairnom/fed-chair-nominee/kxfedchairnom-29"
```

```json
{
  "url": "https://kalshi.com/markets/kxfedchairnom/fed-chair-nominee/kxfedchairnom-29",
  "title": "Who will Trump nominate as Fed Chair?",
  "outcomes": [
    { "label": "Kevin Warsh", "price_cents": 98, "raw": "98%" },
    { "label": "Judy Shelton", "price_cents": 2, "raw": "2%" }
  ],
  "status": "ok",
  "error": null
}
```

Example -- binary market:

```bash
python3 scripts/scrape_markets.py market "https://kalshi.com/markets/kxaliens/aliens/kxaliens-27"
```

```json
{
  "url": "https://kalshi.com/markets/kxaliens/aliens/kxaliens-27",
  "title": "Will the U.S. confirm that aliens exist before 2027?",
  "outcomes": [
    { "label": "Yes", "price_cents": 15, "raw": "15¢" },
    { "label": "No",  "price_cents": 86, "raw": "86¢" }
  ],
  "status": "ok",
  "error": null
}
```

### 3. Visible browser mode (debugging)

Append `--no-headless` to any command to launch a visible browser window.
Useful for debugging selector issues.

```bash
python3 scripts/scrape_markets.py --no-headless browse --url "https://kalshi.com/category/politics"
```

### 4. Explicit binary paths

Override auto-detection if needed:

```bash
python3 scripts/scrape_markets.py \
  --chrome-binary /path/to/chrome \
  --chromedriver /path/to/chromedriver \
  browse --max 10
```

## Agent Usage Instructions

When the user asks for Kalshi market data, follow this sequence:

1. **Install dependencies** if not already present:
   ```bash
   pip install selenium webdriver-manager
   ```

2. **Ensure a Chrome binary is available.** If not found on PATH, install
   via Playwright:
   ```bash
   pip install playwright && python3 -m playwright install chromium
   ```

3. **Run the appropriate command** (`browse` or `market`) using Bash.
   For the `browse` command, use a specific category URL (e.g.
   `https://kalshi.com/category/politics`) rather than the bare `/browse`
   path, as category pages contain the actual market listings.

4. **Parse the JSON output** from stdout. The script always emits valid JSON
   to stdout on success, and a JSON error object to stderr on failure.

5. **Present the data** to the user in a readable format (table, summary,
   or raw JSON depending on what they asked for).

6. If the script returns `"status": "no_outcomes_found"` or an `"error"`
   field, inform the user that the page structure may have changed and
   recommend using the official Kalshi API instead.

## Design Decisions

| Decision | Rationale |
|---|---|
| **Headless Chrome** | Required for server/CI environments where no display is available. |
| **Explicit Waits (`WebDriverWait`)** | Avoids brittle `time.sleep()` calls. Waits only as long as the DOM actually needs to render. |
| **XPath selectors on text content** | Kalshi's CSS class names are hashed by their build toolchain and change between deploys. Selecting by visible text (`%`, `¢`, `Yes`, `No`) or semantic tags (`h1`, `a[href*=markets]`) is more durable. |
| **SVG `<tspan>` filtering** | Chart axis labels (0%, 25%, 50%, etc.) are rendered in SVG `<tspan>` elements and are excluded to avoid false positives. |
| **Auto-detection of Chrome** | Searches system PATH, then Playwright-managed installs, so the script works out of the box on most setups. |
| **JSON output** | Machine-readable by default so the agent can parse and post-process results programmatically. |

## Limitations

- **Rate limits & blocking:** Kalshi may rate-limit or block automated
  browsers. Do not run this at high frequency.
- **Selector drift:** If Kalshi significantly redesigns their UI, the XPath
  selectors may need updating. The script is built to be resilient, but no
  scraper is immune to structural changes.
- **No authentication:** This scraper accesses only publicly visible market
  data. It does not log in or access private account information.
- **Single-threaded:** The script opens one browser instance per invocation.
  For bulk work, use the official API.
