"""
pdf_export.py
=============
Generates a clean, print-ready PDF of the week's AFL tips and full AI analysis.

Requires: fpdf2  (pip install fpdf2)
  → Add 'fpdf2' to requirements.txt
"""

from fpdf import FPDF
from datetime import datetime
import re


# ─── Colour palette ───────────────────────────────────────────────────────────
DARK_BG    = (13,  17,  23)
SURFACE    = (22,  27,  34)
GOLD       = (232, 180, 75)
GREEN      = (63,  185, 80)
AMBER      = (210, 153, 34)
RED        = (248, 81,  73)
TEXT       = (230, 237, 243)
MUTED      = (139, 148, 158)
BORDER     = (48,  54,  61)
WHITE      = (255, 255, 255)


def _conf_colour(confidence: str):
    return {"High": GREEN, "Medium": AMBER, "Low": RED}.get(confidence, AMBER)


def _extract_winner(text: str, home: str, away: str):
    t = text.upper()
    if "PREDICTED WINNER:" in t:
        idx     = t.index("PREDICTED WINNER:")
        snippet = t[idx:idx+120]
        hp      = snippet.find(home.upper().split()[-1])
        ap      = snippet.find(away.upper().split()[-1])
        if hp != -1 and (ap == -1 or hp < ap):
            return home
        if ap != -1:
            return away
    return None


def _extract_probability(text: str):
    for m in re.findall(r'(\d{2,3}(?:\.\d)?)\s*%', text):
        v = float(m)
        if 50 <= v <= 99:
            return v
    return None


def _extract_margin(text: str):
    for m in re.findall(r'~?(\d{1,3})\s*points?', text.lower()):
        v = int(m)
        if 1 <= v <= 150:
            return v
    return None


def _extract_confidence(text: str):
    t = text.upper()
    if "CONFIDENCE:** HIGH" in t or "CONFIDENCE: HIGH" in t:
        return "High"
    if "CONFIDENCE:** LOW" in t or "CONFIDENCE: LOW" in t:
        return "Low"
    return "Medium"


def _clean_text(text: str) -> str:
    """Strip markdown bold/italic markers and normalise whitespace."""
    text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)
    text = text.replace("━", "-").replace("═", "=").replace("─", "-")
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ─── PDF class ────────────────────────────────────────────────────────────────

class TipsPDF(FPDF):

    def __init__(self, round_num, generated_at):
        super().__init__()
        self.round_num    = round_num
        self.generated_at = generated_at
        self.set_auto_page_break(auto=True, margin=18)
        self.add_page()

    def header(self):
        # Dark header bar
        self.set_fill_color(*DARK_BG)
        self.rect(0, 0, 210, 20, 'F')

        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*GOLD)
        self.set_xy(10, 5)
        self.cell(0, 10, f"AFL TIPPING AGENT  —  ROUND {self.round_num} PREDICTIONS", ln=False)

        self.set_font("Helvetica", "", 8)
        self.set_text_color(*MUTED)
        self.set_xy(10, 13)
        self.cell(0, 5, f"Generated: {self.generated_at}    |    Data-driven · Unbiased · AI-powered    |    For entertainment only", ln=False)

        self.ln(10)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*MUTED)
        self.set_fill_color(*DARK_BG)
        self.rect(0, 285, 210, 15, 'F')
        self.cell(0, 8,
            f"AFL Tipping Agent — Round {self.round_num}    |    Page {self.page_no()}    |    For entertainment only. Please gamble responsibly.",
            align="C"
        )

    def section_rule(self):
        self.set_draw_color(*BORDER)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)

    def coloured_cell(self, w, h, txt, colour, bold=False, align="L", fill=False, fill_colour=None):
        self.set_text_color(*colour)
        self.set_font("Helvetica", "B" if bold else "", 9)
        if fill and fill_colour:
            self.set_fill_color(*fill_colour)
        self.cell(w, h, txt, align=align, fill=fill)

    def write_summary_table(self, predictions):
        """Top-of-PDF quick-glance table."""
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*GOLD)
        self.cell(0, 8, "ROUND SUMMARY — ALL TIPS AT A GLANCE", ln=True)
        self.ln(1)

        # Table header
        col_w = [62, 28, 24, 22, 22, 22, 20]
        hdrs  = ["Match", "Venue", "Date", "Our Tip", "Prob %", "Margin", "Conf"]
        self.set_font("Helvetica", "B", 7.5)
        self.set_fill_color(*SURFACE)
        self.set_text_color(*MUTED)
        for w, h in zip(col_w, hdrs):
            self.cell(w, 7, h.upper(), border=0, fill=True, align="C")
        self.ln(7)

        # Data rows
        for pred in predictions:
            home   = pred["home_team"]
            away   = pred["away_team"]
            text   = pred.get("prediction", "")
            conf   = _extract_confidence(text)
            winner = _extract_winner(text, home, away)
            prob   = _extract_probability(text)
            margin = _extract_margin(text)
            cc     = _conf_colour(conf)

            # Alternating row shading
            self.set_fill_color(22, 27, 34)
            self.rect(10, self.get_y(), 180, 8, 'F')

            self.set_font("Helvetica", "B", 8)
            self.set_text_color(*TEXT)
            self.cell(col_w[0], 8, f"{home} vs {away}"[:32], border=0)

            self.set_font("Helvetica", "", 8)
            self.set_text_color(*MUTED)
            self.cell(col_w[1], 8, pred.get("venue", "")[:18], align="C", border=0)
            self.cell(col_w[2], 8, pred.get("date", ""), align="C", border=0)

            self.set_font("Helvetica", "B", 8)
            self.set_text_color(*cc)
            self.cell(col_w[3], 8, winner[:14] if winner else "—", align="C", border=0)

            self.set_font("Helvetica", "", 8)
            self.set_text_color(*TEXT)
            self.cell(col_w[4], 8, f"{prob:.0f}%" if prob else "—", align="C", border=0)
            self.cell(col_w[5], 8, f"~{margin} pts" if margin else "—", align="C", border=0)

            self.set_font("Helvetica", "B", 7.5)
            self.set_text_color(*cc)
            self.cell(col_w[6], 8, conf.upper(), align="C", border=0)
            self.ln(8)

        self.ln(6)

    def write_match_section(self, pred):
        """Full analysis block for one match — starts on a new page if close to bottom."""
        home   = pred["home_team"]
        away   = pred["away_team"]
        text   = pred.get("prediction", "")
        conf   = _extract_confidence(text)
        winner = _extract_winner(text, home, away)
        prob   = _extract_probability(text)
        margin = _extract_margin(text)
        odds   = pred.get("betting_odds", {})
        cc     = _conf_colour(conf)

        # Keep match header together — add page if < 60mm remaining
        if self.get_y() > 240:
            self.add_page()

        self.section_rule()

        # Match header bar
        self.set_fill_color(*SURFACE)
        self.rect(10, self.get_y(), 180, 14, 'F')

        # Left: round/venue/date
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*MUTED)
        self.set_x(12)
        self.cell(0, 5, f"Round {pred.get('round', '')}  ·  {pred.get('venue', '')}  ·  {pred.get('date', '')}", ln=True)

        # Team names
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*TEXT)
        self.set_x(12)
        self.cell(120, 9, f"{home}  vs  {away}", ln=False)

        # Confidence badge (right side)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*cc)
        self.cell(68, 9, f"{conf.upper()} CONFIDENCE", align="R", ln=True)
        self.ln(2)

        # Prediction box
        if winner:
            self.set_fill_color(*SURFACE)
            self.rect(10, self.get_y(), 180, 16, 'F')
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(*cc)
            self.set_x(12)
            tip_line = f"⚡  TIP: {winner}"
            if prob:
                tip_line += f"   ({prob:.0f}% win probability)"
            if margin:
                tip_line += f"   ·   ~{margin} pt margin"
            self.cell(0, 8, tip_line, ln=True)
            self.set_x(12)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(*MUTED)

            # Odds line
            parts = []
            if odds.get("home_odds"):
                parts.append(f"{home} ${odds['home_odds']} ({odds.get('home_implied_prob', '?')}% implied)")
            if odds.get("away_odds"):
                parts.append(f"{away} ${odds['away_odds']} ({odds.get('away_implied_prob', '?')}% implied)")
            if odds.get("line_summary"):
                parts.append(f"Line: {odds['line_summary']}")
            if parts:
                self.cell(0, 6, "  |  ".join(parts), ln=True)
            self.ln(3)

        # Full AI analysis text
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*GOLD)
        self.set_x(10)
        self.cell(0, 7, "FULL AI ANALYSIS", ln=True)

        clean = _clean_text(text)
        lines = clean.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                self.ln(2)
                continue

            # Section headers (all-caps or starting with **)
            is_header = (
                line.isupper() and len(line) > 4
                or line.startswith("PREDICTED ")
                or line.startswith("KEY FACTORS")
                or line.startswith("SCORING TRENDS")
                or line.startswith("MARKET & MODEL")
                or line.startswith("FATIGUE")
                or line.startswith("WEATHER")
                or line.startswith("TEAM NEWS")
                or line.startswith("CONFIDENCE:")
                or line.startswith("UPSET RISK")
                or line.startswith("DATA CONFLICTS")
            )

            if is_header:
                self.set_font("Helvetica", "B", 8.5)
                self.set_text_color(*GOLD)
            else:
                self.set_font("Helvetica", "", 8)
                self.set_text_color(*TEXT)

            # Use multi_cell for wrapped text
            self.set_x(10)
            self.multi_cell(190, 5, line)

        self.ln(4)


# ─── Public API ───────────────────────────────────────────────────────────────

def generate_pdf(predictions: list) -> bytes:
    """
    Generate a PDF from a list of prediction dicts.
    Returns the PDF as bytes, ready for st.download_button().

    Each prediction dict needs at minimum:
      home_team, away_team, venue, date, round, prediction (str), betting_odds (dict)
    """
    if not predictions:
        raise ValueError("No predictions to export")

    round_num    = predictions[0].get("round", "?")
    generated_at = datetime.now().strftime("%d %b %Y  %H:%M")

    pdf = TipsPDF(round_num=round_num, generated_at=generated_at)
    pdf.set_margins(10, 22, 10)

    # Page 1: Summary table
    pdf.write_summary_table(predictions)

    # Subsequent pages: per-match analysis
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*GOLD)
    pdf.cell(0, 8, "DETAILED MATCH ANALYSIS", ln=True)
    pdf.ln(2)

    for pred in predictions:
        pdf.write_match_section(pred)

    return bytes(pdf.output())
