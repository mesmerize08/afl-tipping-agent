"""
predict.py  (UPDATED — now uses team news + prediction history)
===============================================================
The AI prediction engine. Feeds all data sources into Google Gemini
and returns structured match predictions with probabilities.

New in this version:
  - Team selection / injury news injected into prompt
  - Agent's own past accuracy and prediction history injected
  - AI is instructed to learn from its past mistakes
"""

import google.generativeai as genai
import os

from team_news import format_team_news_for_ai
from tracker import format_history_for_ai, save_predictions

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


# ─── Formatting Helpers ────────────────────────────────────────────────────────

def format_form(form_list, team_name):
    """Format recent form into readable string."""
    if not form_list:
        return "No recent data available"
    wins = sum(1 for g in form_list if g["result"] == "W")
    details = " | ".join(
        f"{g['result']} vs {g['opponent']} ({g['score']}) on {g['date']}"
        for g in form_list
    )
    return f"{wins}/{len(form_list)} wins. {details}"


def format_h2h(h2h_list):
    """Format head-to-head history into readable string."""
    if not h2h_list:
        return "No H2H data available"
    results = [
        f"{g['winner']} won ({g['score']}) at {g['venue']} in {g['year']}"
        for g in h2h_list[:6]
    ]
    return " | ".join(results)


def format_ladder(ladder_data):
    """Format ladder position info."""
    if not ladder_data:
        return "Ladder data unavailable"
    pos   = ladder_data.get("rank", "?")
    wins  = ladder_data.get("wins", "?")
    loss  = ladder_data.get("losses", "?")
    pct   = ladder_data.get("percentage", "?")
    pts   = ladder_data.get("pts", "?")
    return f"Position {pos} | {wins}W-{loss}L | {pts} pts | {pct}% percentage"


# ─── Single Match Prediction ───────────────────────────────────────────────────

def generate_prediction(match_data, general_news_context=""):
    """
    Use Gemini to generate a prediction for a single match.
    Now includes team news and the agent's own history.
    """
    home  = match_data["home_team"]
    away  = match_data["away_team"]
    odds  = match_data.get("betting_odds", {})

    # ── Odds section ──
    if odds:
        odds_text = (
            f"BETTING ODDS (averaged across bookmakers):\n"
            f"  - {home}: ${odds.get('home_odds', 'N/A')} "
            f"(implied prob: {odds.get('home_implied_prob', 'N/A')}%)\n"
            f"  - {away}: ${odds.get('away_odds', 'N/A')} "
            f"(implied prob: {odds.get('away_implied_prob', 'N/A')}%)"
        )
    else:
        odds_text = "BETTING ODDS: Not available this week."

    # ── Team news (injuries, selections, suspensions) ──
    team_news_text = format_team_news_for_ai(home, away)

    # ── Agent's own history & accuracy ──
    history_text = format_history_for_ai(home, away)

    # ── Full prompt ──
    prompt = f"""
You are an expert AFL analyst with a data-driven, unbiased approach.
Study ALL sections below carefully before making your prediction.

════════════════════════════════════════════
MATCH: {home} vs {away}
Round {match_data['round']} | {match_data['date']} | {match_data['venue']}
════════════════════════════════════════════

━━━ LADDER STANDINGS ━━━
{home}: {format_ladder(match_data['home_ladder'])}
{away}: {format_ladder(match_data['away_ladder'])}

━━━ RECENT FORM (last 5 games) ━━━
{home}: {format_form(match_data['home_form'], home)}
{away}: {format_form(match_data['away_form'], away)}

━━━ HOME/AWAY RECORD ━━━
{home} is playing at HOME.
{away} is playing AWAY.
Home team wins approximately 58% of AFL games historically — factor this in.

━━━ HEAD TO HEAD (last 10 meetings) ━━━
{format_h2h(match_data['head_to_head'])}

━━━ VENUE RECORD at {match_data['venue']} ━━━
{home}: {format_form(match_data['home_venue_record'], home)}
{away}: {format_form(match_data['away_venue_record'], away)}

━━━ {odds_text} ━━━

━━━ TEAM NEWS — INJURIES, SELECTIONS & SUSPENSIONS ━━━
{team_news_text}

━━━ GENERAL AFL NEWS (context) ━━━
{general_news_context[:1000] if general_news_context else "No general news available."}

━━━ YOUR OWN PREDICTION HISTORY & ACCURACY ━━━
{history_text}

NOTE: Review your past incorrect predictions above. If you have been consistently
wrong about a particular team or factor, adjust your approach accordingly.
If your upset-pick accuracy is low, be more conservative with underdog predictions.

════════════════════════════════════════════
YOUR PREDICTION — use EXACTLY this format:
════════════════════════════════════════════

**PREDICTED WINNER:** [Team name]

**WIN PROBABILITY:** {home}: XX% | {away}: XX%
(Do NOT simply copy the betting implied probability. Use it as one input
alongside form, H2H, venue, team news, and your own historical accuracy.)

**PREDICTED MARGIN:** ~XX points

**KEY FACTORS:**
1. [Most important reason, referencing specific data]
2. [Second reason, referencing specific data]
3. [Third reason, referencing specific data]
4. [Fourth reason if relevant]

**TEAM NEWS IMPACT:**
[Explain specifically how any injuries, suspensions, or selection changes affect the prediction]

**CONFIDENCE:** Low / Medium / High
[Explain why — e.g. "High — all indicators agree" or "Low — injury uncertainty"]

**UPSET RISK:** 
[What specific factors could cause the underdog to win?]

**SELF-CALIBRATION NOTE:**
[Based on your past history above, note anything that makes you more or less
confident in this specific prediction. If you've been wrong about one of these
teams recently, acknowledge it and explain how it affects your tip.]
"""

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ Error generating prediction: {e}"


# ─── Run All Predictions for the Week ─────────────────────────────────────────

def run_weekly_predictions(match_data_list, news_headlines):
    """
    Run predictions for all this week's matches and save to history.
    """
    # Format general news into a single context block
    general_news = ""
    for item in news_headlines[:10]:
        general_news += f"• {item['title']}: {item['summary']}\n"

    all_predictions = []
    round_number = None

    for match in match_data_list:
        home = match["home_team"]
        away = match["away_team"]
        print(f"\n🏉 Predicting: {home} vs {away}...")

        prediction_text = generate_prediction(match, general_news)
        round_number = match.get("round")

        all_predictions.append({
            "round":        round_number,
            "date":         match.get("date", ""),
            "venue":        match.get("venue", ""),
            "home_team":    home,
            "away_team":    away,
            "betting_odds": match.get("betting_odds", {}),
            "prediction":   prediction_text
        })

    # ── Auto-save to history ──
    if all_predictions and round_number:
        print(f"\n💾 Saving predictions for Round {round_number} to history...")
        save_predictions(all_predictions, round_number)

    return all_predictions
