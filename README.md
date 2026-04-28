# CCAF Intelligence Dashboard

> Live Claude & Anthropic updates + CCA-F exam intelligence — last 7 days, served as a local web app.

## Quick Start

1. Install [Python 3.8+](https://python.org/downloads) if not already installed
2. Double-click **`START_DASHBOARD.bat`**
3. Dashboard opens automatically at [http://localhost:7474](http://localhost:7474)

No manual pip installs. No config. Just run the BAT file.

## Features

- **6 Themes** — Midnight, Dawn, Forest, Ember, Arctic, Grape (persisted via localStorage)
- **3 Density modes** — Compact / Normal / Spacious cards
- **Tab 1: Claude & Anthropic** — Official, Community, News columns (last 7 days)
- **Tab 2: Exam Intelligence** — Exam-specific updates + full study plan + resource links
- **Auto-refresh** every 90 seconds while the window is open
- **Manual refresh** via the ↺ Refresh button
- All headlines link directly to original sources

## Files

```
ccaf-dashboard/
├── START_DASHBOARD.bat   ← Double-click every morning
├── server.py             ← Python backend (fetches news, serves UI)
├── index.html            ← Dashboard UI with themes
├── cache.json            ← Auto-created on first run
└── README.md
```

## Sources Monitored

**General (Claude & Anthropic tab):**
- Anthropic News RSS
- Hacker News (Claude/Anthropic keyword filter)
- Reddit r/ClaudeAI
- Reddit r/artificial (Claude filter)
- VentureBeat AI, TechCrunch AI, The Verge

**Exam-Specific (Exam Intelligence tab):**
- GitHub: `paullarionov/claude-certified-architect` — community study guide commits
- GitHub: `modelcontextprotocol/specification` — MCP spec changes
- Reddit r/ClaudeAI certification/exam posts
- Hacker News CCAF filter
- Anthropic Docs Changelog

## Auto-Launch on Windows Startup

Press `Win+R` → type `shell:startup` → paste a shortcut to `START_DASHBOARD.bat` there.

## Requirements

- Python 3.8+  
- Internet connection  
- Auto-installed on first run: `requests`, `feedparser`, `beautifulsoup4`

## Exam Quick Reference

| Item | Detail |
|------|--------|
| Exam | Claude Certified Architect – Foundations (CCA-F) |
| Format | 60 multiple-choice, scenario-anchored |
| Duration | 120 minutes |
| Passing Score | 720 / 1000 |
| Credential Valid | 6 months |
| Exam Fee | $99 (free for first 5,000 Partner Network employees) |
| Registration | [anthropic.skilljar.com](https://anthropic.skilljar.com) |
| Partner Network | [anthropic.com/news/claude-partner-network](https://www.anthropic.com/news/claude-partner-network) |
| Domains | D1 Agentic 27% · D2 Claude Code 20% · D3 Prompt Eng 20% · D4 MCP 18% · D5 Context 15% |

## Theme Preview

| Theme | Vibe |
|-------|------|
| Midnight | Dark navy + violet — default |
| Dawn | Warm parchment — easy on eyes |
| Forest | Deep green — calm focus |
| Ember | Dark amber — warm intensity |
| Arctic | Light blue — clean & bright |
| Grape | Deep purple — rich contrast |
