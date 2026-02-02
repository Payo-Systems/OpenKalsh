#!/usr/bin/env python3
"""
Kalshi Prediction Market Scraper

Scrapes live market data from Kalshi.com using Selenium.
Kalshi is a Single Page Application (SPA) built with React, so a real browser
engine is required to render the JavaScript-driven DOM before data extraction.

DISCLAIMER: The official Kalshi API (https://trading-api.readme.io/reference)
is the preferred method for programmatic, high-frequency, or production data
access. This scraper is intended for ad-hoc visual validation and one-off
research only. Respect Kalshi's Terms of Service and robots.txt. Do not use
this for automated trading or any activity that violates their policies.
"""

import argparse
import json
import os
import sys
import re
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)

try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    ChromeDriverManager = None


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KALSHI_BASE_URL = "https://kalshi.com"
KALSHI_BROWSE_URL = f"{KALSHI_BASE_URL}/browse"
DEFAULT_WAIT_SECONDS = 20


# ---------------------------------------------------------------------------
# Driver setup
# ---------------------------------------------------------------------------


def _find_chrome_binary() -> Optional[str]:
    """Auto-detect a Chrome/Chromium binary on the system.

    Search order:
      1. Common system paths (google-chrome, chromium-browser, chromium)
      2. Playwright-managed Chromium installs under ~/.cache/ms-playwright
    """
    for name in ("google-chrome", "google-chrome-stable", "chromium-browser", "chromium"):
        for directory in os.environ.get("PATH", "").split(os.pathsep):
            candidate = os.path.join(directory, name)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate

    pw_base = Path.home() / ".cache" / "ms-playwright"
    if pw_base.is_dir():
        candidates = sorted(pw_base.glob("chromium-*/chrome-linux64/chrome"), reverse=True)
        for c in candidates:
            if c.is_file() and os.access(str(c), os.X_OK):
                return str(c)

    return None


def _find_chromedriver() -> Optional[str]:
    """Auto-detect a chromedriver binary.

    Search order:
      1. System PATH
      2. /tmp/chromedriver-linux64/chromedriver (common manual download location)
    """
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = os.path.join(directory, "chromedriver")
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    candidate = "/tmp/chromedriver-linux64/chromedriver"
    if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
        return candidate

    return None


def create_driver(
    headless: bool = True,
    chrome_binary: Optional[str] = None,
    chromedriver_path: Optional[str] = None,
) -> webdriver.Chrome:
    """Create and return a configured Chrome WebDriver instance."""
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    binary = chrome_binary or _find_chrome_binary()
    if binary:
        opts.binary_location = binary

    driver_path = chromedriver_path or _find_chromedriver()
    if driver_path:
        service = Service(driver_path)
        return webdriver.Chrome(service=service, options=opts)

    if ChromeDriverManager is not None:
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=opts)

    return webdriver.Chrome(options=opts)


# ---------------------------------------------------------------------------
# Scraping helpers
# ---------------------------------------------------------------------------


def _safe_text(element) -> str:
    """Return stripped inner text of an element, or empty string."""
    try:
        return element.text.strip()
    except Exception:
        return ""


def _parse_price(raw: str) -> Optional[int]:
    """Extract a numeric price (in cents) from text like '47¢', '$0.47', or '47%'.

    Kalshi displays prices as percentages (e.g. '35%') which correspond to
    cents in their binary contracts.  Returns an integer in [0, 100].
    """
    raw = raw.replace("\u00a2", "").replace("$", "").replace("%", "").strip()
    match = re.search(r"(\d+\.?\d*)", raw)
    if match:
        value = float(match.group(1))
        if value < 1.0:
            return round(value * 100)
        return round(value)
    return None


def scrape_market_page(driver: webdriver.Chrome, url: str) -> dict:
    """Scrape a single Kalshi market/event page and return structured data."""
    driver.get(url)

    result = {
        "url": url,
        "title": None,
        "outcomes": [],
        "status": None,
        "error": None,
    }

    try:
        WebDriverWait(driver, DEFAULT_WAIT_SECONDS).until(
            EC.presence_of_element_located(
                (By.XPATH, "//*[contains(text(),'Yes') or contains(text(),'No')]")
            )
        )
    except TimeoutException:
        result["error"] = "Timed out waiting for market page to render."
        return result

    # --- Title ---
    for tag in ("h1", "h2"):
        try:
            el = driver.find_element(By.TAG_NAME, tag)
            text = _safe_text(el)
            if text and len(text) > 5:
                result["title"] = text
                break
        except NoSuchElementException:
            continue
    if not result["title"]:
        result["title"] = driver.title

    # --- Outcomes ---
    # Kalshi uses two display formats:
    #   1. Multi-outcome markets: percentages in <span> (e.g. "98%") with
    #      candidate names nearby (e.g. "Kevin Warsh\n98%").
    #   2. Binary markets: cent prices in the order panel (e.g. "15¢") with
    #      "Yes"/"No" labels nearby (e.g. "Yes  15¢").
    # Chart axis labels use <tspan> (SVG) — we skip those.
    try:
        price_elements = driver.find_elements(
            By.XPATH,
            "//*[contains(text(),'%') or contains(text(),'\u00a2')]"
        )

        for el in price_elements:
            if el.tag_name in ("tspan", "text"):
                continue
            text = _safe_text(el)
            # Match either "47%" or "15¢" style prices
            if len(text) > 10:
                continue
            if not re.search(r"\d+[%¢]", text):
                continue
            price = _parse_price(text)
            if price is None or price > 100:
                continue

            # Walk up to the nearest container that has a meaningful label.
            parent = el
            label = None
            for _ in range(3):
                try:
                    parent = parent.find_element(By.XPATH, "..")
                except NoSuchElementException:
                    break
                parent_text = _safe_text(parent)
                # Remove price portions to isolate the label
                candidate = re.sub(r"<?\d+[%¢]", "", parent_text).strip()
                candidate = re.sub(r"[\d.]+¢", "", candidate).strip()
                # Check for Yes/No first
                m = re.search(r"\b(Yes|No)\b", candidate)
                if m:
                    label = m.group(1).capitalize()
                    break
                # Otherwise use the remaining text as the option name
                lines = [l.strip() for l in candidate.split("\n") if l.strip()]
                if lines and 2 < len(lines[0]) < 60:
                    if re.match(r"^[▲▼△▽↑↓]\s*\d", lines[0]):
                        continue
                    label = lines[0]
                    break

            if label:
                result["outcomes"].append(
                    {"label": label, "price_cents": price, "raw": text}
                )

    except Exception as exc:
        result["error"] = f"Outcome extraction failed: {exc}"

    # De-duplicate (keep first occurrence)
    seen = set()
    unique = []
    for o in result["outcomes"]:
        key = (o["label"], o["price_cents"])
        if key not in seen:
            seen.add(key)
            unique.append(o)

    # If we have both % and ¢ outcomes, the ¢ ones are from the order
    # panel for the currently selected sub-market.  Prefer the named
    # outcomes (those with % or non-Yes/No labels from % elements).
    has_percent = any("%" in o["raw"] for o in unique)
    has_cents = any("¢" in o["raw"] for o in unique)
    if has_percent and has_cents:
        unique = [o for o in unique if "%" in o["raw"]]

    result["outcomes"] = unique

    result["status"] = "ok" if result["outcomes"] else "no_outcomes_found"
    return result


def scrape_browse_page(
    driver: webdriver.Chrome,
    url: str = KALSHI_BROWSE_URL,
    max_markets: int = 20,
) -> list[dict]:
    """Scrape a Kalshi browse / category page.

    Returns a list of dicts with ``title`` and ``url`` for each market card.
    Kalshi market links follow the pattern /markets/<slug>/...
    """
    driver.get(url)
    markets: list[dict] = []

    try:
        WebDriverWait(driver, DEFAULT_WAIT_SECONDS).until(
            EC.presence_of_element_located(
                (By.XPATH, "//a[contains(@href,'/markets/')]")
            )
        )
    except TimeoutException:
        return markets

    links = driver.find_elements(
        By.XPATH, "//a[contains(@href,'/markets/')]"
    )

    seen_hrefs: set[str] = set()
    for link in links:
        href = link.get_attribute("href") or ""
        if href in seen_hrefs:
            continue
        # Skip nav/category links — real market links have multiple path segments
        # e.g. /markets/kxgovshutlength/...
        parts = href.replace(KALSHI_BASE_URL, "").strip("/").split("/")
        if len(parts) < 2:
            continue
        seen_hrefs.add(href)

        title = _safe_text(link)
        if not title or len(title) < 5:
            continue

        # Clean trailing price snippets from card text (e.g. "Title\n8%")
        title = re.split(r"\n\s*<?(\d+[%¢])", title)[0].strip()

        markets.append({"title": title, "url": href})
        if len(markets) >= max_markets:
            break

    return markets


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape Kalshi prediction market data."
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run browser in visible (non-headless) mode.",
    )
    parser.add_argument(
        "--chrome-binary",
        default=None,
        help="Path to Chrome/Chromium binary. Auto-detected if omitted.",
    )
    parser.add_argument(
        "--chromedriver",
        default=None,
        help="Path to chromedriver binary. Auto-detected if omitted.",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # -- browse --
    browse_p = sub.add_parser("browse", help="List markets from the browse page.")
    browse_p.add_argument("--url", default=KALSHI_BROWSE_URL, help="Browse page URL.")
    browse_p.add_argument(
        "--max", type=int, default=20, help="Max number of markets to return."
    )

    # -- market --
    market_p = sub.add_parser("market", help="Scrape a single market page.")
    market_p.add_argument("url", help="Full URL of the Kalshi market page.")

    args = parser.parse_args()

    driver = None
    try:
        driver = create_driver(
            headless=not args.no_headless,
            chrome_binary=args.chrome_binary,
            chromedriver_path=args.chromedriver,
        )

        if args.command == "browse":
            data = scrape_browse_page(driver, url=args.url, max_markets=args.max)
        elif args.command == "market":
            data = scrape_market_page(driver, url=args.url)
        else:
            parser.print_help()
            sys.exit(1)

        print(json.dumps(data, indent=2, ensure_ascii=False))

    except WebDriverException as exc:
        error = {"error": f"WebDriver error: {exc}"}
        print(json.dumps(error, indent=2), file=sys.stderr)
        sys.exit(1)
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    main()
