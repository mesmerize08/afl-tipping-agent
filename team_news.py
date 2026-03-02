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

ZEROHANGER_RSS          = "https://www.zerohanger.com/feed"
ZEROHANGER_INJURIES_URL = "https://www.zerohanger.com/afl/injuries-suspensions/"

# Per-team latest news pages — not subject to the 20-article global RSS cap.
# These cover team-specific news going back weeks even when the main feed rolls over.
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


# ─── Supplementary: Zero Hanger injuries/suspensions page ────────────────────

def get_zerohanger_injuries_page(days_back=None):
    """
    Scrape Zero Hanger's dedicated Injuries & Suspensions page.

    This is a supplement to the RSS feed — it covers injury and suspension news
    across all 18 clubs and is not subject to the 20-article global RSS cap.
    Useful for catching MRO decisions, tribunal outcomes, and training injuries
    announced earlier in the week that may have been pushed off the RSS feed
    by newer articles.

    Returns articles in the same format as get_zerohanger_news().
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

        # Extract article titles and URLs from the HTML.
        # Zero Hanger article links follow a consistent pattern:
        # <a href="/some-article-slug-123456/"> or absolute URLs
        # We look for links whose text looks like an article headline.
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
                articles.append({
                    "title":     title,
                    "summary":   "",
                    "url":       url,
                    "published": datetime.now().strftime("%Y-%m-%d"),
                    "source":    "Zero Hanger (Injuries Hub)",
                })

        print(f"  📋 Zero Hanger Injuries page: {len(articles)} relevant articles found")

    except Exception as e:
        print(f"  ⚠️  Could not fetch Zero Hanger Injuries page: {e}")

    return articles


def get_zerohanger_team_page(team_name, days_back=None):
    """
    Scrape Zero Hanger's per-team latest news page.

    Each team has a dedicated page at zerohanger.com/afl/{team}-latest-news/
    which contains team-specific articles going back much further than the
    20-article global RSS feed allows.

    Called for the two specific teams playing each week, rather than all 18.
    Returns articles in the same format as get_zerohanger_news().
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
                articles.append({
                    "title":     title,
                    "summary":   "",
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

    Sources (in priority order):
      1. Zero Hanger RSS feed (latest ~20 articles, all teams)
      2. Zero Hanger Injuries & Suspensions hub (not subject to RSS cap)
      3. Zero Hanger per-team latest news pages (team-specific archive)
      4. Individual club RSS feeds (supplementary, where available)

    Sources 2 and 3 are critical for catching suspensions, MRO decisions,
    and training injuries that may have been pushed off the 20-article
    global RSS feed by more recent general news articles.
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

    # 1. Zero Hanger global RSS — fetch once, filter per team
    all_zh = get_zerohanger_news(days_back=days_back)
    home_rss = [a for a in all_zh if article_mentions_team(a["title"], a["summary"], home_team)]
    away_rss = [a for a in all_zh if article_mentions_team(a["title"], a["summary"], away_team)]

    # 2. Injuries & Suspensions hub — catches MRO/tribunal news off the main feed
    injuries_articles = get_zerohanger_injuries_page(days_back=days_back)
    home_injuries = [a for a in injuries_articles if article_mentions_team(a["title"], a["summary"], home_team)]
    away_injuries = [a for a in injuries_articles if article_mentions_team(a["title"], a["summary"], away_team)]

    # 3. Per-team news pages — team-specific archive not capped at 20 globally
    home_team_page = get_zerohanger_team_page(home_team, days_back=days_back)
    away_team_page = get_zerohanger_team_page(away_team, days_back=days_back)

    # 4. Club RSS (supplementary — many are dead but worth trying)
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
        for a in home_news[:6]:
            sections.append(f"  • [{a.get('source','Zero Hanger')}] {a['title']}: {a['summary'][:200]}")
    else:
        sections.append(
            f"📋 {home_team.upper()} TEAM NEWS: No relevant news found in last "
            f"{'21' if preseason else '7'} days."
        )

    if away_news:
        sections.append(f"\n📋 {away_team.upper()} TEAM NEWS:")
        for a in away_news[:6]:
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