"""Helpers used by the chapter files in content/ to declare lessons and their teaching aids.

Writing rules for content:
- A lesson answers its source questions. `summary` is the "In short" answer shown first.
- Define each necessary term once, in plain words, in the lesson that teaches it, and add it to
  content/glossary.py. Elsewhere, just use the term; the renderer links it to its definition.
- Don't repeat another lesson's explanation; link to it with *Exact lesson title*.
- Prose is plain Markdown-like text: paragraphs, `- ` bullet lists, `1. ` numbered lists, **bold**, `code`.
- Add an aid only when it shows something the prose cannot: branching, timing, a worked example,
  or the exact order of checks. A diagram that repeats a sentence as boxes is not worth its space.
"""

import textwrap


def lesson(slug, title, sources, summary, sections, reason, *, questions=(), related=(), references=()):
    """`sources` are original question numbers; `questions` adds questions for lessons without a source."""
    return dict(slug=slug, title=title, sources=list(sources), summary=summary, sections=sections,
                reason=reason, questions=list(questions), related=list(related), references=list(references))


def section(title, *parts):
    """Prose strings and aids, rendered in the order given."""
    blocks = []
    for part in parts:
        if isinstance(part, str):
            if part.strip():
                blocks.append({"text": textwrap.dedent(part).strip()})
        else:
            blocks.append(part)
    return dict(title=title, blocks=blocks)


def code(title, text, caption=""):
    return {"code": dict(title=title, text=textwrap.dedent(text).strip(), caption=caption)}


def table(title, headings, rows, caption=""):
    return {"table": dict(title=title, headings=headings, rows=rows, caption=caption)}


def flow(title, nodes, edges, caption=""):
    """nodes: (key, column, row, "Heading\\ndetail"[, "start"|"good"|"bad"]); edges: (a, b, label[, "bad"])."""
    return {"figure": dict(kind="graph", title=title, nodes=nodes, edges=edges, caption=caption)}


def timeline(title, tracks, caption="", markers=(), unit="s"):
    """tracks: (label, [(start, stop, text[, style]), ...]); markers: [(time, label)]."""
    return {"figure": dict(kind="timeline", title=title, tracks=tracks, caption=caption,
                           markers=list(markers), unit=unit)}
