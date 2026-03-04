"""
pdf_export.py (OPTIMIZED — Uses extraction_utils, no duplication)
===================================================================
White paper, dark ink, print-ready layout.
Requires: fpdf2
"""

import re
from fpdf import FPDF
from datetime import datetime
from typing import List, Dict
from extraction_utils import (  # NEW: Import from shared module
    extract_confidence,
    extract_winner,
    extract_probability,
    extract_margin
)

# ── Unicode sanitiser ─────────────────────────────────────────────────────────
_UMAP = {
    "\u2014": "--",  "\u2013": "-",   "\u2012": "-",   "\u2011": "-",  "\u2010": "-",
    "\u2018": "'",   "\u2019": "'",   "\u201c": '"',   "\u201d": '"',
    "\u2022": "-",   "\u2026": "...", "\u2192": "->",  "\u2190": "<-",
    "\u2191": "^",   "\u2193": "v",   "\u25b2": "^",   "\u25bc": "v",
    "\u2248": "~",   "\u2260": "!=",  "\u2265": ">=",  "\u2264": "<=",
    "\u00b7": ".",   "\u2500": "-",   "\u2501": "-",   "\u2502": "|",
    "\u2503": "|",   "\u2550": "=",   "\u2551": "|",   "\u2580": " ",
    "\u2588": "#",   "\u2591": " ",   "\u2592": " ",   "\u26a1": ">>",
    "\u2705": "[Y]", "\u274c": "[N]", "\u26a0": "[!]", "\u2713": "OK",
    "\u2717": "X",   "\u2714": "OK",  "\u2764": "<3",  "\u2b50": "*",
}
_TRANS = str.maketrans(_UMAP)


def _safe(v) -> str:
    """Sanitise any value to a Latin-1-safe string for Helvetica."""
    s = str(v) if v is not None else ""
    s = s.translate(_TRANS)
    return s.encode("latin-1", errors="ignore").decode("latin-1")


def _clean(text: str) -> str:
    """Strip markdown bold/italic markers and sanitise unicode."""
    text = re.sub(r"\*{1,3}([^*\n]+)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,2}([^_\n]+)_{1,2}", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return _safe(text).strip()


# ── Colour palette — white paper ──────────────────────────────────────────────
WHITE      = (255, 255, 255)
ROW_ALT    = (245, 247, 250)
LIGHT_GRAY = (240, 243, 247)
MID_GRAY   = (220, 225, 230)
RULE_GRAY  = (200, 205, 210)

INK        = (20,  25,  30)     # near-black body text
SUB        = (75,  85,  100)    # secondary / muted text
CAP        = (140, 150, 160)    # captions

NAVY       = (18,  45,  85)     # header banner
GOLD       = (160, 110, 20)     # gold on white
GOLD_BG    = (255, 245, 215)

G_INK      = (25,  120, 50)     # green on white
G_BG       = (225, 248, 230)
A_INK      = (155,  95, 10)     # amber on white
A_BG       = (255, 240, 205)
R_INK      = (180,  35, 30)     # red on white
R_BG       = (255, 228, 225)


def _cc(conf: str) -> tuple:
    """Get color tuple for confidence level."""
    return {
        "High":   (G_INK, G_BG),
        "Medium": (A_INK, A_BG),
        "Low":    (R_INK, R_BG),
    }.get(conf, (A_INK, A_BG))


# ── PDF class ─────────────────────────────────────────────────────────────────

class TipsPDF(FPDF):
    """
    AFL Tipping Agent PDF — white paper, print-optimised.
    cell() and multi_cell() are overridden so _safe() runs on all text.
    """

    def __init__(self, round_num: int, generated_at: str):
        super().__init__()
        self.round_num    = round_num
        self.generated_at = _safe(generated_at)
        self.set_auto_page_break(True, margin=22)
        self.set_margins(14, 28, 14)
        self.add_page()

    # Sanitise every string before it reaches the font
    def cell(self, w=0, h=0, txt="", border=0, ln=0,
             align="", fill=False, link=""):
        return super().cell(w, h, _safe(txt), border, ln, align, fill, link)

    def multi_cell(self, w, h, txt="", border=0, align="J",
                   fill=False, split_only=False, link="", **kw):
        return super().multi_cell(
            w, h, _safe(txt), border, align, fill,
            split_only=split_only, link=link
        )

    def header(self):
        # Navy banner
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 19, "F")
        # Gold underline stripe
        self.set_fill_color(*GOLD)
        self.rect(0, 19, 210, 2.5, "F")

        self.set_xy(14, 3)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(255, 255, 255)
        super().cell(130, 8, f"AFL TIPPING AGENT  |  ROUND {self.round_num}", ln=False)

        self.set_font("Helvetica", "", 7)
        self.set_text_color(190, 205, 220)
        super().cell(0, 8, f"Generated: {self.generated_at}", align="R", ln=True)

        self.set_xy(14, 12)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(170, 185, 205)
        super().cell(
            0, 5,
            "Data-driven  .  Unbiased  .  AI-powered  .  For entertainment only",
            ln=True
        )
        self.set_text_color(*INK)
        self.ln(7)

    def footer(self):
        self.set_y(-14)
        self.set_draw_color(*RULE_GRAY)
        self.line(14, self.get_y(), 196, self.get_y())
        self.ln(1)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*CAP)
        super().cell(
            0, 6,
            f"AFL Tipping Agent  |  Round {self.round_num}  |  "
            f"Page {self.page_no()}  |  "
            "For entertainment only. Please gamble responsibly.",
            align="C"
        )

    def _rule(self, color=None):
        self.set_draw_color(*(color or RULE_GRAY))
        self.line(14, self.get_y(), 196, self.get_y())
        self.ln(3)

    def _section_label(self, title: str):
        self.set_fill_color(*GOLD_BG)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*GOLD)
        self.set_x(14)
        super().cell(182, 6, f"  {title}", fill=True, ln=True)
        self.ln(2)

    def write_summary_table(self, predictions: List[Dict]):
        self._section_label("ROUND SUMMARY -- ALL TIPS AT A GLANCE")

        # Column widths — must sum to 182
        CW   = [55, 28, 24, 38, 13, 16, 8]
        HDRS = ["MATCH", "VENUE", "DATE", "TIP", "PROB", "MARGIN", ""]

        # Header row
        self.set_fill_color(*NAVY)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 7.5)
        self.set_x(14)
        for w, h in zip(CW, HDRS):
            super().cell(w, 8, f"  {h}" if h else "", fill=True, border=0)
        self.ln(8)

        alt = False
        for pred in predictions:
            home = _safe(pred.get("home_team", ""))
            away = _safe(pred.get("away_team", ""))
            text = pred.get("prediction", "")
            
            # Use extraction_utils functions
            conf = extract_confidence(text)
            win  = extract_winner(text, pred.get("home_team", ""), pred.get("away_team", ""))
            prob = extract_probability(text, win)
            mar  = extract_margin(text)
            c_ink, c_bg = _cc(conf)

            # Alternating row backgrounds
            self.set_fill_color(*(ROW_ALT if alt else WHITE))
            alt = not alt
            self.set_x(14)

            # Match name
            self.set_font("Helvetica", "B", 8)
            self.set_text_color(*INK)
            super().cell(CW[0], 9, f"  {home} vs {away}"[:28], fill=True)

            # Venue + Date
            self.set_font("Helvetica", "", 7.5)
            self.set_text_color(*SUB)
            super().cell(CW[1], 9, _safe(pred.get("venue", ""))[:14],
                         fill=True, align="C")
            super().cell(CW[2], 9, _safe(pred.get("date", "")),
                         fill=True, align="C")

            # Tip
            self.set_font("Helvetica", "B", 8)
            self.set_text_color(*c_ink)
            super().cell(CW[3], 9, f"  {_safe(win)[:16]}" if win else "  --", fill=True)

            # Prob + Margin
            self.set_font("Helvetica", "", 7.5)
            self.set_text_color(*SUB)
            super().cell(CW[4], 9, f"{prob:.0f}%" if prob else "--",
                         fill=True, align="C")
            super().cell(CW[5], 9, f"~{mar}pts" if mar else "--",
                         fill=True, align="C")

            # Confidence badge
            self.set_font("Helvetica", "B", 6.5)
            self.set_fill_color(*c_bg)
            self.set_text_color(*c_ink)
            super().cell(CW[6], 9, conf[0], fill=True, align="C")
            self.ln(9)

        self._rule()
        self.ln(4)

    def write_match_section(self, pred: Dict):
        home = _safe(pred.get("home_team", ""))
        away = _safe(pred.get("away_team", ""))
        text = pred.get("prediction", "")
        
        # Use extraction_utils functions
        conf = extract_confidence(text)
        win  = extract_winner(text, pred.get("home_team", ""), pred.get("away_team", ""))
        prob = extract_probability(text, win)
        mar  = extract_margin(text)
        odds = pred.get("betting_odds", {}) or {}
        c_ink, c_bg = _cc(conf)

        if self.get_y() > 240:
            self.add_page()

        # Match header bar
        y0 = self.get_y()
        self.set_fill_color(*LIGHT_GRAY)
        self.rect(14, y0, 182, 20, "F")
        self.set_fill_color(*c_ink)
        self.rect(14, y0, 4, 20, "F")

        # Meta info
        self.set_xy(21, y0 + 2)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*CAP)
        super().cell(
            0, 4,
            f"Round {pred.get('round', '')}   |   "
            f"{_safe(pred.get('venue', ''))}   |   "
            f"{_safe(pred.get('date', ''))}",
            ln=True
        )

        # Team names
        self.set_x(21)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*INK)
        super().cell(130, 11, f"{home}  vs  {away}", ln=False)

        # Confidence badge
        self.set_font("Helvetica", "B", 7.5)
        self.set_fill_color(*c_bg)
        self.set_text_color(*c_ink)
        super().cell(34, 11, f"{conf.upper()} CONFIDENCE",
                     fill=True, align="C", ln=True)
        self.set_text_color(*INK)
        self.ln(5)

        # Tip summary panel
        if win:
            y1 = self.get_y()
            self.set_fill_color(*c_bg)
            self.rect(14, y1, 182, 17, "F")
            self.set_fill_color(*c_ink)
            self.rect(14, y1, 3, 17, "F")

            self.set_xy(20, y1 + 2.5)
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(*c_ink)
            super().cell(12, 6, "TIP:", ln=False)

            self.set_font("Helvetica", "B", 13)
            self.set_text_color(*INK)
            super().cell(65, 6, _safe(win), ln=False)

            self.set_font("Helvetica", "", 9)
            self.set_text_color(*SUB)
            stats = []
            if prob: stats.append(f"{prob:.0f}% win probability")
            if mar:  stats.append(f"approx. {mar}pt margin")
            super().cell(0, 6, "   ".join(stats), ln=True)

            # Odds line
            self.set_xy(20, y1 + 10)
            self.set_font("Helvetica", "", 7.5)
            self.set_text_color(*SUB)
            parts = []
            if odds.get("home_odds"):
                parts.append(
                    f"{home} ${odds['home_odds']} "
                    f"({odds.get('home_implied_prob', '?')}% implied)"
                )
            if odds.get("away_odds"):
                parts.append(
                    f"{away} ${odds['away_odds']} "
                    f"({odds.get('away_implied_prob', '?')}% implied)"
                )
            if odds.get("line_summary"):
                parts.append(f"Line: {_safe(str(odds['line_summary']))}")
            if parts:
                super().cell(0, 5, "   |   ".join(parts), ln=True)

            self.set_text_color(*INK)
            self.ln(6)

        # Full AI analysis
        SECTION_STARTS = (
            "PREDICTED WINNER",  "WIN PROBABILITY",   "PREDICTED MARGIN",
            "KEY FACTORS",       "SCORING TRENDS",    "HOME GROUND",
            "MARKET",            "FATIGUE",            "WEATHER",
            "TEAM NEWS",         "CONFIDENCE",         "UPSET RISK",
            "DATA CONFLICTS",
        )

        for line in _clean(text).split("\n"):
            s = line.strip()
            if not s:
                self.ln(1.5)
                continue

            is_hdr = any(s.upper().startswith(k) for k in SECTION_STARTS)

            if is_hdr:
                self.ln(2)
                self.set_draw_color(*RULE_GRAY)
                self.line(14, self.get_y(), 196, self.get_y())
                self.ln(1.5)
                self.set_font("Helvetica", "B", 8.5)
                self.set_text_color(*GOLD)
            else:
                self.set_font("Helvetica", "", 8.5)
                self.set_text_color(*INK)

            self.set_x(14)
            super().multi_cell(182, 5, s)

        self.ln(4)
        self._rule(MID_GRAY)
        self.ln(4)


# ── Public API ────────────────────────────────────────────────────────────────

def generate_pdf(predictions: List[Dict]) -> bytes:
    """
    Generate a print-ready PDF from a list of prediction dicts.
    Returns raw bytes suitable for st.download_button().
    """
    if not predictions:
        raise ValueError("No predictions to export.")

    round_num    = predictions[0].get("round", "?")
    generated_at = datetime.now().strftime("%d %b %Y  %H:%M")

    pdf = TipsPDF(round_num=round_num, generated_at=generated_at)

    pdf.write_summary_table(predictions)

    pdf._section_label("DETAILED MATCH ANALYSIS")
    pdf.ln(3)

    for pred in predictions:
        pdf.write_match_section(pred)

    return bytes(pdf.output())
