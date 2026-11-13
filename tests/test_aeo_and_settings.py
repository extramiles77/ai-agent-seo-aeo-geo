"""AEO checker, SEO/AEO/GEO settings, and plugin-option handling outside Claude."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import aeo_check  # noqa: E402
import install_targets  # noqa: E402
import seo_settings  # noqa: E402

ANSWER = " ".join(["Technical SEO is the work of making a site easy to crawl, render and index"] * 3) + "."

GOOD_PAGE = f"""<!doctype html><html lang="en"><head>
<script type="application/ld+json">{json.dumps({"@context": "https://schema.org", "@graph": [
    {"@type": "Article", "author": {"@type": "Person", "name": "A"}, "dateModified": "2026-11-01"},
    {"@type": "Organization", "name": "Example"}]})}</script></head><body><main>
<p>Technical SEO is the practice of helping search engines crawl and index a site.</p>
<h2>Key takeaways</h2><ul><li>Crawl</li><li>Render</li><li>Index</li></ul>
<h2>What is technical SEO?</h2><p>{ANSWER}</p>
<h2>How do you run a technical SEO audit?</h2><ol><li>Crawl the site and list every status code you find there</li>
<li>Check robots.txt and the XML sitemap for blocked or missing pages</li><li>Measure Core Web Vitals in the field and fix the slowest templates first</li></ol>
<h2>Apakah SEO teknis penting?</h2><p>{ANSWER}</p>
<table><tr><th>Tool</th><th>Use</th></tr><tr><td>A</td><td>B</td></tr></table>
<time datetime="2026-11-01">1 Nov</time></main></body></html>"""

THIN_PAGE = """<!doctype html><html><body><main><h2>Our services</h2>
<p>We do many things for many clients across many industries and markets.</p></main></body></html>"""


def test_question_detection_covers_english_and_indonesian() -> None:
    assert aeo_check.is_question("What is AEO?")
    assert aeo_check.is_question("How to write a snippet")
    assert aeo_check.is_question("Bagaimana cara optimasi AEO")
    assert not aeo_check.is_question("Our services")


def test_answer_ready_page_scores_high_and_counts_signals() -> None:
    result = aeo_check.run_checks(GOOD_PAGE, "https://example.com/guide")
    facts = result["facts"]
    assert facts["question_headings"] == 3
    assert facts["concise_answers"] == 3
    assert facts["lists"] >= 1 and facts["tables"] == 1
    assert facts["summary_block"] and facts["definition_opening"]
    assert facts["author_signal"] and facts["date_signal"] and facts["entity_schema"]
    assert {"Article", "Organization"} <= set(result["schema_types"])
    assert result["score"]["label"] == "heuristic"
    assert result["score"]["value"] >= 85
    assert not [f for f in result["findings"] if f["severity"] in ("High", "Medium")]


def test_thin_page_reports_missing_answer_signals() -> None:
    result = aeo_check.run_checks(THIN_PAGE, "https://example.com/")
    ids = {f["id"] for f in result["findings"]}
    assert {"no_question_headings", "no_list_or_table", "no_author_signal", "no_lang"} <= ids
    assert result["score"]["value"] < 30


def test_retired_schema_is_info_not_a_recommendation() -> None:
    page = GOOD_PAGE.replace('"@type": "Organization"', '"@type": "FAQPage"')
    findings = {f["id"]: f for f in aeo_check.run_checks(page, "https://example.com/")["findings"]}
    assert findings["faqpage_present"]["severity"] == "Info"
    assert "2026-05-07" in findings["faqpage_present"]["message"]


def test_file_mode_needs_no_network(tmp_path: Path, capsys) -> None:
    page = tmp_path / "page.html"
    page.write_text(GOOD_PAGE, encoding="utf-8")
    assert aeo_check.main(["--file", str(page), "--base-url", "https://example.com/guide"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["source"] == "file" and out["facts"]["question_headings"] == 3


@pytest.fixture
def isolated_settings(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setenv("AI_AGENT_SEO_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("AI_AGENT_SEO_FOCUS", raising=False)
    return tmp_path


def test_every_profile_sums_to_100() -> None:
    for name, weights in seo_settings.PROFILES.items():
        assert sum(weights) == 100, name
        assert len(weights) == len(seo_settings.CATEGORIES)


def test_focus_precedence(isolated_settings: Path, monkeypatch) -> None:
    assert seo_settings.resolve()["optimization_focus"] == "balanced"
    seo_settings.write_focus("geo")
    assert seo_settings.resolve()["source"] == "settings-file"
    assert seo_settings.resolve(plugin_focus="aeo")["optimization_focus"] == "aeo"
    monkeypatch.setenv("AI_AGENT_SEO_FOCUS", "seo")
    assert seo_settings.resolve(plugin_focus="aeo")["optimization_focus"] == "seo"
    assert seo_settings.resolve(focus="aeo")["source"] == "flag"


def test_unexpanded_or_invalid_values_fall_through(isolated_settings: Path) -> None:
    result = seo_settings.resolve(plugin_focus="${user_config.optimization_focus}")
    assert result["optimization_focus"] == "balanced"
    result = seo_settings.resolve(focus="nonsense")
    assert result["optimization_focus"] == "balanced"
    assert result["ignored_invalid"] == [{"source": "flag", "value": "nonsense"}]


def test_plugin_option_is_declared_and_used_by_skills() -> None:
    manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    option = manifest["userConfig"]["optimization_focus"]
    assert option["options"] == list(seo_settings.FOCUSES)
    assert option["default"] == seo_settings.DEFAULT_FOCUS
    for skill in ("seo", "seo-audit", "seo-aeo", "seo-geo"):
        text = (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
        assert '--plugin-focus "${user_config.optimization_focus}"' in text, skill


def test_installers_blank_plugin_options_outside_claude(tmp_path: Path) -> None:
    plan = install_targets.Plan("agents", tmp_path, None, "x", runtime_home=tmp_path / "seo")
    text = 'run seo_settings.py show --plugin-focus "${user_config.optimization_focus}" --json'
    assert install_targets.rewrite_text(text, plan) == 'run seo_settings.py show --plugin-focus "" --json'
    assert "s#\\${user_config\\.[A-Za-z_][A-Za-z0-9_]*}##g" in (ROOT / "install.sh").read_text(encoding="utf-8")
    assert "user_config" in (ROOT / "install.ps1").read_text(encoding="utf-8")
