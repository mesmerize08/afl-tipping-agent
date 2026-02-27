"""
team_news.py
============
Scrapes AFL team selection announcements, injury reports, and suspension news.
Sources used (all free, no API key needed):
  - AFL.com.au RSS feed
  - Squiggle API injury/selection data
  - AFL official team pages
"""

import requests
import feedparser
import re
from datetime import datetime, timedelta


# ─── AFL Team Page URLs ────────────────────────────────────────────────────────
# Each AFL club publishes team selections on their website. We scrape these.
TEAM_URLS = {
    "Adelaide":         "https://www.afl.com.au/rss/news/team/adelaide-crows",
    "Brisbane Lions":   "https://www.afl.com.au/rss/news/team/brisbane-lions",
    "Carlton":          "https://www.afl.com.au/rss/news/team/carlton",
    "Collingwood":      "https://www.afl.com.au/rss/news/team/collingwood",
    "Essendon":         "https://www.afl.com.au/rss/news/team/essendon",
    "Fremantle":        "https://www.afl.com.au/rss/news/team/fremantle",
    "Geelong":          "https://www.afl.com.au/rss/news/team/geelong-cats",
    "Gold Coast":       "https://www.afl.com.au/rss/news/team/gold-coast-suns",
    "GWS Giants":       "https://www.afl.com.au/rss/news/team/gws-giants",
    "Hawthorn":         "https://www.afl.com.au/rss/news/team/hawthorn",
    "Melbourne":        "https://www.afl.com.au/rss/news/team/melbourne",
    "North Melbourne":  "https://www.afl.com.au/rss/news/team/north-melbourne",
    "Port Adelaide":    "https://www.afl.com.au/rss/news/team/port-adelaide",
    "Richmond":         "https://www.afl.com.au/rss/news/team/richmond",
    "St Kilda":         "https://www.afl.com.au/rss/news/team/st-kilda",
    "Sydney":           "https://www.afl.com.au/rss/news/team/sydney-swans",
    "West Coast":       "https://www.afl.com.au/rss/news/team/west-coast-eagles",
    "Western Bulldogs": "https://www.afl.com.au/rss/news/team/western-bulldogs",
}

# Keywords that indicate injury/selection relevant news
INJURY_KEYWORDS = [
    "injury", "injured", "out", "ruled out", "unavailable", "hamstring",
    "knee", "ankle", "shoulder", "concussion", "suspension", "banned",
    "delisted", "omitted", "dropped", "recalled", "returns", "debut",
    "selection", "named", "team list", "ins and outs", "changes",
    "indefinitely", "surgery", "fractured", "torn", "strain"
]


def is_relevant_article(title, summary):
    """Check if an article is about team news/injuries/selections."""
    text = (title + " " + summary).lower()
    return any(keyword in text for keyword in INJURY_KEYWORDS)


def get_team_news(team_name, days_back=7):
    """
    Fetch recent news for a specific team, filtered to injury/selection relevant articles.
    Returns a list of dicts with title, summary, published date.
    """
    url = TEAM_URLS.get(team_name)
    if not url:
        return []

    cutoff = datetime.now() - timedelta(days=days_back)
    articles = []

    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.get("title", "")
            summary = entry.get("summary", "")[:300]
            published_str = entry.get("published", "")

            # Try to parse the date
            try:
                published = datetime(*entry.published_parsed[:6])
                if published < cutoff:
                    continue
            except Exception:
                pass  # Include article if we can't parse date

            if is_relevant_article(title, summary):
                articles.append({
                    "team": team_name,
                    "title": title,
                    "summary": summary,
                    "published": published_str
                })

    except Exception as e:
        print(f"  Warning: Could not fetch news for {team_name}: {e}")

    return articles


def get_afl_wide_selection_news(days_back=5):
    """
    Scrape the main AFL.com.au news RSS for any selection/injury news
    across all teams. Good for catching news not on individual team pages.
    """
    articles = []
    feeds = [
        "https://www.afl.com.au/rss/news",
        "https://www.afl.com.au/rss/news/category/injuries",
    ]

    cutoff = datetime.now() - timedelta(days=days_back)

    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                title = entry.get("title", "")
                summary = entry.get("summary", "")[:300]

                try:
                    published = datetime(*entry.published_parsed[:6])
                    if published < cutoff:
                        continue
                except Exception:
                    pass

                if is_relevant_article(title, summary):
                    articles.append({
                        "team": "General",
                        "title": title,
                        "summary": summary,
                        "published": entry.get("published", "")
                    })
        except Exception as e:
            print(f"  Warning: Could not fetch AFL-wide news: {e}")

    # Deduplicate by title
    seen = set()
    unique = []
    for a in articles:
        if a["title"] not in seen:
            seen.add(a["title"])
            unique.append(a)

    return unique


def get_squiggle_tips_and_injuries():
    """
    Squiggle tracks injury/selection data via their tips endpoint.
    This gets any player-level data Squiggle exposes.
    """
    try:
        response = requests.get("https://api.squiggle.com.au/?q=games;year=2026", timeout=10)
        return response.json().get("games", [])
    except Exception:
        return []


def format_team_news_for_ai(home_team, away_team):
    """
    Fetch and format all relevant team news for both teams in a match.
    Returns a structured string ready to inject into the AI prompt.
    """
    print(f"  📰 Fetching team news for {home_team} and {away_team}...")

    home_news = get_team_news(home_team)
    away_news = get_team_news(away_team)
    general_news = get_afl_wide_selection_news()

    # Filter general news for mentions of either team
    home_keywords = home_team.lower().split()
    away_keywords = away_team.lower().split()

    relevant_general = []
    for article in general_news:
        text = (article["title"] + " " + article["summary"]).lower()
        if any(kw in text for kw in home_keywords + away_keywords):
            relevant_general.append(article)

    # Format output
    sections = []

    if home_news:
        sections.append(f"📋 {home_team.upper()} TEAM NEWS:")
        for a in home_news[:5]:
            sections.append(f"  • {a['title']}: {a['summary']}")
    else:
        sections.append(f"📋 {home_team.upper()} TEAM NEWS: No recent selection/injury news found.")

    if away_news:
        sections.append(f"\n📋 {away_team.upper()} TEAM NEWS:")
        for a in away_news[:5]:
            sections.append(f"  • {a['title']}: {a['summary']}")
    else:
        sections.append(f"\n📋 {away_team.upper()} TEAM NEWS: No recent selection/injury news found.")

    if relevant_general:
        sections.append(f"\n📋 OTHER RELEVANT AFL NEWS:")
        for a in relevant_general[:4]:
            sections.append(f"  • {a['title']}: {a['summary']}")

    return "\n".join(sections)


def get_all_teams_news_summary():
    """
    Get a quick summary of news for ALL 18 teams.
    Used for the app's news dashboard view.
    """
    all_news = []
    for team in TEAM_URLS.keys():
        news = get_team_news(team, days_back=5)
        all_news.extend(news)
    return all_news
