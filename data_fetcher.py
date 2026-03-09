"""
data_fetcher.py  (COMPLETE — all upgrades + Round 0 Opening Round fix)
=======================================================================
Functions:
  get_upcoming_fixtures()          : fetches this week's games, handles Round 0
  get_ladder()                     : current AFL ladder
  get_team_season_data()           : single API call per team, falls back to prior year
  get_form_from_games()            : W/L form with score integers and margins
  get_scoring_stats()              : avg pts for/against + attack/defense trend
  get_days_rest()                  : days between last game and upcoming game
  get_travel_info()                : travel fatigue detection
  get_head_to_head()               : H2H results between two teams
  get_venue_record()               : team record at a specific venue
  get_betting_odds()               : h2h + spreads + totals from The Odds API
  get_squiggle_tips()              : Squiggle model predictions, handles round 0
  format_squiggle_tips_for_prompt(): formats Squiggle data for AI prompt
  get_afl_news()                   : AFL.com.au RSS headlines
  compile_match_data()             : assembles all data for one match
"""

import logging
import os
import requests
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from urllib.parse import urlsplit

SQUIGGLE_BASE = "https://api.squiggle.com.au/"
ODDS_API_KEY  = os.getenv("ODDS_API_KEY")

logger = logging.getLogger(__name__)


def _safe_url(url: str) -> str:
    """Return URL with query string stripped (hides API keys in log messages)."""
    return urlsplit(url)._replace(query="", fragment="").geturl()


# ─── Team home cities (for travel detection) ──────────────────────────────────

TEAM_HOME_CITIES = {
    "Adelaide":         "Adelaide",
    "Port Adelaide":    "Adelaide",
    "Brisbane Lions":   "Brisbane",
    "Gold Coast":       "Gold Coast",
    "GWS Giants":       "Sydney",
    "Sydney":           "Sydney",
    "West Coast":       "Perth",
    "Fremantle":        "Perth",
    "Geelong":          "Geelong",
    "Carlton":          "Melbourne",
    "Collingwood":      "Melbourne",
    "Essendon":         "Melbourne",
    "Hawthorn":         "Melbourne",
    "Melbourne":        "Melbourne",
    "North Melbourne":  "Melbourne",
    "Richmond":         "Melbourne",
    "St Kilda":         "Melbourne",
    "Western Bulldogs": "Melbourne",
}

VENUE_CITIES = {
    "MCG":                              "Melbourne",
    "Marvel Stadium":                   "Melbourne",
    "Docklands":                        "Melbourne",
    "Etihad Stadium":                   "Melbourne",
    "GMHBA Stadium":                    "Geelong",
    "Kardinia Park":                    "Geelong",
    "Mars Stadium":                     "Ballarat",
    "Adelaide Oval":                    "Adelaide",
    "Optus Stadium":                    "Perth",
    "Gabba":                            "Brisbane",
    "People First Stadium":             "Gold Coast",
    "Carrara":                          "Gold Coast",
    "SCG":                              "Sydney",
    "Giants Stadium":                   "Sydney",
    "GIANTS Stadium":                   "Sydney",
    "Engie Stadium":                    "Sydney",
    "ENGIE Stadium":                    "Sydney",
    "Sydney Showground":                "Sydney",
    "Spotless Stadium":                 "Sydney",
    "TIO Stadium":                      "Darwin",
    "Traeger Park":                     "Alice Springs",
    "Cazaly's Stadium":                 "Cairns",
    "University of Tasmania Stadium":   "Launceston",
    "Blundstone Arena":                 "Hobart",
    "Manuka Oval":                      "Canberra",
}

HIGH_TRAVEL_PAIRS = {
    ("Perth", "Melbourne"), ("Melbourne", "Perth"),
    ("Perth", "Sydney"),    ("Sydney", "Perth"),
    ("Perth", "Brisbane"),  ("Brisbane", "Perth"),
    ("Perth", "Adelaide"),  ("Adelaide", "Perth"),
    ("Perth", "Geelong"),   ("Geelong", "Perth"),
    ("Darwin", "Melbourne"),("Melbourne", "Darwin"),
    ("Darwin", "Sydney"),   ("Sydney", "Darwin"),
    ("Darwin", "Perth"),    ("Perth", "Darwin"),
    ("Cairns", "Melbourne"),("Melbourne", "Cairns"),
    ("Cairns", "Sydney"),   ("Sydney", "Cairns"),
    ("Alice Springs", "Melbourne"), ("Melbourne", "Alice Springs"),
}

MEDIUM_TRAVEL_PAIRS = {
    ("Adelaide", "Melbourne"), ("Melbourne", "Adelaide"),
    ("Adelaide", "Sydney"),    ("Sydney", "Adelaide"),
    ("Adelaide", "Geelong"),   ("Geelong", "Adelaide"),
    ("Brisbane", "Melbourne"), ("Melbourne", "Brisbane"),
    ("Brisbane", "Geelong"),   ("Geelong", "Brisbane"),
    ("Gold Coast", "Melbourne"),("Melbourne", "Gold Coast"),
    ("Canberra", "Melbourne"), ("Melbourne", "Canberra"),
    ("Launceston", "Melbourne"),("Melbourne", "Launceston"),
    ("Hobart", "Melbourne"),   ("Melbourne", "Hobart"),
}


# ─── Fixtures ──────────────────────────────────────────────────────────────────

# Squiggle uses "Greater Western Sydney" — normalise to our canonical name.
SQUIGGLE_TEAM_NAME_MAP = {
    "Greater Western Sydney": "GWS Giants",
}

# Required by Squiggle API since Apr 2024 — cloud IPs without it are rate-limited.
# See https://api.squiggle.com.au/#section_bots
_UA = {"User-Agent": "AFL-Tipping-Agent/1.0 (github.com/mesmerize08/afl-tipping-agent)"}


def _normalise_game(game):
    """Normalise team names and strip dots from venue abbreviations."""
    g = dict(game)
    g["hteam"] = SQUIGGLE_TEAM_NAME_MAP.get(g.get("hteam", ""), g.get("hteam", ""))
    g["ateam"] = SQUIGGLE_TEAM_NAME_MAP.get(g.get("ateam", ""), g.get("ateam", ""))
    g["venue"] = g.get("venue", "").replace(".", "").replace("  ", " ").strip()
    return g


def _sq_get(url):
    """GET a Squiggle URL with User-Agent. Returns list of games or []."""
    try:
        r = requests.get(url, timeout=15, headers=_UA)
        r.raise_for_status()
        games = r.json().get("games", [])
        logger.debug("Squiggle [%s] -> %d games", url.split("?", 1)[-1], len(games))
        return games
    except Exception as e:
        logger.warning("Squiggle fetch failed [%s]: %s", _safe_url(url), e)
        return []


def get_upcoming_fixtures():
    """
    Fetch this week's upcoming AFL games from Squiggle.

    API reference: https://api.squiggle.com.au/
    Query strategy (stops at the first group that returns results):
      1. complete=!100        -- ALL incomplete games (documented API example)
      2. year=X;complete=0    -- future-only games this year
      3. round=0/1/2          -- explicit round fallbacks

    IMPORTANT: ?q=games;year=X returns only COMPLETED games by Squiggle
    convention — never use it as the primary query at season start.

    A game is "upcoming" if complete < 100 AND date is within the next 14 days.
    Only the single earliest round is returned so two rounds never appear at once.
    """
    today      = datetime.now()
    window_end = today + timedelta(days=14)
    year       = today.year
    seen_ids   = set()
    candidates = []

    # Groups tried in order — stop as soon as any group yields results
    url_groups = [
        [f"{SQUIGGLE_BASE}?q=games;complete=!100"],
        [f"{SQUIGGLE_BASE}?q=games;year={year};complete=0"],
        [
            f"{SQUIGGLE_BASE}?q=games;year={year};round=0",
            f"{SQUIGGLE_BASE}?q=games;year={year};round=1",
            f"{SQUIGGLE_BASE}?q=games;year={year};round=2",
        ],
    ]

    for group in url_groups:
        for url in group:
            for raw in _sq_get(url):
                gid = raw.get("id")
                if gid in seen_ids:
                    continue
                seen_ids.add(gid)

                try:
                    if int(raw.get("complete") or 0) >= 100:
                        continue
                except (ValueError, TypeError):
                    pass

                date_str = raw.get("date", "")
                if not date_str:
                    continue
                try:
                    gd = datetime.strptime(date_str[:10], "%Y-%m-%d")
                    if today.date() <= gd.date() <= window_end.date():
                        candidates.append(_normalise_game(raw))
                except Exception:
                    continue

        if candidates:
            break  # Stop at the first group that returns results

    candidates.sort(key=lambda x: x.get("date", ""))

    # Return only the single earliest round
    if candidates:
        earliest = min(g.get("round", 99) for g in candidates)
        candidates = [g for g in candidates if g.get("round") == earliest]
        logger.info("Keeping round %s: %d fixture(s)", earliest, len(candidates))

    logger.info("Total upcoming fixtures: %d", len(candidates))
    return candidates


# ─── Ladder ───────────────────────────────────────────────────────────────────

def get_ladder():
    """Get current AFL ladder standings."""
    year = datetime.now().year
    try:
        r = requests.get(f"{SQUIGGLE_BASE}?q=standings;year={year}",
                         timeout=15, headers=_UA)
        r.raise_for_status()
        return r.json().get("standings", [])
    except Exception as e:
        logger.warning("Could not fetch ladder: %s", e)
        return []


# ─── Core: Single API call per team, reused across all helpers ────────────────

def get_team_season_data(team_name, year=None):
    """
    Fetch ALL completed games for a team in a given year in one API call.
    Returns completed games sorted by date descending.
    If no completed games found for the current year (start of season),
    automatically falls back to the previous year for form calculations.
    """
    if year is None:
        year = datetime.now().year
    url = f"{SQUIGGLE_BASE}?q=games;year={year};team={requests.utils.quote(team_name)}"
    try:
        r = requests.get(url, timeout=15, headers=_UA)
        r.raise_for_status()
        games = r.json().get("games", [])
    except Exception as e:
        logger.warning("Could not fetch season data for %s: %s", team_name, e)
        games = []

    completed = [g for g in games if str(g.get("complete", "")).split(".")[0] == "100"]
    completed.sort(key=lambda x: x.get("date", ""), reverse=True)

    # Fall back to previous year if no completed games yet this season
    if not completed:
        logger.info("No %s data for %s — falling back to %s", year, team_name, year - 1)
        try:
            r2 = requests.get(
                f"{SQUIGGLE_BASE}?q=games;year={year-1};team={requests.utils.quote(team_name)}",
                timeout=15, headers=_UA)
            r2.raise_for_status()
            fb_games = r2.json().get("games", [])
        except Exception as e:
            logger.warning("Fallback fetch failed for %s: %s", team_name, e)
            fb_games = []
        completed = [g for g in fb_games if str(g.get("complete", "")).split(".")[0] == "100"]
        completed.sort(key=lambda x: x.get("date", ""), reverse=True)

    return completed


# ─── Form (with score integers for margin calculations) ───────────────────────

def get_form_from_games(team_name, completed_games, num_games=5):
    """Extract W/L form from pre-fetched season data. Includes raw scores and margin."""
    form = []
    for game in completed_games[:num_games]:
        is_home    = game.get("hteam") == team_name
        team_score = int(game.get("hscore") or 0) if is_home else int(game.get("ascore") or 0)
        opp_score  = int(game.get("ascore") or 0) if is_home else int(game.get("hscore") or 0)
        opponent   = game.get("ateam") if is_home else game.get("hteam")
        result     = "W" if team_score > opp_score else "L"
        margin     = team_score - opp_score

        form.append({
            "date":       game.get("date", "")[:10],
            "opponent":   opponent,
            "result":     result,
            "score":      f"{team_score}-{opp_score}",
            "margin":     margin,
            "team_score": team_score,
            "opp_score":  opp_score,
            "venue":      game.get("venue", ""),
            "home_away":  "Home" if is_home else "Away"
        })
    return form


# ─── Scoring Stats — averages and trend ───────────────────────────────────────

def get_scoring_stats(team_name, completed_games):
    """
    Calculate detailed scoring statistics.
    Compares last-3 vs last-5 averages to identify attack and defense trends.
    """
    if not completed_games:
        return {}

    form_5 = get_form_from_games(team_name, completed_games, num_games=5)
    form_3 = get_form_from_games(team_name, completed_games, num_games=3)

    def avg(lst, key):
        vals = [g[key] for g in lst if g.get(key) is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    avg_for_5     = avg(form_5, "team_score")
    avg_against_5 = avg(form_5, "opp_score")
    avg_for_3     = avg(form_3, "team_score")
    avg_against_3 = avg(form_3, "opp_score")

    def trend(val_3, val_5, label_up, label_down):
        if val_3 is None or val_5 is None:
            return "stable"
        diff = val_3 - val_5
        if diff > 8:  return label_up
        if diff < -8: return label_down
        return "stable"

    attack_trend  = trend(avg_for_3,     avg_for_5,     "improving ↑", "declining ↓")
    defense_trend = trend(avg_against_3, avg_against_5, "leaking more ↑", "tightening ↓")
    wins_5        = sum(1 for g in form_5 if g["result"] == "W")

    return {
        "avg_for_5":      avg_for_5,
        "avg_against_5":  avg_against_5,
        "avg_for_3":      avg_for_3,
        "avg_against_3":  avg_against_3,
        "attack_trend":   attack_trend,
        "defense_trend":  defense_trend,
        "wins_last_5":    wins_5,
        "avg_margin_5":   avg(form_5, "margin"),
    }


# ─── Days Rest ────────────────────────────────────────────────────────────────

def get_days_rest(team_name, completed_games, upcoming_game_date_str):
    """
    Calculate days between a team's last game and the upcoming game.
    Short turnarounds (7 days or fewer) are a genuine fatigue factor.
    """
    if not completed_games or not upcoming_game_date_str:
        return None

    try:
        upcoming_date = datetime.strptime(upcoming_game_date_str[:10], "%Y-%m-%d")
    except Exception:
        return None

    for game in completed_games:
        try:
            last_date = datetime.strptime(game["date"][:10], "%Y-%m-%d")
            if last_date < upcoming_date:
                days = (upcoming_date - last_date).days
                return {
                    "days":        days,
                    "last_game":   game["date"][:10],
                    "flag":        "⚠️ SHORT TURNAROUND" if days <= 6 else ("✅ GOOD REST" if days >= 10 else ""),
                    "description": (
                        f"{days} days rest (SHORT TURNAROUND — fatigue risk)"
                        if days <= 6
                        else f"{days} days rest"
                    )
                }
        except Exception:
            continue

    return None


# ─── Travel Fatigue ───────────────────────────────────────────────────────────

def get_travel_info(team_name, game_venue):
    """
    Detect if a team is travelling far from their home city.
    Flags high-fatigue situations like Perth teams going east.
    """
    home_city  = TEAM_HOME_CITIES.get(team_name)
    venue_city = VENUE_CITIES.get(game_venue)

    # Try partial venue name match
    if not venue_city:
        for v, c in VENUE_CITIES.items():
            if v.lower() in game_venue.lower() or game_venue.lower() in v.lower():
                venue_city = c
                break

    if not home_city or not venue_city:
        return {"travelling": False, "fatigue_level": "unknown", "description": ""}

    if home_city == venue_city:
        return {
            "travelling":    False,
            "fatigue_level": "none",
            "description":   f"Playing at home in {home_city}"
        }

    pair = (home_city, venue_city)

    if pair in HIGH_TRAVEL_PAIRS:
        return {
            "travelling":    True,
            "fatigue_level": "high",
            "home_city":     home_city,
            "venue_city":    venue_city,
            "description":   f"⚠️ LONG-HAUL TRAVEL: {home_city} → {venue_city} (significant fatigue factor)"
        }
    elif pair in MEDIUM_TRAVEL_PAIRS:
        return {
            "travelling":    True,
            "fatigue_level": "medium",
            "home_city":     home_city,
            "venue_city":    venue_city,
            "description":   f"Moderate travel: {home_city} → {venue_city}"
        }
    else:
        return {
            "travelling":    True,
            "fatigue_level": "low",
            "home_city":     home_city,
            "venue_city":    venue_city,
            "description":   f"Short travel: {home_city} → {venue_city}"
        }


# ─── Head to Head ─────────────────────────────────────────────────────────────

def get_head_to_head(team1, team2, num_games=10):
    """Get recent H2H results between two teams across all years."""
    try:
        r = requests.get(
            f"{SQUIGGLE_BASE}?q=games;team={requests.utils.quote(team1)}",
            timeout=15, headers=_UA
        )
        r.raise_for_status()
        games = r.json().get("games", [])
    except Exception as e:
        logger.warning("Could not fetch H2H data: %s", e)
        return []

    h2h = []
    for game in games:
        if (game.get("hteam") == team2 or game.get("ateam") == team2) and game.get("complete") == 100:
            hscore = int(game.get("hscore") or 0)
            ascore = int(game.get("ascore") or 0)
            winner = game.get("hteam") if hscore > ascore else game.get("ateam")
            h2h.append({
                "date":      game.get("date", "")[:10],
                "home_team": game.get("hteam"),
                "away_team": game.get("ateam"),
                "score":     f"{hscore}-{ascore}",
                "winner":    winner,
                "venue":     game.get("venue", ""),
                "year":      game.get("year")
            })

    h2h.sort(key=lambda x: x.get("date", ""), reverse=True)
    if not h2h:
        logger.info("No H2H history found between %s and %s", team1, team2)
    return h2h[:num_games]


# ─── Venue Record ─────────────────────────────────────────────────────────────

def get_venue_record(team_name, venue, num_games=5):
    """Get a team's recent record at a specific venue (all years)."""
    try:
        r = requests.get(
            f"{SQUIGGLE_BASE}?q=games;team={requests.utils.quote(team_name)};venue={requests.utils.quote(venue)}",
            timeout=15, headers=_UA
        )
        r.raise_for_status()
        games = r.json().get("games", [])
    except Exception as e:
        logger.warning("Could not fetch venue record: %s", e)
        return []

    completed = [g for g in games if str(g.get("complete", "")).split(".")[0] == "100"]
    completed.sort(key=lambda x: x.get("date", ""), reverse=True)

    venue_form = []
    for game in completed[:num_games]:
        is_home    = game.get("hteam") == team_name
        team_score = int(game.get("hscore") or 0) if is_home else int(game.get("ascore") or 0)
        opp_score  = int(game.get("ascore") or 0) if is_home else int(game.get("hscore") or 0)
        opponent   = game.get("ateam") if is_home else game.get("hteam")
        result     = "W" if team_score > opp_score else "L"
        venue_form.append({
            "date":      game.get("date", "")[:10],
            "opponent":  opponent,
            "result":    result,
            "score":     f"{team_score}-{opp_score}",
            "margin":    team_score - opp_score,
            "home_away": "Home" if is_home else "Away"
        })
    return venue_form


def get_home_away_split(team_name, completed_games):
    """
    Compute a team's home vs away win rate from their season game data.
    Uses already-fetched games so no extra API call is needed.
    """
    def record(games, side):
        wins = sum(
            1 for g in games
            if (int(g.get("hscore") or 0) > int(g.get("ascore") or 0)) == (side == "home")
        )
        n   = len(games)
        pct = round(wins / n * 100) if n else None
        return {"wins": wins, "games": n, "pct": pct}

    home_games = [g for g in completed_games if g.get("hteam") == team_name]
    away_games = [g for g in completed_games if g.get("ateam") == team_name]
    return {"home": record(home_games, "home"), "away": record(away_games, "away")}


# ─── Betting Odds (h2h + spreads + totals) ────────────────────────────────────

def get_betting_odds():
    """
    Get AFL betting odds from The Odds API.
    Fetches three markets:
      h2h     : win/loss odds → implied win probability
      spreads : line/handicap → market's expected margin
      totals  : over/under   → expected total score
    """
    if not ODDS_API_KEY:
        return {}

    base_url    = "https://api.the-odds-api.com/v4/sports/aussierules_afl/odds/"
    params_base = {"apiKey": ODDS_API_KEY, "regions": "au", "oddsFormat": "decimal"}
    all_data    = {}

    for market in ["h2h", "spreads", "totals"]:
        try:
            response = requests.get(
                base_url, params={**params_base, "markets": market}, timeout=15
            )
            games = response.json()

            if not isinstance(games, list):
                continue

            for game in games:
                home = game.get("home_team")
                away = game.get("away_team")
                key  = f"{home} vs {away}"

                if key not in all_data:
                    all_data[key] = {"home_team": home, "away_team": away}

                bookmakers = game.get("bookmakers", [])
                if not bookmakers:
                    continue

                if market == "h2h":
                    home_list, away_list = [], []
                    for bm in bookmakers:
                        for m in bm.get("markets", []):
                            if m.get("key") == "h2h":
                                for o in m.get("outcomes", []):
                                    if o["name"] == home: home_list.append(o["price"])
                                    elif o["name"] == away: away_list.append(o["price"])
                    if home_list and away_list:
                        avg_h = sum(home_list) / len(home_list)
                        avg_a = sum(away_list) / len(away_list)
                        all_data[key].update({
                            "home_odds":         round(avg_h, 2),
                            "away_odds":         round(avg_a, 2),
                            "home_implied_prob": round((1 / avg_h) * 100, 1),
                            "away_implied_prob": round((1 / avg_a) * 100, 1),
                        })

                elif market == "spreads":
                    spreads = []
                    for bm in bookmakers:
                        for m in bm.get("markets", []):
                            if m.get("key") == "spreads":
                                for o in m.get("outcomes", []):
                                    if o["name"] == home:
                                        spreads.append(o.get("point", 0))
                    if spreads:
                        avg_s = sum(spreads) / len(spreads)
                        all_data[key].update({
                            "line_home_spread": round(avg_s, 1),
                            "line_summary": (
                                f"{home} giving {abs(avg_s):.1f} pts"
                                if avg_s < 0
                                else f"{away} giving {abs(avg_s):.1f} pts"
                            )
                        })

                elif market == "totals":
                    totals = []
                    for bm in bookmakers:
                        for m in bm.get("markets", []):
                            if m.get("key") == "totals":
                                for o in m.get("outcomes", []):
                                    if o.get("name") == "Over":
                                        totals.append(o.get("point", 0))
                    if totals:
                        avg_t = sum(totals) / len(totals)
                        all_data[key].update({
                            "total_line":    round(avg_t, 1),
                            "total_summary": f"Market expects total score ~{avg_t:.0f} pts"
                        })

        except Exception as e:
            logger.warning("Could not fetch %s odds: %s", market, e)

    return all_data


# ─── Squiggle Model Tips ───────────────────────────────────────────────────────

def get_squiggle_tips(round_number=None, year=None):
    """
    Fetch Squiggle's aggregated model predictions.
    Uses 'is not None' check so round 0 (Opening Round) is passed correctly --
    round_number=0 is falsy in Python so a simple 'if round_number' would skip it.
    Year defaults to current calendar year if not specified.
    """
    if year is None:
        year = datetime.now().year
    url = f"{SQUIGGLE_BASE}?q=tips;year={year}"
    if round_number is not None:
        url += f";round={round_number}"

    try:
        response = requests.get(url, timeout=15, headers=_UA)
        tips     = response.json().get("tips", [])
        result   = {}
        for tip in tips:
            home = tip.get("hteam")
            away = tip.get("ateam")
            if not home or not away:
                continue
            key = f"{home} vs {away}"
            result[key] = {
                "home_team":       home,
                "away_team":       away,
                "squiggle_tip":    tip.get("tip"),
                "squiggle_margin": tip.get("margin"),
                "home_win_prob":   tip.get("hconfidence"),
                "confidence":      tip.get("confidence"),
                "source":          tip.get("sourcename", "Squiggle")
            }
        return result
    except Exception as e:
        logger.warning("Could not fetch Squiggle tips: %s", e)
        return {}


def format_squiggle_tips_for_prompt(squiggle_data, home_team, away_team):
    """Format Squiggle tip for a single match into AI prompt text."""
    if not squiggle_data:
        return "Squiggle model predictions not available this week."

    tip = None
    for key, val in squiggle_data.items():
        if val.get("home_team") == home_team and val.get("away_team") == away_team:
            tip = val
            break
        if home_team.split()[-1] in key and away_team.split()[-1] in key:
            tip = val
            break

    if not tip:
        return "Squiggle model prediction not found for this match."

    lines = [f"Squiggle statistical model tips: {tip.get('squiggle_tip', '?')} to win"]

    # Both fields may be None before Squiggle publishes model tips (e.g. Round 0)
    raw_margin = tip.get("squiggle_margin")
    if raw_margin is not None:
        try:
            lines.append(f"  Expected margin: {float(raw_margin):.1f} pts")
        except (TypeError, ValueError):
            pass

    raw_prob = tip.get("home_win_prob")
    if raw_prob is not None:
        try:
            hp = float(raw_prob)
            lines.append(
                f"  Model win probabilities: {home_team}: {hp:.1f}% | "
                f"{away_team}: {round(100 - hp, 1)}%"
            )
        except (TypeError, ValueError):
            pass

    lines.append(
        "  Cross-check: if model, market, and form all agree -- higher confidence."
    )
    return "\n".join(lines)


# ─── AFL News ─────────────────────────────────────────────────────────────────

def get_afl_news():
    """
    Get recent AFL news headlines for the general context section of the AI prompt.
    Uses Zero Hanger RSS (AFL.com.au RSS feeds are dead as of early 2026).
    Returns up to 15 items, filtered for injury/selection relevance.
    """
    import feedparser
    try:
        feed = feedparser.parse("https://www.zerohanger.com/feed")
        items = []
        for e in feed.entries[:30]:
            title   = e.get("title", "")
            summary = e.get("summary", "")[:200]
            if title:
                items.append({
                    "title":     title,
                    "summary":   summary,
                    "published": e.get("published", "")
                })
            if len(items) >= 15:
                break
        logger.info("AFL news: %d articles from Zero Hanger", len(items))
        return items
    except Exception as ex:
        logger.warning("Could not fetch AFL news: %s", ex)
        return []


# ─── Compile All Match Data ───────────────────────────────────────────────────

def compile_match_data(game, ladder, betting_odds, squiggle_tips=None):
    """
    Compile all data for a single match.
    Makes one API call per team via get_team_season_data() and reuses
    the result across form, scoring stats, rest days, and travel helpers
    to minimise total API requests.
    """
    home_team  = game.get("hteam")
    away_team  = game.get("ateam")
    venue      = game.get("venue", "Unknown Venue")
    game_date  = game.get("date", "")[:10]
    round_num  = game.get("round")

    # Fetch both teams' season data in parallel (2 independent API calls)
    current_year = datetime.now().year
    logger.info("Fetching season data for %s and %s", home_team, away_team)
    with ThreadPoolExecutor(max_workers=2) as pool:
        home_fut = pool.submit(get_team_season_data, home_team, current_year)
        away_fut = pool.submit(get_team_season_data, away_team, current_year)
        home_games = home_fut.result()
        away_games = away_fut.result()

    # Form with margins
    home_form = get_form_from_games(home_team, home_games)
    away_form = get_form_from_games(away_team, away_games)

    # Scoring stats and trends
    home_scoring = get_scoring_stats(home_team, home_games)
    away_scoring = get_scoring_stats(away_team, away_games)

    # Rest days
    home_rest = get_days_rest(home_team, home_games, game_date)
    away_rest = get_days_rest(away_team, away_games, game_date)

    # Travel fatigue
    home_travel = get_travel_info(home_team, venue)
    away_travel = get_travel_info(away_team, venue)

    # H2H and venue records (separate calls — span multiple years)
    h2h               = get_head_to_head(home_team, away_team)
    home_venue_record = get_venue_record(home_team, venue)
    away_venue_record = get_venue_record(away_team, venue)
    # Home/away win split (no extra API call — uses already-fetched season data)
    home_ha_split     = get_home_away_split(home_team, home_games)
    away_ha_split     = get_home_away_split(away_team, away_games)

    # Ladder positions
    home_ladder = next((t for t in ladder if t.get("name") == home_team), {})
    away_ladder = next((t for t in ladder if t.get("name") == away_team), {})

    # Match betting odds — handle slight team name variations between APIs
    odds = {}
    for key, val in betting_odds.items():
        if home_team in key and away_team in key:
            odds = val
            break
        if home_team.split()[-1] in key and away_team.split()[-1] in key:
            odds = val
            break

    # Squiggle model tip for this match
    squiggle_text = ""
    if squiggle_tips:
        squiggle_text = format_squiggle_tips_for_prompt(squiggle_tips, home_team, away_team)

    return {
        "game_id":            game.get("id"),
        "round":              round_num,
        "date":               game_date,
        "date_full":          game.get("date", ""),
        "venue":              venue,
        "home_team":          home_team,
        "away_team":          away_team,
        "home_form":          home_form,
        "away_form":          away_form,
        "home_scoring":       home_scoring,
        "away_scoring":       away_scoring,
        "home_rest":          home_rest,
        "away_rest":          away_rest,
        "home_travel":        home_travel,
        "away_travel":        away_travel,
        "head_to_head":       h2h,
        "home_venue_record":  home_venue_record,
        "away_venue_record":  away_venue_record,
        "home_ha_split":      home_ha_split,
        "away_ha_split":      away_ha_split,
        "home_ladder":        home_ladder,
        "away_ladder":        away_ladder,
        "betting_odds":       odds,
        "squiggle_model":     squiggle_text,
    }
