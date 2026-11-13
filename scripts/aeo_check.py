#!/usr/bin/env python3
"""
Deterministic Answer Engine Optimization (AEO) checks for one page.

AEO is the work of making a page easy to lift as a direct answer: featured
snippets, People Also Ask, voice assistants, and the answer boxes of AI search.
This script measures the on-page signals an answer engine can see, so the agent
that calls it explains findings instead of counting them by hand:

* question-shaped headings (English and Indonesian interrogatives, or a "?")
* whether the first block under each question answers it concisely
* list and table formats, a summary block and a definitional opening sentence
* author, date and entity signals (Organization / Person)
* answer-related JSON-LD: QAPage, Article family, speakable, FAQPage, HowTo

The 0-100 score is a heuristic of this project, not a search engine metric.
Search engines publish no answer-length rule; the 25-70 word "concise answer"
band is a display heuristic, and the messages say so.

Schema facts follow skills/seo/references/schema-types.md: FAQPage rich
results were retired for all sites on 2026-05-07, HowTo rich results were
removed in September 2023, and Speakable is still labelled beta.

Usage:
    python aeo_check.py --url https://example.com/page
    python aeo_check.py --file page.html --base-url https://example.com/page

``--url`` fetches through fetch_page.py (url_safety SSRF protection).
``--file`` reads a saved document and makes no network request.

Output (JSON on stdout)::

    {
      "url": "...", "source": "url" | "file", "status_code": 200 | null,
      "facts": {"question_headings": 4, "concise_answers": 3, ...},
      "questions": [{"heading": "What is ...?", "answer_words": 48, "concise": true}],
      "schema_types": ["Article", "Organization"],
      "score": {"value": 72, "max": 100, "label": "heuristic", "breakdown": {...}},
      "findings": [{"id": "...", "severity": "High", "message": "...", "evidence": "..."}]
    }
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Iterable, Optional

from bs4 import BeautifulSoup

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_FILE_BYTES = 10 * 1024 * 1024
CONCISE_MIN_WORDS = 25
CONCISE_MAX_WORDS = 70
EVIDENCE_MAX_CHARS = 140

try:  # lxml is faster and forgiving; html.parser keeps the script usable without it.
    import lxml  # noqa: F401

    _HTML_PARSER = "lxml"
except ImportError:  # pragma: no cover - depends on the environment
    _HTML_PARSER = "html.parser"

INTERROGATIVES = (
    # English
    "what", "why", "how", "when", "where", "who", "whom", "whose", "which",
    "can", "could", "does", "do", "did", "is", "are", "was", "were", "should",
    "will", "would", "may", "must",
    # Indonesian
    "apa", "apakah", "mengapa", "kenapa", "bagaimana", "kapan", "dimana",
    "di mana", "siapa", "berapa", "bisakah", "haruskah", "manakah",
)
SUMMARY_HINTS = re.compile(
    r"\b(tl;?dr|summary|key takeaways?|in short|at a glance|ringkasan|intisari|poin penting|kesimpulan)\b",
    re.IGNORECASE,
)
SUMMARY_CLASS_HINTS = re.compile(r"(tldr|summary|takeaway|ringkasan|key-points)", re.IGNORECASE)
DEFINITION_RE = re.compile(r"\b(is|are|refers to|means|adalah|merupakan|ialah|yaitu)\b", re.IGNORECASE)
ARTICLE_TYPES = {"Article", "BlogPosting", "NewsArticle", "TechArticle", "Report", "ScholarlyArticle"}
ENTITY_TYPES = {"Organization", "Person", "LocalBusiness", "Corporation", "NewsMediaOrganization"}


class _InputError(Exception):
    def __init__(self, message: str, code: int = 1):
        super().__init__(message)
        self.code = code


def _trim(value: object, limit: int = EVIDENCE_MAX_CHARS) -> str:
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _words(text: str) -> int:
    return len(re.findall(r"\w+", text, flags=re.UNICODE))


def is_question(text: str) -> bool:
    """True for headings shaped like a question in English or Indonesian."""
    clean = text.strip().lower()
    if not clean:
        return False
    if clean.endswith("?"):
        return True
    return any(clean == word or clean.startswith(word + " ") for word in INTERROGATIVES)


def _jsonld_nodes(soup) -> Iterable[dict]:
    for script in soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)}):
        try:
            data = json.loads(script.string or script.get_text() or "")
        except (ValueError, TypeError):
            continue
        stack = [data]
        while stack:
            item = stack.pop()
            if isinstance(item, list):
                stack.extend(item)
            elif isinstance(item, dict):
                yield item
                for value in item.values():
                    if isinstance(value, (dict, list)):
                        stack.append(value)


def _types_of(node: dict) -> list[str]:
    value = node.get("@type")
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str)]
    return []


def _first_answer_block(heading) -> str:
    """Text of the first paragraph-like block after a heading, before the next heading."""
    for element in heading.find_all_next():
        if element.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            return ""
        if element.name in {"p", "dd"}:
            text = element.get_text(" ", strip=True)
            if text:
                return text
        if element.name in {"ul", "ol"}:
            items = [li.get_text(" ", strip=True) for li in element.find_all("li")]
            text = " ".join(i for i in items if i)
            if text:
                return text
    return ""


def run_checks(html: str, page_url: str) -> dict:
    soup = BeautifulSoup(html, _HTML_PARSER)
    html_tag = soup.find("html")
    lang = (html_tag.get("lang") or "").strip() if html_tag else ""

    nodes = list(_jsonld_nodes(soup))
    schema_types = sorted({t for node in nodes for t in _types_of(node)})
    has_speakable = any("speakable" in node for node in nodes)
    has_author_schema = any("author" in node for node in nodes)
    has_date_schema = any(("dateModified" in node or "datePublished" in node) for node in nodes)

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup

    questions = []
    for heading in main.find_all(["h2", "h3", "h4"]):
        text = heading.get_text(" ", strip=True)
        if not is_question(text):
            continue
        answer = _first_answer_block(heading)
        words = _words(answer)
        questions.append({
            "heading": _trim(text, 120),
            "answer_words": words,
            "concise": CONCISE_MIN_WORDS <= words <= CONCISE_MAX_WORDS,
        })

    lists = [el for el in main.find_all(["ul", "ol"]) if len(el.find_all("li", recursive=False)) >= 3
             and not el.find_parent(["nav", "footer", "header"])]
    tables = [t for t in main.find_all("table") if t.find("th")]
    headings_text = " ".join(h.get_text(" ", strip=True) for h in main.find_all(["h2", "h3", "h4", "strong"]))
    summary = bool(SUMMARY_HINTS.search(headings_text)) or any(
        SUMMARY_CLASS_HINTS.search(" ".join(el.get("class", [])) + " " + (el.get("id") or ""))
        for el in main.find_all(True)
    )
    first_p = next((p.get_text(" ", strip=True) for p in main.find_all("p") if _words(p.get_text()) >= 8), "")
    first_sentence = re.split(r"(?<=[.!?])\s", first_p, maxsplit=1)[0] if first_p else ""
    definition = bool(first_sentence) and bool(DEFINITION_RE.search(first_sentence)) and _words(first_sentence) <= 40

    author = has_author_schema or bool(soup.find(attrs={"rel": "author"})) or bool(
        soup.find(class_=re.compile(r"(author|byline|penulis)", re.I)))
    dated = has_date_schema or bool(soup.find("time")) or bool(
        soup.find("meta", attrs={"property": re.compile(r"article:(modified|published)_time")}))
    entity = bool(ENTITY_TYPES & set(schema_types))
    article = bool(ARTICLE_TYPES & set(schema_types))
    qapage = "QAPage" in schema_types

    concise_count = sum(1 for q in questions if q["concise"])
    breakdown = {
        "question_coverage": round(min(len(questions), 5) / 5 * 25),
        "concise_answers": round((concise_count / len(questions)) * 25) if questions else 0,
        "answer_formats": (8 if lists else 0) + (7 if tables else 0),
        "summary_and_definition": (5 if summary else 0) + (5 if definition else 0),
        "trust_and_entity": (5 if author else 0) + (5 if dated else 0) + (5 if entity else 0),
        "answer_schema": (7 if (article or qapage) else 0) + (3 if has_speakable else 0),
    }

    findings = []

    def add(check_id: str, severity: str, message: str, evidence: str = "") -> None:
        findings.append({"id": check_id, "severity": severity, "message": message, "evidence": _trim(evidence)})

    if not questions:
        add("no_question_headings", "High",
            "No question-shaped H2-H4 headings. Answer engines match user questions; phrase key sections "
            "as the questions people ask (for example from People Also Ask).")
    elif len(questions) < 3:
        add("few_question_headings", "Medium",
            f"Only {len(questions)} question heading(s). Cover the main follow-up questions of the topic.",
            "; ".join(q["heading"] for q in questions))
    long_or_missing = [q for q in questions if not q["concise"]]
    if long_or_missing:
        add("answers_not_concise", "High" if len(long_or_missing) == len(questions) else "Medium",
            f"{len(long_or_missing)} of {len(questions)} question(s) are not followed by a concise "
            f"{CONCISE_MIN_WORDS}-{CONCISE_MAX_WORDS} word answer (display heuristic). Put a direct answer "
            "first, then the detail.",
            "; ".join(f"{q['heading']} ({q['answer_words']} words)" for q in long_or_missing[:3]))
    if not lists and not tables:
        add("no_list_or_table", "Medium",
            "No list (3+ items) or table with headers in the main content. Steps, options and comparisons "
            "are easier to quote as lists and tables.")
    if not summary:
        add("no_summary_block", "Low", "No summary or key-takeaways block. A short summary near the top gives "
            "answer engines a self-contained passage.")
    if not definition:
        add("no_definition_opening", "Low", "The opening sentence does not define the topic. Start with a "
            "plain 'X is ...' sentence.", first_sentence)
    if not author:
        add("no_author_signal", "Medium", "No author byline or author in structured data.")
    if not dated:
        add("no_date_signal", "Medium", "No published or modified date (time element, meta or JSON-LD).")
    if not entity:
        add("no_entity_schema", "Low", "No Organization or Person structured data to anchor the entity "
            "behind the answer.")
    if "FAQPage" in schema_types:
        add("faqpage_present", "Info", "FAQPage markup found. Google retired FAQ rich results for all sites on "
            "2026-05-07; keep it if it is accurate, but do not expect a SERP feature. Use QAPage only for "
            "genuine single-question community pages.")
    if "HowTo" in schema_types:
        add("howto_present", "Info", "HowTo markup found. Google removed HowTo rich results in September 2023.")
    if has_speakable:
        add("speakable_present", "Info", "speakable markup found. Google still labels Speakable beta and "
            "limits it to eligible news content.")
    if not lang:
        add("no_lang", "Low", "The html element has no lang attribute; answer engines use it to match the "
            "query language.")

    facts = {
        "lang": lang,
        "word_count": _words(main.get_text(" ", strip=True)),
        "question_headings": len(questions),
        "concise_answers": concise_count,
        "lists": len(lists),
        "tables": len(tables),
        "summary_block": summary,
        "definition_opening": definition,
        "author_signal": author,
        "date_signal": dated,
        "entity_schema": entity,
        "speakable": has_speakable,
    }
    return {
        "url": page_url,
        "facts": facts,
        "questions": questions[:30],
        "schema_types": schema_types,
        "score": {"value": sum(breakdown.values()), "max": 100, "label": "heuristic", "breakdown": breakdown},
        "findings": findings,
    }


def _decode(raw: bytes) -> str:
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _from_file(path: str, base_url: Optional[str]) -> dict:
    if not base_url or not re.match(r"^https?://", base_url, re.I):
        raise _InputError("--file needs --base-url, the http(s) address the page is published at", 2)
    try:
        with open(path, "rb") as handle:
            raw = handle.read(MAX_FILE_BYTES + 1)
    except OSError as exc:
        raise _InputError(f"cannot read --file: {exc}") from exc
    if len(raw) > MAX_FILE_BYTES:
        raise _InputError(f"--file is larger than {MAX_FILE_BYTES} bytes")
    result = run_checks(_decode(raw), base_url)
    return {"url": result.pop("url"), "source": "file", "status_code": None, **result}


def _from_url(url: str, timeout: int) -> dict:
    if _SCRIPTS_DIR not in sys.path:
        sys.path.insert(0, _SCRIPTS_DIR)
    from fetch_page import fetch_page  # SSRF-safe fetch: url_safety validates and pins DNS

    page = fetch_page(url, timeout=timeout)
    if page.get("error"):
        raise _InputError(str(page["error"]))
    status = page.get("status_code")
    if page.get("content") is None or (isinstance(status, int) and status >= 400):
        raise _InputError(f"HTTP {status} from {page.get('url')}: no page to check")
    result = run_checks(page["content"], page["url"])
    return {"url": result.pop("url"), "source": "url", "status_code": status, **result}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic AEO (answer engine) checks. JSON on stdout.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="Page to fetch and check (fetched through fetch_page.py).")
    source.add_argument("--file", help="Saved HTML file to check. No network request is made.")
    parser.add_argument("--base-url", help="With --file: the URL the page is published at.")
    parser.add_argument("--timeout", type=int, default=30, help="With --url: timeout in seconds (default 30).")
    parser.add_argument("--json", action="store_true", help="Accepted for consistency. Output is always JSON.")
    args = parser.parse_args(argv)
    try:
        if args.file:
            result = _from_file(args.file, args.base_url)
        else:
            if args.base_url:
                raise _InputError("--base-url applies to --file only", 2)
            result = _from_url(args.url, args.timeout)
    except _InputError as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return exc.code
    except RecursionError:
        print(json.dumps({"error": "the document is nested too deeply to parse"}, indent=2))
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
