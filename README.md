# Clawshi

Kalshi prediction market data via the public REST API, packaged as a drop-in [OpenClaw](https://github.com/openclaw/openclaw) skill.

## Installation

Clone or copy this repo directly into your OpenClaw `skills/` directory:

```bash
cd <your-workspace>/skills
git clone https://github.com/Payo-Systems/Clawshi.git kalshi-market-data
```

Or into the global skills directory:

```bash
cd ~/.openclaw/skills
git clone https://github.com/Payo-Systems/Clawshi.git kalshi-market-data
```

OpenClaw discovers it automatically on the next session.

### Dependencies

No external dependencies. Uses Python stdlib only (`urllib.request` + `json`).

### Verify

```bash
python3 main.py browse --url "https://kalshi.com" --max 3
```

### Optional: openclaw.json

```json
{
  "skills": {
    "entries": {
      "kalshi-market-data": {
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
  kalshi_api.py     # REST API client (stdlib only)
```

## Usage

### Browse markets by category

```bash
python3 main.py browse --url "https://kalshi.com/category/politics" --max 5
```

Filter by category: `politics`, `economics`, `crypto`, `climate`, `culture`, `companies`, `financials`, `mentions`, `science`.
Sports: `https://kalshi.com/sports/all-sports`.

### Fetch a single market

```bash
python3 main.py market "https://kalshi.com/markets/kxfed/fed-meeting/kxfed-26mar"
```

You can also pass a bare event ticker:

```bash
python3 main.py market "KXFED-26MAR"
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
