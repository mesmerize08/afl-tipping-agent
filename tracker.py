"""
tracker.py (COMPLETE FIX - Extraction + Team Name Normalization)
==================================================================
Manages prediction history and accuracy tracking.
"""

import base64
import json
import logging
import os
import shutil
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Import shared extraction utilities
from extraction_utils import extract_winner, extract_probability

logger = logging.getLogger(__name__)

_HERE = Path(__file__).parent
HISTORY_FILE = str(_HERE / "predictions_history.json")
BACKUP_FILE  = str(_HERE / "predictions_history.json.backup")
SQUIGGLE_BASE = "https://api.squiggle.com.au/"


# ─── Team Name Normalization ───────────────────────────────────────────────────

def normalize_team_name(team_name: str) -> str:
    """
    Normalize team names to handle variations between data sources.
    Squiggle API uses different names than what might be in predictions.
    """
    team_map = {
        # Adelaide
        "adelaide": "Adelaide",
        "crows": "Adelaide",
        "adelaide crows": "Adelaide",
        
        # Brisbane
        "brisbane": "Brisbane Lions",
        "brisbane lions": "Brisbane Lions",
        "lions": "Brisbane Lions",
        
        # Carlton
        "carlton": "Carlton",
        "blues": "Carlton",
        
        # Collingwood
        "collingwood": "Collingwood",
        "magpies": "Collingwood",
        "pies": "Collingwood",
        
        # Essendon
        "essendon": "Essendon",
        "bombers": "Essendon",
        
        # Fremantle
        "fremantle": "Fremantle",
        "dockers": "Fremantle",
        
        # Geelong
        "geelong": "Geelong",
        "cats": "Geelong",
        "geelong cats": "Geelong",
        
        # Gold Coast
        "gold coast": "Gold Coast",
        "suns": "Gold Coast",
        "gold coast suns": "Gold Coast",
        
        # GWS Giants
        "gws": "GWS Giants",
        "gws giants": "GWS Giants",
        "greater western sydney": "GWS Giants",
        "giants": "GWS Giants",
        
        # Hawthorn
        "hawthorn": "Hawthorn",
        "hawks": "Hawthorn",
        
        # Melbourne
        "melbourne": "Melbourne",
        "demons": "Melbourne",
        
        # North Melbourne
        "north melbourne": "North Melbourne",
        "kangaroos": "North Melbourne",
        "roos": "North Melbourne",
        "north": "North Melbourne",
        
        # Port Adelaide
        "port adelaide": "Port Adelaide",
        "power": "Port Adelaide",
        "port": "Port Adelaide",
        
        # Richmond
        "richmond": "Richmond",
        "tigers": "Richmond",
        
        # St Kilda
        "st kilda": "St Kilda",
        "saints": "St Kilda",
        
        # Sydney
        "sydney": "Sydney",
        "swans": "Sydney",
        "sydney swans": "Sydney",
        
        # West Coast
        "west coast": "West Coast",
        "eagles": "West Coast",
        "west coast eagles": "West Coast",
        
        # Western Bulldogs
        "western bulldogs": "Western Bulldogs",
        "bulldogs": "Western Bulldogs",
        "dogs": "Western Bulldogs",
    }
    
    # Handle None or non-string values
    if not team_name:
        return ""
    
    normalized = team_name.lower().strip()
    result = team_map.get(normalized)
    if result is None:
        logger.warning("normalize_team_name: unknown team name %r — returning as-is", team_name)
        return team_name
    return result


# ─── Fix Existing Predictions ──────────────────────────────────────────────────

def fix_existing_predictions() -> Dict[str, Any]:
    """
    One-time fix for existing predictions with 'Unknown' winners.
    Re-extracts winners and probabilities from prediction text.
    Returns summary of what was fixed.
    """
    history = load_history()
    predictions = history.get("predictions", [])
    
    fixed_count = 0
    already_good = 0
    no_text = 0
    
    for pred in predictions:
        # Skip if already has a valid winner
        if pred.get("predicted_winner") and pred.get("predicted_winner") != "Unknown":
            already_good += 1
            continue
        
        # Get prediction text
        prediction_text = pred.get("prediction_text", "")
        if not prediction_text:
            no_text += 1
            continue
        
        # Re-extract using extraction_utils
        home = pred.get("home_team", "")
        away = pred.get("away_team", "")
        
        if not home or not away:
            continue
        
        new_winner = extract_winner(prediction_text, home, away)
        new_prob = extract_probability(prediction_text, new_winner)
        
        # Update prediction
        old_winner = pred.get("predicted_winner")
        old_prob = pred.get("predicted_probability")
        
        if new_winner != old_winner or new_prob != old_prob:
            pred["predicted_winner"] = new_winner
            pred["predicted_probability"] = new_prob
            fixed_count += 1
    
    # Save if we fixed anything
    if fixed_count > 0:
        save_history(history)
    
    return {
        "fixed": fixed_count,
        "already_good": already_good,
        "no_text": no_text,
        "total": len(predictions)
    }


# ─── Load / Save History with Backup Protection ───────────────────────────────

def load_history() -> Dict[str, Any]:
    """Load prediction history with JSON validation and backup recovery."""
    if not os.path.exists(HISTORY_FILE):
        return {"predictions": [], "accuracy_summary": {}}
    
    try:
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
        
        if not isinstance(history, dict):
            raise ValueError("History is not a dict")
        if "predictions" not in history:
            history["predictions"] = []
        if "accuracy_summary" not in history:
            history["accuracy_summary"] = {}
        
        return history
        
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("History file corrupted: %s", e)

        if os.path.exists(BACKUP_FILE):
            logger.info("Attempting recovery from backup...")
            try:
                with open(BACKUP_FILE, "r") as f:
                    history = json.load(f)
                logger.info("Recovered from backup successfully")
                return history
            except Exception:
                pass

        logger.warning("Starting with empty history")
        return {"predictions": [], "accuracy_summary": {}}


def save_history(history: Dict[str, Any]) -> None:
    """Save history with automatic backup and atomic write, then sync to GitHub."""
    if os.path.exists(HISTORY_FILE):
        try:
            shutil.copy2(HISTORY_FILE, BACKUP_FILE)
        except Exception as e:
            logger.warning("Could not create backup: %s", e)

    temp_file = f"{HISTORY_FILE}.tmp"
    try:
        with open(temp_file, "w") as f:
            json.dump(history, f, indent=2)

        with open(temp_file, "r") as f:
            json.load(f)

        shutil.move(temp_file, HISTORY_FILE)

    except Exception as e:
        logger.error("Save failed: %s", e)

        if os.path.exists(temp_file):
            os.remove(temp_file)

        if os.path.exists(BACKUP_FILE):
            logger.info("Restoring from backup...")
            shutil.copy2(BACKUP_FILE, HISTORY_FILE)

        raise

    # Persist to GitHub so state survives Streamlit Cloud restarts
    _push_history_to_github(history)


def _push_history_to_github(history: Dict[str, Any]) -> bool:
    """
    Push predictions_history.json to the GitHub repo via the Contents API.

    This is the only way to survive Streamlit Cloud's ephemeral filesystem —
    on every restart the app reads from the repo, not local disk.

    Requires:
      GITHUB_TOKEN  — Personal Access Token with 'repo' (or 'contents:write') scope
    Optional:
      GITHUB_REPO   — defaults to mesmerize08/afl-tipping-agent
      GITHUB_BRANCH — defaults to main
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        logger.debug("GITHUB_TOKEN not set — skipping GitHub sync")
        return False

    repo   = os.getenv("GITHUB_REPO",   "mesmerize08/afl-tipping-agent")
    branch = os.getenv("GITHUB_BRANCH", "main")
    path   = "predictions_history.json"
    api_url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept":        "application/vnd.github.v3+json",
    }

    try:
        # GitHub requires the current file SHA to update an existing file
        r = requests.get(api_url, headers=headers, params={"ref": branch}, timeout=10)
        r.raise_for_status()
        sha = r.json().get("sha")

        content_b64 = base64.b64encode(
            json.dumps(history, indent=2).encode("utf-8")
        ).decode("ascii")

        payload = {
            "message": f"chore: auto-update predictions history [{datetime.now().strftime('%Y-%m-%d')}]",
            "content": content_b64,
            "sha":     sha,
            "branch":  branch,
        }
        r = requests.put(api_url, headers=headers, json=payload, timeout=15)
        r.raise_for_status()
        logger.info("predictions_history.json synced to GitHub")
        return True

    except Exception as e:
        logger.warning("GitHub sync failed (data saved locally): %s", e)
        return False


# ─── Save New Predictions ──────────────────────────────────────────────────────

def save_predictions(predictions_list: List[Dict], round_number: int, year: Optional[int] = None) -> Dict:
    """Save predictions to history with proper extraction."""
    if year is None:
        year = datetime.now().year
    
    history = load_history()
    
    for pred in predictions_list:
        existing = next((
            p for p in history["predictions"]
            if p["home_team"] == pred["home_team"]
            and p["away_team"] == pred["away_team"]
            and p["round"] == round_number
            and p["year"] == year
        ), None)
        
        if existing:
            logger.info("Already saved: %s vs %s", pred["home_team"], pred["away_team"])
            continue
        
        prediction_text = pred.get("prediction", "")
        predicted_winner = extract_winner(
            prediction_text,
            pred["home_team"],
            pred["away_team"]
        )
        predicted_probability = extract_probability(
            prediction_text,
            predicted_winner
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
            "prediction_text": prediction_text,
            "actual_winner": None,
            "actual_margin": None,
            "correct": None,
            "saved_at": datetime.now().isoformat()
        }
        
        history["predictions"].append(record)
        
        prob_str = f"{predicted_probability:.0f}%" if predicted_probability else "?"
        logger.info("Saved: %s vs %s → %s (%s)", pred["home_team"], pred["away_team"], predicted_winner, prob_str)
    
    save_history(history)
    return history


# ─── Check Results After Round Completes ──────────────────────────────────────

def check_and_update_results(year: Optional[int] = None) -> Optional[Dict]:
    """
    Fetch results and update history with team name normalization.
    Run after each round completes.
    """
    history = load_history()
    updated_count = 0

    if year is None:
        year = datetime.now().year

    pending = [p for p in history["predictions"] if p["correct"] is None and p["year"] == year]

    if not pending:
        logger.info("No pending predictions to check")
        return None

    _UA = {"User-Agent": "AFL-Tipping-Agent/1.0 (github.com/mesmerize08/afl-tipping-agent)"}

    # Collect completed games from Squiggle.
    # Strategy: query each pending round explicitly (round 0 / Opening Round is not
    # reliably returned by ?q=games;year=X), then also try the general year query.
    pending_rounds = sorted({p["round"] for p in pending})
    seen_ids: set = set()
    all_games: List[Dict] = []

    def _fetch(url: str) -> List[Dict]:
        try:
            r = requests.get(url, timeout=10, headers=_UA)
            r.raise_for_status()
            return r.json().get("games", [])
        except Exception as exc:
            logger.warning("Squiggle fetch failed for %s: %s", url, exc)
            return []

    # Round-specific queries first (most reliable for round 0)
    for rnd in pending_rounds:
        for game in _fetch(f"{SQUIGGLE_BASE}?q=games;year={year};round={rnd}"):
            gid = game.get("id")
            if gid not in seen_ids:
                seen_ids.add(gid)
                all_games.append(game)

    # General year query as a supplement
    for game in _fetch(f"{SQUIGGLE_BASE}?q=games;year={year}"):
        gid = game.get("id")
        if gid not in seen_ids:
            seen_ids.add(gid)
            all_games.append(game)

    # Accept complete == 100 as int, float, or string
    completed_games = [g for g in all_games if str(g.get("complete", "")).split(".")[0] == "100"]
    logger.info("Found %d completed games across rounds %s", len(completed_games), pending_rounds)
    
    for pred in pending:
        # Normalize team names for matching
        pred_home = normalize_team_name(pred["home_team"])
        pred_away = normalize_team_name(pred["away_team"])
        
        # Find matching completed game
        match = next((
            g for g in completed_games
            if normalize_team_name(g.get("hteam", "")) == pred_home
            and normalize_team_name(g.get("ateam", "")) == pred_away
            and str(g.get("round")) == str(pred["round"])
        ), None)
        
        if not match:
            continue
        
        # Determine actual winner
        home_score = match.get("hscore", 0)
        away_score = match.get("ascore", 0)
        
        if home_score > away_score:
            actual_winner = pred["home_team"]
            actual_margin = home_score - away_score
        else:
            actual_winner = pred["away_team"]
            actual_margin = away_score - home_score
        
        # Check if prediction was correct (normalize for comparison)
        predicted_winner_norm = normalize_team_name(pred.get("predicted_winner", ""))
        actual_winner_norm = normalize_team_name(actual_winner)
        is_correct = (predicted_winner_norm == actual_winner_norm)
        
        # Update prediction
        pred["actual_winner"] = actual_winner
        pred["actual_margin"] = actual_margin
        pred["correct"] = is_correct
        pred["checked_at"] = datetime.now().isoformat()
        
        status = "correct" if is_correct else "incorrect"
        logger.info("%s vs %s: tipped %s, actual %s (%s)",
                    pred["home_team"], pred["away_team"], pred["predicted_winner"], actual_winner, status)
        
        updated_count += 1
    
    if updated_count > 0:
        accuracy_summary = calculate_accuracy_summary(history["predictions"])
        history["accuracy_summary"] = accuracy_summary
        
        save_history(history)
        logger.info("Updated %d predictions", updated_count)
        
        return accuracy_summary
    
    return None


# ─── Calculate Accuracy Summary ───────────────────────────────────────────────

def calculate_accuracy_summary(predictions: List[Dict]) -> Dict:
    """Calculate overall and round-by-round accuracy."""
    completed = [p for p in predictions if p["correct"] is not None]
    
    if not completed:
        return {}
    
    correct = sum(1 for p in completed if p["correct"])
    total = len(completed)
    
    rounds = {}
    for p in completed:
        r = str(p["round"])
        if r not in rounds:
            rounds[r] = {"correct": 0, "total": 0}
        rounds[r]["total"] += 1
        if p["correct"]:
            rounds[r]["correct"] += 1
    
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

def format_history_for_ai(home_team: str, away_team: str, max_season_records: int = 15) -> str:
    """Format prediction history for AI prompt."""
    history = load_history()
    predictions = history.get("predictions", [])
    accuracy = history.get("accuracy_summary", {})
    
    if not predictions:
        return "No prediction history yet — this is the first round of the season."
    
    sections = []
    
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
        
        by_round = accuracy.get("by_round", {})
        if by_round:
            recent_rounds = sorted(by_round.keys(), key=lambda x: int(x))[-3:]
            round_summary = ", ".join(
                f"Rd {r}: {by_round[r]['correct']}/{by_round[r]['total']}"
                for r in recent_rounds
            )
            sections.append(f"  Recent rounds: {round_summary}")
    
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
            prob_str = f"{p['predicted_probability']:.0f}" if p.get("predicted_probability") else "?"
            sections.append(
                f"  Rd {p['round']}: {p['home_team']} vs {p['away_team']} — "
                f"tipped {p['predicted_winner']} ({prob_str}% confidence) -- "
                f"{result} (actual winner: {p['actual_winner']})"
            )
    
    wrong_recent = [p for p in predictions if p["correct"] is False]
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

def get_accuracy_display_data() -> Dict:
    """Returns structured data for Streamlit accuracy dashboard."""
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
