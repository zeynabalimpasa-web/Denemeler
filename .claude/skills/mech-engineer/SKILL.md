---
name: mech-engineer
description: >
  Use this skill whenever the user wants to design, model, or generate mechanical parts,
  assemblies, or engineering components using OpenSCAD. Triggers include: any mention of
  OpenSCAD, .scad files, parametric parts, gears, brackets, enclosures, mechanical design,
  3D-printable parts, STL generation, STEP export from code, CNC-ready models, threaded
  fasteners, or programmatic CAD. Also trigger when a user describes a physical mechanical
  component they want to generate — even if they don't say "OpenSCAD" explicitly. Also
  trigger for heat sink design, cooling channels, thermal management, snap-fits, press-fits,
  DFM rules (FDM/SLA/CNC/sheet metal/molding), beam deflection, or tolerance stack-ups.
  Do NOT use for FEA/simulation or general 3D mesh editing unrelated to parametric generation.
---

# OpenSCAD Mechanical & Thermal Engineering Skill

## Overview

OpenSCAD is a **code-first parametric CAD** tool — think of it as "React for 3D parts":
you declare geometry as functions of parameters, and it renders the output. This makes
it ideal for programmatic generation, scripted variation, and CI/CD-style part pipelines.

This skill covers three domains:
1. **Parametric CAD** — part generation, assemblies, gears, fasteners, export pipelines
2. **Thermal engineering** — heat sinks, cooling channels, thermal calculations, enclosure ventilation
3. **Structural design & DFM** — reinforcement patterns, snap-fits, press-fits, manufacturing constraints

## Quick Decision Table

| Task | Approach | Reference |
|------|----------|-----------|
| Generate a parametric part | Write `.scad` + BOSL2, render via CLI | This file |
| Export for 3D printing | `openscad -o part.stl input.scad` | `references/cli-reference.md` |
| Export for CNC/CAD interchange | STL → FreeCAD Python → STEP | `references/step-pipeline.md` |
| Render preview image | `openscad --render -o preview.png --camera=...` | `references/cli-reference.md` |
| Gears, threads, fasteners | Use BOSL2 modules | `references/bosl2-cheatsheet.md` |
| 2D profiles for laser cutting | `openscad -o part.dxf input.scad` | `references/cli-reference.md` |
| Multi-part assembly | Use BOSL2 attachments system | `references/bosl2-cheatsheet.md` |
| **Heat sink / fin array design** | Plate-fin, pin-fin, or radial modules + thermal calcs | `references/thermal-design.md` |
| **Cooling channel / cold plate** | Serpentine or conformal channel patterns | `references/thermal-design.md` |
| **Thermal resistance estimate** | Echo-based R_θ calculator in .scad | `references/thermal-design.md` |
| **Thermal expansion compensation** | CTE-aware dimensioning functions | `references/thermal-design.md` |
| **Ventilation / fan mounts** | Vent slot, hex vent, fan cutout modules | `references/thermal-design.md` |
| **Structural ribs / bosses** | Gusset, waffle rib, screw boss modules | `references/dfm-and-structural.md` |
| **Snap-fit / living hinge** | Cantilever hook with strain check | `references/dfm-and-structural.md` |
| **Press-fit / bearing pocket** | Interference sizing tables + modules | `references/dfm-and-structural.md` |
| **Spring geometry** | Coil spring, leaf spring modules | `references/dfm-and-structural.md` |
| **DFM rules (FDM/SLA/CNC/sheet metal/molding)** | Constraint tables per process | `references/dfm-and-structural.md` |
| **Section properties / beam deflection** | OpenSCAD functions with echo output | `references/dfm-and-structural.md` |
| **Tolerance stack-up** | RSS and worst-case analysis functions | `references/dfm-and-structural.md` |

---

## Setup (verify before running)

```bash
# Check OpenSCAD CLI availability
openscad --version

# Check FreeCAD Python (for STEP export)
python3 -c "import FreeCAD; print(FreeCAD.Version())"
```

### Installing OpenSCAD

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install -y openscad
```

**macOS (Homebrew):**
```bash
brew install openscad
# CLI binary lands at /Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD
# Create a symlink for convenience:
ln -sf /Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD /usr/local/bin/openscad
```

**macOS (manual):** Download the `.dmg` from https://openscad.org/downloads.html, drag to Applications, then symlink as above.

**Windows (winget):**
```powershell
winget install OpenSCAD.OpenSCAD
# CLI available at: "C:\Program Files\OpenSCAD\openscad.exe"
# Add to PATH or use full path in commands
```

**Windows (Chocolatey):**
```powershell
choco install openscad
```

**Windows (manual):** Download the installer from https://openscad.org/downloads.html and add the install directory to your system PATH.

### Installing FreeCAD (for STEP export)

**Linux:** `sudo apt-get install -y freecad`
**macOS:** `brew install --cask freecad`
**Windows:** `winget install FreeCAD.FreeCAD` or `choco install freecad`

### BOSL2 Library

Must be available in the OpenSCAD library path. The path differs by OS:

| OS | Library Path |
|----|-------------|
| Linux | `~/.local/share/OpenSCAD/libraries` |
| macOS | `~/Library/Application Support/OpenSCAD/libraries` |
| Windows | `%APPDATA%\OpenSCAD\libraries` (typically `C:\Users\<you>\AppData\Roaming\OpenSCAD\libraries`) |

**Check/install (Linux & macOS):**
```bash
# Set LIBPATH for your OS (Linux shown; macOS use ~/Library/Application Support/OpenSCAD/libraries)
LIBPATH="$HOME/.local/share/OpenSCAD/libraries"
mkdir -p "$LIBPATH"
ls "$LIBPATH/BOSL2/std.scad" 2>/dev/null && echo "BOSL2 OK" || echo "BOSL2 MISSING"
```

**Install BOSL2 if missing (Linux & macOS):**
```bash
LIBPATH="$HOME/.local/share/OpenSCAD/libraries"  # adjust for macOS
mkdir -p "$LIBPATH"
curl -L https://github.com/BelfrySCAD/BOSL2/archive/refs/heads/master.zip -o /tmp/bosl2.zip
unzip -q /tmp/bosl2.zip -d /tmp/
mv /tmp/BOSL2-master "$LIBPATH/BOSL2"
echo "BOSL2 installed at $LIBPATH/BOSL2"
```

**Install BOSL2 if missing (Windows PowerShell):**
```powershell
$libpath = "$env:APPDATA\OpenSCAD\libraries"
New-Item -ItemType Directory -Force -Path $libpath
Invoke-WebRequest -Uri "https://github.com/BelfrySCAD/BOSL2/archive/refs/heads/master.zip" -OutFile "$env:TEMP\bosl2.zip"
Expand-Archive -Path "$env:TEMP\bosl2.zip" -DestinationPath "$env:TEMP\bosl2" -Force
Move-Item "$env:TEMP\bosl2\BOSL2-master" "$libpath\BOSL2" -Force
Write-Host "BOSL2 installed at $libpath\BOSL2"
```

---

## Core Workflow

### 1. Write the `.scad` file

**Always** structure `.scad` files with:
1. **Parameter block** at the top (all tunable values as variables)
2. **Module definitions** (reusable geometry)
3. **Top-level instantiation** at the bottom
4. **Echo-based design checks** (thermal, structural, DFM) — so the user gets feedback at render time

**Minimal template:**
```openscad
// ── Parameters ──────────────────────────────────────────────
width   = 40;   // mm
height  = 20;   // mm
depth   = 10;   // mm
wall_t  = 2;    // wall thickness

// ── Includes ─────────────────────────────────────────────────
include <BOSL2/std.scad>

// ── Modules ──────────────────────────────────────────────────
module my_part() {
    difference() {
        cuboid([width, depth, height], rounding=1);
        // ... subtractive geometry
    }
}

// ── Design Checks ────────────────────────────────────────────
echo(str("Volume: ~", width * depth * height, " mm³"));

// ── Main ─────────────────────────────────────────────────────
my_part();
```

### 2. Render / Export via CLI

```bash
# STL export (3D printing)
openscad -o part.stl part.scad

# STL with parameter override (no need to edit the file)
openscad -o part_large.stl -D "width=80;height=40" part.scad

# PNG preview (adjust camera as needed)
openscad --render -o preview.png \
  --camera=0,0,0,55,0,25,200 \
  --colorscheme="Tomorrow Night" \
  part.scad

# DXF (2D projection for laser cutting)
openscad -o part.dxf part.scad  # requires 2D geometry or projection()

# Echo-only run (fast — for thermal/structural calcs without rendering)
openscad -o /dev/null --export-format=echo part.scad
```

### 3. STEP Export Pipeline

OpenSCAD does not natively export STEP. The canonical pipeline is:
**OpenSCAD → STL → FreeCAD Python → STEP**

See `references/step-pipeline.md` for the full script.

---

## BOSL2 Key Patterns

> Full cheatsheet in `references/bosl2-cheatsheet.md`. Load it for complex parts.

**Always include at top of file:**
```openscad
include <BOSL2/std.scad>
```

**Attachments** (the killer feature — place parts relative to each other):
```openscad
cuboid([40, 20, 10])
  attach(TOP, BOTTOM) cylinder(h=15, d=8);
```

**Gears:**
```openscad
include <BOSL2/gears.scad>
spur_gear(pitch=5, teeth=20, thickness=8, shaft_diam=5);
```

**Threads / Fasteners:**
```openscad
include <BOSL2/screws.scad>
screw("M3,10");              // M3 x 10mm screw
nut("M3");
screw_hole("M3,10", drilled=true); // hole with clearance
```

**Rounding & Filleting:**
```openscad
cuboid([40, 20, 10], rounding=2, edges=TOP);  // round top edges only
```

---

## Thermal Engineering (Summary)

> Full modules, calculations, and material tables in `references/thermal-design.md`.
> **Always load that reference** for any thermal management task.

### When to load `thermal-design.md`:
- User mentions heat sink, fin, cooling, thermal management, cold plate
- User asks about thermal resistance, temperature rise, heat dissipation
- User wants vent slots, fan mounts, or airflow geometry
- User asks about thermal expansion or CTE compensation
- User needs material thermal properties (conductivity, CTE, max temp)

### Quick overview of what's available:

**Heat sink modules:**
- `plate_fin_heatsink()` — rectangular base + parallel fins, with echo'd thermal estimates
- `pin_fin_heatsink()` — omnidirectional pin fin array
- `radial_heatsink()` — circular sunburst pattern (LED, round packages)

**Thermal calculations (echo-based, computed at render):**
- Fin efficiency (tanh formula for rectangular fins)
- Thermal resistance chain: R_base + R_conv/η
- Temperature rise: ΔT = Q × R_total
- All printed via `echo()` — run with `--export-format=echo` for fast calculation-only mode

**Cooling channels:**
- Serpentine cold plate (2.5D, CNC or SLM)
- Conformal channels (3D, metal AM)

**Thermal expansion:**
- `thermal_dim(L, CTE, T_ref, T_op)` function for CTE-compensated dimensions
- CTE constants for 15+ materials (metals, polymers, ceramics)
- Interference/clearance check at operating temperature

**Airflow geometry:**
- `vent_slots()` — parametric slot array with open-area fraction echo
- `hex_vent()` — honeycomb vent pattern
- `fan_mount_holes()` / `fan_cutout()` — standard fan sizes 25–140mm

**Material thermal properties table:** covers aluminum alloys, copper, steels, titanium, plastics (PLA/ABS/PETG/Nylon/PC/PEEK), PCB (FR-4), thermal pads, ceramics (Al₂O₃, AlN).

---

## Structural Design & DFM (Summary)

> Full modules, tables, and calculators in `references/dfm-and-structural.md`.
> **Always load that reference** for structural reinforcement, snap-fits, DFM, or engineering calculations.

### When to load `dfm-and-structural.md`:
- User asks about ribs, gussets, bosses, structural reinforcement
- User needs snap-fit, living hinge, or press-fit design
- User mentions bearing pockets, shaft interfaces, spring geometry
- User asks "can I 3D print this?" or about FDM/SLA/CNC/sheet metal/injection molding constraints
- User needs section properties (moment of inertia), beam deflection, stress estimates
- User asks about tolerance analysis or stack-up

### Quick overview of what's available:

**Structural modules:**
- `gusset_rib()`, `rib_array()`, `waffle_ribs()` — reinforcement patterns
- `screw_boss()` — self-tapping screw post with gussets and pilot hole table
- `snap_hook()` — cantilever snap-fit with strain validation echo (checks ABS/PC/POM/PP limits)
- `living_hinge()` — print-in-place flex hinge with slit pattern
- `bearing_pocket()` — standard bearing bore with retention lip
- `coil_spring()`, `leaf_spring()` — spring geometry with rate calculation echo

**Press-fit/interference sizing:**
- `press_fit_bore(shaft_d, fit)` function → light/medium/heavy interference
- ISO fit class table (H7/h6 through H7/s6)
- 3D print offset corrections

**DFM constraint tables for 5 processes:**
- FDM: wall thickness, overhangs, hole accuracy, clearances, teardrop holes
- SLA: min features, drain holes, suction cup avoidance
- CNC: corner radii, pocket depth ratios, thread engagement, surface finish
- Sheet metal: bend allowance calculator, k-factors, min flange/hole rules
- Injection molding: draft angles, rib/boss ratios, gate planning, sink mark avoidance

**Engineering calculators (OpenSCAD functions + echo output):**
- `I_rect()`, `I_circle()`, `I_tube()`, `I_beam()` — moment of inertia
- `deflect_cantilever_point()`, `deflect_simply_supported_center()`, `deflect_simply_supported_udl()` — beam deflection
- `stress_cantilever()` — max bending stress with yield check
- Young's modulus constants for 8 materials (Al, steel, PLA, ABS, PETG, Nylon, PC, PEEK)
- `rss_tol()`, `wc_tol()` — tolerance stack-up analysis (worst-case and RSS)
- `bend_allowance()` — sheet metal flat pattern calculation

---

## Parametric Design Patterns

### Pattern: Variation sweep (generate a family of parts)
```bash
for SIZE in 20 30 40 50; do
  openscad -o "bracket_${SIZE}mm.stl" -D "base_width=${SIZE}" bracket.scad
done
```

### Pattern: Assembly with sub-components
```openscad
include <BOSL2/std.scad>

module base_plate(w=80, d=60, h=4) {
    cuboid([w, d, h], rounding=1, edges=TOP+BOTTOM);
}

module standoff(h=20, od=8, id=3.2) {
    diff() cylinder(h=h, d=od) attach(CENTER, CENTER) cylinder(h=h+1, d=id);
}

// Assembly
base_plate()
  attach(TOP, BOTTOM, overlap=0) {
    move([-25, -15, 0]) standoff();
    move([ 25, -15, 0]) standoff();
    move([-25,  15, 0]) standoff();
    move([ 25,  15, 0]) standoff();
  }
```

### Pattern: Enclosure with integrated thermal management
```openscad
include <BOSL2/std.scad>

// Parametric electronics enclosure with vent slots and standoffs
module thermal_enclosure(
    inner_w=80, inner_d=60, inner_h=40,
    wall=2, lid_h=8,
    vent_slot_w=2, vent_spacing=3
) {
    outer_w = inner_w + 2*wall;
    outer_d = inner_d + 2*wall;
    outer_h = inner_h + wall;  // base wall

    diff() {
        cuboid([outer_w, outer_d, outer_h], rounding=2, edges=BOTTOM, anchor=BOTTOM);
        // Hollow interior
        tag("remove") up(wall)
            cuboid([inner_w, inner_d, inner_h+1], anchor=BOTTOM);
        // Side vent slots (both long sides)
        for (side = [-1, 1]) {
            tag("remove")
            translate([0, side * outer_d/2, wall + inner_h/2]) {
                // Use vent_slots module from thermal-design.md reference
                n = floor((inner_h * 0.6) / (vent_slot_w + vent_spacing));
                for (i = [0:n-1]) {
                    translate([0, 0, -n*(vent_slot_w+vent_spacing)/2 + i*(vent_slot_w+vent_spacing)])
                        cuboid([inner_w*0.7, wall+1, vent_slot_w], rounding=0.5);
                }
            }
        }
    }
}

thermal_enclosure();
```

### Pattern: Parameterize for Thingiverse Customizer compatibility
Use `/* [Section Name] */` comments and named parameters — they become UI sliders.

---

## Manifest Validation

Before exporting, check geometry is valid (manifold = watertight):
```bash
openscad --render -o /dev/null part.scad 2>&1 | grep -i "warning\|error\|manifold"
```

A silent exit (no warnings) means the geometry is clean and exportable.

---

## Common Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| `Object isn't a valid 2-manifold` | Boolean op created zero-thickness faces | Add `$eps` overlap to cutters (`h = wall + 0.01`) |
| Slow render | Complex BOSL2 geometry without manifold backend | Use `openscad --enable=manifold` flag |
| BOSL2 `include` not found | Library not on path | Set `OPENSCADPATH` or install to user library dir |
| STEP conversion artifacts | Mesh → BREP via FreeCAD loses parametric edges | Increase `$fn` before export for smoother meshes |
| DXF projection empty | Using 3D primitives without `projection()` | Wrap in `projection(cut=false) { ... }` |
| Heat sink fin too thin | Under-extrusion in FDM at fin_t < 0.8mm | Use fin_t ≥ 1.2mm for FDM, ≥ 0.6mm for SLA |
| Snap-fit breaks on insertion | Strain exceeds material limit | Check echo output; increase beam_l or reduce hook_h |
| Press-fit too loose/tight | FDM hole shrinkage not accounted for | Add 0.1–0.2mm to bore diameter for FDM |
| CNC pocket won't machine | Sharp internal corners | Add corner radius ≥ tool radius + 0.1mm |
| Thermal calc gives NaN | Zero-thickness or zero-area in formula | Ensure all dimensions > 0 before calculation |

---

## Reference Files

- `references/bosl2-cheatsheet.md` — BOSL2 module reference by category (primitives, attachments, gears, fasteners, transforms)
- `references/step-pipeline.md` — Full STL→STEP FreeCAD Python pipeline + headless script
- `references/cli-reference.md` — All OpenSCAD CLI flags with examples
- `references/thermal-design.md` — **NEW** Heat sink modules, cooling channels, thermal calcs, CTE compensation, vent/fan patterns, material thermal properties
- `references/dfm-and-structural.md` — **NEW** Ribs, bosses, snap-fits, press-fits, bearing pockets, springs, DFM rules (FDM/SLA/CNC/sheet metal/molding), section properties, beam deflection, tolerance stack-up
