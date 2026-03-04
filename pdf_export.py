"""
pdf_export.py
=============
Generates a clean, print-ready PDF of the week's AFL tips and full AI analysis.

Requires: fpdf2  (add 'fpdf2' to requirements.txt)

Unicode safety: fpdf2's built-in Helvetica is Latin-1 only. All text is
sanitised through _safe() before reaching fpdf2. The TipsPDF class overrides
cell() and multi_cell() so sanitisation is guaranteed on every code path.
"""

import re
from fpdf import FPDF
from datetime import datetime


# ─── Unicode → ASCII sanitiser ────────────────────────────────────────────────

_UNICODE_MAP = {
    "\u2014": "--",    # em dash     —
    "\u2013": "-",     # en dash     –
    "\u2012": "-",     # figure dash
    "\u2011": "-",     # non-breaking hyphen
    "\u2010": "-",     # hyphen
    "\u2018": "'",     # left single quote
    "\u2019": "'",     # right single quote / apostrophe
    "\u201c": '"',     # left double quote
    "\u201d": '"',     # right double quote
    "\u2022": "-",     # bullet          •
    "\u2026": "...",   # ellipsis        …
    "\u2192": "->",    # right arrow     →
    "\u2190": "<-",    # left arrow      ←
    "\u2191": "(up)",  # up arrow        ↑
    "\u2193": "(dn)",  # down arrow      ↓
    "\u25b2": "(up)",  # triangle up     ▲
    "\u25bc": "(dn)",  # triangle down   ▼
    "\u2248": "~",     # almost equal    ≈
    "\u2260": "!=",    # not equal       ≠
    "\u2265": ">=",    # greater/equal   ≥
    "\u2264": "<=",    # less/equal      ≤
    "\u00b7": ".",     # middle dot      ·
    "\u2500": "-", "\u2501": "-", "\u2502": "|", "\u2503": "|",
    "\u2550": "=", "\u2551": "|",
    "\u2580": " ", "\u2588": "#", "\u2591": " ", "\u2592": " ",
    "\u26a1": "!",     # ⚡
    "\u2705": "[Y]",   # ✅
    "\u274c": "[N]",   # ❌
    "\u26a0": "[!]",   # ⚠
    "\u2713": "OK",    # ✓
    "\u2717": "X",     # ✗
    "\u2764": "<3",    # ❤
    "\u2b50": "*",     # ⭐
    "\u26bd": "o",     # ⚽
    "\u2714": "OK",    # ✔
}

_TRANS = str.maketrans(_UNICODE_MAP)


def _safe(text) -> str:
    """Sanitise any value to a Latin-1-safe string for Helvetica."""
    if text is None:
        return ""
    s = str(text)
    s = s.translate(_TRANS)
    # Drop any remaining non-Latin-1 characters (emojis, etc.)
    s = s.encode("latin-1", errors="ignore").decode("latin-1")
    return s


def _clean_ai(text: str) -> str:
    """Clean AI markdown text for PDF: strip markers, sanitise unicode."""
    text = re.sub(r"\*{1,3}([^*\n]+)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,2}([^_\n]+)_{1,2}", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return _safe(text).strip()


# ─── Colours (RGB) ────────────────────────────────────────────────────────────
BG      = (13,  17,  23)
SURFACE = (22,  27,  34)
SURF2   = (28,  33,  40)
BORDER  = (48,  54,  61)
GOLD    = (232, 180, 75)
GREEN   = (63,  185, 80)
AMBER   = (210, 153, 34)
RED     = (248, 81,  73)
TEXT    = (230, 237, 243)
MUTED   = (139, 148, 158)


def _conf_col(c): return {"High": GREEN, "Medium": AMBER, "Low": RED}.get(c, AMBER)


# ─── Extraction helpers ───────────────────────────────────────────────────────

def _winner(text, home, away):
    t = text.upper()
    if "PREDICTED WINNER:" in t:
        idx = t.index("PREDICTED WINNER:")
        s = t[idx:idx+120]
        hp = s.find(home.upper().split()[-1])
        ap = s.find(away.upper().split()[-1])
        if hp != -1 and (ap == -1 or hp < ap): return home
        if ap != -1: return away
    return None

def _prob(text):
    for m in re.findall(r"(\d{2,3}(?:\.\d)?)\s*%", text):
        v = float(m)
        if 50 <= v <= 99: return v
    return None

def _margin(text):
    for m in re.findall(r"~?(\d{1,3})\s*points?", text.lower()):
        v = int(m)
        if 1 <= v <= 150: return v
    return None

def _conf(text):
    t = text.upper()
    if "CONFIDENCE:** HIGH" in t or "CONFIDENCE: HIGH" in t: return "High"
    if "CONFIDENCE:** LOW"  in t or "CONFIDENCE: LOW"  in t: return "Low"
    return "Medium"


# ─── PDF class ────────────────────────────────────────────────────────────────

class TipsPDF(FPDF):
    """
    AFL Tipping Agent PDF.
    cell() and multi_cell() are overridden to auto-sanitise all text —
    nothing can reach Helvetica unless it is Latin-1 safe.
    """

    def __init__(self, round_num, generated_at):
        super().__init__()
        self.round_num    = round_num
        self.generated_at = _safe(generated_at)
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(10, 24, 10)
        self.add_page()

    # Override to guarantee sanitisation on every text output
    def cell(self, w=0, h=0, txt="", border=0, ln=0,
             align="", fill=False, link=""):
        return super().cell(w, h, _safe(txt), border, ln, align, fill, link)

    def multi_cell(self, w, h, txt="", border=0, align="J",
                   fill=False, split_only=False, link="", **kwargs):
        return super().multi_cell(
            w, h, _safe(txt), border, align, fill,
            split_only=split_only, link=link
        )

    def header(self):
        self.set_fill_color(*BG)
        self.rect(0, 0, 210, 22, "F")
        self.set_xy(10, 5)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*GOLD)
        super().cell(
            0, 8,
            f"AFL TIPPING AGENT  --  ROUND {self.round_num} PREDICTIONS",
            ln=False
        )
        self.set_xy(10, 14)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*MUTED)
        super().cell(
            0, 5,
            f"Generated: {self.generated_at}   |   "
            "Data-driven . Unbiased . AI-powered   |   For entertainment only",
            ln=True
        )
        self.ln(4)

    def footer(self):
        self.set_y(-14)
        self.set_fill_color(*BG)
        self.rect(0, 283, 210, 20, "F")
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*MUTED)
        super().cell(
            0, 8,
            f"AFL Tipping Agent  |  Round {self.round_num}  |  "
            f"Page {self.page_no()}  |  For entertainment only. Please gamble responsibly.",
            align="C"
        )

    # ── Summary table ─────────────────────────────────────────────────────────

    def write_summary_table(self, predictions):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*GOLD)
        self.cell(0, 8, "ROUND SUMMARY -- ALL TIPS AT A GLANCE", ln=True)
        self.ln(1)

        CW = [60, 30, 24, 34, 14, 18, 20]   # total = 200 - 10 margins = fits
        HDRS = ["MATCH", "VENUE", "DATE", "OUR TIP", "PROB", "MARGIN", "CONF"]

        self.set_fill_color(*SURFACE)
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*MUTED)
        for w, h in zip(CW, HDRS):
            super().cell(w, 7, h, border=0, fill=True, align="C")
        self.ln(7)

        alt = False
        for pred in predictions:
            home   = _safe(pred.get("home_team", ""))
            away   = _safe(pred.get("away_team", ""))
            text   = pred.get("prediction", "")
            conf   = _conf(text)
            win    = _winner(text, pred.get("home_team",""), pred.get("away_team",""))
            prob   = _prob(text)
            mar    = _margin(text)
            cc     = _conf_col(conf)

            bg = (25, 30, 37) if alt else (20, 25, 32)
            self.set_fill_color(*bg)
            self.rect(10, self.get_y(), 180, 8, "F")
            alt = not alt

            self.set_font("Helvetica", "B", 8)
            self.set_text_color(*TEXT)
            super().cell(CW[0], 8, f"{home} vs {away}"[:28], border=0)

            self.set_font("Helvetica", "", 8)
            self.set_text_color(*MUTED)
            super().cell(CW[1], 8, _safe(pred.get("venue",""))[:16], align="C", border=0)
            super().cell(CW[2], 8, _safe(pred.get("date","")), align="C", border=0)

            self.set_font("Helvetica", "B", 8)
            self.set_text_color(*cc)
            super().cell(CW[3], 8, _safe(win)[:18] if win else "--", align="C", border=0)

            self.set_font("Helvetica", "", 8)
            self.set_text_color(*TEXT)
            super().cell(CW[4], 8, f"{prob:.0f}%" if prob else "--", align="C", border=0)
            super().cell(CW[5], 8, f"~{mar}pts" if mar else "--", align="C", border=0)

            self.set_font("Helvetica", "B", 7)
            self.set_text_color(*cc)
            super().cell(CW[6], 8, conf.upper(), align="C", border=0)
            self.ln(8)

        self.ln(6)

    # ── Per-match section ─────────────────────────────────────────────────────

    def write_match_section(self, pred):
        home   = _safe(pred.get("home_team", ""))
        away   = _safe(pred.get("away_team", ""))
        text   = pred.get("prediction", "")
        conf   = _conf(text)
        win    = _winner(text, pred.get("home_team",""), pred.get("away_team",""))
        prob   = _prob(text)
        mar    = _margin(text)
        odds   = pred.get("betting_odds", {}) or {}
        cc     = _conf_col(conf)

        if self.get_y() > 245:
            self.add_page()

        # Rule
        self.set_draw_color(*BORDER)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)

        # Header bar
        y0 = self.get_y()
        self.set_fill_color(*SURFACE)
        self.rect(10, y0, 180, 15, "F")

        self.set_xy(12, y0 + 1)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*MUTED)
        super().cell(
            0, 5,
            f"Round {pred.get('round','')}   "
            f"{_safe(pred.get('venue',''))}   "
            f"{_safe(pred.get('date',''))}",
            ln=True
        )
        self.set_x(12)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*TEXT)
        super().cell(120, 8, f"{home}  vs  {away}", ln=False)

        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*cc)
        super().cell(68, 8, f"{conf.upper()} CONFIDENCE", align="R", ln=True)
        self.ln(2)

        # Tip box
        if win:
            y1 = self.get_y()
            self.set_fill_color(*SURF2)
            self.rect(10, y1, 180, 14, "F")

            self.set_xy(12, y1 + 2)
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(*cc)
            tip = f"TIP: {_safe(win)}"
            if prob:  tip += f"   ({prob:.0f}% win probability)"
            if mar:   tip += f"   approx. {mar}pt margin"
            super().cell(0, 6, tip, ln=True)

            self.set_x(12)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(*MUTED)
            parts = []
            if odds.get("home_odds"):
                parts.append(f"{home} ${odds['home_odds']} ({odds.get('home_implied_prob','?')}% implied)")
            if odds.get("away_odds"):
                parts.append(f"{away} ${odds['away_odds']} ({odds.get('away_implied_prob','?')}% implied)")
            if odds.get("line_summary"):
                parts.append(f"Line: {_safe(str(odds['line_summary']))}")
            if parts:
                super().cell(0, 5, "  |  ".join(parts), ln=True)
            self.ln(4)

        # AI analysis text
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*GOLD)
        self.set_x(10)
        super().cell(0, 7, "FULL AI ANALYSIS", ln=True)

        SECTION_STARTS = (
            "PREDICTED WINNER", "WIN PROBABILITY", "PREDICTED MARGIN",
            "KEY FACTORS", "SCORING TRENDS", "MARKET", "FATIGUE",
            "WEATHER", "TEAM NEWS", "CONFIDENCE", "UPSET RISK",
            "DATA CONFLICTS",
        )

        for line in _clean_ai(text).split("\n"):
            s = line.strip()
            if not s:
                self.ln(2)
                continue
            is_hdr = any(s.upper().startswith(k) for k in SECTION_STARTS)
            if is_hdr:
                self.ln(1)
                self.set_font("Helvetica", "B", 8.5)
                self.set_text_color(*GOLD)
            else:
                self.set_font("Helvetica", "", 8)
                self.set_text_color(*TEXT)
            self.set_x(10)
            super().multi_cell(190, 4.5, s)

        self.ln(5)


# ─── Public function ──────────────────────────────────────────────────────────

def generate_pdf(predictions: list) -> bytes:
    """
    Generate a PDF from a list of prediction dicts.
    Returns raw bytes for st.download_button().
    """
    if not predictions:
        raise ValueError("No predictions to export.")

    round_num    = predictions[0].get("round", "?")
    generated_at = datetime.now().strftime("%d %b %Y  %H:%M")

    pdf = TipsPDF(round_num=round_num, generated_at=generated_at)

    pdf.write_summary_table(predictions)

    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*GOLD)
    pdf.cell(0, 8, "DETAILED MATCH ANALYSIS", ln=True)
    pdf.ln(2)

    for pred in predictions:
        pdf.write_match_section(pred)

    return bytes(pdf.output())
