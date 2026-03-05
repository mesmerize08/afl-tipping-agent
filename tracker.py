"""
tracker.py (OPTIMIZED — Uses extraction_utils, backup protection)
===================================================================
Manages prediction history and accuracy tracking with automatic backup.
"""

import json
import os
import shutil
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import shared extraction utilities
from extraction_utils import extract_winner, extract_probability

HISTORY_FILE = "predictions_history.json"
BACKUP_FILE = "predictions_history.json.backup"
SQUIGGLE_BASE = "https://api.squiggle.com.au/"


# ─── Load / Save History with Backup Protection ───────────────────────────────

def load_history() -> Dict[str, Any]:
    """
    Load prediction history with JSON validation and backup recovery.
    """
    if not os.path.exists(HISTORY_FILE):
        return {"predictions": [], "accuracy_summary": {}}
    
    try:
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
        
        # Validate structure
        if not isinstance(history, dict):
            raise ValueError("History is not a dict")
        if "predictions" not in history:
            history["predictions"] = []
        if "accuracy_summary" not in history:
            history["accuracy_summary"] = {}
        
        return history
        
    except (json.JSONDecodeError, ValueError) as e:
        print(f"  ⚠️  History file corrupted: {e}")
        
        # Try to recover from backup
        if os.path.exists(BACKUP_FILE):
            print(f"  🔄 Attempting recovery from backup...")
            try:
                with open(BACKUP_FILE, "r") as f:
                    history = json.load(f)
                print(f"  ✅ Recovered from backup!")
                return history
            except Exception:
                pass
        
        print(f"  ⚠️  Starting with empty history")
        return {"predictions": [], "accuracy_summary": {}}


def save_history(history: Dict[str, Any]) -> None:
    """
    Save history with automatic backup and atomic write.
    """
    # Create backup of existing file
    if os.path.exists(HISTORY_FILE):
        try:
            shutil.copy2(HISTORY_FILE, BACKUP_FILE)
        except Exception as e:
            print(f"  ⚠️  Could not create backup: {e}")
    
    # Write to temporary file first
    temp_file = f"{HISTORY_FILE}.tmp"
    try:
        with open(temp_file, "w") as f:
            json.dump(history, f, indent=2)
        
        # Validate temp file
        with open(temp_file, "r") as f:
            json.load(f)
        
        # Move temp to actual file (atomic on Unix)
        shutil.move(temp_file, HISTORY_FILE)
        
    except Exception as e:
        print(f"  ❌ Save failed: {e}")
        
        # Clean up temp file
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        # Restore from backup if save failed
        if os.path.exists(BACKUP_FILE):
            print(f"  🔄 Restoring from backup...")
            shutil.copy2(BACKUP_FILE, HISTORY_FILE)
        
        raise


# ─── Save New Predictions ──────────────────────────────────────────────────────

def save_predictions(predictions_list: List[Dict], round_number: int, year: Optional[int] = None) -> Dict:
    """
    Save predictions to history with proper extraction.
    """
    if year is None:
        year = datetime.now().year
    
    history = load_history()
    
    for pred in predictions_list:
        # Check if already saved
        existing = next((
            p for p in history["predictions"]
            if p["home_team"] == pred["home_team"]
            and p["away_team"] == pred["away_team"]
            and p["round"] == round_number
            and p["year"] == year
        ), None)
        
        if existing:
            print(f"  ℹ️  Already saved: {pred['home_team']} vs {pred['away_team']}")
            continue
        
        # Extract predicted winner and probability using extraction_utils
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
        print(f"  ✅ Saved: {pred['home_team']} vs {pred['away_team']} → {predicted_winner} ({prob_str})")
    
    save_history(history)
    return history


# ─── Check Results After Round Completes ──────────────────────────────────────

def check_and_update_results(year: Optional[int] = None) -> Optional[Dict]:
    """
    Fetch results and update history. Run after each round completes.
    """
    history = load_history()
    updated_count = 0
    
    if year is None:
        year = datetime.now().year
    
    pending = [p for p in history["predictions"] if p["correct"] is None and p["year"] == year]
    
    if not pending:
        print("No pending predictions to check.")
        return None
    
    # Fetch completed games from Squiggle
    _UA = {"User-Agent": "AFL-Tipping-Agent/1.0 (github.com/mesmerize08/afl-tipping-agent)"}
    try:
        response = requests.get(
            f"{SQUIGGLE_BASE}?q=games;year={year}",
            timeout=10,
            headers=_UA
        )
        response.raise_for_status()
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
        
        # Update prediction
        pred["actual_winner"] = actual_winner
        pred["actual_margin"] = actual_margin
        pred["correct"] = (pred["predicted_winner"] == actual_winner)
        pred["checked_at"] = datetime.now().isoformat()
        
        result_emoji = "✅" if pred["correct"] else "❌"
        print(f"{result_emoji} {pred['home_team']} vs {pred['away_team']}: "
              f"Tipped {pred['predicted_winner']}, actual {actual_winner}")
        
        updated_count += 1
    
    if updated_count > 0:
        # Recalculate accuracy summary
        accuracy_summary = calculate_accuracy_summary(history["predictions"])
        history["accuracy_summary"] = accuracy_summary
        
        save_history(history)
        print(f"\n✅ Updated {updated_count} predictions")
        
        return accuracy_summary
    
    return None


# ─── Calculate Accuracy Summary ───────────────────────────────────────────────

def calculate_accuracy_summary(predictions: List[Dict]) -> Dict:
    """
    Calculate overall and round-by-round accuracy.
    """
    completed = [p for p in predictions if p["correct"] is not None]
    
    if not completed:
        return {}
    
    correct = sum(1 for p in completed if p["correct"])
    total = len(completed)
    
    # By round
    rounds = {}
    for p in completed:
        r = str(p["round"])
        if r not in rounds:
            rounds[r] = {"correct": 0, "total": 0}
        rounds[r]["total"] += 1
        if p["correct"]:
            rounds[r]["correct"] += 1
    
    # Favourite vs underdog
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
    """
    Format prediction history for AI prompt.
    """
    history = load_history()
    predictions = history.get("predictions", [])
    accuracy = history.get("accuracy_summary", {})
    
    if not predictions:
        return "No prediction history yet — this is the first round of the season."
    
    sections = []
    
    # Overall accuracy
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
    
    # Past predictions for these teams
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
    
    # Recent wrong predictions
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
    """
    Returns structured data for Streamlit accuracy dashboard.
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
