# AGENTS.md

## Repo overview

Single-script Unity 2D mesh animation extractor: `index.py` reads a `.pet.json` asset + a `._Atlas_.png` texture atlas, renders mesh deformations per frame, and exports GIF/WebP/PNG frames. `index.html` provides a browser-based WebGL preview of the same data.

No build step, no tests, no linter, no CI.

## Setup

```bash
pip install Pillow
```

No other dependencies.

## Running the tool

```bash
# Default: renders "standby" sequence as GIF to output/
python index.py 4913.pet.json 4913._Atlas_.png

# Export WebP with transparent background
python index.py 4913.pet.json 4913._Atlas_.png --webp --transparent

# Pick a different sequence
python index.py 4913.pet.json 4913._Atlas_.png -s attack --webp --transparent

# All options
python index.py -h
```

Always run from repo root — asset paths in the command are relative.

## WebGL preview

Open `index.html` directly in a browser (no server needed). It loads `./4913.pet.json` and `./4913._Atlas_.png` by default. The JS is inline — no build, no npm.

## Data files

- `*.pet.json` — Unity asset JSON (very large, ~190k lines). Contains `FrameRate` and a `Sequences` array of `{Name, Frames}`. Each frame has `MeshData.Vertices[{x,y}]` and `MeshData.UVs` (16.16 fixed-point encoding).
- `*._Atlas_.png` — texture atlas paired with the JSON.
- `img/` — README screenshots, not used at runtime.

## Output

Output goes to the directory specified by `-o` (default `output/`). The `output*` glob in `.gitignore` prevents accidental commits.

## Conventions

- No codegen, no migrations, no env files, no dev server.
- No tests exist — verify by running the tool and checking the output visually.
- The `.pet.json` files are too large for the Read tool — use `grep` to inspect them.
