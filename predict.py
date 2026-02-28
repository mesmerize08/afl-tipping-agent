"""
predict.py  (UPGRADED — uses scoring stats, travel, rest days, scoring trends)
===============================================================================
All new data fields from data_fetcher.py are now injected into the AI prompt.
"""

import google.generativeai as genai
import os

from team_news import format_team_news_for_ai
from tracker   import format_history_for_ai, save_predictions
from weather   import format_weather_for_ai
from data_fetcher import get_squiggle_tips, format_squiggle_tips_for_prompt

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


# ─── Formatting helpers ────────────────────────────────────────────────────────

def format_form(form_list):
    """Format form with margin data included."""
    if not form_list:
        return "No recent data"
    parts = []
    for g in form_list:
        margin_str = f"+{g['margin']}" if g.get('margin', 0) > 0 else str(g.get('margin', 0))
        parts.append(f"{g['result']} vs {g['opponent']} {g['score']} ({margin_str} pts) on {g['date']}")
    wins = sum(1 for g in form_list if g["result"] == "W")
    return f"{wins}/{len(form_list)} wins. " + " | ".join(parts)


def format_scoring_stats(scoring, team_name):
    """Format scoring stats and trends into readable prompt text."""
    if not scoring:
        return "Scoring data unavailable"

    lines = []
    af5 = scoring.get("avg_for_5")
    aa5 = scoring.get("avg_against_5")
    af3 = scoring.get("avg_for_3")
    aa3 = scoring.get("avg_against_3")
    atk = scoring.get("attack_trend", "stable")
    dft = scoring.get("defense_trend", "stable")
    am5 = scoring.get("avg_margin_5")

    if af5 is not None:
        lines.append(f"  Avg score (last 5): {af5} pts for, {aa5} pts against")
    if af3 is not None:
        lines.append(f"  Avg score (last 3): {af3} pts for, {aa3} pts against")
    if af5 and af3:
        lines.append(f"  Attack trend: {atk}  |  Defense trend: {dft}")
    if am5 is not None:
        lines.append(f"  Average margin (last 5): {am5:+.1f} pts")

    return "\n".join(lines) if lines else "Scoring data unavailable"


def format_rest_and_travel(rest, travel, team_name):
    """Format rest days and travel fatigue for the prompt."""
    parts = []
    if rest:
        parts.append(rest.get("description", ""))
    if travel:
        desc = travel.get("description", "")
        if desc:
            parts.append(desc)
    return "\n  ".join(parts) if parts else "No rest/travel data"


def format_odds_section(odds, home, away):
    """Format all three betting markets."""
    if not odds:
        return "Betting odds not available this week."

    lines = ["BETTING MARKETS (averaged across bookmakers):"]
    if odds.get("home_odds"):
        lines.append(
            f"  Win/Loss: {home} ${odds['home_odds']} ({odds.get('home_implied_prob','?')}% implied) | "
            f"{away} ${odds['away_odds']} ({odds.get('away_implied_prob','?')}% implied)"
        )
    if odds.get("line_summary"):
        lines.append(f"  Line market: {odds['line_summary']} (market's expected margin)")
    if odds.get("total_summary"):
        lines.append(f"  Totals market: {odds['total_summary']}")
    lines.append(
        "  Note: Use all markets as ONE input alongside form, scoring trends, travel, and team news."
    )
    return "\n".join(lines)


def format_h2h(h2h_list):
    if not h2h_list:
        return "No H2H data"
    return " | ".join(
        f"{g['winner']} won {g['score']} at {g['venue']} in {g['year']}"
        for g in h2h_list[:6]
    )


def format_ladder(ld):
    if not ld:
        return "Unavailable"
    return (
        f"Position {ld.get('rank','?')} | "
        f"{ld.get('wins','?')}W-{ld.get('losses','?')}L | "
        f"{ld.get('pts','?')} pts | {ld.get('percentage','?')}%"
    )


# ─── Single match prediction ───────────────────────────────────────────────────

def generate_prediction(match_data, general_news_context=""):
    """Generate a full AI prediction for one match."""
    home  = match_data["home_team"]
    away  = match_data["away_team"]
    venue = match_data["venue"]
    date  = match_data["date"]

    weather_text   = format_weather_for_ai(venue, date)
    odds_text      = format_odds_section(match_data.get("betting_odds", {}), home, away)
    team_news_text = format_team_news_for_ai(home, away)
    history_text   = format_history_for_ai(home, away)
    squiggle_text  = match_data.get("squiggle_model", "Not available.")

    home_scoring = match_data.get("home_scoring", {})
    away_scoring = match_data.get("away_scoring", {})
    home_rest    = match_data.get("home_rest", {})
    away_rest    = match_data.get("away_rest", {})
    home_travel  = match_data.get("home_travel", {})
    away_travel  = match_data.get("away_travel", {})

    prompt = f"""
You are an expert AFL analyst. Study ALL data sections below carefully before predicting.

════════════════════════════════════════════
MATCH: {home} vs {away}
Round {match_data['round']} | {date} | {venue}
════════════════════════════════════════════

━━━ LADDER STANDINGS ━━━
{home}: {format_ladder(match_data['home_ladder'])}
{away}: {format_ladder(match_data['away_ladder'])}

━━━ RECENT FORM — W/L with actual margins ━━━
{home}: {format_form(match_data['home_form'])}
{away}: {format_form(match_data['away_form'])}

━━━ SCORING STATISTICS & TRENDS ━━━
{home} scoring stats:
{format_scoring_stats(home_scoring, home)}

{away} scoring stats:
{format_scoring_stats(away_scoring, away)}

IMPORTANT: A team averaging 110 pts in their last 3 vs 92 pts over their last 5
is in much better form than W/L alone suggests. Weight recent scoring trends heavily.

━━━ REST DAYS & TRAVEL FATIGUE ━━━
{home} (Home team):
  {format_rest_and_travel(home_rest, home_travel, home)}

{away} (Away team):
  {format_rest_and_travel(away_rest, away_travel, away)}

IMPORTANT: Perth teams travelling east, or any team on fewer than 7 days rest,
carry a genuine performance penalty — especially in Q3 and Q4.

━━━ HEAD TO HEAD (last 10 meetings) ━━━
{format_h2h(match_data['head_to_head'])}

━━━ VENUE RECORD at {venue} ━━━
{home}: {format_form(match_data.get('home_venue_record', []))}
{away}: {format_form(match_data.get('away_venue_record', []))}

━━━ BETTING MARKETS ━━━
{odds_text}

━━━ SQUIGGLE STATISTICAL MODEL CROSS-CHECK ━━━
{squiggle_text}

━━━ WEATHER FORECAST ━━━
{weather_text}

━━━ TEAM NEWS — INJURIES, SELECTIONS & SUSPENSIONS ━━━
{team_news_text}

━━━ GENERAL AFL NEWS ━━━
{general_news_context[:800] if general_news_context else "No general news."}

━━━ AGENT'S OWN ACCURACY HISTORY ━━━
{history_text}

════════════════════════════════════════════
Use EXACTLY this response format:
════════════════════════════════════════════

**PREDICTED WINNER:** [Team name]

**WIN PROBABILITY:** {home}: XX% | {away}: XX%
Briefly explain how you weighted: betting market vs Squiggle model vs form vs scoring trend.

**PREDICTED MARGIN:** ~XX points

**KEY FACTORS:**
1. [Specific data reference — e.g. "Carlton averaging 108 pts in last 3, trending up vs 89 for Melbourne"]
2. [Specific data reference]
3. [Specific data reference]
4. [Fourth factor if relevant]

**SCORING TRENDS ANALYSIS:**
[Which team is trending up or down in attack AND defense? Reference last-3 vs last-5 averages.]

**MARKET & MODEL ANALYSIS:**
[Do the betting line, h2h market, and Squiggle model agree? If not, explain which you trust more.]

**FATIGUE & TRAVEL IMPACT:**
[Any short turnarounds or long travel? How does this affect the prediction, especially late in the game?]

**WEATHER IMPACT:**
[How will forecast conditions affect this specific match?]

**TEAM NEWS IMPACT:**
[Specific impact of any injuries, suspensions or selection changes.]

**CONFIDENCE:** High / Medium / Low
[Reasoning — e.g. "High — all indicators align" or "Low — key injury uncertainty"]

**UPSET RISK:**
[Specific factors that could cause the underdog to win.]

**SELF-CALIBRATION NOTE:**
[Based on past accuracy history, note anything affecting confidence in this pick.]
"""

    try:
        model    = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ Error generating prediction: {e}"


# ─── Run all predictions ───────────────────────────────────────────────────────

def run_weekly_predictions(match_data_list, news_headlines):
    """Run predictions for all this week's matches and save to history."""
    general_news = "".join(
        f"• {item['title']}: {item['summary']}\n"
        for item in news_headlines[:10]
    )

    round_number = match_data_list[0].get("round") if match_data_list else None
    print(f"\n📊 Fetching Squiggle model predictions for Round {round_number}...")
    squiggle_tips = get_squiggle_tips(round_number=round_number)

    all_predictions = []

    for match in match_data_list:
        home = match["home_team"]
        away = match["away_team"]
        print(f"\n🏉 Predicting: {home} vs {away}...")

        match["squiggle_model"] = format_squiggle_tips_for_prompt(squiggle_tips, home, away)
        prediction_text         = generate_prediction(match, general_news)

        all_predictions.append({
            "round":        match.get("round"),
            "date":         match.get("date", ""),
            "date_full":    match.get("date_full", ""),
            "venue":        match.get("venue", ""),
            "home_team":    home,
            "away_team":    away,
            "betting_odds": match.get("betting_odds", {}),
            "home_scoring": match.get("home_scoring", {}),
            "away_scoring": match.get("away_scoring", {}),
            "home_rest":    match.get("home_rest", {}),
            "away_rest":    match.get("away_rest", {}),
            "home_travel":  match.get("home_travel", {}),
            "away_travel":  match.get("away_travel", {}),
            "prediction":   prediction_text
        })

    if all_predictions and round_number:
        print(f"\n💾 Saving Round {round_number} predictions to history...")
        save_predictions(all_predictions, round_number)

    return all_predictions
