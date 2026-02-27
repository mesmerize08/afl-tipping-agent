import streamlit as st
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

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="🏉 AFL Tipping Agent",
    page_icon="🏉",
    layout="wide"
)

st.title("🏉 AFL AI Tipping Agent")
st.caption(f"Data-driven predictions powered by real-time stats, form, and AI analysis")

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Controls")
    
    run_btn = st.button("🔄 Generate This Week's Tips", type="primary", use_container_width=True)
    
    st.divider()
    st.markdown("**Data Sources:**")
    st.markdown("- 📊 Squiggle API (form, ladder, H2H)")
    st.markdown("- 💰 The Odds API (betting markets)")
    st.markdown("- 📰 AFL.com.au (news & team updates)")
    st.markdown("- 🤖 Google Gemini AI (analysis)")
    
    st.divider()
    st.caption("Predictions are for entertainment only. Please gamble responsibly.")

# ── Main content ──────────────────────────────────────────────
if run_btn:
    with st.spinner("Fetching fixtures and data..."):
        fixtures = get_upcoming_fixtures()
        ladder = get_ladder()
        odds = get_betting_odds()
        news = get_afl_news()
    
    if not fixtures:
        st.warning("No upcoming fixtures found for this week. Check back closer to the round start.")
    else:
        st.success(f"Found {len(fixtures)} games this week!")
        
        # Compile all match data
        match_data_list = []
        progress = st.progress(0, text="Gathering match data...")
        for i, game in enumerate(fixtures):
            match_data = compile_match_data(game, ladder, odds)
            match_data_list.append(match_data)
            progress.progress((i+1)/len(fixtures), text=f"Loading data: {game.get('hteam')} vs {game.get('ateam')}")
        
        # Run AI predictions
        with st.spinner("🤖 AI is analysing all matches..."):
            predictions = run_weekly_predictions(match_data_list, news)
        
        progress.empty()
        st.divider()
        
        # Display round header
        if predictions:
            st.header(f"Round {predictions[0]['round']} Predictions")
        
        # Display each prediction
        for pred in predictions:
            home = pred["home_team"]
            away = pred["away_team"]
            odds_data = pred.get("betting_odds", {})
            
            with st.expander(f"🏉 **{home}** vs **{away}**  —  {pred['date']} at {pred['venue']}", expanded=True):
                
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.markdown(f"**🏠 {home}** *(Home)*")
                    if odds_data:
                        st.metric("Odds", f"${odds_data.get('home_odds', 'N/A')}", 
                                 f"{odds_data.get('home_implied_prob', '')}% implied")
                
                with col2:
                    st.markdown(f"**✈️ {away}** *(Away)*")
                    if odds_data:
                        st.metric("Odds", f"${odds_data.get('away_odds', 'N/A')}",
                                 f"{odds_data.get('away_implied_prob', '')}% implied")
                
                with col3:
                    st.markdown(f"**📍 Venue**")
                    st.markdown(pred["venue"])
                
                st.divider()
                st.markdown(pred["prediction"])

# ── Show info if not yet run ───────────────────────────────────
else:
    st.info("👈 Click **Generate This Week's Tips** in the sidebar to get started!")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 📊 What it analyses")
        st.markdown("""
- Current ladder positions
- Last 5 games form
- Head-to-head history  
- Venue/ground records
- Home vs away patterns
        """)
    with col2:
        st.markdown("### 💰 Market data")
        st.markdown("""
- Live betting odds
- Implied probabilities
- Market consensus
- Odds movements (context)
        """)
    with col3:
        st.markdown("### 🤖 AI output")
        st.markdown("""
- Predicted winner
- Win probability %
- Expected margin
- Key deciding factors
- Confidence rating
        """)