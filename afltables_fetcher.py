"""
afltables_fetcher.py
====================
Scrapes afltables.com for historical AFL statistics to supplement
Squiggle's current-season data (which is thin early in the season).

Provides three public functions:
  get_historical_home_away_split(team_name)     -> all-time home/away win rates
  get_historical_venue_record(team_name, venue) -> all-time venue win rates
  get_historical_scoring_averages(team_name, num_years=3) -> recent scoring baseline

Design principles:
  - Cache-first: every scraped page stored in .cache/afltables/ for 24 hours
  - Rate-limited: 2-second minimum gap between HTTP requests (threading.Lock)
  - Graceful: returns {} or [] on any error — never raises to caller
  - Transparent: User-Agent identifies the bot
"""

import hashlib
import json
import logging
import os
import re
import threading
import time
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

AFLTABLES_BASE = "https://afltables.com/afl/teams"
CACHE_DIR       = ".cache/afltables"
CACHE_TTL       = 86400   # 24 hours
MIN_REQUEST_GAP = 2.0     # seconds between requests (polite scraping)

# Verified slugs for all 18 current AFL teams (confirmed 2026-04-11)
AFLTABLES_TEAM_SLUGS: Dict[str, str] = {
    "Adelaide":        "adelaide",
    "Brisbane Lions":  "brisbanel",    # 'l' = Lions (Bears was 'brisbaneb')
    "Carlton":         "carlton",
    "Collingwood":     "collingwood",
    "Essendon":        "essendon",
    "Fremantle":       "fremantle",
    "Geelong":         "geelong",
    "Gold Coast":      "goldcoast",
    "GWS Giants":      "gws",
    "Hawthorn":        "hawthorn",
    "Melbourne":       "melbourne",
    "North Melbourne": "kangaroos",    # afltables uses historical 'kangaroos' slug
    "Port Adelaide":   "padelaide",
    "Richmond":        "richmond",
    "St Kilda":        "stkilda",
    "Sydney":          "swans",        # afltables uses 'swans'
    "West Coast":      "westcoast",
    "Western Bulldogs":"bullldogs",    # triple-l quirk in afltables URL
}

# Venue name aliases: Squiggle/current name → afltables historical name(s).
# afltables uses older venue names. We map current to all known historical aliases.
VENUE_ALIASES: Dict[str, List[str]] = {
    "MCG":                              ["M.C.G."],
    "Marvel Stadium":                   ["Docklands", "Etihad Stadium"],
    "Docklands":                        ["Docklands", "Etihad Stadium"],
    "Etihad Stadium":                   ["Docklands", "Etihad Stadium"],
    "SCG":                              ["S.C.G."],
    "Optus Stadium":                    ["Optus Stadium", "Perth Stadium", "Subiaco"],
    "GMHBA Stadium":                    ["GMHBA Stadium", "Kardinia Park"],
    "Kardinia Park":                    ["Kardinia Park", "GMHBA Stadium"],
    "People First Stadium":             ["Carrara", "People First Stadium"],
    "Carrara":                          ["Carrara", "People First Stadium"],
    "Giants Stadium":                   ["Giants Stadium", "GIANTS Stadium", "Sydney Showground"],
    "GIANTS Stadium":                   ["Giants Stadium", "GIANTS Stadium", "Sydney Showground"],
    "Gabba":                            ["Gabba", "The Gabba"],
    "Adelaide Oval":                    ["Adelaide Oval"],
    "TIO Stadium":                      ["TIO Stadium", "Marrara Oval"],
    "Traeger Park":                     ["Traeger Park", "Alice Springs"],
    "Cazaly's Stadium":                 ["Cazaly's Stadium"],
    "University of Tasmania Stadium":   ["York Park", "University of Tasmania Stadium"],
    "Blundstone Arena":                 ["Bellerive Oval", "Blundstone Arena"],
    "Manuka Oval":                      ["Manuka Oval"],
    "Mars Stadium":                     ["Mars Stadium", "Eureka Stadium"],
    "Engie Stadium":                    ["Stadium Australia", "Engie Stadium"],
    "ENGIE Stadium":                    ["Stadium Australia", "ENGIE Stadium"],
}


# ── Rate-limited HTTP session ─────────────────────────────────────────────────

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": (
        "AFL-Tipping-Agent/1.0 "
        "(github.com/mesmerize08/afl-tipping-agent; research use)"
    )
})
_REQUEST_LOCK      = threading.Lock()
_LAST_REQUEST_TIME = 0.0


def _polite_get(url: str) -> Optional[requests.Response]:
    """Fetch a URL with rate limiting and error handling. Returns None on failure."""
    global _LAST_REQUEST_TIME
    with _REQUEST_LOCK:
        elapsed = time.time() - _LAST_REQUEST_TIME
        if elapsed < MIN_REQUEST_GAP:
            time.sleep(MIN_REQUEST_GAP - elapsed)
        _LAST_REQUEST_TIME = time.time()

    try:
        resp = _SESSION.get(url, timeout=20)
        resp.raise_for_status()
        logger.debug("afltables fetch OK: %s", url)
        return resp
    except Exception as e:
        logger.warning("afltables fetch failed [%s]: %s", url, e)
        return None


# ── Disk cache ────────────────────────────────────────────────────────────────

def _cache_key(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def _cache_read(url: str):
    """Return cached data for url if present and not expired, else None."""
    path = os.path.join(CACHE_DIR, f"{_cache_key(url)}.json")
    try:
        with open(path) as f:
            entry = json.load(f)
        if time.time() - entry["ts"] < CACHE_TTL:
            return entry["data"]
    except Exception:
        pass
    return None


def _cache_write(url: str, data) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f"{_cache_key(url)}.json")
    try:
        with open(path, "w") as f:
            json.dump({"ts": time.time(), "data": data}, f)
    except Exception as e:
        logger.warning("afltables cache write failed: %s", e)


def _fetch_soup(url: str) -> Optional[BeautifulSoup]:
    """Return BeautifulSoup for url, using disk cache where possible."""
    cached_html = _cache_read(url)
    if cached_html is not None:
        return BeautifulSoup(cached_html, "html.parser")

    resp = _polite_get(url)
    if resp is None:
        return None

    _cache_write(url, resp.text)
    return BeautifulSoup(resp.text, "html.parser")


# ── Row parser for overall_vn.html / overall_wl.html ─────────────────────────

def _parse_stats_row(row) -> Optional[Dict]:
    """
    Parse a data row from afltables stats tables (overall_vn.html, overall_wl.html).

    The table has malformed HTML — some cells (draws, 100+A) may have replacement
    characters causing cells to merge. We use center-aligned <td> elements and find
    For/Agn by locating the dotted 'goals.behinds' cells as anchors.

    Returns dict with: p, w, l, d, score_for, score_agn, win_pct
    Returns None if row cannot be parsed.
    """
    # Use only center-aligned cells (the data cells, not the venue/team label)
    center_cells = [td.get_text(strip=True) for td in row.find_all("td", align="center")]
    if len(center_cells) < 5:
        return None

    try:
        p = int(center_cells[0])
        w = int(center_cells[1])
        if p == 0:
            return None

        # Find the first dotted cell (goals.behinds format e.g. '6013.5782')
        # Everything before it is P, W, D, L; everything from it onward is stats
        gf_idx = next(
            (i for i, v in enumerate(center_cells) if re.match(r'^\d+\.\d+', v)),
            None
        )
        if gf_idx is None or gf_idx + 3 >= len(center_cells):
            return None

        # For = center_cells[gf_idx + 1]  (integer after GF.BF)
        # GA.BA = center_cells[gf_idx + 2] (dotted: goals.behinds against)
        # Agn = center_cells[gf_idx + 3]   (integer after GA.BA)
        score_for = int(center_cells[gf_idx + 1])
        score_agn = int(center_cells[gf_idx + 3])
        l = p - w  # approximate — draws are rare in AFL

        win_pct = round(w / p * 100)
        return {
            "p":         p,
            "w":         w,
            "l":         l,
            "score_for": score_for,
            "score_agn": score_agn,
            "win_pct":   win_pct,
        }
    except (ValueError, IndexError, StopIteration, TypeError):
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def get_historical_home_away_split(team_name: str) -> Dict:
    """
    Return a team's all-time home and away win rates from afltables overall_wl.html.
    Sums all opponent rows from the Home and Away tables respectively.

    Returns:
        {
          "home": {"wins": 1234, "games": 2000, "pct": 62},
          "away": {"wins": 900,  "games": 2000, "pct": 45},
          "source": "afltables all-time"
        }
    Returns {} on failure.
    """
    slug = AFLTABLES_TEAM_SLUGS.get(team_name)
    if not slug:
        logger.warning("afltables: no slug for '%s'", team_name)
        return {}

    url  = f"{AFLTABLES_BASE}/{slug}/overall_wl.html"
    soup = _fetch_soup(url)
    if soup is None:
        return {}

    try:
        tables = soup.find_all("table")
        # Table layout: 0=All, 1=Home, 2=Away, 3=Finals
        if len(tables) < 3:
            logger.warning("afltables: expected ≥3 tables in overall_wl.html for %s", team_name)
            return {}

        def _sum_table(table) -> Dict:
            total_p = total_w = 0
            # Skip first 2 rows (table heading + column header)
            for row in table.find_all("tr")[2:]:
                stats = _parse_stats_row(row)
                if stats:
                    total_p += stats["p"]
                    total_w += stats["w"]
            pct = round(total_w / total_p * 100) if total_p else None
            return {"wins": total_w, "games": total_p, "pct": pct}

        return {
            "home":   _sum_table(tables[1]),
            "away":   _sum_table(tables[2]),
            "source": "afltables all-time",
        }
    except Exception as e:
        logger.warning("afltables: error parsing overall_wl.html for %s: %s", team_name, e)
        return {}


def get_historical_venue_record(team_name: str, venue: str) -> Dict:
    """
    Return a team's all-time record at a specific venue from afltables overall_vn.html.
    Matches venue names using an alias table (afltables uses historical names like
    'M.C.G.' and 'Docklands' rather than current names like 'MCG' and 'Marvel Stadium').

    Returns:
        {
          "wins": 228, "losses": 251, "games": 485,
          "win_pct": 47,
          "avg_score_for": 86.3, "avg_score_against": 86.0,
          "avg_margin": 0.3,
          "source": "afltables all-time"
        }
    Returns {} on failure or if venue not found.
    """
    # Avoid pointless lookups for special one-off venues
    try:
        from data_fetcher import SPECIAL_EVENT_VENUES
        if venue in SPECIAL_EVENT_VENUES:
            return {}
    except ImportError:
        pass

    slug = AFLTABLES_TEAM_SLUGS.get(team_name)
    if not slug:
        return {}

    url  = f"{AFLTABLES_BASE}/{slug}/overall_vn.html"
    soup = _fetch_soup(url)
    if soup is None:
        return {}

    try:
        tables = soup.find_all("table")
        if not tables:
            return {}

        # Build a set of afltables names to match against (from alias table + raw venue)
        target_names = set()
        target_names.add(venue.lower())
        for aliases in [VENUE_ALIASES.get(venue, []), VENUE_ALIASES.get(venue.title(), [])]:
            target_names.update(a.lower() for a in aliases)

        def _matches(row_venue: str) -> bool:
            rv = row_venue.lower()
            return (rv in target_names
                    or any(t in rv for t in target_names)
                    or any(rv in t for t in target_names))

        # Search Table 1 (all venues regardless of home/away)
        for row in tables[0].find_all("tr")[1:]:
            cells = row.find_all("td")
            if not cells:
                continue
            row_venue = cells[0].get_text(strip=True)
            if not _matches(row_venue):
                continue

            stats = _parse_stats_row(row)
            if stats is None:
                continue

            p, w = stats["p"], stats["w"]
            sf, sa = stats["score_for"], stats["score_agn"]
            return {
                "wins":              w,
                "losses":            stats["l"],
                "games":             p,
                "win_pct":           stats["win_pct"],
                "avg_score_for":     round(sf / p, 1),
                "avg_score_against": round(sa / p, 1),
                "avg_margin":        round((sf - sa) / p, 1),
                "source":            "afltables all-time",
            }

        logger.info("afltables: no venue match for '%s' (team: %s)", venue, team_name)
        return {}

    except Exception as e:
        logger.warning("afltables: error parsing overall_vn.html for %s at %s: %s",
                       team_name, venue, e)
        return {}


def get_historical_scoring_averages(team_name: str, num_years: int = 3) -> Dict:
    """
    Return scoring averages from the last `num_years` completed seasons using
    afltables season.html. Excludes the current partial season.

    season.html has one row per year with columns:
      Year | P | W | D | L | For (goals.behinds.total) | Agn | % | ... (finals)

    Returns:
        {
          "avg_score_for": 85.1,
          "avg_score_against": 79.9,
          "avg_margin": 5.2,
          "games": 69,
          "years": [2025, 2024, 2023]
        }
    Returns {} on failure.
    """
    slug = AFLTABLES_TEAM_SLUGS.get(team_name)
    if not slug:
        return {}

    url  = f"{AFLTABLES_BASE}/{slug}/season.html"
    soup = _fetch_soup(url)
    if soup is None:
        return {}

    try:
        tables = soup.find_all("table")
        if not tables:
            return {}

        current_year = __import__("datetime").datetime.now().year
        target_years = set(range(current_year - 1, current_year - 1 - num_years, -1))

        total_for = total_agn = total_games = 0
        found_years: List[int] = []

        for row in tables[0].find_all("tr"):
            cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
            if not cells:
                continue
            try:
                year = int(cells[0])
            except ValueError:
                continue
            if year not in target_years:
                continue

            try:
                games = int(cells[1])   # P (home & away games)
                # For total is the last part of 'goals.behinds.total' string in cells[5]
                # e.g. '259.245.1799' → 1799
                for_parts = cells[5].split(".")
                agn_parts  = cells[6].split(".")
                score_for = int(for_parts[-1])
                score_agn  = int(agn_parts[-1])
                if games == 0:
                    continue
                total_for   += score_for
                total_agn   += score_agn
                total_games += games
                found_years.append(year)
            except (ValueError, IndexError):
                continue

        if not found_years or total_games == 0:
            return {}

        return {
            "avg_score_for":     round(total_for  / total_games, 1),
            "avg_score_against": round(total_agn  / total_games, 1),
            "avg_margin":        round((total_for - total_agn) / total_games, 1),
            "games":             total_games,
            "years":             sorted(found_years, reverse=True),
        }
    except Exception as e:
        logger.warning("afltables: error parsing season.html for %s: %s", team_name, e)
        return {}
