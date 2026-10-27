# Agentic System Design

Open **index.html** in a browser. The guide works offline, with no installation, server, or build step. Keep the folder together so the shared assets and figures stay available.

A tutorial on designing AI agent systems: **79 lessons** in **13 chapters**, in the order you need them, from deciding whether you need an agent at all, through tools, recovery, retrieval, evaluation, memory, and multi-agent designs, to operations, worked case studies, and platform decisions.

## How a lesson reads

Each lesson opens with the questions it answers and an **In short** summary. The sections that follow explain the details, using a running example where it helps: a customer asking for $80 back on order 42.

Technical terms are defined once, in plain words, in the lesson that teaches them and in **glossary.html**. In every other lesson, a term's first use is underlined: hover to see its definition, or click to open the glossary.

A teaching aid appears only where it adds something the prose cannot:

- **Tables** (58) compare options, show worked numbers, or summarize a design.
- **Pseudocode** (51) shows the exact order of checks. It uses abstract helpers and is not production code.
- **Figures** (9) are kept only for timing (crash windows, deadlines, stale workers, tail latency) and for real branching (the reference architecture, the task state machine, the refund paths, the tool gateway).

Numbers, prices, and timings in examples are illustrative.

## Files

```text
index.html                     Searchable chapter and lesson index
glossary.html                  Every technical term, defined once
lessons/                       One page per lesson, plus redirects for merged lessons
questions/001.html … 160.html  Redirects from each original question to its lesson
figures/                       Generated SVG figures
assets/styles.css, app.js      Shared styles, search, navigation, reading progress
content/chNN_*.py              Lesson content: one file per chapter, aids defined inline
content/glossary.py            Term definitions, each tied to the lesson that teaches it
authoring.py                   Helpers used by the content files, plus the writing rules
lessons.py                     Chapter order, numbering, and aliases for merged lessons
drawing.py                     Standard-library SVG rendering for figures and timelines
render_guide.py                Page, index, redirect, and audit generation
build.py                       Build entry point
data/source-map.json           The 160 original questions and the lesson that answers each
data/lessons.json              Generated: complete lesson content
data/review.json               Generated: audit of every source question's destination
data/term-links.txt            Generated: every place a glossary term was linked, for review
```

## Editing

Change a file in `content/` (or `authoring.py`, `drawing.py`, or the assets), then run:

```sh
python3 build.py
```

The build rejects some mistakes outright: a source question that is unassigned or assigned twice, a broken related-lesson link, a `*Lesson title*` cross-reference that matches no lesson, a glossary term tied to a missing lesson, and a timeline label too long for its bar.

In prose, `*Exact lesson title*` becomes a link to that lesson. Paragraphs, `- ` bullets, `1. ` numbered lists, `**bold**`, and `` `code` `` are supported.

