"""Shared drawing code for the micrograph graphics.

The tissue is built vector-first. A jittered hexagonal Voronoi tiling is warped
by a smooth noise field, so neighbouring cells keep sharing their edges, then
each cell is rounded and inset to leave a membrane. The grayscale electron
micrograph texture is rasterized from those outlines and embedded as a JPEG.
Colored segments are vector copies of the same outlines, animated with CSS
keyframes, so every frame lines up with the membranes underneath.

Animations are written as opacity curves sampled over one loop. The Motion
class simplifies each curve and deduplicates identical keyframes.
"""
from __future__ import annotations

import base64
import hashlib
import io
from html import escape
from pathlib import Path

import cv2
import numpy as np
import shapely
import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from PIL import Image
from scipy.spatial import Voronoi, cKDTree
from shapely.geometry import Polygon

HERE = Path(__file__).resolve().parent
FONT = HERE / 'fonts' / 'Archivo.ttf'
FPS = 12

# Segment colors after the FlyWire viewer; GLOW tints carry signals and highlights.
SEG = {'pink': '#ff5fa8', 'cyan': '#3fd0ff', 'yellow': '#ffd23f', 'green': '#7be36b', 'violet': '#b483ff'}
GLOW = {'pink': '#ffc4df', 'cyan': '#c9f2ff', 'yellow': '#fff0b3', 'green': '#dcffd2', 'violet': '#e8dbff'}
BAR, LABEL, VALUE, SUB, RULE = '#000000', '#8c8c8c', '#ffffff', '#b9b9b9', '#333333'


# ---------------------------------------------------------------- geometry

def hex_seeds(x0, y0, x1, y1, pitch, rng, jitter=0.36):
    rows = np.arange(y0, y1, pitch * 0.866)
    cols = np.arange(x0, x1, pitch)
    pts = [(x + (j % 2) * pitch / 2, y) for j, y in enumerate(rows) for x in cols]
    pts = np.array(pts, float)
    return pts + rng.uniform(-jitter, jitter, pts.shape) * pitch


class Field:
    """Smooth 2D noise from a few random plane waves; cheap and resolution free."""

    def __init__(self, rng, wavelength, n=5):
        self.f = 2 * np.pi / (wavelength * rng.uniform(0.7, 1.6, n))
        self.a = rng.uniform(0, np.pi, n)
        self.p = rng.uniform(0, 2 * np.pi, n)

    def __call__(self, x, y):
        x, y = np.asarray(x, float)[..., None], np.asarray(y, float)[..., None]
        proj = x * np.cos(self.a) + y * np.sin(self.a)
        return np.sin(proj * self.f + self.p).mean(-1) * 1.6


def chaikin(ring, passes=2):
    for _ in range(passes):
        nxt = np.roll(ring, -1, axis=0)
        ring = np.stack([ring * 0.75 + nxt * 0.25, ring * 0.25 + nxt * 0.75], 1).reshape(-1, 2)
    return ring


def largest(geom):
    if geom.is_empty:
        return None
    if geom.geom_type == 'Polygon':
        return geom
    parts = [g for g in getattr(geom, 'geoms', []) if g.geom_type == 'Polygon']
    return max(parts, key=lambda g: g.area) if parts else None


class Tissue:
    """A field of cell profiles with exact outlines and a matching texture."""

    def __init__(self, w, h, pitch, seed, k=2, holes=0.24, seeds=None, somata=()):
        self.w, self.h, self.k, self.pitch, self.seed = w, h, k, pitch, seed
        rng = np.random.default_rng(seed)
        m = 3 * pitch
        if seeds is None:
            seeds = hex_seeds(-m, -m, w + m, h + m, pitch, rng)
            clump = Field(rng, pitch * 7)(seeds[:, 0], seeds[:, 1])
            seeds = seeds[rng.random(len(seeds)) > holes * (0.45 + 0.75 * clump)]
            # Bundles of fine axons: patches where profiles are about half the size.
            bundle = Field(rng, pitch * 9)
            seeds = seeds[bundle(seeds[:, 0], seeds[:, 1]) < 0.5]
            fine = rng.uniform([-m, -m], [w + m, h + m], (int((w + 2 * m) * (h + 2 * m) / (0.5 * pitch) ** 2), 2))
            seeds = np.vstack([seeds, fine[bundle(fine[:, 0], fine[:, 1]) >= 0.5]])
        seeds = np.asarray(seeds, float)
        for sx, sy, radius in somata:
            far = np.hypot(seeds[:, 0] - sx, seeds[:, 1] - sy) > radius
            seeds = np.vstack([seeds[far], [[sx, sy]]])
        self.somata = [len(seeds) - len(somata) + i for i in range(len(somata))]

        bound = np.array([[-1e4, -1e4], [1e4, -1e4], [-1e4, 1e4], [1e4, 1e4]])
        vor = Voronoi(np.vstack([seeds, bound]))
        wx, wy = Field(rng, pitch * 4.5), Field(rng, pitch * 4.5)
        amp = 0.2 * pitch
        clip = shapely.box(-m, -m, w + m, h + m)
        gap = self.gap = max(0.5, 0.042 * pitch)
        self.fused = []

        self.cells, self.seed_of = [], []
        for i in range(len(seeds)):
            region = vor.regions[vor.point_region[i]]
            if not region or -1 in region:
                continue
            poly = largest(Polygon(vor.vertices[region]).intersection(clip))
            if poly is None or poly.area < 1:
                continue
            ring = np.asarray(shapely.segmentize(poly, pitch / 5).exterior.coords)[:-1]
            ring = ring + amp * np.stack([wx(ring[:, 0], ring[:, 1]), wy(ring[:, 0], ring[:, 1])], 1)
            cell = largest(Polygon(chaikin(ring)).buffer(-gap))
            if cell is None or cell.area < 2:
                continue
            self.cells.append(cell)
            self.seed_of.append(i)
        self.n = len(self.cells)
        c = np.array([[p.centroid.x, p.centroid.y] for p in self.cells])
        self.cx, self.cy = c[:, 0], c[:, 1]
        self.area = np.array([p.area for p in self.cells])
        self.tree = cKDTree(c)
        self.visible = (self.cx > -pitch) & (self.cx < w + pitch) & (self.cy > -pitch) & (self.cy < h + pitch)
        self.nuclei = {}
        index = {s: j for j, s in enumerate(self.seed_of)}
        self.somata = [index[s] for s in self.somata if s in index]
        self._label()

    def _label(self):
        k = self.k
        lab = np.zeros((round(self.h * k), round(self.w * k)), np.int32)
        for i, cell in enumerate(self.cells):
            pts = np.round(np.asarray(cell.exterior.coords) * k).astype(np.int32)
            cv2.fillPoly(lab, [pts], i + 1)
        self.label = lab

    def cell_at(self, x, y):
        """Cell index under each point, or -1 on a membrane."""
        H, W = self.label.shape
        xi = np.clip((np.asarray(x) * self.k).astype(int), 0, W - 1)
        yi = np.clip((np.asarray(y) * self.k).astype(int), 0, H - 1)
        return self.label[yi, xi] - 1

    def path(self, i):
        poly = largest(self.cells[i].buffer(-0.3).simplify(0.3)) or self.cells[i]
        if i in self.nuclei:
            poly = poly.difference(self._nucleus(i))
        return outline(poly)

    def add_nuclei(self, cells, seed=0):
        """Give cells a nucleus: drawn dark in the texture, cut out of the overlay."""
        rng = np.random.default_rng(seed)
        for i in cells:
            r = np.sqrt(self.area[i] / np.pi)
            self.nuclei[int(i)] = (self.cx[i], self.cy[i], r * rng.uniform(0.34, 0.4), r * rng.uniform(0.28, 0.33), rng.uniform(0, 180))

    def _nucleus(self, i):
        cx, cy, rx, ry, ang = self.nuclei[i]
        a = np.linspace(0, 2 * np.pi, 24, endpoint=False)
        c, s = np.cos(np.radians(ang)), np.sin(np.radians(ang))
        x, y = rx * np.cos(a), ry * np.sin(a)
        return Polygon(np.c_[cx + x * c - y * s, cy + x * s + y * c])

    def fuse(self, cells, lines=()):
        """Join cells into one continuous profile: a neurite lying in the section.

        Returns the joined outline. lines are centerlines, used to draw
        microtubules and elongated mitochondria along the process."""
        cells = sorted(int(i) for i in cells)
        shape = shapely.union_all([self.cells[i].buffer(self.gap * 1.3) for i in cells]).buffer(-self.gap * 0.3)
        k = self.k
        for poly in getattr(shape, 'geoms', [shape]):
            rings = [poly.exterior, *poly.interiors]
            cv2.fillPoly(self.label, [np.round(np.asarray(r.coords) * k).astype(np.int32) for r in rings], cells[0] + 1)
        self.fused.append((cells, list(lines)))
        return shape

    # ------------------------------------------------------------ texture

    def texture(self, quality=70):
        """Grayscale EM texture as a base64 JPEG data URI."""
        k = self.k
        rng = np.random.default_rng(self.seed + 1)
        lab = self.label
        H, W = lab.shape
        n = self.n
        base = rng.normal(148, 12, n + 1).clip(116, 180)
        base[1:][rng.random(n) < 0.05] = 96          # dense glial and dark profiles
        base[0] = 40
        img = base[lab].astype(np.float32)
        dist = cv2.distanceTransform((lab > 0).astype(np.uint8), cv2.DIST_L2, 3)
        img -= (img - 38) * np.exp(-dist / (0.7 * k))

        fused = {i for cells, _ in self.fused for i in cells}
        for cells, lines in self.fused:
            gid = cells[0] + 1
            mask = lab == gid
            img[mask] += 8
            streak = img.copy()
            for line in lines:
                pts = np.asarray(line) * k
                tang = np.gradient(pts, axis=0)
                norm = np.c_[-tang[:, 1], tang[:, 0]] / (np.hypot(*tang.T)[:, None] + 1e-9)
                for off, tone in [(-0.26, -10), (-0.1, 8), (0.06, -9), (0.2, 7)]:
                    poly = (pts + norm * off * self.pitch * k).astype(np.int32)
                    cv2.polylines(streak, [poly], False, float(base[gid] + 8 + tone), max(1, int(0.6 * k)), cv2.LINE_AA)
                for j in rng.choice(len(pts), max(1, len(pts) // 420), replace=False):
                    ang = np.degrees(np.arctan2(tang[j, 1], tang[j, 0]))
                    cv2.ellipse(streak, tuple(pts[j].astype(int)), (int(0.9 * self.pitch * k), int(0.2 * self.pitch * k)), ang, 0, 360, 112, -1, cv2.LINE_AA)
            img = np.where(mask, streak, img)
        radius = np.sqrt(self.area / np.pi) * k
        for i in self.somata:
            cx, cy, r = self.cx[i] * k, self.cy[i] * k, radius[i]
            cv2.ellipse(img, (int(cx), int(cy)), (int(r * 0.56), int(r * 0.5)), 20, 0, 360, 118, -1, cv2.LINE_AA)
            cv2.ellipse(img, (int(cx), int(cy)), (int(r * 0.56), int(r * 0.5)), 20, 0, 360, 62, max(1, int(k)), cv2.LINE_AA)
            for _ in range(70):
                a, d = rng.uniform(0, 2 * np.pi), rng.uniform(0, r * 0.45)
                cv2.circle(img, (int(cx + np.cos(a) * d), int(cy + np.sin(a) * d)), int(rng.uniform(1, 2.2) * k / 2), 92, -1, cv2.LINE_AA)
            cv2.circle(img, (int(cx + r * 0.12), int(cy - r * 0.08)), int(r * 0.12), 70, -1, cv2.LINE_AA)

        for i, (cx, cy, rx, ry, ang) in self.nuclei.items():
            centre, axes = (int(cx * k), int(cy * k)), (int(rx * k), int(ry * k))
            cv2.ellipse(img, centre, axes, ang, 0, 360, 104, -1, cv2.LINE_AA)
            for _ in range(int(rx * ry * 0.25)):
                a, d = rng.uniform(0, 2 * np.pi), rng.uniform(0, 0.8)
                cv2.circle(img, (int(centre[0] + np.cos(a) * d * axes[0]), int(centre[1] + np.sin(a) * d * axes[1])), max(1, int(k * 0.7)), 84, -1, cv2.LINE_AA)
            cv2.ellipse(img, centre, axes, ang, 0, 360, 58, max(1, int(k * 0.8)), cv2.LINE_AA)
        for i in range(n):
            if not self.visible[i] or i in self.somata or i in fused or i in self.nuclei:
                continue
            cx, cy, r = self.cx[i] * k, self.cy[i] * k, radius[i]
            roll = rng.random()
            if roll < 0.09 and r > 4 * k:              # synaptic vesicle cluster
                vr = max(1.6, 0.07 * self.pitch * k)
                for _ in range(int(rng.integers(10, 24))):
                    a, d = rng.uniform(0, 2 * np.pi), rng.uniform(0, r * 0.55)
                    c = (int(cx + np.cos(a) * d), int(cy + np.sin(a) * d))
                    cv2.circle(img, c, int(vr), 166, -1, cv2.LINE_AA)
                    cv2.circle(img, c, int(vr), 72, max(1, int(k * 0.6)), cv2.LINE_AA)
            elif roll < 0.15 and r > 5 * k:            # mitochondrion with cristae
                ang = rng.uniform(0, 180)
                ax = (int(r * 0.42), int(r * 0.2))
                cv2.ellipse(img, (int(cx), int(cy)), ax, ang, 0, 360, 92, -1, cv2.LINE_AA)
                cv2.ellipse(img, (int(cx), int(cy)), ax, ang, 0, 360, 48, max(1, int(k * 0.7)), cv2.LINE_AA)
                ca, sa = np.cos(np.radians(ang)), np.sin(np.radians(ang))
                for t in np.linspace(-0.7, 0.7, 5):
                    px, py = cx + ca * ax[0] * t, cy + sa * ax[0] * t
                    cv2.line(img, (int(px - sa * ax[1] * 0.7), int(py + ca * ax[1] * 0.7)),
                             (int(px + sa * ax[1] * 0.7), int(py - ca * ax[1] * 0.7)), 130, max(1, int(k * 0.5)), cv2.LINE_AA)
            elif roll < 0.2:                           # postsynaptic density on the membrane
                ring = np.asarray(self.cells[i].exterior.coords) * k
                j = int(rng.integers(0, len(ring) - 4))
                cv2.polylines(img, [ring[j:j + 4].astype(np.int32)], False, 30, max(2, int(0.13 * self.pitch * k)), cv2.LINE_AA)

        lo = rng.normal(0, 1, (H // (7 * k) + 2, W // (7 * k) + 2)).astype(np.float32)
        img += cv2.resize(lo, (W, H), interpolation=cv2.INTER_CUBIC) * 8
        img = cv2.GaussianBlur(img, (0, 0), 0.55 * k)
        img += rng.normal(0, 7, img.shape).astype(np.float32)
        out = io.BytesIO()
        Image.fromarray(img.clip(0, 255).astype(np.uint8), 'L').save(out, 'JPEG', quality=quality, optimize=True, progressive=True)
        return 'data:image/jpeg;base64,' + base64.b64encode(out.getvalue()).decode()


# ---------------------------------------------------------------- type

class Type:
    """Archivo set as vector outlines; GitHub will not load fonts inside images."""

    def __init__(self):
        self.face = hb.Face(hb.Blob.from_file_path(str(FONT)))
        self.fonts = {}

    def _font(self, wght, wdth):
        if (wght, wdth) not in self.fonts:
            font = hb.Font(self.face)
            font.set_variations({'wght': wght, 'wdth': wdth})
            self.fonts[wght, wdth] = font
        return self.fonts[wght, wdth]

    def _shape(self, text, wght, wdth):
        font = self._font(wght, wdth)
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(font, buf, {'kern': True, 'liga': True})
        return font, buf

    def width(self, text, size, wght=400, wdth=100):
        _, buf = self._shape(text, wght, wdth)
        return sum(p.x_advance for p in buf.glyph_positions) * size / self.face.upem

    def __call__(self, text, x, y, size, wght=400, wdth=100, fill=VALUE, anchor='start', attrs=''):
        font, buf = self._shape(text, wght, wdth)
        s = size / self.face.upem
        width = sum(p.x_advance for p in buf.glyph_positions) * s
        x -= {'start': 0, 'middle': width / 2, 'end': width}[anchor]
        pen = SVGPathPen(None, ntos=lambda v: f'{v:.2f}'.rstrip('0').rstrip('.'))
        cursor = 0
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            font.draw_glyph_with_pen(info.codepoint, TransformPen(pen, (s, 0, 0, -s, x + (cursor + pos.x_offset) * s, y - pos.y_offset * s)))
            cursor += pos.x_advance
        return f'<path d="{pen.getCommands()}" fill="{fill}"{attrs}/>'


# ---------------------------------------------------------------- motion

def simplify(t, v, eps):
    """Douglas-Peucker on a sampled curve; keeps the stops a linear tween needs."""
    keep = np.zeros(len(t), bool)
    keep[[0, -1]] = True
    stack = [(0, len(t) - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        line = v[a] + (v[b] - v[a]) * (t[a + 1:b] - t[a]) / (t[b] - t[a])
        err = np.abs(v[a + 1:b] - line)
        i = int(err.argmax())
        if err[i] > eps:
            keep[a + 1 + i] = True
            stack += [(a, a + 1 + i), (a + 1 + i, b)]
    return t[keep], v[keep]


def num(v):
    out = f'{v:.2f}'.rstrip('0').rstrip('.')
    return out.replace('0.', '.', 1) if out.startswith('0.') else (out or '0')


def pct(v):
    return f'{v:.1f}'.rstrip('0').rstrip('.') or '0'


def outline(geom):
    """SVG path data for a polygon or multipolygon, holes included."""
    d = ''
    for poly in getattr(geom, 'geoms', [geom]):
        for ring in [poly.exterior, *poly.interiors]:
            pts = np.asarray(ring.coords)[:-1]
            d += 'M' + 'L'.join(f'{x:.1f} {y:.1f}' for x, y in pts) + 'Z'
    return d


class Motion:
    """One looping timeline. Curves become deduplicated @keyframes rules."""

    def __init__(self, period, prefix='k'):
        self.period, self.prefix = period, prefix
        self.t = np.linspace(0, period, int(round(period * FPS)) + 1)
        self.rules = {}

    def keyframes(self, values, eps=0.03):
        t, v = simplify(self.t, np.round(np.clip(values, 0, 1), 3), eps)
        body = ''.join(f'{pct(ti / self.period * 100)}%{{opacity:{num(vi)}}}' for ti, vi in zip(t, v))
        name = self.prefix + hashlib.md5(body.encode()).hexdigest()[:6]
        self.rules[name] = body
        return name

    def css(self):
        return ''.join(f'@keyframes {n}{{{b}}}' for n, b in self.rules.items())


def ramp(t, a, b):
    return np.clip((np.asarray(t, float) - a) / (b - a), 0, 1)


def ease(x):
    return x * x * (3 - 2 * x)


def transient(dt, rise=0.25, decay=1.2):
    """Calcium-indicator style response: quick rise, slow exponential decay."""
    dt = np.asarray(dt, float)
    up = ease(np.clip(dt / rise, 0, 1))
    return np.where(dt < 0, 0, np.where(dt < rise, up, np.exp(-(dt - rise) / decay)))


def periodic(dt, period):
    """Wrap a time offset into (-period/2, period/2] so loops join seamlessly."""
    return (np.asarray(dt) + period / 2) % period - period / 2


# ---------------------------------------------------------------- svg

class Overlay:
    """Collects animated <use> copies of cell outlines, per layer."""

    def __init__(self, tissue, motion, static_t):
        self.T, self.motion = tissue, motion
        self.static = int(round(static_t * FPS))
        self.defs, self.uses = {}, []

    def add(self, cls, curves, floor=0.04):
        for i, curve in curves.items():
            if curve.max() < floor or not self.T.visible[i]:
                continue
            if np.ptp(curve) < 0.01:
                self.still(cls, {i: curve.mean()})
                continue
            self.defs.setdefault(i, self.T.path(i))
            name = self.motion.keyframes(curve)
            self.uses.append(f'<use href="#c{i}" class="a {cls}" opacity="{num(curve[self.static])}" style="animation-name:{name}"/>')

    def shared(self, cls, delays, curve):
        """Cells running one curve, each shifted by its own delay."""
        name = self.motion.keyframes(curve)
        for i, delay in delays.items():
            if not self.T.visible[i]:
                continue
            self.defs.setdefault(i, self.T.path(i))
            self.uses.append(f'<use href="#c{i}" class="a {cls}" opacity="0" style="animation-name:{name};animation-delay:{num(delay)}s"/>')

    def still(self, cls, values):
        for i, v in values.items():
            self.defs.setdefault(i, self.T.path(i))
            self.uses.insert(0, f'<use href="#c{i}" class="{cls}" opacity="{num(v)}"/>')

    def svg(self):
        rule = lambda i: ' fill-rule="evenodd"' if i in self.T.nuclei else ''
        return ('<defs>' + ''.join(f'<path id="c{i}" d="{d}"{rule(i)}/>' for i, d in self.defs.items()) + '</defs>',
                '<g>' + ''.join(self.uses) + '</g>')


def layer_css(layers):
    return ''.join(f'.{cls}{{fill:{color}}}' for cls, color in layers.items())


def document(w, h, title, desc, css, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-labelledby="t d">\n<title id="t">{escape(title)}</title>\n<desc id="d">{escape(desc)}</desc>\n'
            f'<style>{css}@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}.motion{{display:none}}}}</style>\n'
            f'{body}\n</svg>\n')


def base_css(period):
    return f'.a{{animation:{num(period)}s linear infinite}}'


def field_columns(type_, fields, x_end, y, col, label_size, value_size, dot=None):
    """Labelled fields in the style of an SEM data bar, right-aligned to x_end."""
    out = ''
    x = x_end - col * len(fields)
    for label, value in fields:
        out += f'<rect x="{x - 14:.1f}" y="{y - label_size - 10:.1f}" width="1" height="{label_size + value_size + 22:.1f}" fill="{RULE}"/>'
        out += type_(label, x, y, label_size, 400, 80, LABEL)
        vx = x
        if dot and label == dot:
            out += (f'<circle class="breathe" cx="{x + value_size * 0.3:.1f}" cy="{y + value_size * 1.02:.1f}" '
                    f'r="{value_size * 0.27:.1f}" fill="{SEG["green"]}"/>')
            vx += value_size * 0.9
        out += type_(value, vx, y + value_size * 1.38, value_size, 500, 80, VALUE)
        x += col
    return out
