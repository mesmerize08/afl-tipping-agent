# 🏉 AFL Tipping Agent

**Data-driven, unbiased, AI-powered Australian Rules Football predictions**

[![Streamlit App](https://img.shields.io/badge/Streamlit-Live%20App-FF4B4B?style=for-the-badge&logo=streamlit)](https://afl-tipping-agent.streamlit.app)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

> An intelligent AFL tipping system that combines real-time data, betting markets, team news, and AI analysis to generate weekly match predictions with confidence ratings.

**🔗 Live App:** [afl-tipping-agent.streamlit.app](https://afl-tipping-agent.streamlit.app)

---

## 📖 Table of Contents

- [Features](#-features)
- [How It Works](#-how-it-works)
- [Data Sources](#-data-sources)
- [Quick Start](#-quick-start)
- [Setup Guide](#-setup-guide)
- [Usage](#-usage)
- [Architecture](#-architecture)
- [Season 2026 Status](#-season-2026-status)
- [Contributing](#-contributing)
- [Disclaimer](#-disclaimer)
- [License](#-license)

---

## ✨ Features

### 🎯 Core Capabilities
- **AI-Powered Analysis** - Uses Claude (Anthropic) for sophisticated match predictions
- **Multi-Source Data** - Combines form, odds, team news, weather, travel, and venue data
- **Confidence Ratings** - High/Medium/Low confidence for each prediction
- **Live Tracking** - Countdown timers to match lockout for each game
- **Season Accuracy** - Tracks performance across the entire season
- **PDF Export** - Download professional prediction reports

### 📊 Data Integration
- **Real-time betting odds** (head-to-head, line, totals)
- **Team news & injuries** from Zero Hanger
- **Form analysis** (last 5 games with margins)
- **Travel & fatigue** indicators (interstate games, short turnarounds)
- **Weather data** for each venue
- **Venue performance** (home/away splits)
- **Head-to-head history** between teams

### 🎨 User Experience
- **Quick-glance summary table** - See all tips at once
- **Detailed match cards** - Expand for full AI analysis
- **Performance banner** - Last round accuracy displayed prominently
- **Responsive design** - Works on desktop and mobile
- **Dark theme** - Easy on the eyes during late-night tipping sessions

---

## 🧠 How It Works

### The Prediction Pipeline

```
1. DATA COLLECTION
   ├── Squiggle API (fixtures, ladder, results)
   ├── The Odds API (betting markets)
   ├── Zero Hanger (team news & injuries)
   ├── Open-Meteo (weather forecasts)
   └── Historical data (form, H2H, venue)

2. DATA COMPILATION
   ├── Match context (date, venue, time)
   ├── Team form (last 5 games with margins)
   ├── Betting confidence (odds → probabilities)
   ├── Team news (injuries, suspensions, selections)
   ├── Fatigue factors (travel distance, rest days)
   └── Venue performance (home/away splits)

3. AI ANALYSIS (Claude Haiku 4.5)
   ├── Analyzes all compiled data
   ├── Identifies key factors
   ├── Assesses confidence level
   ├── Generates prediction with reasoning
   └── Provides win probability & margin

4. OUTPUT
   ├── Structured predictions
   ├── Confidence ratings
   ├── PDF export option
   └── Season tracking
```

### The AI Prompt Strategy

The AI receives:
- **Quantitative data:** Ladder positions, odds, form, margins
- **Qualitative data:** Team news, injury reports, selection changes
- **Context:** Venue, weather, travel, rest days
- **Instructions:** Predict winner, probability, margin, confidence level

The AI is instructed to:
- ✅ Weight all data appropriately
- ✅ Identify conflicting signals
- ✅ Flag uncertainty with confidence ratings
- ✅ Provide clear reasoning
- ❌ Never ignore betting markets (they aggregate wisdom)
- ❌ Never pick upsets without strong evidence

---

## 📡 Data Sources

| Source | Purpose | Frequency | Cost |
|--------|---------|-----------|------|
| **[Squiggle API](https://api.squiggle.com.au)** | Fixtures, results, ladder, tips | Real-time | Free |
| **[The Odds API](https://the-odds-api.com)** | Betting odds (h2h, line, totals) | Daily | Free tier (500/month) |
| **[Zero Hanger](https://www.zerohanger.com)** | Team news, injuries, suspensions | Daily | Free (RSS) |
| **[Open-Meteo](https://open-meteo.com)** | Weather forecasts | Hourly | Free |
| **[Anthropic Claude](https://www.anthropic.com)** | AI prediction engine | Per request | ~$0.013/round |
| **[Groq](https://groq.com)** | Backup AI engine | Per request | Free tier |

**Total Cost:** ~$0.30 for a full 24-round season

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9 or higher
- API keys (see [Setup Guide](#-setup-guide))

### Installation

```bash
# Clone the repository
git clone https://github.com/mesmerize08/afl-tipping-agent.git
cd afl-tipping-agent

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with your API keys
cp .env.example .env
# Edit .env and add your API keys

# Run the app
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

---

## 🔧 Setup Guide

### 1. Get API Keys

#### Anthropic (Primary AI - Required)
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up / Log in
3. Navigate to Settings → API Keys
4. Create a new key
5. Add $5-10 credit (lasts the whole season)

**Cost:** ~$0.013 per round (~$0.30 for 24 rounds)

#### The Odds API (Betting Data - Required)
1. Go to [the-odds-api.com](https://the-odds-api.com)
2. Sign up for free account
3. Copy your API key
4. Free tier: 500 requests/month (sufficient for season)

**Cost:** Free

#### Groq (Backup AI - Optional but Recommended)
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up / Log in
3. Get your API key
4. Free tier available

**Cost:** Free

### 2. Configure Environment Variables

#### For Local Development
Create a `.env` file in the project root:

```bash
# .env file

# PRIMARY AI ENGINE (required)
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# BETTING ODDS (required)
ODDS_API_KEY=your-odds-api-key-here

# BACKUP AI ENGINE (optional but recommended)
GROQ_API_KEY=gsk_your-groq-key-here
```

#### For Streamlit Cloud
1. Go to your app settings
2. Click "Secrets"
3. Add in TOML format:

```toml
ANTHROPIC_API_KEY = "sk-ant-api03-your-key-here"
ODDS_API_KEY = "your-odds-api-key-here"
GROQ_API_KEY = "gsk_your-groq-key-here"
```

### 3. Deploy to Streamlit Cloud (Optional)

1. Fork this repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click "New app"
4. Connect your GitHub repository
5. Set main file: `app.py`
6. Add secrets (see above)
7. Deploy!

---

## 📱 Usage

### Generating Predictions

1. **Navigate to "This Week's Tips" tab**
2. **Click "Generate This Week's Tips"**
3. **Wait 45-60 seconds** while the system:
   - Fetches fixtures and ladder
   - Retrieves betting odds
   - Scrapes team news
   - Compiles match data
   - Runs AI analysis

4. **Review predictions:**
   - Quick summary table shows all tips at once
   - Detailed cards provide full analysis
   - Confidence levels guide your picks

5. **Export to PDF** (optional):
   - Click "Download PDF Report"
   - Save for your records

### Tracking Accuracy

1. **Navigate to "Accuracy Tracker" tab**
2. **View season performance:**
   - Overall accuracy percentage
   - Round-by-round breakdown
   - Favourite vs underdog picks
   - Chart of accuracy over time

3. **Update results** (after each round):
   - Go to "Update Results" tab
   - Click "Check Results & Update History"
   - System fetches results and calculates accuracy

### Browsing Team News

1. **Navigate to "Team News" tab**
2. **Select a team** or choose "All Teams"
3. **Click "Fetch Latest News"**
4. **Review articles:**
   - Injuries and suspensions
   - Team selections
   - MRO decisions
   - Coach comments

**Best times to fetch:**
- **Thursday evening** - Initial squads named
- **Friday** - Final teams confirmed
- **Any time** - For injury updates, MRO charges, tribunal results

---

## 🏗 Architecture

### Project Structure

```
afl-tipping-agent/
├── app.py                    # Main Streamlit UI
├── predict.py                # AI prediction engine
├── data_fetcher.py           # Data collection & compilation
├── tracker.py                # Accuracy tracking & history
├── team_news.py              # Team news scraping
├── pdf_export.py             # PDF generation
├── extraction_utils.py       # Shared parsing functions
├── weather.py                # Weather data fetching
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (local)
├── .gitignore               # Git ignore rules
└── README.md                # This file
```

### Key Files

#### `app.py` - User Interface
- Streamlit-based web interface
- 4 tabs: Tips, Accuracy, Team News, Update Results
- Countdown timers, performance banners, PDF export
- Environment variable validation on startup

#### `predict.py` - AI Engine
- Primary: Anthropic Claude Haiku 4.5
- Backup: Groq Llama 3.3 70B
- Retry logic with exponential backoff
- Prompt engineering for structured predictions

#### `data_fetcher.py` - Data Collection
- Squiggle API integration
- Betting odds compilation
- Match data assembly
- Travel & fatigue calculations

#### `tracker.py` - Season Tracking
- Saves predictions to JSON
- Fetches results from Squiggle
- Calculates accuracy metrics
- Automatic backup protection

#### `team_news.py` - News Scraping
- Zero Hanger RSS parsing
- Article content extraction
- Keyword filtering for relevance
- Data quality indicators

#### `pdf_export.py` - Report Generation
- Professional PDF layout
- Unicode sanitization
- Summary table + detailed analysis
- Print-ready formatting

---

## 🎯 Season 2026 Status

### ✅ Production Ready

**Launch Date:** March 5, 2026 (Round 1)

**Pre-Launch Testing:**
- ✅ All systems tested with Round 0 (pre-season)
- ✅ Team news extraction verified (player names working)
- ✅ API integrations operational
- ✅ Backup systems in place
- ✅ Performance optimized

**Known Status:**
- All data sources confirmed working for Season 2026
- Anthropic API tested and funded
- Odds API within free tier limits
- Team news scraping reliable

### Monitoring Plan

**During Season:**
- Monitor API usage (especially Odds API - 500/month limit)
- Track prediction accuracy
- Collect user feedback
- Fix issues as they arise

**After Each Round:**
- Update results (Monday/Tuesday)
- Review accuracy
- Check for any anomalies
- Update documentation if needed

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

### Reporting Issues
- Use GitHub Issues
- Include error messages
- Describe what you expected vs what happened
- Include screenshots if relevant

### Suggesting Enhancements
- Open an issue with "Enhancement" label
- Describe the feature
- Explain the use case
- Discuss implementation approach

### Code Contributions
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test thoroughly
5. Commit with clear messages (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guide
- Add type hints to functions
- Include docstrings
- Test your changes
- Update documentation

---

## 📈 Future Enhancements

### Potential Improvements
- **Player statistics** - Individual player form and impact
- **Machine learning** - Train models on historical prediction accuracy
- **Request caching** - Reduce API calls by caching data
- **Mobile app** - Native iOS/Android apps
- **Social features** - Compare tips with friends
- **Telegram bot** - Get tips via Telegram
- **Historical analysis** - Compare to expert tipsters

### Mid-Season Optimizations
- Implement request caching for Squiggle data
- Add more sophisticated travel fatigue models
- Enhance UI with interactive charts
- Add player injury impact quantification

---

## ⚠️ Disclaimer

**For Entertainment Purposes Only**

This application is designed for entertainment and educational purposes only. While it uses real data and sophisticated analysis:

- ❌ This is **NOT** professional gambling advice
- ❌ Past performance does **NOT** guarantee future results
- ❌ All predictions carry **uncertainty**
- ✅ Use at your own risk
- ✅ Gamble responsibly
- ✅ Never bet more than you can afford to lose

**The creators of this application:**
- Do not encourage gambling
- Are not responsible for any financial losses
- Provide no guarantees of accuracy
- Recommend using predictions for fun tipping competitions only

**If you have a gambling problem:**
- Call 1800 858 858 (Gambling Help Online - Australia)
- Visit [gamblinghelponline.org.au](https://www.gamblinghelponline.org.au)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### MIT License Summary

```
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software...
```

**In simple terms:**
- ✅ Use commercially
- ✅ Modify
- ✅ Distribute
- ✅ Private use
- ⚠️ Include copyright notice
- ⚠️ Include license text

---

## 🙏 Acknowledgments

### Data Providers
- **Squiggle** - For their excellent free AFL API
- **The Odds API** - For reliable betting odds data
- **Zero Hanger** - For comprehensive AFL news coverage
- **Open-Meteo** - For free weather data

### Technology
- **Anthropic** - For Claude AI API
- **Streamlit** - For the amazing web framework
- **Python** - For being awesome

### Community
- Thanks to all AFL fans who use and improve this tool
- Special thanks to contributors and issue reporters
- Shoutout to the AFL data science community

---

## 📞 Contact & Support

- **GitHub Issues:** [Report bugs or request features](https://github.com/mesmerize08/afl-tipping-agent/issues)
- **Live App:** [afl-tipping-agent.streamlit.app](https://afl-tipping-agent.streamlit.app)
- **Repository:** [github.com/mesmerize08/afl-tipping-agent](https://github.com/mesmerize08/afl-tipping-agent)

---

## ⭐ Support This Project

If you find this project useful:
- ⭐ Star this repository
- 🐛 Report bugs
- 💡 Suggest features
- 🤝 Contribute code
- 📢 Share with friends
- ☕ Buy me a coffee (optional)

---

<p align="center">
  <strong>Built with ❤️ for AFL fans</strong><br>
  <em>Data-driven. Unbiased. AI-powered.</em>
</p>

<p align="center">
  <a href="https://afl-tipping-agent.streamlit.app">
    <img src="https://img.shields.io/badge/Try%20It%20Live-FF4B4B?style=for-the-badge&logo=streamlit" alt="Try It Live">
  </a>
</p>

---

**Last Updated:** March 4, 2026 | **Season:** 2026 | **Status:** ✅ Production Ready
