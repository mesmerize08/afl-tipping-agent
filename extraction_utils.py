"""
extraction_utils.py
===================
Shared extraction functions for parsing AI prediction text.
Used by both app.py (UI) and pdf_export.py (PDF generation).

Eliminates code duplication and ensures consistent parsing logic.
"""

import re
from typing import Optional


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
    return "Medium"


def extract_winner(text: str, home_team: str, away_team: str) -> Optional[str]:
    """
    Extract predicted winner from AI prediction text.
    
    Args:
        text: AI prediction text
        home_team: Home team name
        away_team: Away team name
        
    Returns:
        Team name or None if not found
    """
    t = text.upper()
    if "PREDICTED WINNER:" in t:
        idx = t.index("PREDICTED WINNER:")
        snippet = t[idx:idx + 120]
        
        # Use last word of team name (e.g., "Lions", "Tigers")
        home_pos = snippet.find(home_team.upper().split()[-1])
        away_pos = snippet.find(away_team.upper().split()[-1])
        
        if home_pos != -1 and (away_pos == -1 or home_pos < away_pos):
            return home_team
        if away_pos != -1:
            return away_team
    
    return None


def extract_probability(text: str, winner: Optional[str]) -> Optional[float]:
    """
    Extract win probability percentage from AI prediction text.
    
    Args:
        text: AI prediction text
        winner: Predicted winner team name
        
    Returns:
        Probability as float (50-99) or None
    """
    if not winner:
        return None
    
    # Look for patterns like "65%" or "65.0%"
    matches = re.findall(r'(\d{2,3}(?:\.\d)?)\s*%', text)
    if matches:
        # Return first probability that's plausibly a win prob (50-99%)
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
