"""Generate an offline guide, its figures, and compatibility links."""

from __future__ import annotations

import html
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
from drawing import graph_svg, timeline_svg
from lessons import ALIASES, CHAPTERS, LESSONS
from content.glossary import TERMS

ROOT = Path(__file__).resolve().parent
BY_SLUG = {item["slug"]: item for item in LESSONS}
BY_TITLE = {item["title"]: item["slug"] for item in LESSONS}
TOTAL = len(LESSONS)
SOURCE_MAP = json.loads((ROOT / "data/source-map.json").read_text())
QUESTIONS = {source["source_number"]: source["source_topic"] for source in SOURCE_MAP}
LESSON_FOR_SOURCE = {n: item for item in LESSONS for n in item["sources"]}


def term_id(term):
    return "term-" + re.sub(r"[^a-z0-9]+", "-", term.lower()).strip("-")


# Every alias maps to its glossary entry. Acronyms (any uppercase letter or digit after the first
# character) match case-sensitively; everything else ignores case.
TERM_FOR = {}
_patterns = []
_originals = {}
for _entry in TERMS:
    for _alias in [_entry[0]] + _entry[1]:
        _key = html.escape(_alias, quote=True).lower()   # prose is HTML-escaped before matching
        if _key in TERM_FOR:
            raise ValueError(f"Glossary alias used twice: {_alias}")
        TERM_FOR[_key] = _entry
        _originals[_key] = _alias
for _key in sorted(TERM_FOR, key=len, reverse=True):
    _original = _originals[_key]
    _escaped = re.escape(html.escape(_original, quote=True))
    _patterns.append(_escaped if re.search(r"[A-Z0-9]", _original[1:]) or _original.isupper() else f"(?i:{_escaped})")
TERM_PATTERN = re.compile(r"(?<![\w@-])(" + "|".join(_patterns) + r")(?![\w@-])")
# Per-lesson state: link only the first use of each term, and never in the term's home lesson.
LINKING = {"slug": None, "done": set(), "log": []}


def term_link(match):
    text = match.group(1)
    entry = TERM_FOR[text.lower()]
    term, _, definition, home = entry
    if LINKING["slug"] is None or home == LINKING["slug"] or term in LINKING["done"]:
        return text
    LINKING["done"].add(term)
    LINKING["log"].append((LINKING["slug"], term, text))
    return f'<a class="term" href="../glossary.html#{term_id(term)}" data-def="{esc(definition)}">{text}</a>'


def esc(value):
    return html.escape(str(value), quote=True)


def inline(text):
    parts = re.split(r"(`[^`]+`)", text)
    output = []
    for part in parts:
        if part.startswith("`") and part.endswith("`"):
            output.append(f"<code>{esc(part[1:-1])}</code>")
        else:
            part = esc(part)
            refs = []
            def hold(match):
                refs.append(lesson_link(match))
                return f"\x00{len(refs) - 1}\x00"
            part = re.sub(r"(?<![*\w])\*([^*]+)\*(?![*\w])", hold, part.replace("**", "\x01"))
            part = TERM_PATTERN.sub(term_link, part)
            part = re.sub(r"\x01(.+?)\x01", r"<strong>\1</strong>", part)
            part = re.sub(r"\x00(\d+)\x00", lambda m: refs[int(m.group(1))], part)
            output.append(part)
    return "".join(output)


def lesson_link(match):
    """`*Exact lesson title*` becomes a link to that lesson; anything else is an error."""
    title = html.unescape(match.group(1))
    if title not in BY_TITLE:
        raise ValueError(f"Cross-reference to unknown lesson title: {title!r}")
    return f'<a class="lesson-ref" href="{BY_TITLE[title]}.html">{match.group(1)}</a>'


def prose(text):
    """Paragraphs, `- ` bullet lists, and `1. ` numbered lists."""
    blocks = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [line.strip() for line in block.strip().splitlines()]
        if all(re.match(r"^- ", line) for line in lines):
            blocks.append("<ul>" + "".join(f"<li>{inline(line[2:])}</li>" for line in lines) + "</ul>")
        elif all(re.match(r"^\d+\. ", line) for line in lines):
            blocks.append("<ol>" + "".join(f"<li>{inline(re.sub(r'^\d+\. ', '', line))}</li>" for line in lines) + "</ol>")
        else:
            blocks.append("<p>" + inline(" ".join(lines)) + "</p>")
    return "\n".join(blocks)


def path_for(lesson):
    return f'lessons/{lesson["slug"]}.html'


def credit():
    return '''<footer class="author-credit"><span>Ozan Ciga</span><a href="https://www.linkedin.com/in/ozan-ciga-794300153/" target="_blank" rel="me noreferrer" aria-label="Ozan Ciga on LinkedIn"><svg class="linkedin-icon" width="14" height="14" viewBox="0 0 24 24" aria-hidden="true"><rect width="24" height="24" rx="3" fill="currentColor"/><path fill="#171b18" d="M5 9h3v10H5zm1.5-5a1.7 1.7 0 1 0 0 3.4 1.7 1.7 0 0 0 0-3.4zM10 9h3v1.4c.7-1.1 1.6-1.7 3-1.7 3 0 3.6 1.9 3.6 4.4V19h-3v-5.2c0-1.3 0-2.5-1.6-2.5s-2 1.2-2 2.5V19h-3z"/></svg><span>LinkedIn</span></a><a href="https://ozanciga.wordpress.com/" target="_blank" rel="me noreferrer">Blog <span aria-hidden="true">↗</span></a></footer>'''


def sidebar(prefix, current=None):
    groups = []
    for chapter, (title, _) in enumerate(CHAPTERS, 1):
        links = []
        for item in LESSONS:
            if item["chapter"] != chapter:
                continue
            active = ' aria-current="page"' if item["slug"] == current else ""
            source_numbers = " ".join(str(n) for n in item["sources"])
            search = f'{item["number"]} {item["title"]} {title}'
            links.append(f'<a class="lesson-link" href="{prefix}{path_for(item)}" data-search="{esc(search)}" data-sources="{source_numbers}" data-number="{item["number"]}"{active}><span class="lesson-number">{item["number"]:02d}</span><span>{esc(item["title"])}</span></a>')
        groups.append(f'<div class="nav-chapter"><a class="nav-chapter-title" href="{prefix}index.html#chapter-{chapter:02d}">{chapter:02d} · {esc(title)}</a>{"".join(links)}</div>')
    return f'''<aside class="sidebar" id="sidebar" aria-label="Guide navigation"><div class="brand"><a href="{prefix}index.html"><span class="eyebrow">The field guide</span><span class="brand-title">Agentic System Design</span></a><p>From bounded tasks to reliable systems.</p></div><div class="sidebar-tools"><label class="visually-hidden" for="sidebar-search">Find a topic or lesson number</label><input id="sidebar-search" type="search" placeholder="Find a topic…" autocomplete="off"><div class="list-label"><span>Contents</span><span id="sidebar-count">{TOTAL} lessons</span></div></div><nav class="lesson-list" aria-label="Chapters and lessons">{"".join(groups)}<p id="sidebar-empty" class="empty" hidden>No matching topics.</p></nav><a class="sidebar-footer" href="{prefix}index.html#contents">All chapters <span aria-hidden="true">↗</span></a></aside>'''


def page(title, content, item=None):
    prefix = "../" if item else "./"
    data = f' data-guide-count="{TOTAL}"'
    breadcrumb = '<a class="top-home" href="./index.html">AGENTIC SYSTEM DESIGN</a>'
    page_count = ""
    progress = ""
    if item:
        data += f' data-lesson-slug="{item["slug"]}" data-lesson-number="{item["number"]}"'
        chapter = item["chapter"]
        breadcrumb = f'<a class="top-home top-chapter" href="../index.html#chapter-{chapter:02d}">{chapter:02d} / {esc(CHAPTERS[chapter - 1][0])}</a>'
        page_count = f'<span class="page-count" aria-label="Lesson {item["number"]} of {TOTAL}">{item["number"]:02d} / {TOTAL}</span>'
        progress = f'<div class="progress" aria-hidden="true"><span style="width:{item["number"] / TOTAL * 100:.3f}%"></span></div>'
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#171b18"><title>{esc(title)} · Agentic System Design</title><link rel="stylesheet" href="{prefix}assets/styles.css"><script src="{prefix}assets/app.js" defer></script></head><body data-root="{prefix}"{data}><a class="skip-link" href="#main">Skip to content</a><div class="shell">{sidebar(prefix, item["slug"] if item else None)}<button class="sidebar-backdrop" aria-label="Close contents" tabindex="-1" hidden></button><main id="main"><div class="topbar"><div class="top-left"><button class="menu-button" id="menu-button" aria-label="Open contents" aria-expanded="false" aria-controls="sidebar"><span aria-hidden="true">☰</span></button>{breadcrumb}</div><div class="topbar-actions">{page_count}<a class="source-link" href="{prefix}glossary.html">Glossary</a><a class="source-link" href="{prefix}index.html#contents">Contents <span aria-hidden="true">↗</span></a></div></div>{progress}{content}{credit()}</main></div></body></html>'''


def caption(text, tag="figcaption", cls=""):
    return f'<{tag}{cls}>{inline(text)}</{tag}>' if text else ""


def render_aid(aid, file_key):
    output = []
    if "figure" in aid:
        figure = aid["figure"]
        svg = graph_svg(figure) if figure["kind"] == "graph" else timeline_svg(figure)
        filename = file_key + ".svg"
        (ROOT / "figures" / filename).write_text(svg)
        width = int(re.search(r'width="(\d+)"', svg).group(1))
        height = re.search(r'height="(\d+)"', svg).group(1)
        alt = figure["title"] + (". " + figure["caption"] if figure["caption"] else "")
        output.append(f'''<figure class="learning-figure"><div class="aid-heading"><h3>{esc(figure["title"])}</h3><a class="artifact-link" href="../figures/{filename}" target="_blank" rel="noreferrer">Open figure <span aria-hidden="true">↗</span></a></div><div class="diagram-scroll" tabindex="0" role="region" aria-label="Scrollable diagram"><img src="../figures/{filename}" alt="{esc(alt)}" width="{width}" height="{height}" style="min-width:min({width}px,460px)"></div>{caption(figure["caption"])}</figure>''')
    if "table" in aid:
        table = aid["table"]
        head = "".join(f'<th scope="col">{inline(cell)}</th>' for cell in table["headings"])
        rows = "".join("<tr>" + "".join(f'<th scope="row">{inline(cell)}</th>' if index == 0 else f'<td>{inline(cell)}</td>' for index, cell in enumerate(row)) + "</tr>" for row in table["rows"])
        output.append(f'''<figure class="table-figure"><h3>{esc(table["title"])}</h3><div class="table-scroll" tabindex="0" role="region" aria-label="Scrollable table"><table><caption class="visually-hidden">{esc(table["title"])}</caption><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>{caption(table["caption"])}</figure>''')
    if "code" in aid:
        code = aid["code"]
        output.append(f'''<section class="code-example" aria-labelledby="{file_key}-title"><div class="aid-heading"><div><span class="eyebrow">Pseudocode</span><h3 id="{file_key}-title">{esc(code["title"])}</h3></div><button class="copy-button" type="button" aria-live="polite">Copy</button></div><pre tabindex="0"><code>{esc(code["text"])}</code></pre>{caption(code["caption"], "p", ' class="aid-caption"')}</section>''')
    return "\n".join(output)


def lesson_page(item):
    LINKING["slug"], LINKING["done"] = item["slug"], set()
    number = item["number"]
    chapter = item["chapter"]
    chapter_title = CHAPTERS[chapter - 1][0]
    sections = []
    anchors = []
    for index, section in enumerate(item["sections"], 1):
        section_id = f"step-{index}"
        anchors.append(f'<a href="#{section_id}">{esc(section["title"])}</a>')
        parts, aid_index = [], 0
        for block in section["blocks"]:
            if "text" in block:
                parts.append(f'<div class="answer-content">{prose(block["text"])}</div>')
            else:
                aid_index += 1
                key = f'{item["slug"]}-{index}-{aid_index}'
                parts.append(f'<div class="teaching section-aids">{render_aid(block, key)}</div>')
        sections.append(f'<section class="lesson-section" id="{section_id}" aria-labelledby="{section_id}-title"><h2 id="{section_id}-title">{esc(section["title"])}</h2>{"".join(parts)}</section>')
    references = ""
    if item["references"]:
        refs = "".join(f'<li>{esc(note)} <a href="{esc(url)}" target="_blank" rel="noreferrer">{esc(title)} ↗</a></li>' for title, url, note in item["references"])
        references = f'<details class="references"><summary>References</summary><ul>{refs}</ul></details>'
    related = ""
    if item["related"]:
        links = "".join(f'<a href="{slug}.html">{esc(BY_SLUG[slug]["title"])} <span aria-hidden="true">↗</span></a>' for slug in item["related"])
        related = f'<aside class="related-lessons" aria-label="Connected concepts"><h2>Connected concepts</h2>{links}</aside>'
    previous = LESSONS[number - 2] if number > 1 else None
    following = LESSONS[number] if number < TOTAL else None
    if previous:
        prev = f'<a class="adjacent-card previous" rel="prev" href="{previous["slug"]}.html"><span>← Previous · {previous["number"]:02d}</span><strong>{esc(previous["title"])}</strong></a>'
    else:
        prev = '<a class="adjacent-card previous" href="../index.html"><span>← Contents</span><strong>Browse all chapters</strong></a>'
    if following:
        nxt = f'<a class="adjacent-card next" rel="next" href="{following["slug"]}.html"><span>Next · {following["number"]:02d} →</span><strong>{esc(following["title"])}</strong></a>'
    else:
        nxt = '<a class="adjacent-card next" href="../index.html"><span>Contents →</span><strong>Revisit a chapter</strong></a>'
    questions = [QUESTIONS[n] for n in item["sources"]] + item["questions"]
    asked = "".join(f"<li>{esc(q)}</li>" for q in questions)
    content = f'''<article class="answer-card"><header class="lesson-header"><h1>{esc(item["title"])}</h1><div class="lesson-questions"><span class="eyebrow">{"Questions" if len(questions) > 1 else "Question"} this lesson answers</span><ul>{asked}</ul></div><p class="lesson-summary"><strong>In short.</strong> {inline(item["summary"])}</p><nav class="in-this-lesson" aria-label="In this lesson">{"".join(anchors)}</nav></header>{"".join(sections)}{references}</article>{related}<nav class="adjacent-navigation" aria-label="Previous and next lesson">{prev}{nxt}</nav><p class="keyboard-hint">Use <kbd>←</kbd> and <kbd>→</kbd> to move between lessons.</p>'''
    LINKING["slug"] = None
    return page(item["title"], content, item)


def glossary_page():
    entries = []
    for term, aliases, definition, home in sorted(TERMS, key=lambda e: e[0].lower()):
        lesson = BY_SLUG[home]
        entries.append(f'<div class="glossary-entry" id="{term_id(term)}" data-search="{esc(term + " " + " ".join(aliases) + " " + definition)}"><dt>{esc(term)}</dt><dd>{esc(definition)} <a class="lesson-ref" href="{path_for(lesson)}">Explained in: {esc(lesson["title"])}</a></dd></div>')
    content = f'''<header class="library-header"><h1>Glossary</h1><p>One plain definition per term. In lessons, the first use of a term is underlined; hover to see its definition, or click to come here.</p></header><dl class="glossary">{"".join(entries)}</dl>'''
    return page("Glossary", content)


def search_text(item):
    text = f'{item["number"]} {item["title"]} {item["summary"]} {CHAPTERS[item["chapter"] - 1][0]}'
    text += " " + " ".join([QUESTIONS[n] for n in item["sources"]] + item["questions"])
    for section in item["sections"]:
        text += f' {section["title"]}'
        for block in section["blocks"]:
            text += ' ' + (block["text"] if "text" in block else json.dumps(block, ensure_ascii=False))
    return text


def aid_labels(item):
    kinds = {kind for section in item["sections"] for block in section["blocks"] for kind in block}
    return [label for kind, label in [("figure", "Diagrams"), ("table", "Tables"), ("code", "Pseudocode")] if kind in kinds]


def index_page():
    chapters = []
    jump_links = []
    for chapter, (title, description) in enumerate(CHAPTERS, 1):
        jump_links.append(f'<a href="#chapter-{chapter:02d}"><span>{chapter:02d}</span>{esc(title)}</a>')
        items = []
        for item in LESSONS:
            if item["chapter"] != chapter:
                continue
            labels = " · ".join(aid_labels(item))
            meta = f'<small>{esc(labels)}</small>' if labels else ""
            source_numbers = " ".join(str(n) for n in item["sources"])
            items.append(f'<li class="directory-item" data-search="{esc(search_text(item))}" data-number="{item["number"]}" data-sources="{source_numbers}"><a href="{path_for(item)}"><span class="directory-number">{item["number"]:02d}</span><span class="directory-text">{esc(item["title"])}{meta}</span><span class="directory-arrow" aria-hidden="true">↗</span></a></li>')
        chapters.append(f'<section class="topic-section" id="chapter-{chapter:02d}"><h2><span>{chapter:02d}</span>{esc(title)}</h2><p class="chapter-description">{esc(description)}</p><ol class="directory-list">{"".join(items)}</ol></section>')
    intro = f'''<header class="library-header"><h1>Agentic System Design</h1><p>Build from a bounded task to a system that can act, recover, and be evaluated. Follow the chapters in order, or revisit a concept when you need it.</p><a class="resume-link" id="resume-link" href="{path_for(LESSONS[0])}">Start reading <span aria-hidden="true">→</span></a></header><details class="chapter-jump"><summary>Jump to a chapter <span>{len(CHAPTERS)}</span></summary><nav class="chapter-overview" aria-label="Learning path">{"".join(jump_links)}</nav></details><div class="directory-tools" id="contents"><label for="directory-search">Find a concept</label><input id="directory-search" type="search" placeholder="Search explanations, examples, or lesson numbers…" autocomplete="off"><div class="search-status" id="directory-count" role="status">{TOTAL} lessons · {len(CHAPTERS)} chapters</div></div><p class="empty" id="directory-empty" hidden>No matches. Try a broader term.</p>'''
    return page("Contents", intro + "".join(chapters))


def redirect(destination, title):
    # Ordinary relative URLs preserve compatibility with direct file:// use.
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0; url={destination}"><meta name="theme-color" content="#171b18"><title>{esc(title)}</title><style>:root{{color-scheme:dark}}body{{background:#171b18;color:#e8e9e5;font:15px/1.6 system-ui;padding:8vh 24px;max-width:650px;margin:auto}}a{{color:#a7cbb2}}</style></head><body><p><a href="{destination}">Continue to {esc(title)} →</a></p><script>location.replace({json.dumps(destination)});</script></body></html>'''


def validate_content():
    if len(BY_SLUG) != TOTAL:
        raise ValueError("Lesson slugs must be unique.")
    if sorted(n for item in LESSONS for n in item["sources"]) != list(range(1, 161)):
        raise ValueError("Each source entry must be assigned exactly once.")
    for term, _, _, home in TERMS:
        if home not in BY_SLUG:
            raise ValueError(f"Glossary term {term!r} points to unknown lesson {home!r}")
    for old, new in ALIASES.items():
        if old in BY_SLUG or new not in BY_SLUG:
            raise ValueError(f"Bad alias {old} -> {new}")
    for item in LESSONS:
        if not item["sections"] or not item["reason"]:
            raise ValueError("Every lesson needs content and an editorial rationale.")
        if not all(isinstance(section, dict) and section["blocks"] for section in item["sections"]):
            raise ValueError(f"{item['slug']}: every section must be a non-empty section() call.")
        if not item["sources"] and not item["questions"]:
            raise ValueError(f"{item['slug']} needs at least one question.")
        for slug in item["related"]:
            if slug not in BY_SLUG:
                raise ValueError(f"Missing related lesson: {slug}")


def main():
    validate_content()
    for folder in ("lessons", "questions", "figures", "assets", "data"):
        (ROOT / folder).mkdir(exist_ok=True)
    # These are owned generated artifacts; source text and shared assets are retained.
    for artifact in (ROOT / "figures").glob("*.svg"):
        artifact.unlink()
    for artifact in (ROOT / "lessons").glob("*.html"):
        artifact.unlink()
    for item in LESSONS:
        (ROOT / path_for(item)).write_text(lesson_page(item))
    for old, new in ALIASES.items():
        (ROOT / f"lessons/{old}.html").write_text(redirect(f"{new}.html", BY_SLUG[new]["title"]))
    (ROOT / "index.html").write_text(index_page())
    (ROOT / "glossary.html").write_text(glossary_page())
    (ROOT / "data/term-links.txt").write_text("".join(f"{slug}\t{term}\t{text}\n" for slug, term, text in LINKING["log"]))
    review = []
    for source in SOURCE_MAP:
        item = LESSON_FOR_SOURCE[source["source_number"]]
        source["lesson_slug"] = item["slug"]
        review.append(dict(**source, lesson_number=item["number"],
            action="merged" if len(item["sources"]) > 1 else "expanded_and_reordered",
            rationale=item["reason"], destination=path_for(item)))
        (ROOT / f'questions/{source["source_number"]:03d}.html').write_text(redirect("../" + path_for(item), item["title"]))
    (ROOT / "data/source-map.json").write_text(json.dumps(SOURCE_MAP, ensure_ascii=False, indent=2) + "\n")
    (ROOT / "data/lessons.json").write_text(json.dumps(LESSONS, ensure_ascii=False, indent=2) + "\n")
    (ROOT / "data/review.json").write_text(json.dumps(dict(
        source_entries_reviewed=len(review), lessons=TOTAL, chapters=len(CHAPTERS),
        approach="Order by prerequisites; merge repeated concepts; answer each source question directly with a concrete example; keep a figure, table, or pseudocode block only where it adds information the prose does not.",
        added_questions=[dict(lesson=item["slug"], questions=item["questions"]) for item in LESSONS if item["questions"]],
        merged_lessons=[dict(old_slug=old, lesson=new) for old, new in ALIASES.items()],
        decisions=review,
    ), ensure_ascii=False, indent=2) + "\n")
    aid_counts = {kind: sum(kind in aid for item in LESSONS for section in item["sections"] for aid in section["blocks"]) for kind in ("figure", "table", "code")}
    print(f"Built {TOTAL} lessons in {len(CHAPTERS)} chapters; {len(review)} source entries reviewed; {aid_counts}")


if __name__ == "__main__":
    main()
