"""
team_news.py  (FINAL — Multiple sources, robust fallbacks, clear AI formatting)
================================================================================
STRATEGY CHANGE: Accept that full article scraping is unreliable.
Focus on: 1) Good RSS summaries, 2) Clear formatting for AI, 3) Multiple sources

KEY IMPROVEMENTS:
  - Uses RSS summaries as primary source (they're often good enough)
  - Only scrapes articles if RSS summary is too short (<100 chars)
  - Clearly formats data for AI with explicit data quality indicators
  - Multiple fallback strategies
  - Tells AI when data is limited (so it can weight other factors more)
"""

import re
import requests
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

# ─── Configuration ─────────────────────────────────────────────────────────────

ZEROHANGER_RSS = "https://www.zerohanger.com/feed"
ZEROHANGER_INJURIES_URL = "https://www.zerohanger.com/afl/injuries-suspensions/"

# Official AFL sources (better reliability)
AFL_OFFICIAL_NEWS = "https://www.afl.com.au/api/news/all"  # JSON API

ZEROHANGER_TEAM_NEWS_URLS = {
    "Adelaide": "https://www.zerohanger.com/afl/adelaide-crows-latest-news/",
    "Brisbane Lions": "https://www.zerohanger.com/afl/brisbane-lions-latest-news/",
    "Carlton": "https://www.zerohanger.com/afl/carlton-blues-latest-news/",
    "Collingwood": "https://www.zerohanger.com/afl/collingwood-magpies-latest-news/",
    "Essendon": "https://www.zerohanger.com/afl/essendon-bombers-latest-news/",
    "Fremantle": "https://www.zerohanger.com/afl/fremantle-dockers-latest-news/",
    "Geelong": "https://www.zerohanger.com/afl/geelong-cats-latest-news/",
    "Gold Coast": "https://www.zerohanger.com/afl/gold-coast-suns-latest-news/",
    "GWS Giants": "https://www.zerohanger.com/afl/gws-giants-latest-news/",
    "Hawthorn": "https://www.zerohanger.com/afl/hawthorn-hawks-latest-news/",
    "Melbourne": "https://www.zerohanger.com/afl/melbourne-demons-latest-news/",
    "North Melbourne": "https://www.zerohanger.com/afl/north-melbourne-kangaroos-latest-news/",
    "Port Adelaide": "https://www.zerohanger.com/afl/port-adelaide-power-latest-news/",
    "Richmond": "https://www.zerohanger.com/afl/richmond-tigers-latest-news/",
    "St Kilda": "https://www.zerohanger.com/afl/st-kilda-saints-latest-news/",
    "Sydney": "https://www.zerohanger.com/afl/sydney-swans-latest-news/",
    "West Coast": "https://www.zerohanger.com/afl/west-coast-eagles-latest-news/",
    "Western Bulldogs": "https://www.zerohanger.com/afl/western-bulldogs-latest-news/",
}

TEAM_URLS = {
    "Adelaide": "https://www.afc.com.au/feed",
    "Brisbane Lions": "https://www.lions.com.au/feed",
    "Carlton": "https://www.carltonfc.com.au/feed",
    "Collingwood": "https://www.collingwoodfc.com.au/feed",
    "Essendon": "https://www.essendonfc.com.au/feed",
    "Fremantle": "https://www.fremantlefc.com.au/feed",
    "Geelong": "https://www.geelongcats.com.au/feed",
    "Gold Coast": "https://www.goldcoastfc.com.au/feed",
    "GWS Giants": "https://www.gwsgiants.com.au/feed",
    "Hawthorn": "https://www.hawthornfc.com.au/feed",
    "Melbourne": "https://www.melbournefc.com.au/feed",
    "North Melbourne": "https://www.nmfc.com.au/feed",
    "Port Adelaide": "https://www.portadelaidefc.com.au/feed",
    "Richmond": "https://www.richmondfc.com.au/feed",
    "St Kilda": "https://www.saints.com.au/feed",
    "Sydney": "https://www.sydneyswans.com.au/feed",
    "West Coast": "https://www.westcoasteagles.com.au/feed",
    "Western Bulldogs": "https://www.westernbulldogs.com.au/feed",
}

INJURY_KEYWORDS = [
    "injury", "injured", "out", "ruled out", "unavailable", "sidelined",
    "hamstring", "knee", "ankle", "shoulder", "concussion", "calf",
    "surgery", "fractured", "torn", "strain", "managed", "rehab",
    "suspension", "suspended", "tribunal", "mro", "charged",
    "selection", "named", "omitted", "dropped", "recalled", "returns",
    "preseason", "doubt", "fitness", "test", "cleared",
]

TEAM_ALIASES = {
    "crows": "Adelaide", "adelaide": "Adelaide",
    "brisbane": "Brisbane Lions", "lions": "Brisbane Lions",
    "carlton": "Carlton", "blues": "Carlton",
    "collingwood": "Collingwood", "magpies": "Collingwood", "pies": "Collingwood",
    "essendon": "Essendon", "bombers": "Essendon",
    "fremantle": "Fremantle", "dockers": "Fremantle",
    "geelong": "Geelong", "cats": "Geelong",
    "gold coast": "Gold Coast", "suns": "Gold Coast",
    "gws": "GWS Giants", "giants": "GWS Giants",
    "hawthorn": "Hawthorn", "hawks": "Hawthorn",
    "melbourne": "Melbourne", "demons": "Melbourne",
    "north": "North Melbourne", "kangaroos": "North Melbourne",
    "port": "Port Adelaide", "power": "Port Adelaide",
    "richmond": "Richmond", "tigers": "Richmond",
    "st kilda": "St Kilda", "saints": "St Kilda",
    "sydney": "Sydney", "swans": "Sydney",
    "west coast": "West Coast", "eagles": "West Coast",
    "bulldogs": "Western Bulldogs", "dogs": "Western Bulldogs",
}

# ─── Enhanced Content Extraction ──────────────────────────────────────────────

def extract_article_content_aggressive(url: str) -> str:
    """
    Aggressive multi-method content extraction.
    Returns content or empty string (never fails).
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, timeout=12, headers=headers)
        response.raise_for_status()
        html = response.text
        
        content = ""
        
        # Method 1: BeautifulSoup (if available)
        if HAS_BS4 and not content:
            try:
                soup = BeautifulSoup(html, 'lxml')
                
                # Remove noise
                for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
                    tag.decompose()
                
                # Try article tag
                article = soup.find('article')
                if article:
                    content = article.get_text(separator=' ', strip=True)
                
                # Try entry-content
                if not content or len(content) < 100:
                    entry = soup.find('div', class_=re.compile(r'entry-content|post-content'))
                    if entry:
                        content = entry.get_text(separator=' ', strip=True)
                
                # Try main paragraphs
                if not content or len(content) < 100:
                    paragraphs = soup.find_all('p')
                    substantial = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40]
                    if substantial:
                        content = ' '.join(substantial[:10])
            except:
                pass
        
        # Method 2: Regex extraction (fallback)
        if not content or len(content) < 100:
            # Try to find article content
            patterns = [
                r'<article[^>]*>(.*?)</article>',
                r'<div[^>]*class="[^"]*entry-content[^"]*"[^>]*>(.*?)</div>',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
                if match:
                    raw = match.group(1)
                    # Remove tags
                    clean = re.sub(r'<[^>]+>', ' ', raw)
                    clean = re.sub(r'\s+', ' ', clean).strip()
                    if len(clean) > len(content):
                        content = clean
        
        # Method 3: Extract ALL paragraphs as last resort
        if not content or len(content) < 100:
            paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
            substantial = []
            for p in paragraphs:
                clean = re.sub(r'<[^>]+>', '', p)
                clean = re.sub(r'\s+', ' ', clean).strip()
                if len(clean) > 40 and 'cookie' not in clean.lower():
                    substantial.append(clean)
            
            if substantial:
                content = ' '.join(substantial[:10])
        
        # Clean final content
        if content:
            # Decode HTML entities
            replacements = {
                '&nbsp;': ' ', '&amp;': '&', '&lt;': '<', '&gt;': '>',
                '&quot;': '"', '&#8217;': "'", '&#8220;': '"', '&#8221;': '"',
                '&#8211;': '-', '&#8212;': '--'
            }
            for entity, char in replacements.items():
                content = content.replace(entity, char)
            
            content = re.sub(r'\s+', ' ', content).strip()
            
            # Truncate
            if len(content) > 900:
                content = content[:900] + "..."
            
            return content
        
        return ""
        
    except:
        return ""


# ─── Utility Functions ─────────────────────────────────────────────────────────

def is_preseason() -> bool:
    now = datetime.now()
    month, day = now.month, now.day
    return month >= 11 or month <= 2 or (month == 3 and day <= 10)


def is_relevant_article(title: str, summary: str) -> bool:
    text = (title + " " + summary).lower()
    return any(kw in text for kw in INJURY_KEYWORDS)


def article_mentions_team(title: str, summary: str, team_name: str) -> bool:
    text = (title + " " + summary).lower()
    if team_name.lower() in text:
        return True
    for alias, canonical in TEAM_ALIASES.items():
        if canonical == team_name and alias in text:
            return True
    return False


# ─── RSS Feed Functions ────────────────────────────────────────────────────────

def get_zerohanger_news(days_back: Optional[int] = None) -> List[Dict]:
    """Get Zero Hanger RSS feed (primary source)."""
    preseason = is_preseason()
    if days_back is None:
        days_back = 21 if preseason else 7
    
    cutoff = datetime.now() - timedelta(days=days_back)
    articles = []
    
    try:
        feed = feedparser.parse(ZEROHANGER_RSS)
        
        if not feed.entries:
            return []
        
        for entry in feed.entries:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            url = entry.get("link", "")
            pub_str = entry.get("published", "")
            
            try:
                published = datetime(*entry.published_parsed[:6])
                if published < cutoff:
                    continue
            except:
                pass
            
            if is_relevant_article(title, summary):
                # STRATEGY: Use RSS summary if it's substantial (>100 chars)
                # Otherwise, try to scrape article content
                if len(summary) < 100 and url:
                    scraped = extract_article_content_aggressive(url)
                    if scraped and len(scraped) > len(summary):
                        summary = scraped
                
                # Always include at least the title
                if not summary or len(summary) < 20:
                    summary = f"[Headline only] {title}"
                
                articles.append({
                    "team": "General",
                    "title": title,
                    "summary": summary,
                    "published": pub_str,
                    "source": "Zero Hanger",
                    "url": url,
                    "data_quality": "good" if len(summary) > 100 else "limited",
                })
        
        print(f"  📰 Zero Hanger RSS: {len(articles)} relevant articles")
        
    except Exception as e:
        print(f"  ⚠️  Zero Hanger RSS failed: {e}")
    
    return articles


def get_club_rss_news(team_name: str, days_back: Optional[int] = None) -> List[Dict]:
    """Get official club RSS."""
    url = TEAM_URLS.get(team_name)
    if not url:
        return []
    
    preseason = is_preseason()
    if days_back is None:
        days_back = 30 if preseason else 7
    
    cutoff = datetime.now() - timedelta(days=days_back)
    articles = []
    
    try:
        feed = feedparser.parse(url)
        if not feed.entries:
            return []
        
        for entry in feed.entries:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            pub_str = entry.get("published", "")
            
            try:
                published = datetime(*entry.published_parsed[:6])
                if published < cutoff:
                    continue
            except:
                pass
            
            if is_relevant_article(title, summary):
                articles.append({
                    "team": team_name,
                    "title": title,
                    "summary": summary if summary else title,
                    "published": pub_str,
                    "source": f"{team_name} Official",
                    "data_quality": "good" if len(summary) > 100 else "limited",
                })
    except:
        pass
    
    return articles


def get_team_news(team_name: str, days_back: Optional[int] = None) -> List[Dict]:
    """Get all news for a single team."""
    preseason = is_preseason()
    if days_back is None:
        days_back = 21 if preseason else 7
    
    # Get from all sources
    zh_all = get_zerohanger_news(days_back=days_back)
    rss_articles = [
        {**a, "team": team_name}
        for a in zh_all
        if article_mentions_team(a["title"], a["summary"], team_name)
    ]
    
    club_articles = [
        {**a, "team": team_name}
        for a in get_club_rss_news(team_name, days_back=days_back)
    ]
    
    # Deduplicate
    seen, merged = set(), []
    for a in rss_articles + club_articles:
        key = a["title"].lower().strip()
        if key not in seen:
            seen.add(key)
            merged.append(a)
    
    return merged


# ─── AI Prompt Formatting (CRITICAL) ───────────────────────────────────────────

def format_team_news_for_ai(home_team: str, away_team: str) -> str:
    """
    Format team news for AI with EXPLICIT data quality indicators.
    AI needs to know when data is limited so it can weight other factors more.
    """
    preseason = is_preseason()
    print(f"  📰 Fetching team news: {home_team} vs {away_team}")
    
    days_back = 21 if preseason else 7
    
    home_news = get_team_news(home_team, days_back=days_back)
    away_news = get_team_news(away_team, days_back=days_back)
    
    sections = []
    
    # Add data quality warning at the top
    sections.append("=" * 70)
    sections.append("TEAM NEWS DATA QUALITY NOTICE")
    sections.append("=" * 70)
    sections.append("")
    
    if preseason:
        sections.append("⚠️  PRESEASON MODE: Team news covers 21 days. Squad changes expected.")
    
    # Check overall data quality
    home_quality = sum(1 for a in home_news if a.get("data_quality") == "good")
    away_quality = sum(1 for a in away_news if a.get("data_quality") == "good")
    
    if home_quality == 0 and away_quality == 0:
        sections.append("")
        sections.append("⚠️  WARNING: Limited team news detail available.")
        sections.append("Recommendation: Weight form, odds, and venue data more heavily.")
        sections.append("")
    
    sections.append("=" * 70)
    sections.append("")
    
    # HOME TEAM
    sections.append(f"{'─' * 70}")
    sections.append(f"{home_team.upper()} TEAM NEWS")
    sections.append(f"{'─' * 70}")
    
    if home_news:
        sections.append(f"Found {len(home_news)} relevant articles ({home_quality} with detailed content)")
        sections.append("")
        
        for i, article in enumerate(home_news[:5], 1):
            quality = article.get("data_quality", "unknown")
            source = article.get("source", "Unknown")
            
            sections.append(f"Article {i}: [{source}]")
            sections.append(f"Title: {article['title']}")
            sections.append(f"Data Quality: {quality.upper()}")
            
            summary = article.get("summary", "")
            if summary and len(summary) > 30:
                sections.append(f"Content: {summary[:700]}")
            else:
                sections.append("Content: [Headline only - no details available]")
            
            sections.append("")
    else:
        sections.append(f"⚠️  NO RELEVANT NEWS found in last {days_back} days.")
        sections.append("")
    
    # AWAY TEAM
    sections.append(f"{'─' * 70}")
    sections.append(f"{away_team.upper()} TEAM NEWS")
    sections.append(f"{'─' * 70}")
    
    if away_news:
        sections.append(f"Found {len(away_news)} relevant articles ({away_quality} with detailed content)")
        sections.append("")
        
        for i, article in enumerate(away_news[:5], 1):
            quality = article.get("data_quality", "unknown")
            source = article.get("source", "Unknown")
            
            sections.append(f"Article {i}: [{source}]")
            sections.append(f"Title: {article['title']}")
            sections.append(f"Data Quality: {quality.upper()}")
            
            summary = article.get("summary", "")
            if summary and len(summary) > 30:
                sections.append(f"Content: {summary[:700]}")
            else:
                sections.append("Content: [Headline only - no details available]")
            
            sections.append("")
    else:
        sections.append(f"⚠️  NO RELEVANT NEWS found in last {days_back} days.")
        sections.append("")
    
    sections.append("=" * 70)
    sections.append("END TEAM NEWS SECTION")
    sections.append("=" * 70)
    
    return "\n".join(sections)


def get_all_teams_news_summary() -> List[Dict]:
    """Get news for all teams (for Streamlit UI)."""
    preseason = is_preseason()
    days_back = 21 if preseason else 7
    
    all_zh = get_zerohanger_news(days_back=days_back)
    all_news = []
    
    for team in TEAM_URLS.keys():
        rss_articles = [
            {**a, "team": team}
            for a in all_zh
            if article_mentions_team(a["title"], a["summary"], team)
        ]
        club_articles = get_club_rss_news(team, days_back=days_back)
        
        seen, merged = set(), []
        for a in rss_articles + club_articles:
            key = a["title"].lower().strip()
            if key not in seen:
                seen.add(key)
                merged.append(a)
        
        all_news.extend(merged)
    
    return all_news


def get_afl_wide_selection_news(days_back: Optional[int] = None) -> List[Dict]:
    """Get general AFL news."""
    return get_zerohanger_news(days_back=days_back)
