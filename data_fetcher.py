import requests
import os
from datetime import datetime, timedelta

SQUIGGLE_BASE = "https://api.squiggle.com.au/"
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

def get_upcoming_fixtures():
    """Get this week's upcoming AFL games from Squiggle."""
    response = requests.get(f"{SQUIGGLE_BASE}?q=games;year=2026")
    games = response.json().get("games", [])
    
    # Filter to only upcoming games (next 7 days)
    upcoming = []
    today = datetime.now()
    week_ahead = today + timedelta(days=7)
    
    for game in games:
        if game.get("date"):
            try:
                game_date = datetime.strptime(game["date"][:10], "%Y-%m-%d")
                if today <= game_date <= week_ahead and game.get("complete") == 0:
                    upcoming.append(game)
            except:
                pass
    return upcoming

def get_ladder():
    """Get current AFL ladder standings."""
    response = requests.get(f"{SQUIGGLE_BASE}?q=standings;year=2026")
    return response.json().get("standings", [])

def get_team_form(team_name, num_games=5):
    """Get last N results for a team."""
    response = requests.get(f"{SQUIGGLE_BASE}?q=games;year=2026;team={requests.utils.quote(team_name)}")
    games = response.json().get("games", [])
    
    # Only completed games, most recent first
    completed = [g for g in games if g.get("complete") == 100]
    completed.sort(key=lambda x: x.get("date", ""), reverse=True)
    
    form = []
    for game in completed[:num_games]:
        is_home = game.get("hteam") == team_name
        team_score = game.get("hscore") if is_home else game.get("ascore")
        opp_score = game.get("ascore") if is_home else game.get("hscore")
        opponent = game.get("ateam") if is_home else game.get("hteam")
        
        result = "W" if team_score > opp_score else "L"
        form.append({
            "date": game.get("date", "")[:10],
            "opponent": opponent,
            "result": result,
            "score": f"{team_score}-{opp_score}",
            "venue": game.get("venue", "")
        })
    return form

def get_head_to_head(team1, team2, num_games=10):
    """Get recent H2H results between two teams."""
    response = requests.get(f"{SQUIGGLE_BASE}?q=games;team={requests.utils.quote(team1)}")
    games = response.json().get("games", [])
    
    h2h = []
    for game in games:
        if (game.get("hteam") == team2 or game.get("ateam") == team2) and game.get("complete") == 100:
            winner = game.get("hteam") if game.get("hscore", 0) > game.get("ascore", 0) else game.get("ateam")
            h2h.append({
                "date": game.get("date", "")[:10],
                "home_team": game.get("hteam"),
                "away_team": game.get("ateam"),
                "score": f"{game.get('hscore')}-{game.get('ascore')}",
                "winner": winner,
                "venue": game.get("venue", ""),
                "year": game.get("year")
            })
    
    h2h.sort(key=lambda x: x.get("date", ""), reverse=True)
    return h2h[:num_games]

def get_venue_record(team_name, venue, num_games=5):
    """Get a team's recent record at a specific venue."""
    response = requests.get(f"{SQUIGGLE_BASE}?q=games;team={requests.utils.quote(team_name)};venue={requests.utils.quote(venue)}")
    games = response.json().get("games", [])
    
    completed = [g for g in games if g.get("complete") == 100]
    completed.sort(key=lambda x: x.get("date", ""), reverse=True)
    
    venue_form = []
    for game in completed[:num_games]:
        is_home = game.get("hteam") == team_name
        team_score = game.get("hscore") if is_home else game.get("ascore")
        opp_score = game.get("ascore") if is_home else game.get("hscore")
        opponent = game.get("ateam") if is_home else game.get("hteam")
        result = "W" if team_score > opp_score else "L"
        venue_form.append({
            "date": game.get("date", "")[:10],
            "opponent": opponent,
            "result": result,
            "score": f"{team_score}-{opp_score}",
            "home_away": "Home" if is_home else "Away"
        })
    return venue_form

def get_betting_odds():
    """Get AFL betting odds from The Odds API."""
    if not ODDS_API_KEY:
        return {}
    
    url = "https://api.the-odds-api.com/v4/sports/aussierules_afl/odds/"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "au",
        "markets": "h2h",
        "oddsFormat": "decimal"
    }
    
    try:
        response = requests.get(url, params=params)
        games = response.json()
        
        odds_dict = {}
        for game in games:
            home = game.get("home_team")
            away = game.get("away_team")
            key = f"{home} vs {away}"
            
            bookmakers = game.get("bookmakers", [])
            if bookmakers:
                # Average across bookmakers for a fairer view
                home_odds_list = []
                away_odds_list = []
                
                for bookmaker in bookmakers:
                    for market in bookmaker.get("markets", []):
                        if market.get("key") == "h2h":
                            for outcome in market.get("outcomes", []):
                                if outcome["name"] == home:
                                    home_odds_list.append(outcome["price"])
                                elif outcome["name"] == away:
                                    away_odds_list.append(outcome["price"])
                
                if home_odds_list and away_odds_list:
                    avg_home = sum(home_odds_list) / len(home_odds_list)
                    avg_away = sum(away_odds_list) / len(away_odds_list)
                    
                    # Convert odds to implied probability
                    home_prob = round((1 / avg_home) * 100, 1)
                    away_prob = round((1 / avg_away) * 100, 1)
                    
                    odds_dict[key] = {
                        "home_team": home,
                        "away_team": away,
                        "home_odds": round(avg_home, 2),
                        "away_odds": round(avg_away, 2),
                        "home_implied_prob": home_prob,
                        "away_implied_prob": away_prob
                    }
        return odds_dict
    except Exception as e:
        print(f"Error fetching odds: {e}")
        return {}

def get_afl_news():
    """Scrape recent AFL news headlines from AFL.com.au RSS."""
    import feedparser
    try:
        feed = feedparser.parse("https://www.afl.com.au/rss/news")
        headlines = []
        for entry in feed.entries[:15]:
            headlines.append({
                "title": entry.get("title", ""),
                "summary": entry.get("summary", "")[:200],
                "published": entry.get("published", "")
            })
        return headlines
    except:
        return []

def compile_match_data(game, ladder, betting_odds):
    """Compile all data for a single match."""
    home_team = game.get("hteam")
    away_team = game.get("ateam")
    venue = game.get("venue", "Unknown Venue")
    game_date = game.get("date", "")[:10]
    round_num = game.get("round")
    
    # Get form for both teams
    home_form = get_team_form(home_team)
    away_form = get_team_form(away_team)
    
    # Get H2H
    h2h = get_head_to_head(home_team, away_team)
    
    # Get venue records
    home_venue_record = get_venue_record(home_team, venue)
    away_venue_record = get_venue_record(away_team, venue)
    
    # Get ladder positions
    home_ladder = next((t for t in ladder if t.get("name") == home_team), {})
    away_ladder = next((t for t in ladder if t.get("name") == away_team), {})
    
    # Get odds - try to match teams
    odds = {}
    for key, val in betting_odds.items():
        if home_team in key and away_team in key:
            odds = val
            break
        # Handle team name variations
        home_short = home_team.split()[-1]
        away_short = away_team.split()[-1]
        if home_short in key and away_short in key:
            odds = val
            break
    
    return {
        "game_id": game.get("id"),
        "round": round_num,
        "date": game_date,
        "venue": venue,
        "home_team": home_team,
        "away_team": away_team,
        "home_form": home_form,
        "away_form": away_form,
        "head_to_head": h2h,
        "home_venue_record": home_venue_record,
        "away_venue_record": away_venue_record,
        "home_ladder": home_ladder,
        "away_ladder": away_ladder,
        "betting_odds": odds
    }