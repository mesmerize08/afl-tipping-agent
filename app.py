"""
app.py  (UPDATED — accuracy dashboard + team news tab)
=======================================================
Streamlit web app for the AFL AI Tipping Agent.

New tabs:
  🏉 This Week's Tips   — predictions as before
  📊 Accuracy Tracker   — season-long accuracy dashboard
  📰 Team News          — latest injuries & selections across all teams
  🔄 Update Results     — manually trigger result-checking after each round
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from data_fetcher import (
    get_upcoming_fixtures, get_ladder,
    get_betting_odds, get_afl_news, compile_match_data
)
from predict import run_weekly_predictions
from tracker import (
    check_and_update_results,
    get_accuracy_display_data,
    load_history
)
from team_news import get_all_teams_news_summary, TEAM_URLS

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🏉 AFL Tipping Agent",
    page_icon="🏉",
    layout="wide"
)

st.title("🏉 AFL AI Tipping Agent")
st.caption("Data-driven predictions · Accuracy tracking · Team news · Powered by real-time data + AI")

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🏉 This Week's Tips",
    "📊 Accuracy Tracker",
    "📰 Team News & Injuries",
    "🔄 Update Results"
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — WEEKLY TIPS
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    col_main, col_side = st.columns([3, 1])

    with col_side:
        st.markdown("### ⚙️ Controls")
        run_btn = st.button("🔄 Generate This Week's Tips", type="primary", use_container_width=True)
        st.divider()
        st.markdown("**Data sources used:**")
        st.markdown("- 📊 Squiggle (form, ladder, H2H)")
        st.markdown("- 💰 The Odds API (betting markets)")
        st.markdown("- 📰 AFL news (team selections)")
        st.markdown("- 🧠 Own history (past accuracy)")
        st.markdown("- 🤖 Google Gemini AI (analysis)")
        st.divider()
        st.caption("For entertainment only. Please gamble responsibly.")

    with col_main:
        if run_btn:
            with st.spinner("Fetching fixtures..."):
                fixtures  = get_upcoming_fixtures()
                ladder    = get_ladder()
                odds      = get_betting_odds()
                news      = get_afl_news()

            if not fixtures:
                st.warning("No upcoming fixtures found. Check back closer to round start.")
            else:
                st.success(f"Found {len(fixtures)} games this week!")

                match_data_list = []
                progress = st.progress(0, text="Gathering match data...")
                for i, game in enumerate(fixtures):
                    match_data = compile_match_data(game, ladder, odds)
                    match_data_list.append(match_data)
                    progress.progress(
                        (i + 1) / len(fixtures),
                        text=f"Loading: {game.get('hteam')} vs {game.get('ateam')}"
                    )
                progress.empty()

                with st.spinner("🤖 AI is analysing all matches (including team news & history)..."):
                    predictions = run_weekly_predictions(match_data_list, news)

                st.divider()

                if predictions:
                    st.header(f"Round {predictions[0]['round']} Predictions")

                for pred in predictions:
                    home      = pred["home_team"]
                    away      = pred["away_team"]
                    odds_data = pred.get("betting_odds", {})

                    with st.expander(
                        f"🏉 **{home}** vs **{away}**  —  {pred['date']} at {pred['venue']}",
                        expanded=True
                    ):
                        c1, c2, c3 = st.columns([2, 2, 1])
                        with c1:
                            st.markdown(f"**🏠 {home}** *(Home)*")
                            if odds_data:
                                st.metric("Odds", f"${odds_data.get('home_odds','N/A')}",
                                          f"{odds_data.get('home_implied_prob','')}% implied")
                        with c2:
                            st.markdown(f"**✈️ {away}** *(Away)*")
                            if odds_data:
                                st.metric("Odds", f"${odds_data.get('away_odds','N/A')}",
                                          f"{odds_data.get('away_implied_prob','')}% implied")
                        with c3:
                            st.markdown(f"**📍 Venue**")
                            st.markdown(pred["venue"])

                        st.divider()
                        st.markdown(pred["prediction"])
        else:
            st.info("👈 Click **Generate This Week's Tips** to get started!")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("### 📊 What it analyses")
                st.markdown("Current ladder · Last 5 games form · Head-to-head history · Venue/ground records · Home vs away patterns · Betting market odds & implied probabilities")
            with c2:
                st.markdown("### 🏥 Team news")
                st.markdown("Injury reports · Team selections · Suspensions · Key player returns · Debutants")
            with c3:
                st.markdown("### 🧠 Self-learning")
                st.markdown("Agent reviews its own past accuracy · Adjusts confidence based on what it's got wrong · Improves as the season progresses")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — ACCURACY TRACKER
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.header("📊 Season Accuracy Tracker")
    st.caption("Tracks every prediction and compares it to the actual result after each round.")

    data = get_accuracy_display_data()
    accuracy = data["accuracy_summary"]
    completed = data["completed_predictions"]
    pending   = data["pending_predictions"]

    if not completed and not pending:
        st.info("No predictions saved yet. Generate your first round of tips to start tracking!")
    else:
        # ── Season summary metrics ──
        if accuracy:
            st.subheader("Season Overview")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Correct",   f"{accuracy.get('overall_correct', 0)}/{accuracy.get('overall_total', 0)}")
            m2.metric("Accuracy %",      f"{accuracy.get('overall_accuracy_pct', 0)}%")

            fav = accuracy.get("favourite_picks", {})
            if fav.get("total", 0) > 0:
                fav_pct = round((fav["correct"] / fav["total"]) * 100, 1)
                m3.metric("Favourite Pick Accuracy", f"{fav_pct}%", f"{fav['correct']}/{fav['total']}")

            upset = accuracy.get("upset_picks", {})
            if upset.get("total", 0) > 0:
                upset_pct = round((upset["correct"] / upset["total"]) * 100, 1)
                m4.metric("Underdog Pick Accuracy", f"{upset_pct}%", f"{upset['correct']}/{upset['total']}")

            # ── Round-by-round chart ──
            by_round = accuracy.get("by_round", {})
            if by_round:
                st.subheader("Round by Round")
                chart_data = pd.DataFrame([
                    {
                        "Round": f"Rd {r}",
                        "Correct": v["correct"],
                        "Total": v["total"],
                        "Accuracy %": v["pct"]
                    }
                    for r, v in sorted(by_round.items(), key=lambda x: int(x[0]))
                ])
                st.bar_chart(chart_data.set_index("Round")["Accuracy %"])
                st.dataframe(chart_data, use_container_width=True, hide_index=True)

        st.divider()

        # ── Completed predictions table ──
        if completed:
            st.subheader(f"Completed Predictions ({len(completed)})")
            rows = []
            for p in sorted(completed, key=lambda x: (x.get("year", 0), int(x.get("round", 0))), reverse=True):
                rows.append({
                    "Round":     p["round"],
                    "Date":      p.get("date", ""),
                    "Match":     f"{p['home_team']} vs {p['away_team']}",
                    "Tipped":    p["predicted_winner"],
                    "Prob %":    f"{p['predicted_probability']:.0f}%" if p.get("predicted_probability") else "–",
                    "Actual":    p["actual_winner"],
                    "Margin":    f"{p.get('actual_margin', '?')} pts",
                    "Result":    "✅" if p["correct"] else "❌"
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # ── Pending predictions ──
        if pending:
            st.subheader(f"Awaiting Results ({len(pending)} games)")
            rows = []
            for p in pending:
                rows.append({
                    "Round": p["round"],
                    "Match": f"{p['home_team']} vs {p['away_team']}",
                    "Tipped": p["predicted_winner"],
                    "Prob %": f"{p['predicted_probability']:.0f}%" if p.get("predicted_probability") else "–",
                    "Date":  p.get("date", "")
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — TEAM NEWS & INJURIES
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.header("📰 Team News, Injuries & Selections")
    st.caption("Scraped from AFL.com.au team pages. Updates when you refresh.")

    selected_team = st.selectbox(
        "Filter by team (or view all)",
        options=["All Teams"] + sorted(TEAM_URLS.keys())
    )

    fetch_news_btn = st.button("🔄 Fetch Latest Team News", type="secondary")

    if fetch_news_btn:
        with st.spinner("Fetching team news from AFL.com.au..."):
            if selected_team == "All Teams":
                all_news = get_all_teams_news_summary()
            else:
                from team_news import get_team_news
                all_news = get_team_news(selected_team, days_back=7)

        if not all_news:
            st.warning("No recent injury/selection news found. Try again on Thursday when teams name their squads.")
        else:
            st.success(f"Found {len(all_news)} relevant articles!")
            for article in all_news:
                team_label = article.get("team", "")
                with st.expander(f"**{team_label}** — {article['title']}", expanded=False):
                    st.markdown(article["summary"])
                    st.caption(f"Published: {article.get('published', 'Unknown')}")
    else:
        st.info("Click **Fetch Latest Team News** to load injury and selection news.")
        st.markdown("""
**Team news is typically published:**
- 🗓️ **Thursday** — Squads named (check for key ins and outs)
- 🗓️ **Friday** — Final teams locked in
- 🗓️ **Anytime** — Injury updates and suspension decisions
        """)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — UPDATE RESULTS
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.header("🔄 Update Results After Each Round")
    st.caption(
        "Run this on Monday or Tuesday after each round to check your predictions "
        "against real results. The agent uses this data to improve future predictions."
    )

    st.markdown("""
**When to run this:**
- ✅ Monday or Tuesday after each round completes
- ✅ After all games in a round have been played
- ✅ Before generating tips for the next round (so history is up to date)
    """)

    update_btn = st.button("🔄 Check Results & Update History", type="primary")

    if update_btn:
        with st.spinner("Fetching results from Squiggle and comparing to predictions..."):
            summary = check_and_update_results()

        if summary:
            st.success("Results updated!")
            col1, col2 = st.columns(2)
            col1.metric("Season Accuracy",
                        f"{summary.get('overall_accuracy_pct', 0)}%",
                        f"{summary.get('overall_correct', 0)}/{summary.get('overall_total', 0)} correct")

            by_round = summary.get("by_round", {})
            if by_round:
                latest_round = max(by_round.keys(), key=lambda x: int(x))
                r = by_round[latest_round]
                col2.metric(f"Round {latest_round}",
                            f"{r['pct']}%",
                            f"{r['correct']}/{r['total']} correct")

            st.balloons()
            st.info("✅ History updated! The agent will use this data to improve next week's predictions.")
        else:
            st.info("No results to update yet — games may not have been played, or no predictions are saved.")

    # ── Show current history file status ──
    st.divider()
    st.subheader("📁 Prediction History File")
    history = load_history()
    total_saved = len(history.get("predictions", []))
    total_checked = len([p for p in history.get("predictions", []) if p.get("correct") is not None])

    st.markdown(f"- **Total predictions saved:** {total_saved}")
    st.markdown(f"- **Results checked:** {total_checked}")
    st.markdown(f"- **Awaiting results:** {total_saved - total_checked}")
    st.markdown("- **File location:** `predictions_history.json` in your project folder")

    if total_saved > 0:
        if st.button("📥 Download History as JSON"):
            history_json = json.dumps(history, indent=2)
            st.download_button(
                label="Download predictions_history.json",
                data=history_json,
                file_name="predictions_history.json",
                mime="application/json"
            )
