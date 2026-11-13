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
        capture_output=True, text=True, env={"AI_AGENT_SEO_INSTALL_HOME": str(home), "PATH": "/usr/bin:/bin"},
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
    launcher = (root / "seo" / "scripts" / "ai-agent-seo").as_posix()
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
    assert (tmp_path / ".agents" / "skills" / "seo" / "scripts" / "ai-agent-seo").as_posix() in audit
    assert (tmp_path / ".claude" / "agents").as_posix() + "/<name>.md" in audit
    assert (tmp_path / ".claude" / "agents" / "seo-geo.md").is_file()


def test_windows_rewrite_uses_cmd_launcher(tmp_path: Path) -> None:
    plan = install_targets.Plan("agents", tmp_path / "skills", None, "x", runtime_home=tmp_path / "skills" / "seo")
    text = '"${CLAUDE_PLUGIN_ROOT}/scripts/ai-agent-seo" run fetch_page.py'
    assert install_targets.rewrite_text(text, plan, windows=True).startswith(
        '"' + (tmp_path / "skills" / "seo" / "scripts" / "ai-agent-seo.cmd").as_posix() + '" run'
    )
    assert (ROOT / "scripts" / "ai-agent-seo.cmd").is_file()


def test_uninstall_removes_only_our_skills(tmp_path: Path) -> None:
    _install(tmp_path, "--target", "agents")
    other = tmp_path / ".agents" / "skills" / "someone-else"
    other.mkdir()
    (other / "SKILL.md").write_text("---\nname: someone-else\ndescription: x\n---\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "runtime.py"), "uninstall", "--target", "agents"],
        capture_output=True, text=True, env={"AI_AGENT_SEO_INSTALL_HOME": str(tmp_path), "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 0, result.stderr
    remaining = sorted(p.name for p in (tmp_path / ".agents" / "skills").iterdir())
    assert remaining == ["someone-else"]


def test_installers_forward_targets_to_cross_harness_installer() -> None:
    assert 'exec "${SOURCE_DIR}/scripts/ai-agent-seo" install "$@"' in (ROOT / "install.sh").read_text(encoding="utf-8")
    ps1 = (ROOT / "install.ps1").read_text(encoding="utf-8")
    assert "[string[]]$Target" in ps1 and "'install'" in ps1


def _skill_frontmatter() -> dict[str, str]:
    found = {}
    for path in [*ROOT.glob("skills/*/SKILL.md"), *ROOT.glob("extensions/*/skills/*/SKILL.md")]:
        head = path.read_text(encoding="utf-8").split("---", 2)[1]
        name = re.search(r"^name: (.+)$", head, re.M).group(1).strip()
        desc = re.search(r"^description: (.+)$", head, re.M).group(1).strip()
        found[name] = json.loads(desc) if desc.startswith('"') else desc
    return found


def test_skill_list_fits_codex_budget() -> None:
    """Codex lists skills within 8,000 characters; leave room for other skills."""
    total = sum(len(name) + len(desc) for name, desc in _skill_frontmatter().items())
    assert total <= 7800, f"skill names + descriptions total {total} characters"


def test_every_skill_says_when_to_use_it() -> None:
    missing = [name for name, desc in _skill_frontmatter().items()
               if not re.search(r"\bUse (when|for|only)\b", desc)]
    assert missing == []


def test_skill_descriptions_are_single_line_for_every_parser() -> None:
    folded = [
        str(p.relative_to(ROOT))
        for p in [*ROOT.glob("skills/*/SKILL.md"), *ROOT.glob("extensions/*/skills/*/SKILL.md"),
                  *ROOT.glob("agents/*.md"), *ROOT.glob("extensions/*/agents/*.md")]
        if re.search(r"^description:\s*[>|]", p.read_text(encoding="utf-8").split("---", 2)[1], re.M)
    ]
    assert folded == []


def _runtime():
    import importlib.util

    spec = importlib.util.spec_from_file_location("ai_agent_seo_runtime_under_test", ROOT / "scripts" / "runtime.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_legacy_claude_seo_env_vars_still_work() -> None:
    env = {"CLAUDE_SEO_PYTHON": "/old/python", "AI_AGENT_SEO_DATA_DIR": "/new", "CLAUDE_SEO_DATA_DIR": "/old"}
    _runtime()._apply_legacy_env(env)
    assert env["AI_AGENT_SEO_PYTHON"] == "/old/python"
    assert env["AI_AGENT_SEO_DATA_DIR"] == "/new", "an explicit new name wins over the legacy one"


def test_legacy_config_folder_is_copied_once_with_permissions(tmp_path: Path, monkeypatch) -> None:
    old = tmp_path / ".config" / "claude-seo"
    old.mkdir(parents=True)
    secret = old / "google-api.json"
    secret.write_text("{}", encoding="utf-8")
    secret.chmod(0o600)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    _runtime()._migrate_legacy_user_dirs()
    copied = tmp_path / ".config" / "ai-agent-seo" / "google-api.json"
    assert copied.read_text(encoding="utf-8") == "{}"
    assert secret.is_file(), "the legacy folder is left in place"
    if sys.platform != "win32":
        assert copied.stat().st_mode & 0o777 == 0o600


def test_launchers_accept_legacy_python_override() -> None:
    assert "CLAUDE_SEO_PYTHON" in (ROOT / "scripts" / "ai-agent-seo").read_text(encoding="utf-8")
    assert "CLAUDE_SEO_PYTHON" in (ROOT / "scripts" / "ai-agent-seo.cmd").read_text(encoding="utf-8")
    assert "CLAUDE_SEO_PYTHON" in (ROOT / "hooks" / "run-python-hook.js").read_text(encoding="utf-8")
