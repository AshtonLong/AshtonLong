"""Draw the GitHub contribution calendar as a calcium-imaging recording.

    python assets/activity.py --out dist                 # needs GITHUB_TOKEN
    python assets/activity.py --out dist --data cal.json # from a saved response

Each day is a cell in the micrograph. A scan line sweeps through the year and
active days flash as it passes, the way neurons carrying GCaMP light up, then
settle at a brightness set by GitHub's contribution level. Below, the weekly
total is drawn as a fluorescence trace, aligned with the week columns above.
CI runs this hourly and publishes the result to the output branch.
"""
import argparse
import datetime as dt
import json
import os
import urllib.request
from pathlib import Path

import numpy as np

from micrograph import (BAR, GLOW, LABEL, SEG, SUB, Motion, Overlay, Tissue, Type, base_css, document,
                        field_columns, layer_css, num, pct, periodic, ramp, transient)

QUERY = ('query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{'
         'weeks{contributionDays{date contributionCount contributionLevel}}}}}}')
LEVELS = {'NONE': 0, 'FIRST_QUARTILE': 1, 'SECOND_QUARTILE': 2, 'THIRD_QUARTILE': 3, 'FOURTH_QUARTILE': 4}
REST = [0, 0.4, 0.56, 0.72, 0.88]
L, SWEEP = 32, (1.0, 21.0)
TYPE = Type()


def fetch(login, token):
    body = json.dumps({'query': QUERY, 'variables': {'login': login}}).encode()
    req = urllib.request.Request('https://api.github.com/graphql', body,
                                 {'Authorization': f'bearer {token}', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.load(response)
    if 'errors' in data:
        raise SystemExit(f'GitHub API error: {data["errors"]}')
    return data


def weeks_of(data):
    return data['data']['user']['contributionsCollection']['contributionCalendar']['weeks']


def draw(weeks, mobile=False):
    weeks = weeks[-26:] if mobile else weeks
    W, BH = (600, 172) if mobile else (960, 124)
    nw = len(weeks)
    mx, my = (20, 18) if mobile else (24, 18)
    px = (W - 2 * mx) / nw
    py = px * 0.92
    TH = round(7 * py + 2 * my)
    y0 = TH

    # One seed per day on a jittered lattice, padded with tissue all round.
    rng = np.random.default_rng(5)
    jit = lambda: rng.uniform(-0.17, 0.17, 2) * px
    seeds, days = [], {}
    for c, week in enumerate(weeks):
        for day in week['contributionDays']:
            r = dt.date.fromisoformat(day['date']).isoweekday() % 7
            days[(c, r)] = day
    for c in range(-3, nw + 3):
        for r in range(-3, 10):
            if (c, r) in days:
                days[(c, r)]['seed'] = len(seeds)
            seeds.append((mx + (c + 0.5) * px, my + (r + 0.5) * py) + jit())
    T = Tissue(W, TH, px, seed=9, seeds=np.array(seeds))
    cell_of = {s: i for i, s in enumerate(T.seed_of)}
    T.add_nuclei([cell_of[d['seed']] for d in days.values() if d['seed'] in cell_of], seed=2)

    m = Motion(L)
    t = m.t
    ov = Overlay(T, m, static_t=24.0)
    col_t = lambda c: SWEEP[0] + (c + 0.5) / nw * (SWEEP[1] - SWEEP[0])
    back = ramp(t, 27.0, 29.5)
    base, flash = {}, {lv: {} for lv in range(1, 5)}
    reflash = {}
    for (c, r), day in days.items():
        i = cell_of.get(day['seed'])
        level = LEVELS[day['contributionLevel']]
        if i is None or not level:
            continue
        tc = col_t(c)
        lit = 0.08 + (REST[level] - 0.08) * ramp(t, tc, tc + 0.5)
        base[i] = lit * (1 - back) + 0.08 * back
        flash[level][i] = tc
        reflash[i] = rng.uniform(22.0, 26.0)
    ov.add('g', base)
    for level, delays in flash.items():
        ov.shared('gg', delays, (0.42 + 0.12 * level) * transient(periodic(t, L), 0.12, 0.9))
    ov.shared('gg', reflash, 0.28 * transient(periodic(t, L), 0.5, 1.1))
    defs, uses = ov.svg()

    # Weekly totals as a fluorescence trace under the calendar.
    totals = np.array([sum(d['contributionCount'] for d in w['contributionDays']) for w in weeks], float)
    xs = mx + (np.arange(nw) + 0.5) * px
    top, bottom = y0 + 12, y0 + 48
    ys = bottom - np.sqrt(totals / max(totals.max(), 1)) * (bottom - top)
    line = 'M' + 'L'.join(f'{x:.1f} {y:.1f}' for x, y in zip(xs, ys))
    area = line + f'L{xs[-1]:.1f} {bottom}L{xs[0]:.1f} {bottom}Z'
    seglen = np.concatenate([[0], np.cumsum(np.hypot(np.diff(xs), np.diff(ys)))])
    key_t = [0] + [col_t(c) / L for c in range(nw)] + [1]
    key_p = [0] + list(seglen / seglen[-1]) + [1]
    rel = 'M' + 'L'.join(f'{x - xs[0]:.1f} {y - ys[0]:.1f}' for x, y in zip(xs, ys))

    span = W - 2 * mx
    p0, p1 = SWEEP[0] / L * 100, SWEEP[1] / L * 100
    css = (base_css(L) + layer_css({'g': SEG['green'], 'gg': GLOW['green']}) + m.css()
           + f'@keyframes move{{0%,{pct(p0)}%{{transform:translateX(0)}}{pct(p1)}%,100%{{transform:translateX({span:.1f}px)}}}}'
           + f'@keyframes vis{{0%,{pct(p0 - 1.5)}%{{opacity:0}}{pct(p0)}%,{pct(p1)}%{{opacity:1}}{pct(p1 + 2)}%,100%{{opacity:0}}}}'
           + '@keyframes trace{0%,84%{opacity:1}92%,100%{opacity:0}}'
           + f'.scan{{animation:move {L}s linear infinite,vis {L}s linear infinite}}'
           + f'.dot{{animation:vis {L}s linear infinite}}.cover{{animation:move {L}s linear infinite}}'
           + f'.trace{{animation:trace {L}s linear infinite}}')

    scan = (f'<g class="scan motion"><rect x="{mx - 6}" y="0" width="12" height="{TH}" fill="{GLOW["green"]}" opacity=".08"/>'
            f'<rect x="{mx - 1}" y="0" width="2" height="{TH}" fill="{GLOW["green"]}" opacity=".55"/></g>')
    trace = (f'<g class="trace"><path d="{area}" fill="{SEG["green"]}" opacity=".14"/>'
             f'<path d="{line}" fill="none" stroke="{SEG["green"]}" stroke-width="1.6" stroke-linejoin="round"/></g>'
             f'<rect class="cover motion" x="{mx - 4}" y="{top - 4}" width="{W}" height="{bottom - top + 8}" fill="{BAR}"/>'
             f'<circle class="dot motion" cx="{xs[0]:.1f}" cy="{ys[0]:.1f}" r="3.2" fill="{GLOW["green"]}">'
             f'<animateMotion dur="{L}s" repeatCount="indefinite" calcMode="linear" path="{rel}" '
             f'keyTimes="{";".join(f"{k:.4f}" for k in key_t)}" keyPoints="{";".join(f"{k:.4f}" for k in key_p)}"/></circle>')

    months, last = '', None
    for c, week in enumerate(weeks):
        first = dt.date.fromisoformat(week['contributionDays'][0]['date'])
        if first.month != last and c < nw - 2:
            if last is not None or first.day <= 7:
                months += TYPE(f'{first:%b}', mx + c * px, y0 + 64, 11.5, 400, 80, LABEL)
            last = first.month

    total = int(totals.sum())
    active = sum(1 for w in weeks for d in w['contributionDays'] if d['contributionCount'])
    end = dt.date.fromisoformat(weeks[-1]['contributionDays'][-1]['date'])
    fields = [('contributions', f'{total:,}'), ('active days', str(active)), ('updated', f'{end:%b} {end.day}, {end.year}')]
    period = 'Past 26 weeks' if mobile else 'Past year'
    if mobile:
        text = (TYPE('Activity', 20, y0 + 102, 26, 600) + TYPE(period, 20 + TYPE.width('Activity', 26, 600) + 12, y0 + 102, 15, 400, 100, SUB)
                + field_columns(TYPE, fields, 34 + 3 * 186, y0 + 128, 186, 12, 15))
    else:
        text = (TYPE('Activity', 24, y0 + 106, 24, 600) + TYPE(period, 24 + TYPE.width('Activity', 24, 600) + 12, y0 + 106, 15, 400, 100, SUB)
                + field_columns(TYPE, fields, W - 24, y0 + 89, 160, 12, 15))

    image = f'<image width="{W}" height="{TH}" preserveAspectRatio="none" href="{T.texture()}"/>'
    body = (image + defs + uses + scan + f'<rect y="{TH}" width="{W}" height="{BH}" fill="{BAR}"/>'
            + trace + months + text)
    desc = (f'{total:,} GitHub contributions over the {period.lower()} across {active} active days, drawn as a calcium-imaging '
            'recording: each day is a cell that lights up green as a scan line sweeps through the calendar, '
            'with weekly totals traced below.')
    return document(W, TH + BH, 'Activity', desc, css, body)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', default='dist')
    ap.add_argument('--data', help='saved GraphQL response to draw instead of fetching')
    ap.add_argument('--login', default=os.environ.get('GITHUB_USER', 'AshtonLong'))
    args = ap.parse_args()
    if args.data:
        data = json.loads(Path(args.data).read_text(encoding='utf-8'))
    else:
        token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
        if not token:
            raise SystemExit('Set GITHUB_TOKEN, or pass --data with a saved calendar response.')
        data = fetch(args.login, token)
    weeks = weeks_of(data)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, mobile in [('activity.svg', False), ('activity-mobile.svg', True)]:
        svg = draw(weeks, mobile)
        (out / name).write_text(svg, encoding='utf-8')
        print(f'{out / name}: {len(svg.encode()) / 1024:.0f} KB')


if __name__ == '__main__':
    main()
