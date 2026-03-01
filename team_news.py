"""
team_news.py  (REWRITTEN — Zero Hanger RSS replaces dead AFL.com.au feeds)
===========================================================================
Root problem: AFL.com.au has killed all their RSS feeds (all return 404).

Solution: Zero Hanger (zerohanger.com) is Australia's leading independent
AFL news site. Their RSS feed is live, covers all 18 clubs, and specialises
in exactly what we need: injuries, suspensions, MRO decisions, and team
selection news. It is scraped here as the primary news source.

Sources used:
  PRIMARY  — Zero Hanger RSS (zerohanger.com/feed) — all teams, injuries & suspensions
  FALLBACK — Individual club websites (rss or /feed path, varies by club)

Functions:
  is_preseason()               : auto-detects preseason period
  is_relevant_article()        : keyword filter for injury/selection news
  get_zerohanger_news()        : fetch Zero Hanger RSS, filter for both teams
  get_club_rss_news()          : try individual club RSS as supplementary source
  get_team_news()              : fetch news for one team (used by Team News tab)
  get_afl_wide_selection_news(): general AFL injury/suspension feed
  format_team_news_for_ai()   : format all news into AI prompt string
  get_all_teams_news_summary() : all 18 teams (used by Streamlit Team News tab)

TEAM_URLS is kept for backward compatibility but now points to club websites
rather than the dead AFL.com.au team RSS paths.
"""

import re
import requests
import feedparser
from datetime import datetime, timedelta


# ─── Zero Hanger — primary source ─────────────────────────────────────────────

ZEROHANGER_RSS = "https://www.zerohanger.com/feed"

# ─── Individual club website RSS feeds (supplementary) ────────────────────────
# Most clubs run WordPress or similar and expose /feed or /rss
# AFL.com.au team-specific RSS feeds are all dead as of early 2026

TEAM_URLS = {
    "Adelaide":         "https://www.afc.com.au/feed",
    "Brisbane Lions":   "https://www.lions.com.au/feed",
    "Carlton":          "https://www.carltonfc.com.au/feed",
    "Collingwood":      "https://www.collingwoodfc.com.au/feed",
    "Essendon":         "https://www.essendonfc.com.au/feed",
    "Fremantle":        "https://www.fremantlefc.com.au/feed",
    "Geelong":          "https://www.geelongcats.com.au/feed",
    "Gold Coast":       "https://www.goldcoastfc.com.au/feed",
    "GWS Giants":       "https://www.gwsgiants.com.au/feed",
    "Hawthorn":         "https://www.hawthornfc.com.au/feed",
    "Melbourne":        "https://www.melbournefc.com.au/feed",
    "North Melbourne":  "https://www.nmfc.com.au/feed",
    "Port Adelaide":    "https://www.portadelaidefc.com.au/feed",
    "Richmond":         "https://www.richmondfc.com.au/feed",
    "St Kilda":         "https://www.saints.com.au/feed",
    "Sydney":           "https://www.sydneyswans.com.au/feed",
    "West Coast":       "https://www.westcoasteagles.com.au/feed",
    "Western Bulldogs": "https://www.westernbulldogs.com.au/feed",
}

# Keywords that identify injury/selection relevant content
INJURY_KEYWORDS = [
    # Availability
    "injury", "injured", "out", "ruled out", "unavailable", "sidelined",
    "indefinitely", "season-ending", "withdrawn", "won't play",
    # Body parts
    "hamstring", "knee", "ankle", "shoulder", "concussion", "calf",
    "quad", "quadricep", "groin", "back", "foot", "wrist", "finger",
    "achilles", "hip", "rib", "collarbone", "elbow", "shin", "neck",
    "pectoral", "bicep", "clavicle",
    # Medical
    "surgery", "fractured", "torn", "strain", "sprain", "soreness",
    "illness", "managed", "scans", "scanned", "medical", "rehab",
    "rehabilitation", "recovery", "setback", "timeline", "cleared",
    "test", "precaution",
    # Tribunal / MRO
    "suspension", "suspended", "banned", "tribunal", "mro",
    "match review", "rough conduct", "high contact", "week ban",
    "charged", "reported",
    # Selection
    "selection", "named", "team list", "ins and outs", "omitted",
    "dropped", "recalled", "returns", "debut", "delisted",
    # Preseason
    "preseason", "pre-season", "community series", "aami",
    "practice match", "intra-club", "intraclub", "trial",
    "contract", "signed", "trade", "draft", "retirement", "retired",
    "captain", "leadership group",
    # Opening round
    "opening round", "round 0", "round 1",
    # ── Australian AFL vernacular ─────────────────────────────────────────
    # "rubbed out" = suspended, "in doubt" = injured/uncertain,
    # "miss" used specifically in AFL injury context, "casualty ward" etc.
    "rubbed out", "in doubt", "doubt for", "will miss", "set to miss",
    "race against", "under an injury", "health scare", "fitness test",
    "fitness concern", "fitness cloud", "injury cloud", "injury scare",
    "managed load", "manage his", "manage their", "rested",
    "casualty ward", "line ball", "line-ball",
    "forced off", "helped off", "subbed out", "sub out",
    "under watch", "being monitored", "monitored closely",
    "not expected", "unlikely to play", "unlikely to feature",
    "doubtful", "questionable", "touch and go", "50-50",
    "racing the clock", "beat the clock",
    "protocols", "concussion protocols", "return to play protocol",
]

# Broader terms for preseason (lower bar for capturing team news)
PRESEASON_BROAD_KEYWORDS = [
    "player", "squad", "team", "season", "fixture", "fitness",
    "training", "camp", "preparing", "premiership",
]

# Map common team name variants to canonical names for fuzzy matching
TEAM_ALIASES = {
    "crows":       "Adelaide",
    "adelaide":    "Adelaide",
    "brisbane":    "Brisbane Lions",
    "lions":       "Brisbane Lions",
    "carlton":     "Carlton",
    "blues":       "Carlton",
    "collingwood": "Collingwood",
    "magpies":     "Collingwood",
    "pies":        "Collingwood",
    "essendon":    "Essendon",
    "bombers":     "Essendon",
    "fremantle":   "Fremantle",
    "dockers":     "Fremantle",
    "geelong":     "Geelong",
    "cats":        "Geelong",
    "gold coast":  "Gold Coast",
    "suns":        "Gold Coast",
    "gws":         "GWS Giants",
    "giants":      "GWS Giants",
    "hawthorn":    "Hawthorn",
    "hawks":       "Hawthorn",
    "melbourne":   "Melbourne",
    "demons":      "Melbourne",
    "north":       "North Melbourne",
    "kangaroos":   "North Melbourne",
    "roos":        "North Melbourne",
    "port":        "Port Adelaide",
    "power":       "Port Adelaide",
    "richmond":    "Richmond",
    "tigers":      "Richmond",
    "st kilda":    "St Kilda",
    "saints":      "St Kilda",
    "sydney":      "Sydney",
    "swans":       "Sydney",
    "west coast":  "West Coast",
    "eagles":      "West Coast",
    "bulldogs":    "Western Bulldogs",
    "dogs":        "Western Bulldogs",
}


# ─── Preseason detection ───────────────────────────────────────────────────────

def is_preseason():
    """
    True during the AFL preseason period (November through early March).
    Triggers wider search windows and looser keyword filtering.
    """
    now   = datetime.now()
    month = now.month
    day   = now.day
    if month >= 11:                  return True   # Nov, Dec
    if month <= 2:                   return True   # Jan, Feb
    if month == 3 and day <= 10:     return True   # Early March
    return False


# ─── Relevance filter ─────────────────────────────────────────────────────────

# Short keywords that need word-boundary protection to avoid substring false-positives.
# e.g. "out" would match "throughout", "test" would match "latest", etc.
_SHORT_KW_PATTERNS = [
    re.compile(r"\b" + kw + r"\b")
    for kw in ("out", "back", "test", "hip", "rib", "shin", "neck", "miss", "rested")
]

# All other keywords are long enough that substring matching is safe.
_LONG_KEYWORDS = [
    kw for kw in INJURY_KEYWORDS
    if kw not in {"out", "back", "test", "hip", "rib", "shin", "neck", "miss", "rested"}
]


def is_relevant_article(title, summary, strict=True):
    """
    Returns True if article is relevant to team news/injuries/selections.
    Uses word-boundary matching for short ambiguous keywords to avoid false
    positives (e.g. 'out' in 'throughout', 'test' in 'latest').
    strict=False includes broader terms (used in preseason).
    """
    text = (title + " " + summary).lower()

    # Long keywords: safe as substring
    if any(kw in text for kw in _LONG_KEYWORDS):
        return True

    # Short keywords: require word boundary
    if any(pat.search(text) for pat in _SHORT_KW_PATTERNS):
        return True

    if not strict and any(kw in text for kw in PRESEASON_BROAD_KEYWORDS):
        return True

    return False


def article_mentions_team(title, summary, team_name):
    """
    Check whether an article mentions a specific team by name or nickname.
    Uses TEAM_ALIASES for fuzzy matching.
    """
    text = (title + " " + summary).lower()

    # Direct name match
    if team_name.lower() in text:
        return True

    # Match any alias that maps to this team
    for alias, canonical in TEAM_ALIASES.items():
        if canonical == team_name and alias in text:
            return True

    return False


# ─── Primary source: Zero Hanger RSS ─────────────────────────────────────────

def get_zerohanger_news(days_back=None):
    """
    Fetch Zero Hanger's AFL RSS feed — the primary source for team news.
    Zero Hanger covers injuries, suspensions, MRO decisions, and selections
    for all 18 clubs. Their feed is live and updated daily.
    """
    preseason = is_preseason()
    if days_back is None:
        days_back = 21 if preseason else 7

    cutoff   = datetime.now() - timedelta(days=days_back)
    articles = []

    try:
        feed = feedparser.parse(ZEROHANGER_RSS)

        if not feed.entries:
            print("  ⚠️  Zero Hanger RSS returned no articles")
            return []

        print(f"  ✅ Zero Hanger RSS: {len(feed.entries)} articles available")

        for entry in feed.entries:
            title   = entry.get("title", "")
            summary = entry.get("summary", "")[:400]
            pub_str = entry.get("published", "")

            try:
                published = datetime(*entry.published_parsed[:6])
                if published < cutoff:
                    continue
            except Exception:
                pass

            if is_relevant_article(title, summary, strict=not preseason):
                articles.append({
                    "team":      "General",   # will be tagged per-team when filtering
                    "title":     title,
                    "summary":   summary,
                    "published": pub_str,
                    "source":    "Zero Hanger",
                })

        print(f"  📰 Zero Hanger: {len(articles)} relevant articles in last {days_back} days")

    except Exception as e:
        print(f"  ⚠️  Could not fetch Zero Hanger RSS: {e}")

    return articles


# ─── Supplementary source: individual club RSS ────────────────────────────────

def get_club_rss_news(team_name, days_back=None):
    """
    Try to fetch the individual club's own RSS/feed endpoint.
    Used as a supplementary source — some club sites work, some don't.
    Fails silently if unavailable.
    """
    url = TEAM_URLS.get(team_name)
    if not url:
        return []

    preseason = is_preseason()
    if days_back is None:
        days_back = 30 if preseason else 7

    cutoff   = datetime.now() - timedelta(days=days_back)
    articles = []

    try:
        feed = feedparser.parse(url)
        if not feed.entries or getattr(feed, 'status', 200) == 404:
            return []

        for entry in feed.entries:
            title   = entry.get("title", "")
            summary = entry.get("summary", "")[:400]
            pub_str = entry.get("published", "")

            try:
                published = datetime(*entry.published_parsed[:6])
                if published < cutoff:
                    continue
            except Exception:
                pass

            if is_relevant_article(title, summary, strict=not preseason):
                articles.append({
                    "team":      team_name,
                    "title":     title,
                    "summary":   summary,
                    "published": pub_str,
                    "source":    f"{team_name} Official Site",
                })

    except Exception:
        pass   # Silently skip clubs whose feeds are broken

    return articles


# ─── Per-team news (used by Streamlit Team News tab) ─────────────────────────

def get_team_news(team_name, days_back=None):
    """
    Get all relevant news for a single team.
    Combines Zero Hanger (filtered for this team) + club RSS (if available).
    """
    preseason = is_preseason()
    if days_back is None:
        days_back = 21 if preseason else 7

    # Zero Hanger filtered to this team
    zh_all = get_zerohanger_news(days_back=days_back)
    team_articles = [
        a for a in zh_all
        if article_mentions_team(a["title"], a["summary"], team_name)
    ]

    # Tag with team name
    for a in team_articles:
        a["team"] = team_name

    # Supplement with club RSS if available
    club_articles = get_club_rss_news(team_name, days_back=days_back)

    # Merge and deduplicate by title
    seen   = set()
    merged = []
    for a in team_articles + club_articles:
        if a["title"] not in seen:
            seen.add(a["title"])
            merged.append(a)

    return merged


# ─── General AFL news (injuries & suspensions across all teams) ───────────────

def get_afl_wide_selection_news(days_back=None):
    """
    Get broad AFL injury/suspension/selection news across all teams.
    Returns all relevant Zero Hanger articles, not filtered to specific teams.
    """
    return get_zerohanger_news(days_back=days_back)


# ─── Format for AI prompt ─────────────────────────────────────────────────────

def format_team_news_for_ai(home_team, away_team):
    """
    Fetch and format all relevant team news for both teams.
    Returns a structured string ready to inject into the AI prompt.
    """
    preseason = is_preseason()
    print(f"  📰 Fetching team news for {home_team} and {away_team}...")
    if preseason:
        print("  ℹ️  Preseason mode active — wider 21-day window")

    days_back = 21 if preseason else 7

    # Fetch Zero Hanger once, then filter per team — avoids double API call
    all_zh = get_zerohanger_news(days_back=days_back)

    home_news = [
        a for a in all_zh
        if article_mentions_team(a["title"], a["summary"], home_team)
    ]
    away_news = [
        a for a in all_zh
        if article_mentions_team(a["title"], a["summary"], away_team)
    ]

    # Supplement with club RSS
    home_club = get_club_rss_news(home_team, days_back=days_back)
    away_club = get_club_rss_news(away_team, days_back=days_back)

    def merge(main, club):
        seen = set(a["title"] for a in main)
        return main + [a for a in club if a["title"] not in seen]

    home_news = merge(home_news, home_club)
    away_news = merge(away_news, away_club)

    sections = []

    if preseason:
        sections.append(
            "NOTE: Preseason/Opening Round period. Team news covers the last 21 days. "
            "Trial match results, MRO decisions, and preseason injuries are included. "
            "Final squads may not yet be fully confirmed."
        )
        sections.append("")

    if home_news:
        sections.append(f"📋 {home_team.upper()} TEAM NEWS:")
        for a in home_news[:5]:
            sections.append(f"  • [{a.get('source','Zero Hanger')}] {a['title']}: {a['summary'][:200]}")
    else:
        sections.append(
            f"📋 {home_team.upper()} TEAM NEWS: No relevant news found in last "
            f"{'21' if preseason else '7'} days."
        )

    if away_news:
        sections.append(f"\n📋 {away_team.upper()} TEAM NEWS:")
        for a in away_news[:5]:
            sections.append(f"  • [{a.get('source','Zero Hanger')}] {a['title']}: {a['summary'][:200]}")
    else:
        sections.append(
            f"\n📋 {away_team.upper()} TEAM NEWS: No relevant news found in last "
            f"{'21' if preseason else '7'} days."
        )

    return "\n".join(sections)


# ─── All-teams news (used by Streamlit Team News tab) ─────────────────────────

def get_all_teams_news_summary():
    """
    Get relevant news for all 18 teams for the Team News tab.
    Fetches Zero Hanger once and splits by team — efficient single request.
    """
    preseason = is_preseason()
    days_back = 21 if preseason else 7
    all_zh    = get_zerohanger_news(days_back=days_back)
    all_news  = []

    for team in TEAM_URLS.keys():
        team_articles = [
            {**a, "team": team}
            for a in all_zh
            if article_mentions_team(a["title"], a["summary"], team)
        ]
        # Supplement with club RSS if it works
        club_articles = get_club_rss_news(team, days_back=days_back)
        seen = set(a["title"] for a in team_articles)
        merged = team_articles + [a for a in club_articles if a["title"] not in seen]
        all_news.extend(merged)

    return all_news
