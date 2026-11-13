# README demo GIFs

The three GIFs in `screenshots/` are rendered from **real command output**, not
screen recordings and not hand-typed text:

| GIF | Shows |
|---|---|
| `seo-install-demo.gif` | `install.sh --list` and `--target all` into a throwaway home folder |
| `seo-command-demo.gif` | Claude Code's view of the plugin and the same skills in `~/.agents/skills` |
| `seo-audit-demo.gif` | `seo_settings.py`, `aeo_check.py` and `agentic_check.py` on example.com |

## Rebuild

```bash
# Pillow is in the plugin runtime; gifsicle (optional) shrinks the output.
~/.agents/skills/seo/.venv/bin/python docs/demos/build_demos.py
~/.agents/skills/seo/.venv/bin/python docs/demos/build_demos.py --only seo-audit-demo.gif
```

Requirements on the build machine: an installed runtime (`bash install.sh
--target agents`), `jq`, the Claude Code CLI for the command demo, and network
access for the example.com checks.

## Configure

Everything lives in `demos.json`:

- `canvas`: size and typing speed (`fps_ms` per frame)
- `theme`: the purple backdrop, white window bar, terminal and accent colours
- `line_colors`: regex rules that colour output lines (success, detected, warnings, issues)
- `chips` and `footer`: the SEO / AEO / GEO badges and the repository link
- `demos[].steps[]`: `show` is the command as a user types it (`ai-agent-seo`
  stands for the installed launcher), `run` is what executes; `{launcher}`,
  `{home}` and `{sandbox}` are filled in at build time

Home and sandbox paths in the output are rewritten to `~` so no personal path
ends up in a published GIF.
