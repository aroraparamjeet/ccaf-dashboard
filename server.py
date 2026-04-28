"""
CCAF Intelligence Dashboard - Backend Server
Fetches live updates from multiple sources and serves an HTML dashboard.
Run via START_DASHBOARD.bat - do not run directly.
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
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
SEVEN_DAYS_AGO = datetime.now(timezone.utc) - timedelta(days=7)

# ── SOURCES ───────────────────────────────────────────────────────────────────
GENERAL_SOURCES = [
    {"name": "Anthropic News", "type": "rss", "url": "https://www.anthropic.com/rss.xml", "icon": "🏛️", "category": "official"},
    {"name": "Hacker News – Claude/Anthropic", "type": "rss", "url": "https://hnrss.org/newest?q=anthropic+OR+claude+AI&count=20", "icon": "🟧", "category": "community", "keywords": ["anthropic", "claude", "claude ai", "claude code", "mcp"]},
    {"name": "Reddit r/ClaudeAI", "type": "rss", "url": "https://www.reddit.com/r/ClaudeAI/.rss", "icon": "👾", "category": "community"},
    {"name": "Reddit r/artificial", "type": "rss", "url": "https://www.reddit.com/r/artificial/.rss", "icon": "🤖", "category": "community", "keywords": ["anthropic", "claude", "claude ai"]},
    {"name": "VentureBeat AI", "type": "rss", "url": "https://venturebeat.com/category/ai/feed/", "icon": "📰", "category": "news", "keywords": ["anthropic", "claude", "claude ai", "claude code"]},
    {"name": "TechCrunch AI", "type": "rss", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "icon": "🚀", "category": "news", "keywords": ["anthropic", "claude"]},
    {"name": "The Verge AI", "type": "rss", "url": "https://www.theverge.com/rss/index.xml", "icon": "▲", "category": "news", "keywords": ["anthropic", "claude"]},
    {"name": "GitHub – CCAF Community Guide", "type": "github_commits", "url": "https://api.github.com/repos/paullarionov/claude-certified-architect/commits", "icon": "🐙", "category": "exam"},
]

EXAM_SOURCES = [
    {"name": "Reddit r/ClaudeAI – Exam Posts", "type": "rss", "url": "https://www.reddit.com/r/ClaudeAI/search/.rss?q=certification+OR+exam+OR+ccaf+OR+architect&sort=new", "icon": "👾", "category": "exam", "keywords": ["certif", "exam", "ccaf", "architect", "claude certified"]},
    {"name": "Hacker News – CCAF", "type": "rss", "url": "https://hnrss.org/newest?q=claude+certification+OR+ccaf+OR+claude+architect&count=15", "icon": "🟧", "category": "exam", "keywords": ["certif", "exam", "ccaf", "architect"]},
    {"name": "GitHub – MCP Specification", "type": "github_commits", "url": "https://api.github.com/repos/modelcontextprotocol/specification/commits", "icon": "🔌", "category": "exam"},
    {"name": "Anthropic Docs Changelog", "type": "web_scrape", "url": "https://docs.anthropic.com/en/release-notes/overview", "icon": "📋", "category": "exam", "keywords": ["claude code", "mcp", "api", "agent", "tool", "release"]},
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

def within_7_days(s):
    dt = parse_date(s)
    if dt is None: return True
    dt = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    return dt >= SEVEN_DAYS_AGO

def fmt_date(s):
    dt = parse_date(s)
    return dt.strftime("%b %d, %Y") if dt else "Recent"

def kw_match(text, kws):
    if not kws: return True
    return any(k.lower() in text.lower() for k in kws)

# ── FETCHERS ──────────────────────────────────────────────────────────────────
def fetch_rss(src):
    items = []
    try:
        feed = feedparser.parse(src["url"])
        kws = src.get("keywords", [])
        for e in feed.entries[:30]:
            title = getattr(e, "title", "No title")
            summary = getattr(e, "summary", "")
            link = getattr(e, "link", "#")
            pub = getattr(e, "published", None) or getattr(e, "updated", None)
            if not within_7_days(pub): continue
            if kws and not kw_match(title + " " + summary, kws): continue
            try: clean = BeautifulSoup(summary, "html.parser").get_text(" ", strip=True)[:280]
            except: clean = summary[:280]
            items.append({"title": title[:160], "summary": clean, "url": link, "date": fmt_date(pub),
                          "source": src["name"], "icon": src["icon"], "category": src.get("category", "general")})
    except Exception as ex:
        print(f"  RSS error [{src['name']}]: {ex}")
    return items

def fetch_github_commits(src):
    items = []
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
            if not within_7_days(date): continue
            items.append({"title": msg[:140], "summary": f"Commit {sha} by {author}", "url": url,
                          "date": fmt_date(date), "source": src["name"], "icon": src["icon"],
                          "category": src.get("category", "general")})
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
            items.append({"title": title[:160], "summary": text[:280], "url": link, "date": "Recent",
                          "source": src["name"], "icon": src["icon"], "category": src.get("category", "general")})
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
    seen = set()
    def dedup(items):
        out = []
        for i in items:
            if i["url"] not in seen:
                seen.add(i["url"]); out.append(i)
        return out
    general = dedup(general); exam = dedup(exam)
    data = {"fetched_at": datetime.now().strftime("%B %d, %Y at %I:%M %p"),
            "general": general[:60], "exam": exam[:40],
            "exam_plan": EXAM_PLAN, "exam_resources": EXAM_RESOURCES,
            "total_general": len(general), "total_exam": len(exam)}
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
            data = load_cache() or {"general": [], "exam": [], "exam_plan": EXAM_PLAN,
                                    "exam_resources": EXAM_RESOURCES, "fetched_at": "Loading...",
                                    "total_general": 0, "total_exam": 0}
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
    threading.Thread(target=lambda: socketserver.TCPServer(("", PORT), Handler).serve_forever(), daemon=True).start()
    print(f"\nDashboard at http://localhost:{PORT} — opening browser...")
    time.sleep(1.5); webbrowser.open(f"http://localhost:{PORT}")
    print("Press Ctrl+C to stop.\n")
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: print("\nServer stopped.")
