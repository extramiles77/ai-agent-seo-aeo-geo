#!/usr/bin/env python3
"""
Optimization settings for AI Agent SEO: how much audits weigh SEO, AEO and GEO.

* SEO: classic search rankings (crawl, index, content, on-page, speed).
* AEO, Answer Engine Optimization: being lifted as the direct answer in
  featured snippets, People Also Ask, voice assistants and answer boxes.
* GEO, Generative Engine Optimization: being cited by AI search (Google AI
  Overviews and AI Mode, ChatGPT, Perplexity, Gemini, Copilot).

One setting, ``optimization_focus``, picks the scoring profile: ``balanced``
(default), ``seo``, ``aeo`` or ``geo``. It is resolved in this order, first
non-empty value wins:

1. ``--focus``            an explicit choice for one command (``/seo audit <url> --focus aeo``)
2. ``AI_AGENT_SEO_FOCUS`` environment variable (any harness)
3. ``--plugin-focus``     the Claude Code plugin option, passed by the skills as
                          ``${user_config.optimization_focus}`` (set it in ``/config``)
4. ``settings.json``      ``~/.config/ai-agent-seo/settings.json`` (or
                          ``$AI_AGENT_SEO_CONFIG_DIR/settings.json``), written by ``set``
5. ``balanced``

The weights are this project's scoring conventions, not search engine factors.

Usage:
    python seo_settings.py show [--focus aeo] [--plugin-focus geo] [--json]
    python seo_settings.py set focus aeo
    python seo_settings.py profiles

Output (JSON on stdout)::

    {"optimization_focus": "aeo", "source": "env", "weights": {"Technical SEO": 14, ...},
     "headline_scores": ["SEO Health", "AEO", "GEO"], "settings_path": "~/.config/ai-agent-seo/settings.json"}
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

FOCUSES = ("balanced", "seo", "aeo", "geo")
DEFAULT_FOCUS = "balanced"
ENV_FOCUS = "AI_AGENT_SEO_FOCUS"
CATEGORIES = (
    "Technical SEO",
    "Content Quality",
    "On-Page SEO",
    "Schema / Structured Data",
    "Performance (CWV)",
    "AI Search Readiness (GEO)",
    "Answer Readiness (AEO)",
    "Images",
)
# Each profile sums to 100. Order matches CATEGORIES.
PROFILES = {
    "balanced": (20, 20, 18, 10, 10, 10, 7, 5),
    "seo": (22, 22, 20, 10, 10, 6, 5, 5),
    "aeo": (14, 20, 12, 14, 6, 12, 18, 4),
    "geo": (14, 20, 12, 12, 6, 22, 10, 4),
}
DESCRIPTIONS = {
    "balanced": "SEO, AEO and GEO together; the default for a full audit.",
    "seo": "Classic rankings first: technical, content and on-page.",
    "aeo": "Direct answers first: featured snippets, People Also Ask, voice and answer boxes.",
    "geo": "AI citations first: AI Overviews and AI Mode, ChatGPT, Perplexity, Gemini, Copilot.",
}


def config_dir() -> Path:
    override = os.environ.get("AI_AGENT_SEO_CONFIG_DIR") or os.environ.get("CLAUDE_SEO_CONFIG_DIR")
    return Path(override).expanduser() if override else Path.home() / ".config" / "ai-agent-seo"


def settings_path() -> Path:
    return config_dir() / "settings.json"


def _normalise(value: object) -> str:
    text = str(value or "").strip().lower()
    # An unexpanded template token (a harness that does not substitute it) means unset.
    return "" if text.startswith("${") else text


def _read_file() -> dict:
    try:
        data = json.loads(settings_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def resolve(focus: str = "", plugin_focus: str = "") -> dict:
    """Return the effective focus, where it came from, and its weights."""
    candidates = (
        ("flag", _normalise(focus)),
        ("env", _normalise(os.environ.get(ENV_FOCUS))),
        ("plugin-option", _normalise(plugin_focus)),
        ("settings-file", _normalise(_read_file().get("optimization_focus"))),
    )
    chosen, source, ignored = DEFAULT_FOCUS, "default", []
    for origin, value in candidates:
        if not value:
            continue
        if value in FOCUSES:
            chosen, source = value, origin
            break
        ignored.append({"source": origin, "value": value})
    weights = dict(zip(CATEGORIES, PROFILES[chosen]))
    result = {
        "optimization_focus": chosen,
        "source": source,
        "description": DESCRIPTIONS[chosen],
        "weights": weights,
        "headline_scores": ["SEO Health", "AEO", "GEO"],
        "settings_path": str(settings_path()).replace(str(Path.home()), "~", 1),
    }
    if ignored:
        result["ignored_invalid"] = ignored
    return result


def write_focus(value: str) -> dict:
    value = _normalise(value)
    if value not in FOCUSES:
        raise ValueError(f"focus must be one of: {', '.join(FOCUSES)}")
    path = settings_path()
    data = _read_file()
    data["optimization_focus"] = value
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SEO / AEO / GEO optimization settings. JSON on stdout.")
    sub = parser.add_subparsers(dest="command", required=True)
    show = sub.add_parser("show", help="print the effective settings")
    show.add_argument("--focus", default="", help="explicit focus for this command")
    show.add_argument("--plugin-focus", default="", help="the Claude Code plugin option value")
    show.add_argument("--json", action="store_true", help="accepted for consistency; output is JSON")
    setter = sub.add_parser("set", help="save a setting to settings.json")
    setter.add_argument("key", choices=["focus"])
    setter.add_argument("value", choices=FOCUSES)
    sub.add_parser("profiles", help="list every focus profile and its weights")
    args = parser.parse_args(argv)

    if args.command == "show":
        print(json.dumps(resolve(args.focus, args.plugin_focus), indent=2))
    elif args.command == "set":
        print(json.dumps(write_focus(args.value), indent=2))
    else:
        print(json.dumps({name: {"description": DESCRIPTIONS[name], "weights": dict(zip(CATEGORIES, PROFILES[name]))}
                          for name in FOCUSES}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
