# OpenKalsh

Selenium-based scraper for [Kalshi.com](https://kalshi.com) prediction markets. Works as a skill for both **Claude Code** and **OpenClaw**.

> **Disclaimer:** The official [Kalshi API](https://trading-api.readme.io/reference) is the preferred method for programmatic data access. This scraper is for ad-hoc visual validation only. Respect Kalshi's Terms of Service.

## Project Structure

```
claude/
  SKILL.md              # Claude Code skill (declarative)

openclaw/
  skill.yaml            # OpenClaw manifest
  main.py               # OpenClaw entrypoint (executable plugin)
  SKILL.md              # OpenClaw skill docs

scripts/
  scrape_markets.py     # Shared scraper (used by both platforms)
```

---

## Installing into OpenClaw

### Option 1: Workspace skill (recommended)

Copy the skill into your OpenClaw workspace's `skills/` directory:

```bash
# From your OpenClaw workspace root
mkdir -p skills/kalshi-scraper
cp -r /path/to/OpenKalsh/openclaw/* skills/kalshi-scraper/
cp -r /path/to/OpenKalsh/scripts skills/kalshi-scraper/scripts
```

OpenClaw automatically discovers skills in `<workspace>/skills/` on the next session.

### Option 2: Managed skill (shared across workspaces)

Install into your global OpenClaw skills directory:

```bash
mkdir -p ~/.openclaw/skills/kalshi-scraper
cp -r /path/to/OpenKalsh/openclaw/* ~/.openclaw/skills/kalshi-scraper/
cp -r /path/to/OpenKalsh/scripts ~/.openclaw/skills/kalshi-scraper/scripts
```

### Option 3: Clone directly into skills

```bash
cd <your-workspace>/skills
git clone https://github.com/Payo-Systems/OpenKalsh.git kalshi-scraper
```

When cloning the full repo, the entrypoint in `openclaw/main.py` already references `../scripts/scrape_markets.py` via relative path, so it works out of the box.

### Install dependencies

```bash
pip install selenium webdriver-manager
```

If no Chrome/Chromium browser is available on your system:

```bash
pip install playwright
python3 -m playwright install chromium
```

### Verify installation

```bash
# From the skill directory
python3 openclaw/main.py browse --url "https://kalshi.com/category/politics" --max 3
```

You should see JSON output with market titles and URLs.

### Optional: Configure in openclaw.json

Add to `~/.openclaw/openclaw.json` if you want to manage the skill explicitly:

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

---

## Installing into Claude Code

Claude Code discovers skills from the `claude/SKILL.md` file. No special installation is needed — just work within this repo:

```bash
cd /path/to/OpenKalsh
claude
```

Then ask Claude to scrape Kalshi markets. It will read the skill instructions and run the scraper.

---

## Usage

### Browse markets by category

```bash
python3 scripts/scrape_markets.py browse --url "https://kalshi.com/category/politics" --max 5
```

Available categories: `politics`, `economics`, `crypto`, `climate`, `culture`, `companies`, `financials`.
Sports: `https://kalshi.com/sports/all-sports`.

### Scrape a single market

```bash
python3 scripts/scrape_markets.py market "https://kalshi.com/markets/kxfedchairnom/fed-chair-nominee/kxfedchairnom-29"
```

### Output

Browse returns a JSON array:

```json
[
  { "title": "Fed decision in March?", "url": "https://kalshi.com/markets/..." }
]
```

Market returns a JSON object with outcomes:

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

### Optional flags

| Flag              | Description                           |
|-------------------|---------------------------------------|
| `--no-headless`   | Launch visible browser for debugging. |
| `--chrome-binary` | Override Chrome binary path.          |
| `--chromedriver`  | Override chromedriver binary path.     |
