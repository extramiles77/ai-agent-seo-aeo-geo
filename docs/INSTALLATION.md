# Installation Guide

## Prerequisites

- **Python 3.11 to 3.14** with pip. Python 3.10 reached end of life in October 2026, and 3.15 waits on the Google Ads client library
- **Claude Code CLI** installed and configured

Optional:
- **Playwright Chromium** - install.sh attempts this automatically; failure is non-fatal; needed only for SPA rendering and screenshots

## Quick Install

Claude Code 1.0.33+:

1. **Point Claude Code at this checkout** (or copy it anywhere on disk).
2. **Run the installer for your platform**

```bash
bash install.sh
```

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

The installer copies every skill and agent into `~/.claude/skills` and
`~/.claude/agents` straight from the directory it lives in. It does not clone a
repository, and it never falls back to global or user package installation.

3. **Verify the managed runtime**

```bash
~/.claude/skills/seo/scripts/ai-agent-seo doctor
```

`/seo setup` provisions dependencies and Chromium into
`~/.claude/skills/seo/.venv/`. If only Chromium failed, the installer reports a
degraded result and raw-fetch analysis remains available.

## Installation Paths

The installer copies files to:

| Component | Path |
|-----------|------|
| Main skill | `~/.claude/skills/seo/` |
| Sub-skills | `~/.claude/skills/seo-*/` |
| Subagents | `~/.claude/agents/seo-*.md` |
| Runtime launcher | `~/.claude/skills/seo/scripts/ai-agent-seo` |
| Isolated Python | `~/.claude/skills/seo/.venv/` |

## Other AI Agents (Codex, Gemini CLI, Cursor, OpenCode, Copilot, Antigravity, Windsurf)

Pass a target to the same installer. It copies the skills to the folder that
harness scans, writes absolute launcher paths into every `SKILL.md`, places the
specialist agents in `seo/subagents/` for harnesses without a subagent tool,
and builds the runtime once.

```bash
bash install.sh --list                      # detected harnesses
bash install.sh --target agents             # ~/.agents/skills (Codex, Gemini CLI, Cursor, OpenCode, Copilot)
bash install.sh --target antigravity        # ~/.gemini/config/skills
bash install.sh --target windsurf           # ~/.codeium/windsurf/skills
bash install.sh --target all                # all detected, one shared runtime
bash install.sh --project /path/to/repo --target agents   # <repo>/.agents/skills
bash install.sh --dest /path/to/skills      # any other harness
bash install.sh --target agents --dry-run   # preview only
```

Windows PowerShell: `.\install.ps1 -Target agents` (or `-List`). In
PowerShell-based harnesses the skills call `scripts\ai-agent-seo.cmd`.

Notes:

- OpenAI Codex runs commands in a sandbox without network by default. The SEO
  scripts fetch live pages, so allow network access
  (`[sandbox_workspace_write] network_access = true` in `~/.codex/config.toml`)
  or approve the commands when asked.
- OpenCode, Cursor and Copilot also read `~/.claude/skills`. Installing both
  `claude` and `agents` is fine; both copies are identical.
- Uninstall: `./scripts/ai-agent-seo uninstall --target agents`.

## Verify Installation

1. Start Claude Code:

```bash
claude
```

2. Check that the skill is loaded:

```
/seo
```

You should see a help message or prompt for a URL.

## Uninstallation

From the checkout you installed from:

```bash
bash uninstall.sh
```

```powershell
powershell -ExecutionPolicy Bypass -File uninstall.ps1
```

If you installed through a marketplace instead, use `/plugin uninstall` with the
plugin name and remove the marketplace entry with `/plugin marketplace remove`.

`uninstall.sh` removes all installed sub-skills, sub-agents, and the plugin's MCP entries from `~/.claude/settings.json`. Do not maintain a hand-coded `rm` list. The shipped uninstaller is the canonical source.

## Upgrading

To upgrade, replace this checkout with the newer one and rerun the installer.
The installer is idempotent: it overwrites installed skills and agents, then
refreshes the managed runtime.

```bash
bash uninstall.sh
bash install.sh
```

### Upgrading from claude-seo

The project is now named AI Agent SEO (`ai-agent-seo`). Old settings keep
working:

| Before | Now | Compatibility |
|---|---|---|
| `scripts/claude-seo` launcher | `scripts/ai-agent-seo` | Reinstall; the installer rewrites every skill to the new launcher |
| `CLAUDE_SEO_*` variables (`CLAUDE_SEO_PYTHON`, `CLAUDE_SEO_LOCAL_TARGETS`, ...) | `AI_AGENT_SEO_*` | Old names are still read when the new one is unset |
| `~/.config/claude-seo/`, `~/.cache/claude-seo/` | `~/.config/ai-agent-seo/`, `~/.cache/ai-agent-seo/` | Copied once on the first script run if the new folder does not exist; the old folder is left in place |
| Plugin `claude-seo` | Plugin `ai-agent-seo` | Uninstall the old plugin, then install the new one |

## Troubleshooting

### "Skill not found" error

Ensure the skill is installed in the correct location:

```bash
ls ~/.claude/skills/seo/SKILL.md
```

If the file doesn't exist, re-run the installer.

### Python dependency errors

Run the managed setup again:

```bash
~/.claude/skills/seo/scripts/ai-agent-seo setup
```

### Playwright screenshot errors

Run the managed setup again and inspect the result:

```bash
~/.claude/skills/seo/scripts/ai-agent-seo setup
~/.claude/skills/seo/scripts/ai-agent-seo doctor
```

### Permission errors on Unix

Make sure scripts are executable:

```bash
chmod +x ~/.claude/skills/seo/scripts/*.py
```
