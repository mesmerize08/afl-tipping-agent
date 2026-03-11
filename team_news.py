"""
team_news.py — Multiple sources, robust fallbacks, clear AI formatting
=======================================================================
Sources (in priority order):
  1. Zero Hanger category RSS feeds (injuries/suspensions + tribunal/MRP)
  2. Zero Hanger main RSS feed
  3. Zero Hanger injury/suspension HTML page (scraped)
  4. AFL.com.au injury list (__NEXT_DATA__ JSON)
  5. AFL.com.au tribunal/MRP page (__NEXT_DATA__ JSON)
  6. Club official RSS feeds
"""

import json
import logging
import re
import requests
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

try:
    from scrapling.fetchers import Fetcher as ScraplingFetcher
    HAS_SCRAPLING = True
except ImportError:
    HAS_SCRAPLING = False

# ─── Configuration ─────────────────────────────────────────────────────────────

# Zero Hanger feeds
ZEROHANGER_RSS          = "https://www.zerohanger.com/feed"
ZEROHANGER_INJURIES_RSS = "https://www.zerohanger.com/afl/injuries-suspensions/feed/"
ZEROHANGER_TRIBUNAL_RSS = "https://www.zerohanger.com/afl/tribunal-mrp/feed/"
ZEROHANGER_INJURIES_URL = "https://www.zerohanger.com/afl/injuries-suspensions/"
ZEROHANGER_TRIBUNAL_URL = "https://www.zerohanger.com/afl/tribunal-mrp/"

# AFL.com.au official pages
AFL_INJURY_LIST_URL = "https://www.afl.com.au/matches/injury-list"
AFL_TRIBUNAL_URL    = "https://www.afl.com.au/news/tribunal-and-mrp"

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

INJURY_KEYWORDS = [
    "injury", "injured", "out", "ruled out", "unavailable", "sidelined",
    "hamstring", "knee", "ankle", "shoulder", "concussion", "calf",
    "surgery", "fractured", "torn", "strain", "managed", "rehab",
    "suspension", "suspended", "tribunal", "mro", "mrp", "charged",
    "selection", "named", "omitted", "dropped", "recalled", "returns",
    "preseason", "doubt", "fitness", "test", "cleared", "strikes",
    "late out", "late inclusion", "team sheet", "team list",
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
    "gws": "GWS Giants", "giants": "GWS Giants", "greater western sydney": "GWS Giants",
    "hawthorn": "Hawthorn", "hawks": "Hawthorn",
    "melbourne": "Melbourne", "demons": "Melbourne",
    "north": "North Melbourne", "kangaroos": "North Melbourne", "roos": "North Melbourne",
    "port": "Port Adelaide", "power": "Port Adelaide",
    "richmond": "Richmond", "tigers": "Richmond",
    "st kilda": "St Kilda", "saints": "St Kilda",
    "sydney": "Sydney", "swans": "Sydney",
    "west coast": "West Coast", "eagles": "West Coast",
    "bulldogs": "Western Bulldogs", "dogs": "Western Bulldogs",
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.9",
}


# ─── Utility Functions ─────────────────────────────────────────────────────────

def is_preseason() -> bool:
    """True from November through the week before Round 1 (mid-March)."""
    now = datetime.now()
    month, day = now.month, now.day
    # Regular season opens mid-March; treat everything before Round 1 as preseason
    return month >= 11 or month <= 2 or (month == 3 and day <= 14)


def is_relevant_article(title: str, summary: str) -> bool:
    text = (title + " " + summary).lower()
    return any(kw in text for kw in INJURY_KEYWORDS)


# Names that are suffixes of a longer team name and need disambiguation.
# key: the short name (lowercased), value: the prefix that makes it a different team.
# e.g. "port " + "adelaide" = Port Adelaide, NOT the Adelaide Crows.
_SUFFIX_CONFLICTS: Dict[str, str] = {
    "adelaide": "port ",   # "port adelaide" ≠ Adelaide Crows
    "melbourne": "north ",  # "north melbourne" ≠ Melbourne Demons
}


def _name_in_text(name: str, text: str) -> bool:
    """
    Return True if `name` appears in `text` as a standalone team reference.
    Applies a negative lookbehind for names that are suffixes of other team
    names (e.g. 'adelaide' won't match inside 'port adelaide').
    """
    prefix = _SUFFIX_CONFLICTS.get(name)
    if prefix:
        # Fixed-length negative lookbehind — supported by Python's re module
        pattern = r"(?<!" + re.escape(prefix) + r")" + re.escape(name)
        return bool(re.search(pattern, text))
    return name in text


def article_mentions_team(title: str, summary: str, team_name: str) -> bool:
    text = (title + " " + summary).lower()
    if _name_in_text(team_name.lower(), text):
        return True
    for alias, canonical in TEAM_ALIASES.items():
        if canonical == team_name and _name_in_text(alias, text):
            return True
    return False


_HTML_ENTITIES = [
    ("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
    ("&quot;", '"'), ("&#8217;", "'"), ("&#8220;", '"'), ("&#8221;", '"'),
    ("&#8211;", "-"), ("&#8212;", "--"),
]

# CSS selectors for Zero Hanger (WordPress) article body
_WP_BODY_SELECTORS = [
    ".entry-content",
    ".post-content",
    ".article-content",
    "[class*='entry-content']",
    "[class*='post-content']",
    "article .content",
    "main article",
]

# Elements to strip before any text extraction
_NOISE_TAGS = [
    "script", "style", "nav", "header", "footer", "aside",
    ".widget", ".sidebar", ".site-nav", ".site-header", ".site-footer",
    ".navigation", ".nav", ".menu", "#menu", ".wp-block-navigation",
    "[class*='sidebar']", "[class*='widget']", "[class*='navigation']",
    "[class*='breadcrumb']", "[class*='related']", "[class*='share']",
    "[class*='social']", "[class*='newsletter']", "[class*='subscribe']",
    "[class*='advertisement']", "[class*='ad-']",
]


def _extract_wp_article_body(html: str, max_chars: int = 800) -> str:
    """
    Extract the article body from a WordPress page, ignoring nav/sidebar.
    Returns clean text, or empty string on failure.
    """
    if not HAS_BS4:
        # Plain regex fallback — strip all tags
        text = re.sub(r"<[^>]+>", " ", html)
        for entity, char in _HTML_ENTITIES:
            text = text.replace(entity, char)
        return re.sub(r"\s+", " ", text).strip()[:max_chars]

    try:
        soup = BeautifulSoup(html, "lxml")

        # Strip all noise elements first
        for selector in _NOISE_TAGS:
            for el in soup.select(selector):
                el.decompose()
        for tag in soup.find_all(["script", "style", "nav", "header",
                                   "footer", "aside"]):
            tag.decompose()

        # Try to find the article body container
        body = None
        for selector in _WP_BODY_SELECTORS:
            body = soup.select_one(selector)
            if body:
                break

        if body is None:
            # Fallback: use <article> or <main>
            body = soup.find("article") or soup.find("main") or soup

        # Extract paragraphs from the body only
        paragraphs = []
        for p in body.find_all("p"):
            text = p.get_text(separator=" ", strip=True)
            # Skip very short or nav-like paragraphs
            if len(text) < 30:
                continue
            # Skip paragraphs that look like nav menus (many caps words)
            caps_ratio = sum(1 for w in text.split() if w.isupper()) / max(len(text.split()), 1)
            if caps_ratio > 0.4:
                continue
            paragraphs.append(text)
            if sum(len(p) for p in paragraphs) >= max_chars:
                break

        content = " ".join(paragraphs)
        for entity, char in _HTML_ENTITIES:
            content = content.replace(entity, char)
        content = re.sub(r"\s+", " ", content).strip()

        if len(content) > max_chars:
            content = content[:max_chars] + "..."
        return content

    except Exception:
        return ""


def _get_html(url: str, timeout: int = 12) -> Optional[str]:
    """
    Fetch a URL. Tries Scrapling first (better anti-bot), falls back to requests.
    Returns raw HTML string or None on failure.
    """
    if HAS_SCRAPLING:
        try:
            fetcher = ScraplingFetcher(auto_match=False)
            page = fetcher.get(url, stealthy_headers=True, timeout=timeout)
            return str(page.html) if page else None
        except Exception as exc:
            logger.debug("Scrapling fetch failed for %s: %s", url, exc)

    try:
        r = requests.get(url, headers=_HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as exc:
        logger.debug("requests fetch failed for %s: %s", url, exc)
        return None


# ─── RSS Fetching ──────────────────────────────────────────────────────────────

def _parse_rss_feed(url: str, days_back: int, source_label: str) -> List[Dict]:
    """
    Generic RSS parser. Returns articles published within days_back days
    that match INJURY_KEYWORDS. Never raises.
    """
    cutoff = datetime.now() - timedelta(days=days_back)
    articles: List[Dict] = []

    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title   = entry.get("title", "")
            summary = entry.get("summary", "") or ""
            link    = entry.get("link", "")
            pub_str = entry.get("published", "")

            try:
                published = datetime(*entry.published_parsed[:6])
                if published < cutoff:
                    continue
            except Exception:
                pass  # include if we can't parse the date

            if not is_relevant_article(title, summary):
                continue

            # match_text uses ONLY title + original RSS summary (never scraped
            # body) so team matching isn't polluted by nav/sidebar content.
            match_text = f"{title} {summary}".strip()

            # Upgrade short summaries by fetching the article body
            if len(summary) < 100 and link:
                html = _get_html(link)
                if html:
                    scraped = _extract_wp_article_body(html)
                    if len(scraped) > len(summary):
                        summary = scraped

            if not summary or len(summary) < 20:
                summary = f"[Headline only] {title}"

            articles.append({
                "team":         "General",
                "title":        title,
                "summary":      summary,
                "match_text":   match_text,
                "published":    pub_str,
                "source":       source_label,
                "url":          link,
                "data_quality": "good" if len(summary) > 100 else "limited",
            })

    except Exception as exc:
        logger.warning("%s RSS failed: %s", source_label, exc)

    return articles


# ─── Zero Hanger Sources ────────────────────────────────────────────────────────

def get_zerohanger_news(days_back: Optional[int] = None) -> List[Dict]:
    """
    Combines three Zero Hanger feeds:
      • main RSS (general AFL news)
      • injuries/suspensions RSS
      • tribunal/MRP RSS
    Deduplicates by title.
    """
    if days_back is None:
        days_back = 21 if is_preseason() else 7

    seen: set = set()
    all_articles: List[Dict] = []

    feeds = [
        (ZEROHANGER_RSS,          "Zero Hanger"),
        (ZEROHANGER_INJURIES_RSS, "Zero Hanger Injuries"),
        (ZEROHANGER_TRIBUNAL_RSS, "Zero Hanger Tribunal"),
    ]
    for feed_url, label in feeds:
        for article in _parse_rss_feed(feed_url, days_back, label):
            key = article["title"].lower().strip()
            if key not in seen:
                seen.add(key)
                all_articles.append(article)

    logger.info("Zero Hanger (all feeds): %d relevant articles", len(all_articles))
    return all_articles


def _scrape_zerohanger_html_page(url: str, source_label: str, days_back: int) -> List[Dict]:
    """
    Scrape a Zero Hanger archive/listing page (injuries or tribunal).
    Extracts article links and snippets using BeautifulSoup.
    """
    if not HAS_BS4:
        return []

    cutoff = datetime.now() - timedelta(days=days_back)
    articles: List[Dict] = []

    html = _get_html(url)
    if not html:
        return []

    try:
        soup = BeautifulSoup(html, "lxml")

        # Zero Hanger uses standard WordPress article listings
        for item in soup.select("article, .post, .entry"):
            title_tag = item.find(["h2", "h3", "h1"])
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            if not title or not is_relevant_article(title, ""):
                continue

            link_tag = title_tag.find("a") or item.find("a", href=True)
            link = link_tag["href"] if link_tag and link_tag.get("href") else ""

            # Parse date if present
            pub_str = ""
            date_tag = item.find(["time", ".entry-date", ".post-date"])
            if date_tag:
                pub_str = date_tag.get("datetime", "") or date_tag.get_text(strip=True)
                try:
                    published = datetime.fromisoformat(pub_str.split("T")[0])
                    if published < cutoff:
                        continue
                except Exception:
                    pass

            # Get excerpt from the listing page only (never fetch full article
            # here — listing-page excerpts are clean; full pages have nav junk)
            excerpt = item.find(class_=re.compile(r"excerpt|summary|entry-summary"))
            summary = excerpt.get_text(strip=True) if excerpt else ""

            if not summary:
                summary = f"[Headline only] {title}"

            # match_text uses title + listing excerpt only — never full scrape
            match_text = f"{title} {summary}".strip()

            articles.append({
                "team":         "General",
                "title":        title,
                "summary":      summary,
                "match_text":   match_text,
                "published":    pub_str,
                "source":       source_label,
                "url":          link,
                "data_quality": "good" if len(summary) > 100 else "limited",
            })

    except Exception as exc:
        logger.warning("Failed scraping %s: %s", url, exc)

    logger.info("%s HTML scrape: %d articles", source_label, len(articles))
    return articles


# ─── AFL.com.au Sources ─────────────────────────────────────────────────────────

def _extract_next_data(html: str) -> Optional[dict]:
    """Extract the __NEXT_DATA__ JSON blob from a Next.js page."""
    if not HAS_BS4:
        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        return json.loads(match.group(1)) if match else None
    soup = BeautifulSoup(html, "lxml")
    tag = soup.find("script", id="__NEXT_DATA__")
    if tag and tag.string:
        try:
            return json.loads(tag.string)
        except json.JSONDecodeError:
            return None
    return None


def get_afl_injury_list() -> List[Dict]:
    """
    Scrape the official AFL injury list from afl.com.au/matches/injury-list.
    Extracts data from the embedded __NEXT_DATA__ JSON when available.
    Falls back to HTML text extraction.
    """
    articles: List[Dict] = []

    html = _get_html(AFL_INJURY_LIST_URL, timeout=15)
    if not html:
        logger.info("AFL injury list: could not fetch page")
        return []

    # Try __NEXT_DATA__ first (Next.js SSR)
    next_data = _extract_next_data(html)
    if next_data:
        try:
            # Navigate common Next.js page prop paths
            props = (
                next_data.get("props", {})
                         .get("pageProps", {})
            )
            # Try several known key names
            injury_data = (
                props.get("injuries")
                or props.get("injuryList")
                or props.get("data", {}).get("injuries")
                or props.get("initialData", {}).get("injuries")
            )

            if injury_data and isinstance(injury_data, list):
                for entry in injury_data:
                    team  = entry.get("team", {})
                    team_name = team.get("name", "General") if isinstance(team, dict) else str(team)
                    player  = entry.get("player", {})
                    p_name  = player.get("name", "") if isinstance(player, dict) else str(player)
                    injury  = entry.get("injury", entry.get("condition", ""))
                    status  = entry.get("status", entry.get("returnDate", ""))
                    title   = f"{p_name} ({team_name}) — {injury}"
                    summary = f"Status: {status}. Injury: {injury}." if status else f"Injury: {injury}."
                    articles.append({
                        "team":         team_name,
                        "title":        title,
                        "summary":      summary,
                        "published":    "",
                        "source":       "AFL.com.au Injury List",
                        "url":          AFL_INJURY_LIST_URL,
                        "data_quality": "good",
                    })
                logger.info("AFL injury list (__NEXT_DATA__): %d entries", len(articles))
                return articles
        except Exception as exc:
            logger.debug("__NEXT_DATA__ injury parse failed: %s", exc)

    # Fallback: parse visible text from page
    if HAS_BS4:
        try:
            soup = BeautifulSoup(html, "lxml")
            for tag in soup(["script", "style", "nav", "header", "footer"]):
                tag.decompose()
            rows = soup.select("tr, .injury-row, [class*='injury'], [class*='player-row']")
            for row in rows:
                text = row.get_text(separator=" ", strip=True)
                if len(text) > 20 and any(kw in text.lower() for kw in INJURY_KEYWORDS):
                    articles.append({
                        "team":         "General",
                        "title":        text[:120],
                        "summary":      text,
                        "published":    "",
                        "source":       "AFL.com.au Injury List",
                        "url":          AFL_INJURY_LIST_URL,
                        "data_quality": "limited",
                    })
        except Exception as exc:
            logger.debug("AFL injury list HTML fallback failed: %s", exc)

    logger.info("AFL injury list (HTML fallback): %d entries", len(articles))
    return articles


def get_afl_tribunal_news(days_back: int = 7) -> List[Dict]:
    """
    Scrape AFL.com.au tribunal/MRP page. Tries __NEXT_DATA__ then HTML.
    """
    articles: List[Dict] = []
    cutoff = datetime.now() - timedelta(days=days_back)

    html = _get_html(AFL_TRIBUNAL_URL, timeout=15)
    if not html:
        logger.info("AFL tribunal: could not fetch page")
        return []

    # Try __NEXT_DATA__ first
    next_data = _extract_next_data(html)
    if next_data:
        try:
            props = next_data.get("props", {}).get("pageProps", {})
            news_list = (
                props.get("articles")
                or props.get("news")
                or props.get("data", {}).get("articles")
                or props.get("initialData", {}).get("articles")
                or []
            )
            for item in news_list:
                title   = item.get("title", item.get("headline", ""))
                summary = item.get("summary", item.get("description", item.get("body", "")))
                pub_str = item.get("publishedDate", item.get("date", ""))
                link    = item.get("url", item.get("link", AFL_TRIBUNAL_URL))

                if not title:
                    continue

                try:
                    published = datetime.fromisoformat(pub_str.split("T")[0])
                    if published < cutoff:
                        continue
                except Exception:
                    pass

                if not is_relevant_article(title, summary):
                    continue

                articles.append({
                    "team":         "General",
                    "title":        title,
                    "summary":      summary or f"[Headline only] {title}",
                    "published":    pub_str,
                    "source":       "AFL.com.au Tribunal",
                    "url":          link,
                    "data_quality": "good" if len(summary) > 100 else "limited",
                })
            if articles:
                logger.info("AFL tribunal (__NEXT_DATA__): %d entries", len(articles))
                return articles
        except Exception as exc:
            logger.debug("__NEXT_DATA__ tribunal parse failed: %s", exc)

    # Fallback: scrape visible text
    if HAS_BS4:
        try:
            soup = BeautifulSoup(html, "lxml")
            for tag in soup(["script", "style", "nav", "header", "footer"]):
                tag.decompose()
            for item in soup.select("article, .news-item, [class*='article'], [class*='card']"):
                title_tag = item.find(["h1", "h2", "h3"])
                title = title_tag.get_text(strip=True) if title_tag else ""
                if not title or not is_relevant_article(title, ""):
                    continue
                link_tag = title_tag.find("a") if title_tag else None
                link = link_tag.get("href", AFL_TRIBUNAL_URL) if link_tag else AFL_TRIBUNAL_URL
                excerpt = item.find(class_=re.compile(r"excerpt|summary|description"))
                summary = excerpt.get_text(strip=True) if excerpt else ""
                articles.append({
                    "team":         "General",
                    "title":        title,
                    "summary":      summary or f"[Headline only] {title}",
                    "published":    "",
                    "source":       "AFL.com.au Tribunal",
                    "url":          link,
                    "data_quality": "limited",
                })
        except Exception as exc:
            logger.debug("AFL tribunal HTML fallback failed: %s", exc)

    logger.info("AFL tribunal (HTML fallback): %d entries", len(articles))
    return articles


# ─── Club RSS ──────────────────────────────────────────────────────────────────

def get_club_rss_news(team_name: str, days_back: Optional[int] = None) -> List[Dict]:
    """Get official club RSS."""
    url = TEAM_URLS.get(team_name)
    if not url:
        return []

    if days_back is None:
        days_back = 30 if is_preseason() else 7

    articles = []
    try:
        feed = feedparser.parse(url)
        cutoff = datetime.now() - timedelta(days=days_back)

        for entry in feed.entries:
            title   = entry.get("title", "")
            summary = entry.get("summary", "") or ""
            pub_str = entry.get("published", "")

            try:
                published = datetime(*entry.published_parsed[:6])
                if published < cutoff:
                    continue
            except Exception:
                pass

            if is_relevant_article(title, summary):
                articles.append({
                    "team":         team_name,
                    "title":        title,
                    "summary":      summary if summary else title,
                    "published":    pub_str,
                    "source":       f"{team_name} Official",
                    "url":          entry.get("link", ""),
                    "data_quality": "good" if len(summary) > 100 else "limited",
                })
    except Exception:
        pass

    return articles


# ─── Team / All-teams API ──────────────────────────────────────────────────────

def _all_news_sources(days_back: int) -> List[Dict]:
    """
    Collect articles from all sources in one pass and deduplicate.
    Used by both get_team_news() and get_all_teams_news_summary().
    """
    seen: set = set()
    all_articles: List[Dict] = []

    # 1. Zero Hanger RSS (main + injury + tribunal category feeds)
    for article in get_zerohanger_news(days_back=days_back):
        key = article["title"].lower().strip()
        if key not in seen:
            seen.add(key)
            all_articles.append(article)

    # 2. Zero Hanger injuries/suspensions HTML page
    for article in _scrape_zerohanger_html_page(
        ZEROHANGER_INJURIES_URL, "Zero Hanger Injuries", days_back
    ):
        key = article["title"].lower().strip()
        if key not in seen:
            seen.add(key)
            all_articles.append(article)

    # 3. Zero Hanger tribunal HTML page
    for article in _scrape_zerohanger_html_page(
        ZEROHANGER_TRIBUNAL_URL, "Zero Hanger Tribunal", days_back
    ):
        key = article["title"].lower().strip()
        if key not in seen:
            seen.add(key)
            all_articles.append(article)

    # 4. AFL.com.au injury list
    for article in get_afl_injury_list():
        key = article["title"].lower().strip()
        if key not in seen:
            seen.add(key)
            all_articles.append(article)

    # 5. AFL.com.au tribunal/MRP
    for article in get_afl_tribunal_news(days_back=days_back):
        key = article["title"].lower().strip()
        if key not in seen:
            seen.add(key)
            all_articles.append(article)

    return all_articles


def get_team_news(team_name: str, days_back: Optional[int] = None) -> List[Dict]:
    """Get all relevant news for a single team from all sources."""
    if days_back is None:
        days_back = 21 if is_preseason() else 7

    all_articles = _all_news_sources(days_back)

    # Filter to articles that mention this team
    team_articles = [
        {**a, "team": team_name}
        for a in all_articles
        if article_mentions_team(a["title"], a.get("match_text", a["title"]), team_name)
           or a.get("team") == team_name
    ]

    # Add club official RSS
    seen_titles = {a["title"].lower().strip() for a in team_articles}
    for a in get_club_rss_news(team_name, days_back=days_back):
        key = a["title"].lower().strip()
        if key not in seen_titles:
            seen_titles.add(key)
            team_articles.append({**a, "team": team_name})

    return team_articles


def get_all_teams_news_summary() -> List[Dict]:
    """Get news for all teams (for Streamlit Team News tab)."""
    days_back = 21 if is_preseason() else 7
    all_articles = _all_news_sources(days_back)
    result: List[Dict] = []

    for team in TEAM_URLS.keys():
        seen_titles: set = set()
        team_articles: List[Dict] = []

        # Match general articles to this team
        for a in all_articles:
            if article_mentions_team(a["title"], a.get("match_text", a["title"]), team) or a.get("team") == team:
                key = a["title"].lower().strip()
                if key not in seen_titles:
                    seen_titles.add(key)
                    team_articles.append({**a, "team": team})

        # Club RSS
        for a in get_club_rss_news(team, days_back=days_back):
            key = a["title"].lower().strip()
            if key not in seen_titles:
                seen_titles.add(key)
                team_articles.append({**a, "team": team})

        result.extend(team_articles)

    return result


# ─── AI Prompt Formatting ──────────────────────────────────────────────────────

def format_team_news_for_ai(home_team: str, away_team: str) -> str:
    """Format team news for the AI prediction prompt."""
    preseason = is_preseason()
    logger.info("Fetching team news: %s vs %s", home_team, away_team)

    days_back = 21 if preseason else 7

    home_news = get_team_news(home_team, days_back=days_back)
    away_news = get_team_news(away_team, days_back=days_back)

    sections = []
    sections.append("=" * 70)
    sections.append("TEAM NEWS, INJURIES & TRIBUNAL")
    sections.append("=" * 70)
    if preseason:
        sections.append("NOTE: Pre-season mode — news covers 21 days.")
    sections.append("")

    home_good = sum(1 for a in home_news if a.get("data_quality") == "good")
    away_good = sum(1 for a in away_news if a.get("data_quality") == "good")

    if home_good == 0 and away_good == 0 and not home_news and not away_news:
        sections.append(
            "WARNING: No team news found. "
            "Weight form, odds, and venue data more heavily."
        )
        sections.append("")

    for team, news, good_count in [
        (home_team, home_news, home_good),
        (away_team, away_news, away_good),
    ]:
        sections.append("─" * 70)
        sections.append(f"{team.upper()} — INJURIES, SUSPENSIONS & SELECTION NEWS")
        sections.append("─" * 70)

        if news:
            sections.append(
                f"{len(news)} relevant articles "
                f"({good_count} with detailed content)"
            )
            sections.append("")
            for i, article in enumerate(news[:6], 1):
                source  = article.get("source", "Unknown")
                quality = article.get("data_quality", "unknown").upper()
                summary = article.get("summary", "")
                sections.append(f"[{source}] {article['title']}")
                if summary and len(summary) > 30:
                    sections.append(f"  {summary[:700]}")
                else:
                    sections.append("  [Headline only — no detail available]")
                sections.append("")
        else:
            sections.append(f"No relevant news in the last {days_back} days.")
            sections.append("")

    sections.append("=" * 70)
    sections.append("END TEAM NEWS")
    sections.append("=" * 70)

    return "\n".join(sections)


def get_afl_wide_selection_news(days_back: Optional[int] = None) -> List[Dict]:
    """Get general AFL-wide selection/injury news (convenience wrapper)."""
    return get_zerohanger_news(days_back=days_back)
