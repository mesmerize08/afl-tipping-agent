# 🏉 AFL AI Tipping Agent

> A fully automated, data-driven AFL tipping agent that analyses betting markets, team form, scoring trends, weather, travel fatigue and more — then uses AI to generate weekly match predictions with win probabilities and explanations.

**Live app:** [afl-tipping-agent.streamlit.app](https://afl-tipping-agent.streamlit.app)

---

## What It Does

Every week during the AFL season, this agent:

1. Fetches fixtures, ladder standings, form, and head-to-head records from the Squiggle API
2. Pulls live betting odds across three markets (win/loss, line, totals) from The Odds API
3. Cross-checks against Squiggle's aggregated statistical model predictions
4. Fetches weather forecasts for each venue from Open-Meteo
5. Scrapes AFL.com.au for injury, suspension and team selection news
6. Calculates travel fatigue and days rest for each team
7. Analyses scoring trends (last 3 vs last 5 games)
8. Reviews its own past prediction accuracy to self-calibrate
9. Feeds everything into Google Gemini AI to generate predictions
10. Saves predictions and tracks accuracy across the season

---

## Features

### 🏉 Weekly Predictions
- Predicted winner with win probability %
- Expected winning margin
- High / Medium / Low confidence rating (colour coded)
- Full analysis covering all data sources

### ⚡ Quick-Glance Summary Table
Scan every game in the round at a glance — tip, probability, margin and confidence in one compact table before reading the detail.

### ⏱️ Match Countdown Timers
Live countdown to lockout on every match card so you never miss submitting your tips.

### 🔥 Last Round Performance Banner
Instant accuracy context at the top of the page — see how the agent went last round and for the season.

### 📊 Accuracy Tracker
Full season accuracy dashboard tracking every prediction against real results. The agent uses this history to improve future predictions — underperforming on underdog picks? It knows, and adjusts.

### 📰 Team News & Injuries
Scraped from AFL.com.au team RSS feeds, filtered for injury, suspension and selection keywords. Best fetched Thursday–Friday after squads are named.

### 🔄 Automated Weekly Pipeline
GitHub Actions runs every Thursday automatically — updates last round's results, generates new predictions, and commits everything back to the repo.

---

## Data Sources

| Source | What it provides | Cost |
|---|---|---|
| [Squiggle API](https://api.squiggle.com.au) | Fixtures, ladder, form, H2H, results, model tips | Free |
| [The Odds API](https://the-odds-api.com) | Win/loss, line and totals betting markets | Free tier |
| [Open-Meteo](https://open-meteo.com) | Venue weather forecasts | Free, no key needed |
| [AFL.com.au](https://afl.com.au) | Team news, injuries, selections | Free (RSS) |
| [Google Gemini](https://aistudio.google.com) | AI analysis and prediction generation | Free tier |

---

## Tech Stack

```
Python 3.11
├── streamlit          — Web interface
├── google-generativeai — Gemini AI
├── requests           — API calls
├── feedparser         — RSS scraping
├── pandas             — Data display
└── python-dotenv      — Environment variables

GitHub Actions         — Weekly automation
Streamlit Cloud        — Free hosting
```

---

## Project Structure

```
afl-tipping-agent/
├── app.py                      # Streamlit web app (4 tabs)
├── data_fetcher.py             # All API data fetching
├── predict.py                  # AI prediction engine
├── team_news.py                # Injury & selection scraper
├── tracker.py                  # Accuracy tracking & history
├── weather.py                  # Venue weather forecasts
├── run_weekly.py               # Weekly automation script
├── predictions_history.json    # Auto-generated prediction history
├── requirements.txt
└── .github/
    └── workflows/
        └── weekly_tips.yml     # Automated Thursday pipeline
```

---

## How the AI Prediction Works

Every match prediction is built from a structured prompt containing:

```
LADDER STANDINGS
RECENT FORM (W/L with actual margins)
SCORING STATISTICS & TRENDS (last 3 vs last 5)
REST DAYS & TRAVEL FATIGUE
HEAD TO HEAD (last 10 meetings)
VENUE RECORD
BETTING MARKETS (h2h + line + totals)
SQUIGGLE MODEL CROSS-CHECK
WEATHER FORECAST
TEAM NEWS (injuries, suspensions, selections)
AGENT'S OWN ACCURACY HISTORY
```

The AI is instructed to compare all sources, explain disagreements between the betting market and statistical models, and rate its own confidence. It also reviews its past mistakes and adjusts accordingly.

---

## Self-Learning Accuracy System

The agent tracks every prediction it makes:

- After each round, run **Update Results** to compare predictions vs real results
- The accuracy data is injected into future prompts
- The agent sees which teams it gets wrong and adjusts its confidence
- By mid-season it has a meaningful track record to calibrate against

Example history injected into future prompts:
```
Season accuracy: 38/54 (70.4%)
Favourite picks: 32/40 (80%)
Underdog picks: 6/14 (42.8%)

Past predictions involving these teams:
Rd 4: Collingwood vs Essendon — tipped Collingwood (72%) — ✅ CORRECT
Rd 1: Essendon vs Carlton — tipped Essendon (58%) — ❌ WRONG
```

---

## Weekly Workflow

| Day | Action |
|---|---|
| **Thursday (auto)** | GitHub Actions runs — results updated, new tips generated |
| **Thursday night** | Open app → Team News tab → check injuries → review tips |
| **Before lockout** | Submit your picks! |
| **Monday/Tuesday** | Open app → Update Results tab → record last round |

---

## Setup

### Requirements
- Python 3.11+
- Google Gemini API key (free at [aistudio.google.com](https://aistudio.google.com))
- The Odds API key (free tier at [the-odds-api.com](https://the-odds-api.com))

### Local Development
```bash
git clone https://github.com/mesmerize08/afl-tipping-agent.git
cd afl-tipping-agent
pip install -r requirements.txt
```

Create a `.env` file:
```
ODDS_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
```

Run locally:
```bash
streamlit run app.py
```

### Deployment
The app is deployed on [Streamlit Community Cloud](https://share.streamlit.io) — free tier.
API keys are stored as secrets in the Streamlit app settings.

GitHub Actions secrets required:
- `ODDS_API_KEY`
- `GEMINI_API_KEY`

---

## Confidence Guide

| Rating | Meaning |
|---|---|
| 🟢 High | All data sources agree — betting market, Squiggle model, and form align |
| 🟡 Medium | Most indicators agree but some uncertainty (injury news, mixed form) |
| 🔴 Low | Data sources conflict, significant injury uncertainty, or coin-flip match |

---

## Disclaimer

This tool is built for entertainment purposes and friendly tipping competitions. It is not financial advice. Please gamble responsibly.

---

*Built with Python, Streamlit, Google Gemini, and a lot of AFL love. 🏉*
