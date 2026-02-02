#!/usr/bin/env python3
"""Tests for the Kalshi REST API client."""

import json
import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(__file__))

from scripts.kalshi_api import (
    parse_kalshi_url,
    fetch_events,
    fetch_event,
    events_to_browse_list,
    event_to_market_result,
    _market_price_cents,
    KalshiAPIError,
)

PASS = 0
FAIL = 0


def report(name, ok, detail=""):
    global PASS, FAIL
    tag = "PASS" if ok else "FAIL"
    if not ok:
        FAIL += 1
    else:
        PASS += 1
    print(f"  [{tag}] {name}" + (f"  -- {detail}" if detail else ""))


# ── Unit Tests ─────────────────────────────────────────────────

print("\n=== Unit Tests ===")

# -- parse_kalshi_url --
print("\n--- URL parsing ---")

r = parse_kalshi_url("https://kalshi.com")
report("home page", r == {"type": "home"}, f"got {r}")

r = parse_kalshi_url("https://kalshi.com/")
report("home page trailing slash", r == {"type": "home"}, f"got {r}")

r = parse_kalshi_url("https://kalshi.com/category/economics")
report("category URL", r == {"type": "category", "category_slug": "economics"}, f"got {r}")

r = parse_kalshi_url("https://kalshi.com/category/politics")
report("category politics", r == {"type": "category", "category_slug": "politics"}, f"got {r}")

r = parse_kalshi_url("https://kalshi.com/sports/all-sports")
report("sports URL", r == {"type": "category", "category_slug": "all-sports"}, f"got {r}")

r = parse_kalshi_url("https://kalshi.com/markets/kxfed/fed-meeting/kxfed-26mar")
report("market URL", r["type"] == "market" and r["event_ticker"] == "KXFED-26MAR", f"got {r}")

r = parse_kalshi_url("https://kalshi.com/markets/kxfed/fed-meeting")
report("market URL 2 segments", r["type"] == "market" and r["event_ticker"] == "FED-MEETING", f"got {r}")

r = parse_kalshi_url("KXFED-26MAR")
report("bare ticker", r == {"type": "event_ticker", "event_ticker": "KXFED-26MAR"}, f"got {r}")

r = parse_kalshi_url("kxfed-26mar")
report("bare ticker lowercase", r == {"type": "event_ticker", "event_ticker": "KXFED-26MAR"}, f"got {r}")

# -- _market_price_cents --
print("\n--- Price extraction ---")

report("price from last_price", _market_price_cents({"last_price": 83}) == 83)
report("price from last_price zero", _market_price_cents({"last_price": 0}) == 0)
report("price from last_price 100", _market_price_cents({"last_price": 100}) == 100)
report("price from yes_ask fallback", _market_price_cents({"yes_ask": 47}) == 47)
report("price from yes_bid fallback", _market_price_cents({"yes_bid": 12}) == 12)
report("price missing", _market_price_cents({}) is None)

# -- event_to_market_result --
print("\n--- Outcome extraction ---")

# Binary market
binary_event = {
    "title": "Will it rain tomorrow?",
    "mutually_exclusive": False,
    "markets": [
        {"ticker": "RAIN-YES", "last_price": 65}
    ],
}
r = event_to_market_result(binary_event)
report("binary title", r["title"] == "Will it rain tomorrow?")
report("binary status ok", r["status"] == "ok")
report("binary 2 outcomes", len(r["outcomes"]) == 2, f"got {len(r['outcomes'])}")
if len(r["outcomes"]) == 2:
    report("binary Yes label", r["outcomes"][0]["label"] == "Yes")
    report("binary Yes price", r["outcomes"][0]["price_cents"] == 65)
    report("binary No label", r["outcomes"][1]["label"] == "No")
    report("binary No price", r["outcomes"][1]["price_cents"] == 35)

# Multi-outcome market
multi_event = {
    "title": "Fed decision in March?",
    "mutually_exclusive": True,
    "markets": [
        {"ticker": "KXFED-HOLD", "yes_sub_title": "Hold", "last_price": 83},
        {"ticker": "KXFED-CUT25", "yes_sub_title": "Cut 25bps", "last_price": 12},
        {"ticker": "KXFED-CUT50", "yes_sub_title": "Cut 50bps", "last_price": 3},
    ],
}
r = event_to_market_result(multi_event)
report("multi title", r["title"] == "Fed decision in March?")
report("multi status ok", r["status"] == "ok")
report("multi 3 outcomes", len(r["outcomes"]) == 3, f"got {len(r['outcomes'])}")
if len(r["outcomes"]) == 3:
    report("multi first label", r["outcomes"][0]["label"] == "Hold")
    report("multi first price 83", r["outcomes"][0]["price_cents"] == 83)

# Empty markets
empty_event = {"title": "Empty", "markets": []}
r = event_to_market_result(empty_event)
report("empty market status", r["status"] == "no_outcomes_found")
report("empty market error", r["error"] is not None)

# -- events_to_browse_list --
print("\n--- Browse list conversion ---")

events = [
    {"title": "Event A", "event_ticker": "EVA", "series_ticker": "EVA"},
    {"title": "Event B", "event_ticker": "EVB", "series_ticker": "EVB"},
    {"title": "Event C", "event_ticker": "EVC", "series_ticker": "EVC"},
]
r = events_to_browse_list(events, max_markets=2)
report("browse list length capped", len(r) == 2, f"got {len(r)}")
report("browse list has title", r[0]["title"] == "Event A")
report("browse list has url", "kalshi.com/markets/" in r[0]["url"])

r = events_to_browse_list([], max_markets=5)
report("browse list empty input", len(r) == 0)


# ── Integration Tests (live API) ──────────────────────────────

print("\n=== Integration Tests (live API) ===")

# Test 1: Fetch events
print("\n--- Fetch events ---")
events = []
try:
    events = fetch_events(limit=5)
    ok = isinstance(events, list) and len(events) > 0
    report("fetch_events() returns events", ok, f"got {len(events)} event(s)")
    if events:
        for e in events[:3]:
            print(f"    - {e.get('title', '?')[:60]}  [{e.get('event_ticker', '?')}]")
        first = events[0]
        report("event has title", "title" in first)
        report("event has event_ticker", "event_ticker" in first)
        report("event has markets", "markets" in first and isinstance(first["markets"], list))
except KalshiAPIError as exc:
    report("fetch_events()", False, str(exc))
except Exception as exc:
    report("fetch_events()", False, str(exc))
    traceback.print_exc()

# Test 2: Fetch a single event
print("\n--- Fetch single event ---")
single_event = None
try:
    if events:
        ticker = events[0]["event_ticker"]
        print(f"  Fetching event: {ticker}")
        single_event = fetch_event(ticker)
        ok = isinstance(single_event, dict) and single_event.get("title") is not None
        report("fetch_event() returns data", ok)
        if single_event:
            print(f"    title: {single_event.get('title', '?')[:60]}")
            markets = single_event.get("markets", [])
            print(f"    markets: {len(markets)}")
            report("event has nested markets", len(markets) > 0)
    else:
        report("fetch_event() skipped", False, "no events from browse")
except KalshiAPIError as exc:
    report("fetch_event()", False, str(exc))
except Exception as exc:
    report("fetch_event()", False, str(exc))
    traceback.print_exc()

# Test 3: Full browse flow via main module
print("\n--- Full browse flow ---")
try:
    from main import browse as main_browse
    results = main_browse(max_markets=5)
    ok = isinstance(results, list) and len(results) > 0
    report("browse() returns results", ok, f"got {len(results)} result(s)")
    if results:
        for r in results[:3]:
            print(f"    - {r['title'][:60]}  =>  {r['url']}")
        report("browse result has title & url", "title" in results[0] and "url" in results[0])
except Exception as exc:
    report("browse()", False, str(exc))
    traceback.print_exc()

# Test 4: Full market flow via main module
print("\n--- Full market flow ---")
try:
    from main import market as main_market
    if events:
        ticker = events[0]["event_ticker"]
        print(f"  Testing ticker: {ticker}")
        result = main_market(url=ticker)
        print(f"  title: {result.get('title', '?')}")
        print(f"  outcomes: {len(result.get('outcomes', []))}")
        print(f"  status: {result.get('status')}")
        if result.get("error"):
            print(f"  error: {result['error']}")

        ok = isinstance(result, dict) and result.get("title") is not None
        report("market() returns data", ok)

        if result.get("outcomes"):
            for o in result["outcomes"][:5]:
                print(f"    - {o['label']}: {o['price_cents']}¢  (raw: {o['raw']})")
            report("outcomes found", True, f"{len(result['outcomes'])} outcome(s)")
        elif result.get("status") == "ok":
            report("market page returned outcomes", False, "status ok but no outcomes")
        else:
            report("market page had issue", False, result.get("error", "unknown"))
    else:
        report("market() skipped", False, "no events available")
except Exception as exc:
    report("market()", False, str(exc))
    traceback.print_exc()

# ── Summary ─────────────────────────────────────────────────────

print(f"\n=== Results: {PASS} passed, {FAIL} failed ===")
sys.exit(1 if FAIL > 0 else 0)
