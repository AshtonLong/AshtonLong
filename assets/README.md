# Profile graphics

Every graphic is an animated electron micrograph: grayscale brain tissue, colored segments, and a black data bar like a microscope's.

## Design

- Tissue is built vector-first. A jittered hexagonal Voronoi tiling is warped by smooth noise, rounded, and inset to leave membranes, with patches of fine axon bundles. The grayscale texture (membranes, vesicles, mitochondria, nuclei, grain) is rasterized from those outlines and embedded as a JPEG.
- Colored segments are vector copies of the same cell outlines, so they always sit inside the membranes. Colors follow the FlyWire viewer: pink `#ff5fa8` (Fruit Fly), cyan `#3fd0ff` (AnkiGPT), yellow `#ffd23f` (ScanAir), green `#7be36b` (activity), violet `#b483ff` (background). Each has a lighter glow tint for signals.
- The data bar is black `#000000`, with white values, gray `#8c8c8c` labels and `#333333` rules.
- Text is Archivo (SIL Open Font License, in `fonts/`), set with HarfBuzz and converted to vector outlines, since GitHub does not load fonts inside images.
- Motion is CSS keyframes plus one SMIL path, which run inside `<img>`. Each scene is written as opacity curves over one loop; `Motion` simplifies them and deduplicates identical keyframes, and motions that differ only in timing share one rule with per-cell delays. `prefers-reduced-motion` stops everything on a representative frame.

## Graphics

- `hero.svg`: three neurites, one per project, are traced in from their roots on load. Afterwards slow signals travel out along every branch, each neuron at its own rhythm, while background cells flicker like calcium transients.
- `projects/fruitfly.svg`: a resting fruit fly. Ripples of activity start at an eye or the antennae and twitch each leg as they arrive; once a loop the wings lift and shimmer.
- `projects/ankigpt.svg`: lines on a page are read one at a time, sparks carry them to new flashcards, a near-duplicate slides into its twin, and the deck flips card by card.
- `projects/scanair.svg`: a mission in three acts. Plan: the scan-area boundary draws itself with corner handles and the route is generated. Fly: the drone marker and its camera footprint follow the lawnmower route, firing a photo frame along every survey line while overlap builds up in the cells below. Reconstruct: Gaussian splats bloom into the captured site, a gable-roofed house, a road, trees and crop rows.
- `activity.svg` (CI): the contribution calendar as a calcium-imaging recording. Each day is a neuron with a nucleus; a scan line sweeps the year and active days light up as green rings, brighter for busier days, while the weekly total draws itself as a fluorescence trace aligned with the columns.

Each graphic has a `-mobile` layout that the README selects below 600px.

## Regenerate

From the repository root:

```sh
python -m pip install -r assets/requirements.txt
python assets/generate.py
```

`generate.py` writes the hero and project panels; commit them alongside the script. Output is deterministic.

The activity graphic is not committed. `.github/workflows/activity.yml` runs `activity.py` every hour and on every push to `main`. When the drawing has changed it publishes `activity.svg` and `activity-mobile.svg` to the `output` branch, and each scheduled run re-enables the workflow so GitHub does not switch it off after 60 quiet days. To draw it locally:

```sh
GITHUB_TOKEN=$(gh auth token) python assets/activity.py --out dist
```
