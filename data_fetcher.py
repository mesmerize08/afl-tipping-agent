"""
data_fetcher.py  (UPGRADED — line/totals markets + Squiggle model cross-check)
===============================================================================
Changes in this version:
  - get_betting_odds() now fetches h2h, spreads (line), AND totals markets
  - get_squiggle_tips() fetches Squiggle's aggregated model predictions
  - compile_match_data() includes both of the above
"""

import requests
import os
from datetime import datetime, timedelta

SQUIGGLE_BASE = "https://api.squiggle.com.au/"
ODDS_API_KEY  = os.getenv("ODDS_API_KEY")


# ─── Fixtures ──────────────────────────────────────────────────────────────────

def get_upcoming_fixtures():
    """Get this week's upcoming AFL games from Squiggle."""
    response = requests.get(f"{SQUIGGLE_BASE}?q=games;year=2026")
    games    = response.json().get("games", [])

    upcoming   = []
    today      = datetime.now()
    week_ahead = today + timedelta(days=7)

    for game in games:
        if game.get("date"):
            try:
                game_date = datetime.strptime(game["date"][:10], "%Y-%m-%d")
                if today <= game_date <= week_ahead and game.get("complete") == 0:
                    upcoming.append(game)
            except Exception:
                pass
    return upcoming


# ─── Ladder ───────────────────────────────────────────────────────────────────

def get_ladder():
    """Get current AFL ladder standings."""
    response = requests.get(f"{SQUIGGLE_BASE}?q=standings;year=2026")
    return response.json().get("standings", [])


# ─── Team Form ────────────────────────────────────────────────────────────────

def get_team_form(team_name, num_games=5):
    """Get last N results for a team."""
    response  = requests.get(f"{SQUIGGLE_BASE}?q=games;year=2026;team={requests.utils.quote(team_name)}")
    games     = response.json().get("games", [])
    completed = [g for g in games if g.get("complete") == 100]
    completed.sort(key=lambda x: x.get("date", ""), reverse=True)

    form = []
    for game in completed[:num_games]:
        is_home    = game.get("hteam") == team_name
        team_score = game.get("hscore") if is_home else game.get("ascore")
        opp_score  = game.get("ascore") if is_home else game.get("hscore")
        opponent   = game.get("ateam")  if is_home else game.get("hteam")
        result     = "W" if team_score > opp_score else "L"
        form.append({
            "date":      game.get("date", "")[:10],
            "opponent":  opponent,
            "result":    result,
            "score":     f"{team_score}-{opp_score}",
            "venue":     game.get("venue", "")
        })
    return form


# ─── Head to Head ─────────────────────────────────────────────────────────────

def get_head_to_head(team1, team2, num_games=10):
    """Get recent H2H results between two teams."""
    response = requests.get(f"{SQUIGGLE_BASE}?q=games;team={requests.utils.quote(team1)}")
    games    = response.json().get("games", [])

    h2h = []
    for game in games:
        if (game.get("hteam") == team2 or game.get("ateam") == team2) and game.get("complete") == 100:
            winner = game.get("hteam") if game.get("hscore", 0) > game.get("ascore", 0) else game.get("ateam")
            h2h.append({
                "date":      game.get("date", "")[:10],
                "home_team": game.get("hteam"),
                "away_team": game.get("ateam"),
                "score":     f"{game.get('hscore')}-{game.get('ascore')}",
                "winner":    winner,
                "venue":     game.get("venue", ""),
                "year":      game.get("year")
            })

    h2h.sort(key=lambda x: x.get("date", ""), reverse=True)
    return h2h[:num_games]


# ─── Venue Record ─────────────────────────────────────────────────────────────

def get_venue_record(team_name, venue, num_games=5):
    """Get a team's recent record at a specific venue."""
    response  = requests.get(
        f"{SQUIGGLE_BASE}?q=games;team={requests.utils.quote(team_name)};venue={requests.utils.quote(venue)}"
    )
    games     = response.json().get("games", [])
    completed = [g for g in games if g.get("complete") == 100]
    completed.sort(key=lambda x: x.get("date", ""), reverse=True)

    venue_form = []
    for game in completed[:num_games]:
        is_home    = game.get("hteam") == team_name
        team_score = game.get("hscore") if is_home else game.get("ascore")
        opp_score  = game.get("ascore") if is_home else game.get("hscore")
        opponent   = game.get("ateam")  if is_home else game.get("hteam")
        result     = "W" if team_score > opp_score else "L"
        venue_form.append({
            "date":      game.get("date", "")[:10],
            "opponent":  opponent,
            "result":    result,
            "score":     f"{team_score}-{opp_score}",
            "home_away": "Home" if is_home else "Away"
        })
    return venue_form


# ─── Betting Odds (h2h + line/spread + totals) ────────────────────────────────

def get_betting_odds():
    """
    Get AFL betting odds from The Odds API.
    Fetches THREE markets:
      - h2h      : win/loss odds → implied win probability
      - spreads  : line/handicap → market's expected margin
      - totals   : over/under total score → expected game total
    """
    if not ODDS_API_KEY:
        return {}

    base_url = "https://api.the-odds-api.com/v4/sports/aussierules_afl/odds/"
    params_base = {
        "apiKey":      ODDS_API_KEY,
        "regions":     "au",
        "oddsFormat":  "decimal"
    }

    markets_to_fetch = ["h2h", "spreads", "totals"]
    all_market_data  = {}

    for market in markets_to_fetch:
        try:
            params  = {**params_base, "markets": market}
            response = requests.get(base_url, params=params, timeout=10)
            games   = response.json()

            if isinstance(games, list):
                for game in games:
                    home = game.get("home_team")
                    away = game.get("away_team")
                    key  = f"{home} vs {away}"

                    if key not in all_market_data:
                        all_market_data[key] = {
                            "home_team": home,
                            "away_team": away
                        }

                    bookmakers = game.get("bookmakers", [])
                    if not bookmakers:
                        continue

                    if market == "h2h":
                        home_odds_list = []
                        away_odds_list = []
                        for bm in bookmakers:
                            for m in bm.get("markets", []):
                                if m.get("key") == "h2h":
                                    for outcome in m.get("outcomes", []):
                                        if outcome["name"] == home:
                                            home_odds_list.append(outcome["price"])
                                        elif outcome["name"] == away:
                                            away_odds_list.append(outcome["price"])

                        if home_odds_list and away_odds_list:
                            avg_home = sum(home_odds_list) / len(home_odds_list)
                            avg_away = sum(away_odds_list) / len(away_odds_list)
                            all_market_data[key].update({
                                "home_odds":         round(avg_home, 2),
                                "away_odds":         round(avg_away, 2),
                                "home_implied_prob": round((1 / avg_home) * 100, 1),
                                "away_implied_prob": round((1 / avg_away) * 100, 1)
                            })

                    elif market == "spreads":
                        # Line market — the handicap applied to the favourite
                        # e.g. home team -12.5 means market expects home to win by ~12-13 pts
                        spreads = []
                        for bm in bookmakers:
                            for m in bm.get("markets", []):
                                if m.get("key") == "spreads":
                                    for outcome in m.get("outcomes", []):
                                        if outcome["name"] == home:
                                            spreads.append(outcome.get("point", 0))

                        if spreads:
                            avg_spread = sum(spreads) / len(spreads)
                            all_market_data[key].update({
                                "line_home_spread":  round(avg_spread, 1),
                                # Positive = home is underdog, Negative = home is favourite
                                "line_summary": (
                                    f"{home} giving {abs(avg_spread):.1f} pts"
                                    if avg_spread < 0
                                    else f"{away} giving {abs(avg_spread):.1f} pts"
                                )
                            })

                    elif market == "totals":
                        # Total points market — over/under line
                        totals = []
                        for bm in bookmakers:
                            for m in bm.get("markets", []):
                                if m.get("key") == "totals":
                                    for outcome in m.get("outcomes", []):
                                        if outcome.get("name") == "Over":
                                            totals.append(outcome.get("point", 0))

                        if totals:
                            avg_total = sum(totals) / len(totals)
                            all_market_data[key].update({
                                "total_line":    round(avg_total, 1),
                                "total_summary": f"Market expects total score around {avg_total:.0f} pts"
                            })

        except Exception as e:
            print(f"  Warning: Could not fetch {market} odds: {e}")

    return all_market_data


# ─── Squiggle Model Predictions (cross-check) ─────────────────────────────────

def get_squiggle_tips(round_number=None, year=2026):
    """
    Fetch Squiggle's aggregated model predictions for the upcoming round.

    Squiggle aggregates several statistical AFL prediction models
    (including their own) and provides a consensus win probability.
    This is a powerful cross-check — if the models AND the betting
    market AND the form all agree, confidence should be higher.

    Returns a dict keyed by "HomeTeam vs AwayTeam"
    """
    url = f"{SQUIGGLE_BASE}?q=tips;year={year}"
    if round_number:
        url += f";round={round_number}"

    try:
        response = requests.get(url, timeout=10)
        tips     = response.json().get("tips", [])

        squiggle_dict = {}
        for tip in tips:
            home      = tip.get("hteam")
            away      = tip.get("ateam")
            if not home or not away:
                continue

            key            = f"{home} vs {away}"
            predicted_team = tip.get("tip")         # Team Squiggle tips to win
            confidence     = tip.get("confidence")  # 0-100, Squiggle's confidence
            margin         = tip.get("margin")       # Expected winning margin

            # hconfidence is home team win probability (0-100)
            home_win_prob = tip.get("hconfidence")

            squiggle_dict[key] = {
                "home_team":       home,
                "away_team":       away,
                "squiggle_tip":    predicted_team,
                "squiggle_margin": margin,
                "home_win_prob":   home_win_prob,
                "confidence":      confidence,
                "source":          tip.get("sourcename", "Squiggle")
            }

        return squiggle_dict

    except Exception as e:
        print(f"  Warning: Could not fetch Squiggle tips: {e}")
        return {}


def format_squiggle_tips_for_prompt(squiggle_data, home_team, away_team):
    """
    Format Squiggle model data into a readable string for the AI prompt.
    """
    if not squiggle_data:
        return "Squiggle model predictions not available this week."

    # Try to find this match
    tip = None
    for key, val in squiggle_data.items():
        if val.get("home_team") == home_team and val.get("away_team") == away_team:
            tip = val
            break
        # Fuzzy match on last word of team name
        home_short = home_team.split()[-1]
        away_short = away_team.split()[-1]
        if home_short in key and away_short in key:
            tip = val
            break

    if not tip:
        return "Squiggle model prediction not found for this match."

    lines = [
        f"Squiggle statistical model tips: {tip.get('squiggle_tip', 'Unknown')} to win",
    ]

    if tip.get("squiggle_margin"):
        lines.append(f"  Expected margin: {tip['squiggle_margin']:.1f} pts")

    if tip.get("home_win_prob") is not None:
        away_prob = round(100 - tip["home_win_prob"], 1)
        lines.append(
            f"  Model win probabilities: {home_team}: {tip['home_win_prob']:.1f}% | "
            f"{away_team}: {away_prob}%"
        )

    lines.append(
        "  Note: Use this as a cross-check. If Squiggle model, betting market, "
        "and form data all agree, confidence should be higher."
    )

    return "\n".join(lines)


# ─── AFL News ─────────────────────────────────────────────────────────────────

def get_afl_news():
    """Scrape recent AFL news headlines from AFL.com.au RSS."""
    import feedparser
    try:
        feed      = feedparser.parse("https://www.afl.com.au/rss/news")
        headlines = []
        for entry in feed.entries[:15]:
            headlines.append({
                "title":     entry.get("title", ""),
                "summary":   entry.get("summary", "")[:200],
                "published": entry.get("published", "")
            })
        return headlines
    except Exception:
        return []


# ─── Compile All Match Data ───────────────────────────────────────────────────

def compile_match_data(game, ladder, betting_odds, squiggle_tips=None):
    """
    Compile all data for a single match including:
      - Form, H2H, venue records
      - Ladder positions
      - Betting odds (h2h + line + totals)
      - Squiggle model predictions
    """
    home_team  = game.get("hteam")
    away_team  = game.get("ateam")
    venue      = game.get("venue", "Unknown Venue")
    game_date  = game.get("date", "")[:10]
    round_num  = game.get("round")

    home_form        = get_team_form(home_team)
    away_form        = get_team_form(away_team)
    h2h              = get_head_to_head(home_team, away_team)
    home_venue_record = get_venue_record(home_team, venue)
    away_venue_record = get_venue_record(away_team, venue)

    home_ladder = next((t for t in ladder if t.get("name") == home_team), {})
    away_ladder = next((t for t in ladder if t.get("name") == away_team), {})

    # Match betting odds — handle slight team name variations
    odds = {}
    for key, val in betting_odds.items():
        if home_team in key and away_team in key:
            odds = val
            break
        home_short = home_team.split()[-1]
        away_short = away_team.split()[-1]
        if home_short in key and away_short in key:
            odds = val
            break

    # Format Squiggle model tip for this match
    squiggle_text = ""
    if squiggle_tips:
        squiggle_text = format_squiggle_tips_for_prompt(squiggle_tips, home_team, away_team)

    return {
        "game_id":           game.get("id"),
        "round":             round_num,
        "date":              game_date,
        "venue":             venue,
        "home_team":         home_team,
        "away_team":         away_team,
        "home_form":         home_form,
        "away_form":         away_form,
        "head_to_head":      h2h,
        "home_venue_record": home_venue_record,
        "away_venue_record": away_venue_record,
        "home_ladder":       home_ladder,
        "away_ladder":       away_ladder,
        "betting_odds":      odds,
        "squiggle_model":    squiggle_text
    }
