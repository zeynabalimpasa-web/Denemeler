# Structural Design & DFM Patterns for OpenSCAD

> Structural reinforcement patterns, snap-fit / press-fit design, material-aware DFM rules,
> and engineering calculation helpers for parametric mechanical parts.

---

## Table of Contents

1. [Structural Reinforcement Patterns](#1-structural-reinforcement-patterns)
2. [Snap-Fit & Living Hinge Design](#2-snap-fit--living-hinge-design)
3. [Press-Fit & Interference Fit Sizing](#3-press-fit--interference-fit-sizing)
4. [Bearing & Shaft Interface Patterns](#4-bearing--shaft-interface-patterns)
5. [Spring Geometry](#5-spring-geometry)
6. [DFM: FDM / FFF 3D Printing](#6-dfm-fdm--fff-3d-printing)
7. [DFM: SLA / Resin Printing](#7-dfm-sla--resin-printing)
8. [DFM: CNC Machining](#8-dfm-cnc-machining)
9. [DFM: Sheet Metal](#9-dfm-sheet-metal)
10. [DFM: Injection Molding](#10-dfm-injection-molding)
11. [Section Property Calculators](#11-section-property-calculators)
12. [Beam Deflection Estimators](#12-beam-deflection-estimators)
13. [Tolerance Stack-Up Helper](#13-tolerance-stack-up-helper)

---

## 1. Structural Reinforcement Patterns

### Rib Pattern Module

```openscad
include <BOSL2/std.scad>

// Triangular gusset rib (placed at wall-floor junctions)
module gusset_rib(h=15, base=15, t=2) {
    // Right-triangle gusset oriented in XZ plane
    linear_extrude(t, center=true)
        polygon([[0,0], [base,0], [0,h]]);
}

// Linear rib array along a wall
module rib_array(wall_l, rib_h=15, rib_base=15, rib_t=2, spacing=20) {
    n = floor(wall_l / spacing);
    for (i = [0 : n]) {
        translate([i * spacing - wall_l/2 + spacing/2, 0, 0])
            gusset_rib(h=rib_h, base=rib_base, t=rib_t);
    }
}

// Cross-pattern reinforcement (waffle / egg-crate)
module waffle_ribs(area_w, area_d, rib_h=8, rib_t=1.5, spacing=15) {
    nx = floor(area_w / spacing);
    ny = floor(area_d / spacing);

    // X-direction ribs
    for (i = [0 : nx]) {
        x = -area_w/2 + i * spacing;
        translate([x, 0, 0])
            cuboid([rib_t, area_d, rib_h], anchor=BOTTOM);
    }
    // Y-direction ribs
    for (j = [0 : ny]) {
        y = -area_d/2 + j * spacing;
        translate([0, y, 0])
            cuboid([area_w, rib_t, rib_h], anchor=BOTTOM);
    }
}
```

**Rib design rules:**
- Rib thickness ≤ 0.6× adjacent wall thickness (prevents sink marks in molding)
- Rib height ≤ 3× rib thickness for moldability
- Draft angle: 0.5°–1° per side for ribs
- For 3D printing: ribs can be any aspect ratio, but >8:1 may need support

### Boss Pattern (for screw posts)

```openscad
include <BOSL2/std.scad>

// Self-tapping screw boss for plastics
module screw_boss(od=8, id=2.5, h=12, gusset=true, gusset_h=8, n_gussets=4) {
    diff() {
        union() {
            // Main boss cylinder
            cyl(h=h, d=od, anchor=BOTTOM);
            // Gussets for reinforcement
            if (gusset) {
                for (a = [0 : 360/n_gussets : 360 - 360/n_gussets]) {
                    zrot(a)
                    translate([od/4, 0, 0])
                        cuboid([od/2, 1.5, gusset_h], anchor=BOTTOM);
                }
            }
        }
        // Pilot hole
        tag("remove") cyl(h=h+1, d=id, anchor=BOTTOM);
    }
}
```

**Self-tapping screw pilot hole sizing (plastics):**

| Screw Size | Boss OD (mm) | Pilot Hole ID (mm) |
|-----------|-------------|-------------------|
| M2 (ST2.2) | 5.0 | 1.8 |
| M2.5 (ST2.9) | 6.5 | 2.3 |
| M3 (ST3.5) | 8.0 | 2.8 |
| M4 (ST4.2) | 9.5 | 3.4 |
| M5 (ST4.8) | 11.0 | 3.9 |

---

## 2. Snap-Fit & Living Hinge Design

### Cantilever Snap-Fit

```openscad
include <BOSL2/std.scad>

// Cantilever snap-fit hook
module snap_hook(
    beam_l    = 12,   // mm — cantilever length
    beam_w    = 6,    // mm — beam width
    beam_t    = 1.5,  // mm — beam thickness
    hook_h    = 1.0,  // mm — hook undercut depth
    hook_l    = 2.0,  // mm — hook lip length
    entry_angle = 30  // degrees — insertion ramp angle
) {
    // Strain check (echo at render time)
    // Max strain at root = (1.5 * hook_h * beam_t) / (beam_l^2)
    max_strain = (1.5 * hook_h * beam_t) / (beam_l * beam_l);
    echo(str("Snap-fit max strain: ", max_strain * 100, " %"));
    echo(str("  OK for ABS (< 5%): ", max_strain < 0.05 ? "YES" : "NO — reduce hook_h or increase beam_l"));
    echo(str("  OK for PC  (< 4%): ", max_strain < 0.04 ? "YES" : "NO"));
    echo(str("  OK for POM (< 6%): ", max_strain < 0.06 ? "YES" : "NO"));
    echo(str("  OK for PP  (< 8%): ", max_strain < 0.08 ? "YES" : "NO"));

    // Beam
    cuboid([beam_l, beam_w, beam_t], anchor=LEFT+BOTTOM);

    // Hook with angled entry and vertical retention face
    translate([beam_l, 0, 0])
    union() {
        // Ramp (entry)
        translate([0, 0, beam_t])
            rotate([0, 0, 0])
            linear_extrude(hook_h)
                polygon([
                    [-hook_h/tan(entry_angle), -beam_w/2],
                    [-hook_h/tan(entry_angle),  beam_w/2],
                    [0,  beam_w/2],
                    [0, -beam_w/2]
                ]);
        // Lip (retention)
        translate([0, 0, beam_t])
            cuboid([hook_l, beam_w, hook_h], anchor=LEFT+BOTTOM);
    }
}
```

**Allowable strain by material (single insertion):**

| Material | Max Strain (%) | Notes |
|----------|---------------|-------|
| ABS | 4–5 | Good all-rounder |
| PC | 3–4 | Stiffer, less forgiving |
| POM (Delrin) | 5–6 | Excellent for repeated snap |
| PP | 6–8 | Very flexible |
| Nylon (PA) | 4–6 | Good, moisture-sensitive |
| PLA | 1.5–2 | Brittle — avoid snap-fits |
| PETG | 3–4 | Decent |

### Living Hinge (print-in-place)

```openscad
include <BOSL2/std.scad>

module living_hinge(w=40, hinge_t=0.4, hinge_l=2, n_slits=5) {
    // Multiple thin sections with slits for flex distribution
    slit_w = 1.5;
    slit_gap = w / (n_slits + 1);

    difference() {
        cuboid([hinge_l, w, hinge_t], anchor=BOTTOM);
        // Alternating slits for strain distribution
        for (i = [1 : n_slits]) {
            translate([0, -w/2 + i * slit_gap, 0])
                cuboid([hinge_l * 0.7, slit_w, hinge_t + 0.1], anchor=BOTTOM);
        }
    }
}
```

**Living hinge rules:** PP is best (0.25–0.5 mm thick), PETG workable (0.4–0.6 mm), PLA does not survive repeated flexing.

---

## 3. Press-Fit & Interference Fit Sizing

```openscad
// ── Press-Fit Calculator ────────────────────────────────────
// Interference fit for shaft-in-bore assemblies

function press_fit_bore(shaft_d, fit="light") =
    fit == "light"  ? shaft_d - 0.01 * shaft_d :   // H7/n6-ish
    fit == "medium" ? shaft_d - 0.015 * shaft_d :   // H7/p6
    fit == "heavy"  ? shaft_d - 0.02 * shaft_d :    // H7/s6
    shaft_d;  // clearance

// Example
shaft = 8.000;  // mm
bore  = press_fit_bore(shaft, "medium");
echo(str("Shaft: ", shaft, " mm, Bore: ", bore, " mm, Interference: ", (shaft - bore)*1000, " µm"));
```

**3D-printed press-fit adjustments (FDM):**
- FDM shrinks holes by ~0.1–0.2 mm diameter → add 0.1 mm to bore for light press-fit
- Shaft: print nominal or +0.05 mm
- Test with calibration prints — every printer differs

**Common interference fits (machined, metric):**

| Fit Class | Interference (on Ø10 shaft) | Use Case |
|-----------|----------------------------|----------|
| H7/h6 (sliding) | 0 to +15 µm clearance | Locating, alignment |
| H7/k6 (transition) | -2 to +13 µm | Light press, hand assembly |
| H7/n6 (light press) | -10 to +1 µm | Pulleys, gears on shafts |
| H7/p6 (press) | -14 to -1 µm | Bearings, permanent assembly |
| H7/s6 (heavy press) | -28 to -14 µm | High-torque, requires arbor press |

---

## 4. Bearing & Shaft Interface Patterns

```openscad
include <BOSL2/std.scad>

// Standard bearing pocket module
module bearing_pocket(
    od, width,       // bearing OD and width
    press_fit = true,
    lip_h = 0.5,     // retention lip height
    lip_t = 0.5,     // retention lip radial thickness
    depth_extra = 0  // extra pocket depth
) {
    // Press-fit pocket: bore = bearing OD - interference
    bore_d = press_fit ? od - 0.03 : od + 0.05;  // tight vs. slip fit

    echo(str("Bearing pocket bore: ", bore_d, " mm for ", od, " mm bearing"));

    diff() {
        cyl(h=width + depth_extra, d=bore_d, anchor=BOTTOM);
        // Retention lip at opening
        if (lip_h > 0) {
            tag("remove")
            up(width + depth_extra - lip_h)
                tube(h=lip_h + 0.01, od=bore_d + 1, id=bore_d - 2*lip_t, anchor=BOTTOM);
        }
    }
}
```

**Common bearing dimensions (608, 6001, 6200 series):**

| Bearing | ID (mm) | OD (mm) | Width (mm) |
|---------|---------|---------|------------|
| 608-2RS | 8 | 22 | 7 |
| 6000-2RS | 10 | 26 | 8 |
| 6001-2RS | 12 | 28 | 8 |
| 6002-2RS | 15 | 32 | 9 |
| 6200-2RS | 10 | 30 | 9 |
| 6201-2RS | 12 | 32 | 10 |
| 6202-2RS | 15 | 35 | 11 |
| 6203-2RS | 17 | 40 | 12 |
| 6204-2RS | 20 | 47 | 14 |

---

## 5. Spring Geometry

### Coil Spring (visual / spatial planning)

```openscad
include <BOSL2/std.scad>

module coil_spring(wire_d=1.5, coil_d=12, pitch=4, n_coils=8) {
    total_h = pitch * n_coils;
    coil_r  = (coil_d - wire_d) / 2;

    echo(str("Spring free length: ", total_h, " mm"));
    echo(str("Approx spring rate (steel): ",
        (79300 * pow(wire_d, 4)) / (8 * pow(coil_d, 3) * n_coils),
        " N/mm"));  // G_steel = 79300 MPa

    // Helix as sweep
    steps = n_coils * 36;
    path = [for (i = [0 : steps])
        let(a = i * 360 / 36)
        [coil_r * cos(a), coil_r * sin(a), i * pitch / 36]
    ];

    // Sweep a circle along the helix
    // (Note: requires BOSL2 path_sweep or manual polyhedron)
    color("silver")
    for (i = [0 : len(path)-2]) {
        hull() {
            translate(path[i]) sphere(d=wire_d, $fn=12);
            translate(path[i+1]) sphere(d=wire_d, $fn=12);
        }
    }
}

coil_spring();
```

### Leaf Spring

```openscad
include <BOSL2/std.scad>

module leaf_spring(l=60, w=10, t=1.2, deflection=5, n_segments=20) {
    // Approximate curved beam as segmented strip
    seg_l = l / n_segments;
    // Parabolic deflection curve
    for (i = [0 : n_segments - 1]) {
        x0 = i * seg_l - l/2;
        x1 = (i+1) * seg_l - l/2;
        z0 = deflection * (1 - pow(2*x0/l, 2));
        z1 = deflection * (1 - pow(2*x1/l, 2));
        hull() {
            translate([x0, 0, z0]) cuboid([seg_l*0.1, w, t], anchor=CENTER);
            translate([x1, 0, z1]) cuboid([seg_l*0.1, w, t], anchor=CENTER);
        }
    }
}
```

---

## 6. DFM: FDM / FFF 3D Printing

**General constraints for FDM with 0.4mm nozzle:**

| Feature | Minimum | Recommended | Notes |
|---------|---------|-------------|-------|
| Wall thickness | 0.8 mm (2 perimeters) | 1.2–1.6 mm | For structural parts |
| Hole diameter accuracy | ±0.2 mm | ±0.1 mm with calibration | Holes shrink ~0.1–0.2 mm |
| Overhang angle | 45° | 50–60° | Beyond needs support |
| Bridge length | 5–10 mm | < 5 mm for quality | Cooling dependent |
| Minimum feature | 0.4 mm | 0.8 mm | Nozzle diameter limited |
| Clearance (moving parts) | 0.3 mm | 0.4–0.5 mm | Per side |
| Embossed text height | 0.4 mm | 0.6 mm | Raised from surface |
| Engraved text depth | 0.3 mm | 0.5 mm | Cut into surface |
| Pin/hole fit clearance | 0.15 mm/side | 0.2 mm/side | For snap or press fit |
| Horizontal hole (no support) | Use teardrop! | BOSL2 `teardrop()` | Self-supporting shape |

**Print orientation strategy:**
- Strongest axis: along layer lines (XY), weakest: between layers (Z)
- Orient load-bearing features so primary stress is in XY plane
- Use `teardrop()` for horizontal holes to avoid support
- Flat mating surfaces should face the build plate

```openscad
// FDM-friendly horizontal hole (self-supporting teardrop)
include <BOSL2/std.scad>
teardrop(d=8, h=20, ang=45);  // replaces cylinder for side-mounted holes
```

---

## 7. DFM: SLA / Resin Printing

| Feature | Minimum | Notes |
|---------|---------|-------|
| Wall thickness | 0.4 mm | 0.8 mm for structural |
| Hole diameter | 0.5 mm | Drain holes needed for hollow parts! |
| Min feature | 0.15 mm | Layer height dependent |
| Clearance | 0.15 mm/side | Better than FDM |
| Unsupported overhang | 1 mm | 19° min from horizontal |
| Drain holes for hollow parts | ≥ 2.5 mm | Two holes for flow |
| Suction cup avoidance | Tilt 10–20° | Reduce peel forces |

**Key SLA rule:** Always add drain holes to hollow sections (minimum 2.5 mm diameter, at least 2 holes placed at lowest points during print orientation). Trapped resin = warping, cracking, uncured hazard.

---

## 8. DFM: CNC Machining

| Feature | Minimum | Recommended | Notes |
|---------|---------|-------------|-------|
| Internal corner radius | ≥ tool radius | 1.5× tool radius + 0.1 mm | Can't cut sharp internal corners |
| Min pocket depth-to-width | — | ≤ 4:1 | Tool deflection beyond this |
| Wall thickness | 0.5 mm (Al) | 1.5 mm (Al), 0.8 mm (steel) | Chatter risk on thin walls |
| Hole depth (drilling) | — | ≤ 10× diameter | Deep holes need peck drilling |
| Thread depth | — | 1.5× diameter | M3 in Al: 4.5 mm min engagement |
| Undercuts | Avoid if possible | T-slot cutter if needed | Adds setup, cost |
| Surface finish (standard) | Ra 3.2 µm | Ra 1.6 µm with finish pass | Mirror: Ra 0.4 µm |
| Flat bottom pocket corners | R ≥ 1 mm | R ≥ 1.5 mm | 1/8" endmill = 1.59 mm radius |

```openscad
// CNC-friendly internal pocket with proper corner radii
module cnc_pocket(w, d, depth, corner_r=1.6) {
    linear_extrude(depth)
        rect([w, d], rounding=corner_r);
}
```

**5-axis rules of thumb:**
- Undercuts and compound surfaces OK but increase cost 3–5×
- Keep datum surfaces accessible from one setup where possible
- Add alignment features (dowel holes) for multi-setup parts

---

## 9. DFM: Sheet Metal

```openscad
// Sheet metal bend allowance calculator
function bend_allowance(r, t, angle_deg, k=0.33) =
    (angle_deg / 180) * PI * (r + k * t);

// Common k-factors by material
// Soft aluminum: k = 0.33
// Mild steel: k = 0.41
// Stainless: k = 0.45
// Spring steel: k = 0.50

// Example: 90° bend, 1mm aluminum sheet, 1mm inner radius
ba = bend_allowance(1, 1, 90, 0.33);
echo(str("Bend allowance: ", ba, " mm"));
echo(str("Flat pattern deduction: ", 2*(1+1) - ba, " mm"));
```

**Sheet metal design rules:**

| Rule | Guideline |
|------|-----------|
| Min bend radius | ≥ sheet thickness (soft Al), ≥ 1.5t (steel) |
| Min flange length | ≥ 4× thickness |
| Hole-to-bend distance | ≥ 2.5× thickness + bend radius |
| Hole-to-edge distance | ≥ 2× thickness |
| Min slot width | ≥ 1.5× thickness |
| Tab/slot fit clearance | 0.05–0.1 mm per side |
| Standard gauges | 20ga (0.8mm), 18ga (1.2mm), 16ga (1.5mm), 14ga (1.9mm) |

---

## 10. DFM: Injection Molding

| Rule | Guideline |
|------|-----------|
| Draft angle | 1–2° per side (standard), 0.5° min |
| Wall thickness | Uniform! ±10% variation max |
| Rib thickness | ≤ 0.6× wall thickness |
| Rib height | ≤ 3× rib thickness |
| Boss OD | 2× screw diameter |
| Boss wall | ≤ 0.6× adjacent wall |
| Core/cavity shut-off angle | ≥ 3° |
| Gate vestige | Plan gate location on non-cosmetic surface |
| Sink mark avoidance | Avoid thick sections; core out solid areas |
| Undercuts | Side actions ($$$) or collapsing cores |
| Minimum radius | 0.5× wall thickness on all internal corners |

---

## 11. Section Property Calculators

```openscad
// ── Cross-Section Moment of Inertia ─────────────────────────
// Rectangular section
function I_rect(b, h) = b * pow(h, 3) / 12;          // mm⁴
function S_rect(b, h) = b * pow(h, 2) / 6;            // section modulus mm³
function A_rect(b, h) = b * h;

// Circular section
function I_circle(d) = PI * pow(d, 4) / 64;
function S_circle(d) = PI * pow(d, 3) / 32;
function A_circle(d) = PI * pow(d, 2) / 4;

// Hollow circular (tube)
function I_tube(od, id) = PI * (pow(od, 4) - pow(id, 4)) / 64;
function S_tube(od, id) = PI * (pow(od, 4) - pow(id, 4)) / (32 * od);
function A_tube(od, id) = PI * (pow(od, 2) - pow(id, 2)) / 4;

// I-beam / channel (simplified, symmetric)
function I_beam(w, h, tw, tf) =
    (w * pow(h, 3) - (w - tw) * pow(h - 2*tf, 3)) / 12;

// Example usage
echo(str("I (30×10 rect): ", I_rect(30, 10), " mm⁴"));
echo(str("I (Ø12 solid): ", I_circle(12), " mm⁴"));
echo(str("I (Ø12/Ø8 tube): ", I_tube(12, 8), " mm⁴"));
```

---

## 12. Beam Deflection Estimators

```openscad
// ── Beam Deflection (echo at render time) ───────────────────
// Cantilever beam, point load at tip
function deflect_cantilever_point(P, L, E, I) = P * pow(L, 3) / (3 * E * I);

// Simply supported beam, center point load
function deflect_simply_supported_center(P, L, E, I) = P * pow(L, 3) / (48 * E * I);

// Simply supported beam, uniform distributed load
function deflect_simply_supported_udl(w, L, E, I) = 5 * w * pow(L, 4) / (384 * E * I);

// Max bending stress (cantilever, point load at tip)
function stress_cantilever(P, L, I, c) = P * L * c / I;  // c = distance to neutral axis

// Common Young's modulus values (MPa)
E_AL6061  = 68900;
E_STEEL   = 200000;
E_PLA     = 2500;     // approximate, varies with temp
E_ABS     = 2100;
E_PETG    = 2000;
E_NYLON   = 1700;
E_PC      = 2300;
E_PEEK    = 4100;

// Example: 3mm thick × 20mm wide PLA cantilever, 100mm long, 5N tip load
P = 5;        // N
L = 100;      // mm
b = 20;       // mm
h = 3;        // mm
E = E_PLA;
I = I_rect(b, h);
c = h / 2;

d = deflect_cantilever_point(P, L, E, I);
sigma = stress_cantilever(P, L, I, c);

echo(str("Deflection: ", d, " mm"));
echo(str("Max stress: ", sigma, " MPa"));
echo(str("PLA yield (~50 MPa): ", sigma < 50 ? "SAFE" : "EXCEEDS YIELD"));
```

---

## 13. Tolerance Stack-Up Helper

```openscad
// ── Tolerance Stack-Up Analysis (RSS method) ────────────────
// Each dimension is [nominal, tolerance_plus_minus]

// Worst-case stack: sum of all tolerances
function wc_stack(dims) =
    [for (s = [0], d = dims) s + d[0]][len(dims)];

function wc_tol(dims) =
    [for (s = [0], d = dims) s + d[1]][len(dims)];

// RSS (root sum of squares): statistical stack
function rss_tol(dims) =
    sqrt([for (s = [0], d = dims) s + pow(d[1], 2)][len(dims)]);

// Example: 3-part stack-up
dims = [
    [10.00, 0.05],  // part A
    [ 5.00, 0.10],  // spacer
    [15.00, 0.05],  // part B
];

nominal = 10 + 5 + 15;
wc = 0.05 + 0.10 + 0.05;
rss = sqrt(pow(0.05,2) + pow(0.10,2) + pow(0.05,2));

echo(str("Nominal total: ", nominal, " mm"));
echo(str("Worst-case tolerance: ±", wc, " mm → range ", nominal-wc, " to ", nominal+wc));
echo(str("RSS tolerance (3σ): ±", rss, " mm → range ", nominal-rss, " to ", nominal+rss));
```
