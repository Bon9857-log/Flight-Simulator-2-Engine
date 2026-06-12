# Flight Simulator 2.0 - Engine Core

A complete 3D flight simulator engine built entirely in Scratch using Python code generation.

## Features

- **3D Engine**: Full transform, projection, and rendering pipeline
- **Painter's Algorithm**: Back-to-front depth sorting for correct face ordering
- **Frustum Culling**: Back-face and near-plane culling
- **Directional Lighting**: Per-face shading with directional + ambient light
- **Lookup Tables**: Precomputed sine/cosine for performance
- **Interactive Controls**: 
  - Arrow keys to orbit the camera
  - Z/X keys to zoom in/out
  - Auto-rotating aircraft model

## Building the .sb3 File

### Option 1: Codespace (Recommended)

1. Click "Code" → "Codespaces" → "Create codespace on main"
2. Wait for the environment to load
3. In the terminal, run:
   ```bash
   python build_engine.py
   ```
4. The `.sb3` file will be generated in `/home/claude/sb3build/`
5. Download it and open in Scratch!

### Option 2: Local Environment

1. Clone this repo
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `python build_engine.py`
4. Find your `.sb3` file in the output directory

## Architecture

- **geometry.py**: 3D model data (11 vertices, 16 faces of a Darkstar aircraft)
- **build_engine.py**: Main engine - generates Scratch blocks procedurally
- **All logic runs in a single "Renderer" sprite** with:
  - `init engine` - Setup and data loading
  - `transform vertices` - 3D rotations (model spin + camera orbit)
  - `project vertices` - Perspective projection
  - `compute visibility` - Culling pipeline
  - `sort face order` - Insertion sort (painter's algorithm)
  - `fill triangle` - Scanline rasterization
  - `render frame` - Final rendering with shading

## Performance

This runs in pure Scratch using:
- Lookup tables for trig (361 entries: 0°-360°)
- Scanline triangle fill (2px stepping for speed)
- Simplified directional + ambient shading

Expect ~20-30 FPS on a modern machine!

## Customization

Edit `geometry.py` to change the 3D model:
- `VERTICES`: List of (name, x, y, z) coordinates
- `FACES`: List of (v1, v2, v3, (r, g, b)) triangles

Then rebuild the `.sb3` file.
