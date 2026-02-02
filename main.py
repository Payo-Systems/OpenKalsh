"""OpenClaw skill entrypoint for Kalshi market data.

This module wraps scripts/kalshi_api.py so OpenClaw can load and
execute it as a plugin.  Uses the Kalshi public REST API — no
external dependencies required.
"""

import json
import sys
import os

# Add the skill root to sys.path so we can import the API client
_skill_root = os.path.abspath(os.path.dirname(__file__))
if _skill_root not in sys.path:
    sys.path.insert(0, _skill_root)

from scripts.kalshi_api import (
    parse_kalshi_url,
    fetch_events,
    fetch_event,
    events_to_browse_list,
    event_to_market_result,
    KalshiAPIError,
)


def browse(url: str = "https://kalshi.com", max_markets: int = 20) -> list[dict]:
    """List markets from a Kalshi category or home page.

    Args:
        url: Kalshi page URL or category URL.
        max_markets: Maximum number of markets to return.

    Returns:
        List of dicts with 'title' and 'url' keys.
    """
    parsed = parse_kalshi_url(url)
    category_slug = parsed.get("category_slug")
    events = fetch_events(category_slug=category_slug, limit=max_markets)
    return events_to_browse_list(events, max_markets=max_markets)


def market(url: str) -> dict:
    """Fetch data for a single Kalshi market/event.

    Args:
        url: Full URL of the Kalshi market page, or an event ticker.

    Returns:
        Dict with 'title', 'outcomes', 'status', and 'error' keys.
    """
    parsed = parse_kalshi_url(url)
    event_ticker = parsed.get("event_ticker")

    if not event_ticker:
        return {
            "title": None,
            "outcomes": [],
            "status": "error",
            "error": f"Could not extract event ticker from URL: {url}",
        }

    try:
        event = fetch_event(event_ticker)
        return event_to_market_result(event)
    except KalshiAPIError as exc:
        return {
            "title": None,
            "outcomes": [],
            "status": "error",
            "error": str(exc),
        }


# Allow direct execution: python main.py browse|market [args]
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py browse [--url URL] [--max N]")
        print("       python main.py market <URL>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "browse":
        url = "https://kalshi.com"
        max_m = 20
        args = sys.argv[2:]
        i = 0
        while i < len(args):
            if args[i] == "--url" and i + 1 < len(args):
                url = args[i + 1]
                i += 2
            elif args[i] == "--max" and i + 1 < len(args):
                max_m = int(args[i + 1])
                i += 2
            else:
                i += 1
        print(json.dumps(browse(url=url, max_markets=max_m), indent=2, ensure_ascii=False))

    elif command == "market":
        if len(sys.argv) < 3:
            print("Usage: python main.py market <URL>", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(market(url=sys.argv[2]), indent=2, ensure_ascii=False))

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)
