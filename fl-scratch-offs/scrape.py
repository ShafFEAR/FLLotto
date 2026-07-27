#!/usr/bin/env python3
"""
Scrapes Florida scratch-off "prizes remaining" data from lottery.net
(a public aggregator of official Florida Lottery data) and saves it
to data.json for the webpage to display.

Run: python3 scrape.py
"""
import json
import re
import sys
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

URL = "https://www.lottery.net/florida/scratch-offs"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; personal-scratch-off-tracker/1.0)"
}


def parse_money(text):
    """Turn '$1,000,000' or '$50,000YR/LIFE' into a float where possible, else keep raw."""
    text = text.strip()
    m = re.match(r"\$([\d,]+)", text)
    if m:
        return float(m.group(1).replace(",", ""))
    return None


def parse_odds(text):
    """Turn '1 in 3.31' into a float 3.31 (lower = better odds)."""
    m = re.search(r"1 in ([\d.]+)", text)
    return float(m.group(1)) if m else None


def scrape():
    resp = requests.get(URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    table = soup.find("table")
    if table is None:
        raise RuntimeError("Could not find a table on the page — site layout may have changed.")

    rows = table.find_all("tr")
    header_cells = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]

    games = []
    for row in rows[1:]:
        cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
        if len(cells) < 6:
            continue
        name, game_no, price, top_prize, prizes_remaining, odds = cells[:6]
        games.append({
            "name": name,
            "game_number": game_no,
            "price": price,
            "price_value": parse_money(price),
            "top_prize": top_prize,
            "top_prize_value": parse_money(top_prize),
            "prizes_remaining": int(prizes_remaining) if prizes_remaining.isdigit() else None,
            "odds": odds,
            "odds_value": parse_odds(odds),
        })

    if not games:
        raise RuntimeError("Parsed table but found zero games — check selectors.")

    return {
        "source": URL,
        "note": "Data aggregated from public Florida Lottery figures; not the official site itself.",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "games": games,
    }


if __name__ == "__main__":
    try:
        data = scrape()
    except Exception as e:
        print(f"Scrape failed: {e}", file=sys.stderr)
        sys.exit(1)

    with open("data.json", "w") as f:
        json.dump(data, f, indent=2)

    print(f"Saved {len(data['games'])} games to data.json")
