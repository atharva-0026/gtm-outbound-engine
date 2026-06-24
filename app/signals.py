"""
Signal monitoring.

There's no free, no-signup API for funding rounds or regulatory
licences (Clay, Crunchbase, etc. all require paid accounts). This uses
Google News RSS instead — a plain HTTP GET, no API key, returns real
public news. Less structured than a dedicated signals API, but real
and free, which matters more for a project at this stage.

This is polling, not push — "real-time signal monitoring" in practice
almost always means checking on an interval (hourly/daily cron), not a
literal live feed. check_signals.py is meant to be run on a schedule
(see its docstring for the cron/launchd setup).

State (data/signal_state.json) tracks the most recent signal link seen
per company, so re-running only flags what's NEW since the last check —
that diffing is the actual point of "monitoring" vs. just searching.
"""

import json
import os
from urllib.parse import quote

import feedparser
import requests

STATE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "signal_state.json")
RSS_TIMEOUT_SECONDS = 10

SIGNAL_KEYWORDS = {
    "funding": ["funding", "raises", "raised", "series a", "series b", "series c", "series d", "valuation", "investment round"],
    "regulatory": ["licence", "license", "licensed", "regulatory", "approval", "approved", "registration", "authorised", "authorized"],
    "partnership": ["partnership", "partners with", "collaborat", "teams up"],
    "acquisition": ["acquire", "acquisition", "acquired", "merger", "buys", "bought"],
}


def classify_signal(title: str) -> str:
    lowered = title.lower()
    for category, keywords in SIGNAL_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            return category
    return "other"


def _rss_url(company_name: str) -> str:
    query = f'"{company_name}" (funding OR raises OR licence OR license OR acquisition OR partnership)'
    return f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"


def fetch_signals(company_name: str, max_results: int = 5):
    """Fetches current news signals for a company. Returns [] on any
    failure (network down, feed unreachable, etc.) rather than raising —
    signal monitoring being unavailable shouldn't break anything else."""
    try:
        response = requests.get(_rss_url(company_name), timeout=RSS_TIMEOUT_SECONDS)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except Exception:
        return []

    signals = []
    for entry in feed.entries[:max_results]:
        signals.append(
            {
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "category": classify_signal(entry.get("title", "")),
            }
        )
    return signals


def _load_state():
    if not os.path.exists(STATE_PATH):
        return {}
    with open(STATE_PATH) as f:
        return json.load(f)


def _save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def check_for_new_signals(companies: list) -> dict:
    """For each company, fetches current signals and returns only the
    ones not seen on a previous check. Updates state as a side effect."""
    state = _load_state()
    new_signals_by_company = {}

    for company in companies:
        name = company.get("company_name", "")
        current = fetch_signals(name)
        seen_links = set(state.get(name, {}).get("seen_links", []))

        new = [s for s in current if s["link"] and s["link"] not in seen_links]
        if new:
            new_signals_by_company[name] = new

        all_links = seen_links.union(s["link"] for s in current if s["link"])
        state[name] = {"seen_links": list(all_links)}

    _save_state(state)
    return new_signals_by_company
