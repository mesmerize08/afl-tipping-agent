# 🏉 AFL Tipping Agent

**Data-driven · Unbiased · AI-powered**

[![Live App](https://img.shields.io/badge/Streamlit-Live%20App-FF4B4B?style=for-the-badge&logo=streamlit)](https://afl-tipping-agent.streamlit.app)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

An AI-powered AFL prediction system that combines live betting markets, team form, injury news, travel fatigue, and weather data to generate weekly match tips with confidence ratings and full reasoning.

**🔗 [afl-tipping-agent.streamlit.app](https://afl-tipping-agent.streamlit.app)**

---

## Contents

- [How It Works](#how-it-works)
- [Features](#features)
- [Data Sources](#data-sources)
- [Weekly Workflow](#weekly-workflow)
- [Setup](#setup)
- [Deployment (Streamlit Cloud)](#deployment-streamlit-cloud)
- [Project Structure](#project-structure)
- [Disclaimer](#disclaimer)

---

## How It Works

Every prediction is built from six data layers, compiled into a single structured prompt and analysed by a large language model:

```
1. FIXTURES & LADDER    Squiggle API — round, venue, ladder positions
2. BETTING MARKETS      The Odds API — head-to-head, line, total score
3. FORM & STATS         Squiggle API — last 5 results, margins, scoring trends
4. TEAM NEWS            Multi-source — injuries, suspensions, tribunal decisions
5. TRAVEL & REST        Calculated — distance, days between games
6. WEATHER              Open-Meteo — forecast for venue at game time
                                  ↓
                        AI ANALYSIS (Groq / Claude)
                                  ↓
              Predicted winner · Win probability · Margin
              Confidence rating · Upset risk · Data conflicts
```

The AI is explicitly instructed to weight betting markets heavily (they aggregate collective wisdom), flag any conflicting signals between data sources, and never fabricate information when data is absent. Win probabilities are derived from a weighted blend of betting market, Squiggle model, and form data — not copied directly from market implied probabilities.

Predictions are saved to `predictions_history.json` and automatically pushed back to GitHub so accuracy tracking persists across app restarts on Streamlit Cloud.

---

## Features

| | |
|---|---|
| **AI predictions** | Groq Llama 3.3 70B (primary, free) with Anthropic Claude fallback |
| **Confidence ratings** | High / Medium / Low with one-sentence justification |
| **Summary table** | Scan the full round at a glance |
| **Match cards** | Expand for the full AI analysis |
| **Lockout countdowns** | Live JavaScript timer per game |
| **Accuracy tracker** | Season-long correct/incorrect record by round |
| **Team news tab** | Injuries, suspensions and tribunal news from multiple sources |
| **PDF export** | Print-ready round report |
| **Auto GitHub sync** | History file pushed to repo after every save — no data lost on restart |
| **Performance banner** | Last round accuracy shown at the top of the app |
| **Re-generation safe** | Generating tips again before results updates history with the new prediction |

---

## Data Sources

| Source | Data | Cost |
|--------|------|------|
| [Squiggle API](https://api.squiggle.com.au) | Fixtures, results, ladder, H2H history | Free |
| [The Odds API](https://the-odds-api.com) | Betting odds — h2h, line, totals | Free (500 req/month) |
| [Zero Hanger](https://www.zerohanger.com) | Injuries/suspensions + tribunal RSS feeds and pages | Free |
| [AFL.com.au](https://www.afl.com.au) | Official injury list + tribunal/MRP decisions | Free |
| [Open-Meteo](https://open-meteo.com) | Venue weather forecasts | Free |
| [Groq](https://groq.com) | Primary AI engine (Llama 3.3 70B) | Free tier |
| [Anthropic Claude](https://www.anthropic.com) | Fallback AI engine | ~$0.013/round |

**Estimated cost for a full 24-round season: ~$0.30** (Anthropic fallback only fires if Groq fails)

---

## Weekly Workflow

```
Thursday night   Fetch latest news, then click "Generate This Week's Tips"
Before lockout   Review predictions — re-generate as many times as you like
                 (history always stores the most recent generation)
Monday/Tuesday   Click "Check Results & Update History" to record last round
```

Results are fetched from Squiggle and matched against your predictions automatically. The accuracy tracker updates immediately and the history file is synced back to GitHub.

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/mesmerize08/afl-tipping-agent.git
cd afl-tipping-agent

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Get API keys

**Groq (primary AI — free)**
1. Sign up at [console.groq.com](https://console.groq.com)
2. Create an API key

**The Odds API (betting data — required)**
1. Sign up at [the-odds-api.com](https://the-odds-api.com)
2. Copy your key — free tier (500 req/month) is sufficient for a full season

**Anthropic (AI fallback — optional)**
1. Sign up at [console.anthropic.com](https://console.anthropic.com)
2. Add $5–10 credit — lasts the whole season as a fallback only

### 3. Create `.env`

```bash
cp .env.example .env
```

Edit `.env`:

```bash
GROQ_API_KEY=gsk_your_groq_key_here
ODDS_API_KEY=your_odds_api_key_here
ANTHROPIC_API_KEY=sk-ant-api03-your_key_here   # optional fallback
```

### 4. Run

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`.

---

## Deployment (Streamlit Cloud)

### Initial deploy

1. Fork this repository
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Connect your fork, set main file to `app.py`
4. Add secrets (Settings → Secrets):

```toml
GROQ_API_KEY      = "gsk_your_groq_key_here"
ODDS_API_KEY      = "your_odds_api_key_here"
ANTHROPIC_API_KEY = "sk-ant-api03-your_key_here"
GITHUB_TOKEN      = "ghp_your_token_here"
```

5. Deploy

### Persisting history across restarts (important)

Streamlit Cloud has an **ephemeral filesystem** — any file written at runtime is lost when the app sleeps or redeploys. To keep your prediction history intact, the app automatically pushes `predictions_history.json` back to GitHub after every save.

**This requires a `GITHUB_TOKEN` secret:**

1. GitHub → Settings → Developer settings → Personal access tokens → **Tokens (classic)**
2. Generate new token — check the **`repo`** scope — no expiration
3. Copy the token and add it as `GITHUB_TOKEN` in your Streamlit secrets

Without this token the app still works, but all results will be lost on the next restart. A warning banner is shown in the Update Results tab when the token is not configured.

---

## Project Structure

```
afl-tipping-agent/
├── app.py                   # Streamlit UI — 4 tabs, session state, caching
├── predict.py               # AI prediction engine, retry logic, sequential execution
├── data_fetcher.py          # Squiggle + Odds API, match data compilation
├── tracker.py               # Prediction history, accuracy, GitHub sync
├── team_news.py             # Multi-source team news — Zero Hanger, AFL.com.au
├── extraction_utils.py      # Shared parsing — winner, probability, confidence, margin
├── weather.py               # Open-Meteo integration and venue impact
├── pdf_export.py            # Round report PDF generation
├── run_weekly.py            # CLI runner (alternative to the Streamlit UI)
├── predictions_history.json # Season prediction log (auto-committed by app)
├── requirements.txt
└── .env.example
```

### Module responsibilities

**`data_fetcher.py`** — Collects all external data. The two per-match Squiggle team-data calls (home + away) are parallelised with `ThreadPoolExecutor`. Betting odds are fetched in three calls (h2h, spreads, totals). API keys are stripped from exception messages to prevent accidental leakage in logs.

**`predict.py`** — Builds a structured prompt for each match and calls the AI. Matches are predicted **sequentially** with a 3-second gap between each to respect Groq's token-per-minute rate limit. Falls back to Anthropic Claude if Groq fails after three retries with exponential backoff.

**`tracker.py`** — Loads, saves and syncs `predictions_history.json`. Round-specific Squiggle queries are used to fetch results (the general `?q=games;year=X` endpoint does not reliably return Opening Round games). Re-generating tips before results are recorded **overwrites** the previous prediction so history always reflects the latest generation. Once a result is recorded the entry is locked. After every save the file is pushed to GitHub via the Contents API.

**`team_news.py`** — Aggregates news from multiple sources: Zero Hanger main RSS, Zero Hanger injuries/suspensions and tribunal/MRP category feeds, direct HTML scraping of Zero Hanger listing pages, and AFL.com.au injury list and tribunal/MRP pages. Team attribution uses title-only matching (not scraped body) to avoid nav/sidebar pollution, with negative-lookbehind regex to prevent "Adelaide" matching "Port Adelaide" and "Melbourne" matching "North Melbourne".

**`extraction_utils.py`** — Shared parsing functions used by both `predict.py` and `tracker.py`. `extract_winner()` matches the full team name first before falling back to the nickname, preventing false matches (e.g. "Port Adelaide" vs "Adelaide"). `extract_probability()` searches only within the window immediately after the `WIN PROBABILITY:` label.

**`app.py`** — Streamlit UI. Fixtures and ladder calls are cached with `@st.cache_data(ttl=3600)`. After checking results, `st.rerun()` is called so the Accuracy Tracker tab re-renders with the updated data rather than showing stale pre-update state.

---

## Disclaimer

This application is for entertainment and personal tipping competitions only.

- This is **not** financial or gambling advice
- Predictions carry inherent uncertainty — no system beats the market consistently
- Never bet money you cannot afford to lose

**Gambling help (Australia):** 1800 858 858 · [gamblinghelponline.org.au](https://www.gamblinghelponline.org.au)

---

## License

MIT — see [LICENSE](LICENSE).

---

## Acknowledgements

[Squiggle](https://api.squiggle.com.au) · [The Odds API](https://the-odds-api.com) · [Zero Hanger](https://www.zerohanger.com) · [AFL.com.au](https://www.afl.com.au) · [Open-Meteo](https://open-meteo.com) · [Groq](https://groq.com) · [Anthropic](https://www.anthropic.com) · [Streamlit](https://streamlit.io)

---

*Season 2026 · Updated March 2026*
