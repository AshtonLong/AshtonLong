# Profile graphics

The visual reference is [Ashton's portfolio](https://ashtonlong.github.io/), as viewed in September 2026.

## Design

- Black `#000000`, white `#ffffff`, and the portfolio's mint `#b9e5cc`.
- Body gray `#d2d2d2`, secondary gray `#a9a9a9`, and rules `#2e2e2e`.
- Square pixel lettering, a dotted field, fine vertical lines, and numbered labels.
- A custom Blender workstation: graphite enclosure, individual keycaps, mint pixel display, and soft studio lighting.
- Three project diagrams: flashcards, survey waypoints, and neural connectivity.
- Native Markdown holds the biography, project descriptions, toolkit, and contact links. GitHub controls its fonts and page background.

## Edit and regenerate

Edit copy in the root README. Edit graphic layouts, labels, and colors in `generate.py`, then run from the repository root:

```sh
python -m pip install -r assets/requirements.txt
python assets/generate.py
```

Generation uses `resvg-py` to rasterize the desktop hero at 1920 × 840. The README uses `hero.png` for reliable GitHub rendering; `hero.svg` is its self-contained source with the Blender render embedded. Commit generated images alongside the script. Generation is deterministic on the same machine and validates SVG XML before writing. Text uses installed system fonts; the pixel wordmark is vector geometry.

### Workstation asset

`computer.blend` is the editable Blender 5.2 scene. `build_computer.py` builds the model, materials, lights, and camera; it was executed through Blender MCP. `computer.png` is the transparent render used by the hero generator.

To rebuild through Blender MCP, execute the script with its absolute path supplied as `__file__`, then run `bpy.ops.render.render(write_still=True)`. Alternatively, from the repository root with Blender on your PATH:

```sh
blender --background --python assets/build_computer.py -- --render
python assets/generate.py
```

The script replaces only its dedicated `Profile Workstation` scene. The compact phone header keeps the name and education without the desktop illustration.

Each hero and project banner has a phone layout selected by the README's `<picture>` element below 600px. Desktop images remain the fallback. The graphics use system font stacks and vector squares, with no scripts, remote fonts, or motion dependencies. Body content remains selectable and wraps at narrow widths.

The contribution snake is generated independently by `.github/workflows/snake.yml` and retains its light/dark variants.
