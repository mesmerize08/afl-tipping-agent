# 🏉 AFL Tipping Agent — Upgrade Guide
## Adding: Accuracy Tracking + Team News Integration

This upgrade adds two major capabilities:

1. **Self-learning accuracy tracker** — every prediction is saved, compared to the real result after each round, and fed back into future prompts so the AI knows what it's been getting right and wrong
2. **Team news & injury scraper** — automatically pulls AFL.com.au team pages for injury, suspension, and selection news before each prediction

---

## 🗂️ New File Structure

After this upgrade your project should look like this:

```
afl-tipping-agent/
├── app.py                      ← REPLACE (major update — 4 new tabs)
├── predict.py                  ← REPLACE (now uses team news + history)
├── data_fetcher.py             ← Keep as-is (no changes needed)
├── team_news.py                ← NEW — scrapes injuries & selections
├── tracker.py                  ← NEW — saves & tracks accuracy
├── predictions_history.json    ← AUTO-CREATED on first run (don't touch)
├── requirements.txt            ← REPLACE (feedparser already included)
└── .github/
    └── workflows/
        └── weekly_tips.yml     ← UPDATE (see below)
```

---

## 📋 Step-by-Step Instructions

### Step 1 — Add the new files to your project folder

Copy these 2 new files into your `afl-tipping-agent` folder:
- `team_news.py`
- `tracker.py`

### Step 2 — Replace these existing files

Replace the contents of these files with the new versions:
- `app.py`
- `predict.py`
- `requirements.txt`

> **Tip:** The easiest way is to open each file in a text editor (Notepad on Windows, TextEdit on Mac), select all, delete, and paste the new content.

### Step 3 — Install the new package

Open Terminal in your project folder and run:
```bash
pip install feedparser
```
(Everything else was already installed.)

### Step 4 — Test locally

```bash
streamlit run app.py
```

You should now see **4 tabs** at the top:
- 🏉 This Week's Tips
- 📊 Accuracy Tracker  
- 📰 Team News & Injuries
- 🔄 Update Results

### Step 5 — Push to GitHub

```bash
git add .
git commit -m "Add accuracy tracking and team news integration"
git push
```

Streamlit Cloud will automatically redeploy with the new version.

---

## 📖 How the New Features Work

### 🧠 Accuracy Tracking & Self-Learning

**Every time you generate tips:**
- Predictions are auto-saved to `predictions_history.json`
- Each record stores: teams, predicted winner, confidence %, date, round

**After each round (run Monday/Tuesday):**
- Go to the **Update Results** tab and click the button
- It fetches real scores from Squiggle API automatically
- Compares your prediction to the actual result (✅ or ❌)
- Recalculates your season accuracy stats

**The following week:**
- The AI prompt now includes your accuracy history
- It sees which teams it's been wrong about
- It adjusts its confidence accordingly
- By mid-season it has a meaningful track record to learn from

**What the AI sees in future prompts (example):**
```
📊 AGENT'S OWN ACCURACY THIS SEASON:
  Overall: 38/54 (70.4% correct)
  Favourite picks: 32/40 (80%)
  Underdog picks: 6/14 (42.8%)
  Recent rounds: Rd 8: 7/9, Rd 9: 6/9, Rd 10: 8/9

🔍 PAST PREDICTIONS INVOLVING COLLINGWOOD OR ESSENDON:
  Rd 4: Collingwood vs Essendon — tipped Collingwood (72%) — ✅ CORRECT
  Rd 1: Essendon vs Carlton — tipped Essendon (58%) — ❌ WRONG (actual: Carlton)

⚠️ RECENT INCORRECT PREDICTIONS:
  Rd 9: Tipped Richmond over Melbourne — Melbourne won by 34 pts
```

### 📰 Team News & Injury Scraping

**Sources scraped (all free, no API key):**
- `afl.com.au/rss/news/team/[team-name]` — each club's official news feed
- `afl.com.au/rss/news` — AFL-wide news feed

**Keywords filtered for:**
injury, ruled out, suspension, banned, hamstring, knee, ankle, shoulder,
concussion, omitted, recalled, returns, selection, named, ins and outs, etc.

**What it adds to the AI prompt:**
```
━━━ TEAM NEWS — INJURIES, SELECTIONS & SUSPENSIONS ━━━

📋 COLLINGWOOD TEAM NEWS:
  • Brayden Maynard OUT with hamstring injury: Named in extended squad 
    but is racing the clock on a hamstring injury suffered in training...
  • Jordan De Goey returns: Star midfielder has been cleared to play after 
    missing last two rounds with a knee complaint...

📋 ESSENDON TEAM NEWS:
  • Zach Merrett suspension: Merrett has accepted a two-match ban...
```

**Best time to generate predictions:**
- 🗓️ **Thursday night or Friday** — after teams are officially named
- This ensures the injury data is fresh and accurate

---

## 🔄 Updated Weekly Workflow

| Day | Action |
|---|---|
| **Mon/Tue** | Go to **Update Results** tab → click button to record last round's results |
| **Thursday** | Teams named → open app → go to **Team News** tab → check injuries |
| **Thursday night / Friday** | Click **Generate This Week's Tips** (includes team news + updated history) |
| **Before lockout** | Review tips and make your picks! |

---

## ❓ Troubleshooting

**"No recent injury/selection news found"**
→ Try fetching on Thursday or Friday when teams are named. Earlier in the week there's less news.

**Predictions saving but results not updating**
→ Make sure you wait until Monday/Tuesday when Squiggle has processed all scores. Squiggle sometimes takes 24hrs after the final game.

**predictions_history.json not found**
→ It's created automatically on your first prediction run. Don't create it manually.

**Team news showing articles that aren't relevant**
→ The keyword filter is intentionally broad to avoid missing important news. The AI is instructed to judge relevance itself.

---

## 💡 How Accuracy Improves Over Time

| Round | What the agent knows |
|---|---|
| Rd 1 | No history — pure data analysis |
| Rd 3-4 | Starting to see patterns in what it gets right/wrong |
| Rd 10 | Knows its favourite-pick vs underdog accuracy, adjusts confidence |
| Rd 20 | Rich history — knows specific teams it tends to misjudge |
| Finals | Fully calibrated for the season's patterns |

The key insight: if the AI discovers it has only 30% accuracy on underdog picks,
it will automatically become more conservative about tipping upsets — becoming
a better, more calibrated predictor as the season goes on.

---

*Good luck with the tipping comp! 🏉🏆*
