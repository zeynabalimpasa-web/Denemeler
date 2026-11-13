# OpenSCAD CLI Reference

## Basic Usage

```bash
openscad [options] <input.scad>
```

---

## Export Commands

```bash
# STL (3D printing, most common)
openscad -o part.stl input.scad

# STL with Manifold backend (MUCH faster for complex geometry)
openscad --enable=manifold -o part.stl input.scad

# 3MF (newer format, supports color)
openscad -o part.3mf input.scad

# OFF (simple mesh format)
openscad -o part.off input.scad

# DXF (2D — requires top-level 2D geometry or projection())
openscad -o part.dxf input.scad

# SVG (2D vector)
openscad -o part.svg input.scad

# CSG (OpenSCAD's own intermediate format)
openscad -o part.csg input.scad

# PNG render (preview image)
openscad --render -o preview.png \
  --camera=0,0,0,55,0,25,200 \
  --imgsize=1920,1080 \
  --colorscheme="Tomorrow Night" \
  input.scad

# ECHO only (print variables without rendering)
openscad -o /dev/null --export-format=echo input.scad
```

---

## Parameter Overrides

Override any top-level variable without editing the file:

```bash
# Single parameter
openscad -o part.stl -D "width=50" input.scad

# Multiple parameters
openscad -o part.stl -D "width=50;height=30;wall_t=3" input.scad

# String parameter (requires escaped quotes)
openscad -o part.stl -D 'label="Rev-B"' input.scad

# Batch family generation
for W in 20 30 40 50; do
  openscad -o "bracket_${W}mm.stl" -D "width=${W}" bracket.scad
done
```

---

## Camera Settings

Camera string format: `translateX,translateY,translateZ,rotX,rotY,rotZ,distance`

```bash
# Good default isometric-ish view
--camera=0,0,0,55,0,25,200

# Top-down (for DXF projection preview)
--camera=0,0,0,0,0,0,300

# Front view
--camera=0,0,0,90,0,0,200

# Auto-fit camera to model (EXPERIMENTAL)
--autocenter --viewall
```

---

## Color Schemes

```bash
--colorscheme="Cornfield"       # default warm
--colorscheme="Tomorrow Night"  # dark with contrast
--colorscheme="BeforeDawn"
--colorscheme="Metallic"
--colorscheme="Nature"
--colorscheme="Starnight"
```

---

## Validation / Debugging

```bash
# Check for manifold errors (silent = clean)
openscad --render -o /dev/null input.scad 2>&1 | grep -i "warning\|error\|manifold"

# Print all ECHO statements + variable values
openscad -o /dev/null --export-format=echo input.scad 2>&1

# Verbose output
openscad --render -o part.stl --enable=manifold -v input.scad

# Time the render
time openscad --enable=manifold -o part.stl input.scad
```

---

## Library Path Management

```bash
# Set library search path (semicolon-separated on Linux/Mac)
OPENSCADPATH="/path/to/BOSL2:$HOME/.local/share/OpenSCAD/libraries"
export OPENSCADPATH
openscad -o part.stl input.scad

# Or pass inline
openscad -o part.stl --library-dir=/path/to/BOSL2 input.scad
```

---

## Headless Batch Script Template

```bash
#!/bin/bash
# render_all.sh — Render all .scad files in current directory to STL

set -e
OUTDIR="output"
mkdir -p "$OUTDIR"

for SCAD in *.scad; do
  NAME="${SCAD%.scad}"
  echo "Rendering: $SCAD → $OUTDIR/${NAME}.stl"
  openscad --enable=manifold -o "$OUTDIR/${NAME}.stl" "$SCAD"
  
  # Optional: also render preview PNG
  openscad --render -o "$OUTDIR/${NAME}.png" \
    --camera=0,0,0,55,0,25,200 \
    --imgsize=800,600 \
    "$SCAD"
done

echo "Done. Files in $OUTDIR/"
```

---

## All CLI Flags (Reference)

| Flag | Description |
|------|-------------|
| `-o <file>` | Output file (type inferred from extension) |
| `-D <var=val>` | Override parameter |
| `--render` | Force full render (not just preview) for PNG |
| `--enable=manifold` | Use fast manifold backend (10-1000x speedup) |
| `--camera=x,y,z,rx,ry,rz,d` | Camera position for PNG |
| `--imgsize=W,H` | PNG output resolution |
| `--colorscheme=NAME` | Color theme for PNG |
| `--autocenter` | Center model for camera |
| `--viewall` | Auto-zoom camera to fit model |
| `--library-dir=PATH` | Add library search path |
| `--export-format=FORMAT` | Force format: `stl`, `off`, `dxf`, `svg`, `echo` |
| `-v` | Verbose output |
| `--version` | Print OpenSCAD version |
| `--info` | Print library paths and build info |
