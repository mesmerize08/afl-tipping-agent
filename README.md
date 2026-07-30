# AFL Tipping Agent

**Data-driven · Unbiased · AI-powered**

[![Live App](https://img.shields.io/badge/Streamlit-Live%20App-FF4B4B?style=for-the-badge&logo=streamlit)](https://afl-tipping-agent.streamlit.app)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

An AI-powered AFL prediction system that combines live betting markets, team form, injury news, travel fatigue, and weather data to generate weekly match tips with confidence ratings and full reasoning.

**[afl-tipping-agent.streamlit.app](https://afl-tipping-agent.streamlit.app)**

---

## Version history

| Version | Season | Status |
|---------|--------|--------|
| **v1.0** | **2026** | **Complete — see [Season 2026 Results](#season-2026-results-v10)** |
| v2.0 | 2027 | Planned — see [Season 2027 Improvements](#season-2027-planned-improvements) |

---

## Contents

- [How It Works](#how-it-works)
- [Season 2026 Results (v1.0)](#season-2026-results-v10)
- [Features](#features)
- [Data Sources](#data-sources)
- [Weekly Workflow](#weekly-workflow)
- [Setup](#setup)
- [Deployment (Streamlit Cloud)](#deployment-streamlit-cloud)
- [Project Structure](#project-structure)
- [Season 2027 Planned Improvements](#season-2027-planned-improvements)
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

The agent is **self-learning**: every prediction is stored in `predictions_history.json` and injected back into subsequent predictions as an accuracy history block. The AI reads its own past errors and is explicitly instructed to identify patterns and correct for them.

---

## Season 2026 Results (v1.0)

### Overall performance

| Metric | Result |
|--------|--------|
| Rounds completed | 20 of 24 (Round 21 in progress) |
| Total predictions | 171 resolved + 9 pending |
| **Overall accuracy** | **73.1% (125/171)** |
| Favourite tips (≥65% confidence) | **84.6% (55/65)** |
| Underdog tips (<65% confidence) | **66.0% (70/106)** |
| High confidence (75%+) | **89.7% (26/29)** |
| Medium confidence (65–74%) | **80.6% (29/36)** |
| Low confidence (<65%) | **66.0% (70/106)** |
| Best round | Rd 18 — **9/9 (100%)** |
| Worst round | Rd 10 — 5/9 (56%) |

### Round-by-round breakdown

```
Rd  0:  3/ 5  60%  ######
Rd  1:  6/ 9  67%  ######
Rd  2:  5/ 7  71%  #######
Rd  3:  6/ 7  86%  ########
Rd  4:  5/ 8  62%  ######
Rd  5:  8/ 9  89%  #########
Rd  6:  8/ 9  89%  #########
Rd  7:  8/ 9  89%  #########
Rd  8:  7/ 9  78%  #######
Rd  9:  8/ 9  89%  #########
Rd 10:  5/ 9  56%  #####     ← slump begins
Rd 11:  7/ 9  78%  #######
Rd 12:  4/ 7  57%  #####
Rd 13:  5/ 8  62%  ######
Rd 14:  4/ 7  57%  #####
Rd 15:  4/ 7  57%  #####
Rd 16:  5/ 7  71%  #######
Rd 17:  5/ 9  56%  #####     ← slump ends
Rd 18:  9/ 9 100%  ##########  ← perfect round
Rd 19:  6/ 9  67%  ######
Rd 20:  7/ 9  78%  #######
```

### What happened

**Rounds 5–9 (best stretch):** Strong form, averaging 89%. The agent's home-advantage weighting and betting-market blending were well-calibrated for this period.

**Rounds 10–17 (mid-season slump):** Six rounds below 70%, averaging ~62%. Post-analysis identified three contributing factors:
- **Abnormally high upset rate** in this stretch of the draw — teams mid-table were volatile
- **Away-team overconfidence** — a systemic bias toward backing away teams that were market favourites; corrected mid-season by adding a calibration note to the history prompt
- **Prompt truncation** — some prompts exceeded the 12,000-character limit (later raised to 16,000), causing the output template instructions to be clipped and producing malformed AI responses

**Rounds 18–20 (recovery):** Strong close to the season. Rd 18 was a perfect 9/9. The self-learning system's calibration notes on away-team errors and team-specific weaknesses contributed to improved accuracy.

### Confidence calibration verdict

The confidence tiers are well-calibrated: high-confidence tips (75%+) hit at 89.7%, medium at 80.6%, and low at 66.0%. The system correctly assigns uncertainty — when it says it's confident, it usually is right.

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
| **Round-by-round chart** | Bar chart with zero-padded labels (Rd 01–24) for correct sort order |
| **Team news tab** | Injuries, suspensions and tribunal news from multiple sources |
| **PDF export** | Print-ready round report |
| **Auto GitHub sync** | History file pushed to repo after every save — no data lost on restart |
| **Performance banner** | Last round accuracy shown at the top of the app |
| **Self-learning** | Past prediction errors injected into each new prompt with explicit correction directive |
| **Confidence calibration** | Tier-based accuracy history fed back to the AI to prevent overconfidence |
| **Team error detection** | Teams the agent has consistently mis-predicted are flagged in the history prompt |

---

## Data Sources

| Source | Data | Cost |
|--------|------|------|
| [Squiggle API](https://api.squiggle.com.au) | Fixtures, results, ladder, H2H history, statistical model tips | Free |
| [The Odds API](https://the-odds-api.com) | Betting odds — h2h, line, totals | Free (500 req/month) |
| [Zero Hanger](https://www.zerohanger.com) | Injuries/suspensions + tribunal RSS feeds and pages | Free |
| [AFL.com.au](https://www.afl.com.au) | Official injury list + tribunal/MRP decisions | Free |
| [Open-Meteo](https://open-meteo.com) | Venue weather forecasts | Free |
| [Groq](https://groq.com) | Primary AI engine (Llama 3.3 70B) | Free tier |
| [Anthropic Claude](https://www.anthropic.com) | Fallback AI engine (Haiku) | ~$0.013/round |

**Estimated cost for a full 24-round season: ~$0.30** (Anthropic fallback only fires if Groq fails)

---

## Weekly Workflow

```
Wednesday night  GitHub Actions cron runs automatically (23:00 UTC)
                 ├─ Fetches last round results → resolves pending predictions
                 ├─ Fetches upcoming fixtures + all data layers
                 ├─ Generates 9 AI predictions
                 └─ Commits predictions_history.json + predictions.json to repo

Thursday morning Open the Streamlit app → click "Generate This Week's Tips"
                 Review predictions — re-generate as many times as you like
                 (history always stores the most recent generation)

After round ends Results are auto-resolved on the next Wednesday CI run
                 OR click "Check Results & Update History" in the app manually
```

The GitHub Actions cron is the primary mechanism. The Streamlit app's generate button is a supplement for reviewing or regenerating mid-week.

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
# Streamlit app
streamlit run app.py

# Or CLI runner (generates predictions and writes predictions.json)
python run_weekly.py
```

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

### Persisting history across restarts

Streamlit Cloud has an **ephemeral filesystem** — files written at runtime are lost when the app sleeps or redeploys. To keep prediction history intact, the app pushes `predictions_history.json` back to GitHub after every save.

**This requires a `GITHUB_TOKEN` secret:**

1. GitHub → Settings → Developer settings → Personal access tokens → **Tokens (classic)**
2. Generate new token — check the **`repo`** scope — no expiration
3. Copy the token and add it as `GITHUB_TOKEN` in your Streamlit secrets

Without this token the app still works but results will be lost on the next restart.

### GitHub Actions (CI) — keeping it alive

GitHub **automatically disables scheduled workflows** after 60 days of no human pushes to the repo. The `keepalive.yml` workflow (added in v1.0) runs on the 1st and 16th of each month and commits a timestamp file to keep the repo active. No action needed — it runs automatically.

If the cron ever gets disabled (e.g., you forked the repo fresh), re-enable it by:
1. GitHub → Actions → "Weekly AFL Tips" workflow → **Enable workflow**

---

## Project Structure

```
afl-tipping-agent/
├── app.py                   # Streamlit UI — 4 tabs, session state, caching
├── predict.py               # AI prediction engine, retry logic, sequential execution
├── data_fetcher.py          # Squiggle + Odds API, match data compilation
├── tracker.py               # Prediction history, accuracy, GitHub sync, self-learning
├── team_news.py             # Multi-source team news — Zero Hanger, AFL.com.au
├── extraction_utils.py      # Shared parsing — winner, probability, confidence, margin
├── weather.py               # Open-Meteo integration and venue impact
├── pdf_export.py            # Round report PDF generation
├── run_weekly.py            # CLI runner (also used by GitHub Actions CI)
├── predictions_history.json # Full season prediction log — source of truth
├── predictions.json         # Current round predictions (overwritten each week)
├── .github/
│   └── workflows/
│       ├── weekly_tips.yml  # Wednesday night cron — generates and commits tips
│       └── keepalive.yml    # 1st & 16th monthly — prevents 60-day cron disable
├── requirements.txt
└── .env.example
```

### Module responsibilities

**`data_fetcher.py`** — Collects all external data. The two per-match Squiggle team-data calls (home + away) are parallelised with `ThreadPoolExecutor`. Betting odds are fetched in three calls (h2h, spreads, totals). API keys are stripped from exception messages. The `get_upcoming_fixtures()` function has three fallback query groups: `complete=!100` (often returns 400 — harmless, falls through), `year=X;complete=0`, and round-specific queries estimated from the current date.

**`predict.py`** — Builds a structured prompt for each match and calls the AI. Matches are predicted **sequentially** with a 3-second gap between each to respect Groq's token-per-minute rate limit. Falls back to Anthropic Claude if Groq fails after three retries with exponential backoff. `MAX_PROMPT_LENGTH` is set to 16,000 characters to avoid truncating output instructions (Groq's Llama 3.3 70B supports 128k token context).

**`tracker.py`** — Loads, saves and syncs `predictions_history.json`. Provides `format_history_for_ai()` which builds the self-learning history block injected into each prompt: season accuracy, confidence calibration by tier, away-team error rate, team-specific error patterns, and a LEARNING DIRECTIVE instructing the AI to explicitly correct for identified patterns.

**`team_news.py`** — Aggregates news from Zero Hanger RSS feeds, Zero Hanger HTML pages, and AFL.com.au. Uses `lxml` parser with `html.parser` fallback. Team attribution uses title-only matching with negative-lookbehind regex to prevent "Adelaide" matching "Port Adelaide".

**`extraction_utils.py`** — Shared parsing functions. `extract_winner()` searches 300 characters after the `PREDICTED WINNER:` label (widened from 120 in v1.0 after finding the AI sometimes puts the team name on the next line). Falls back to team nickname matching.

**`app.py`** — Streamlit UI. Fixtures and ladder calls are cached with `@st.cache_data(ttl=3600)`. Bar chart uses zero-padded round labels (`Rd 01`, `Rd 02`…) so alphabetical sort equals numeric sort. After checking results, `st.rerun()` re-renders the accuracy tracker immediately.

---

## Season 2027 Planned Improvements

This section documents lessons from Season 2026 and proposed changes for v2.0. It is written to be read by Claude as a reference when implementing Season 2027 updates.

### What worked well — keep in v2.0

- **Betting market weighting** — The market-weighted probability blend (40% market, 30% Squiggle, 30% form) is well-calibrated. Do not simplify this away.
- **Squiggle statistical model** — The Squiggle model's tips are a strong signal, particularly for lopsided matchups. Continue including them.
- **Self-learning history injection** — The `format_history_for_ai()` history block clearly contributed to improved accuracy in the second half of the season. Extend, not remove.
- **Confidence calibration tiers** — High confidence tips (89.7%) outperformed medium (80.6%) which outperformed low (66.0%). The tiers are meaningful — preserve the calibration logic.
- **Three-source AI fallback** — Groq primary + Anthropic fallback worked throughout the season with minimal failures.
- **Away-team error tracking** — Adding the away-bias calibration note mid-season contributed to the Rd 18–20 recovery. Retain and expand this.

### Proposed improvements for v2.0

#### Data pipeline

- **Player-level data** — Currently only team-level statistics are used. Adding key player availability (top goal-scorers, key defenders) would improve predictions for injury-affected matches. Source: AFL Fantasy, Champion Data public feeds, or AFL.com.au player pages.
- **Live odds movement** — The current snapshot captures odds at fetch time. Tracking line movement (opening vs. current line) would signal sharp money and improve market interpretation.
- **Post-bye effect** — Teams coming off a bye historically outperform their form-based rating. Add a `bye_last_round` flag to the match data and instruct the AI to weight it appropriately.
- **Ground conditions / grass length** — MCG and some other venues have documented characteristics (slower ball movement on heavy outfields). Low priority, but worth a data flag.
- **Historical round-specific performance** — Some teams perform differently in the final rounds of a season (finals pressure, tanking). Injecting the team's last-5 years' Round 18–23 record would help.

#### Prediction engine

- **Parallel prediction generation** — Currently predictions are generated sequentially with a 3-second gap to respect Groq rate limits. Groq's free tier allows 30 requests/minute. With 9 matches, parallel generation (3 concurrent batches of 3) would cut total generation time from ~4 minutes to ~90 seconds. Implement with `asyncio` or `ThreadPoolExecutor` and shared rate-limit backoff.
- **Prompt size budgeting** — Instead of a hard character truncation, dynamically trim each data section to a proportional budget before assembling the prompt. Priority order: match facts > betting market > form data > H2H > team news > weather > history.
- **Structured output / JSON mode** — Instruct the AI to return predictions as JSON (`{"winner": "...", "probability": 58, ...}`) rather than parsing free-text. Groq and Anthropic both support structured output / JSON mode. This eliminates the entire `extraction_utils.py` regex layer and makes the system more robust.
- **Multiple model ensemble** — Run each match through two models (e.g. Llama 3.3 70B and Llama 3.1 8B) and use the majority vote as the tip. Disagreement is an explicit upset-risk signal.

#### Accuracy and tracking

- **Margin tracking** — `predicted_margin` is now stored. Build a separate accuracy metric for margin predictions (e.g. within ±12 points) in the accuracy tracker.
- **Model version tagging** — Record which AI model and prompt version generated each prediction (e.g. `"model": "llama-3.3-70b", "prompt_version": "v1.2"`). This allows attributing accuracy changes to specific prompt changes rather than guessing.
- **Season-over-season comparison** — Once 2027 data starts accumulating, the tracker should show 2026 vs. 2027 side-by-side for the same rounds.
- **Calibration curve** — Plot predicted probability vs. actual win rate (e.g. of all matches tipped at 65–70%, what % actually won?). This is the standard calibration metric and would reveal any systematic over/underconfidence.

#### Infrastructure

- **Secret rotation reminder** — The Odds API free tier (500 req/month) is tight by end of season. Add a CI step that warns when the key is approaching its limit.
- **Pre-season smoke test** — Add a `test_pipeline.py` that runs the full data fetch → prediction → save cycle with a mock round, so any broken API or missing dependency is caught before Round 1.
- **Notification on CI failure** — When the Wednesday CI run fails, there is currently no alert. Add a `on: workflow_run` handler that sends a GitHub notification or posts to a webhook if the prediction step fails.

#### Known bugs / edge cases from 2026

- `complete=!100` Squiggle query always returns HTTP 400 — the fallback works, but this log warning appears every run. Remove `complete=!100` from the first fallback group to clean up log output.
- The Squiggle API `?q=games;year=X` endpoint does not reliably return Opening Round (Round 0) games. The current workaround (querying `round=0` explicitly) works. Document this with a comment in the code and do not remove the explicit round-0 query.
- Team name normalisation: "Greater Western Sydney" vs "GWS Giants" — the current `SQUIGGLE_TEAM_NAME_MAP` handles this, but verify it covers all current team name variants at the start of 2027.

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

*v1.0 · Season 2026 · Updated July 2026*
