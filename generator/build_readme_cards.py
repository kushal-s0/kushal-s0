"""
Builds the animated SVG cards used by README.md — section headers, highlight
stats, the about.yaml terminal, project covers, the journey timeline, etc.

    cd generator
    python build_readme_cards.py

Output goes to assets/readme/*.svg. No dependencies beyond the standard library.

GitHub serves README images through a sanitising proxy: external fonts and
scripts are stripped, but inline <style>, CSS keyframes and SMIL animations
survive. So everything here uses system font stacks and pure-SVG motion.
"""
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

OUT = Path(__file__).resolve().parent.parent / "assets" / "readme"

# ── palette (matches banner.svg and the stats cards) ─────────────────────────
BG = "#0A101F"
PANEL = "#0F172A"
LINE = "#1E293B"
CYAN = "#22D3EE"
VIOLET = "#A78BFA"
EMERALD = "#10B981"
AMBER = "#F59E0B"
TEXT = "#F8FAFC"
MUTED = "#94A3B8"
DIM = "#64748B"

MONO = "ui-monospace,SFMono-Regular,'JetBrains Mono','Cascadia Code',Consolas,'Liberation Mono',Menlo,monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,Helvetica,Arial,sans-serif"

BASE_CSS = f"""
.m{{font-family:{MONO}}}
.s{{font-family:{SANS}}}
.up{{animation:up .7s cubic-bezier(.2,.7,.2,1) both}}
.fade{{animation:fade .9s ease both}}
.blink{{animation:blink 1.1s steps(1) infinite}}
@keyframes up{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes fade{{from{{opacity:0}}to{{opacity:1}}}}
@keyframes blink{{50%{{opacity:0}}}}
@media (prefers-reduced-motion:reduce){{.up,.fade,.blink{{animation:none}}}}
"""

GRID = (
    '<pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">'
    '<path d="M24 0H0V24" fill="none" stroke="#FFFFFF" stroke-opacity=".035"/></pattern>'
)


# ── helpers ──────────────────────────────────────────────────────────────────
def svg(w, h, title, body, css=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-label={quoteattr(title)}>'
        f"<title>{escape(title)}</title><style>{BASE_CSS}{css}</style>{body}</svg>\n"
    )


def t(x, y, s, size=14, fill=TEXT, cls="s", weight=None, anchor=None, extra=""):
    attrs = f'x="{x}" y="{y}" font-size="{size}" fill="{fill}" class="{cls}"'
    if weight:
        attrs += f' font-weight="{weight}"'
    if anchor:
        attrs += f' text-anchor="{anchor}"'
    return f"<text {attrs} {extra}>{escape(s)}</text>"


def orbit(cx, cy, rx, ry, r, fill, dur, stroke_opacity):
    """Ellipse orbit with an electron riding it.

    The electron sits at the orbit's start point and animateMotion follows a
    path relative to it, so renderers that ignore SMIL still show it on the ring.
    """
    rel = f"M0,0 a{rx},{ry} 0 1,0 {2 * rx},0 a{rx},{ry} 0 1,0 {-2 * rx},0"
    return (
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="none" stroke="{fill}" '
        f'stroke-opacity="{stroke_opacity}" stroke-width="1.3"/>'
        f'<circle cx="{cx - rx}" cy="{cy}" r="{r}" fill="{fill}">'
        f'<animateMotion dur="{dur}s" repeatCount="indefinite" path="{rel}"/></circle>'
    )


def delay(seconds):
    return f'style="animation-delay:{seconds:.2f}s"'


def wrap(s, width):
    lines, cur = [], ""
    for word in s.split():
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    if cur:
        lines.append(cur)
    return lines


def glow(gid, color, cx="0", cy="0", r="70%", opacity=".22"):
    return (
        f'<radialGradient id="{gid}" cx="{cx}" cy="{cy}" r="{r}">'
        f'<stop offset="0" stop-color="{color}" stop-opacity="{opacity}"/>'
        f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>'
    )


def text_gradient(gid, a, b):
    return (
        f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient>'
    )


def shimmer_bar(gid, x, y, w, h, colors, dur=5):
    """A gradient bar with a highlight sweeping across it."""
    n = len(colors) - 1
    stops = "".join(f'<stop offset="{i / n:.2f}" stop-color="{c}"/>' for i, c in enumerate(colors))
    return (
        f'<defs><linearGradient id="{gid}" x1="0" x2="1">{stops}</linearGradient>'
        f'<linearGradient id="{gid}h" x1="0" x2="1">'
        f'<stop offset="0" stop-color="#FFFFFF" stop-opacity="0"/>'
        f'<stop offset=".5" stop-color="#FFFFFF" stop-opacity=".85"/>'
        f'<stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></linearGradient>'
        f'<clipPath id="{gid}c"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h / 2}"/></clipPath></defs>'
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h / 2}" fill="url(#{gid})"/>'
        f'<g clip-path="url(#{gid}c)"><rect x="{x - 180}" y="{y}" width="180" height="{h}" fill="url(#{gid}h)" opacity=".6">'
        f'<animate attributeName="x" from="{x - 180}" to="{x + w}" dur="{dur}s" repeatCount="indefinite"/></rect></g>'
    )


def panel(w, h, accent, gid="p", rx=16, glow_at=("0", "0")):
    """Dark rounded panel with a faint grid and a corner glow."""
    return (
        f'<defs><clipPath id="{gid}clip"><rect width="{w}" height="{h}" rx="{rx}"/></clipPath>'
        f'{glow(gid + "glow", accent, *glow_at)}</defs>'
        f'<g clip-path="url(#{gid}clip)">'
        f'<rect width="{w}" height="{h}" fill="{BG}"/>'
        f'<rect width="{w}" height="{h}" fill="url(#grid)"/>'
        f'<rect width="{w}" height="{h}" fill="url(#{gid}glow)"/></g>'
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{rx - .5}" fill="none" '
        f'stroke="{accent}" stroke-opacity=".25"/>'
    )


# ── section headers ──────────────────────────────────────────────────────────
SECTIONS = [
    ("about", "01", "About Me", "cat about.yaml", CYAN),
    ("highlights", "02", "Highlights", "./highlights --top", AMBER),
    ("experience", "03", "Professional Experience", "git log --author=kushal", VIOLET),
    ("projects", "04", "Featured Projects", "ls ~/projects", EMERALD),
    ("stack", "05", "Technology Stack", "which --all", CYAN),
    ("analytics", "06", "GitHub Analytics", "gh stats kushal-s0", VIOLET),
    ("education", "07", "Education & Achievements", "cat awards.log", AMBER),
    ("journey", "08", "Engineering Journey", "git log --graph", EMERALD),
    ("beyond", "09", "Beyond the Code", "echo $PHILOSOPHY", VIOLET),
]


def section_header(num, title, cmd, accent):
    w, h = 900, 76
    partner = VIOLET if accent != VIOLET else CYAN
    body = (
        f"<defs>{GRID}</defs>"
        + panel(w, h, accent, rx=14, glow_at=("0", ".5"))
        + shimmer_bar("bar", 88, h - 16, 220, 3, [accent, partner, BG])
        + f'<g class="up"><rect x="22" y="19" width="50" height="38" rx="10" fill="{accent}" '
        f'fill-opacity=".12" stroke="{accent}" stroke-opacity=".5"/>'
        + t(47, 44, num, 16, accent, "m", 700, "middle")
        + t(88, 47, title, 25, TEXT, "s", 700)
        + "</g>"
        + f'<g class="fade" {delay(.35)}>'
        + t(w - 42, 44, "$ " + cmd, 13, DIM, "m", None, "end")
        + f'<rect class="blink" x="{w - 34}" y="31" width="9" height="17" rx="1" fill="{accent}"/></g>'
    )
    return svg(w, h, title, body)


# ── highlight stats ──────────────────────────────────────────────────────────
STATS = [
    ("9.48", "CGPA", "B.Tech Computer Engg.", "Honors in AI & ML", CYAN),
    ("3", "PODIUM FINISHES", "IET InTech 2K26 winner", "TechnoGenesis · AI-Robo", AMBER),
    ("2", "AI / ML INTERNSHIPS", "GenAI & Agentic AI", "ML (Finance) · Claidroid", VIOLET),
    ("4", "FLAGSHIP PROJECTS", "Atomix · GeoSwipe", "CommUnity · Recommender", EMERALD),
]


def highlights():
    w, h, gap = 900, 184, 16
    cw = (w - gap * 3) / 4
    body = f"<defs>{GRID}</defs>"
    for i, (num, label, sub1, sub2, accent) in enumerate(STATS):
        x = i * (cw + gap)
        gid = f"s{i}"
        body += (
            f'<g class="up" {delay(i * .12)}><g transform="translate({x:.1f} 0)">'
            f"<defs>{text_gradient(gid + 'num', TEXT, accent)}</defs>"
            + panel(cw, h, accent, gid=gid, rx=14, glow_at=("1", "0"))
            + f'<rect x="20" y="22" width="28" height="4" rx="2" fill="{accent}"/>'
            + t(cw - 20, 28, f"0{i + 1}", 11, DIM, "m", None, "end")
            + t(20, 90, num, 50, f"url(#{gid}num)", "s", 800)
            + t(20, 116, label, 11.5, accent, "m", 700, extra='letter-spacing="1.2"')
            + t(20, 142, sub1, 12.5, MUTED)
            + t(20, 161, sub2, 12.5, MUTED)
            + "</g></g>"
        )
    return svg(w, h, "Highlights: 9.48 CGPA, 3 podium finishes, 2 AI/ML internships, 4 flagship projects", body)


# ── about.yaml terminal ──────────────────────────────────────────────────────
ABOUT_YAML = """\
name: Kushal D. Soni
location: Mumbai, India
education:
  degree: B.Tech Computer Engineering (Honors - AI & ML)
  college: K. J. Somaiya Institute of Technology
  cgpa: 9.48
current_role: Generative AI & Agentic AI Intern @ Claidroid
current_focus:
  - Agentic AI systems & multi-model AI workflows
  - Applied Machine Learning & Forecasting
  - Full Stack Engineering (Django · React · Flask)
  - Computer Vision & Gesture Interaction
currently_building:
  atomix: Unity 3D AI-guided virtual chemistry lab
  hospital_ai: Agentic forecasting for hospital operations
  geoswipe: Gesture-controlled 3D Earth explorer
  community: AI-powered club & event management portal
looking_for:
  - Software Engineering Internships
  - AI / ML & Generative AI Opportunities
  - Open Source Collaboration
motto: "Build AI that does real work, not demos."
"""


def yaml_segments(line):
    indent = line[: len(line) - len(line.lstrip())]
    body = line.strip()
    if body.startswith("- "):
        return [(indent, TEXT), ("- ", CYAN), (body[2:], TEXT)]
    key, _, value = body.partition(":")
    value = value.strip()
    segs = [(indent, TEXT), (key, VIOLET), (":", DIM)]
    if not value:
        return segs
    if value.replace(".", "").isdigit():
        color = AMBER
    elif value.startswith('"'):
        color = EMERALD
    else:
        color = TEXT
    return segs + [(" " + value, color)]


def tspans(segs):
    return "".join(f'<tspan fill="{c}">{escape(s)}</tspan>' for s, c in segs)


def about_terminal():
    lines = ABOUT_YAML.splitlines()
    w, lh, top = 900, 22, 104
    h = top + len(lines) * lh + 44
    pre = 'xml:space="preserve" style="white-space:pre"'
    prompt = [("kushal", EMERALD), ("@", DIM), ("kjsit", EMERALD), (":", DIM), ("~/profile", CYAN), ("$ ", DIM)]

    body = (
        f"<defs>{GRID}{text_gradient('mono', CYAN, VIOLET)}"
        f'<linearGradient id="ring" x1="0" x2="1"><stop offset="0" stop-color="{CYAN}"/>'
        f'<stop offset="1" stop-color="{VIOLET}"/></linearGradient></defs>'
        + panel(w, h, CYAN, glow_at=("1", ".45"))
        # window chrome
        + f'<path d="M16 .5H{w - 16}A15.5 15.5 0 0 1 {w - .5} 16V40H.5V16A15.5 15.5 0 0 1 16 .5Z" fill="#070B16"/>'
        + f'<line x1="1" y1="40.5" x2="{w - 1}" y2="40.5" stroke="{LINE}"/>'
        + '<circle cx="24" cy="20" r="6" fill="#FF5F56"/><circle cx="44" cy="20" r="6" fill="#FFBD2E"/>'
        + '<circle cx="64" cy="20" r="6" fill="#27C93F"/>'
        + t(w / 2, 25, "kushal@kjsit: ~/profile — about.yaml", 12, DIM, "m", None, "middle")
        + f'<text x="28" y="72" font-size="13.5" class="m fade" {pre}>{tspans(prompt + [("cat about.yaml", TEXT)])}</text>'
    )
    for i, line in enumerate(lines):
        y = top + i * lh
        body += (
            f'<g class="fade" {delay(.25 + i * .05)}>'
            + t(46, y, str(i + 1), 12, "#334155", "m", None, "end")
            + f'<text x="62" y="{y}" font-size="13.5" class="m" {pre}>{tspans(yaml_segments(line))}</text></g>'
        )
    last = top + len(lines) * lh + 12
    body += (
        f'<text x="28" y="{last}" font-size="13.5" class="m fade" xml:space="preserve" '
        f'style="white-space:pre;animation-delay:{.25 + len(lines) * .05:.2f}s">'
        + tspans(prompt)
        + f'<tspan fill="{CYAN}">█<animate attributeName="fill-opacity" values="1;0;1" dur="1.1s" '
        f'calcMode="discrete" repeatCount="indefinite"/></tspan></text>'
    )

    # orbiting monogram on the right
    cx, cy = 772, (top + h) / 2 - 30
    body += '<g class="fade" style="animation-delay:.4s">'
    for k, angle in enumerate((0, 60, 120)):
        color = (CYAN, VIOLET, EMERALD)[k]
        body += (
            f'<g transform="rotate({angle} {cx} {cy})">'
            + orbit(cx, cy, 96, 32, 4.5, color, 5 + k * 1.5, ".35")
            + "</g>"
        )
    body += (
        f'<circle cx="{cx}" cy="{cy}" r="44" fill="{BG}" stroke="url(#ring)" stroke-width="2"/>'
        f'<circle cx="{cx}" cy="{cy}" r="44" fill="none" stroke="{CYAN}" stroke-opacity=".5">'
        f'<animate attributeName="r" values="44;60" dur="2.6s" repeatCount="indefinite"/>'
        f'<animate attributeName="stroke-opacity" values=".5;0" dur="2.6s" repeatCount="indefinite"/></circle>'
        + t(cx, cy + 11, "KS", 32, "url(#mono)", "s", 800, "middle")
        + f'<rect x="{cx - 104}" y="{cy + 128}" width="208" height="30" rx="15" fill="{EMERALD}" '
        f'fill-opacity=".1" stroke="{EMERALD}" stroke-opacity=".45"/>'
        + f'<circle cx="{cx - 84}" cy="{cy + 143}" r="4" fill="{EMERALD}">'
        f'<animate attributeName="opacity" values="1;.25;1" dur="1.6s" repeatCount="indefinite"/></circle>'
        + t(cx + 8, cy + 147, "OPEN TO INTERNSHIPS", 11.5, EMERALD, "m", 700, "middle", 'letter-spacing="1"')
        + "</g>"
    )
    return svg(w, h, "about.yaml — Kushal D. Soni, Generative AI & Agentic AI developer from Mumbai", body)


# ── current focus ────────────────────────────────────────────────────────────
FOCUS = [
    ("BUILDING", CYAN, ["Atomix", "CommUnity", "GeoSwipe"]),
    ("LEARNING", VIOLET, ["Agentic AI & LLM Tooling", "MLOps & Model Deployment", "Advanced React"]),
    ("INTERESTED IN", EMERALD, ["System Design", "Cloud Architecture", "Scalable Data Pipelines"]),
]


def focus():
    w, h = 900, 196
    col = w / 3
    body = f"<defs>{GRID}</defs>" + panel(w, h, VIOLET, glow_at=(".5", "0"))
    for i, (label, accent, items) in enumerate(FOCUS):
        x = i * col + 30
        if i:
            body += f'<line x1="{i * col}" y1="26" x2="{i * col}" y2="{h - 26}" stroke="{LINE}"/>'
        body += (
            f'<g class="up" {delay(i * .15)}>'
            + f'<rect x="{x}" y="30" width="10" height="10" rx="2.5" fill="{accent}"/>'
            + t(x + 20, 40, label, 12, accent, "m", 700, extra='letter-spacing="2"')
        )
        for j, item in enumerate(items):
            y = 84 + j * 36
            body += t(x, y, "›", 18, accent, "m", 700) + t(x + 20, y, item, 15.5, TEXT, "s", 500)
        body += "</g>"
    return svg(w, h, "Current focus — building, learning, interested in", body)


# ── project covers ───────────────────────────────────────────────────────────
def motif_network(color):
    c = (362, 92)
    nodes = [(312, 58), (366, 36), (414, 70), (404, 132), (338, 142), (300, 104)]
    out = ""
    for k, n in enumerate(nodes):
        m = nodes[(k + 1) % len(nodes)]
        out += f'<line x1="{c[0]}" y1="{c[1]}" x2="{n[0]}" y2="{n[1]}" stroke="{color}" stroke-opacity=".35"/>'
        out += f'<line x1="{n[0]}" y1="{n[1]}" x2="{m[0]}" y2="{m[1]}" stroke="{color}" stroke-opacity=".15"/>'
    for k, n in enumerate(nodes):
        out += (
            f'<circle cx="{n[0]}" cy="{n[1]}" r="6" fill="{BG}" stroke="{color}" stroke-width="2">'
            f'<animate attributeName="r" values="6;9;6" dur="2.4s" begin="{k * .4}s" repeatCount="indefinite"/></circle>'
        )
    out += f'<circle cx="{c[0]}" cy="{c[1]}" r="13" fill="{color}" fill-opacity=".9"/>'
    a = (nodes[2][0] - c[0], nodes[2][1] - c[1])
    b = (nodes[3][0] - c[0], nodes[3][1] - c[1])
    out += (
        f'<circle cx="{c[0]}" cy="{c[1]}" r="3" fill="#FFFFFF">'
        f'<animateMotion dur="3s" repeatCount="indefinite" path="M0,0 L{a[0]},{a[1]} L{b[0]},{b[1]} Z"/></circle>'
    )
    return out


def motif_globe(color):
    cx, cy, r = 360, 92, 58
    out = (
        f'<circle cx="{cx}" cy="{cy}" r="{r + 14}" fill="{color}" fill-opacity=".06"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{BG}" stroke="{color}" stroke-width="1.6"/>'
    )
    for dy, rx, ry in ((0, r, 14), (-30, 49, 9), (30, 49, 9)):
        out += f'<ellipse cx="{cx}" cy="{cy + dy}" rx="{rx}" ry="{ry}" fill="none" stroke="{color}" stroke-opacity=".3"/>'
    for k in range(3):
        out += (
            f'<ellipse cx="{cx}" cy="{cy}" rx="0" ry="{r}" fill="none" stroke="{color}" stroke-opacity=".55">'
            f'<animate attributeName="rx" values="{r};0;{r}" dur="6s" begin="{-k * 2}s" repeatCount="indefinite"/></ellipse>'
        )
    out += (
        f'<circle cx="{cx + 22}" cy="{cy - 24}" r="4" fill="{AMBER}"/>'
        f'<circle cx="{cx + 22}" cy="{cy - 24}" r="4" fill="none" stroke="{AMBER}">'
        f'<animate attributeName="r" values="4;14" dur="1.8s" repeatCount="indefinite"/>'
        f'<animate attributeName="stroke-opacity" values="1;0" dur="1.8s" repeatCount="indefinite"/></circle>'
    )
    return out


def motif_atom(color):
    cx, cy = 360, 92
    out = ""
    for k, angle in enumerate((0, 60, 120)):
        out += (
            f'<g transform="rotate({angle} {cx} {cy})">'
            f'<ellipse cx="{cx}" cy="{cy}" rx="70" ry="24" fill="none" stroke="{color}" stroke-opacity=".45" stroke-width="1.4"/>'
            + orbit(cx, cy, 70, 24, 4.5, (color, AMBER, VIOLET)[k], 2.6 + k * .7, "0")
            + "</g>"
        )
    out += (
        f'<circle cx="{cx}" cy="{cy}" r="16" fill="{color}" fill-opacity=".18">'
        f'<animate attributeName="r" values="14;20;14" dur="2.4s" repeatCount="indefinite"/></circle>'
        f'<circle cx="{cx}" cy="{cy}" r="9" fill="{color}"/>'
    )
    return out


def motif_match(color):
    left = [(318, 46), (318, 78), (318, 110), (318, 142)]
    right = [(412, 40), (412, 72), (412, 104), (412, 136)]
    out = ""
    for a in left:
        for b in right:
            out += f'<path d="M{a[0]},{a[1]} C365,{a[1]} 365,{b[1]} {b[0]},{b[1]}" fill="none" stroke="{MUTED}" stroke-opacity=".08"/>'
    for k, (i, j) in enumerate(((0, 2), (1, 0), (2, 3), (3, 1))):
        a, b = left[i], right[j]
        out += (
            f'<path d="M{a[0]},{a[1]} C365,{a[1]} 365,{b[1]} {b[0]},{b[1]}" fill="none" stroke="{color}" '
            f'stroke-width="2" stroke-dasharray="6 6">'
            f'<animate attributeName="stroke-dashoffset" from="48" to="0" dur="{1.6 + k * .3}s" repeatCount="indefinite"/></path>'
        )
    for p in left:
        out += f'<circle cx="{p[0]}" cy="{p[1]}" r="6" fill="{BG}" stroke="{CYAN}" stroke-width="2"/>'
    for p in right:
        out += f'<rect x="{p[0] - 6}" y="{p[1] - 6}" width="12" height="12" rx="3" fill="{BG}" stroke="{color}" stroke-width="2"/>'
    return out


PROJECTS = [
    ("community", "CommUnity", "For Committees and Clubs", "FULL-STACK · GENAI", VIOLET, motif_network,
     None, "kushal-s0/CommUnity", 30),
    ("geoswipe", "GeoSwipe", "Earth Exploration Using Hand Gestures", "COMPUTER VISION · 3D", EMERALD, motif_globe,
     "2ND PRIZE · AI-ROBO FEST 2026", "Interior-Gardener/Geoswipe", 30),
    ("atomix", "Atomix", "Your Personal Laboratory With AI", "UNITY 3D · GENAI", CYAN, motif_atom,
     "WINNER · IET INTECH 2K26", "Dhir-learner/Atomix", 30),
    ("recommender", "Internship", "AI-Based Recommendation System", "MACHINE LEARNING · FLASK", AMBER, motif_match,
     None, "kushal-s0/AI-Based_Internship_Recommendation_Engine", 30),
]


def project_cover(title, tagline, kind, accent, motif, award, repo, size):
    w, h = 440, 184
    if title == "Internship":
        title_svg = t(24, 76, "Internship", size, TEXT, "s", 800) + t(24, 108, "Recommender", size, TEXT, "s", 800)
        tag_y = 132
    else:
        title_svg = t(24, 94, title, size + 4, TEXT, "s", 800)
        tag_y = 120
    chip_w = len(kind) * 7 + 22
    body = (
        f"<defs>{GRID}</defs>"
        + panel(w, h, accent, glow_at=("1", ".5"))
        + f'<g class="fade" {delay(.2)}>{motif(accent)}</g>'
        + f'<g class="up"><rect x="24" y="22" width="{chip_w}" height="22" rx="11" fill="{accent}" '
        f'fill-opacity=".12" stroke="{accent}" stroke-opacity=".4"/>'
        + t(24 + chip_w / 2, 37, kind, 10.5, accent, "m", 700, "middle", 'letter-spacing=".6"')
        + title_svg
        + t(24, tag_y, tagline, 13.5, MUTED)
        + "</g>"
    )
    if award:
        aw = len(award) * 7 + 40
        body += (
            f'<g class="up" {delay(.25)}><rect x="24" y="{h - 42}" width="{aw}" height="24" rx="6" fill="{AMBER}" '
            f'fill-opacity=".14" stroke="{AMBER}" stroke-opacity=".55"/>'
            + t(38, h - 25.5, "★", 12, AMBER, "s")
            + t(54, h - 25.5, award, 10.5, AMBER, "m", 700, extra='letter-spacing=".5"')
            + "</g>"
        )
    else:
        body += f'<g class="up" {delay(.25)}>' + t(24, h - 25, "↗ " + repo, 11, DIM, "m") + "</g>"
    name = "Internship Recommender" if title == "Internship" else title
    return svg(w, h, f"{name} — {tagline}", body)


# ── engineering journey timeline ─────────────────────────────────────────────
KIND_COLOR = {
    "MILESTONE": EMERALD, "AWARD": AMBER, "BUILD": CYAN,
    "INTERNSHIP": VIOLET, "SHOWCASE": AMBER, "NOW": EMERALD,
}
JOURNEY = [
    ("2023", [
        ("MILESTONE", "Started B.Tech in Computer Engineering (Honors – AIML) @ KJSIT"),
    ]),
    ("2024", [
        ("AWARD", "TechnoGenesis 2K24 — Project Competition Winner"),
        ("BUILD", "Built AI-Based Internship Recommendation System"),
    ]),
    ("2025", [
        ("INTERNSHIP", "Machine Learning Intern (Finance) — Claidroid Technologies"),
        ("BUILD", "Built CommUnity — Django event portal with AI report generation"),
        ("BUILD", "Built GeoSwipe — gesture-controlled 3D Earth explorer"),
        ("INTERNSHIP", "Generative AI & Agentic AI Intern — Claidroid Technologies"),
    ]),
    ("2026", [
        ("AWARD", "IET InTech 2K26 National Winner — Atomix"),
        ("AWARD", "Somaiya AI-Robo Festival — 2nd Prize"),
        ("SHOWCASE", "CIIA National Innovation Showcase"),
        ("NOW", "Building Atomix & exploring Agentic AI, System Design, MLOps"),
    ]),
]


def journey():
    w, pad = 900, 24
    col = (w - pad * 2) / 4
    track_y, cards_top, lh = 78, 106, 17

    columns, max_bottom = [], 0
    for year, events in JOURNEY:
        cards, y = [], cards_top
        for kind, text in events:
            lines = wrap(text, 22)
            ch = 48 + (len(lines) - 1) * lh + 12
            cards.append((y, ch, kind, lines))
            y += ch + 12
        columns.append((year, cards))
        max_bottom = max(max_bottom, y)
    h = int(max_bottom + 14)

    body = (
        f"<defs>{GRID}</defs>"
        + panel(w, h, EMERALD, glow_at=("1", "0"))
        + shimmer_bar("track", pad, track_y - 1.5, w - pad * 2, 3, [EMERALD, CYAN, VIOLET, AMBER], dur=6)
    )
    for i, (year, cards) in enumerate(columns):
        x = pad + i * col
        nx = x + 10
        is_now = i == len(columns) - 1
        accent = (EMERALD, CYAN, VIOLET, AMBER)[i]
        body += f'<g class="up" {delay(i * .18)}>'
        body += t(x + 2, 58, year, 26, TEXT, "s", 800)
        if is_now:
            body += (
                f'<circle cx="{nx}" cy="{track_y}" r="7" fill="none" stroke="{accent}">'
                f'<animate attributeName="r" values="7;20" dur="2s" repeatCount="indefinite"/>'
                f'<animate attributeName="stroke-opacity" values="1;0" dur="2s" repeatCount="indefinite"/></circle>'
            )
        body += f'<circle cx="{nx}" cy="{track_y}" r="7" fill="{BG}" stroke="{accent}" stroke-width="3"/>'
        last_mid = cards[-1][0] + 24
        body += f'<line x1="{nx}" y1="{track_y + 8}" x2="{nx}" y2="{last_mid}" stroke="{LINE}" stroke-width="2"/>'
        for cy, ch, kind, lines in cards:
            color = KIND_COLOR[kind]
            cx, cw = x + 26, col - 38
            body += (
                f'<line x1="{nx}" y1="{cy + 24}" x2="{cx}" y2="{cy + 24}" stroke="{LINE}" stroke-width="2"/>'
                f'<circle cx="{nx}" cy="{cy + 24}" r="3" fill="{color}"/>'
                f'<rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" rx="10" fill="{PANEL}" '
                f'stroke="{color}" stroke-opacity="{.6 if kind == "NOW" else .22}"/>'
                f'<rect x="{cx}" y="{cy + 12}" width="3" height="{ch - 24}" rx="1.5" fill="{color}"/>'
                + t(cx + 14, cy + 22, ("● " if kind == "NOW" else "") + kind, 9.5, color, "m", 700, extra='letter-spacing="1.2"')
            )
            for k, line in enumerate(lines):
                body += t(cx + 14, cy + 44 + k * lh, line, 12.5, TEXT if k == 0 else "#CBD5E1")
        body += "</g>"
    return svg(w, h, "Engineering journey 2023–2026", body)


# ── philosophy + dev tiles ───────────────────────────────────────────────────
def philosophy():
    w, h = 900, 176
    body = (
        f"<defs>{GRID}{text_gradient('q', CYAN, VIOLET)}"
        f'<linearGradient id="qh" x1="0" x2="1"><stop offset="0" stop-color="{CYAN}"/>'
        f'<stop offset="1" stop-color="{VIOLET}"/></linearGradient></defs>'
        + panel(w, h, VIOLET, glow_at=(".5", "1"))
        + t(46, 112, "“", 120, "url(#q)", "s", 800, extra='opacity=".35"')
        + t(w - 46, 190, "”", 120, "url(#q)", "s", 800, "end", 'opacity=".35"')
        + t(w / 2, 44, "// DEVELOPER PHILOSOPHY", 11, DIM, "m", 700, "middle", 'letter-spacing="2"')
        + f'<g class="up">'
        + t(w / 2, 92, "An AI feature nobody trusts is just an expensive animation.", 23, TEXT, "s", 600, "middle")
        + "</g>"
        + f'<g class="up" {delay(.35)}>'
        + t(w / 2, 130, "Build the boring reliability first.", 23, "url(#qh)", "s", 800, "middle")
        + "</g>"
    )
    return svg(w, h, "An AI feature nobody trusts is just an expensive animation. Build the boring reliability first.", body)


TILES = [
    ("COFFEE", ["Infinite"], AMBER),
    ("LATE NIGHTS", ["Too Many"], VIOLET),
    ("FAVORITE LANGUAGE", ["Python"], CYAN),
    ("CURRENT OBSESSION", ["Agentic AI"], EMERALD),
    ("DREAM", ["Build AI products", "used at scale"], VIOLET),
]


def dev_tiles():
    w, h, gap = 900, 112, 12
    tw = (w - gap * 4) / 5
    body = f"<defs>{GRID}</defs>"
    for i, (label, value, accent) in enumerate(TILES):
        x = i * (tw + gap)
        size = 17 if len(value) == 1 else 14
        body += (
            f'<g class="up" {delay(i * .1)}><g transform="translate({x:.1f} 0)">'
            + panel(tw, h, accent, gid=f"t{i}", rx=12, glow_at=("0", "1"))
            + f'<rect x="18" y="22" width="18" height="3" rx="1.5" fill="{accent}"/>'
            + t(18, 46, label, 10, accent, "m", 700, extra='letter-spacing="1.2"')
        )
        for k, v in enumerate(value):
            body += t(18, 76 + k * 19 - (8 if len(value) > 1 else 0), v, size, TEXT, "s", 700)
        body += "</g></g>"
    return svg(w, h, "Coffee: infinite · Late nights: too many · Favorite language: Python · Obsession: Agentic AI · Dream: build AI products used at scale", body)


# ── build ────────────────────────────────────────────────────────────────────
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = {f"section-{key}.svg": section_header(num, title, cmd, accent)
             for key, num, title, cmd, accent in SECTIONS}
    files.update({
        "highlights.svg": highlights(),
        "about.svg": about_terminal(),
        "focus.svg": focus(),
        "journey.svg": journey(),
        "philosophy.svg": philosophy(),
        "dev-tiles.svg": dev_tiles(),
    })
    for key, *spec in PROJECTS:
        files[f"project-{key}.svg"] = project_cover(*spec)
    for name, content in files.items():
        (OUT / name).write_text(content, encoding="utf-8")
        print(f"wrote assets/readme/{name}")


if __name__ == "__main__":
    main()
