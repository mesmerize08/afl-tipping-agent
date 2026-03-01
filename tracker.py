"""
tracker.py
==========
Manages the agent's prediction history and accuracy tracking.

How it works:
  1. Every time we make predictions, they're saved to predictions_history.json
  2. After each round completes, run check_results() to compare predictions vs actuals
  3. The accuracy data is fed back into future AI prompts so the agent learns
     which factors it's been good/bad at predicting

File stored: predictions_history.json (lives in your project folder, committed to GitHub)
"""

import json
import os
import requests
from datetime import datetime


HISTORY_FILE = "predictions_history.json"
SQUIGGLE_BASE = "https://api.squiggle.com.au/"


# ─── Load / Save History ───────────────────────────────────────────────────────

def load_history():
    """Load the full prediction history from disk."""
    if not os.path.exists(HISTORY_FILE):
        return {"predictions": [], "accuracy_summary": {}}
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"predictions": [], "accuracy_summary": {}}


def save_history(history):
    """Save the full prediction history to disk."""
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


# ─── Save New Predictions ──────────────────────────────────────────────────────

def save_predictions(predictions_list, round_number, year=2026):
    """
    Save this week's predictions to history.
    Call this right after generating predictions each week.
    """
    history = load_history()

    for pred in predictions_list:
        # Check if we already have this game saved
        existing = next((
            p for p in history["predictions"]
            if p["home_team"] == pred["home_team"]
            and p["away_team"] == pred["away_team"]
            and p["round"] == round_number
            and p["year"] == year
        ), None)

        if existing:
            print(f"  ℹ️  Prediction already saved for {pred['home_team']} vs {pred['away_team']}")
            continue

        # Extract predicted winner from AI text
        predicted_winner = extract_predicted_winner(
            pred["prediction"], pred["home_team"], pred["away_team"]
        )
        predicted_probability = extract_predicted_probability(
            pred["prediction"], predicted_winner
        )

        record = {
            "year": year,
            "round": round_number,
            "date": pred.get("date", ""),
            "venue": pred.get("venue", ""),
            "home_team": pred["home_team"],
            "away_team": pred["away_team"],
            "predicted_winner": predicted_winner,
            "predicted_probability": predicted_probability,
            "prediction_text": pred["prediction"],
            "actual_winner": None,       # Filled in after the game
            "actual_margin": None,       # Filled in after the game
            "correct": None,             # True/False after result
            "saved_at": datetime.now().isoformat()
        }

        history["predictions"].append(record)
        print(f"  ✅ Saved prediction: {pred['home_team']} vs {pred['away_team']} — tipped: {predicted_winner}")

    save_history(history)
    return history


# ─── Extract Predicted Winner from AI Text ────────────────────────────────────

def extract_predicted_winner(prediction_text, home_team, away_team):
    """
    Parse the AI's prediction text to extract the predicted winner.
    Looks for 'PREDICTED WINNER:' header in the AI response.

    Uses full team name matching (not last-word) to avoid collisions between
    teams that share a last word:
      Melbourne / North Melbourne  → both end in 'MELBOURNE'
      Adelaide  / Port Adelaide    → both end in 'ADELAIDE'
      Gold Coast / West Coast      → both end in 'COAST'
    """
    text       = prediction_text.upper()
    home_upper = home_team.upper()
    away_upper = away_team.upper()

    # Look for the predicted winner section
    if "PREDICTED WINNER" in text:
        idx     = text.index("PREDICTED WINNER")
        snippet = text[idx:idx + 200]

        # Search for full team names in the snippet (not just last word)
        home_pos = snippet.find(home_upper)
        away_pos = snippet.find(away_upper)

        if home_pos != -1 and (away_pos == -1 or home_pos < away_pos):
            return home_team
        elif away_pos != -1:
            return away_team

    # Fallback: count full team name mentions in first 300 chars
    snippet     = prediction_text[:300].upper()
    home_count  = snippet.count(home_upper)
    away_count  = snippet.count(away_upper)

    if home_count > away_count:
        return home_team
    elif away_count > home_count:
        return away_team

    return "Unknown"


def extract_predicted_probability(prediction_text, predicted_winner):
    """Extract the predicted win probability % from AI text."""
    import re
    # Look for patterns like "65%" or "65.0%"
    matches = re.findall(r'(\d{2,3}(?:\.\d)?)\s*%', prediction_text)
    if matches:
        # Return the first probability that's plausibly a win prob (50-99%)
        for m in matches:
            val = float(m)
            if 50 <= val <= 99:
                return val
    return None


# ─── Check Results After Round Completes ──────────────────────────────────────

def check_and_update_results(year=2026):
    """
    Fetch completed game results from Squiggle and update our history.
    Run this after each round finishes (Monday/Tuesday).
    Returns a summary of how we went this round.
    """
    history = load_history()
    updated_count = 0

    # Find predictions that don't have results yet
    pending = [p for p in history["predictions"] if p["correct"] is None and p["year"] == year]

    if not pending:
        print("No pending predictions to check.")
        return None

    # Fetch all completed games from Squiggle
    try:
        response = requests.get(f"{SQUIGGLE_BASE}?q=games;year={year}", timeout=10)
        all_games = response.json().get("games", [])
        completed_games = [g for g in all_games if g.get("complete") == 100]
    except Exception as e:
        print(f"Error fetching results: {e}")
        return None

    for pred in pending:
        # Find matching completed game
        match = next((
            g for g in completed_games
            if g.get("hteam") == pred["home_team"]
            and g.get("ateam") == pred["away_team"]
            and str(g.get("round")) == str(pred["round"])
        ), None)

        if not match:
            continue  # Game hasn't been played yet

        # Determine actual winner
        home_score = match.get("hscore", 0)
        away_score = match.get("ascore", 0)

        if home_score > away_score:
            actual_winner = pred["home_team"]
        elif away_score > home_score:
            actual_winner = pred["away_team"]
        else:
            actual_winner = "Draw"

        actual_margin = abs(home_score - away_score)
        correct = (pred["predicted_winner"] == actual_winner)

        # Update the record
        pred["actual_winner"] = actual_winner
        pred["actual_margin"] = actual_margin
        pred["correct"] = correct
        pred["result_checked_at"] = datetime.now().isoformat()

        updated_count += 1
        result_emoji = "✅" if correct else "❌"
        print(f"  {result_emoji} {pred['home_team']} vs {pred['away_team']}: "
              f"tipped {pred['predicted_winner']}, actual {actual_winner}")

    # Recalculate overall accuracy summary
    history["accuracy_summary"] = calculate_accuracy_summary(history["predictions"])

    save_history(history)
    print(f"\nUpdated {updated_count} results.")
    return history["accuracy_summary"]


# ─── Accuracy Calculations ─────────────────────────────────────────────────────

def calculate_accuracy_summary(predictions):
    """Calculate overall and per-round accuracy stats."""
    completed = [p for p in predictions if p["correct"] is not None]

    if not completed:
        return {}

    total = len(completed)
    correct = sum(1 for p in completed if p["correct"])

    # Per-round breakdown
    rounds = {}
    for p in completed:
        r = str(p["round"])
        if r not in rounds:
            rounds[r] = {"correct": 0, "total": 0}
        rounds[r]["total"] += 1
        if p["correct"]:
            rounds[r]["correct"] += 1

    # Favourite vs underdog accuracy
    # (where we picked the lower-probability team = underdog pick)
    upset_picks = [p for p in completed if p.get("predicted_probability") and p["predicted_probability"] < 55]
    favourite_picks = [p for p in completed if p.get("predicted_probability") and p["predicted_probability"] >= 55]

    return {
        "overall_correct": correct,
        "overall_total": total,
        "overall_accuracy_pct": round((correct / total) * 100, 1) if total > 0 else 0,
        "by_round": {
            r: {
                "correct": v["correct"],
                "total": v["total"],
                "pct": round((v["correct"] / v["total"]) * 100, 1)
            }
            for r, v in rounds.items()
        },
        "favourite_picks": {
            "correct": sum(1 for p in favourite_picks if p["correct"]),
            "total": len(favourite_picks)
        },
        "upset_picks": {
            "correct": sum(1 for p in upset_picks if p["correct"]),
            "total": len(upset_picks)
        },
        "last_updated": datetime.now().isoformat()
    }


# ─── Format History for AI Prompt ─────────────────────────────────────────────

def format_history_for_ai(home_team, away_team, max_season_records=15):
    """
    Format the agent's own prediction history into a context block
    that gets injected into the AI prompt. This lets the AI:
      1. Know its own accuracy so far this season
      2. Review its past predictions for these two specific teams
      3. Learn from rounds where it was wrong
    """
    history = load_history()
    predictions = history.get("predictions", [])
    accuracy = history.get("accuracy_summary", {})

    if not predictions:
        return "No prediction history yet — this is the first round of the season."

    sections = []

    # ── Overall accuracy this season ──
    if accuracy:
        sections.append("📊 AGENT'S OWN ACCURACY THIS SEASON:")
        sections.append(
            f"  Overall: {accuracy.get('overall_correct', 0)}/{accuracy.get('overall_total', 0)} "
            f"({accuracy.get('overall_accuracy_pct', 0)}% correct)"
        )

        fav = accuracy.get("favourite_picks", {})
        if fav.get("total", 0) > 0:
            fav_pct = round((fav["correct"] / fav["total"]) * 100, 1)
            sections.append(f"  Favourite picks: {fav['correct']}/{fav['total']} ({fav_pct}%)")

        upset = accuracy.get("upset_picks", {})
        if upset.get("total", 0) > 0:
            upset_pct = round((upset["correct"] / upset["total"]) * 100, 1)
            sections.append(f"  Underdog picks: {upset['correct']}/{upset['total']} ({upset_pct}%)")

        # Recent round-by-round
        by_round = accuracy.get("by_round", {})
        if by_round:
            recent_rounds = sorted(by_round.keys(), key=lambda x: int(x))[-3:]
            round_summary = ", ".join(
                f"Rd {r}: {by_round[r]['correct']}/{by_round[r]['total']}"
                for r in recent_rounds
            )
            sections.append(f"  Recent rounds: {round_summary}")

    # ── Past predictions involving these two teams ──
    team_history = [
        p for p in predictions
        if (p["home_team"] in [home_team, away_team] or p["away_team"] in [home_team, away_team])
        and p["correct"] is not None
    ]
    team_history.sort(key=lambda x: (x.get("year", 0), int(x.get("round", 0))), reverse=True)

    if team_history:
        sections.append(f"\n🔍 AGENT'S PAST PREDICTIONS INVOLVING {home_team.upper()} OR {away_team.upper()}:")
        for p in team_history[:6]:
            result = "✅ CORRECT" if p["correct"] else "❌ WRONG"
            sections.append(
                f"  Rd {p['round']}: {p['home_team']} vs {p['away_team']} — "
                f"tipped {p['predicted_winner']} "
                f"({'%.0f' % p['predicted_probability']}% confidence) — "
                f"{result} (actual winner: {p['actual_winner']})"
            )

    # ── Recent wrong predictions (for calibration) ──
    wrong_recent = [
        p for p in predictions
        if p["correct"] is False
    ]
    wrong_recent.sort(key=lambda x: (x.get("year", 0), int(x.get("round", 0))), reverse=True)

    if wrong_recent[:4]:
        sections.append(f"\n⚠️  RECENT INCORRECT PREDICTIONS (use these to recalibrate):")
        for p in wrong_recent[:4]:
            sections.append(
                f"  Rd {p['round']}: Tipped {p['predicted_winner']} over "
                f"{p['actual_winner']} — actual winner won by {p.get('actual_margin', '?')} pts"
            )

    return "\n".join(sections)


# ─── Display Summary (for app.py) ─────────────────────────────────────────────

def get_accuracy_display_data():
    """
    Returns structured data for the Streamlit accuracy dashboard.
    """
    history = load_history()
    predictions = history.get("predictions", [])
    accuracy = history.get("accuracy_summary", {})

    completed = [p for p in predictions if p["correct"] is not None]
    pending = [p for p in predictions if p["correct"] is None]

    return {
        "accuracy_summary": accuracy,
        "completed_predictions": completed,
        "pending_predictions": pending,
        "all_predictions": predictions
    }
