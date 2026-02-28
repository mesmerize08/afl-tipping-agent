"""
predict.py  (UPGRADED — weather + line/totals odds + Squiggle cross-check)
==========================================================================
New sections injected into the AI prompt:
  - Weather forecast and game impact assessment
  - Line market (expected margin from betting markets)
  - Totals market (expected total score)
  - Squiggle statistical model cross-check
"""

import google.generativeai as genai
import os

from team_news import format_team_news_for_ai
from tracker   import format_history_for_ai, save_predictions
from weather   import format_weather_for_ai
from data_fetcher import get_squiggle_tips

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


# ─── Formatting Helpers ────────────────────────────────────────────────────────

def format_form(form_list, team_name):
    if not form_list:
        return "No recent data available"
    wins    = sum(1 for g in form_list if g["result"] == "W")
    details = " | ".join(
        f"{g['result']} vs {g['opponent']} ({g['score']}) on {g['date']}"
        for g in form_list
    )
    return f"{wins}/{len(form_list)} wins. {details}"


def format_h2h(h2h_list):
    if not h2h_list:
        return "No H2H data available"
    return " | ".join(
        f"{g['winner']} won ({g['score']}) at {g['venue']} in {g['year']}"
        for g in h2h_list[:6]
    )


def format_ladder(ladder_data):
    if not ladder_data:
        return "Ladder data unavailable"
    return (
        f"Position {ladder_data.get('rank','?')} | "
        f"{ladder_data.get('wins','?')}W-{ladder_data.get('losses','?')}L | "
        f"{ladder_data.get('pts','?')} pts | "
        f"{ladder_data.get('percentage','?')}% percentage"
    )


def format_odds_section(odds, home, away):
    """Format all three betting markets into a clear prompt section."""
    if not odds:
        return "Betting odds not available this week."

    lines = ["BETTING MARKETS (averaged across bookmakers):"]

    # H2H
    if odds.get("home_odds"):
        lines.append(
            f"  Win/Loss: {home} ${odds['home_odds']} ({odds.get('home_implied_prob','?')}% implied) | "
            f"{away} ${odds['away_odds']} ({odds.get('away_implied_prob','?')}% implied)"
        )

    # Line/Spread
    if odds.get("line_summary"):
        lines.append(
            f"  Line market: {odds['line_summary']} "
            f"(this is the market's expected winning margin)"
        )

    # Totals
    if odds.get("total_summary"):
        lines.append(f"  Totals market: {odds['total_summary']}")

    lines.append(
        "  Note: Do NOT simply copy the implied probabilities. "
        "Use all three markets together as ONE input alongside form, H2H, weather, and team news."
    )

    return "\n".join(lines)


# ─── Single Match Prediction ───────────────────────────────────────────────────

def generate_prediction(match_data, general_news_context=""):
    """Generate a prediction for a single match using all available data."""
    home  = match_data["home_team"]
    away  = match_data["away_team"]
    venue = match_data["venue"]
    date  = match_data["date"]

    # ── Fetch weather ──
    weather_text   = format_weather_for_ai(venue, date)

    # ── Format all data sections ──
    odds_text      = format_odds_section(match_data.get("betting_odds", {}), home, away)
    team_news_text = format_team_news_for_ai(home, away)
    history_text   = format_history_for_ai(home, away)
    squiggle_text  = match_data.get("squiggle_model", "Squiggle data not available.")

    prompt = f"""
You are an expert AFL analyst. Study ALL data sections below carefully before predicting.

════════════════════════════════════════════
MATCH: {home} vs {away}
Round {match_data['round']} | {date} | {venue}
════════════════════════════════════════════

━━━ LADDER STANDINGS ━━━
{home}: {format_ladder(match_data['home_ladder'])}
{away}: {format_ladder(match_data['away_ladder'])}

━━━ RECENT FORM (last 5 games) ━━━
{home}: {format_form(match_data['home_form'], home)}
{away}: {format_form(match_data['away_form'], away)}

━━━ HOME/AWAY CONTEXT ━━━
{home} is playing at HOME. {away} is playing AWAY.
Home teams win ~58% of AFL games — factor this in, but do not over-weight it.

━━━ HEAD TO HEAD (last 10 meetings) ━━━
{format_h2h(match_data['head_to_head'])}

━━━ VENUE RECORD at {venue} ━━━
{home}: {format_form(match_data['home_venue_record'], home)}
{away}: {format_form(match_data['away_venue_record'], away)}

━━━ BETTING MARKETS ━━━
{odds_text}

━━━ SQUIGGLE STATISTICAL MODEL CROSS-CHECK ━━━
{squiggle_text}

━━━ WEATHER FORECAST ━━━
{weather_text}

━━━ TEAM NEWS — INJURIES, SELECTIONS & SUSPENSIONS ━━━
{team_news_text}

━━━ GENERAL AFL NEWS ━━━
{general_news_context[:800] if general_news_context else "No general news available."}

━━━ YOUR OWN PREDICTION HISTORY & ACCURACY ━━━
{history_text}

════════════════════════════════════════════
INSTRUCTIONS: Use EXACTLY this format for your response:
════════════════════════════════════════════

**PREDICTED WINNER:** [Team name]

**WIN PROBABILITY:** {home}: XX% | {away}: XX%
Explain briefly how you weighted the betting market vs Squiggle model vs form data.

**PREDICTED MARGIN:** ~XX points

**KEY FACTORS:**
1. [Most important reason with specific data reference]
2. [Second reason with specific data reference]
3. [Third reason with specific data reference]
4. [Fourth reason if relevant]

**MARKET & MODEL ANALYSIS:**
[Compare the betting line market, the h2h implied probability, and the Squiggle model prediction.
Do they agree or disagree? If they disagree, explain why you sided with one over the other.]

**WEATHER IMPACT:**
[How will the forecast conditions affect this specific match? 
Which team benefits or suffers more from the conditions?]

**TEAM NEWS IMPACT:**
[How do any injuries, suspensions or selection changes affect the prediction?]

**CONFIDENCE:** High / Medium / Low
[Explain — e.g. "High — betting market, Squiggle model, and form all agree" or 
"Low — Squiggle model and betting market disagree significantly"]

**UPSET RISK:**
[What specific factors could cause the underdog to win?]

**SELF-CALIBRATION NOTE:**
[Based on your past accuracy history above, note anything that makes you more or less
confident. If you've been wrong about one of these teams recently, acknowledge it.]
"""

    try:
        model    = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ Error generating prediction: {e}"


# ─── Run All Predictions ───────────────────────────────────────────────────────

def run_weekly_predictions(match_data_list, news_headlines):
    """Run predictions for all this week's matches and save to history."""

    # Format general news
    general_news = ""
    for item in news_headlines[:10]:
        general_news += f"• {item['title']}: {item['summary']}\n"

    # Fetch Squiggle tips once for the round
    round_number = match_data_list[0].get("round") if match_data_list else None
    print(f"\n📊 Fetching Squiggle model predictions for Round {round_number}...")
    squiggle_tips = get_squiggle_tips(round_number=round_number)

    all_predictions = []

    for match in match_data_list:
        home = match["home_team"]
        away = match["away_team"]
        print(f"\n🏉 Predicting: {home} vs {away}...")

        # Inject Squiggle data into match data
        from data_fetcher import format_squiggle_tips_for_prompt
        match["squiggle_model"] = format_squiggle_tips_for_prompt(squiggle_tips, home, away)

        prediction_text = generate_prediction(match, general_news)

        all_predictions.append({
            "round":        match.get("round"),
            "date":         match.get("date", ""),
            "venue":        match.get("venue", ""),
            "home_team":    home,
            "away_team":    away,
            "betting_odds": match.get("betting_odds", {}),
            "prediction":   prediction_text
        })

    # Auto-save to history
    if all_predictions and round_number:
        print(f"\n💾 Saving predictions for Round {round_number} to history...")
        save_predictions(all_predictions, round_number)

    return all_predictions
