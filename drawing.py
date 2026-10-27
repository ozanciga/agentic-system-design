"""Dependency-free SVG rendering for the guide diagrams.

Figures are drawn at their natural size; the page never stretches them.
"""
import html
import textwrap

NODE_W = 168
FONT = "Inter, system-ui, -apple-system, sans-serif"
# Node styles: default, "start" (entry point), "good" (desired outcome), "bad" (blocked or failure).
STYLES = {
    None: ("#242b27", "#4c5b51"),
    "start": ("#26332b", "#5e806a"),
    "good": ("#24382b", "#6fa27e"),
    "bad": ("#3a2b25", "#b48869"),
}


def esc(value):
    return html.escape(str(value), quote=True)


def svg_shell(width, height, title, description, body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">{esc(title)}</title><desc id="desc">{esc(description)}</desc>
<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 1 1 L 9 5 L 1 9" fill="none" stroke="#9bc4ad" stroke-width="1.6"/></marker>
<marker id="arrow-bad" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 1 1 L 9 5 L 1 9" fill="none" stroke="#c99a78" stroke-width="1.6"/></marker></defs>
<rect width="100%" height="100%" rx="10" fill="#1b201d"/>
<g font-family="{FONT}">{body}</g></svg>'''


def svg_lines(lines, x, y, size, fill, weight=400, anchor="middle", line_height=None):
    line_height = line_height or size + 4
    return "".join(
        f'<text x="{x:.1f}" y="{y + i * line_height:.1f}" text-anchor="{anchor}" font-size="{size}" font-weight="{weight}" fill="{fill}">{esc(line)}</text>'
        for i, line in enumerate(lines)
    )


def label_width(text):
    return len(text) * 5.9 + 12


def node_lines(text):
    heading, _, detail = text.partition("\n")
    headings = textwrap.wrap(heading, 22, break_long_words=False) or [""]
    details = textwrap.wrap(detail, 27, break_long_words=False) if detail else []
    return headings, details


def graph_svg(figure):
    """Grid-placed boxes joined by orthogonal arrows.

    nodes: (key, column, row, "Heading\\ndetail"[, style])
    edges: (source, target, label[, "bad"])
    """
    nodes = [tuple(n) + (None,) * (5 - len(n)) for n in figure["nodes"]]
    edges = [tuple(e) + (None,) * (4 - len(e)) for e in figure["edges"]]
    texts = {key: node_lines(text) for key, _, _, text, _ in nodes}
    node_h = max(46, max(len(h) * 17 + (6 if d else 0) + len(d) * 15 + 20 for h, d in texts.values()))
    cell = {key: (col, row) for key, col, row, _, _ in nodes}
    horizontal_labels = [label_width(label) for a, b, label, _ in edges if label and cell[a][1] == cell[b][1]]
    gap_x = max(54, max(horizontal_labels, default=0) + 18)
    gap_y = 50 if any(label and cell[a][0] == cell[b][0] for a, b, label, _ in edges) else 40
    dx, dy, margin = NODE_W + gap_x, node_h + gap_y, 18
    max_col = max(n[1] for n in nodes)
    max_row = max(n[2] for n in nodes)
    width = int(2 * margin + max_col * dx + NODE_W)
    height = int(2 * margin + max_row * dy + node_h)
    pos = {key: (margin + col * dx, margin + row * dy) for key, (col, row) in cell.items()}
    pairs = {(a, b) for a, b, _, _ in edges}
    paths, labels, boxes = [], [], []
    for source, target, label, style in edges:
        sx, sy = pos[source]
        tx, ty = pos[target]
        reverse = (target, source) in pairs
        if sx != tx:
            right = tx > sx
            x1 = sx + NODE_W if right else sx
            x2 = tx if right else tx + NODE_W
            y1, y2 = sy + node_h / 2, ty + node_h / 2
            if sy != ty:
                # Leave from the lower or upper part of the side so this edge never merges
                # with a horizontal arrow entering the same side at mid-height.
                y1 = sy + node_h * (0.74 if ty > sy else 0.26)
            if reverse and sy == ty:
                y1 += -9 if right else 9
                y2 += -9 if right else 9
            mid = (x1 + x2) / 2
            d = f"M {x1} {y1} H {mid} V {y2} H {x2}"
            lx, ly = mid, (y1 - 8 if sy == ty else (y1 + y2) / 2)
            if reverse and sy == ty:
                ly = y1 - 8 if right else y1 + 15
        else:
            down = ty > sy
            x1 = x2 = sx + NODE_W / 2 + ((-12 if down else 12) if reverse else 0)
            y1 = sy + node_h if down else sy
            y2 = ty if down else ty + node_h
            d = f"M {x1} {y1} V {y2}"
            lx, ly = x1 + (-1 if reverse and down else 1) * (label_width(label or "") / 2 + 6), (y1 + y2) / 2 + 4
        bad = style == "bad"
        stroke = "#c99a78" if bad else "#9bc4ad"
        dash = ' stroke-dasharray="5 4"' if bad else ""
        marker = "arrow-bad" if bad else "arrow"
        paths.append(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-opacity=".85" stroke-width="1.5"{dash} marker-end="url(#{marker})"/>')
        if label:
            w = label_width(label)
            labels.append(f'<rect x="{lx - w / 2:.1f}" y="{ly - 11:.1f}" width="{w:.1f}" height="16" rx="4" fill="#1b201d"/>')
            labels.append(svg_lines([label], lx, ly + 1, 10.5, "#d1a585" if bad else "#abb6ae"))
    for key, _, _, _, style in nodes:
        x, y = pos[key]
        fill, stroke = STYLES[style]
        boxes.append(f'<rect x="{x}" y="{y}" width="{NODE_W}" height="{node_h}" rx="9" fill="{fill}" stroke="{stroke}"/>')
        headings, details = texts[key]
        total = len(headings) * 17 + (6 if details else 0) + len(details) * 15
        first = y + (node_h - total) / 2 + 12
        boxes.append(svg_lines(headings, x + NODE_W / 2, first, 13, "#e4ebe4", 600, line_height=17))
        if details:
            boxes.append(svg_lines(details, x + NODE_W / 2, first + len(headings) * 17 + 6, 11, "#b0bcb2", line_height=15))
    description = "; ".join(t.replace("\n", ": ") for _, _, _, t, _ in nodes)
    description += ". Connections: " + "; ".join(f"{a} to {b}" + (f" ({label})" if label else "") for a, b, label, _ in edges)
    return svg_shell(width, height, figure["title"], description, "".join(paths + boxes + labels))


def timeline_svg(figure):
    """Horizontal bars on a shared time axis.

    tracks: (label, [(start, stop, text[, "bad"|"good"]), ...])
    markers: optional [(time, label)] vertical reference lines, e.g. a deadline.
    """
    tracks = figure["tracks"]
    markers = figure.get("markers", [])
    unit = figure.get("unit", "s")
    label_w = 12 + max(len(label) for label, _ in tracks) * 6.4
    left, top, row = label_w + 8, 30, 34
    end = max(stop for _, blocks in tracks for block in blocks for stop in [block[1]])
    end = max([end] + [t for t, _ in markers])
    scale = max(34, min(56, 520 / end))
    right_pad = max([24] + [len(text) * 3.4 + 10 for _, text in markers])
    width = int(left + end * scale + right_pad)
    height = top + len(tracks) * row + (22 if markers else 8)
    body = []
    step = 1 if end <= 12 else 2 if end <= 24 else 5
    for tick in range(0, end + 1, step):
        x = left + tick * scale
        body.append(f'<path d="M{x:.1f} {top - 6} V{top + len(tracks) * row}" stroke="#2e3830" stroke-dasharray="2 4"/>')
        body.append(svg_lines([f"{tick}{unit if tick == end else ''}"], x, top - 11, 10, "#8f9a90"))
    fills = {None: "#344f3e", "alt": "#3b443a", "bad": "#64402b", "good": "#2f5a3e"}
    for i, (label, blocks) in enumerate(tracks):
        y = top + i * row + 4
        body.append(svg_lines([label], 12, y + 17, 12, "#e4ebe4", 500, anchor="start"))
        for j, block in enumerate(blocks):
            start, stop, text = block[:3]
            style = block[3] if len(block) > 3 else ("alt" if j % 2 else None)
            x, w = left + start * scale, (stop - start) * scale - 2
            if len(text) * 5.9 + 6 > w:
                raise ValueError(f"Timeline label {text!r} does not fit its {stop - start}{unit} bar in {figure['title']!r}.")
            body.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="24" rx="4" fill="{fills[style]}" stroke="#6b8e74" stroke-opacity=".7"/>')
            body.append(svg_lines([text], x + w / 2, y + 16, 10.5, "#e4ebe4", 500))
    for t, text in markers:
        x = left + t * scale
        bottom = top + len(tracks) * row
        body.append(f'<path d="M{x:.1f} {top - 4} V{bottom + 2}" stroke="#e4ad85" stroke-width="1.5"/>')
        body.append(svg_lines([text], x, bottom + 15, 10.5, "#e4ad85", 600))
    description = "; ".join(f"{label}: " + ", ".join(f"{b[0]} to {b[1]} {unit} {b[2]}" for b in blocks) for label, blocks in tracks)
    if markers:
        description += ". Markers: " + ", ".join(f"{text} at {t} {unit}" for t, text in markers)
    return svg_shell(width, height, figure["title"], description, "".join(body))
