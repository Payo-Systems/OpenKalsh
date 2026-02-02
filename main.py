"""OpenClaw skill entrypoint for the Kalshi market scraper.

This module wraps scripts/scrape_markets.py so OpenClaw can load and
execute it as a plugin.  It imports the shared scraper functions and
exposes them as callable skill actions.
"""

import json
import sys
import os

# Add the skill root to sys.path so we can import the scraper
_skill_root = os.path.abspath(os.path.dirname(__file__))
if _skill_root not in sys.path:
    sys.path.insert(0, _skill_root)

from scripts.scrape_markets import (
    create_driver,
    scrape_browse_page,
    scrape_market_page,
)


def browse(url: str = "https://kalshi.com/category/politics", max_markets: int = 20) -> list[dict]:
    """List markets from a Kalshi category page.

    Args:
        url: Kalshi category page URL.
        max_markets: Maximum number of markets to return.

    Returns:
        List of dicts with 'title' and 'url' keys.
    """
    driver = create_driver(headless=True)
    try:
        return scrape_browse_page(driver, url=url, max_markets=max_markets)
    finally:
        driver.quit()


def market(url: str) -> dict:
    """Scrape a single Kalshi market page.

    Args:
        url: Full URL of the Kalshi market page.

    Returns:
        Dict with 'title', 'outcomes', 'status', and 'error' keys.
    """
    driver = create_driver(headless=True)
    try:
        return scrape_market_page(driver, url=url)
    finally:
        driver.quit()


# Allow direct execution: python main.py browse|market [args]
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py browse [--url URL] [--max N]")
        print("       python main.py market <URL>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "browse":
        url = "https://kalshi.com/category/politics"
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
