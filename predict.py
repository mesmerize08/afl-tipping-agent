"""
predict.py  (OPTIMIZED — Added retry logic, better error handling, type hints)
===============================================================================
AI prediction engine for the AFL Tipping Agent.

IMPROVEMENTS IN THIS VERSION:
  - Exponential backoff retry logic for API failures
  - Better error messages with actionable guidance
  - Type hints for better code quality
  - Prompt length validation
  - Request timeout constants

AI backend: Groq (free tier, llama-3.3-70b-versatile, 6000 req/day)
  Primary:  https://api.groq.com/openai/v1/chat/completions
  Fallback: Anthropic API (claude-haiku-4-5-20251001)

Environment variables required:
  GROQ_API_KEY      — primary AI engine
  ANTHROPIC_API_KEY — fallback (optional but recommended)
"""

import logging
import os
import re
import time
import traceback
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

from team_news  import format_team_news_for_ai
from tracker    import format_history_for_ai, save_predictions
from weather    import format_weather_for_ai
from data_fetcher import get_squiggle_tips, format_squiggle_tips_for_prompt


# ── Configuration Constants ───────────────────────────────────────────────────

API_TIMEOUT = 60  # seconds
MAX_RETRIES = 3
RETRY_DELAY_BASE = 2  # exponential backoff base (2^attempt seconds)
MAX_PROMPT_LENGTH = 12000  # characters (approx 3000 tokens)


# ── AI backend with retry logic ───────────────────────────────────────────────

def _call_ai_with_retry(prompt: str, max_retries: int = MAX_RETRIES) -> str:
    """
    Call AI backend with exponential backoff retry logic.
    Handles transient failures like timeouts and rate limits gracefully.
    
    Args:
        prompt: The full prediction prompt
        max_retries: Maximum number of retry attempts (default: 3)
    
    Returns:
        AI response text, or detailed error message
    """
    groq_key = os.getenv("GROQ_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    # Validate prompt length
    if len(prompt) > MAX_PROMPT_LENGTH:
        logger.warning("Prompt is %d chars (limit: %d) — truncating", len(prompt), MAX_PROMPT_LENGTH)
        prompt = prompt[:MAX_PROMPT_LENGTH] + "\n\n[Prompt truncated due to length]"
    
    last_error = None
    
    # Try Groq first with retries
    if groq_key:
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {groq_key}",
                        "Content-Type":  "application/json",
                    },
                    json={
                        "model":       "llama-3.3-70b-versatile",
                        "max_tokens":  2000,
                        "temperature": 0.3,
                        "messages":    [{"role": "user", "content": prompt}],
                    },
                    timeout=API_TIMEOUT,
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
                
            except requests.exceptions.Timeout:
                last_error = f"Groq timeout on attempt {attempt + 1}/{max_retries}"
                logger.warning(last_error)
                if attempt < max_retries - 1:
                    delay = RETRY_DELAY_BASE ** attempt
                    logger.info("Retrying in %ds...", delay)
                    time.sleep(delay)

            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code

                # Rate limit (429) or service unavailable (503) - retry with backoff
                if status_code in [429, 503]:
                    last_error = f"Groq {status_code} (rate limit/unavailable) on attempt {attempt + 1}/{max_retries}"
                    logger.warning(last_error)
                    if attempt < max_retries - 1:
                        delay = RETRY_DELAY_BASE ** attempt
                        logger.info("Retrying in %ds...", delay)
                        time.sleep(delay)
                else:
                    # Other HTTP errors - don't retry, fall through to Anthropic
                    last_error = f"Groq HTTP {status_code}: {str(e)}"
                    logger.error(last_error)
                    break

            except Exception as e:
                last_error = f"Groq unexpected error: {str(e)}"
                logger.error(last_error)
                break

        logger.warning("Groq failed after %d attempts — trying Anthropic fallback", max_retries)
    
    # Try Anthropic fallback
    if anthropic_key:
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key":         anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type":      "application/json",
                },
                json={
                    "model":      "claude-haiku-4-5-20251001",
                    "max_tokens": 2000,
                    "messages":   [{"role": "user", "content": prompt}],
                },
                timeout=API_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()["content"][0]["text"]
            
        except Exception as e:
            last_error = f"Anthropic fallback also failed: {str(e)}"
            logger.error(last_error)
    
    # Both backends failed - return helpful error message
    error_msg = f"""
ERROR: Unable to generate AI prediction after {max_retries} retries.

Last error: {last_error}

TROUBLESHOOTING:
1. Check your API keys are set correctly in environment variables:
   - GROQ_API_KEY: {'✓ Set' if groq_key else '✗ Missing'}
   - ANTHROPIC_API_KEY: {'✓ Set' if anthropic_key else '✗ Missing (fallback)'}

2. Check your API rate limits:
   - Groq: 6,000 requests/day
   - Check current usage at https://console.groq.com

3. Check your internet connection

4. Try again in a few minutes (may be temporary service issue)

If this persists, please report at: github.com/mesmerize08/afl-tipping-agent/issues
"""
    return error_msg


# Backward compatibility - keep old function name
def _call_ai(prompt: str) -> str:
    """Legacy function name - redirects to retry version"""
    return _call_ai_with_retry(prompt)


# ── Formatting helpers ─────────────────────────────────────────────────────────

def format_form(form_list: List[Dict]) -> str:
    """Format form list with margins."""
    if not form_list:
        return "No recent data"
    parts = []
    for g in form_list:
        margin_str = f"+{g['margin']}" if g.get("margin", 0) > 0 else str(g.get("margin", 0))
        parts.append(f"{g['result']} vs {g['opponent']} {g['score']} ({margin_str} pts) on {g['date']}")
    wins = sum(1 for g in form_list if g["result"] == "W")
    return f"{wins}/{len(form_list)} wins. " + " | ".join(parts)


def format_scoring_stats(scoring: Dict, team_name: str) -> str:
    """Format scoring stats and trends into readable prompt text."""
    if not scoring:
        return "Scoring data unavailable"
    lines = []
    af5 = scoring.get("avg_for_5")
    aa5 = scoring.get("avg_against_5")
    af3 = scoring.get("avg_for_3")
    aa3 = scoring.get("avg_against_3")
    atk = scoring.get("attack_trend",  "stable")
    dft = scoring.get("defense_trend", "stable")
    am5 = scoring.get("avg_margin_5")
    if af5 is not None:
        lines.append(f"  Avg score (last 5): {af5} pts for, {aa5} pts against")
    if af3 is not None:
        lines.append(f"  Avg score (last 3): {af3} pts for, {aa3} pts against")
    if af5 and af3:
        lines.append(f"  Attack trend: {atk}  |  Defence trend: {dft}")
    if am5 is not None:
        lines.append(f"  Average margin (last 5): {am5:+.1f} pts")
    return "\n".join(lines) if lines else "Scoring data unavailable"


def format_rest_and_travel(rest: Optional[Dict], travel: Optional[Dict], team_name: str) -> str:
    """Format rest days and travel fatigue."""
    parts = []
    if rest:
        parts.append(rest.get("description", ""))
    if travel:
        desc = travel.get("description", "")
        if desc:
            parts.append(desc)
    return "\n  ".join(parts) if parts else "No rest/travel data"


def format_odds_section(odds: Dict, home: str, away: str) -> str:
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


def format_h2h(h2h_list: List[Dict]) -> str:
    if not h2h_list:
        return "No H2H data"
    return " | ".join(
        f"{g['winner']} won {g['score']} at {g['venue']} in {g['year']}"
        for g in h2h_list[:6]
    )


def format_ladder(ld: Dict) -> str:
    if not ld:
        return "Unavailable"
    return (
        f"Position {ld.get('rank','?')} | "
        f"{ld.get('wins','?')}W-{ld.get('losses','?')}L | "
        f"{ld.get('pts','?')} pts | {ld.get('percentage','?')}%"
    )


def format_home_advantage(match_data: Dict, home: str, away: str) -> str:
    """
    Format home/away win splits and venue record into a clear prompt block.
    Combines the season split (broad) with the specific venue record (narrow).
    """
    lines = []
    venue = match_data.get("venue", "this venue")

    # Season home vs away win rate
    for team, key in [(home, "home_ha_split"), (away, "away_ha_split")]:
        split = match_data.get(key, {})
        h = split.get("home", {})
        a = split.get("away", {})
        h_str = (f"{h['wins']}/{h['games']} ({h['pct']}%)" if h.get("games") else "no data")
        a_str = (f"{a['wins']}/{a['games']} ({a['pct']}%)" if a.get("games") else "no data")
        if h.get("games") or a.get("games"):
            lines.append(f"{team} this season -- Home: {h_str} | Away: {a_str}")
            if h.get("pct") is not None and a.get("pct") is not None:
                diff = h["pct"] - a["pct"]
                if diff >= 20:
                    lines.append(
                        f"  >> {team} win rate is {diff}pp higher at home "
                        f"-- HOME GROUND ADVANTAGE IS SIGNIFICANT"
                    )
                elif diff <= -20:
                    lines.append(
                        f"  >> {team} win rate is {abs(diff)}pp higher away "
                        f"-- performs better as visitor"
                    )

    # Specific venue record
    for team, record_key in [(home, "home_venue_record"), (away, "away_venue_record")]:
        rec = match_data.get(record_key, [])
        if rec:
            wins       = sum(1 for g in rec if g["result"] == "W")
            n          = len(rec)
            avg_margin = sum(g["margin"] for g in rec) / n
            lines.append(
                f"{team} at {venue} (last {n} games): {wins}W-{n - wins}L "
                f"| avg margin {avg_margin:+.1f} pts"
            )
        else:
            lines.append(f"{team} at {venue}: no venue history available")

    lines.append(
        "Context: AFL home ground advantage is typically worth 5-10 pts. "
        "Key factors: crowd noise, ground familiarity, reduced travel for home side."
    )

    return "\n".join(lines) if lines else "Home/away data unavailable."


# ── Single match prediction ────────────────────────────────────────────────────

def generate_prediction(match_data: Dict, general_news_context: str = "") -> str:
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
    home_rest    = match_data.get("home_rest",    {})
    away_rest    = match_data.get("away_rest",    {})
    home_travel  = match_data.get("home_travel",  {})
    away_travel  = match_data.get("away_travel",  {})

    prompt = f"""
You are a professional Australian Rules Football data analyst. You have no team allegiances,
no emotional investment in any outcome, and no awareness of media narratives or public opinion.

YOUR ONLY FUNCTION is to analyse the data provided below and produce a structured, evidence-based
prediction. Every conclusion you state must be explicitly justified by a specific number,
statistic, or data point from the sections below. If the data does not support a conclusion,
do not make it.

STRICT RULES:
- Never reference media narratives, public sentiment, fan expectations, or team reputations
- Never use "dominant", "powerhouse", "struggling" unless directly supported by the numbers
- Never say "traditionally strong" or "historically tough" without citing actual H2H figures
- Never use gut feel, hype, or assumptions -- only the data below
- If two data points contradict each other, acknowledge the contradiction explicitly
- Uncertainty is acceptable and encouraged -- do not manufacture false confidence
- The betting market and Squiggle model are data inputs, not answers. Interrogate them.

=====================================
MATCH: {home} vs {away}
Round {match_data['round']} | {date} | {venue}
=====================================

--- LADDER STANDINGS ---
{home}: {format_ladder(match_data['home_ladder'])}
{away}: {format_ladder(match_data['away_ladder'])}

--- RECENT FORM (W/L with actual margins) ---
{home}: {format_form(match_data['home_form'])}
{away}: {format_form(match_data['away_form'])}

--- SCORING STATISTICS & TRENDS ---
{home}:
{format_scoring_stats(home_scoring, home)}

{away}:
{format_scoring_stats(away_scoring, away)}

--- REST DAYS & TRAVEL FATIGUE ---
{home} (Home):
  {format_rest_and_travel(home_rest, home_travel, home)}

{away} (Away):
  {format_rest_and_travel(away_rest, away_travel, away)}

--- HEAD TO HEAD (last 10 meetings) ---
{format_h2h(match_data['head_to_head'])}

--- HOME GROUND ADVANTAGE & VENUE RECORD ---
{format_home_advantage(match_data, home, away)}

--- BETTING MARKETS ---
{odds_text}

--- SQUIGGLE STATISTICAL MODEL ---
{squiggle_text}

--- WEATHER FORECAST ---
{weather_text}

--- TEAM NEWS ---
{team_news_text}

--- GENERAL AFL NEWS ---
{general_news_context[:800] if general_news_context else "None available."}

--- AGENT ACCURACY HISTORY ---
{history_text}

=====================================
OUTPUT INSTRUCTIONS
=====================================

Produce your output in the exact sections below. Each section heading is shown in bold.
The text in (parentheses) after a heading describes what to write — do NOT copy that
descriptive text into your output. Replace it with your actual analysis.

---

**PREDICTED WINNER:** (team name only — one of {home} or {away})

**WIN PROBABILITY:** (write as "{home}: XX% | {away}: XX%" where the two values sum to 100%.
Derive from a weighted blend of betting market, Squiggle model, and form data — do not simply
copy the market's implied probabilities, which include the bookmaker's overround and will not
sum to 100%. Then write one sentence stating which data inputs drove the probability and how
much weight you gave each source.)

**PREDICTED MARGIN:** (write as "~XX points". Anchor to the line market and scoring margin
averages. Then write one sentence justifying with specific numbers.)

**KEY FACTORS:** (3–4 numbered points. Each must cite a specific statistic from the data above
and explain its impact on this match. No vague statements.)

**SCORING TRENDS ANALYSIS:** (state the last-5 and last-3 averages for both teams. State
whether each team's attack and defence is trending up, down, or stable. State which team's
scoring profile gives them an advantage and why.)

**HOME GROUND ADVANTAGE:** (state each team's home/away win rate from the season data. State
each team's record at this specific venue. Estimate the point value of home advantage for this
match. If season data is unavailable, note it and use venue history only. Do not omit.)

**MARKET & MODEL ANALYSIS:** (state what the h2h market implies. State what the line market
implies. State what the Squiggle model predicts. Note whether they agree or disagree. If they
disagree, state which you weighted more heavily and why, with data.)

**FATIGUE & TRAVEL IMPACT:** (state exact days rest for each team. Flag any travel. State
whether fatigue is a real factor for this match. Do not omit — if no fatigue exists, say so.)

**WEATHER IMPACT:** (state the forecast. State whether conditions favour one team over the
other based on their scoring style. If neutral, say so.)

**TEAM NEWS IMPACT:** (list confirmed ins/outs and their positional impact. If no team news
is available, state that explicitly. Do not omit.)

**CONFIDENCE:** High / Medium / or Low — then one sentence referencing whether the data
sources agree or conflict.

**UPSET RISK:** Low / Medium / or High — then list specific data points that support an upset.
No hypotheticals — only factors visible in the data above.

**DATA CONFLICTS:** (list any cases where two data sources gave contradictory signals. If
none, write "None identified.")
"""

    return _call_ai_with_retry(prompt)


# ── Run all predictions ────────────────────────────────────────────────────────

def run_weekly_predictions(match_data_list: List[Dict], news_headlines: List[Dict]) -> List[Dict]:
    """Run predictions for all this week's matches and save to history."""
    if not match_data_list:
        return []

    general_news = "".join(
        f"- {item['title']}: {item['summary']}\n"
        for item in news_headlines[:10]
    )

    round_number = match_data_list[0].get("round")
    logger.info("Fetching Squiggle model predictions for Round %s", round_number)
    squiggle_tips = get_squiggle_tips(round_number=round_number)

    # Attach Squiggle tips to each match dict before spawning threads
    for match in match_data_list:
        match["squiggle_model"] = format_squiggle_tips_for_prompt(
            squiggle_tips, match["home_team"], match["away_team"]
        )

    def _predict_one(match: Dict) -> Dict:
        home = match["home_team"]
        away = match["away_team"]
        logger.info("Predicting: %s vs %s", home, away)
        prediction_text = generate_prediction(match, general_news)
        return {
            "round":        match.get("round"),
            "date":         match.get("date", ""),
            "date_full":    match.get("date_full", ""),
            "venue":        match.get("venue", ""),
            "home_team":    home,
            "away_team":    away,
            "betting_odds": match.get("betting_odds", {}),
            "home_scoring": match.get("home_scoring", {}),
            "away_scoring": match.get("away_scoring", {}),
            "home_rest":    match.get("home_rest",    {}),
            "away_rest":    match.get("away_rest",    {}),
            "home_travel":  match.get("home_travel",  {}),
            "away_travel":  match.get("away_travel",  {}),
            "home_ha_split":match.get("home_ha_split",{}),
            "away_ha_split":match.get("away_ha_split",{}),
            "prediction":   prediction_text,
        }

    # Run predictions sequentially with a small gap between requests.
    # Groq's free tier allows 6,000 tokens/minute; each prompt is ~3,000–4,000 tokens.
    # Firing 3+ requests simultaneously blows the TPM limit and causes rate-limit
    # errors, degraded responses, and prompt-echo artifacts in the output.
    # Sequential + 3 s gap keeps us well inside the limit at the cost of ~2 min
    # for a 9-game round — acceptable for a once-per-week task.
    all_predictions: List[Dict] = []
    for i, match in enumerate(match_data_list):
        if i > 0:
            time.sleep(3)   # respect Groq's 6,000 tokens/min rate limit
        try:
            all_predictions.append(_predict_one(match))
        except Exception as exc:
            logger.error("Prediction failed for %s vs %s: %s",
                         match.get("home_team"), match.get("away_team"), exc)

    # Use 'is not None' so Round 0 (falsy) is saved correctly
    if all_predictions and round_number is not None:
        logger.info("Saving Round %s predictions to history (%d matches)", round_number, len(all_predictions))
        try:
            save_predictions(all_predictions, round_number)
            logger.info("Successfully saved %d predictions", len(all_predictions))
        except Exception as e:
            logger.error("Failed to save predictions: %s", e)
            traceback.print_exc()
    else:
        logger.warning("Predictions not saved — all_predictions=%s, round_number=%s", bool(all_predictions), round_number)

    return all_predictions