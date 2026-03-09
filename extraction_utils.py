"""
extraction_utils.py
===================
Shared extraction functions for parsing AI prediction text.
Used by both app.py (UI) and pdf_export.py (PDF generation).

Eliminates code duplication and ensures consistent parsing logic.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def extract_confidence(text: str) -> str:
    """
    Extract confidence level from AI prediction text.

    Args:
        text: AI prediction text

    Returns:
        "High", "Medium", or "Low"
    """
    t = text.upper()
    if "CONFIDENCE:** HIGH" in t or "CONFIDENCE: HIGH" in t:
        return "High"
    if "CONFIDENCE:** LOW" in t or "CONFIDENCE: LOW" in t:
        return "Low"
    if "CONFIDENCE:** MEDIUM" in t or "CONFIDENCE: MEDIUM" in t or \
       "CONFIDENCE:** MODERATE" in t or "CONFIDENCE: MODERATE" in t:
        return "Medium"
    # Genuine parse failure — log so it surfaces during debugging
    if "CONFIDENCE" not in t:
        logger.warning("extract_confidence: no CONFIDENCE field found in prediction text")
    return "Medium"


def extract_winner(text: str, home_team: str, away_team: str) -> Optional[str]:
    """
    Extract predicted winner from AI prediction text.

    Matching strategy (most → least specific to avoid false positives):
      1. Full team name in the 120-char window after "PREDICTED WINNER:"
      2. Last word of team name (nickname) as a fallback

    Args:
        text: AI prediction text
        home_team: Home team name
        away_team: Away team name

    Returns:
        Team name or None if not found
    """
    t = text.upper()
    if "PREDICTED WINNER:" not in t:
        return None

    idx = t.index("PREDICTED WINNER:")
    snippet = t[idx:idx + 120]

    home_upper = home_team.upper()
    away_upper = away_team.upper()

    # --- Pass 1: full team name ---
    home_pos = snippet.find(home_upper)
    away_pos = snippet.find(away_upper)

    if home_pos != -1 and (away_pos == -1 or home_pos < away_pos):
        return home_team
    if away_pos != -1:
        return away_team

    # --- Pass 2: last word (nickname) fallback ---
    home_parts = home_team.split()
    away_parts = away_team.split()
    if not home_parts or not away_parts:
        return None

    home_nick = home_parts[-1].upper()
    away_nick = away_parts[-1].upper()

    home_pos = snippet.find(home_nick)
    away_pos = snippet.find(away_nick)

    if home_pos != -1 and (away_pos == -1 or home_pos < away_pos):
        return home_team
    if away_pos != -1:
        return away_team

    logger.warning("extract_winner: could not match either team in snippet: %r", snippet)
    return None


def extract_probability(text: str, winner: Optional[str]) -> Optional[float]:
    """
    Extract win probability percentage from AI prediction text.

    Searches within the 200-char window after "WIN PROBABILITY:" to avoid
    picking up unrelated percentages earlier in the text (e.g. attack stats).

    Args:
        text: AI prediction text
        winner: Predicted winner team name

    Returns:
        Probability as float (50-99) or None
    """
    if not winner:
        return None

    t_upper = text.upper()
    label = "WIN PROBABILITY:"
    search_text = text  # default: scan full text

    if label in t_upper:
        idx = t_upper.index(label)
        search_text = text[idx:idx + 200]

    matches = re.findall(r'(\d{2,3}(?:\.\d)?)\s*%', search_text)
    for m in matches:
        val = float(m)
        if 50 <= val <= 99:
            return val

    return None


def extract_margin(text: str) -> Optional[int]:
    """
    Extract predicted margin from AI prediction text.
    
    Args:
        text: AI prediction text
        
    Returns:
        Margin as integer (1-150) or None
    """
    # Look for patterns like "~25 points" or "25 pts"
    matches = re.findall(r'~?(\d{1,3})\s*(?:points?|pts)', text.lower())
    if matches:
        for m in matches:
            val = int(m)
            if 1 <= val <= 150:
                return val
    
    return None


def confidence_style(confidence: str) -> dict:
    """
    Get color styling for confidence level.
    
    Args:
        confidence: "High", "Medium", or "Low"
        
    Returns:
        Dict with 'color', 'bg', and 'label' keys
    """
    styles = {
        "High": {
            "color": "#3fb950",
            "bg": "rgba(63,185,80,0.06)",
            "label": "HIGH CONFIDENCE"
        },
        "Medium": {
            "color": "#d29922",
            "bg": "rgba(210,153,34,0.06)",
            "label": "MEDIUM CONFIDENCE"
        },
        "Low": {
            "color": "#f85149",
            "bg": "rgba(248,81,73,0.06)",
            "label": "LOW CONFIDENCE"
        },
    }
    
    return styles.get(confidence, styles["Medium"])
