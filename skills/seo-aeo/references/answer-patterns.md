# Answer patterns for AEO

Reference for `seo-aeo`. Pick the answer format from the question, put the
answer first, then support it. Formats below are observed conventions of
answer surfaces, not published ranking rules.

## Match the format to the question

| Question shape | Best answer format | Example opening |
|---|---|---|
| What is / apa itu | One-sentence definition, then 1-2 supporting sentences | "Technical SEO is the work of ..." |
| How to / bagaimana cara | Numbered steps (3-8), each starting with a verb | "1. Open Search Console ..." |
| Best / top / options | Bulleted list with one line per item | "- Option A: best for ..." |
| X vs Y / comparison | Table with a header row, then a one-line verdict | Table: feature, X, Y |
| How much / berapa | The number or range first, then what changes it | "Most audits take 2-4 weeks ..." |
| Why / mengapa | Direct reason first, then evidence | "Because Google ..." |
| Can / does / is (yes-no) | "Yes" or "No" first, then the condition | "Yes, if ..." |

## Answer-first passage checklist

- The heading states the question in the user's words (from People Also Ask
  or related searches).
- The first block under it answers the question on its own, without needing
  the paragraph before it. Aim for roughly 25-70 words for a paragraph answer
  (display heuristic).
- Name the subject instead of "it" or "this", so the passage stands alone when
  quoted.
- Put qualifiers after the answer, not before it.
- Use one idea per paragraph; lists and tables for steps, options and
  comparisons.

## Page-level signals

- A short summary or key-takeaways block near the top.
- An opening sentence that defines the topic.
- A visible author and a published or updated date; Organization or Person
  structured data for the entity behind the answer.
- Fast, crawlable HTML: answers rendered only after interaction may not be read.

## Structured data status (check before recommending)

| Type | Status for answers |
|---|---|
| QAPage | Supported for genuine single-question community pages |
| Article family | Supports author and date signals |
| FAQPage | No Google rich result for any site since 2026-05-07; do not add for SERP benefit |
| HowTo | Rich results removed September 2023 |
| Speakable | Beta, eligible news content only |

Source of truth for dates: `${CLAUDE_PLUGIN_ROOT}/skills/seo/references/schema-types.md`.

## Voice assistants

Voice answers read one short passage. Keep spoken answers to one or two plain
sentences, avoid tables for the spoken part, and expand the abbreviations a
listener would not parse.

## Primary sources

- Featured snippets: https://developers.google.com/search/docs/appearance/featured-snippets
- QAPage structured data: https://developers.google.com/search/docs/appearance/structured-data/qapage
- Speakable structured data: https://developers.google.com/search/docs/appearance/structured-data/speakable
