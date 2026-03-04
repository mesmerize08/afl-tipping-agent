"""
pdf_export.py  —  AFL Tipping Agent
White paper, dark ink, print-ready layout.
Requires: fpdf2
"""

import re
from fpdf import FPDF
from datetime import datetime

# ── Unicode sanitiser ─────────────────────────────────────────────────────────
_UMAP = {
    "\u2014":"--", "\u2013":"-",  "\u2012":"-",  "\u2011":"-",  "\u2010":"-",
    "\u2018":"'",  "\u2019":"'",  "\u201c":'"',  "\u201d":'"',
    "\u2022":"-",  "\u2026":"...","\u2192":"->",  "\u2190":"<-",
    "\u2191":"^",  "\u2193":"v",  "\u25b2":"^",  "\u25bc":"v",
    "\u2248":"~",  "\u2260":"!=", "\u2265":">=",  "\u2264":"<=",
    "\u00b7":".",  "\u2500":"-",  "\u2501":"-",  "\u2502":"|",
    "\u2503":"|",  "\u2550":"=",  "\u2551":"|",  "\u2580":" ",
    "\u2588":"#",  "\u2591":" ",  "\u2592":" ",  "\u26a1":">>",
    "\u2705":"[Y]","\u274c":"[N]","\u26a0":"[!]","\u2713":"OK",
    "\u2717":"X",  "\u2714":"OK", "\u2764":"<3",  "\u2b50":"*",
}
_TRANS = str.maketrans(_UMAP)

def _safe(v) -> str:
    s = str(v) if v is not None else ""
    s = s.translate(_TRANS)
    return s.encode("latin-1", errors="ignore").decode("latin-1")

def _clean(text: str) -> str:
    text = re.sub(r"\*{1,3}([^*\n]+)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,2}([^_\n]+)_{1,2}", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return _safe(text).strip()

# ── Palette: white paper ───────────────────────────────────────────────────────
WHITE    = (255, 255, 255)
PAPER    = (252, 252, 252)
ROW_ALT  = (245, 247, 250)
INK      = (20,  25,  30)       # near-black body text
SUB      = (75,  85,  100)      # secondary text
CAP      = (140, 150, 160)      # captions
RULE     = (210, 215, 220)      # divider lines

NAVY     = (18,  45,  85)       # header background
GOLD     = (160, 110, 20)       # gold on white
GOLD_BG  = (255, 245, 215)

G_INK    = (25,  120, 50)       # green on white
G_BG     = (225, 248, 230)
A_INK    = (155,  95, 10)       # amber on white
A_BG     = (255, 240, 205)
R_INK    = (180,  35, 30)       # red on white
R_BG     = (255, 228, 225)

def _cc(conf):
    return {"High":(G_INK,G_BG), "Medium":(A_INK,A_BG), "Low":(R_INK,R_BG)}.get(conf,(A_INK,A_BG))

# ── Extraction ────────────────────────────────────────────────────────────────
def _winner(text, home, away):
    t = text.upper()
    if "PREDICTED WINNER:" in t:
        idx = t.index("PREDICTED WINNER:")
        s   = t[idx:idx+120]
        hp  = s.find(home.upper().split()[-1])
        ap  = s.find(away.upper().split()[-1])
        if hp!=-1 and (ap==-1 or hp<ap): return home
        if ap!=-1: return away
    return None

def _prob(text):
    for m in re.findall(r"(\d{2,3}(?:\.\d)?)\s*%", text):
        v=float(m)
        if 50<=v<=99: return v
    return None

def _margin(text):
    for m in re.findall(r"~?(\d{1,3})\s*points?", text.lower()):
        v=int(m)
        if 1<=v<=150: return v
    return None

def _conf(text):
    t=text.upper()
    if "CONFIDENCE:** HIGH" in t or "CONFIDENCE: HIGH" in t: return "High"
    if "CONFIDENCE:** LOW"  in t or "CONFIDENCE: LOW"  in t: return "Low"
    return "Medium"

# ── PDF class ─────────────────────────────────────────────────────────────────
class TipsPDF(FPDF):

    def __init__(self, round_num, generated_at):
        super().__init__()
        self.round_num    = round_num
        self.generated_at = _safe(generated_at)
        self.set_auto_page_break(True, margin=22)
        self.set_margins(14, 28, 14)
        self.add_page()

    # Sanitise every string before it reaches the font
    def cell(self, w=0, h=0, txt="", border=0, ln=0, align="", fill=False, link=""):
        return super().cell(w, h, _safe(txt), border, ln, align, fill, link)

    def multi_cell(self, w, h, txt="", border=0, align="J", fill=False,
                   split_only=False, link="", **kw):
        return super().multi_cell(w, h, _safe(txt), border, align, fill,
                                  split_only=split_only, link=link)

    # ── Header ────────────────────────────────────────────────────────────────
    def header(self):
        # Navy banner
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 19, "F")
        # Gold underline
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
        super().cell(0, 5, "Data-driven  .  Unbiased  .  AI-powered  .  For entertainment only", ln=True)

        self.set_text_color(*INK)
        self.ln(7)

    # ── Footer ────────────────────────────────────────────────────────────────
    def footer(self):
        self.set_y(-14)
        self.set_draw_color(*RULE)
        self.line(14, self.get_y(), 196, self.get_y())
        self.ln(1)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*CAP)
        super().cell(0, 6,
            f"AFL Tipping Agent  |  Round {self.round_num}  |  "
            f"Page {self.page_no()}  |  For entertainment only. Please gamble responsibly.",
            align="C")

    # ── Divider ───────────────────────────────────────────────────────────────
    def _rule(self, color=RULE):
        self.set_draw_color(*color)
        self.line(14, self.get_y(), 196, self.get_y())
        self.ln(3)

    # ── Section label ─────────────────────────────────────────────────────────
    def _section_label(self, title):
        self.set_fill_color(*GOLD_BG)
        self.set_x(14)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*GOLD)
        super().cell(182, 6, f"  {title}", fill=True, ln=True)
        self.ln(2)

    # ── Summary table ─────────────────────────────────────────────────────────
    def write_summary_table(self, predictions):
        self._section_label("ROUND SUMMARY -- ALL TIPS AT A GLANCE")

        # Column widths sum to 182
        CW   = [55, 28, 24, 38, 13, 16, 8]
        HDRS = ["MATCH", "VENUE", "DATE", "TIP", "PROB", "MARGIN", ""]

        # Header row — navy background
        self.set_fill_color(*NAVY)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 7.5)
        self.set_x(14)
        for w, h in zip(CW, HDRS):
            super().cell(w, 8, f"  {h}" if h else "", fill=True, border=0)
        self.ln(8)

        alt = False
        for pred in predictions:
            home = _safe(pred.get("home_team",""))
            away = _safe(pred.get("away_team",""))
            text = pred.get("prediction","")
            conf = _conf(text)
            win  = _winner(text, pred.get("home_team",""), pred.get("away_team",""))
            prob = _prob(text)
            mar  = _margin(text)
            c_ink, c_bg = _cc(conf)

            bg = ROW_ALT if alt else WHITE
            alt = not alt
            self.set_fill_color(*bg)
            self.set_x(14)

            # Match
            self.set_font("Helvetica", "B", 8)
            self.set_text_color(*INK)
            super().cell(CW[0], 9, f"  {home} vs {away}"[:28], fill=True)

            # Venue + Date
            self.set_font("Helvetica", "", 7.5)
            self.set_text_color(*SUB)
            super().cell(CW[1], 9, _safe(pred.get("venue",""))[:14], fill=True, align="C")
            super().cell(CW[2], 9, _safe(pred.get("date","")), fill=True, align="C")

            # Tip — coloured
            self.set_font("Helvetica", "B", 8)
            self.set_text_color(*c_ink)
            super().cell(CW[3], 9, f"  {_safe(win)[:16]}" if win else "  --", fill=True)

            # Prob + Margin
            self.set_font("Helvetica", "", 7.5)
            self.set_text_color(*SUB)
            super().cell(CW[4], 9, f"{prob:.0f}%" if prob else "--", fill=True, align="C")
            super().cell(CW[5], 9, f"~{mar}pts" if mar else "--", fill=True, align="C")

            # Confidence mini-badge
            self.set_font("Helvetica", "B", 6.5)
            self.set_fill_color(*c_bg)
            self.set_text_color(*c_ink)
            super().cell(CW[6], 9, conf[0], fill=True, align="C")
            self.ln(9)

        self._rule()
        self.ln(4)

    # ── Per-match section ─────────────────────────────────────────────────────
    def write_match_section(self, pred):
        home = _safe(pred.get("home_team",""))
        away = _safe(pred.get("away_team",""))
        text = pred.get("prediction","")
        conf = _conf(text)
        win  = _winner(text, pred.get("home_team",""), pred.get("away_team",""))
        prob = _prob(text)
        mar  = _margin(text)
        odds = pred.get("betting_odds",{}) or {}
        c_ink, c_bg = _cc(conf)

        if self.get_y() > 240:
            self.add_page()

        # ── Match header bar ──────────────────────────────────────────────────
        y0 = self.get_y()
        # Light grey background
        self.set_fill_color(240, 243, 247)
        self.rect(14, y0, 182, 20, "F")
        # Left accent stripe (confidence colour)
        self.set_fill_color(*c_ink)
        self.rect(14, y0, 4, 20, "F")

        # Meta line: round / venue / date
        self.set_xy(21, y0 + 2)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*CAP)
        super().cell(0, 4,
            f"Round {pred.get('round','')}   |   "
            f"{_safe(pred.get('venue',''))}   |   "
            f"{_safe(pred.get('date',''))}", ln=True)

        # Team names
        self.set_x(21)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*INK)
        super().cell(130, 11, f"{home}  vs  {away}", ln=False)

        # Confidence badge (right side)
        self.set_font("Helvetica", "B", 7.5)
        self.set_fill_color(*c_bg)
        self.set_text_color(*c_ink)
        super().cell(34, 11, f"{conf.upper()} CONFIDENCE", fill=True, align="C", ln=True)

        self.set_text_color(*INK)
        self.ln(5)

        # ── Tip summary panel ─────────────────────────────────────────────────
        if win:
            y1 = self.get_y()
            # Subtle fill with coloured left border
            self.set_fill_color(*c_bg)
            self.rect(14, y1, 182, 17, "F")
            self.set_fill_color(*c_ink)
            self.rect(14, y1, 3, 17, "F")

            # "TIP:" label + winner name
            self.set_xy(20, y1 + 2.5)
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(*c_ink)
            super().cell(12, 6, "TIP:", ln=False)

            self.set_font("Helvetica", "B", 13)
            self.set_text_color(*INK)
            super().cell(65, 6, _safe(win), ln=False)

            # Probability + margin
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
                parts.append(f"{home} ${odds['home_odds']} ({odds.get('home_implied_prob','?')}% implied)")
            if odds.get("away_odds"):
                parts.append(f"{away} ${odds['away_odds']} ({odds.get('away_implied_prob','?')}% implied)")
            if odds.get("line_summary"):
                parts.append(f"Line: {_safe(str(odds['line_summary']))}")
            if parts:
                super().cell(0, 5, "   |   ".join(parts), ln=True)

            self.set_text_color(*INK)
            self.ln(6)

        # ── AI analysis ───────────────────────────────────────────────────────
        SECTION_STARTS = (
            "PREDICTED WINNER", "WIN PROBABILITY", "PREDICTED MARGIN",
            "KEY FACTORS", "SCORING TRENDS", "MARKET", "FATIGUE",
            "WEATHER", "TEAM NEWS", "CONFIDENCE", "UPSET RISK",
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
                self.set_draw_color(*RULE)
                self.line(14, self.get_y(), 196, self.get_y())
                self.ln(1.5)
                self.set_font("Helvetica", "B", 8.5)
                self.set_text_color(*GOLD)
                self.set_x(14)
                super().multi_cell(182, 5, s)
            else:
                self.set_font("Helvetica", "", 8.5)
                self.set_text_color(*INK)
                self.set_x(14)
                super().multi_cell(182, 5, s)

        self.ln(4)
        self._rule((220, 225, 230))
        self.ln(4)


# ── Public function ───────────────────────────────────────────────────────────
def generate_pdf(predictions: list) -> bytes:
    """Generate a PDF. Returns bytes for st.download_button()."""
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
