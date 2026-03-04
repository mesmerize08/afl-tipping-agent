# 🏉 AFL Tipping Agent

**Data-driven · Unbiased · AI-powered**

A fully automated AFL tipping agent built with Streamlit. Every week it fetches live fixture, odds, weather, form, and team news data, runs it through an AI model with a strict analytical prompt, and produces structured predictions with confidence ratings and full reasoning — then tracks its own accuracy across the season.

🚀 **[Live App →](https://afl-tipping-agent.streamlit.app)**

---

## What It Does

- Fetches this week's fixtures from the Squiggle API (handles Opening Round / Round 0)
- Pulls betting odds from The Odds API (h2h win/loss, line/spread, totals)
- Gets weather forecasts for every AFL venue via Open-Meteo (free, no key needed)
- Scrapes injury, suspension and team selection news from Zero Hanger
- Calculates form, scoring trends, rest days and travel fatigue for every team
- Cross-checks Squiggle's aggregated statistical model predictions
- Sends all data to an AI model (Groq / Anthropic) with a strict, no-hype analytical prompt
- Tracks its own correct/incorrect record and feeds that back into future prompts
- Exports predictions to a clean, print-ready PDF

---

## Data Sources

| Source | Data | Cost |
|--------|------|------|
| [Squiggle API](https://api.squiggle.com.au/) | Fixtures, ladder, results, model tips | Free |
| [The Odds API](https://the-odds-api.com/) | H2H odds, line market, totals | Free tier (500 req/mo) |
| [Open-Meteo](https://open-meteo.com/) | Venue weather forecasts | Free, no key |
| [Zero Hanger](https://www.zerohanger.com/) | Injuries, suspensions, team news | Free (scraped) |
| [Groq API](https://console.groq.com/) | AI predictions (Llama 3.3 70B) | Free tier (6 000 req/day) |

---

## File Structure

```
afl-tipping-agent/
├── app.py                  # Streamlit UI — all four tabs
├── data_fetcher.py         # All data retrieval (Squiggle, odds, news)
├── predict.py              # AI prompt + Groq/Anthropic call
├── pdf_export.py           # PDF generation (fpdf2)
├── team_news.py            # Zero Hanger scraping (injuries + team pages)
├── tracker.py              # Prediction history + accuracy tracking
├── weather.py              # Open-Meteo venue forecasts
├── run_weekly.py           # CLI runner (optional, for automation)
├── weekly_tips.yml         # GitHub Actions schedule (optional)
├── requirements.txt
├── predictions_history.json  # Auto-generated, committed each round
└── README.md
```

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/mesmerize08/afl-tipping-agent
cd afl-tipping-agent
pip install -r requirements.txt
```

### 2. API keys

Create a `.env` file (local) or add to Streamlit Cloud Secrets:

```toml
# Required for AI predictions — get free key at console.groq.com
GROQ_API_KEY = "gsk_..."

# Optional — betting odds (free tier at the-odds-api.com)
ODDS_API_KEY = "your_key_here"

# Optional — Anthropic fallback if Groq is unavailable
ANTHROPIC_API_KEY = "sk-ant-..."
```

> **Note:** The Groq free tier gives 6,000 requests/day — more than enough for a full round of tips. No credit card required.
>
> **Claude Pro** ($17/mo at claude.ai) does **not** include API access. The Anthropic API is billed separately at console.anthropic.com. Groq is the recommended free option.

### 3. Run locally

```bash
streamlit run app.py
```

### 4. Deploy to Streamlit Cloud

1. Push to GitHub
2. Go to share.streamlit.io → New app → select repo
3. Add secrets under **Settings → Secrets** (same key=value format as above)

---

## Weekly Workflow

| Day | Action |
|-----|--------|
| **Monday/Tuesday** | Click **Update Results** tab → records last round's outcomes |
| **Thursday night** | Click **Team News** → Fetch Latest News (squads named) |
| **Friday** | Click **Generate This Week's Tips** |
| **Before lockout** | Review tips, click **Export PDF**, submit your picks |

---

## Tabs

### 🏉 This Week's Tips
- Click **Generate This Week's Tips** to run the full pipeline
- Round summary table: winner, probability, margin, confidence for all games at a glance
- Detailed match cards with odds, scoring trends, travel/rest badges
- Full AI analysis (expandable) with structured reasoning for each game
- **Export PDF** button — available immediately after generating tips, persists on page

### 📊 Accuracy Tracker
- Season accuracy: overall %, per-round breakdown, favourite vs underdog splits
- Round-by-round bar chart
- Full history table with correct/incorrect flags

### 📰 Team News
- Sourced from Zero Hanger (injuries hub + per-team pages + global RSS)
- Filter by team or view all 18 clubs
- Covers MRO decisions, tribunal outcomes, long-term injuries, selection news

### 🔄 Update Results
- Fetches completed game scores from Squiggle
- Updates prediction history with actual winners and margins
- Recalculates season accuracy summary
- Download full predictions_history.json

---

## PDF Export

After generating tips, click **Export PDF** (top-right of the tips section) to download a print-ready PDF containing:

- Cover summary table: all games with tip, probability, margin, and confidence
- Full per-match AI analysis with structured reasoning sections
- Betting odds and market data
- Round number and generation timestamp in header/footer

The PDF button appears automatically once tips are generated and remains available until you navigate away or regenerate.

---

## AI Prompt Design

The AI receives a structured prompt that enforces strict analytical rules:

- Prohibits vague language ("dominant", "powerhouse") without citing actual numbers
- Requires every conclusion to reference a specific data point from the provided data
- Cross-checks betting market vs Squiggle model vs recent form
- Explicitly flags data conflicts where sources disagree
- Forces structured output: predicted winner, win probability, margin, key factors, scoring trends, market analysis, fatigue, weather, team news, confidence level, upset risk, data conflicts

The agent also receives its own season accuracy history each week, allowing it to recalibrate based on previous mistakes.

---

## Technical Notes

### Round 0 / Opening Round

The AFL introduced a competitive Opening Round (Round 0) in 2024. The app handles this correctly:

- Uses `complete=!100` query to find all upcoming games (the bare `year=` query returns only completed games)
- Queries `round=0` and `round=1` as fallbacks
- Filters to the earliest round — prevents Round 1 leaking into Opening Round week
- Normalises `Greater Western Sydney` → `GWS Giants` at fetch time
- Strips dotted venue abbreviations (`S.C.G.` → `SCG`, `M.C.G.` → `MCG`)

### Squiggle API

All Squiggle requests include a `User-Agent` header as required by API docs. Cloud IPs without this header can be silently rate-limited.

### Team news coverage

Zero Hanger's global RSS feed has a 20-article cap. To avoid missing mid-week suspensions and injuries, the app also scrapes:
- The Zero Hanger injuries/suspensions hub page
- Per-team latest-news pages for the two teams in each match

---

## Extending

**Add a new venue:**
Edit `VENUE_CITIES` in `data_fetcher.py` and `VENUE_DATA`/`VENUE_ALIASES` in `weather.py`.

**Change the AI model:**
Edit `_call_ai()` in `predict.py`. The Groq block is OpenAI-compatible — swap the model string for any Groq-supported model (e.g. `mixtral-8x7b-32768`, `llama-3.1-8b-instant`).

**Automate weekly runs:**
`weekly_tips.yml` contains a GitHub Actions workflow that runs the CLI (`run_weekly.py`) on a schedule and commits the updated `predictions_history.json`.

---

## Disclaimer

For entertainment only. This app does not constitute financial or gambling advice. Please gamble responsibly.

---

*Built with [Streamlit](https://streamlit.io) · [Squiggle API](https://api.squiggle.com.au) · [Groq](https://console.groq.com) · [Open-Meteo](https://open-meteo.com) · [Zero Hanger](https://zerohanger.com)*
