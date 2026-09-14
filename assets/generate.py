"""Builds every SVG in this folder. Run `python assets/generate.py` from the repo root.

GitHub renders README images through a proxy that strips scripts and external
resources, so each file here is self-contained: inline CSS, SMIL animation,
system font stacks, no web fonts. Edit the text in this file and re-run it
rather than hand-editing the SVGs.
"""
import math
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))

SANS = "'Segoe UI', Ubuntu, 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "Consolas, 'SF Mono', Menlo, 'DejaVu Sans Mono', 'Liberation Mono', monospace"

PANEL = "#161b22"
PANEL2 = "#21262d"
BORDER = "#30363d"
TEXT = "#e6edf3"
BODY = "#c9d1d9"
MUTED = "#8b949e"
BLUE = "#58a6ff"
GREEN = "#3fb950"
PURPLE = "#bc8cff"
ORANGE = "#f78166"
YELLOW = "#e3b341"
PINK = "#f778ba"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fmt(n):
    return ("%.2f" % n).rstrip("0").rstrip(".")


def write(name, svg):
    path = os.path.join(HERE, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(svg)
    print("wrote", os.path.relpath(path, HERE), len(svg), "bytes")


# --------------------------------------------------------------------------
# Hero banner
# --------------------------------------------------------------------------
def hero():
    W, H = 1200, 360
    FS = 14
    CW = FS * 0.6
    LH = 22
    TX, TY, TW, TH = 640, 44, 520, 272
    x0 = TX + 22
    y0 = TY + 32 + 30

    lines = [
        ("cmd", "whoami"),
        ("out", "ashton, 4th-year CS co-op @ University of Guelph"),
        ("cmd", "cat current.txt"),
        ("out", "Software Developer (contract) @ ScanAir"),
        ("out", "FastAPI + React/TS + Mapbox GL + Python geometry"),
        ("cmd", "ls ~/projects"),
        ("out", "AnkiGPT/   AI-Tutor-Bot/   VCard-Manager/"),
        ("cmd", "echo $STATUS"),
        ("out", "open to software developer co-op roles"),
    ]

    out = []
    defs = []
    cursor_keys = []  # (time, x, y)
    t = 0.9
    PER_CHAR = 0.055
    line_i = 0
    for kind, txt in lines:
        y = y0 + line_i * LH
        if kind == "cmd":
            n = len(txt)
            total = "$ " + txt
            t0 = t
            t_type = t0 + 0.35
            dur = n * PER_CHAR
            vals = ";".join(fmt((2 + k) * CW) for k in range(0, n + 1))
            defs.append(
                '<clipPath id="cl%d"><rect x="%s" y="%s" width="0" height="18">' % (line_i, fmt(x0), fmt(y - 12))
                + '<set attributeName="width" to="%s" begin="%ss" fill="freeze"/>' % (fmt(2 * CW), fmt(t0))
                + '<animate attributeName="width" values="%s" begin="%ss" dur="%ss" calcMode="discrete" fill="freeze"/>' % (vals, fmt(t_type), fmt(dur))
                + "</rect></clipPath>"
            )
            out.append(
                '<text x="%s" y="%s" class="mono" textLength="%s" clip-path="url(#cl%d)">' % (fmt(x0), fmt(y), fmt(len(total) * CW), line_i)
                + '<tspan fill="%s">$ </tspan><tspan fill="%s">%s</tspan></text>' % (GREEN, TEXT, esc(txt))
            )
            cursor_keys.append((t0, x0 + 2 * CW, y))
            for k in range(1, n + 1):
                cursor_keys.append((t_type + k * PER_CHAR, x0 + (2 + k) * CW, y))
            t = t_type + dur + 0.3
        else:
            out.append(
                '<text x="%s" y="%s" class="mono" fill="%s" textLength="%s" opacity="0">%s' % (fmt(x0), fmt(y), MUTED, fmt(len(txt) * CW), esc(txt))
                + '<animate attributeName="opacity" from="0" to="1" begin="%ss" dur="0.18s" fill="freeze"/></text>' % fmt(t)
            )
            t += 0.14
        line_i += 1
        if kind == "out" and line_i < len(lines) and lines[line_i][0] == "cmd":
            t += 0.3

    # final prompt
    y = y0 + line_i * LH
    t_end = t + 0.1
    out.append(
        '<text x="%s" y="%s" class="mono" fill="%s" opacity="0">$' % (fmt(x0), fmt(y), GREEN)
        + '<animate attributeName="opacity" from="0" to="1" begin="%ss" dur="0.1s" fill="freeze"/></text>' % fmt(t_end)
    )
    cursor_keys.append((t_end, x0 + 2 * CW, y))

    T = t_end
    first_t = cursor_keys[0][0]
    # SMIL requires the first keyTime to be exactly 0, so park the cursor on
    # the first prompt from t=0 (it stays invisible until first_t anyway).
    cursor_keys.insert(0, (0.0, cursor_keys[0][1], cursor_keys[0][2]))
    kt = ";".join(fmt(min(ct / T, 1.0)) for ct, _, _ in cursor_keys)
    kx = ";".join(fmt(cx) for _, cx, _ in cursor_keys)
    ky = ";".join(fmt(cy - 13) for _, _, cy in cursor_keys)
    cursor = (
        '<g opacity="0"><set attributeName="opacity" to="1" begin="%ss" fill="freeze"/>' % fmt(first_t)
        + '<rect class="blink" x="%s" y="%s" width="%s" height="17" fill="%s" rx="1">' % (fmt(cursor_keys[0][1]), fmt(cursor_keys[0][2] - 13), fmt(CW), BLUE)
        + '<animate attributeName="x" values="%s" keyTimes="%s" calcMode="discrete" begin="0s" dur="%ss" fill="freeze"/>' % (kx, kt, fmt(T))
        + '<animate attributeName="y" values="%s" keyTimes="%s" calcMode="discrete" begin="0s" dur="%ss" fill="freeze"/>' % (ky, kt, fmt(T))
        + "</rect></g>"
    )

    rng = random.Random(7)
    particles = []
    for _ in range(18):
        px = rng.uniform(30, W - 30)
        py = rng.uniform(40, H - 20)
        r = rng.uniform(1.2, 2.6)
        d = rng.uniform(7, 14)
        delay = -rng.uniform(0, 14)
        col = rng.choice([BLUE, PURPLE, GREEN, "#ffffff"])
        particles.append(
            '<circle class="p" cx="%s" cy="%s" r="%s" fill="%s" style="animation-duration:%ss;animation-delay:%ss"/>'
            % (fmt(px), fmt(py), fmt(r), col, fmt(d), fmt(delay))
        )

    css = """
    .sans{font-family:%(sans)s}
    .mono{font-family:%(mono)s;font-size:%(fs)dpx}
    .fade{opacity:0;animation:fadeUp .9s cubic-bezier(.2,.7,.2,1) forwards}
    @keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
    .term{opacity:0;animation:termIn 1s cubic-bezier(.2,.7,.2,1) .35s forwards}
    @keyframes termIn{from{opacity:0;transform:translateY(22px) scale(.985)}to{opacity:1;transform:none}}
    .blink{animation:blink 1.1s steps(2,start) infinite}
    @keyframes blink{to{visibility:hidden}}
    .p{opacity:0;animation-name:rise;animation-timing-function:linear;animation-iteration-count:infinite}
    @keyframes rise{0%%{transform:translateY(0);opacity:0}15%%{opacity:.75}85%%{opacity:.35}100%%{transform:translateY(-70px);opacity:0}}
    .pulse{transform-origin:center;transform-box:fill-box;animation:pulse 2.2s ease-out infinite}
    @keyframes pulse{0%%{transform:scale(1);opacity:.8}100%%{transform:scale(2.6);opacity:0}}
    @media (prefers-reduced-motion:reduce){.fade,.term{animation:none;opacity:1}.p{animation:none}.pulse{animation:none}}
    """ % {"sans": SANS, "mono": MONO, "fs": FS}

    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="%(W)d" height="%(H)d" viewBox="0 0 %(W)d %(H)d" role="img" aria-labelledby="t d">
<title id="t">Ashton Long</title>
<desc id="d">Full-stack and AI developer. Fourth-year Computer Science co-op student at the University of Guelph.</desc>
<style>%(css)s</style>
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#0d1117"/><stop offset="1" stop-color="#0b0f16"/>
  </linearGradient>
  <linearGradient id="name" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="520" y2="0" spreadMethod="repeat">
    <stop offset="0" stop-color="%(BLUE)s"/><stop offset=".35" stop-color="%(PURPLE)s"/><stop offset=".7" stop-color="%(GREEN)s"/><stop offset="1" stop-color="%(BLUE)s"/>
    <animateTransform attributeName="gradientTransform" type="translate" from="0 0" to="520 0" dur="7s" repeatCount="indefinite"/>
  </linearGradient>
  <linearGradient id="line" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="%(BLUE)s"/><stop offset="1" stop-color="%(PURPLE)s" stop-opacity="0"/>
  </linearGradient>
  <pattern id="grid" width="36" height="36" patternUnits="userSpaceOnUse">
    <path d="M36 0H0V36" fill="none" stroke="#ffffff" stroke-opacity=".06"/>
  </pattern>
  <radialGradient id="gridMask" cx=".5" cy=".5" r=".7">
    <stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#000"/>
  </radialGradient>
  <mask id="gm"><rect width="%(W)d" height="%(H)d" fill="url(#gridMask)"/></mask>
  <filter id="blur" x="-50%%" y="-50%%" width="200%%" height="200%%"><feGaussianBlur stdDeviation="70"/></filter>
  <clipPath id="frame"><rect width="%(W)d" height="%(H)d" rx="24"/></clipPath>
  <filter id="shadow" x="-10%%" y="-10%%" width="120%%" height="130%%"><feDropShadow dx="0" dy="14" stdDeviation="16" flood-color="#000" flood-opacity=".55"/></filter>
  %(defs)s
</defs>

<g clip-path="url(#frame)">
  <rect width="%(W)d" height="%(H)d" rx="24" fill="url(#bg)"/>
  <rect width="%(W)d" height="%(H)d" fill="url(#grid)" mask="url(#gm)"/>

  <g filter="url(#blur)">
    <circle cx="180" cy="120" r="170" fill="%(BLUE)s" fill-opacity=".30">
      <animateTransform attributeName="transform" type="translate" values="0 0;60 30;0 0" dur="14s" repeatCount="indefinite"/>
    </circle>
    <circle cx="560" cy="330" r="150" fill="%(PURPLE)s" fill-opacity=".22">
      <animateTransform attributeName="transform" type="translate" values="0 0;-50 -40;0 0" dur="17s" repeatCount="indefinite"/>
    </circle>
    <circle cx="1080" cy="60" r="150" fill="%(GREEN)s" fill-opacity=".16">
      <animateTransform attributeName="transform" type="translate" values="0 0;-40 50;0 0" dur="19s" repeatCount="indefinite"/>
    </circle>
  </g>

  %(particles)s

  <!-- left column -->
  <g class="fade" style="animation-delay:.1s">
    <text class="mono" x="64" y="104" fill="%(BLUE)s">// hi, I'm</text>
  </g>
  <g class="fade" style="animation-delay:.25s">
    <text class="sans" x="62" y="168" font-size="66" font-weight="800" letter-spacing="-1.5" fill="url(#name)">Ashton Long</text>
  </g>
  <g class="fade" style="animation-delay:.4s">
    <text class="sans" x="64" y="210" font-size="26" font-weight="600" fill="%(TEXT)s">Full-stack &amp; AI developer</text>
  </g>
  <g class="fade" style="animation-delay:.55s">
    <text class="sans" x="64" y="242" font-size="17" fill="%(MUTED)s">4th-year Computer Science co-op student, University of Guelph</text>
  </g>
  <g class="fade" style="animation-delay:.7s">
    <rect x="64" y="270" width="200" height="34" rx="17" fill="%(GREEN)s" fill-opacity=".12" stroke="%(GREEN)s" stroke-opacity=".45"/>
    <circle class="pulse" cx="84" cy="287" r="5" fill="%(GREEN)s" fill-opacity=".5"/>
    <circle cx="84" cy="287" r="4.5" fill="%(GREEN)s"/>
    <text class="sans" x="98" y="292" font-size="14" font-weight="600" fill="%(GREEN)s">Open to co-op roles</text>
    <rect x="276" y="270" width="150" height="34" rx="17" fill="%(BLUE)s" fill-opacity=".10" stroke="%(BLUE)s" stroke-opacity=".4"/>
    <path transform="translate(291 279)" d="M6 0a5.5 5.5 0 0 0-5.5 5.5C.5 9.6 6 16 6 16s5.5-6.4 5.5-10.5A5.5 5.5 0 0 0 6 0zm0 7.6a2.1 2.1 0 1 1 0-4.2 2.1 2.1 0 0 1 0 4.2z" fill="%(BLUE)s"/>
    <text class="sans" x="310" y="292" font-size="14" font-weight="600" fill="%(BLUE)s">Guelph, Ontario</text>
  </g>
  <g class="fade" style="animation-delay:.85s">
    <rect x="64" y="322" width="300" height="2" rx="1" fill="url(#line)"/>
  </g>

  <!-- terminal -->
  <g class="term" filter="url(#shadow)">
    <rect x="%(TX)d" y="%(TY)d" width="%(TW)d" height="%(TH)d" rx="14" fill="%(PANEL)s" stroke="%(BORDER)s"/>
    <path d="M%(TX)d %(TYb)dH%(TXr)d" stroke="%(BORDER)s"/>
    <circle cx="%(d1)d" cy="%(dy)d" r="6" fill="#ff5f57"/>
    <circle cx="%(d2)d" cy="%(dy)d" r="6" fill="#febc2e"/>
    <circle cx="%(d3)d" cy="%(dy)d" r="6" fill="#28c840"/>
    <text class="mono" x="%(tmid)s" y="%(tty)d" text-anchor="middle" fill="%(MUTED)s" font-size="12">ashton@guelph: ~</text>
    %(out)s
    %(cursor)s
  </g>
</g>
</svg>
""" % {
        "W": W, "H": H, "css": css, "defs": "".join(defs), "particles": "".join(particles),
        "BLUE": BLUE, "PURPLE": PURPLE, "GREEN": GREEN, "TEXT": TEXT, "MUTED": MUTED, "PANEL": PANEL, "BORDER": BORDER,
        "TX": TX, "TY": TY, "TW": TW, "TH": TH, "TYb": TY + 32, "TXr": TX + TW,
        "d1": TX + 22, "d2": TX + 42, "d3": TX + 62, "dy": TY + 16, "tmid": fmt(TX + TW / 2), "tty": TY + 21,
        "out": "".join(out), "cursor": cursor,
    }
    write("hero.svg", svg)


# --------------------------------------------------------------------------
# Project cards
# --------------------------------------------------------------------------
def icon_cards(c):
    return """<g transform="translate(9 10)" fill="none" stroke="%s" stroke-width="2" stroke-linejoin="round">
      <rect x="6" y="0" width="24" height="17" rx="3" transform="rotate(-8 18 8)" opacity=".45"/>
      <rect x="2" y="9" width="26" height="19" rx="3" fill="%s"/>
      <path d="M8 16h9M8 21h14" stroke-linecap="round" opacity=".8"/>
      <path d="M21 15.5l2 2 4-4" stroke-linecap="round" stroke="%s"/>
    </g>""" % (c, PANEL, GREEN)


def icon_route(c):
    path = "M6 34 L15 12 L23 30 L32 10 L42 30"
    return """<g fill="none" stroke="%(c)s" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="%(p)s" stroke-dasharray="4 4" opacity=".6"/>
      <circle cx="6" cy="34" r="3" fill="%(panel)s"/><circle cx="15" cy="12" r="3" fill="%(panel)s"/>
      <circle cx="23" cy="30" r="3" fill="%(panel)s"/><circle cx="32" cy="10" r="3" fill="%(panel)s"/><circle cx="42" cy="30" r="3" fill="%(panel)s"/>
      <circle r="3.5" fill="%(c)s" stroke="none"><animateMotion dur="3.2s" repeatCount="indefinite" path="%(p)s"/></circle>
    </g>""" % {"c": c, "p": path, "panel": PANEL}


def icon_bot(c):
    blink = '<animate attributeName="ry" values="2.6;2.6;.3;2.6;2.6" keyTimes="0;.44;.47;.5;1" dur="4.5s" repeatCount="indefinite"/>'
    return """<g fill="none" stroke="%(c)s" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M24 6v6"/><circle cx="24" cy="5" r="2" fill="%(c)s"/>
      <rect x="9" y="12" width="30" height="24" rx="7"/>
      <ellipse cx="18" cy="23" rx="2.6" ry="2.6" fill="%(c)s" stroke="none">%(b)s</ellipse>
      <ellipse cx="30" cy="23" rx="2.6" ry="2.6" fill="%(c)s" stroke="none">%(b)s</ellipse>
      <path d="M18 30h12" opacity=".8"/>
      <path d="M4 20v8M44 20v8" opacity=".6"/>
    </g>""" % {"c": c, "b": blink}


def icon_vcard(c):
    return """<g fill="none" stroke="%s" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <rect x="5" y="10" width="38" height="28" rx="4"/>
      <circle cx="16" cy="21" r="4"/>
      <path d="M10 32c1-4 3.5-6 6-6s5 2 6 6" opacity=".8"/>
      <path d="M26 19h12M26 25h12M26 31h8" opacity=".8"/>
    </g>""" % c


def icon_bars(c):
    uns = [14, 26, 8, 30, 18, 22]
    srt = sorted(uns)
    g = []
    for k in range(6):
        x = 6 + k * 6.4
        hv = "%d;%d;%d;%d" % (uns[k], srt[k], srt[k], uns[k])
        yv = "%d;%d;%d;%d" % (40 - uns[k], 40 - srt[k], 40 - srt[k], 40 - uns[k])
        g.append(
            '<rect x="%s" y="%d" width="4.4" height="%d" rx="1.2" fill="%s" opacity="%.2f">' % (fmt(x), 40 - uns[k], uns[k], c, 0.55 + k * 0.08)
            + '<animate attributeName="height" values="%s" keyTimes="0;.4;.65;1" dur="5s" repeatCount="indefinite"/>' % hv
            + '<animate attributeName="y" values="%s" keyTimes="0;.4;.65;1" dur="5s" repeatCount="indefinite"/></rect>' % yv
        )
    return '<g>%s<path d="M4 41h40" stroke="%s" stroke-opacity=".5" stroke-width="1.5" stroke-linecap="round"/></g>' % ("".join(g), c)


def icon_doc(c):
    return """<g fill="none" stroke="%s" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M12 5h16l9 9v27a2 2 0 0 1-2 2H12a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z"/>
      <path d="M28 5v9h9" opacity=".8"/>
      <path d="M16 22h16M16 28h16" opacity=".8"/>
      <path d="M16 37v-4M21 37v-7M26 37v-5M31 37v-9" stroke-width="2.4"/>
    </g>""" % c


def chip(x, y, label):
    CW = 7.2
    w = len(label) * CW + 20
    s = (
        '<rect x="%s" y="%d" width="%s" height="24" rx="12" fill="%s" stroke="%s"/>' % (fmt(x), y, fmt(w), PANEL2, BORDER)
        + '<text x="%s" y="%d" class="mono" fill="%s" textLength="%s">%s</text>' % (fmt(x + 10), y + 16, BODY, fmt(len(label) * CW), esc(label))
    )
    return s, w


def card(name, title, tag, desc, chips, icon, accent, cta, cta_kind="link"):
    W, H, R = 560, 210, 18
    per = 2 * (W - 2 * R) + 2 * (H - 2 * R) + 2 * math.pi * R
    beam = 190
    x = 28
    chips_svg = []
    for label in chips:
        s, w = chip(x, 166, label)
        chips_svg.append(s)
        x += w + 8
    cta_w = len(cta) * 7.2 + 22
    if x - 8 + 16 + cta_w > W - 28:
        raise SystemExit("card %s: chips and link label overlap by %dpx" % (name, x - 8 + 16 + cta_w - (W - 28)))
    desc_svg = "".join(
        '<text x="28" y="%d" class="sans" font-size="15.5" fill="%s">%s</text>' % (112 + i * 23, BODY, esc(l))
        for i, l in enumerate(desc)
    )
    if cta_kind == "link":
        cta_svg = (
            '<g transform="translate(%d 182)" text-anchor="end">' % (W - 28)
            + '<text x="-16" y="0" class="mono" font-size="12" fill="%s">%s</text>' % (accent, esc(cta))
            + '<path transform="translate(-10 -10)" d="M1 9L9 1M3 1h6v6" fill="none" stroke="%s" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>' % accent
            + "</g>"
        )
    else:
        cta_svg = (
            '<g transform="translate(%d 182)" text-anchor="end">' % (W - 28)
            + '<text x="-16" y="0" class="mono" font-size="12" fill="%s">%s</text>' % (MUTED, esc(cta))
            + '<path transform="translate(-11 -11)" d="M2.5 5.5V4a3.5 3.5 0 0 1 7 0v1.5M2 5.5h8a1 1 0 0 1 1 1V10a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V6.5a1 1 0 0 1 1-1z" fill="none" stroke="%s" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>' % MUTED
            + "</g>"
        )
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="%(W)d" height="%(H)d" viewBox="0 0 %(W)d %(H)d" role="img" aria-labelledby="t">
<title id="t">%(title)s. %(alt)s</title>
<style>
  .sans{font-family:%(sans)s}
  .mono{font-family:%(mono)s;font-size:12px}
</style>
<defs>
  <clipPath id="c"><rect width="%(W)d" height="%(H)d" rx="%(R)d"/></clipPath>
  <radialGradient id="glow" cx="1" cy="0" r="1">
    <stop offset="0" stop-color="%(accent)s" stop-opacity=".28"/><stop offset=".6" stop-color="%(accent)s" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="topline" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="%(accent)s" stop-opacity="0"/><stop offset=".5" stop-color="%(accent)s" stop-opacity=".9"/><stop offset="1" stop-color="%(accent)s" stop-opacity="0"/>
  </linearGradient>
</defs>
<g clip-path="url(#c)">
  <rect width="%(W)d" height="%(H)d" rx="%(R)d" fill="%(panel)s"/>
  <rect width="%(W)d" height="%(H)d" fill="url(#glow)"/>
  <rect x="120" y="0" width="320" height="1.5" fill="url(#topline)"/>
</g>
<rect x=".75" y=".75" width="%(Wi)s" height="%(Hi)s" rx="%(R)d" fill="none" stroke="%(border)s"/>
<rect x=".75" y=".75" width="%(Wi)s" height="%(Hi)s" rx="%(R)d" fill="none" stroke="%(accent)s" stroke-width="1.6" stroke-linecap="round" stroke-dasharray="%(beam)s %(gap)s" opacity=".9">
  <animate attributeName="stroke-dashoffset" from="0" to="%(negper)s" dur="7s" repeatCount="indefinite"/>
</rect>
<rect x="28" y="28" width="48" height="48" rx="12" fill="%(accent)s" fill-opacity=".12" stroke="%(accent)s" stroke-opacity=".35"/>
<g transform="translate(28 28)">%(icon)s</g>
<text x="92" y="50" class="sans" font-size="22" font-weight="700" fill="%(text)s">%(title)s</text>
<text x="92" y="72" class="mono" fill="%(muted)s">%(tag)s</text>
%(desc)s
%(chips)s
%(cta)s
</svg>
""" % {
        "W": W, "H": H, "R": R, "Wi": fmt(W - 1.5), "Hi": fmt(H - 1.5),
        "title": esc(title), "alt": esc(" ".join(desc)), "sans": SANS, "mono": MONO,
        "accent": accent, "panel": PANEL, "border": BORDER, "text": TEXT, "muted": MUTED,
        "beam": fmt(beam), "gap": fmt(per - beam), "negper": fmt(-per),
        "icon": icon, "tag": esc(tag), "desc": desc_svg, "chips": "".join(chips_svg), "cta": cta_svg,
    }
    write(os.path.join("cards", name + ".svg"), svg)


def cards():
    card(
        "ankigpt",
        "AnkiGPT",
        "personal project  ·  2025 to now",
        [
            "Paste notes or upload a PDF and get an Anki deck back.",
            "Writes a cheat sheet first, then generates, validates and exports cards.",
        ],
        ["Python", "Flask", "OpenRouter", "Pydantic", "Celery"],
        icon_cards(BLUE),
        BLUE,
        "view repo",
    )
    card(
        "scanair",
        "ScanAir",
        "contract work  ·  2026",
        [
            "Drone mission planner. Turns a scan area into DJI-ready waypoint",
            "missions for 3D Gaussian Splatting capture, with terrain checks.",
        ],
        ["FastAPI", "React", "TypeScript", "Mapbox GL"],
        icon_route(GREEN),
        GREEN,
        "scanair.ca",
    )
    card(
        "tutor-bot",
        "AI Tutor Bot",
        "personal project  ·  2024",
        [
            "Discord bot that answers homework questions on demand.",
            "Routes simple questions to cheaper models to keep the API bill down.",
        ],
        ["Python", "Discord", "OpenAI", "Anthropic"],
        icon_bot(PURPLE),
        PURPLE,
        "private repo",
        cta_kind="lock",
    )
    card(
        "vcard",
        "VCard Manager",
        "course project  ·  2025",
        [
            "Contact manager with a Python frontend over a C backend.",
            "The parser ships as a dynamically linked C library.",
        ],
        ["C", "Python", "SQL"],
        icon_vcard(ORANGE),
        ORANGE,
        "coursework, private",
        cta_kind="lock",
    )
    card(
        "sorting",
        "Sorting Algorithm Visualizer",
        "personal project  ·  2023",
        [
            "Bubble, selection, insertion and quick sort, drawn bar by bar",
            "in the browser. Adjustable array size and a dark mode.",
        ],
        ["JavaScript", "HTML", "CSS"],
        icon_bars(YELLOW),
        YELLOW,
        "view repo",
    )
    card(
        "fruitfly-brain-mod",
        "Fruit Fly: A Small Mind",
        "personal project  ·  Minecraft mod",
        [
            "Fruit-fly neural simulation using real FlyWire connectivity.",
            "Minecraft ecology with a live brain activity visualizer.",
        ],
        ["Java", "Fabric", "Python"],
        icon_doc(PINK),
        PINK,
        "view repo",
    )


# --------------------------------------------------------------------------
# Footer waves
# --------------------------------------------------------------------------
def footer():
    W, H = 1200, 130

    def wave(amp, period, base, phase):
        pts = []
        x = -period
        while x <= W + period:
            y = base + amp * math.sin((x / period) * 2 * math.pi + phase)
            pts.append("%s %s" % (fmt(x), fmt(y)))
            x += period / 24
        return "M" + " L".join(pts) + " L%s %d L%s %d Z" % (fmt(W + period), H, fmt(-period), H)

    layers = [
        (16, 400, 70, 0.0, 10, ".18"),
        (20, 600, 80, 1.3, 15, ".28"),
        (12, 300, 92, 2.1, 8, ".55"),
    ]
    paths = []
    for amp, period, base, phase, dur, op in layers:
        d = wave(amp, period, base, phase)
        paths.append(
            '<path d="%s" fill="url(#g)" opacity="%s">' % (d, op)
            + '<animateTransform attributeName="transform" type="translate" from="0 0" to="%s 0" dur="%ds" repeatCount="indefinite"/></path>' % (fmt(-period), dur)
        )
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="%(W)d" height="%(H)d" viewBox="0 0 %(W)d %(H)d" role="img" aria-label="">
<defs>
  <linearGradient id="g" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="%(BLUE)s"/><stop offset=".5" stop-color="%(PURPLE)s"/><stop offset="1" stop-color="%(GREEN)s"/>
  </linearGradient>
  <clipPath id="c"><rect width="%(W)d" height="%(H)d"/></clipPath>
</defs>
<g clip-path="url(#c)">%(paths)s</g>
</svg>
""" % {"W": W, "H": H, "BLUE": BLUE, "PURPLE": PURPLE, "GREEN": GREEN, "paths": "".join(paths)}
    write("footer.svg", svg)


if __name__ == "__main__":
    hero()
    cards()
    footer()
