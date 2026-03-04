# 🏉 AFL Tipping Agent

> **Data-driven · Unbiased · AI-powered**

An autonomous AFL tipping agent built on Streamlit. Each week it fetches live fixtures, betting markets, team form, weather forecasts, and team news — then feeds everything into an AI model that produces structured, evidence-based match predictions. Results are tracked and fed back into future predictions so the agent improves over time.

---

## Features

- **Live fixture fetching** via Squiggle API with a robust multi-query strategy that handles preseason, Round 0, and mid-season
- **Betting market analysis** — head-to-head win/loss odds, line market (expected margin), totals market, and implied probabilities
- **Statistical model cross-check** — Squiggle's aggregated AI model is injected as a data input and interrogated against the betting market
- **Scoring trends** — last-5 and last-3 attack/defence averages with trend direction (improving / stable / declining)
- **Home ground advantage** — season home vs away win split + venue-specific W/L record and average margin, flagged when the split is ≥ 20 percentage points
- **Rest days & travel fatigue** — days since last game, travel distance, Perth long-haul detection, short-turnaround flags
- **Live weather forecasts** via Open-Meteo (free, no key required) — rain, wind, and heat impact assessed per venue
- **Team news** via Zero Hanger RSS — injuries, suspensions, MRO decisions, and selections across all 18 clubs
- **Self-learning accuracy tracker** — predictions are saved to `predictions_history.json`; after each round the agent checks its own results and uses them to recalibrate future tips
- **PDF export** — clean, print-ready round report with summary table and full per-match AI analysis
- **Match countdown timers** — live JavaScript countdown to lockout per game card
- **Confidence badges** — High / Medium / Low per match based on data source agreement

---

## Screenshots

| Tips Dashboard | Accuracy Tracker |
|---|---|
| Round predictions, summary table, match cards with badges | Season accuracy, round-by-round chart, full prediction history |

---

## Project Structure

```
afl-tipping-agent/
├── app.py                    # Streamlit UI — all four tabs
├── data_fetcher.py           # All Squiggle API, betting odds, and match data assembly
├── predict.py                # AI prompt construction and Groq/Anthropic API calls
├── tracker.py                # Prediction history, result checking, accuracy calculation
├── team_news.py              # Zero Hanger RSS fetching and relevance filtering
├── weather.py                # Open-Meteo weather forecasts per venue
├── pdf_export.py             # fpdf2 PDF generation with Unicode sanitisation
├── requirements.txt          # Python dependencies
├── weekly_tips.yml           # GitHub Actions workflow for automated weekly runs
└── predictions_history.json  # Auto-generated — tracks all predictions and results
```

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/mesmerize08/afl-tipping-agent.git
cd afl-tipping-agent
pip install -r requirements.txt
```

### 2. Set environment variables

Create a `.env` file in the project root:

```env
# Required — primary AI engine (free tier: 6,000 req/day)
GROQ_API_KEY=your_groq_api_key

# Required — betting odds (free tier available)
ODDS_API_KEY=your_odds_api_key

# Optional — fallback AI if Groq is unavailable
ANTHROPIC_API_KEY=your_anthropic_api_key
```

Get your keys:
- **Groq** — [console.groq.com](https://console.groq.com) (free, no credit card)
- **The Odds API** — [the-odds-api.com](https://the-odds-api.com) (free tier: 500 req/month)
- **Anthropic** — [console.anthropic.com](https://console.anthropic.com) (optional fallback)

### 3. Run locally

```bash
streamlit run app.py
```

---

## Deploy to Streamlit Cloud

1. Push the repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app** → select your repo
3. Add secrets under **Settings → Secrets**:

```toml
GROQ_API_KEY = "your_key_here"
ODDS_API_KEY = "your_key_here"
ANTHROPIC_API_KEY = "your_key_here"   # optional
```

4. Deploy — the app runs entirely in-browser, no server required

---

## Weekly Workflow

| Day | Action |
|---|---|
| **Mon / Tue** | Click **Update Results** tab → fetches Squiggle scores and marks predictions correct/incorrect |
| **Thu night** | Click **Team News** → fetch latest injuries, suspensions, and selections |
| **Thu–Fri** | Click **Generate This Week's Tips** → full AI analysis for every match |
| **Before lockout** | Review tips, download PDF report, submit your picks |

---

## Data Sources

| Source | What it provides | Cost |
|---|---|---|
| [Squiggle API](https://api.squiggle.com.au/) | Fixtures, results, ladder, H2H, venue records, model tips | Free |
| [The Odds API](https://the-odds-api.com/) | H2H odds, line market, totals across all bookmakers | Free tier |
| [Open-Meteo](https://open-meteo.com/) | 7-day weather forecasts for every AFL venue | Free, no key |
| [Zero Hanger](https://www.zerohanger.com/) | Injuries, MRO, suspensions, team selections (RSS) | Free |
| [Groq](https://groq.com/) | LLM inference (llama-3.3-70b-versatile) | Free tier |

---

## How the Prediction Engine Works

Each match prediction is built from a structured prompt containing:

1. **Ladder standings** — current season position, W/L, percentage
2. **Recent form** — last 5 results with actual score and margin
3. **Scoring stats** — last-5 and last-3 averages for and against, attack/defence trend
4. **Rest & travel** — days since last game, travel distance, fatigue level
5. **Head-to-head** — last 10 meetings with venue and year
6. **Home ground advantage** — season home/away win split + venue-specific record
7. **Betting markets** — H2H odds, line, totals, implied probabilities
8. **Squiggle model** — aggregated AI model tips cross-checked against markets
9. **Weather** — forecast conditions and assessed game impact
10. **Team news** — injuries, suspensions, selections from Zero Hanger
11. **Agent history** — the agent's own accuracy so far this season, including recent wrong predictions

The AI is instructed to justify every conclusion with a specific data point, acknowledge contradictions between sources, and never manufacture confidence when the data is ambiguous. The output follows a fixed structure with mandatory sections including a new **Home Ground Advantage** section.

---

## Accuracy Tracking

Every prediction is saved automatically. After each round:

- Results are fetched from Squiggle and matched to predictions
- Overall season accuracy, favourite-pick accuracy, and underdog-pick accuracy are calculated
- Round-by-round accuracy is charted in the **Accuracy Tracker** tab
- The accuracy history is injected into the next week's prompts so the agent can learn from its mistakes

---

## Automated Weekly Runs (GitHub Actions)

`weekly_tips.yml` defines a workflow that:
- Runs every Friday at 10:00 AM AEST
- Can also be triggered manually from the Actions tab
- Calls the prediction engine and commits `predictions_history.json` back to the repo

To enable: add `GROQ_API_KEY`, `ODDS_API_KEY`, and optionally `ANTHROPIC_API_KEY` to your repo's **Settings → Secrets → Actions**.

---

## Bug History & Key Fixes

A summary of the major issues resolved during development:

| Issue | Root Cause | Fix |
|---|---|---|
| "No upcoming fixtures found" | `?q=games;year=X` returns only *completed* games by Squiggle convention | Changed primary query to `complete=!100`; multi-group fallback strategy |
| PDF Unicode crash (`helveticaB`) | fpdf2's built-in Helvetica is Latin-1 only; AI output contains em dashes, smart quotes, etc. | `_safe()` maps all common Unicode chars to ASCII; `encode("latin-1", errors="ignore")` as nuclear fallback; overrode `cell()` and `multi_cell()` |
| Round 0 predictions not saved | `if round_number:` evaluates `0` as falsy | Changed to `if round_number is not None:` |
| GWS Giants not matched | Squiggle uses "Greater Western Sydney"; app used "GWS Giants" | `SQUIGGLE_TEAM_NAME_MAP` normaliser on all API responses |
| Squiggle margin crash at season start | `squiggle_margin` and `home_win_prob` are `None` before model tips are published | Wrapped both fields in `try: float(raw_value)` guards |
| Hardcoded `year=2026` | All Squiggle queries used a hardcoded year | Changed every signature to `year=None` with `datetime.now().year` default |
| Missing User-Agent on API calls | Squiggle API rate-limits requests without a User-Agent since April 2024 | Added `_UA` constant; applied to every `requests.get()` call |
| Predictions lost on button click | Streamlit reruns the entire script on any interaction | Wrapped predictions in `st.session_state` |
| Team news false positives | Short keywords like "out", "back", "test" matched substrings ("throughout", "latest") | Word-boundary regex `\b` applied to all short ambiguous keywords |
| AFL.com.au RSS dead | All AFL.com.au RSS feeds return 404 as of early 2026 | Replaced with Zero Hanger RSS as primary source |
| Home ground advantage not analysed | Venue record data was fetched but AI was never asked to analyse it | Added `get_home_away_split()`, `format_home_advantage()`, and mandatory **HOME GROUND ADVANTAGE** output section |

---

## Requirements

```
requests
streamlit
pandas
python-dotenv
feedparser
fpdf2
```

Python 3.9+

---

## Disclaimer

For entertainment purposes only. This tool does not constitute financial advice. Please gamble responsibly.

---

## License

MIT
