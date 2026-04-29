"""
CCAF Intelligence Dashboard - Backend Server
Fetches live updates from multiple sources and serves an HTML dashboard.
Run via START_DASHBOARD.bat - do not run directly.

Bugs fixed vs v1:
- Added r/Anthropic (was completely missing — exam pass posts live there)
- Added r/LocalLLaMA (active Claude/cert discussions)
- Exam posts now show in Community column (priority-sorted to top)
- Expanded exam Reddit searches to cover r/Anthropic + r/LocalLLaMA
- Increased RSS fetch limit 30->50 to catch more posts within window
- Exam sources use 14-day window so cert posts aren't missed
"""

import json, threading, time, http.server, socketserver, os, sys, webbrowser
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import requests, feedparser
    from bs4 import BeautifulSoup
except ImportError:
    print("Installing required packages...")
    os.system(f"{sys.executable} -m pip install requests feedparser beautifulsoup4 -q")
    import requests, feedparser
    from bs4 import BeautifulSoup

PORT = 7474
BASE_DIR = Path(__file__).parent
CACHE_FILE = BASE_DIR / "cache.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
SEVEN_DAYS_AGO  = datetime.now(timezone.utc) - timedelta(days=7)
FOURTEEN_DAYS_AGO = datetime.now(timezone.utc) - timedelta(days=14)

# Exam-related keywords used for filtering and prioritisation
EXAM_KEYWORDS = [
    "certif", "ccaf", "claude certified", "architect exam", "passed", "i passed",
    "exam tips", "study guide", "exam prep", "cca-f", "skilljar", "partner network",
    "exam experience", "exam review", "certification exam"
]

# ── SOURCES ───────────────────────────────────────────────────────────────────
# BUG FIX 1: Added r/Anthropic (was completely missing)
# BUG FIX 2: Added r/LocalLLaMA (active forum for Claude/cert discussions)
# BUG FIX 3: exam-related posts from community sources now use category="community_exam"
#            so they appear in Community column AND get priority sorting

GENERAL_SOURCES = [
    # ── OFFICIAL ──────────────────────────────────────────────────────────────
    {
        "name": "Anthropic News",
        "type": "rss",
        "url": "https://www.anthropic.com/rss.xml",
        "icon": "🏛️",
        "category": "official",
    },

    # ── COMMUNITY — Reddit ────────────────────────────────────────────────────
    {
        "name": "Reddit r/Anthropic",          # FIX: was completely missing
        "type": "rss",
        "url": "https://www.reddit.com/r/Anthropic/.rss",
        "icon": "👾",
        "category": "community",              # shows in Community column
        "exam_boost": True,                   # exam posts sorted to top
    },
    {
        "name": "Reddit r/ClaudeAI",
        "type": "rss",
        "url": "https://www.reddit.com/r/ClaudeAI/.rss",
        "icon": "👾",
        "category": "community",
        "exam_boost": True,
    },
    {
        "name": "Reddit r/LocalLLaMA",         # FIX: new — active Claude/cert discussions
        "type": "rss",
        "url": "https://www.reddit.com/r/LocalLLaMA/.rss",
        "icon": "🦙",
        "category": "community",
        "keywords": ["anthropic", "claude", "certif", "ccaf", "mcp", "claude code"],
        "exam_boost": True,
    },
    {
        "name": "Reddit r/artificial",
        "type": "rss",
        "url": "https://www.reddit.com/r/artificial/.rss",
        "icon": "🤖",
        "category": "community",
        "keywords": ["anthropic", "claude", "claude ai"],
    },

    # ── COMMUNITY — Forums ────────────────────────────────────────────────────
    {
        "name": "Hacker News – Claude/Anthropic",
        "type": "rss",
        "url": "https://hnrss.org/newest?q=anthropic+OR+claude+AI&count=25",
        "icon": "🟧",
        "category": "community",
        "keywords": ["anthropic", "claude", "claude ai", "claude code", "mcp"],
        "exam_boost": True,
    },

    # ── NEWS ──────────────────────────────────────────────────────────────────
    {
        "name": "VentureBeat AI",
        "type": "rss",
        "url": "https://venturebeat.com/category/ai/feed/",
        "icon": "📰",
        "category": "news",
        "keywords": ["anthropic", "claude", "claude ai", "claude code"],
    },
    {
        "name": "TechCrunch AI",
        "type": "rss",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "icon": "🚀",
        "category": "news",
        "keywords": ["anthropic", "claude"],
    },
    {
        "name": "The Verge AI",
        "type": "rss",
        "url": "https://www.theverge.com/rss/index.xml",
        "icon": "▲",
        "category": "news",
        "keywords": ["anthropic", "claude"],
    },

    # ── EXAM (also shown in community via exam_boost) ─────────────────────────
    {
        "name": "GitHub – CCAF Community Guide",
        "type": "github_commits",
        "url": "https://api.github.com/repos/paullarionov/claude-certified-architect/commits",
        "icon": "🐙",
        "category": "community_exam",         # shows in Community column, top priority
    },
]

# FIX: Expanded exam sources to cover r/Anthropic and r/LocalLLaMA
EXAM_SOURCES = [
    {
        "name": "Reddit r/Anthropic – Exam Posts",    # FIX: was missing entirely
        "type": "rss",
        "url": "https://www.reddit.com/r/Anthropic/search/.rss?q=certification+OR+exam+OR+ccaf+OR+architect+OR+passed&sort=new",
        "icon": "👾",
        "category": "exam",
        "keywords": ["certif", "exam", "ccaf", "architect", "claude certified", "passed", "study"],
        "window_days": 14,                    # FIX: 14-day window for exam posts
    },
    {
        "name": "Reddit r/ClaudeAI – Exam Posts",
        "type": "rss",
        "url": "https://www.reddit.com/r/ClaudeAI/search/.rss?q=certification+OR+exam+OR+ccaf+OR+architect+OR+passed&sort=new",
        "icon": "👾",
        "category": "exam",
        "keywords": ["certif", "exam", "ccaf", "architect", "claude certified", "passed"],
        "window_days": 14,
    },
    {
        "name": "Reddit r/LocalLLaMA – Exam Posts",   # FIX: new source
        "type": "rss",
        "url": "https://www.reddit.com/r/LocalLLaMA/search/.rss?q=claude+certified+OR+ccaf+OR+claude+architect&sort=new",
        "icon": "🦙",
        "category": "exam",
        "keywords": ["certif", "ccaf", "architect", "claude certified"],
        "window_days": 14,
    },
    {
        "name": "Hacker News – CCAF",
        "type": "rss",
        "url": "https://hnrss.org/newest?q=claude+certification+OR+ccaf+OR+claude+architect&count=15",
        "icon": "🟧",
        "category": "exam",
        "keywords": ["certif", "exam", "ccaf", "architect"],
        "window_days": 14,
    },
    {
        "name": "GitHub – MCP Specification",
        "type": "github_commits",
        "url": "https://api.github.com/repos/modelcontextprotocol/specification/commits",
        "icon": "🔌",
        "category": "exam",
    },
    {
        "name": "Anthropic Docs Changelog",
        "type": "web_scrape",
        "url": "https://docs.anthropic.com/en/release-notes/overview",
        "icon": "📋",
        "category": "exam",
        "keywords": ["claude code", "mcp", "api", "agent", "tool", "release"],
    },
]

EXAM_PLAN = [
    {"week": "Week 1", "title": "Access + Foundation Blast", "color": "#1D9E75", "tasks": [
        "Join Claude Partner Network (mandatory gate) → anthropic.com/news/claude-partner-network",
        "Submit exam access request → anthropic.skilljar.com",
        "Read Official CCA-F Exam Guide PDF end-to-end (twice)",
        "Complete 'Claude 101' + 'AI Fluency' on Anthropic Academy",
    ]},
    {"week": "Week 2", "title": "Agentic Architecture (D1 · 27%)", "color": "#7F77DD", "tasks": [
        "Complete 'Building with the Claude API' on Skilljar (8.1 hrs)",
        "Build: Coordinator-subagent research system (hub-and-spoke pattern)",
        "Master: agentic loop lifecycle, stop_reason values, session state",
        "Study: Programmatic enforcement vs. prompt-based guidance (#1 tested)",
    ]},
    {"week": "Week 3", "title": "Claude Code + MCP (D2+D4 · 38%)", "color": "#D85A30", "tasks": [
        "Complete 'Claude Code' on Anthropic Academy + Coursera (Vanderbilt)",
        "Complete 'Introduction to MCP': Tools, Resources, Prompts primitives",
        "Build: MCP server with 3+ tools and structured error handling",
        "Study: CLAUDE.md hierarchy, -p flag for CI, hooks, Agent Skills",
    ]},
    {"week": "Week 4", "title": "Prompt Eng + Reliability (D3+D5 · 35%)", "color": "#EF9F27", "tasks": [
        "Study: few-shot prompting, JSON schema enforcement, Pydantic validation",
        "Study: self-evaluation retry loops with error feedback to model",
        "Study: context window budgeting, pruning strategies, HITL checkpoints",
        "Memorize the 7 architectural anti-patterns (wrong exam answers are these)",
    ]},
    {"week": "Week 5-6", "title": "Full Exam Simulation", "color": "#378ADD", "tasks": [
        "Complete official 60-Q practice test on Skilljar — study ALL wrong answers",
        "Work through all 12 sample questions in the Official Exam Guide",
        "Udemy: 360 scenario-based practice questions (Balaji Ashok Kumar)",
        "Target 780+ on practice before booking. Sit exam when scoring 780+ consistently",
    ]},
]

EXAM_RESOURCES = [
    {"name": "Anthropic Academy (All 13 Free Courses)", "url": "https://anthropic.skilljar.com", "cost": "FREE", "priority": "MUST DO", "color": "#1D9E75"},
    {"name": "Exam Registration (Partner Network Required)", "url": "https://anthropic.skilljar.com/claude-certified-architect-foundations-access-request", "cost": "FREE / $99", "priority": "GATE STEP", "color": "#D85A30"},
    {"name": "Claude Partner Network (Join First)", "url": "https://www.anthropic.com/news/claude-partner-network", "cost": "FREE", "priority": "GATE STEP", "color": "#D85A30"},
    {"name": "Official CCA-F Exam Guide PDF", "url": "https://anthropic.skilljar.com", "cost": "FREE", "priority": "READ TWICE", "color": "#7F77DD"},
    {"name": "Building with the Claude API (8.1 hrs)", "url": "https://anthropic.skilljar.com", "cost": "FREE", "priority": "MUST DO", "color": "#1D9E75"},
    {"name": "Claude Code on Coursera (Vanderbilt)", "url": "https://www.coursera.org/learn/claude-code", "cost": "FREE audit", "priority": "MUST DO", "color": "#1D9E75"},
    {"name": "Introduction to MCP", "url": "https://anthropic.skilljar.com", "cost": "FREE", "priority": "MUST DO", "color": "#1D9E75"},
    {"name": "GitHub Community Study Guide", "url": "https://github.com/paullarionov/claude-certified-architect", "cost": "FREE", "priority": "HIGH VALUE", "color": "#378ADD"},
    {"name": "Claude API Documentation", "url": "https://docs.anthropic.com", "cost": "FREE", "priority": "REFERENCE", "color": "#666"},
    {"name": "Udemy Practice Exams (360 Questions)", "url": "https://www.udemy.com/course/new-claude-certified-architect-foundations-cca-f-exams/", "cost": "~$20", "priority": "OPTIONAL", "color": "#EF9F27"},
    {"name": "claudecertifications.com (Community)", "url": "https://claudecertifications.com", "cost": "FREE", "priority": "COMMUNITY", "color": "#888"},
    {"name": "flashgenius.net CCAF Guide", "url": "https://flashgenius.net/blog-article/a-guide-to-the-claude-certified-architect-foundations-certification", "cost": "FREE", "priority": "COMMUNITY", "color": "#888"},
]

# ── DATE HELPERS ──────────────────────────────────────────────────────────────
def parse_date(s):
    if not s: return None
    import email.utils
    try:
        t = email.utils.parsedate_to_datetime(s)
        return t.replace(tzinfo=timezone.utc) if t.tzinfo is None else t
    except Exception: pass
    for fmt in ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"]:
        try: return datetime.strptime(s[:19], fmt[:len(s)]).replace(tzinfo=timezone.utc)
        except Exception: pass
    return None

def within_window(s, days=7):
    dt = parse_date(s)
    if dt is None: return True
    dt = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return dt >= cutoff

def fmt_date(s):
    dt = parse_date(s)
    return dt.strftime("%b %d, %Y") if dt else "Recent"

def kw_match(text, kws):
    if not kws: return True
    return any(k.lower() in text.lower() for k in kws)

def is_exam_related(title, summary=""):
    """Check if a post is exam/certification related for priority boosting."""
    text = (title + " " + summary).lower()
    return any(k in text for k in EXAM_KEYWORDS)

# ── FETCHERS ──────────────────────────────────────────────────────────────────
def fetch_rss(src):
    items = []
    window_days = src.get("window_days", 7)
    try:
        feed = feedparser.parse(src["url"])
        kws = src.get("keywords", [])
        for e in feed.entries[:50]:           # FIX: increased from 30 to 50
            title = getattr(e, "title", "No title")
            summary = getattr(e, "summary", "")
            link = getattr(e, "link", "#")
            pub = getattr(e, "published", None) or getattr(e, "updated", None)
            if not within_window(pub, window_days): continue
            if kws and not kw_match(title + " " + summary, kws): continue
            try: clean = BeautifulSoup(summary, "html.parser").get_text(" ", strip=True)[:300]
            except: clean = summary[:300]

            # FIX: Mark exam-related posts for priority sorting in Community column
            exam_related = src.get("exam_boost", False) and is_exam_related(title, clean)
            cat = "community_exam" if exam_related else src.get("category", "general")

            items.append({
                "title": title[:160], "summary": clean, "url": link,
                "date": fmt_date(pub), "source": src["name"],
                "icon": src["icon"], "category": cat,
                "exam_related": exam_related,
            })
    except Exception as ex:
        print(f"  RSS error [{src['name']}]: {ex}")
    return items

def fetch_github_commits(src):
    items = []
    window_days = src.get("window_days", 7)
    try:
        r = requests.get(src["url"], headers=HEADERS, timeout=12)
        if r.status_code != 200: return items
        commits = r.json()
        if not isinstance(commits, list): return items
        for c in commits[:10]:
            msg = c.get("commit", {}).get("message", "").split("\n")[0]
            sha = c.get("sha", "")[:7]
            url = c.get("html_url", "#")
            date = c.get("commit", {}).get("author", {}).get("date", "")
            author = c.get("commit", {}).get("author", {}).get("name", "")
            if not within_window(date, window_days): continue
            items.append({
                "title": msg[:140], "summary": f"Commit {sha} by {author}", "url": url,
                "date": fmt_date(date), "source": src["name"], "icon": src["icon"],
                "category": src.get("category", "general"), "exam_related": True,
            })
    except Exception as ex:
        print(f"  GitHub error [{src['name']}]: {ex}")
    return items

def fetch_web_scrape(src):
    items = []
    try:
        r = requests.get(src["url"], headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        kws = src.get("keywords", [])
        for el in soup.find_all(["article", "section", "li", "div"], limit=40):
            text = el.get_text(" ", strip=True)
            if len(text) < 40 or len(text) > 800: continue
            if kws and not kw_match(text, kws): continue
            link_tag = el.find("a", href=True)
            link = link_tag["href"] if link_tag else src["url"]
            if link.startswith("/"):
                from urllib.parse import urlparse
                p = urlparse(src["url"])
                link = f"{p.scheme}://{p.netloc}{link}"
            title = link_tag.get_text(strip=True) if link_tag else text[:80]
            items.append({
                "title": title[:160], "summary": text[:280], "url": link, "date": "Recent",
                "source": src["name"], "icon": src["icon"],
                "category": src.get("category", "general"), "exam_related": False,
            })
            if len(items) >= 5: break
    except Exception as ex:
        print(f"  Scrape error [{src['name']}]: {ex}")
    return items

def fetch_source(src):
    t = src["type"]
    if t == "rss": return fetch_rss(src)
    elif t == "github_commits": return fetch_github_commits(src)
    elif t == "web_scrape": return fetch_web_scrape(src)
    return []

# ── MAIN FETCH ────────────────────────────────────────────────────────────────
def fetch_all():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Fetching latest updates...")
    general, exam = [], []

    for src in GENERAL_SOURCES:
        print(f"  -> {src['name']}")
        general.extend(fetch_source(src))

    for src in EXAM_SOURCES:
        print(f"  -> {src['name']}")
        exam.extend(fetch_source(src))

    # Deduplicate by URL (global seen set prevents cross-list duplication)
    seen = set()
    def dedup(items):
        out = []
        for i in items:
            if i["url"] not in seen:
                seen.add(i["url"]); out.append(i)
        return out

    general = dedup(general)
    exam = dedup(exam)

    # FIX: Sort Community column — exam-related posts bubble to top
    # Within each group, preserve chronological order
    def community_sort_key(item):
        cat = item.get("category", "")
        exam_rel = item.get("exam_related", False)
        if cat == "community_exam": return 0          # GitHub CCAF guide commits — top
        if exam_rel: return 1                          # exam-related Reddit/HN posts — next
        if cat == "community": return 2                # regular community posts
        return 3
    general.sort(key=community_sort_key)

    data = {
        "fetched_at": datetime.now().strftime("%B %d, %Y at %I:%M %p"),
        "general": general[:80],
        "exam": exam[:50],
        "exam_plan": EXAM_PLAN,
        "exam_resources": EXAM_RESOURCES,
        "total_general": len(general),
        "total_exam": len(exam),
    }
    with open(CACHE_FILE, "w") as f: json.dump(data, f)
    print(f"  Done: {len(general)} general, {len(exam)} exam updates")
    return data

def load_cache():
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f: return json.load(f)
    return None

# ── HTTP SERVER ───────────────────────────────────────────────────────────────
class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw): super().__init__(*a, directory=str(BASE_DIR), **kw)
    def do_GET(self):
        if self.path == "/api/data":
            data = load_cache() or {
                "general": [], "exam": [], "exam_plan": EXAM_PLAN,
                "exam_resources": EXAM_RESOURCES, "fetched_at": "Loading...",
                "total_general": 0, "total_exam": 0,
            }
            body = json.dumps(data).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers(); self.wfile.write(body)
        elif self.path == "/api/refresh":
            threading.Thread(target=fetch_all, daemon=True).start()
            body = b'{"status":"refreshing"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.end_headers(); self.wfile.write(body)
        elif self.path in ("/", "/index.html"):
            self.path = "/index.html"; super().do_GET()
        else: super().do_GET()
    def log_message(self, *a): pass

if __name__ == "__main__":
    print("=" * 55)
    print("  CCAF Intelligence Dashboard")
    print("  Claude & Exam Updates - Last 7 Days")
    print("=" * 55)
    threading.Thread(target=fetch_all, daemon=True).start()
    threading.Thread(
        target=lambda: socketserver.TCPServer(("", PORT), Handler).serve_forever(),
        daemon=True
    ).start()
    print(f"\nDashboard at http://localhost:{PORT} — opening browser...")
    time.sleep(1.5); webbrowser.open(f"http://localhost:{PORT}")
    print("Press Ctrl+C to stop.\n")
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: print("\nServer stopped.")
