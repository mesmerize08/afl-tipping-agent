"""
app.py  (FULL REDESIGN — Sports Night Broadcast aesthetic)
===========================================================
UI Upgrades:
  1. Full visual redesign — dark theme, gold accents, scoreboard typography
  2. Quick-glance summary table — scan the whole round at a glance
  3. Match lockout countdowns — live JS countdown per game card
  4. Last round performance banner — instant accuracy context at the top
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import os
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from data_fetcher import (
    get_upcoming_fixtures, get_ladder,
    get_betting_odds, get_afl_news, compile_match_data,
    get_squiggle_tips
)
from predict import run_weekly_predictions
from tracker import check_and_update_results, get_accuracy_display_data, load_history
from team_news import get_all_teams_news_summary, TEAM_URLS

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AFL Tipping Agent",
    page_icon="🏉",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── Global CSS — Sports Night Broadcast theme ────────────────────────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;800&family=DM+Mono:wght@400;500&family=Outfit:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg:       #0d1117;
    --surface:  #161b22;
    --surface2: #21262d;
    --border:   #30363d;
    --gold:     #e8b44b;
    --gold-dim: #a07d2e;
    --blue:     #58a6ff;
    --text:     #e6edf3;
    --muted:    #8b949e;
    --green:    #3fb950;
    --amber:    #d29922;
    --red:      #f85149;
  }
  .stApp { background-color: var(--bg) !important; font-family: 'Outfit', sans-serif !important; color: var(--text) !important; }
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding-top: 1.5rem !important; max-width: 1200px !important; }
  h1, h2, h3 { font-family: 'Barlow Condensed', sans-serif !important; color: var(--text) !important; letter-spacing: 0.02em; }
  h1 { font-size: 2.8rem !important; font-weight: 800 !important; }
  h2 { font-size: 1.9rem !important; font-weight: 700 !important; }
  h3 { font-size: 1.4rem !important; font-weight: 600 !important; }
  p, li, label { font-family: 'Outfit', sans-serif !important; color: var(--text) !important; }
  .stTabs [data-baseweb="tab-list"] { background: var(--surface) !important; border-bottom: 1px solid var(--border) !important; gap: 0 !important; padding: 0 !important; }
  .stTabs [data-baseweb="tab"] { font-family: 'Barlow Condensed', sans-serif !important; font-size: 1rem !important; font-weight: 600 !important; letter-spacing: 0.05em !important; color: var(--muted) !important; background: transparent !important; border: none !important; padding: 0.75rem 1.5rem !important; text-transform: uppercase !important; }
  .stTabs [aria-selected="true"] { color: var(--gold) !important; border-bottom: 2px solid var(--gold) !important; }
  .stTabs [data-baseweb="tab-panel"] { background: var(--bg) !important; padding-top: 1.5rem !important; }
  .stButton > button { font-family: 'Barlow Condensed', sans-serif !important; font-size: 1rem !important; font-weight: 700 !important; letter-spacing: 0.08em !important; text-transform: uppercase !important; background: var(--gold) !important; color: #0d1117 !important; border: none !important; border-radius: 4px !important; padding: 0.6rem 1.4rem !important; transition: all 0.15s ease !important; }
  .stButton > button:hover { background: #f0c76a !important; transform: translateY(-1px) !important; }
  [data-testid="stMetric"] { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: 6px !important; padding: 1rem !important; }
  [data-testid="stMetricLabel"] { font-family: 'Barlow Condensed', sans-serif !important; font-size: 0.85rem !important; font-weight: 600 !important; letter-spacing: 0.08em !important; text-transform: uppercase !important; color: var(--muted) !important; }
  [data-testid="stMetricValue"] { font-family: 'Barlow Condensed', sans-serif !important; font-size: 2rem !important; font-weight: 800 !important; color: var(--gold) !important; }
  [data-testid="stMetricDelta"] { font-family: 'DM Mono', monospace !important; font-size: 0.8rem !important; color: var(--muted) !important; }
  .streamlit-expanderHeader { font-family: 'Barlow Condensed', sans-serif !important; font-size: 1rem !important; font-weight: 600 !important; background: var(--surface2) !important; color: var(--text) !important; border: 1px solid var(--border) !important; border-radius: 4px !important; }
  .streamlit-expanderContent { background: var(--surface) !important; border: 1px solid var(--border) !important; border-top: none !important; }
  .stSelectbox > div > div { background: var(--surface) !important; border: 1px solid var(--border) !important; color: var(--text) !important; border-radius: 4px !important; }
  [data-testid="stDataFrame"] { border: 1px solid var(--border) !important; border-radius: 6px !important; overflow: hidden !important; }
  hr { border-color: var(--border) !important; margin: 1.5rem 0 !important; }
  .stSpinner > div { border-top-color: var(--gold) !important; }
  [data-testid="stProgressBar"] > div > div { background: linear-gradient(90deg, var(--gold-dim), var(--gold)) !important; }
  [data-testid="stSidebar"] { background: var(--surface) !important; border-right: 1px solid var(--border) !important; }
</style>
""", unsafe_allow_html=True)


# ─── Extraction helpers ────────────────────────────────────────────────────────

def extract_confidence(text):
    t = text.upper()
    if "CONFIDENCE:** HIGH" in t or "CONFIDENCE: HIGH" in t: return "High"
    if "CONFIDENCE:** MEDIUM" in t or "CONFIDENCE: MEDIUM" in t: return "Medium"
    if "CONFIDENCE:** LOW" in t or "CONFIDENCE: LOW" in t: return "Low"
    return "Medium"

def extract_winner(text, home, away):
    """
    Extract predicted winner using full team name search — not last-word —
    to avoid Melbourne/North Melbourne, Adelaide/Port Adelaide collisions.
    """
    t          = text.upper()
    home_upper = home.upper()
    away_upper = away.upper()
    if "PREDICTED WINNER:" in t:
        idx     = t.index("PREDICTED WINNER:")
        snippet = t[idx:idx + 120]
        hp = snippet.find(home_upper)
        ap = snippet.find(away_upper)
        if hp != -1 and (ap == -1 or hp < ap): return home
        if ap != -1: return away
    return None

def extract_probability(text, winner):
    if not winner: return None
    for m in re.findall(r'(\d{2,3}(?:\.\d)?)\s*%', text):
        v = float(m)
        if 50 <= v <= 99: return v
    return None

def extract_margin(text):
    for m in re.findall(r'~?(\d{1,3})\s*points?', text.lower()):
        v = int(m)
        if 1 <= v <= 150: return v
    return None

def confidence_style(confidence):
    return {
        "High":   {"color": "#3fb950", "bg": "rgba(63,185,80,0.06)",  "label": "HIGH CONFIDENCE"},
        "Medium": {"color": "#d29922", "bg": "rgba(210,153,34,0.06)", "label": "MEDIUM CONFIDENCE"},
        "Low":    {"color": "#f85149", "bg": "rgba(248,81,73,0.06)",  "label": "LOW CONFIDENCE"},
    }.get(confidence, {"color": "#d29922", "bg": "rgba(210,153,34,0.06)", "label": "MEDIUM CONFIDENCE"})


# ─── Performance banner ────────────────────────────────────────────────────────

def render_performance_banner():
    history  = load_history()
    accuracy = history.get("accuracy_summary", {})
    by_round = accuracy.get("by_round", {})
    if not by_round:
        return
    latest      = max(by_round.keys(), key=lambda x: int(x))
    r           = by_round[latest]
    pct         = r["pct"]
    overall_pct = accuracy.get("overall_accuracy_pct", 0)
    color = "#3fb950" if pct >= 70 else ("#d29922" if pct >= 55 else "#f85149")
    emoji = "🔥" if pct >= 70 else ("✅" if pct >= 55 else "📉")
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#161b22 0%,#1c2128 100%);border:1px solid {color};border-left:4px solid {color};border-radius:6px;padding:0.75rem 1.25rem;margin-bottom:1.5rem;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.5rem;">
        <div style="font-family:'Barlow Condensed',sans-serif;font-size:0.8rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#8b949e;">Last Round Performance</div>
        <div style="font-family:'Barlow Condensed',sans-serif;font-size:1.5rem;font-weight:800;color:{color};">{emoji} Round {latest}: {r['correct']}/{r['total']} correct ({pct}%)</div>
        <div style="font-family:'DM Mono',monospace;font-size:0.85rem;color:#8b949e;">Season: {overall_pct}% overall</div>
    </div>
    """, unsafe_allow_html=True)


# ─── Quick-glance summary table ───────────────────────────────────────────────

def render_summary_table(predictions):
    rows_html = ""
    for pred in predictions:
        home   = pred["home_team"]
        away   = pred["away_team"]
        text   = pred["prediction"]
        conf   = extract_confidence(text)
        winner = extract_winner(text, home, away)
        prob   = extract_probability(text, winner)
        margin = extract_margin(text)
        style  = confidence_style(conf)

        conf_badge = f'<span style="background:{style["color"]}22;color:{style["color"]};border:1px solid {style["color"]}44;padding:2px 8px;border-radius:3px;font-size:0.75rem;font-family:Barlow Condensed,sans-serif;font-weight:700;letter-spacing:0.05em;">{conf.upper()}</span>'
        winner_cell = f'<span style="color:{style["color"]};font-family:Barlow Condensed,sans-serif;font-size:1rem;font-weight:700;">{"⚡ " + winner if winner else "—"}</span>'
        prob_cell   = f'<span style="font-family:DM Mono,monospace;color:#e6edf3;">{prob:.0f}%</span>' if prob else "—"
        margin_cell = f'<span style="font-family:DM Mono,monospace;color:#8b949e;">~{margin} pts</span>' if margin else "—"

        rows_html += f"""<tr style="border-bottom:1px solid #21262d;">
            <td style="padding:0.6rem 0.75rem;font-family:Outfit,sans-serif;font-size:0.9rem;"><span style="color:#e6edf3;font-weight:500;">{home}</span><span style="color:#8b949e;margin:0 0.4rem;">vs</span><span style="color:#e6edf3;font-weight:500;">{away}</span></td>
            <td style="padding:0.6rem 0.75rem;color:#8b949e;font-size:0.85rem;">{pred.get("venue","")}</td>
            <td style="padding:0.6rem 0.75rem;color:#8b949e;font-size:0.85rem;font-family:DM Mono,monospace;">{pred.get("date","")}</td>
            <td style="padding:0.6rem 0.75rem;">{winner_cell}</td>
            <td style="padding:0.6rem 0.75rem;text-align:center;">{prob_cell}</td>
            <td style="padding:0.6rem 0.75rem;text-align:center;">{margin_cell}</td>
            <td style="padding:0.6rem 0.75rem;text-align:center;">{conf_badge}</td>
        </tr>"""

    st.markdown(f"""
    <div style="background:#161b22;border:1px solid #30363d;border-radius:8px;overflow:hidden;margin-bottom:2rem;">
        <div style="padding:0.75rem 1rem;border-bottom:1px solid #30363d;font-family:Barlow Condensed,sans-serif;font-size:0.85rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#e8b44b;">⚡ Round Summary — All Tips At A Glance</div>
        <table style="width:100%;border-collapse:collapse;">
            <thead><tr style="background:#1c2128;">
                <th style="padding:0.5rem 0.75rem;text-align:left;font-family:Barlow Condensed,sans-serif;font-size:0.8rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#8b949e;">Match</th>
                <th style="padding:0.5rem 0.75rem;text-align:left;font-family:Barlow Condensed,sans-serif;font-size:0.8rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#8b949e;">Venue</th>
                <th style="padding:0.5rem 0.75rem;text-align:left;font-family:Barlow Condensed,sans-serif;font-size:0.8rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#8b949e;">Date</th>
                <th style="padding:0.5rem 0.75rem;text-align:left;font-family:Barlow Condensed,sans-serif;font-size:0.8rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#8b949e;">Our Tip</th>
                <th style="padding:0.5rem 0.75rem;text-align:center;font-family:Barlow Condensed,sans-serif;font-size:0.8rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#8b949e;">Prob %</th>
                <th style="padding:0.5rem 0.75rem;text-align:center;font-family:Barlow Condensed,sans-serif;font-size:0.8rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#8b949e;">Margin</th>
                <th style="padding:0.5rem 0.75rem;text-align:center;font-family:Barlow Condensed,sans-serif;font-size:0.8rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#8b949e;">Confidence</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)


# ─── Match countdown ──────────────────────────────────────────────────────────

def render_countdown(game_date_str, game_id):
    dt_str = game_date_str[:19] if len(game_date_str) > 10 else f"{game_date_str}T12:00:00"
    components.html(f"""
    <div id="cd_{game_id}" style="display:inline-block;background:#1c2128;border:1px solid #30363d;border-radius:4px;padding:0.3rem 0.75rem;font-family:DM Mono,monospace;font-size:0.8rem;color:#8b949e;margin-bottom:0.5rem;">⏱ Loading...</div>
    <script>
    (function(){{
        const gt=new Date('{dt_str}');
        const el=document.getElementById('cd_{game_id}');
        function u(){{
            const now=new Date(),diff=gt-now;
            if(diff<=0){{el.innerHTML='🔒 LOCKED';el.style.color='#f85149';el.style.borderColor='#f85149';return;}}
            const d=Math.floor(diff/86400000),h=Math.floor((diff%86400000)/3600000),m=Math.floor((diff%3600000)/60000),s=Math.floor((diff%60000)/1000);
            const p=[];if(d>0)p.push(d+'d');p.push(String(h).padStart(2,'0')+'h');p.push(String(m).padStart(2,'0')+'m');p.push(String(s).padStart(2,'0')+'s');
            el.innerHTML='⏱ Lockout in '+p.join(' ');
        }}
        u();setInterval(u,1000);
    }})();
    </script>
    """, height=40)


# ─── Prediction card ──────────────────────────────────────────────────────────

def render_prediction_card(pred, idx):
    home     = pred["home_team"]
    away     = pred["away_team"]
    text     = pred["prediction"]
    conf     = extract_confidence(text)
    winner   = extract_winner(text, home, away)
    prob     = extract_probability(text, winner)
    margin   = extract_margin(text)
    style    = confidence_style(conf)
    odds     = pred.get("betting_odds", {})
    h_rest   = pred.get("home_rest", {})
    a_rest   = pred.get("away_rest", {})
    h_travel = pred.get("home_travel", {})
    a_travel = pred.get("away_travel", {})
    h_score  = pred.get("home_scoring", {})
    a_score  = pred.get("away_scoring", {})

    def travel_badge(t):
        if not t: return ""
        l = t.get("fatigue_level","none")
        if l == "high":   return "<span style='color:#f85149;font-size:0.78rem;'>✈️ LONG-HAUL</span>"
        if l == "medium": return "<span style='color:#d29922;font-size:0.78rem;'>✈️ TRAVELLING</span>"
        return ""

    def rest_badge(r):
        if not r: return ""
        d = r.get("days")
        if d and d <= 6: return f"<span style='color:#f85149;font-size:0.78rem;'>⚠️ {d}d REST</span>"
        if d:            return f"<span style='color:#8b949e;font-size:0.78rem;'>{d}d rest</span>"
        return ""

    def trend_badge(s):
        if not s: return ""
        atk = s.get("attack_trend","stable")
        if "improving" in atk: return "<span style='color:#3fb950;font-size:0.78rem;'>📈 ATK ↑</span>"
        if "declining"  in atk: return "<span style='color:#f85149;font-size:0.78rem;'>📉 ATK ↓</span>"
        return ""

    hb = " ".join(filter(None, [travel_badge(h_travel), rest_badge(h_rest), trend_badge(h_score)]))
    ab = " ".join(filter(None, [travel_badge(a_travel), rest_badge(a_rest), trend_badge(a_score)]))
    prob_d   = f"{prob:.0f}%" if prob else ""
    margin_d = f"~{margin} pts" if margin else ""

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{style['bg']} 0%,#161b22 100%);border:1px solid #30363d;border-left:4px solid {style['color']};border-radius:8px;padding:1.25rem 1.5rem 0.75rem;margin-bottom:0.25rem;">
        <div style="font-family:Barlow Condensed,sans-serif;font-size:0.8rem;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#8b949e;margin-bottom:0.5rem;">Round {pred.get('round','')} &nbsp;·&nbsp; {pred.get('venue','')} &nbsp;·&nbsp; {pred.get('date','')}</div>
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;flex-wrap:wrap;">
            <div style="flex:1;min-width:200px;">
                <div style="font-family:Barlow Condensed,sans-serif;font-size:2rem;font-weight:800;color:#e6edf3;line-height:1.1;margin-bottom:0.35rem;">
                    🏠 {home} <span style="color:#30363d;font-size:1.2rem;margin:0 0.5rem;">vs</span> ✈️ {away}
                </div>
                <div style="display:flex;gap:0.75rem;flex-wrap:wrap;align-items:center;">
                    <span style="font-size:0.78rem;color:#8b949e;">{home}:</span> {hb}
                    &nbsp;&nbsp;
                    <span style="font-size:0.78rem;color:#8b949e;">{away}:</span> {ab}
                </div>
            </div>
            <div style="background:#0d1117;border:1px solid {style['color']}44;border-radius:6px;padding:0.75rem 1rem;text-align:center;min-width:155px;">
                <div style="font-family:Barlow Condensed,sans-serif;font-size:0.7rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:{style['color']};margin-bottom:0.25rem;">{style['label']}</div>
                <div style="font-family:Barlow Condensed,sans-serif;font-size:1.4rem;font-weight:800;color:#e6edf3;line-height:1.1;">{"⚡ " + winner if winner else "—"}</div>
                <div style="font-family:DM Mono,monospace;font-size:0.9rem;color:{style['color']};margin-top:0.2rem;">{prob_d}</div>
                <div style="font-family:DM Mono,monospace;font-size:0.78rem;color:#8b949e;margin-top:0.1rem;">{margin_d}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    date_full = pred.get("date_full") or pred.get("date", "")
    render_countdown(date_full, f"{idx}_{home[:3]}{away[:3]}")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if odds.get("home_odds"):
            st.metric(f"🏠 {home} Odds", f"${odds['home_odds']}", f"{odds.get('home_implied_prob','')}% implied")
    with c2:
        if odds.get("away_odds"):
            st.metric(f"✈️ {away} Odds", f"${odds['away_odds']}", f"{odds.get('away_implied_prob','')}% implied")
    with c3:
        if h_score.get("avg_for_5"):
            st.metric(f"{home} Avg Score", f"{h_score['avg_for_5']} pts", f"Last 3: {h_score.get('avg_for_3','?')} pts")
    with c4:
        if a_score.get("avg_for_5"):
            st.metric(f"{away} Avg Score", f"{a_score['avg_for_5']} pts", f"Last 3: {a_score.get('avg_for_3','?')} pts")

    if odds.get("line_summary") or odds.get("total_summary"):
        parts = []
        if odds.get("line_summary"):  parts.append(f"📊 Line: {odds['line_summary']}")
        if odds.get("total_summary"): parts.append(f"🔢 {odds['total_summary']}")
        st.markdown(
            f"<div style='font-family:DM Mono,monospace;font-size:0.82rem;color:#8b949e;padding:0.3rem 0;'>"
            + "  &nbsp;·&nbsp;  ".join(parts) + "</div>",
            unsafe_allow_html=True
        )

    with st.expander("📋 Full AI Analysis", expanded=False):
        st.markdown(
            f"<div style='font-family:Outfit,sans-serif;font-size:0.9rem;line-height:1.7;color:#c9d1d9;'>"
            f"{text.replace(chr(10), '<br>')}</div>",
            unsafe_allow_html=True
        )
    st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# APP HEADER
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="border-bottom:1px solid #21262d;padding-bottom:1rem;margin-bottom:0.5rem;display:flex;align-items:baseline;gap:1rem;flex-wrap:wrap;">
    <span style="font-family:Barlow Condensed,sans-serif;font-size:2.8rem;font-weight:800;color:#e6edf3;">🏉 AFL TIPPING AGENT</span>
    <span style="font-family:DM Mono,monospace;font-size:0.8rem;color:#e8b44b;letter-spacing:0.05em;">DATA-DRIVEN · UNBIASED · AI-POWERED</span>
</div>
""", unsafe_allow_html=True)

render_performance_banner()

tab1, tab2, tab3, tab4 = st.tabs([
    "🏉  This Week's Tips",
    "📊  Accuracy Tracker",
    "📰  Team News",
    "🔄  Update Results",
])


# ── TAB 1: WEEKLY TIPS ────────────────────────────────────────────────────────
with tab1:
    col_main, col_side = st.columns([4, 1])

    with col_side:
        st.markdown("<div style='font-family:Barlow Condensed,sans-serif;font-size:0.75rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#8b949e;margin-bottom:0.75rem;'>Data Sources</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-family:Outfit,sans-serif;font-size:0.82rem;color:#8b949e;line-height:2;'>📊 Squiggle API<br>💰 Odds (h2h + line + totals)<br>🤖 Squiggle model cross-check<br>🌤️ Open-Meteo weather<br>📰 Zero Hanger team news<br>✈️ Travel & rest analysis<br>📈 Scoring trends<br>🧠 Season accuracy history</div>", unsafe_allow_html=True)
        st.divider()
        st.markdown("<div style='font-family:Outfit,sans-serif;font-size:0.75rem;color:#484f58;line-height:1.6;'>For entertainment only.<br>Please gamble responsibly.</div>", unsafe_allow_html=True)

    with col_main:
        run_btn = st.button("⚡ GENERATE THIS WEEK'S TIPS", type="primary")

        if run_btn:
            with st.spinner("Fetching fixtures and market data..."):
                fixtures = get_upcoming_fixtures()
                ladder   = get_ladder()
                odds     = get_betting_odds()
                news     = get_afl_news()

            if not fixtures:
                st.warning("No upcoming fixtures found. Check back closer to round start.")
            else:
                st.markdown(f"<div style='font-family:Barlow Condensed,sans-serif;font-size:1rem;font-weight:600;letter-spacing:0.05em;color:#3fb950;margin-bottom:1rem;'>✅ {len(fixtures)} GAMES THIS WEEK — GENERATING PREDICTIONS...</div>", unsafe_allow_html=True)

                match_data_list = []
                bar = st.progress(0, text="Gathering match data...")
                for i, game in enumerate(fixtures):
                    bar.progress((i+1)/len(fixtures), text=f"Loading: {game.get('hteam')} vs {game.get('ateam')}")
                    match_data_list.append(compile_match_data(game, ladder, odds))
                bar.empty()

                with st.spinner("🤖 AI analysing all matches..."):
                    predictions = run_weekly_predictions(match_data_list, news)

                if predictions:
                    round_num = predictions[0]["round"]
                    high   = sum(1 for p in predictions if extract_confidence(p["prediction"]) == "High")
                    medium = sum(1 for p in predictions if extract_confidence(p["prediction"]) == "Medium")
                    low    = sum(1 for p in predictions if extract_confidence(p["prediction"]) == "Low")

                    st.markdown(f"""
                    <div style="font-family:Barlow Condensed,sans-serif;font-size:2.2rem;font-weight:800;color:#e8b44b;letter-spacing:0.03em;margin-bottom:0.5rem;">ROUND {round_num} PREDICTIONS</div>
                    <div style="display:flex;gap:1rem;margin-bottom:1.5rem;flex-wrap:wrap;">
                        <span style="background:rgba(63,185,80,0.1);border:1px solid rgba(63,185,80,0.3);color:#3fb950;padding:0.3rem 0.75rem;border-radius:4px;font-family:Barlow Condensed,sans-serif;font-weight:700;font-size:0.85rem;letter-spacing:0.05em;">🟢 HIGH: {high}</span>
                        <span style="background:rgba(210,153,34,0.1);border:1px solid rgba(210,153,34,0.3);color:#d29922;padding:0.3rem 0.75rem;border-radius:4px;font-family:Barlow Condensed,sans-serif;font-weight:700;font-size:0.85rem;letter-spacing:0.05em;">🟡 MEDIUM: {medium}</span>
                        <span style="background:rgba(248,81,73,0.1);border:1px solid rgba(248,81,73,0.3);color:#f85149;padding:0.3rem 0.75rem;border-radius:4px;font-family:Barlow Condensed,sans-serif;font-weight:700;font-size:0.85rem;letter-spacing:0.05em;">🔴 LOW: {low}</span>
                    </div>
                    """, unsafe_allow_html=True)

                    render_summary_table(predictions)

                    st.markdown("<div style='font-family:Barlow Condensed,sans-serif;font-size:0.8rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#8b949e;margin-bottom:1rem;'>── Detailed Match Analysis ──</div>", unsafe_allow_html=True)
                    for i, pred in enumerate(predictions):
                        render_prediction_card(pred, i)

        else:
            st.markdown("""
            <div style="background:linear-gradient(135deg,#161b22 0%,#1c2128 100%);border:1px solid #30363d;border-radius:8px;padding:2.5rem;margin:1rem 0 2rem;text-align:center;">
                <div style="font-family:Barlow Condensed,sans-serif;font-size:3rem;font-weight:800;color:#e8b44b;letter-spacing:0.02em;margin-bottom:0.5rem;">ROUND PREDICTIONS</div>
                <div style="font-family:Outfit,sans-serif;font-size:1rem;color:#8b949e;max-width:500px;margin:0 auto;">Click the button above to generate this week's data-driven AFL predictions.</div>
            </div>
            """, unsafe_allow_html=True)

            c1, c2, c3, c4 = st.columns(4)
            for col, (icon, title, desc) in zip([c1,c2,c3,c4], [
                ("📊","Stats & Form",    "Ladder · Last 5 results with margins · H2H · Venue records · Scoring averages"),
                ("💰","Betting Markets", "Win/loss odds · Line market · Totals market · Implied probabilities"),
                ("✈️","Fatigue Factors","Days since last game · Travel distance · Short turnaround flags · Perth long-haul alerts"),
                ("🧠","Self-Learning",   "Tracks its own accuracy · Learns from past mistakes · Improves each round"),
            ]):
                with col:
                    st.markdown(f"""<div style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:1.25rem;">
                        <div style="font-size:1.5rem;margin-bottom:0.5rem;">{icon}</div>
                        <div style="font-family:Barlow Condensed,sans-serif;font-size:1rem;font-weight:700;letter-spacing:0.05em;text-transform:uppercase;color:#e8b44b;margin-bottom:0.5rem;">{title}</div>
                        <div style="font-family:Outfit,sans-serif;font-size:0.82rem;color:#8b949e;line-height:1.6;">{desc}</div>
                    </div>""", unsafe_allow_html=True)


# ── TAB 2: ACCURACY TRACKER ───────────────────────────────────────────────────
with tab2:
    st.markdown("<h2 style='margin-bottom:0.25rem;'>Season Accuracy Tracker</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#8b949e;font-size:0.9rem;margin-bottom:1.5rem;'>Every prediction tracked against real results. Used to improve future tips.</p>", unsafe_allow_html=True)

    data      = get_accuracy_display_data()
    accuracy  = data["accuracy_summary"]
    completed = data["completed_predictions"]
    pending   = data["pending_predictions"]

    if not completed and not pending:
        st.info("No predictions saved yet. Generate your first round of tips to start tracking.")
    else:
        if accuracy:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Season Correct",   f"{accuracy.get('overall_correct',0)}/{accuracy.get('overall_total',0)}")
            m2.metric("Overall Accuracy", f"{accuracy.get('overall_accuracy_pct',0)}%")
            fav = accuracy.get("favourite_picks", {})
            if fav.get("total", 0) > 0:
                m3.metric("Fav Pick Accuracy", f"{round(fav['correct']/fav['total']*100,1)}%", f"{fav['correct']}/{fav['total']}")
            upset = accuracy.get("upset_picks", {})
            if upset.get("total", 0) > 0:
                m4.metric("Underdog Accuracy", f"{round(upset['correct']/upset['total']*100,1)}%", f"{upset['correct']}/{upset['total']}")
            by_round = accuracy.get("by_round", {})
            if by_round:
                st.divider()
                st.markdown("<h3>Round by Round</h3>", unsafe_allow_html=True)
                chart_data = pd.DataFrame([
                    {"Round": f"Rd {r}", "Accuracy %": v["pct"]}
                    for r, v in sorted(by_round.items(), key=lambda x: int(x[0]))
                ])
                st.bar_chart(chart_data.set_index("Round")["Accuracy %"])

        if completed:
            st.divider()
            st.markdown(f"<h3>Completed Predictions ({len(completed)})</h3>", unsafe_allow_html=True)
            rows = [{"Rd": p["round"], "Match": f"{p['home_team']} vs {p['away_team']}", "Tipped": p["predicted_winner"],
                     "Prob": f"{p['predicted_probability']:.0f}%" if p.get("predicted_probability") else "–",
                     "Actual": p["actual_winner"], "Margin": f"{p.get('actual_margin','?')} pts",
                     "✓": "✅" if p["correct"] else "❌"}
                    for p in sorted(completed, key=lambda x: (x.get("year",0), int(x.get("round",0))), reverse=True)]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        if pending:
            st.divider()
            st.markdown(f"<h3>Awaiting Results ({len(pending)})</h3>", unsafe_allow_html=True)
            rows = [{"Rd": p["round"], "Match": f"{p['home_team']} vs {p['away_team']}", "Tipped": p["predicted_winner"],
                     "Prob": f"{p['predicted_probability']:.0f}%" if p.get("predicted_probability") else "–",
                     "Date": p.get("date","")} for p in pending]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ── TAB 3: TEAM NEWS ──────────────────────────────────────────────────────────
with tab3:
    st.markdown("<h2 style='margin-bottom:0.25rem;'>Team News, Injuries & Selections</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#8b949e;font-size:0.9rem;margin-bottom:1.5rem;'>Sourced from <strong style='color:#e6edf3;'>Zero Hanger</strong> — Australia's leading independent AFL news site. Covers all 18 clubs: injuries, MRO decisions, suspensions, and team selection.</p>", unsafe_allow_html=True)

    c1, c2 = st.columns([3, 1])
    with c1:
        selected_team = st.selectbox("Filter by team", options=["All Teams"] + sorted(TEAM_URLS.keys()))
    with c2:
        st.markdown("<div style='height:1.9rem;'></div>", unsafe_allow_html=True)
        fetch_btn = st.button("🔄 Fetch Latest News", type="primary")

    if fetch_btn:
        with st.spinner("Fetching team news from Zero Hanger..."):
            if selected_team == "All Teams":
                all_news = get_all_teams_news_summary()
            else:
                from team_news import get_team_news
                all_news = get_team_news(selected_team, days_back=21)

        if not all_news:
            st.warning("No relevant news found. Zero Hanger is updated daily — try again later, or check back Thursday–Friday when squads are named.")
        else:
            st.markdown(f"<div style='font-family:Barlow Condensed,sans-serif;font-size:0.9rem;font-weight:600;letter-spacing:0.05em;color:#3fb950;margin-bottom:1rem;'>✅ {len(all_news)} relevant articles found</div>", unsafe_allow_html=True)
            for article in all_news:
                team_label = article.get('team', '')
                source     = article.get('source', 'Zero Hanger')
                header     = f"**{team_label}** — {article['title']}" if team_label and team_label != "General" else article['title']
                with st.expander(header, expanded=False):
                    st.markdown(article["summary"])
                    st.caption(f"Source: {source}  ·  Published: {article.get('published', 'Unknown')}")
    else:
        st.markdown("""<div style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:1.25rem;color:#8b949e;font-size:0.9rem;line-height:1.8;">
            <strong style="color:#e8b44b;">Best times to fetch:</strong><br>
            🗓️ <strong style="color:#e6edf3;">Thursday</strong> — Initial squads named<br>
            🗓️ <strong style="color:#e6edf3;">Friday</strong> — Final teams confirmed<br>
            🗓️ <strong style="color:#e6edf3;">Any time</strong> — MRO charges, injury updates &amp; tribunal news
        </div>""", unsafe_allow_html=True)


# ── TAB 4: UPDATE RESULTS ─────────────────────────────────────────────────────
with tab4:
    st.markdown("<h2 style='margin-bottom:0.25rem;'>Update Results</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#8b949e;font-size:0.9rem;margin-bottom:1.5rem;'>Run Monday or Tuesday after each round to record results and improve future predictions.</p>", unsafe_allow_html=True)

    st.markdown("""<div style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:1.25rem;margin-bottom:1.5rem;color:#8b949e;font-size:0.9rem;line-height:1.8;">
        <strong style="color:#e8b44b;">Weekly workflow:</strong><br>
        1️⃣ &nbsp; Monday/Tuesday — click below to record last round's results<br>
        2️⃣ &nbsp; Thursday night — fetch team news, then generate tips<br>
        3️⃣ &nbsp; Before lockout — review and submit your picks
    </div>""", unsafe_allow_html=True)

    if st.button("🔄 CHECK RESULTS & UPDATE HISTORY", type="primary"):
        with st.spinner("Fetching results from Squiggle..."):
            summary = check_and_update_results()
        if summary:
            st.success("Results updated!")
            c1, c2, c3 = st.columns(3)
            c1.metric("Season Accuracy", f"{summary.get('overall_accuracy_pct',0)}%")
            c2.metric("Total Correct",   f"{summary.get('overall_correct',0)}/{summary.get('overall_total',0)}")
            by_round = summary.get("by_round", {})
            if by_round:
                latest = max(by_round.keys(), key=lambda x: int(x))
                r = by_round[latest]
                c3.metric(f"Round {latest}", f"{r['pct']}%", f"{r['correct']}/{r['total']}")
            st.balloons()
            st.info("✅ History updated. The agent will use this to improve next week's tips.")
        else:
            st.info("No results to update yet — games may not have completed, or no predictions are saved.")

    st.divider()
    st.markdown("<h3>History File Status</h3>", unsafe_allow_html=True)
    history       = load_history()
    total_saved   = len(history.get("predictions", []))
    total_checked = len([p for p in history.get("predictions", []) if p.get("correct") is not None])
    c1, c2, c3 = st.columns(3)
    c1.metric("Predictions Saved", total_saved)
    c2.metric("Results Checked",   total_checked)
    c3.metric("Awaiting Results",  total_saved - total_checked)

    if total_saved > 0:
        st.download_button(
            label="📥 Download predictions_history.json",
            data=json.dumps(history, indent=2),
            file_name="predictions_history.json",
            mime="application/json"
        )
