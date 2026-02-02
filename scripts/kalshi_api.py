"""Kalshi public REST API client.

Lightweight client using only Python stdlib (urllib.request + json).
Replaces the Selenium-based scraper with direct API calls to
https://api.elections.kalshi.com/trade-api/v2.
"""

import json
import re
import urllib.request
import urllib.error
import urllib.parse

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
KALSHI_WEB = "https://kalshi.com"

# Map URL slugs to API category names where they differ
_SLUG_TO_CATEGORY = {
    "climate": "Climate and Weather",
    "science": "Science and Technology",
    "culture": "Entertainment",
    "mentions": "Social",
    "companies": "Financials",
    "all-sports": "Sports",
}


class KalshiAPIError(Exception):
    """Raised when a Kalshi API request fails."""

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def _api_get(path, params=None):
    """HTTP GET against the Kalshi API, returns parsed JSON.

    Args:
        path: API path (e.g. "/events").
        params: Optional dict of query parameters.

    Returns:
        Parsed JSON response as dict/list.

    Raises:
        KalshiAPIError: On HTTP or JSON errors.
    """
    url = BASE_URL + path
    if params:
        qs = urllib.parse.urlencode(
            {k: v for k, v in params.items() if v is not None}
        )
        url = f"{url}?{qs}"

    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        msg = f"Kalshi API returned HTTP {exc.code} for {path}"
        try:
            detail = exc.read().decode("utf-8", errors="replace")
            msg += f": {detail[:200]}"
        except Exception:
            pass
        raise KalshiAPIError(msg, status_code=exc.code) from exc
    except urllib.error.URLError as exc:
        raise KalshiAPIError(f"Network error calling {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise KalshiAPIError(f"Invalid JSON from {path}: {exc}") from exc


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------

def parse_kalshi_url(url):
    """Parse a Kalshi URL or bare ticker into a structured dict.

    Examples:
        "https://kalshi.com" → {"type": "home"}
        "https://kalshi.com/category/economics" → {"type": "category", "category_slug": "economics"}
        "https://kalshi.com/markets/kxfed/fed-meeting/kxfed-26mar"
            → {"type": "market", "event_ticker": "KXFED-26MAR"}
        "KXFED-26MAR" → {"type": "event_ticker", "event_ticker": "KXFED-26MAR"}
    """
    stripped = url.strip()

    # Bare ticker: no slashes, no dots → treat as event ticker
    if "/" not in stripped and "." not in stripped:
        return {"type": "event_ticker", "event_ticker": stripped.upper()}

    # Parse as URL
    parsed = urllib.parse.urlparse(stripped)
    path = parsed.path.strip("/")

    if not path:
        return {"type": "home"}

    segments = path.split("/")

    # /category/<slug>
    if segments[0] == "category" and len(segments) >= 2:
        return {"type": "category", "category_slug": segments[1]}

    # /sports/<slug>
    if segments[0] == "sports" and len(segments) >= 2:
        return {"type": "category", "category_slug": segments[1]}

    # /markets/<series_ticker>/<slug>/<event_ticker>
    # or /markets/<series_ticker>/<slug>
    if segments[0] == "markets" and len(segments) >= 3:
        # The event ticker is the last segment that looks like a ticker
        # (contains letters and possibly hyphens/numbers)
        event_ticker = segments[-1].upper()
        return {"type": "market", "event_ticker": event_ticker}

    # /markets/<something> with only 2 segments
    if segments[0] == "markets" and len(segments) == 2:
        return {"type": "market", "event_ticker": segments[1].upper()}

    return {"type": "home"}


# ---------------------------------------------------------------------------
# API data fetching
# ---------------------------------------------------------------------------

def fetch_events(category_slug=None, status="open", limit=20):
    """Fetch events from the Kalshi API.

    Args:
        category_slug: Optional category to filter by (client-side).
        status: Event status filter (default "open").
        limit: Maximum number of events to return.

    Returns:
        List of event dicts from the API.
    """
    # When filtering by category client-side, request more from the API
    # since matching events may be sparse across all categories.
    api_limit = max(limit, 200) if category_slug else limit

    params = {
        "with_nested_markets": "true",
        "status": status,
        "limit": str(api_limit),
    }

    data = _api_get("/events", params)
    events = data.get("events", [])

    if category_slug:
        # Resolve slug to API category name if needed
        category_name = _SLUG_TO_CATEGORY.get(category_slug.lower(), category_slug)
        cat_lower = category_name.lower()
        events = [
            e for e in events
            if e.get("category", "").lower() == cat_lower
        ]

    return events[:limit]


def fetch_event(event_ticker):
    """Fetch a single event by ticker.

    Args:
        event_ticker: The event ticker (e.g. "KXFED-26MAR").

    Returns:
        Event dict from the API.

    Raises:
        KalshiAPIError: If the event is not found or API fails.
    """
    ticker_encoded = urllib.parse.quote(event_ticker, safe="")
    data = _api_get(f"/events/{ticker_encoded}", {"with_nested_markets": "true"})
    return data.get("event", data)


# ---------------------------------------------------------------------------
# Data conversion
# ---------------------------------------------------------------------------

def events_to_browse_list(events, max_markets=20):
    """Convert API events into a browse list.

    Args:
        events: List of event dicts from the API.
        max_markets: Maximum items to return.

    Returns:
        List of {"title": str, "url": str} dicts.
    """
    results = []
    for event in events:
        title = event.get("title", "")
        ticker = event.get("event_ticker", "")
        series_ticker = event.get("series_ticker", "")

        if not title or not ticker:
            continue

        # Build Kalshi web URL:  /markets/<series>/<slug>/<ticker>
        # Use series ticker (lowercase) and event ticker (lowercase) for the URL
        slug = _ticker_to_slug(title)
        url = f"{KALSHI_WEB}/markets/{series_ticker.lower()}/{slug}/{ticker.lower()}"

        results.append({"title": title, "url": url})

        if len(results) >= max_markets:
            break

    return results


def event_to_market_result(event):
    """Convert an API event into a market result dict.

    Args:
        event: Event dict from the API (with nested markets).

    Returns:
        Dict with "title", "outcomes", "status", "error" keys.
    """
    result = {
        "title": event.get("title"),
        "outcomes": [],
        "status": None,
        "error": None,
    }

    markets = event.get("markets", [])
    if not markets:
        result["status"] = "no_outcomes_found"
        result["error"] = "No markets found for this event."
        return result

    mutually_exclusive = event.get("mutually_exclusive", False)

    if len(markets) == 1 and not mutually_exclusive:
        # Binary market: synthesize Yes/No from last_price
        m = markets[0]
        yes_price = _market_price_cents(m)
        no_price = 100 - yes_price if yes_price is not None else None

        if yes_price is not None:
            result["outcomes"].append({
                "label": "Yes",
                "price_cents": yes_price,
                "raw": f"{yes_price}%",
            })
            result["outcomes"].append({
                "label": "No",
                "price_cents": no_price,
                "raw": f"{no_price}%",
            })
    else:
        # Multi-outcome: one outcome per market
        for m in markets:
            label = m.get("yes_sub_title") or m.get("title") or m.get("ticker", "")
            price = _market_price_cents(m)
            if price is not None:
                result["outcomes"].append({
                    "label": label,
                    "price_cents": price,
                    "raw": f"{price}%",
                })

    result["status"] = "ok" if result["outcomes"] else "no_outcomes_found"
    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _market_price_cents(market):
    """Extract price in cents from a market dict.

    The API returns prices in cents as integers (e.g. 9 = 9 cents)
    when response_price_units is "usd_cent". Falls back to yes_ask
    or yes_bid if last_price is missing.
    """
    price = market.get("last_price")
    if price is None:
        price = market.get("yes_ask")
    if price is None:
        price = market.get("yes_bid")
    if price is not None:
        return round(float(price))
    return None


def _ticker_to_slug(title):
    """Convert a title string to a URL-friendly slug."""
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug[:60]
