# AI Agent SEO: Multi-Platform Agent Instructions

> For **Cursor**, **Cursor Cloud Agents**, **Google Antigravity**, **Gemini CLI**,
> **Grok Build**,
> **OpenAI Codex CLI**, **Cline**, **Aider**, and any other agent harness that
> reads project-root agent instructions.
>
> Claude Code users: see `CLAUDE.md` instead.

## Cross-platform portability

Every skill in `skills/*/SKILL.md` is authored to the portable Agent Skills
format (single-line `name` and `description` frontmatter). Validate compatibility with your harness via:

```bash
./scripts/ai-agent-seo run portability_check.py
```

The check confirms each `SKILL.md` has the minimum frontmatter every harness
expects (`name`, `description`, optional `model`, optional `tools`) and warns
on Claude-Code-specific features (`maxTurns`, multi-line tool list with
descriptive comments) that other harnesses may ignore but do not reject.

### Install for your harness

All skills follow the open Agent Skills format (one folder per skill with a
`SKILL.md`). The installer copies them where each harness looks and replaces
the Claude-only `${CLAUDE_PLUGIN_ROOT}` token with absolute paths, so every
script command and reference link works in any shell. Run from this checkout:

```bash
bash install.sh --list                # detected harnesses and install state
bash install.sh --target agents       # shared ~/.agents/skills
bash install.sh --target all          # every detected harness, one shared runtime
```

Windows: `.\install.ps1 -Target agents`. Any harness not listed: `--dest <its skills folder>`.
Project scope (committed with a repo): `--project <repo> --target agents` writes `<repo>/.agents/skills`.

| Harness | Target | Folder | Invoke |
|---|---|---|---|
| **OpenAI Codex CLI / IDE** | `agents` | `~/.agents/skills` | `$seo audit <url>` or `/skills`; enable sandbox network access |
| **Gemini CLI** | `agents` | `~/.agents/skills` | Automatic (`activate_skill`); `gemini skills list` to verify |
| **Cursor** | `agents` | `~/.agents/skills` | `/seo audit <url>` or automatic |
| **OpenCode** (any provider/model) | `agents` | `~/.agents/skills` | Automatic via the `skill` tool |
| **GitHub Copilot** (CLI, VS Code, JetBrains) | `agents` | `~/.agents/skills` | Automatic, or name the skill (`seo`); `/skills reload` in the CLI |
| **Google Antigravity** | `antigravity` | `~/.gemini/config/skills` | Automatic |
| **Windsurf** | `windsurf` | `~/.codeium/windsurf/skills` | Automatic, or name the skill (`seo`) |
| **Claude Code** | `claude` (default with no options) | `~/.claude/skills` + `~/.claude/agents` | `/seo audit <url>` |
| **Cline, Aider, Grok Build, others** | `--dest` or project | the harness's skills folder, or read `AGENTS.md` | Plain language |

Harnesses without a subagent tool run each specialist inline: the installer
puts every agent's instructions in `seo/subagents/<name>.md`, and the skills
say to read and execute them one at a time. The runtime (scripts plus an
isolated `.venv`) is built once in the first target's `seo/` folder; other
targets in the same run point at it. Uninstall with
`./scripts/ai-agent-seo uninstall --target <name>`.

### Tool-name compatibility

Where ai-agent-seo skills mention Claude Code tools (`Read`, `Write`, `Edit`,
`Bash`, `Glob`, `Grep`, `WebFetch`), each harness typically has an equivalent:

| Claude Code | Codex | Cline | Aider | Cursor / Antigravity |
|---|---|---|---|---|
| Read       | read_file        | read_file       | (inline)        | read |
| Write      | write_file       | write_file      | /add then edit  | write |
| Edit       | apply_diff       | replace_in_file | /edit           | edit |
| Bash       | bash             | execute_command | /run            | shell |
| Glob       | glob             | search_files    | (inline)        | find |
| Grep       | grep             | search_files    | /grep           | grep |
| WebFetch   | fetch / browse   | (browser tool)  | (n/a)           | fetch |

These mappings are automatic in most harnesses; we list them for transparency
in case a recipe needs a specific call.

## Overview

AI Agent SEO is a Tier 4 SEO analysis skill with 27 sub-skills (23 core + 1 orchestrator +
1 framework integration + 2 extension mirrors), 20 sub-agents (17 core + 1 framework
integration + 2 extension mirrors), and 66 Python execution scripts.

## Quick Reference

| Command | What it does |
|---------|-------------|
| `/seo audit <url>` | Full website audit with parallel subagent delegation |
| `/seo page <url>` | Deep single-page analysis |
| `/seo technical <url>` | Technical SEO audit (9 categories) |
| `/seo content <url>` | E-E-A-T and content quality analysis |
| `/seo content-brief <topic>` | Generate a content brief for a topic |
| `/seo schema <url>` | Schema.org detection, validation, generation |
| `/seo sitemap <url>` | XML sitemap analysis or generation |
| `/seo images <url>` | Image SEO: on-page audit, SERP analysis, file optimization |
| `/seo aeo <url>` | Answer Engine Optimization: featured snippets, People Also Ask, voice |
| `/seo settings [set focus <balanced\|seo\|aeo\|geo>]` | SEO / AEO / GEO optimization focus |
| `/seo geo <url>` | AI Overviews / Generative Engine Optimization |
| `/seo plan <type>` | Strategic SEO planning |
| `/seo cluster <keyword>` | SERP-based semantic clustering and content architecture |
| `/seo sxo <url>` | Search Experience Optimization: page-type analysis, personas |
| `/seo drift baseline <url>` | Capture SEO baseline for change monitoring |
| `/seo drift compare <url>` | Compare current state to stored baseline |
| `/seo drift history <url>` | Show drift history over time |
| `/seo ecommerce <url>` | E-commerce SEO: product schema, marketplace intelligence |
| `/seo programmatic [url]` | Programmatic SEO at scale |
| `/seo competitor-pages [url]` | Competitor comparison pages |
| `/seo flow [stage]` | FLOW framework prompts (Find, Leverage, Optimize, Win, Local; prompts/sync utilities.) |
| `/seo local <url>` | Local SEO analysis (GBP, citations, reviews) |
| `/seo maps [cmd] [args]` | Maps intelligence (geo-grid, GBP audit, competitors) |
| `/seo hreflang <url>` | Hreflang/i18n SEO audit, cultural profiles, content parity |
| `/seo google [cmd] [url]` | Google SEO APIs (GSC, PageSpeed, CrUX, Indexing, GA4) |
| `/seo backlinks <url>` | Backlink profile analysis |
| `/seo backlinks setup` | Setup free backlink APIs |
| `/seo backlinks verify <url>` | Verify known backlinks still exist |
| `/seo dataforseo [cmd]` | Live SEO data via DataForSEO (extension) |
| `/seo image-gen [use-case]` | AI image generation for SEO assets (extension) |
| `/seo firecrawl [cmd] <url>` | Full-site crawling and site mapping (extension) |
| `/seo ahrefs [cmd] <target>` | Ahrefs backlink and keyword data (extension) |
| `/seo bing [cmd] <url>` | Bing Webmaster data and IndexNow (extension) |
| `/seo profound [cmd]` | LLM brand-citation tracking (extension) |
| `/seo seranking [cmd]` | AI share-of-voice tracking (extension) |
| `/seo matomo [cmd] [args]` | Matomo Reporting API: GA4 alternative or supplement (extension) |
| `/seo unlighthouse <url>` | Multi-page Lighthouse audits (extension) |

## Using with Cursor / Cursor Cloud

Cursor reads this file automatically. All SKILL.md files contain the full
analysis logic as natural language instructions. Python scripts in `scripts/`
provide execution capabilities.

**Running scripts directly** (Cursor doesn't have MCP):
```bash
# Page fetching with SSRF protection
./scripts/ai-agent-seo run fetch_page.py https://example.com

# HTML parsing for SEO elements
./scripts/ai-agent-seo run parse_html.py https://example.com

# PageSpeed Insights
./scripts/ai-agent-seo run pagespeed_check.py https://example.com --json

# Drift baseline
./scripts/ai-agent-seo run drift_baseline.py https://example.com

# DataForSEO (requires credentials)
DATAFORSEO_USERNAME=user DATAFORSEO_PASSWORD=pass ./scripts/ai-agent-seo run dataforseo_merchant.py search "keyword"
```

**Cursor Cloud gotchas:**
- SSL certificates may not resolve for some domains. Investigate the certificate issue rather than disabling verification.
- Run bundled tools through `ai-agent-seo`; never call the venv interpreter directly.
- Screenshots save to `/tmp/` not CWD. Check absolute paths.

## Using with Google Antigravity

Run `bash install.sh --target antigravity` (global, `~/.gemini/config/skills`)
or `bash install.sh --project . --target agents` (workspace, `.agents/skills`).

## Architecture

```
skills/                    # 27 sub-skills (auto-discovered)
  seo/SKILL.md            # Main orchestrator + routing
  seo-cluster/            # Semantic clustering
  seo-sxo/                # Search Experience Optimization
  seo-drift/              # SEO drift monitoring
  seo-ecommerce/          # E-commerce SEO
  seo-audit/              # Full site audit
  seo-page/               # Single-page analysis
  seo-technical/          # Technical SEO
  seo-content/            # E-E-A-T quality
  seo-content-brief/      # Content brief generation
  seo-schema/             # Schema.org markup
  seo-sitemap/            # XML sitemaps
  seo-images/             # Image optimization
  seo-geo/                # AI search / GEO
  seo-aeo/                # Answer Engine Optimization (AEO)
  seo-agentic/            # Agent readiness (Lighthouse Agentic Browsing, WebMCP)
  seo-local/              # Local SEO
  seo-maps/               # Maps intelligence
  seo-plan/               # Strategic planning
  seo-hreflang/           # International SEO
  seo-google/             # Google APIs
  seo-backlinks/          # Backlink analysis
  seo-programmatic/       # Programmatic SEO
  seo-competitor-pages/   # Competitor pages
  seo-flow/               # FLOW framework integration
  seo-dataforseo/         # DataForSEO (extension)
  seo-image-gen/          # AI images (extension)
agents/                    # 20 subagents
scripts/                   # 66 Python scripts, including the managed runtime and installer
schema/                    # JSON-LD templates
extensions/                # 9 MCP extensions: DataForSEO, Firecrawl, Banana, Ahrefs, SE Ranking, Profound, Bing Webmaster, Matomo, Unlighthouse
```

## Key Principles

1. **Progressive Disclosure**: Read SKILL.md for routing, load references on demand
2. **Industry Detection**: Auto-detect SaaS, e-commerce, local, publisher, agency
3. **Security**: All scripts call `validate_url()` for SSRF protection
4. **Config location**: `~/.config/ai-agent-seo/` for API credentials

## Credits

Created by @extramiles77.
