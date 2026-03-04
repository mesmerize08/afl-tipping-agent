"""
predict.py  (UPGRADED — uses scoring stats, travel, rest days, scoring trends)
===============================================================================
All new data fields from data_fetcher.py are now injected into the AI prompt.
"""

import os
import requests as _requests

from team_news import format_team_news_for_ai
from tracker   import format_history_for_ai, save_predictions
from weather   import format_weather_for_ai
from data_fetcher import get_squiggle_tips, format_squiggle_tips_for_prompt

# ─── AI backend ────────────────────────────────────────────────────────────────
# PRIMARY: Groq free tier (6 000 req/day — no credit card)
#   1. Sign up at console.groq.com
#   2. Create an API key (starts with gsk_...)
#   3. Streamlit Cloud → Settings → Secrets:
#        GROQ_API_KEY = "gsk_..."
#
# FALLBACK: Anthropic API (paid credits at console.anthropic.com,
#   separate from Claude Pro subscription):
#        ANTHROPIC_API_KEY = "sk-ant-..."
# ───────────────────────────────────────────────────────────────────────────────
_GROQ_API_KEY      = os.getenv("GROQ_API_KEY", "")
_ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


def _call_ai(prompt: str) -> str:
    """Route to the best available AI backend (Groq first, Anthropic fallback)."""

    # ── Groq ───────────────────────────────────────────────────────────────────
    if _GROQ_API_KEY:
        try:
            resp = _requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {_GROQ_API_KEY}",
                    "Content-Type":  "application/json",
                },
                json={
                    "model":       "llama-3.3-70b-versatile",
                    "messages":    [{"role": "user", "content": prompt}],
                    "max_tokens":  2048,
                    "temperature": 0.3,
                },
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  Groq error: {e} — trying Anthropic fallback...")

    # ── Anthropic fallback ─────────────────────────────────────────────────────
    if _ANTHROPIC_API_KEY:
        try:
            resp = _requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key":         _ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "Content-Type":      "application/json",
                },
                json={
                    "model":      "claude-haiku-4-5-20251001",
                    "max_tokens": 2048,
                    "messages":   [{"role": "user", "content": prompt}],
                },
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]
        except Exception as e:
            raise RuntimeError(f"Anthropic API error: {e}")

    raise RuntimeError(
        "No AI API key configured. Add GROQ_API_KEY (free at console.groq.com) "
        "or ANTHROPIC_API_KEY to Streamlit Cloud secrets. See predict.py header."
    )


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
You are a professional Australian Rules Football data analyst. You have no team allegiances,
no emotional investment in any outcome, and no awareness of media narratives or public opinion.

YOUR ONLY FUNCTION is to analyse the data provided below and produce a structured, evidence-based
prediction. Every single conclusion you state must be explicitly justified by a specific number,
statistic, or data point from the sections below. If the data does not support a conclusion,
you do not make it.

STRICT RULES:
- Never reference media narratives, public sentiment, fan expectations, or team reputations
- Never use words like "dominant", "powerhouse", "struggling", "resurgent" unless directly
  supported by the numbers in front of you
- Never say "traditionally strong" or "historically tough" without citing actual H2H figures
- Never use gut feel, hype, or assumptions — only the data below
- If two data points contradict each other, acknowledge the contradiction explicitly
- Uncertainty is acceptable and encouraged — do not manufacture false confidence
- The betting market and Squiggle model are data points, not answers. Interrogate them.

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
{home}:
{format_scoring_stats(home_scoring, home)}

{away}:
{format_scoring_stats(away_scoring, away)}

━━━ REST DAYS & TRAVEL FATIGUE ━━━
{home} (Home):
  {format_rest_and_travel(home_rest, home_travel, home)}

{away} (Away):
  {format_rest_and_travel(away_rest, away_travel, away)}

━━━ HEAD TO HEAD (last 10 meetings) ━━━
{format_h2h(match_data['head_to_head'])}

━━━ VENUE RECORD at {venue} ━━━
{home}: {format_form(match_data.get('home_venue_record', []))}
{away}: {format_form(match_data.get('away_venue_record', []))}

━━━ BETTING MARKETS ━━━
{odds_text}

━━━ SQUIGGLE STATISTICAL MODEL ━━━
{squiggle_text}

━━━ WEATHER FORECAST ━━━
{weather_text}

━━━ TEAM NEWS ━━━
{team_news_text}

━━━ GENERAL AFL NEWS ━━━
{general_news_context[:800] if general_news_context else "None available."}

━━━ AGENT ACCURACY HISTORY ━━━
{history_text}

════════════════════════════════════════════
OUTPUT FORMAT — follow this exactly, every week, every match, no exceptions:
════════════════════════════════════════════

**PREDICTED WINNER:** [Team name only]

**WIN PROBABILITY:** {home}: XX% | {away}: XX%
Justify this figure in one sentence by referencing which specific data inputs drove it
and how much weight you gave the betting market vs Squiggle model vs form data.

**PREDICTED MARGIN:** ~XX points
Justify with reference to average scoring margins and line market data.

**KEY FACTORS:**
1. [Data point + what it means for this match. No vague statements.]
2. [Data point + what it means for this match.]
3. [Data point + what it means for this match.]
4. [Data point + what it means for this match. Omit if not supported by data.]

**SCORING TRENDS ANALYSIS:**
State the last-5 and last-3 averages for both teams explicitly.
State whether each team's attack and defense is trending up, down, or stable.
State which team's scoring profile gives them an advantage and why.

**MARKET & MODEL ANALYSIS:**
State what the h2h market implies. State what the line market implies.
State what the Squiggle model predicts. Do they agree or disagree?
If they disagree, state which you weighted more heavily and why, using data to justify.

**FATIGUE & TRAVEL IMPACT:**
State exact days rest for each team. Flag any travel.
State whether this is sufficient to affect performance and in which quarters.
If no fatigue factor exists, say so explicitly — do not omit this section.

**WEATHER IMPACT:**
State the forecast conditions. State whether conditions favour one team over the other
based on their scoring style (high-marking vs ground-level). If conditions are neutral, say so.

**TEAM NEWS IMPACT:**
List any confirmed ins/outs and their specific positional impact.
If no team news is available, state that explicitly — do not omit this section.

**CONFIDENCE:** [High / Medium / Low]
Justify in one sentence. Reference specifically whether the data sources agree or conflict.

**UPSET RISK:** [Low / Medium / High]
List the specific data points that could support an upset. No hypotheticals —
only factors visible in the data above.

**DATA CONFLICTS:**
List any cases where two data sources gave contradictory signals
(e.g. form says Team A but betting market says Team B).
If no conflicts exist, write "None identified."
"""

    try:
        return _call_ai(prompt)
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

    if all_predictions and round_number is not None:
        print(f"\n💾 Saving Round {round_number} predictions to history...")
        save_predictions(all_predictions, round_number)

    return all_predictions
