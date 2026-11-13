# STEP Export Pipeline: OpenSCAD → STEP/IGES

OpenSCAD does not natively export STEP. The best headless pipeline is:

```
OpenSCAD (.scad) → STL → FreeCAD Python → STEP (.step / .stp)
```

---

## Method 1: FreeCAD Python Script (Recommended)

This approach uses FreeCAD's Python API to convert STL → STEP headlessly.

### Step 1: Export STL from OpenSCAD
```bash
openscad -o /tmp/part.stl --enable=manifold part.scad
```

### Step 2: Convert STL → STEP via FreeCAD Python

Save as `stl_to_step.py`:

```python
#!/usr/bin/env python3
"""
Convert STL to STEP via FreeCAD Python API.
Usage: python3 stl_to_step.py input.stl output.step [sew_tolerance]
"""
import sys
import os

def stl_to_step(input_stl: str, output_step: str, sew_tolerance: float = 0.01):
    try:
        import FreeCAD
        import Part
        import Mesh
    except ImportError:
        print("ERROR: FreeCAD Python not available. Install: sudo apt-get install freecad")
        sys.exit(1)

    input_stl = os.path.abspath(input_stl)
    output_step = os.path.abspath(output_step)

    print(f"Loading: {input_stl}")
    mesh = Mesh.Mesh(input_stl)

    print(f"Sewing mesh (tolerance={sew_tolerance})...")
    shape = Part.Shape()
    shape.makeShapeFromMesh(mesh.Topology, sew_tolerance)

    print("Refining shape...")
    refined = shape.removeSplitter()

    print(f"Exporting STEP: {output_step}")
    refined.exportStep(output_step)
    print("Done.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 stl_to_step.py input.stl output.step [tolerance]")
        sys.exit(1)

    tol = float(sys.argv[3]) if len(sys.argv) > 3 else 0.01
    stl_to_step(sys.argv[1], sys.argv[2], sew_tolerance=tol)
```

Run it:
```bash
python3 stl_to_step.py part.stl part.step
# or with custom tolerance for noisy meshes:
python3 stl_to_step.py part.stl part.step 0.05
```

---

## Method 2: Full Pipeline Script (One Command)

```bash
#!/bin/bash
# openscad_to_step.sh <input.scad> <output.step> [openscad_params]
# Example: ./openscad_to_step.sh bracket.scad bracket.step "-D width=50"

INPUT_SCAD="$1"
OUTPUT_STEP="$2"
EXTRA_PARAMS="${@:3}"
TMP_STL="/tmp/$(basename ${INPUT_SCAD%.scad}).stl"

echo "[1/3] Rendering STL from OpenSCAD..."
openscad --enable=manifold -o "$TMP_STL" $EXTRA_PARAMS "$INPUT_SCAD"

if [ $? -ne 0 ]; then echo "OpenSCAD render failed"; exit 1; fi
echo "  -> $TMP_STL"

echo "[2/3] Converting STL to STEP via FreeCAD..."
python3 - <<EOF
import sys, os
try:
    import FreeCAD, Part, Mesh
except ImportError:
    print("FreeCAD Python unavailable. Keeping STL only.")
    sys.exit(0)

mesh = Mesh.Mesh("$TMP_STL")
shape = Part.Shape()
shape.makeShapeFromMesh(mesh.Topology, 0.01)
refined = shape.removeSplitter()
refined.exportStep("$OUTPUT_STEP")
EOF

echo "[3/3] Done: $OUTPUT_STEP"
rm -f "$TMP_STL"
```

Usage:
```bash
chmod +x openscad_to_step.sh
./openscad_to_step.sh bracket.scad bracket.step
./openscad_to_step.sh gear.scad gear.step "-D teeth=30 -D thickness=12"
```

---

## Method 3: CSG → FreeCAD Import (Alternative)

For parts with complex boolean operations that survive poorly as STL meshes:

```bash
# Export CSG (OpenSCAD's native format — easier for FreeCAD to parse)
openscad -o part.csg part.scad

# Then open part.csg in FreeCAD GUI and export as STEP
# (no headless CSG→STEP path exists that handles all operations)
```

---

## Quality Notes

| Concern | Recommendation |
|---------|---------------|
| Curved surface accuracy | Increase `$fn` in .scad before export (e.g. `$fn=72`) |
| Mesh noise / artifacts | Increase sew tolerance: `0.01` → `0.05` |
| Hull/Minkowski fail | These survive STL→STEP; CSG path doesn't handle them |
| Thin walls | Ensure `wall_thickness ≥ 1mm` before meshing |
| Best STEP for machining | Use `$fn=72` or higher so cylinders approximate circles well |

---

## IGES Export

Same pipeline, just change the export call:
```python
refined.exportIges(output_iges)
```
IGES is older and less commonly required than STEP today.

---

## Verifying Output

```bash
# Quick check: open in FreeCAD CLI
python3 -c "
import FreeCAD, Part
s = Part.read('part.step')
print('Faces:', len(s.Faces))
print('Volume:', s.Volume, 'mm³')
print('BoundBox:', s.BoundBox)
"
```
