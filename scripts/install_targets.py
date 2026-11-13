#!/usr/bin/env python3
"""Install Ai Agent SEO into any AI agent harness that reads Agent Skills.

Every harness that follows the open Agent Skills standard (a folder per skill
with a ``SKILL.md``) can load these skills: Claude Code, OpenAI Codex CLI,
Gemini CLI, Cursor, OpenCode, GitHub Copilot, Google Antigravity, Windsurf and
others. Only the folder they scan differs, so this installer copies the same
skills into the folder each harness reads and rewrites the plugin-root token
(``${CLAUDE_PLUGIN_ROOT}``, which only Claude Code expands) into absolute
paths that work in any shell.

Layout after an install into a skills root ``R``::

    R/seo/                 orchestrator skill + runtime home (scripts, schema,
                           data, hooks, extension scripts, managed .venv)
    R/seo/subagents/*.md   specialist instructions; harnesses without a
                           subagent tool read and run these inline
    R/seo-*/               sub-skills

The runtime (scripts and the isolated virtual environment) is installed once,
into the first target. Later targets in the same run point at that runtime, so
a multi-target install does not create several copies of the environment.

Usage::

    claude-seo install --target agents            # Codex, Gemini, Cursor, OpenCode, Copilot
    claude-seo install --target all               # every detected harness
    claude-seo install --project . --target agents
    claude-seo install --dest /path/to/skills     # any other harness
    claude-seo install --list                     # show targets and detection
    claude-seo uninstall --target agents

Standard library only, so it runs before the managed environment exists.
Prints a JSON summary with ``--json``.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

TOKEN = "${CLAUDE_PLUGIN_ROOT}"
LAUNCHER_TOKEN = TOKEN + "/scripts/claude-seo"
COPY_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".venv", ".venv.*", ".DS_Store")

# name -> (skills folder relative to home, agent folder or None, harnesses, detection folder)
TARGETS: dict[str, dict[str, str | None]] = {
    "agents": {
        "skills": ".agents/skills",
        "agents": None,
        "label": "OpenAI Codex CLI, Gemini CLI, Cursor, OpenCode, GitHub Copilot (shared ~/.agents/skills)",
        "detect": None,
    },
    "claude": {
        "skills": ".claude/skills",
        "agents": ".claude/agents",
        "label": "Claude Code",
        "detect": ".claude",
    },
    "antigravity": {
        "skills": ".gemini/config/skills",
        "agents": None,
        "label": "Google Antigravity",
        "detect": ".gemini",
    },
    "windsurf": {
        "skills": ".codeium/windsurf/skills",
        "agents": None,
        "label": "Windsurf (Cascade)",
        "detect": ".codeium/windsurf",
    },
}
ALIASES = {
    "codex": "agents",
    "openai": "agents",
    "gemini": "agents",
    "gemini-cli": "agents",
    "cursor": "agents",
    "opencode": "agents",
    "copilot": "agents",
    "github-copilot": "agents",
    "claude-code": "claude",
}
ALL_ORDER = ("agents", "claude", "antigravity", "windsurf")


@dataclass
class Plan:
    name: str
    skills_root: Path
    agent_dir: Path | None
    label: str
    runtime_home: Path = field(default_factory=Path)
    owns_runtime: bool = False


def _source_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _home() -> Path:
    return Path(os.environ.get("CLAUDE_SEO_INSTALL_HOME") or Path.home()).expanduser()


def _skill_sources(src: Path) -> list[Path]:
    """Core skills first, extension skills after, matching install.sh order."""
    core = sorted(p for p in (src / "skills").iterdir() if (p / "SKILL.md").is_file())
    ext = sorted(p for p in src.glob("extensions/*/skills/*") if (p / "SKILL.md").is_file())
    return core + ext


def _agent_sources(src: Path) -> list[Path]:
    return sorted(src.glob("agents/*.md")) + sorted(src.glob("extensions/*/agents/*.md"))


def _posix(path: Path) -> str:
    return path.as_posix()


def resolve_targets(names: list[str], home: Path) -> list[str]:
    """Expand aliases and ``all``; keep order, drop duplicates."""
    resolved: list[str] = []
    for raw in names:
        for part in raw.split(","):
            name = part.strip().lower()
            if not name:
                continue
            if name == "all":
                chosen = [t for t in ALL_ORDER if _detected(t, home)]
            else:
                name = ALIASES.get(name, name)
                if name not in TARGETS:
                    raise ValueError(
                        f"unknown target '{part}'. Choose from: "
                        + ", ".join(sorted(set(TARGETS) | set(ALIASES) | {"all"}))
                    )
                chosen = [name]
            for item in chosen:
                if item not in resolved:
                    resolved.append(item)
    return resolved


def _detected(name: str, home: Path) -> bool:
    detect = TARGETS[name]["detect"]
    return detect is None or (home / detect).is_dir()


def build_plans(args: argparse.Namespace, home: Path) -> list[Plan]:
    plans: list[Plan] = []
    if args.dest:
        root = Path(args.dest).expanduser().resolve()
        plans.append(Plan("custom", root, None, f"custom folder {root}"))
    if args.project:
        root = (Path(args.project).expanduser().resolve() / ".agents" / "skills")
        plans.append(Plan("project", root, None, "project .agents/skills (Codex, Cursor, Copilot, Antigravity, OpenCode)"))
    names = resolve_targets(args.target or ([] if plans else ["agents"]), home)
    for name in names:
        spec = TARGETS[name]
        agent_dir = home / spec["agents"] if spec["agents"] else None
        plans.append(Plan(name, home / str(spec["skills"]), agent_dir, str(spec["label"])))
    if not plans:
        raise ValueError("nothing to install: no target was detected")
    runtime_home = plans[0].skills_root / "seo"
    if args.runtime_home:
        runtime_home = Path(args.runtime_home).expanduser().resolve()
    for index, plan in enumerate(plans):
        plan.runtime_home = runtime_home
        plan.owns_runtime = index == 0 and not args.runtime_home
    return plans


def _copy_tree(source: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, dest, dirs_exist_ok=True, ignore=COPY_IGNORE)


def _copy_runtime(src: Path, home_dir: Path) -> None:
    """Mirror the repository-relative runtime layout under the seo skill."""
    for folder in ("scripts", "schema", "data", "hooks"):
        if (src / folder).is_dir():
            _copy_tree(src / folder, home_dir / folder)
    for ext in sorted(p for p in (src / "extensions").iterdir() if p.is_dir()):
        for folder in ("references", "scripts"):
            if (ext / folder).is_dir():
                _copy_tree(ext / folder, home_dir / "extensions" / ext.name / folder)
    for name in ("requirements.txt", "pyproject.toml", "LICENSE"):
        if (src / name).is_file():
            shutil.copy2(src / name, home_dir / name)
    for launcher in ("claude-seo", "claude-seo.cmd"):
        target = home_dir / "scripts" / launcher
        if target.is_file() and os.name != "nt":
            target.chmod(target.stat().st_mode | 0o111)


def rewrite_text(text: str, plan: Plan, windows: bool | None = None) -> str:
    """Replace the plugin-root token with absolute paths for this target."""
    windows = (os.name == "nt") if windows is None else windows
    runtime = _posix(plan.runtime_home)
    launcher = runtime + ("/scripts/claude-seo.cmd" if windows else "/scripts/claude-seo")
    agents = _posix(plan.agent_dir) if plan.agent_dir else _posix(plan.skills_root / "seo" / "subagents")
    text = text.replace(LAUNCHER_TOKEN + '"', launcher + '"')
    text = text.replace(LAUNCHER_TOKEN, launcher)
    text = text.replace(TOKEN + "/skills/", _posix(plan.skills_root) + "/")
    text = text.replace(TOKEN + "/agents/", agents + "/")
    return text.replace(TOKEN + "/", runtime + "/")


def _rewrite_file(path: Path, plan: Plan) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return
    updated = rewrite_text(text, plan)
    if updated != text:
        path.write_text(updated, encoding="utf-8", newline="\n")


def install(plan: Plan, src: Path, dry_run: bool) -> dict[str, object]:
    skills = _skill_sources(src)
    agents = _agent_sources(src)
    result: dict[str, object] = {
        "target": plan.name,
        "harnesses": plan.label,
        "skills_root": _posix(plan.skills_root),
        "runtime_home": _posix(plan.runtime_home),
        "owns_runtime": plan.owns_runtime,
        "skills": [p.name for p in skills],
        "subagents": len(agents),
    }
    if dry_run:
        return result
    for skill in skills:
        dest = plan.skills_root / skill.name
        _copy_tree(skill, dest)
        for md in skill.rglob("*.md"):
            _rewrite_file(dest / md.relative_to(skill), plan)
    seo_home = plan.skills_root / "seo"
    if plan.owns_runtime:
        _copy_runtime(src, seo_home)
        for md in (seo_home / "extensions").rglob("*.md"):
            _rewrite_file(md, plan)
    subagent_dirs = [seo_home / "subagents"]
    if plan.agent_dir:
        subagent_dirs.append(plan.agent_dir)
    for folder in subagent_dirs:
        folder.mkdir(parents=True, exist_ok=True)
        for agent in agents:
            shutil.copy2(agent, folder / agent.name)
            _rewrite_file(folder / agent.name, plan)
    return result


def run_setup(runtime_home: Path, skip_browser: bool) -> int:
    runtime = runtime_home / "scripts" / "runtime.py"
    argv = [sys.executable, str(runtime), "setup"] + (["--skip-browser"] if skip_browser else [])
    return subprocess.run(argv).returncode


def uninstall(plan: Plan, src: Path, dry_run: bool) -> dict[str, object]:
    removed: list[str] = []
    for skill in _skill_sources(src):
        dest = plan.skills_root / skill.name
        if (dest / "SKILL.md").is_file():
            removed.append(_posix(dest))
            if not dry_run:
                shutil.rmtree(dest)
    if plan.agent_dir:
        for agent in _agent_sources(src):
            dest = plan.agent_dir / agent.name
            if dest.is_file():
                removed.append(_posix(dest))
                if not dry_run:
                    dest.unlink()
    return {"target": plan.name, "skills_root": _posix(plan.skills_root), "removed": removed}


def list_targets(home: Path) -> list[dict[str, object]]:
    rows = []
    for name in ALL_ORDER:
        spec = TARGETS[name]
        root = home / str(spec["skills"])
        rows.append({
            "target": name,
            "harnesses": spec["label"],
            "skills_root": _posix(root),
            "detected": _detected(name, home),
            "installed": (root / "seo" / "SKILL.md").is_file(),
        })
    return rows


def build_parser(prog: str = "claude-seo install") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Install Ai Agent SEO skills into Claude Code, Codex, Gemini CLI, Cursor, "
        "OpenCode, GitHub Copilot, Antigravity, Windsurf or any Agent Skills folder.",
    )
    parser.add_argument("--target", action="append", metavar="NAME",
                        help="agents (default), claude, antigravity, windsurf, all; aliases: "
                        + ", ".join(sorted(ALIASES)) + ". Repeat or comma-separate.")
    parser.add_argument("--project", metavar="DIR", help="install into DIR/.agents/skills (project scope)")
    parser.add_argument("--dest", metavar="DIR", help="install into any skills folder")
    parser.add_argument("--runtime-home", metavar="DIR",
                        help="reuse an existing installed runtime (its seo skill folder) instead of copying one")
    parser.add_argument("--skip-setup", action="store_true", help="copy files only; do not build the Python runtime")
    parser.add_argument("--skip-browser", action="store_true", help="build the runtime without Chromium")
    parser.add_argument("--uninstall", action="store_true", help="remove the installed skills instead")
    parser.add_argument("--dry-run", action="store_true", help="show what would change")
    parser.add_argument("--list", action="store_true", help="list targets, detection and install state")
    parser.add_argument("--json", action="store_true", help="print a JSON summary")
    return parser


def main(argv: list[str] | None = None, prog: str = "claude-seo install") -> int:
    args = build_parser(prog).parse_args(argv)
    home = _home()
    src = _source_root()
    if not args.list and not (src / "skills" / "seo" / "SKILL.md").is_file():
        print("Ai Agent SEO install: run this from the repository checkout "
              "(./scripts/claude-seo install ...), not from an installed copy.", file=sys.stderr)
        return 2
    if args.list:
        rows = list_targets(home)
        if args.json:
            print(json.dumps({"targets": rows}, indent=2))
        else:
            for row in rows:
                state = "installed" if row["installed"] else ("detected" if row["detected"] else "not found")
                print(f"{row['target']:<12} {state:<10} {row['skills_root']}  ({row['harnesses']})")
        return 0
    try:
        plans = build_plans(args, home)
    except ValueError as exc:
        print(f"Ai Agent SEO install: {exc}", file=sys.stderr)
        return 2
    if args.uninstall:
        results = [uninstall(plan, src, args.dry_run) for plan in plans]
        if args.json:
            print(json.dumps({"uninstalled": results, "dry_run": args.dry_run}, indent=2))
        else:
            for item in results:
                print(f"{item['target']}: removed {len(item['removed'])} item(s) from {item['skills_root']}")
        return 0
    if args.runtime_home and not (Path(args.runtime_home).expanduser() / "scripts" / "runtime.py").is_file():
        print("Ai Agent SEO install: --runtime-home must be an installed seo skill folder", file=sys.stderr)
        return 2
    results = [install(plan, src, args.dry_run) for plan in plans]
    setup_status: int | None = None
    owner = next((p for p in plans if p.owns_runtime), None)
    if owner and not args.dry_run and not args.skip_setup:
        setup_status = run_setup(owner.runtime_home, args.skip_browser)
    summary = {"installed": results, "dry_run": args.dry_run, "setup_exit_code": setup_status}
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        for item in results:
            note = "runtime" if item["owns_runtime"] else f"uses runtime in {item['runtime_home']}"
            print(f"{'Would install' if args.dry_run else 'Installed'} {len(item['skills'])} skills -> "
                  f"{item['skills_root']}  [{item['harnesses']}; {note}]")
        if setup_status not in (None, 0):
            print("Runtime setup did not finish cleanly (exit "
                  f"{setup_status}); rerun: claude-seo setup", file=sys.stderr)
    if setup_status not in (None, 0, 10):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(prog="install_targets.py"))
