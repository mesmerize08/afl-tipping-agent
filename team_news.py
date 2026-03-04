"""
team_news.py  (OPTIMIZED — Full article content fetching added)
==================================================================
Root problem: AFL.com.au has killed all their RSS feeds (all return 404).

Solution: Zero Hanger (zerohanger.com) is Australia's leading independent
AFL news site. Their RSS feed is live, covers all 18 clubs, and specialises
in exactly what we need: injuries, suspensions, MRO decisions, and team
selection news.

NEW IN THIS VERSION:
  - Fetches full article content from URLs (not just headlines)
  - Extracts actual player names, injuries, suspensions
  - Provides meaningful content for AI analysis

Sources used:
  PRIMARY  — Zero Hanger RSS (zerohanger.com/feed) — all teams, injuries & suspensions
  FALLBACK — Individual club websites (rss or /feed path, varies by club)
"""

import re
import requests
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional


# ─── Zero Hanger — primary source ─────────────────────────────────────────────

ZEROHANGER_RSS          = "https://www.zerohanger.com/feed"
ZEROHANGER_INJURIES_URL = "https://www.zerohanger.com/afl/injuries-suspensions/"

# Per-team latest news pages
ZEROHANGER_TEAM_NEWS_URLS = {
    "Adelaide":         "https://www.zerohanger.com/afl/adelaide-crows-latest-news/",
    "Brisbane Lions":   "https://www.zerohanger.com/afl/brisbane-lions-latest-news/",
    "Carlton":          "https://www.zerohanger.com/afl/carlton-blues-latest-news/",
    "Collingwood":      "https://www.zerohanger.com/afl/collingwood-magpies-latest-news/",
    "Essendon":         "https://www.zerohanger.com/afl/essendon-bombers-latest-news/",
    "Fremantle":        "https://www.zerohanger.com/afl/fremantle-dockers-latest-news/",
    "Geelong":          "https://www.zerohanger.com/afl/geelong-cats-latest-news/",
    "Gold Coast":       "https://www.zerohanger.com/afl/gold-coast-suns-latest-news/",
    "GWS Giants":       "https://www.zerohanger.com/afl/gws-giants-latest-news/",
    "Hawthorn":         "https://www.zerohanger.com/afl/hawthorn-hawks-latest-news/",
    "Melbourne":        "https://www.zerohanger.com/afl/melbourne-demons-latest-news/",
    "North Melbourne":  "https://www.zerohanger.com/afl/north-melbourne-kangaroos-latest-news/",
    "Port Adelaide":    "https://www.zerohanger.com/afl/port-adelaide-power-latest-news/",
    "Richmond":         "https://www.zerohanger.com/afl/richmond-tigers-latest-news/",
    "St Kilda":         "https://www.zerohanger.com/afl/st-kilda-saints-latest-news/",
    "Sydney":           "https://www.zerohanger.com/afl/sydney-swans-latest-news/",
    "West Coast":       "https://www.zerohanger.com/afl/west-coast-eagles-latest-news/",
    "Western Bulldogs": "https://www.zerohanger.com/afl/western-bulldogs-latest-news/",
}

# Individual club website RSS feeds (supplementary)
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
    # Australian AFL vernacular
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

# Broader terms for preseason
PRESEASON_BROAD_KEYWORDS = [
    "player", "squad", "team", "season", "fixture", "fitness",
    "training", "camp", "preparing", "premiership",
]

# Map common team name variants to canonical names
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


# ─── NEW: Fetch full article content ──────────────────────────────────────────

def fetch_article_content(url: str, max_length: int = 800) -> str:
    """
    Fetch the full article content from a Zero Hanger URL.
    Extracts the main article text with player names, injuries, etc.
    
    Args:
        url: Article URL
        max_length: Maximum characters to return
        
    Returns:
        Article content or empty string if fetch fails
    """
    try:
        headers = {"User-Agent": "AFL-Tipping-Agent/1.0 (github.com/mesmerize08/afl-tipping-agent)"}
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
        html = response.text
        
        # Extract article content from common WordPress patterns
        # Zero Hanger uses WordPress, so content is typically in:
        # <div class="entry-content"> or <article> or <div class="post-content">
        
        # Try multiple patterns to extract article text
        patterns = [
            r'<div[^>]*class="[^"]*entry-content[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*post-content[^"]*"[^>]*>(.*?)</div>',
            r'<article[^>]*>(.*?)</article>',
            r'<div[^>]*class="[^"]*article-content[^"]*"[^>]*>(.*?)</div>',
        ]
        
        content = ""
        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1)
                break
        
        if not content:
            # Fallback: try to find any large text block after the title
            # Look for <p> tags with substantial content
            paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
            # Filter out short paragraphs (likely navigation/ads)
            substantial = [p for p in paragraphs if len(p) > 50]
            if substantial:
                content = " ".join(substantial[:5])  # First 5 paragraphs
        
        if not content:
            return ""
        
        # Clean HTML tags
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
        content = re.sub(r'<[^>]+>', ' ', content)
        
        # Decode HTML entities
        content = content.replace('&nbsp;', ' ')
        content = content.replace('&amp;', '&')
        content = content.replace('&lt;', '<')
        content = content.replace('&gt;', '>')
        content = content.replace('&quot;', '"')
        content = content.replace('&#8217;', "'")
        content = content.replace('&#8220;', '"')
        content = content.replace('&#8221;', '"')
        content = content.replace('&#8211;', '-')
        content = content.replace('&#8212;', '--')
        
        # Clean whitespace
        content = re.sub(r'\s+', ' ', content)
        content = content.strip()
        
        # Truncate to max length
        if len(content) > max_length:
            content = content[:max_length] + "..."
        
        return content
        
    except Exception as e:
        # Silently fail - we'll just have empty summary
        return ""


# ─── Preseason detection ───────────────────────────────────────────────────────

def is_preseason() -> bool:
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

# Short keywords that need word-boundary protection
_SHORT_KW_PATTERNS = [
    re.compile(r"\b" + kw + r"\b")
    for kw in ("out", "back", "test", "hip", "rib", "shin", "neck", "miss", "rested")
]

# All other keywords are long enough that substring matching is safe
_LONG_KEYWORDS = [
    kw for kw in INJURY_KEYWORDS
    if kw not in {"out", "back", "test", "hip", "rib", "shin", "neck", "miss", "rested"}
]


def is_relevant_article(title: str, summary: str, strict: bool = True) -> bool:
    """
    Returns True if article is relevant to team news/injuries/selections.
    Uses word-boundary matching for short ambiguous keywords.
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


def article_mentions_team(title: str, summary: str, team_name: str) -> bool:
    """
    Check whether an article mentions a specific team by name or nickname.
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


# ─── Zero Hanger injuries/suspensions page ────────────────────────────────────

def get_zerohanger_injuries_page(days_back: Optional[int] = None) -> List[Dict]:
    """
    Scrape Zero Hanger's dedicated Injuries & Suspensions page.
    NOW FETCHES FULL ARTICLE CONTENT.
    """
    import re as _re

    preseason = is_preseason()
    if days_back is None:
        days_back = 21 if preseason else 10

    cutoff   = datetime.now() - timedelta(days=days_back)
    articles = []

    try:
        headers  = {"User-Agent": "AFL-Tipping-Agent/1.0 (github.com/mesmerize08/afl-tipping-agent)"}
        response = requests.get(ZEROHANGER_INJURIES_URL, timeout=15, headers=headers)
        html     = response.text

        # Extract article links
        link_pattern = _re.compile(
            r'href="(https?://www\.zerohanger\.com/[^"]+?-\d{4,}/?)"[^>]*>([^<]{20,200})</a>',
            _re.IGNORECASE
        )
        seen_urls = set()
        for match in link_pattern.finditer(html):
            url, title = match.group(1), match.group(2).strip()
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            # Filter to only injury/suspension/selection relevant headlines
            if is_relevant_article(title, title, strict=not preseason):
                # NEW: Fetch full article content
                content = fetch_article_content(url, max_length=600)
                
                articles.append({
                    "title":     title,
                    "summary":   content if content else title,  # Fallback to title if fetch fails
                    "url":       url,
                    "published": datetime.now().strftime("%Y-%m-%d"),
                    "source":    "Zero Hanger (Injuries Hub)",
                })

        print(f"  📋 Zero Hanger Injuries page: {len(articles)} relevant articles found")

    except Exception as e:
        print(f"  ⚠️  Could not fetch Zero Hanger Injuries page: {e}")

    return articles


def get_zerohanger_team_page(team_name: str, days_back: Optional[int] = None) -> List[Dict]:
    """
    Scrape Zero Hanger's per-team latest news page.
    NOW FETCHES FULL ARTICLE CONTENT.
    """
    import re as _re

    url = ZEROHANGER_TEAM_NEWS_URLS.get(team_name)
    if not url:
        return []

    preseason = is_preseason()
    if days_back is None:
        days_back = 21 if preseason else 10

    articles = []

    try:
        headers  = {"User-Agent": "AFL-Tipping-Agent/1.0 (github.com/mesmerize08/afl-tipping-agent)"}
        response = requests.get(url, timeout=15, headers=headers)
        html     = response.text

        link_pattern = _re.compile(
            r'href="(https?://www\.zerohanger\.com/[^"]+?-\d{4,}/?)"[^>]*>([^<]{20,200})</a>',
            _re.IGNORECASE
        )
        seen_urls = set()
        for match in link_pattern.finditer(html):
            article_url, title = match.group(1), match.group(2).strip()
            if article_url in seen_urls:
                continue
            seen_urls.add(article_url)
            
            if is_relevant_article(title, title, strict=not preseason):
                # NEW: Fetch full article content
                content = fetch_article_content(article_url, max_length=600)
                
                articles.append({
                    "title":     title,
                    "summary":   content if content else title,  # Fallback to title
                    "url":       article_url,
                    "published": datetime.now().strftime("%Y-%m-%d"),
                    "source":    f"Zero Hanger ({team_name})",
                })

        if articles:
            print(f"  📋 Zero Hanger {team_name} page: {len(articles)} relevant articles")

    except Exception as e:
        print(f"  ⚠️  Could not fetch Zero Hanger {team_name} page: {e}")

    return articles


# ─── Primary source: Zero Hanger RSS ─────────────────────────────────────────

def get_zerohanger_news(days_back: Optional[int] = None) -> List[Dict]:
    """
    Fetch Zero Hanger's AFL RSS feed — the primary source for team news.
    RSS feed already has summaries, but we can enhance them if needed.
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
            summary = entry.get("summary", "")[:800]  # Increased from 400 to 800
            pub_str = entry.get("published", "")
            url     = entry.get("link", "")

            try:
                published = datetime(*entry.published_parsed[:6])
                if published < cutoff:
                    continue
            except Exception:
                pass

            if is_relevant_article(title, summary, strict=not preseason):
                # If summary is too short, try to fetch full content
                if len(summary) < 100 and url:
                    full_content = fetch_article_content(url, max_length=600)
                    if full_content:
                        summary = full_content
                
                articles.append({
                    "team":      "General",
                    "title":     title,
                    "summary":   summary if summary else title,
                    "published": pub_str,
                    "source":    "Zero Hanger",
                })

        print(f"  📰 Zero Hanger: {len(articles)} relevant articles in last {days_back} days")

    except Exception as e:
        print(f"  ⚠️  Could not fetch Zero Hanger RSS: {e}")

    return articles


# ─── Supplementary source: individual club RSS ────────────────────────────────

def get_club_rss_news(team_name: str, days_back: Optional[int] = None) -> List[Dict]:
    """
    Try to fetch the individual club's own RSS/feed endpoint.
    Used as a supplementary source.
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
            summary = entry.get("summary", "")[:800]  # Increased from 400
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
                    "summary":   summary if summary else title,
                    "published": pub_str,
                    "source":    f"{team_name} Official Site",
                })

    except Exception:
        pass   # Silently skip clubs whose feeds are broken

    return articles


# ─── Per-team news (used by Streamlit Team News tab) ─────────────────────────

def get_team_news(team_name: str, days_back: Optional[int] = None) -> List[Dict]:
    """
    Get all relevant news for a single team.
    Combines all four sources with full article content.
    """
    preseason = is_preseason()
    if days_back is None:
        days_back = 21 if preseason else 7

    # 1. Zero Hanger RSS filtered to this team
    zh_all = get_zerohanger_news(days_back=days_back)
    rss_articles = [
        {**a, "team": team_name}
        for a in zh_all
        if article_mentions_team(a["title"], a["summary"], team_name)
    ]

    # 2. Injuries & Suspensions hub (now with full content)
    injuries_all     = get_zerohanger_injuries_page(days_back=days_back)
    injuries_articles = [
        {**a, "team": team_name}
        for a in injuries_all
        if article_mentions_team(a["title"], a["summary"], team_name)
    ]

    # 3. Per-team news page (now with full content)
    team_page_articles = [
        {**a, "team": team_name}
        for a in get_zerohanger_team_page(team_name, days_back=days_back)
    ]

    # 4. Club RSS
    club_articles = [
        {**a, "team": team_name}
        for a in get_club_rss_news(team_name, days_back=days_back)
    ]

    # Merge and deduplicate by title
    seen, merged = set(), []
    for a in rss_articles + injuries_articles + team_page_articles + club_articles:
        key = a["title"].lower().strip()
        if key not in seen:
            seen.add(key)
            merged.append(a)

    return merged


# ─── General AFL news ──────────────────────────────────────────────────────────

def get_afl_wide_selection_news(days_back: Optional[int] = None) -> List[Dict]:
    """
    Get broad AFL injury/suspension/selection news across all teams.
    """
    return get_zerohanger_news(days_back=days_back)


# ─── Format for AI prompt ─────────────────────────────────────────────────────

def format_team_news_for_ai(home_team: str, away_team: str) -> str:
    """
    Fetch and format all relevant team news for both teams.
    Returns a structured string ready to inject into the AI prompt.
    NOW WITH FULL ARTICLE CONTENT.
    """
    preseason = is_preseason()
    print(f"  📰 Fetching team news for {home_team} and {away_team}...")
    if preseason:
        print("  ℹ️  Preseason mode active — wider 21-day window")

    days_back = 21 if preseason else 7

    def merge(*sources):
        """Merge article lists, deduplicating by title."""
        seen, result = set(), []
        for source in sources:
            for a in source:
                key = a["title"].lower().strip()
                if key not in seen:
                    seen.add(key)
                    result.append(a)
        return result

    # Fetch from all sources (now with full content)
    all_zh = get_zerohanger_news(days_back=days_back)
    home_rss = [a for a in all_zh if article_mentions_team(a["title"], a["summary"], home_team)]
    away_rss = [a for a in all_zh if article_mentions_team(a["title"], a["summary"], away_team)]

    injuries_articles = get_zerohanger_injuries_page(days_back=days_back)
    home_injuries = [a for a in injuries_articles if article_mentions_team(a["title"], a["summary"], home_team)]
    away_injuries = [a for a in injuries_articles if article_mentions_team(a["title"], a["summary"], away_team)]

    home_team_page = get_zerohanger_team_page(home_team, days_back=days_back)
    away_team_page = get_zerohanger_team_page(away_team, days_back=days_back)

    home_club = get_club_rss_news(home_team, days_back=days_back)
    away_club = get_club_rss_news(away_team, days_back=days_back)

    # Merge all sources, deduplicated
    home_news = merge(home_rss, home_injuries, home_team_page, home_club)
    away_news = merge(away_rss, away_injuries, away_team_page, away_club)

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
        for a in home_news[:6]:  # Top 6 articles
            # Now includes full content, not just title
            sections.append(f"  • [{a.get('source','Zero Hanger')}] {a['title']}")
            if a.get('summary') and len(a['summary']) > 10:
                sections.append(f"    {a['summary'][:500]}")  # Show summary content
    else:
        sections.append(
            f"📋 {home_team.upper()} TEAM NEWS: No relevant news found in last "
            f"{'21' if preseason else '7'} days."
        )

    if away_news:
        sections.append(f"\n📋 {away_team.upper()} TEAM NEWS:")
        for a in away_news[:6]:
            sections.append(f"  • [{a.get('source','Zero Hanger')}] {a['title']}")
            if a.get('summary') and len(a['summary']) > 10:
                sections.append(f"    {a['summary'][:500]}")
    else:
        sections.append(
            f"\n📋 {away_team.upper()} TEAM NEWS: No relevant news found in last "
            f"{'21' if preseason else '7'} days."
        )

    return "\n".join(sections)


# ─── All-teams news (used by Streamlit Team News tab) ─────────────────────────

def get_all_teams_news_summary() -> List[Dict]:
    """
    Get relevant news for all 18 teams for the Team News tab.
    NOW WITH FULL ARTICLE CONTENT.
    """
    preseason = is_preseason()
    days_back = 21 if preseason else 7

    # Fetch both sources once
    all_zh       = get_zerohanger_news(days_back=days_back)
    all_injuries = get_zerohanger_injuries_page(days_back=days_back)
    all_news     = []

    for team in TEAM_URLS.keys():
        # RSS articles for this team
        rss_articles = [
            {**a, "team": team}
            for a in all_zh
            if article_mentions_team(a["title"], a["summary"], team)
        ]
        # Injuries hub articles for this team
        injury_articles = [
            {**a, "team": team}
            for a in all_injuries
            if article_mentions_team(a["title"], a["summary"], team)
        ]
        # Club RSS supplement
        club_articles = get_club_rss_news(team, days_back=days_back)

        seen, merged = set(), []
        for a in rss_articles + injury_articles + club_articles:
            key = a["title"].lower().strip()
            if key not in seen:
                seen.add(key)
                merged.append(a)

        all_news.extend(merged)

    return all_news
