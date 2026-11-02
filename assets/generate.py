"""Generate the animated micrograph profile graphics: python assets/generate.py

Writes the hero and the three project panels, each with a phone layout.
The contribution graphic is built separately by activity.py in CI.
"""
from pathlib import Path

import numpy as np
import shapely
from scipy.spatial import cKDTree
from shapely.geometry import LineString, Point, Polygon

from micrograph import (BAR, GLOW, SEG, SUB, Motion, Overlay, Tissue, Type, base_css, document, ease, field_columns,
                        layer_css, num, outline, pct, periodic, ramp, transient)

HERE = Path(__file__).resolve().parent
TYPE = Type()


def write(name, svg):
    path = HERE / name
    path.parent.mkdir(exist_ok=True)
    path.write_text(svg, encoding='utf-8')
    print(f'{name}: {len(svg.encode()) / 1024:.0f} KB')


def tissue_image(T, w, h, quality=68):
    return f'<image width="{w}" height="{h}" preserveAspectRatio="none" href="{T.texture(quality)}"/>'


def polyline(pts):
    return 'M' + 'L'.join(f'{x:.1f} {y:.1f}' for x, y in pts[::3]) + f'L{pts[-1][0]:.1f} {pts[-1][1]:.1f}'


# ================================================================ hero
# Three neurites, one per project, lie in the section. On load each is traced
# from its root by a travelling light; afterwards slow signals keep moving out
# along every branch, at a different rhythm for each neuron.

NEURONS = [
    dict(color='pink', label='Fruit Fly', start=0.4, period=17, bumps=(0, 0.55), soma=(0.11, 0.7),
         anchor=(0.93, 0.42), branches=[
             [(0.11, 0.70), (0.21, 0.53), (0.40, 0.48), (0.58, 0.40), (0.78, 0.47), (1.04, 0.38)],
             [(0.40, 0.48), (0.45, 0.27), (0.50, -0.06)],
             [(0.78, 0.47), (0.85, 0.72), (0.91, 1.06)],
             [(0.11, 0.70), (0.05, 0.85), (-0.04, 0.93)]]),
    dict(color='cyan', label='AnkiGPT', start=1.6, period=19, bumps=(0, 0.47), anchor=(0.25, 0.17), branches=[
        [(0.27, -0.06), (0.25, 0.20), (0.31, 0.42), (0.29, 0.66), (0.36, 1.06)],
        [(0.25, 0.20), (0.14, 0.31), (-0.04, 0.27)],
        [(0.29, 0.66), (0.20, 0.80), (0.17, 1.06)]]),
    dict(color='yellow', label='ScanAir', start=2.8, period=23, bumps=(0, 0.5), anchor=(0.75, 0.27), branches=[
        [(0.60, 1.06), (0.64, 0.76), (0.70, 0.55), (0.74, 0.28), (0.80, -0.06)],
        [(0.74, 0.28), (0.88, 0.17), (1.04, 0.20)],
        [(0.64, 0.76), (0.52, 0.86), (0.44, 1.06)]]),
]
FIELDS = [('status', 'Open to co-op'), ('now', 'ScanAir, contract'), ('based in', 'Guelph, Ontario')]
PULSE = [(110, 0.2), (64, 0.3), (26, 0.5)]   # dash length in px, opacity: a soft travelling light


def catmull(points, step=1.5):
    """Dense Catmull-Rom polyline through control points."""
    p = np.vstack([points[0], points, points[-1]])
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        n = max(2, int(np.hypot(*(p2 - p1)) / step))
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append(0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3))
    out.append(p[-2])
    return np.array(out)


def trace(T, branches, w, h, taken):
    """Cells along a branching neuron, plus each branch's centerline and root distance."""
    pts, dist, rad, lines = np.empty((0, 2)), np.empty(0), np.empty(0), []
    for b, ctrl in enumerate(branches):
        line = catmull(np.array(ctrl) * [w, h])
        s = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(line, axis=0).T))])
        s0 = dist[np.argmin(np.hypot(*(pts - line[0]).T))] if b else 0.0
        lines.append((line, s0, s[-1]))
        r = np.full(len(line), T.pitch * (0.55 if b == 0 else 0.34))
        pts, dist, rad = np.vstack([pts, line]), np.concatenate([dist, s + s0]), np.concatenate([rad, r])
    cells = {i for i in T.cell_at(pts[:, 0], pts[:, 1]) if i >= 0 and i not in taken}
    d, j = cKDTree(pts).query(np.c_[T.cx, T.cy])
    cells |= {i for i in np.where(d < rad[j])[0] if i not in taken}
    return cells, lines, pts, dist


def pulse_rule(name, a, amax, travel, period, bumps):
    """Dash-offset keyframes moving one dash along a pathLength=1 path, once per bump."""
    lo, hi = a / 2 + amax / 2, a / 2 - 1 - amax / 2
    stops = [] if bumps[0] == 0 else [(0, hi, True)]
    for b in bumps:
        stops += [(b * period, lo, False), (b * period + travel, hi, True)]
    stops.append((period, hi, False))
    body = ''.join(f'{pct(t / period * 100)}%{{stroke-dashoffset:{o:.4f}{";animation-timing-function:step-end" if jump else ""}}}'
                   for t, o, jump in stops)
    return f'@keyframes {name}{{{body}}}'


def hero(mobile=False):
    W, TH, BH = (600, 300, 150) if mobile else (960, 330, 110)
    speed = 135 if mobile else 170
    pitch = 14
    sx, sy = NEURONS[0]['soma']
    T = Tissue(W, TH, pitch, seed=7 if mobile else 4, somata=[(sx * W, sy * TH, pitch * 1.9)])

    css = ['@keyframes draw{from{stroke-dashoffset:1.001}to{stroke-dashoffset:0}}',
           '@keyframes in{from{opacity:0}to{opacity:1}}',
           '.breathe{animation:breathe 3.6s ease-in-out infinite}@keyframes breathe{0%,100%{opacity:.3}50%{opacity:1}}']
    clips, groups, chips, taken = [], [], [], set()
    width = 3.4 * pitch

    for ni, n in enumerate(NEURONS):
        color, glow, P = SEG[n['color']], GLOW[n['color']], n['period']
        cells, lines, pts, dist = trace(T, n['branches'], W, TH, taken)
        taken |= cells
        shape = T.fuse(cells, [line for line, _, _ in lines])
        clips.append(f'<clipPath id="u{ni}"><path d="{outline(shape.buffer(-0.35).simplify(0.25))}"/></clipPath>')

        base, light = '', ''
        if 'soma' in n:
            cx, cy = sx * W, sy * TH
            base += f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{pitch * 2.4:.1f}" fill="{color}" stroke="none" style="animation:in 1s ease-out {n["start"]}s both"/>'
            m = Motion(P, prefix='s')
            name = m.keyframes(sum(transient(periodic(m.t - b * P, P), 0.3, 1.1) for b in n['bumps']) * 0.7)
            css.append(m.css())
            light += f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{pitch * 2.4:.1f}" fill="{glow}" stroke="none" opacity="0" style="animation:{name} {P}s linear {n["start"] - 0.3:.2f}s infinite"/>'
        for bi, (line, s0, length) in enumerate(lines):
            d = polyline(line)
            delay = n['start'] + s0 / speed
            base += f'<path d="{d}" pathLength="1" stroke-dasharray="1 1" style="animation:draw {length / speed:.2f}s linear {delay:.2f}s both"/>'
            amax = PULSE[0][0] / length
            travel = (1 + amax) * length / speed
            for pi, (dash, op) in enumerate(PULSE):
                rule = f'p{ni}{bi}{pi}'
                css.append(pulse_rule(rule, dash / length, amax, travel, P, n['bumps']))
                hidden = dash / length / 2 + amax / 2      # parked before the start; also the reduced-motion state
                light += (f'<path d="{d}" pathLength="1" stroke-dasharray="{dash / length:.4f} 3" stroke-opacity="{op}" '
                          f'style="stroke-dashoffset:{hidden:.4f};animation:{rule} {P}s linear {delay - PULSE[0][0] / 2 / speed:.2f}s infinite both"/>')
        groups.append(f'<g clip-path="url(#u{ni})" fill="none" stroke-linecap="round" stroke-width="{width:.1f}">'
                      f'<g opacity=".5" stroke="{color}">{base}</g><g stroke="{glow}">{light}</g></g>')

        # Label chip, shown once the trace reaches it.
        ax, ay = n['anchor'][0] * W, n['anchor'][1] * TH
        j = np.argmin(np.hypot(pts[:, 0] - ax, pts[:, 1] - ay))
        ax, ay = pts[j]
        cw, ch = TYPE.width(n['label'], 13, 600) + 14, 22
        left = ax > W - cw - 30
        cx = ax - 14 - cw if left else ax + 14
        cy = max(6, ay - 40)
        chips.append(
            f'<g style="animation:in .9s ease-out {n["start"] + dist[j] / speed + 0.2:.2f}s both">'
            f'<path d="M{ax:.1f} {ay:.1f}L{cx + (cw if left else 0):.1f} {cy + ch:.1f}" stroke="{color}" stroke-width="1.5"/>'
            f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{cw:.1f}" height="{ch}" fill="{color}"/>'
            + TYPE(n['label'], cx + 7, cy + 15.5, 13, 600, 100, '#000000') + '</g>')

    # Sparse background activity: unrelated cells brighten and fade like calcium transients.
    rng = np.random.default_rng(11)
    m = Motion(29, prefix='b')
    amb = m.keyframes(transient(periodic(m.t, 29), 1.4, 2.4) * 0.34)
    css.append(m.css() + layer_css({'ag': SEG['green'], 'av': SEG['violet']}))
    pool = [i for i in range(T.n) if i not in taken and 0 < T.cx[i] < W and 0 < T.cy[i] < TH and T.area[i] > pitch ** 2 * 0.3]
    paths, uses = '', ''
    for i in rng.choice(pool, 34, replace=False):
        paths += f'<path id="c{i}" d="{T.path(i)}"/>'
        uses += f'<use href="#c{i}" class="{"ag" if rng.random() < 0.6 else "av"}" opacity="0" style="animation:{amb} 29s linear {-rng.uniform(0, 29):.2f}s infinite"/>'

    y0 = TH
    if mobile:
        text = (TYPE('Ashton Long', 20, y0 + 52, 40, 600)
                + TYPE('Computer Science co-op, University of Guelph', 20, y0 + 80, 16, 400, 100, SUB)
                + field_columns(TYPE, FIELDS, 34 + 3 * 186, y0 + 112, 186, 12.5, 16, dot='status'))
    else:
        text = (TYPE('Ashton Long', 24, y0 + 54, 38, 600)
                + TYPE('Computer Science co-op, University of Guelph', 24, y0 + 84, 15, 400, 100, SUB)
                + field_columns(TYPE, FIELDS, W - 24, y0 + 44, 150, 12.5, 16, dot='status'))

    body = (tissue_image(T, W, TH, 64) + f'<defs>{"".join(clips)}{paths}</defs>' + uses + ''.join(groups) + ''.join(chips)
            + f'<rect y="{TH}" width="{W}" height="{BH}" fill="{BAR}"/>' + text)
    desc = ('An animated electron micrograph of brain tissue. Three neurons, labelled Fruit Fly, AnkiGPT and ScanAir, '
            'are traced into view, then slow signals travel along their branches. Ashton Long, Computer Science co-op, '
            'University of Guelph. Open to co-op. Contract developer at ScanAir. Based in Guelph, Ontario.')
    return document(W, TH + BH, 'Ashton Long', desc, ''.join(css), body)


# ================================================================ panels
# Each panel's colored cells draw a small looping scene about the project.

def sd_box(x, y, cx, cy, hw, hh, r):
    qx, qy = np.abs(x - cx) - hw + r, np.abs(y - cy) - hh + r
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r


def ellipse(x, y, cx, cy, rx, ry):
    return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2


def edge_of(T, mask):
    """Cells in mask with a neighbour outside it."""
    tree = T.tree
    out = np.zeros_like(mask)
    for i in np.where(mask)[0]:
        out[i] = any(not mask[j] for j in tree.query_ball_point([T.cx[i], T.cy[i]], T.pitch * 1.25))
    return out


def seg_dist(x, y, a, b):
    """Distance from points to the segment a-b."""
    ax, ay, bx, by = *a, *b
    u = np.clip(((x - ax) * (bx - ax) + (y - ay) * (by - ay)) / ((bx - ax) ** 2 + (by - ay) ** 2), 0, 1)
    return np.hypot(x - ax - u * (bx - ax), y - ay - u * (by - ay))


LEGS = [((36, 12), (56, 40), (76, 54)), ((26, 16), (22, 46), (12, 66)), ((14, 14), (-4, 44), (-24, 60))]


def fly_shape(X, Y, wing, twitch):
    """Opacity of a resting fruit fly seen from above, head to the right.

    X, Y are fly-local; wing is the spread angle in degrees; twitch[k][side]
    nudges each leg forward."""
    v = np.zeros(np.broadcast(X, Y, wing).shape)
    ay = np.abs(Y)
    a = np.radians(wing)
    for side in (-1, 1):
        ux, uy = -np.cos(a), side * np.sin(a)
        cx, cy = 14 + ux * 56, side * 10 + uy * 56
        along, across = (X - cx) * ux + (Y - cy) * uy, -(X - cx) * uy + (Y - cy) * ux
        w = ellipse(along, across, 0, 0, 56, 19)
        v = np.where(w < 1, np.maximum(v, np.where(w > 0.7, 0.4, 0.16)), v)
    abd = ellipse(X, Y, -22, 0, 34, 21) < 1
    v = np.where(abd, np.where(((X + 60) % 13) < 5, 0.32, 0.6), v)
    v = np.where(ellipse(X, Y, 25, 0, 23, 19) < 1, 0.62, v)
    v = np.where(ellipse(X, Y, 56, 0, 13, 17) < 1, 0.5, v)
    v = np.where(ellipse(X, ay, 59, 14, 10, 9) < 1, 0.95, v)
    for k, (a0, b0, c0) in enumerate(LEGS):
        for si, side in enumerate((-1, 1)):
            j = twitch[k][si]
            A = (a0[0], side * a0[1])
            B = (b0[0] + 4 * j, side * (b0[1] + 2 * j))
            C = (c0[0] + 9 * j, side * (c0[1] + 3 * j))
            d = np.minimum(seg_dist(X, Y, A, B), seg_dist(X, Y, B, C))
            v = np.where((d < 3.2) & (v == 0), 0.6, v)
    for side in (-1, 1):
        v = np.where((seg_dist(X, Y, (66, side * 5), (78, side * 11)) < 2.5) & (v == 0), 0.55, v)
    return v


def fruitfly(T, W, H):
    """A fruit fly at rest. Activity ripples out from an eye or the antennae,
    twitching each leg as it arrives; once a loop the wings lift and shimmer."""
    L = 24
    m = Motion(L)
    t = m.t
    s = H / 170 * 1.1
    X, Y = (T.cx - W * 0.52) / s, (T.cy - H / 2) / s
    near = np.where(T.visible & (np.abs(X) < 140) & (np.abs(Y) < 100))[0]
    Xn, Yn = X[near], Y[near]

    events = [(1.0, (59, 14)), (7.4, (59, -14)), (18.6, (74, 0))]
    speed = 90
    tips = [[(c[0], side * c[1]) for side in (-1, 1)] for _, _, c in LEGS]

    # Wings lift between 12.6 and 16.4 seconds.
    lift = ease(ramp(t, 12.6, 13.4)) * (1 - ease(ramp(t, 15.6, 16.4)))
    wing = 32 + 20 * lift

    base = np.zeros((len(near), len(t)))
    for f, tf in enumerate(t):
        twitch = [[sum(transient(tf - t0 - np.hypot(tx - ox, ty - oy) / speed, 0.15, 0.5) for t0, (ox, oy) in events)
                   for tx, ty in tips[k]] for k in range(3)]
        base[:, f] = fly_shape(Xn, Yn, wing[f], twitch)

    ov = Overlay(T, m, static_t=0.5)
    ov.add('pk', dict(zip(near, base)))

    # Ripples and the wing shimmer are one curve each, delayed per cell.
    resting = base[:, 0] > 0
    ripple = 0.85 * transient(periodic(t, L), 0.2, 0.7)
    for t0, (ox, oy) in events:
        d = np.round(np.hypot(Xn - ox, Yn - oy) / 4) * 4
        ov.shared('pg', {i: t0 + di / speed for i, di, on in zip(near, d, resting) if on}, ripple)
    shimmer = 0.5 * sum(transient(periodic(t - b, L), 0.2, 0.5) for b in (0, 0.8, 1.6))
    wing_cells = resting & (base[:, 0] < 0.45) & (Xn < 20)
    hinge = np.round(np.hypot(Xn - 14, np.abs(Yn) - 10) / 4) * 4
    ov.shared('pg', {i: 13.4 + h / 110 for i, h, on in zip(near, hinge, wing_cells) if on}, shimmer)
    return ov, {'pk': SEG['pink'], 'pg': GLOW['pink']}, L


def keyframes(name, L, stops):
    """CSS keyframes from (seconds, declarations) stops."""
    return f'@keyframes {name}{{' + ''.join(f'{pct(t / L * 100)}%{{{decl}}}' for t, decl in stops) + '}'


def union_clip(T, cells, cid):
    """Clip path covering a set of cells, with the membranes between them bridged."""
    shape = shapely.union_all([T.cells[i].buffer(T.gap * 1.3) for i in cells]).buffer(-T.gap * 0.3 - 0.35)
    return f'<clipPath id="{cid}"><path d="{outline(shape.simplify(0.5))}"/></clipPath>'


def scanair(T, W, H):
    """A mission in three acts. Plan: the scan area and its route are drawn.
    Fly: the drone flies the lawnmower lines, firing its camera, and overlap
    builds up underneath. Reconstruct: Gaussian splats bloom into the site."""
    L = 28
    m = Motion(L)
    t = m.t
    s = H / 170
    p = T.pitch
    FLY0, FLY1 = 3.8, 17.4
    fade = 1 - ramp(t, 25.0, 27.0)

    poly = Polygon(np.array([[0.3, 0.13], [0.58, 0.06], [0.92, 0.17], [0.95, 0.8], [0.7, 0.93], [0.35, 0.86]]) * [W, H])
    home = np.array([0.13 * W, 0.6 * H])
    spacing = 44 * s
    fw, fh = spacing * 1.5, spacing * 0.95          # camera footprint across and along track
    inner = poly.buffer(-10 * s)
    ix0, iy0, ix1, iy1 = inner.bounds
    lines = []
    for x in np.arange(ix0 + spacing * 0.4, ix1, spacing):
        seg = inner.intersection(LineString([(x, -10), (x, H + 10)]))
        if seg.is_empty or seg.geom_type != 'LineString':
            continue
        ys = sorted(q[1] for q in seg.coords)
        lines.append([(x, ys[-1]), (x, ys[0])] if len(lines) % 2 == 0 else [(x, ys[0]), (x, ys[-1])])
    route = np.array([home] + [q for ln in lines for q in ln] + [home], float)
    cum = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(route, axis=0).T))])
    when = lambda dist: FLY0 + dist / cum[-1] * (FLY1 - FLY0)
    dense_s = np.arange(0, cum[-1], 1.0)
    dense = np.c_[np.interp(dense_s, cum, route[:, 0]), np.interp(dense_s, cum, route[:, 1])]

    # The camera fires at even spacing along each survey line, never on transits.
    photos = []
    for k, ((ax, ay), (bx, by)) in enumerate(lines):
        for d in np.arange(0, abs(by - ay) + 0.1, 26 * s):
            photos.append((when(cum[1 + 2 * k] + d), ax, ay + np.sign(by - ay) * d))

    vis = np.where(T.visible)[0]
    cx, cy = T.cx[vis], T.cy[vis]
    inside = np.array([poly.contains(Point(x, y)) for x, y in zip(cx, cy)])
    near_area = np.array([poly.distance(Point(x, y)) < 0.6 * p for x, y in zip(cx, cy)])
    base = np.zeros((len(vis), len(t)))

    # Overlap: each cell brightens from its first photo to its last, by how many saw it.
    hits = [[] for _ in vis]
    for tp, px, py in photos:
        for j in np.where((np.abs(cx - px) < fw / 2) & (np.abs(cy - py) < fh / 2) & near_area)[0]:
            hits[j].append(tp)
    settle = ramp(t, FLY1 + 0.6, FLY1 + 1.8)
    for j, ts in enumerate(hits):
        if ts:
            first, last = round(min(ts), 1), round(max(ts), 1) + 0.3
            grow = min(0.07 * len(ts), 0.34) * ramp(t, first, last)
            base[j] = grow * (1 - settle) + (0.06 if inside[j] else 0) * settle

    # The site, rebuilt from splats once the drone lands.
    aw, ah = ix1 - ix0, iy1 - iy0
    A = lambda u, v: (ix0 + u * aw, iy0 + v * ah)
    rng = np.random.default_rng(8)
    scene, born = np.zeros(len(vis)), np.full(len(vis), np.inf)

    def place(values, start):
        values = np.where(inside, values, 0)
        newer = values > scene
        scene[newer] = values[newer]
        born[newer] = np.round(np.broadcast_to(start, values.shape)[newer], 1)

    bx, by = A(0.34, 0.4)
    wx, wy = bx + 30 * s, by + 34 * s
    # A gable-roofed house with a wing: bright eaves, a sunlit and a shaded roof slope.
    for (ox, oy, hw, hh), ta in [((bx, by, 50 * s, 20 * s), 18.3), ((wx, wy, 16 * s, 16 * s), 18.7)]:
        sd = sd_box(cx, cy, ox, oy, hw, hh, 3 * s)
        roof = np.where(cy < oy, 0.52, 0.28) if hh > 18 * s else 0.4
        val = np.where(np.abs(sd) < 0.55 * p, 0.86, np.where(sd < 0, roof, 0))
        if hh > 18 * s:
            val = np.where((sd < 0) & (np.abs(cy - oy) < 0.4 * p), 0.86, val)
        place(val, ta)
    road = [A(-0.03, 0.95), A(0.12, 0.84), A(0.24, 0.74), (wx, wy + 18 * s)]
    rd = np.min([seg_dist(cx, cy, road[i], road[i + 1]) for i in range(3)], axis=0)
    place(np.where(rd < 8 * s, 0.55, 0), 19.0 + (cx - road[0][0]) / (road[-1][0] - road[0][0]) * 0.8)
    fx0, fy0 = A(0.7, 0.1)
    fx1, fy1 = A(0.97, 0.52)
    in_field = (cx > fx0) & (cx < fx1) & (cy > fy0) & (cy < fy1)
    rows = ((cy - fy0) // (1.5 * p)) % 2 == 0
    place(np.where(in_field, np.where(rows, 0.46, 0.1), 0), 19.4 + (cy - fy0) / (fy1 - fy0) * 0.7)
    trees = [(0.08, 0.22), (0.13, 0.56), (0.21, 0.24), (0.52, 0.8), (0.58, 0.3), (0.66, 0.76), (0.8, 0.8), (0.93, 0.76)]
    for k in rng.permutation(len(trees)):
        tx, ty = A(*trees[k])
        r = rng.uniform(16, 20) * s
        val = 0.82 * np.exp(-1.4 * ((cx - tx) ** 2 + (cy - ty) ** 2) / r ** 2)
        place(np.where(val > 0.1, np.round(val / 0.05) * 0.05, 0), 19.2 + rng.uniform(0, 1.8))
    has = scene > 0
    grown = scene[:, None] * ramp(t[None, :], np.where(has, born, 0)[:, None], np.where(has, born, 0)[:, None] + 0.6)
    shimmer = 0.25 * transient(t[None, :] - 22.6 - np.round((cx - ix0) / aw * 1.6, 1)[:, None], 0.3, 0.7)
    base = np.maximum(base, np.where(has[:, None], grown + shimmer * (scene[:, None] > 0.2), 0))

    hx, hy = home
    pad = np.hypot(cx - hx, cy - hy) < 11 * s
    base[pad] = np.maximum(base[pad], 0.55 * ramp(t, 1.0, 1.6))
    base *= fade

    ov = Overlay(T, m, static_t=22.5)
    ov.add('yl', dict(zip(vis, base)))
    ov.shared('yg', {i: b for i, b, v in zip(vis, born, scene) if v > 0.25}, 0.6 * transient(periodic(t, L), 0.15, 0.6))

    # Vector annotations: route and boundary strokes clipped to their cells,
    # the drone with its camera footprint, photo frames, handles, launch pad.
    route_cells = {int(i) for i in T.cell_at(dense[:, 0], dense[:, 1]) if i >= 0}
    ring = np.asarray(shapely.segmentize(poly.exterior, 1.0).coords)
    ring_cells = {int(i) for i in T.cell_at(ring[:, 0], ring[:, 1]) if i >= 0}
    route_d = 'M' + 'L'.join(f'{x:.1f} {y:.1f}' for x, y in route)
    corners = np.asarray(poly.exterior.coords)[:-1]
    ring_d = 'M' + 'L'.join(f'{x:.1f} {y:.1f}' for x, y in corners) + 'Z'
    sw = 2.6 * p
    off = lambda o, op: f'stroke-dashoffset:{o};opacity:{op}'
    show = lambda a, b: [(0, 'opacity:0'), (a, 'opacity:0'), (b, 'opacity:1'), (25, 'opacity:1'), (27, 'opacity:0'), (L, 'opacity:0')]
    css = [
        keyframes('bd', L, [(0, off(1.001, .4)), (0.4, off(1.001, .4)), (2.0, off(0, .4)), (FLY1 + 0.6, off(0, .4)),
                            (FLY1 + 1.6, off(0, .2)), (25, off(0, .2)), (27, off(0, 0)), (L, off(0, 0))]),
        keyframes('rp', L, [(0, off(1.001, .2)), (2.0, off(1.001, .2)), (3.4, off(0, .2)), (FLY1 + 0.4, off(0, .2)),
                            (FLY1 + 1.4, off(0, 0)), (L, off(0, 0))]),
        keyframes('rf', L, [(0, off(1.001, .82)), (FLY0, off(1.001, .82)), (FLY1, off(0, .82)), (FLY1 + 0.4, off(0, .82)),
                            (FLY1 + 1.6, off(0, .06)), (25, off(0, .06)), (27, off(0, 0)), (L, off(0, 0))]),
        keyframes('dr', L, [(0, 'opacity:0'), (FLY0 - 0.4, 'opacity:0'), (FLY0, 'opacity:1'), (FLY1, 'opacity:1'),
                            (FLY1 + 0.5, 'opacity:0'), (L, 'opacity:0')]),
        keyframes('stp', L, [(0, 'opacity:.9'), (0.3, 'opacity:.4'), (1.6, 'opacity:0'), (L, 'opacity:0')]),
        keyframes('hp', L, show(1.0, 1.5)),
        keyframes('pr', L, [(0, 'transform:scale(1);opacity:.8'), (1.3, 'transform:scale(2.8);opacity:0'),
                            (L, 'transform:scale(2.8);opacity:0')]),
        f'.st{{fill:none;stroke:{GLOW["yellow"]};stroke-width:1;animation:stp {L}s linear infinite}}',
        f'.pr{{fill:none;stroke:{SEG["yellow"]};stroke-width:1.5;transform-box:fill-box;transform-origin:center;'
        f'animation:pr {L}s ease-out infinite}}',
    ]
    ring_cum = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(np.vstack([corners, corners[:1]]), axis=0).T))])
    handles = ''
    for k, (vx, vy) in enumerate(corners):
        tv = 0.4 + ring_cum[k] / ring_cum[-1] * 1.6
        css.append(keyframes(f'h{k}', L, show(tv, tv + 0.25)))
        handles += (f'<circle cx="{vx:.1f}" cy="{vy:.1f}" r="{3.4 * s:.1f}" fill="#000" stroke="{SEG["yellow"]}" '
                    f'stroke-width="1.5" style="animation:h{k} {L}s linear infinite"/>')
    stamps = ''.join(f'<rect class="st" x="{px - fw / 2:.1f}" y="{py - fh / 2:.1f}" width="{fw:.1f}" height="{fh:.1f}" '
                     f'opacity="0" style="animation-delay:{tp:.2f}s"/>' for tp, px, py in photos)
    drone = (f'<g class="motion" opacity="0" style="animation:dr {L}s linear infinite">'
             f'<rect x="{-fw / 2:.1f}" y="{-fh / 2:.1f}" width="{fw:.1f}" height="{fh:.1f}" fill="{GLOW["yellow"]}" '
             f'fill-opacity=".07" stroke="{GLOW["yellow"]}" stroke-opacity=".75" stroke-width="1.2"/>'
             f'<circle r="{10 * s:.1f}" fill="{GLOW["yellow"]}" opacity=".25"/><circle r="{3.6 * s:.1f}" fill="#ffffff"/>'
             f'<animateMotion dur="{L}s" repeatCount="indefinite" calcMode="linear" path="{route_d}" '
             f'keyTimes="0;{FLY0 / L:.4f};{FLY1 / L:.4f};1" keyPoints="0;0;1;1"/></g>')
    pad_marks = (f'<g style="animation:hp {L}s linear infinite"><circle cx="{hx:.1f}" cy="{hy:.1f}" r="{9 * s:.1f}" '
                 f'fill="none" stroke="{SEG["yellow"]}" stroke-width="1.5"/>'
                 f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{2.4 * s:.1f}" fill="{SEG["yellow"]}"/></g>'
                 + ''.join(f'<circle class="pr" cx="{hx:.1f}" cy="{hy:.1f}" r="{9 * s:.1f}" opacity="0" '
                           f'style="animation-delay:{d:.2f}s"/>' for d in (FLY0 - 0.2, FLY1 + 0.1)))
    strokes = (f'<g clip-path="url(#sr)" fill="none" stroke="{SEG["yellow"]}" stroke-width="{sw:.1f}" '
               f'stroke-linecap="round" stroke-linejoin="round">'
               f'<path d="{route_d}" pathLength="1" stroke-dasharray="1 1" opacity="0" style="animation:rp {L}s linear infinite"/>'
               f'<path d="{route_d}" pathLength="1" stroke-dasharray="1 1" opacity=".06" style="animation:rf {L}s linear infinite"/></g>'
               f'<g clip-path="url(#sb)" fill="none" stroke="{SEG["yellow"]}" stroke-width="{sw:.1f}" stroke-linejoin="round">'
               f'<path d="{ring_d}" pathLength="1" stroke-dasharray="1 1" opacity=".2" style="animation:bd {L}s linear infinite"/></g>')
    extra = dict(defs='<defs>' + union_clip(T, route_cells, 'sr') + union_clip(T, ring_cells, 'sb') + '</defs>',
                 body=strokes + stamps + drone + handles + pad_marks, css=''.join(css))
    return ov, {'yl': SEG['yellow'], 'yg': GLOW['yellow']}, L, extra


def ankigpt(T, W, H):
    """Source lines are read, become cards, a duplicate merges, then the deck is reviewed."""
    L = 28
    m = Motion(L)
    s = H / 170
    cs = min(s, 1.1)
    p = T.pitch
    vis = np.where(T.visible)[0]
    X, Y = T.cx[vis][:, None], T.cy[vis][:, None]
    t = m.t[None, :]
    fade = 1 - ramp(t, 24.6, 26.6)

    # Source page with five lines of text, revealed top to bottom.
    phw, phh = 38 * s, 58 * s
    pcx, pcy = max(0.11 * W, 52 * s), H / 2
    rows = [pcy - phh + 17 * s + r * 21 * s for r in range(5)]
    lengths = [0.85, 0.62, 0.9, 0.7, 0.8]
    lx0 = pcx - phw + 10 * s
    lspan = 2 * phw - 20 * s
    page_sd = sd_box(X, Y, pcx, pcy, phw, phh, 4 * s)
    appear = ramp(t - (Y - (pcy - phh)) / (2 * phh) * 0.7, 0.2, 1.0)
    base = np.where(np.abs(page_sd) < 0.5 * p, 0.6, 0) * appear
    glow = np.zeros_like(base)
    reading = {}

    # Cards in a row, plus a near-duplicate of the second card.
    n = 4 if W >= 900 else 3
    hw, hh = 55 * cs, 36 * cs
    left, right = 0.33 * W, 0.955 * W
    gap = (right - left - n * 2 * hw) / (n - 1)
    cards = [(left + hw + k * (2 * hw + gap), H * 0.4) for k in range(n)]
    dup0 = (cards[1][0] + 34 * cs, cards[1][1] + 52 * cs)
    t_read = [1.3 + r * 2.0 for r in range(n + 1)]
    t_arrive = [tr + 2.4 for tr in t_read]

    for r, ry in enumerate(rows):
        in_row = (np.abs(Y - ry) < 0.42 * p) & (X > lx0) & (X < lx0 + lengths[r] * lspan) & (page_sd < -0.5 * p)
        base = np.maximum(base, np.where(in_row, 0.38, 0) * appear)
        if r <= n:
            for i, x in zip(vis[in_row[:, 0]], X[in_row[:, 0], 0]):
                reading[i] = t_read[r] + round((x - lx0) / (lengths[r] * lspan) * 0.9, 1)

    def card(cx, cy, t_a, t_flip):
        a = np.clip((t - t_a) * 1.6 - np.hypot(X - cx, Y - cy) / hw * 0.8, 0, 1)
        u = ramp(t, t_flip, t_flip + 1.2)
        f = np.abs(np.cos(np.pi * u))
        hwe = hw * np.maximum(f, 0.07)
        sd = sd_box(X, Y, cx, cy, hwe, hh, 7 * cs)
        edge = np.abs(sd) < 0.55 * p
        inside = sd < -0.55 * p
        strip = inside & (np.abs(Y - cy) < 0.5 * p) & (X > cx - hwe * 0.6) & (X < cx + hwe * 0.3)
        b = np.where(edge, 0.8, np.where(inside, np.where(u >= 0.5, 0.4, np.where(strip, 0.5, 0.13)), 0))
        g = np.where(edge | inside, 0.75 * np.clip(1 - f / 0.25, 0, 1) * (u > 0) * (u < 1), 0)
        return b * a, g * a

    for k, (cx, cy) in enumerate(cards):
        b, g = card(cx, cy, t_arrive[k], 15.4 + k * 0.9)
        if k == 1:
            g = np.maximum(g, (b > 0) * 0.7 * transient(t - 14.0, 0.15, 0.6))
        base, glow = np.maximum(base, b), np.maximum(glow, g)

    # The duplicate slides into its twin and dissolves.
    mv = ease(ramp(m.t, 12.4, 14.0))
    dx = dup0[0] + (cards[1][0] - dup0[0]) * mv
    dy = dup0[1] + (cards[1][1] - dup0[1]) * mv
    a = np.clip((t - t_arrive[n]) * 1.6 - np.hypot(X - dx, Y - dy) / hw * 0.8, 0, 1)
    sd = sd_box(X, Y, dx, dy, hw, hh, 7 * cs)
    dup = np.where(np.abs(sd) < 0.55 * p, 0.7, np.where(sd < -0.55 * p, 0.12, 0)) * a * (1 - ramp(t, 13.5, 14.1))
    base = np.maximum(base, dup)

    # Sparks carry each read line to its card. A cell glows when the spark passes
    # closest, brighter the nearer it comes.
    targets = [(cx - hw, cy) for cx, cy in cards] + [(dup0[0] - hw, dup0[1])]
    sparks = {level: {} for level in (0.4, 0.7, 1.0)}
    for r in range(n + 1):
        sx, sy = pcx + phw + 4 * s, rows[r]
        tx, ty = targets[r]
        kx, ky = (sx + tx) / 2, min(sy, ty) - 30 * s
        ts = np.linspace(t_read[r] + 0.9, t_read[r] + 2.4, 120)
        u = ease(ramp(ts, ts[0], ts[-1]))
        px = (1 - u) ** 2 * sx + 2 * (1 - u) * u * kx + u * u * tx
        py = (1 - u) ** 2 * sy + 2 * (1 - u) * u * ky + u * u * ty
        d = np.hypot(X - px[None, :], Y - py[None, :])
        j = d.argmin(1)
        heat = np.exp(-(d[np.arange(len(vis)), j] / (7 * s)) ** 2)
        for i, h, tp in zip(vis, heat, ts[j]):
            level = 1.0 if h > 0.75 else 0.7 if h > 0.45 else 0.4 if h > 0.2 else None
            if level:
                sparks[level][i] = round(tp, 2)

    base, glow = np.clip(base * fade, 0, 1), np.clip(glow * fade, 0, 1)

    ov = Overlay(T, m, static_t=21.0)
    ov.add('cy', dict(zip(vis, base)))
    ov.add('cg', dict(zip(vis, glow)))
    ov.shared('cg', reading, 0.85 * transient(periodic(m.t, L), 0.12, 0.8))
    for level, delays in sparks.items():
        ov.shared('cg', delays, 0.95 * level * transient(periodic(m.t, L), 0.08, 0.3))
    return ov, {'cy': SEG['cyan'], 'cg': GLOW['cyan']}, L


PANELS = [
    ('fruitfly', fruitfly, 'Fruit Fly: A Small Mind', [('type', 'Personal project'), ('wiring', 'FlyWire connectome')], 21,
     'A fruit fly made of colored cells. Ripples of activity cross its body and twitch its legs, and its wings lift and shimmer.'),
    ('ankigpt', ankigpt, 'AnkiGPT', [('type', 'Personal project'), ('since', '2025')], 33,
     'Colored cells read lines from a page, turn them into flashcards, merge a duplicate card, then flip the deck.'),
    ('scanair', scanair, 'ScanAir', [('type', 'Contract work'), ('since', 'May 2026')], 47,
     'A drone mission in colored cells: the scan area and route are planned, the drone flies the lines firing its camera '
     'while overlap builds up, then Gaussian splats bloom into the reconstructed site.'),
]


def panel(key, scene, title, fields, seed, desc, mobile=False):
    W, TH, BH = (600, 220, 100) if mobile else (960, 170, 64)
    pitch = (8 if key == 'fruitfly' else 11) if mobile else (7 if key == 'fruitfly' else 10)
    T = Tissue(W, TH, pitch, seed=seed + (100 if mobile else 0))
    ov, colors, L, *rest = scene(T, W, TH)
    extra = rest[0] if rest else {}
    defs, uses = ov.svg()
    y0 = TH
    if mobile:
        text = TYPE(title, 20, y0 + 40, 28, 600) + field_columns(TYPE, fields, 34 + 2 * 190, y0 + 64, 190, 12, 15)
    else:
        text = TYPE(title, 24, y0 + 41, 24, 600) + field_columns(TYPE, fields, W - 24, y0 + 25, 160, 12, 15)
    css = base_css(L) + layer_css(colors) + ov.motion.css() + extra.get('css', '')
    body = (tissue_image(T, W, TH) + defs + extra.get('defs', '') + uses + extra.get('body', '')
            + f'<rect y="{TH}" width="{W}" height="{BH}" fill="{BAR}"/>' + text)
    return document(W, TH + BH, title, 'An animated electron micrograph. ' + desc, css, body)


if __name__ == '__main__':
    write('hero.svg', hero())
    write('hero-mobile.svg', hero(mobile=True))
    for key, scene, title, fields, seed, desc in PANELS:
        write(f'projects/{key}.svg', panel(key, scene, title, fields, seed, desc))
        write(f'projects/{key}-mobile.svg', panel(key, scene, title, fields, seed, desc, mobile=True))
