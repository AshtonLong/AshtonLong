"""Generate self-contained profile SVGs with python assets/generate.py.
Design reference: https://ashtonlong.github.io/ (September 2026).
No external fonts, scripts or animation. Pixel lettering uses vector squares.
"""
from html import escape
from pathlib import Path
import random
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
BG, FG, MINT = '#000000', '#ffffff', '#b9e5cc'
BODY, MUTED, LINE = '#d2d2d2', '#a9a9a9', '#2e2e2e'
SANS = "'Inter','Segoe UI',Arial,sans-serif"
MONO = "'JetBrains Mono',Consolas,'Liberation Mono',monospace"
GLYPHS = {
    'A': ['01110','10001','10001','11111','10001','10001','10001'],
    'S': ['01111','10000','10000','01110','00001','00001','11110'],
    'H': ['10001','10001','10001','11111','10001','10001','10001'],
    'T': ['11111','00100','00100','00100','00100','00100','00100'],
    'O': ['01110','10001','10001','10001','10001','10001','01110'],
    'N': ['10001','11001','11001','10101','10011','10011','10001'],
    'L': ['10000','10000','10000','10000','10000','10000','11111'],
    'G': ['01110','10001','10000','10111','10001','10001','01110'],
}


def rect(x, y, w, h, fill, extra=''):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" {extra}/>'


def text(x, y, value, size=14, color=MUTED, mono=True, extra=''):
    return (f'<text x="{x}" y="{y}" font-family="{MONO if mono else SANS}" '
            f'font-size="{size}" fill="{color}" {extra}>{escape(value)}</text>')


def rule(x1, y1, x2, y2, color=LINE):
    return f'<path d="M{x1} {y1}L{x2} {y2}" stroke="{color}"/>'


def pixels(word, x, y, step, color=FG):
    return '<g aria-hidden="true">' + ''.join(
        rect(x + (i * 6 + col) * step, y + row * step, step - 1, step - 1, color)
        for i, letter in enumerate(word) for row, cells in enumerate(GLYPHS[letter])
        for col, cell in enumerate(cells) if cell == '1'
    ) + '</g>'


def frame(w, h, title, content, grid=False):
    background = rect(0, 0, w, h, BG)
    if grid:
        background += ('<defs><pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse">'
                       '<rect x="11" y="11" width="1" height="1" fill="#242424"/>'
                       '</pattern></defs>' + rect(0, 0, w, h, 'url(#dots)'))
        background += ''.join(rule(x, 0, x, h, '#101612') for x in range(36, w, 92))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img" aria-labelledby="title">\n'
            f'<title id="title">{escape(title)}</title>\n{background}\n{content}\n</svg>\n')


def write(name, svg):
    ET.fromstring(svg)
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding='utf-8', newline='\n')
    print(f'wrote {path.relative_to(HERE)}')


def hero(mobile=False):
    w, h = (480, 410) if mobile else (960, 440)
    x = 28 if mobile else 40
    s = pixels('A', x, 22, 3, MINT)
    s += text(x + 28, 38, 'ASHTON LONG / GITHUB', 11, BODY, extra='letter-spacing="2"')
    s += rule(x, 62, w - x, 62)
    s += rect(x, 91, 6, 6, MINT) + text(x + 17, 98, 'Open to software developer co-op roles', 12, BODY)
    s += pixels('ASHTON', x, 128, 11 if mobile else 12)
    s += pixels('LONG', x, 225 if mobile else 231, 11 if mobile else 12, MINT)
    s += text(x, 334 if mobile else 348, 'Full-stack & AI developer.', 24 if mobile else 28, FG, False, 'font-weight="600" letter-spacing="-0.7"')
    s += text(x, 362 if mobile else 378, '4th-year Computer Science co-op', 13, BODY)
    s += text(x, 384 if mobile else 400, 'University of Guelph · Ontario, Canada', 13, MUTED)
    if not mobile:
        s += rect(576, 94, 344, 218, '#050906', f'stroke="{LINE}"')
        rng = random.Random(7)
        for row in range(5):
            for col in range(13):
                if rng.random() > .64:
                    s += rect(600 + col * 24, 113 + row * 24, 10, 10, MINT,
                              f'opacity="{rng.choice([.10, .18, .28, .45])}"')
        s += text(600, 265, 'CS × REAL-WORLD SOFTWARE', 12, MINT, extra='letter-spacing="1"')
        s += text(600, 289, 'GEOMETRY / AGENTS / NEURAL SYSTEMS', 11, MUTED)
        for cx in [573, 917]:
            for cy in [91, 309]:
                s += rect(cx, cy, 6, 6, MINT)
        s += text(576, 348, 'CURRENTLY', 11, MUTED, extra='letter-spacing="2"')
        s += text(576, 376, 'Software Developer · ScanAir', 18, BODY, False)
        s += text(576, 400, 'FastAPI / React / TypeScript / Mapbox GL', 12, MUTED)
    s += rule(0, h - 1, w, h - 1, '#40594b')
    write('hero-mobile.svg' if mobile else 'hero.svg', frame(w, h,
          'Ashton Long. Full-stack and AI developer. Fourth-year Computer Science co-op student at the University of Guelph. Open to software developer co-op roles.', s, True))


PROJECTS = [
    ('ankigpt', '01', 'AnkiGPT', 'PERSONAL PROJECT / 2025 TO NOW', 'SOURCE → CARDS → REVIEW'),
    ('scanair', '02', 'ScanAir', 'CONTRACT WORK / 2026', 'AREA → GEOMETRY → MISSION'),
    ('fruitfly-brain-mod', '03', 'Fruit Fly: A Small Mind', 'PERSONAL PROJECT / MINECRAFT MOD', 'CONNECTIVITY → SIMULATION'),
]


def schematic(kind):
    s = ''
    if kind == 'ankigpt':
        for x, y in [(680, 33), (710, 43), (740, 53)]:
            s += rect(x, y, 98, 91, '#080d0a', f'stroke="{LINE}"')
            s += rule(x + 17, y + 28, x + 71, y + 28, MINT)
            s += rule(x + 17, y + 44, x + 59, y + 44)
            s += rule(x + 17, y + 60, x + 66, y + 60)
        s += '<path d="M806 116l7 7 14-18" fill="none" stroke="#b9e5cc" stroke-width="2"/>'
    elif kind == 'scanair':
        s += '<path d="M671 137l24-100 172 14 21 73-84 23z" fill="#080d0a" stroke="#40594b"/>'
        s += '<path d="M698 119V59h29v65h29V60h29v66h29V61h29v57" fill="none" stroke="#b9e5cc" stroke-width="2"/>'
        s += rect(695, 116, 6, 6, FG) + rect(840, 115, 6, 6, MINT)
    else:
        points = [(685, 83), (734, 41), (742, 125), (799, 70), (837, 129), (875, 43)]
        for a, b in [(0, 1), (0, 2), (1, 3), (2, 3), (2, 4), (3, 4), (3, 5), (4, 5)]:
            s += rule(*points[a], *points[b], '#40594b')
        for i, (x, y) in enumerate(points):
            s += rect(x - 4, y - 4, 8, 8, MINT if i in [0, 3, 5] else '#526c5e')
    return s


def cards():
    for name, number, title, label, caption in PROJECTS:
        for mobile in [False, True]:
            w, h = (480, 146) if mobile else (960, 186)
            x = 28 if mobile else 36
            s = text(x, 32, f'{number} / {label}', 10 if mobile else 11, MINT, extra='letter-spacing="1"')
            s += text(x, 83 if mobile else 94, title, 29 if mobile else 38, FG, False, 'font-weight="600" letter-spacing="-1"')
            s += text(x, 118 if mobile else 148, caption, 11, MUTED, extra='letter-spacing="1"')
            if not mobile:
                s += rule(629, 22, 629, 164) + schematic(name)
            s += rule(0, h - 1, w, h - 1)
            suffix = '-mobile' if mobile else ''
            write(f'cards/{name}{suffix}.svg', frame(w, h, f'{number}. {title}. {label}.', s))


def footer():
    s = rule(28, 22, 932, 22, '#40594b')
    s += pixels('A', 28, 45, 3, MINT)
    s += text(57, 61, 'ASHTON LONG', 12, BODY, extra='letter-spacing="2"')
    s += text(932, 61, 'CS × REAL-WORLD SOFTWARE', 12, MINT, extra='text-anchor="end" letter-spacing="1"')
    write('footer.svg', frame(960, 90, 'Ashton Long. CS × real-world software.', s))


if __name__ == '__main__':
    hero()
    hero(mobile=True)
    cards()
    footer()
