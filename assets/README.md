# Profile graphics

The visual reference is [Ashton's portfolio](https://ashtonlong.github.io/), as viewed in September 2026.

## Design

- Black `#000000`, white `#ffffff`, and the portfolio's mint `#b9e5cc`.
- Body gray `#d2d2d2`, secondary gray `#a9a9a9`, and rules `#2e2e2e`.
- Square pixel lettering, a dotted field, fine vertical lines, and numbered labels.
- Three project diagrams: flashcards, survey waypoints, and neural connectivity.
- Native Markdown holds the biography, project descriptions, toolkit, and contact links. GitHub controls its fonts and page background.

## Edit and regenerate

Edit copy in the root README. Edit graphic layouts, labels, and colors in `generate.py`, then run from the repository root:

```sh
python assets/generate.py
```

Python 3.9+ is sufficient; generation uses only the standard library. Commit generated SVGs alongside the script. Generation is deterministic and validates SVG XML before writing.

Each hero and project banner has a phone layout selected by the README's `<picture>` element below 600px. Desktop images remain the fallback. The graphics use system font stacks and vector squares, with no scripts, remote fonts, or motion dependencies. Body content remains selectable and wraps at narrow widths.

The contribution snake is generated independently by `.github/workflows/snake.yml` and retains its light/dark variants.
