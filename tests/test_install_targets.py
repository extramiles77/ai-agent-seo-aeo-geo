"""Cross-harness installer: every Agent Skills harness gets working paths."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import install_targets  # noqa: E402


def _install(home: Path, *args: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "runtime.py"), "install", "--skip-setup", "--json", *args],
        capture_output=True, text=True, env={"CLAUDE_SEO_INSTALL_HOME": str(home), "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_aliases_resolve_to_shared_agents_folder(tmp_path: Path) -> None:
    names = install_targets.resolve_targets(["codex,gemini", "cursor", "opencode", "copilot"], tmp_path)
    assert names == ["agents"]


def test_all_only_includes_detected_harnesses(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    assert install_targets.resolve_targets(["all"], tmp_path) == ["agents", "claude"]


def test_unknown_target_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        install_targets.resolve_targets(["notaharness"], tmp_path)


def test_agents_install_rewrites_every_plugin_root_token(tmp_path: Path) -> None:
    summary = _install(tmp_path, "--target", "agents")
    root = tmp_path / ".agents" / "skills"
    assert summary["installed"][0]["owns_runtime"] is True
    leftovers = [
        str(path.relative_to(root))
        for path in root.rglob("*.md")
        if re.search(r"\$\{CLAUDE_PLUGIN_ROOT\}/(scripts|skills|agents|hooks)/", path.read_text(encoding="utf-8"))
    ]
    assert leftovers == []
    audit = (root / "seo-audit" / "SKILL.md").read_text(encoding="utf-8")
    launcher = (root / "seo" / "scripts" / "claude-seo").as_posix()
    assert f'"{launcher}" run render_page.py' in audit
    assert (root / "seo" / "subagents").as_posix() + "/<name>.md" in audit
    assert (root / "seo" / "subagents" / "seo-technical.md").is_file()
    assert (root / "seo" / "scripts" / "runtime.py").is_file()
    assert (root / "seo" / "data" / "google-updates.json").is_file()


def test_every_installed_skill_name_matches_its_folder(tmp_path: Path) -> None:
    _install(tmp_path, "--target", "agents")
    root = tmp_path / ".agents" / "skills"
    for skill in root.glob("*/SKILL.md"):
        head = skill.read_text(encoding="utf-8").split("---", 2)[1]
        assert re.search(rf"^name: {re.escape(skill.parent.name)}$", head, re.M), skill


def test_second_target_reuses_first_runtime(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    summary = _install(tmp_path, "--target", "agents", "--target", "claude")
    claude = summary["installed"][1]
    assert claude["owns_runtime"] is False
    assert not (tmp_path / ".claude" / "skills" / "seo" / "scripts").exists()
    audit = (tmp_path / ".claude" / "skills" / "seo-audit" / "SKILL.md").read_text(encoding="utf-8")
    assert (tmp_path / ".agents" / "skills" / "seo" / "scripts" / "claude-seo").as_posix() in audit
    assert (tmp_path / ".claude" / "agents").as_posix() + "/<name>.md" in audit
    assert (tmp_path / ".claude" / "agents" / "seo-geo.md").is_file()


def test_windows_rewrite_uses_cmd_launcher(tmp_path: Path) -> None:
    plan = install_targets.Plan("agents", tmp_path / "skills", None, "x", runtime_home=tmp_path / "skills" / "seo")
    text = '"${CLAUDE_PLUGIN_ROOT}/scripts/claude-seo" run fetch_page.py'
    assert install_targets.rewrite_text(text, plan, windows=True).startswith(
        '"' + (tmp_path / "skills" / "seo" / "scripts" / "claude-seo.cmd").as_posix() + '" run'
    )
    assert (ROOT / "scripts" / "claude-seo.cmd").is_file()


def test_uninstall_removes_only_our_skills(tmp_path: Path) -> None:
    _install(tmp_path, "--target", "agents")
    other = tmp_path / ".agents" / "skills" / "someone-else"
    other.mkdir()
    (other / "SKILL.md").write_text("---\nname: someone-else\ndescription: x\n---\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "runtime.py"), "uninstall", "--target", "agents"],
        capture_output=True, text=True, env={"CLAUDE_SEO_INSTALL_HOME": str(tmp_path), "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 0, result.stderr
    remaining = sorted(p.name for p in (tmp_path / ".agents" / "skills").iterdir())
    assert remaining == ["someone-else"]


def test_installers_forward_targets_to_cross_harness_installer() -> None:
    assert 'exec "${SOURCE_DIR}/scripts/claude-seo" install "$@"' in (ROOT / "install.sh").read_text(encoding="utf-8")
    ps1 = (ROOT / "install.ps1").read_text(encoding="utf-8")
    assert "[string[]]$Target" in ps1 and "'install'" in ps1


def test_skill_descriptions_are_single_line_for_every_parser() -> None:
    folded = [
        str(p.relative_to(ROOT))
        for p in [*ROOT.glob("skills/*/SKILL.md"), *ROOT.glob("extensions/*/skills/*/SKILL.md"),
                  *ROOT.glob("agents/*.md"), *ROOT.glob("extensions/*/agents/*.md")]
        if re.search(r"^description:\s*[>|]", p.read_text(encoding="utf-8").split("---", 2)[1], re.M)
    ]
    assert folded == []
