# Thermal Design Patterns for OpenSCAD

> Parametric thermal management components: heat sinks, fin arrays, cooling channels,
> thermal enclosures, and heat pipe routing geometry — all with embedded engineering formulas.

---

## Table of Contents

1. [Heat Sink Fundamentals](#1-heat-sink-fundamentals)
2. [Plate-Fin Heat Sink Module](#2-plate-fin-heat-sink-module)
3. [Pin-Fin Heat Sink Module](#3-pin-fin-heat-sink-module)
4. [Radial / Sunburst Heat Sink](#4-radial--sunburst-heat-sink)
5. [Thermal Calculations (Echo-Based)](#5-thermal-calculations-echo-based)
6. [Cooling Channel Patterns](#6-cooling-channel-patterns)
7. [Thermal Expansion Compensation](#7-thermal-expansion-compensation)
8. [Ventilation & Airflow Geometry](#8-ventilation--airflow-geometry)
9. [Thermal Interface Patterns](#9-thermal-interface-patterns)
10. [Material Thermal Properties](#10-material-thermal-properties)

---

## 1. Heat Sink Fundamentals

**Key thermal resistance chain:**
```
T_junction → R_jc → T_case → R_interface → T_sink_base → R_sink → T_ambient
```

**Design levers for R_sink:**
- Increase total fin surface area (more fins, taller fins)
- Optimize fin spacing for airflow regime (natural vs. forced)
- Increase thermal conductivity (aluminum ~200 W/mK, copper ~390 W/mK)
- Thicker base for heat spreading

**Natural convection optimal fin spacing** (vertical orientation):
```
S_opt ≈ 2.714 * L / Ra_L^0.25
```
Where `Ra_L = g·β·ΔT·L³ / (ν·α)` (Rayleigh number based on fin height L).

**Rule of thumb for natural convection:** 6–12 mm fin spacing for fins 20–60 mm tall.
**Forced convection:** 1.5–4 mm spacing depending on fan CFM and duct geometry.

---

## 2. Plate-Fin Heat Sink Module

The workhorse. Rectangular base with parallel vertical fins.

```openscad
include <BOSL2/std.scad>

// ── Parameters ──────────────────────────────────────────────
// Base geometry
base_w     = 60;    // mm — base width (X)
base_d     = 60;    // mm — base depth (Y, along airflow)
base_h     = 3;     // mm — base plate thickness

// Fin geometry
fin_h      = 25;    // mm — fin height above base
fin_t      = 1.5;   // mm — fin thickness
fin_count  = 12;    // number of fins
fin_chamfer = 0.3;  // mm — top edge chamfer (DFM)

// Mounting
mount_hole_d    = 3.2;   // mm — M3 clearance
mount_inset     = 5;     // mm — hole center from edge
mount_cbore_d   = 6;     // mm — counterbore diameter
mount_cbore_h   = 2;     // mm — counterbore depth

// Thermal interface
contact_flatness = 0.05; // mm — bottom surface tolerance target

// Derived
fin_spacing = (base_w - fin_t) / (fin_count - 1);
fin_gap     = fin_spacing - fin_t;

// ── Modules ─────────────────────────────────────────────────

module plate_fin_heatsink() {
    // Thermal performance echo
    total_fin_area = 2 * fin_h * base_d * fin_count;  // both sides of each fin
    base_area      = base_w * base_d;
    echo(str("Fin gap: ", fin_gap, " mm"));
    echo(str("Total fin area: ", total_fin_area, " mm²"));
    echo(str("Base area: ", base_area, " mm²"));
    echo(str("Total surface: ", total_fin_area + base_area, " mm²"));
    echo(str("Fin aspect ratio (h/gap): ", fin_h / fin_gap));

    diff() {
        union() {
            // Base plate
            cuboid([base_w, base_d, base_h], anchor=BOTTOM);

            // Fins
            up(base_h)
            for (i = [0 : fin_count - 1]) {
                x_pos = -base_w/2 + fin_t/2 + i * fin_spacing;
                translate([x_pos, 0, 0])
                    cuboid([fin_t, base_d, fin_h],
                           anchor=BOTTOM,
                           chamfer=fin_chamfer, edges=TOP);
            }
        }

        // Mounting holes (4 corners)
        for (x = [-1, 1], y = [-1, 1]) {
            translate([x*(base_w/2 - mount_inset),
                       y*(base_d/2 - mount_inset), 0])
            {
                // Through-hole
                tag("remove") cyl(h=base_h+1, d=mount_hole_d, anchor=BOTTOM);
                // Counterbore from bottom
                tag("remove") cyl(h=mount_cbore_h, d=mount_cbore_d, anchor=BOTTOM);
            }
        }
    }
}

// ── Main ────────────────────────────────────────────────────
plate_fin_heatsink();
```

**Design guidance echoed at render time** — the script prints fin gap, total surface area, and fin aspect ratio so you can iterate without external tools.

---

## 3. Pin-Fin Heat Sink Module

Better omnidirectional performance for natural convection where airflow direction is unknown.

```openscad
include <BOSL2/std.scad>

// ── Parameters ──────────────────────────────────────────────
base_w     = 50;
base_d     = 50;
base_h     = 3;
pin_h      = 20;    // mm — pin height
pin_d      = 3;     // mm — pin diameter
pin_spacing = 6;    // mm — center-to-center pitch

// Derived
nx = floor((base_w - pin_d) / pin_spacing) + 1;
ny = floor((base_d - pin_d) / pin_spacing) + 1;
total_pins = nx * ny;
pin_area   = PI * pin_d * pin_h * total_pins;

module pin_fin_heatsink() {
    echo(str("Pin grid: ", nx, " x ", ny, " = ", total_pins, " pins"));
    echo(str("Total pin surface area: ", pin_area, " mm²"));

    // Base
    cuboid([base_w, base_d, base_h], anchor=BOTTOM);

    // Pins
    up(base_h)
    for (ix = [0 : nx-1], iy = [0 : ny-1]) {
        x = -base_w/2 + pin_d/2 + (base_w - pin_d - (nx-1)*pin_spacing)/2 + ix*pin_spacing;
        y = -base_d/2 + pin_d/2 + (base_d - pin_d - (ny-1)*pin_spacing)/2 + iy*pin_spacing;
        translate([x, y, 0])
            cyl(h=pin_h, d=pin_d, anchor=BOTTOM, $fn=16);
    }
}

pin_fin_heatsink();
```

**When to use pin-fin vs plate-fin:**
- Pin-fin: natural convection, unknown airflow direction, component radiates heat uniformly
- Plate-fin: forced convection with known airflow axis, higher total area per volume

---

## 4. Radial / Sunburst Heat Sink

For components mounted under circular hotspots (e.g., LED COBs, round power modules).

```openscad
include <BOSL2/std.scad>

// ── Parameters ──────────────────────────────────────────────
outer_r     = 40;    // mm — outer radius
inner_r     = 10;    // mm — center bore radius
base_h      = 3;     // mm — base thickness
fin_h       = 20;    // mm — fin height
fin_t       = 1.2;   // mm — fin thickness
fin_count   = 24;    // number of radial fins
center_bore = 6;     // mm — through-hole for thermal bolt

module radial_heatsink() {
    angle_step = 360 / fin_count;

    echo(str("Angular spacing: ", angle_step, " deg"));
    echo(str("Outer gap at tips: ", 2*PI*outer_r/fin_count - fin_t, " mm"));

    diff() {
        union() {
            // Base disc
            cyl(h=base_h, r=outer_r, anchor=BOTTOM);

            // Radial fins
            up(base_h)
            for (a = [0 : angle_step : 360-angle_step]) {
                zrot(a)
                translate([(inner_r + outer_r)/2, 0, 0])
                    cuboid([outer_r - inner_r, fin_t, fin_h], anchor=BOTTOM);
            }
        }

        // Center bore
        tag("remove") cyl(h=base_h + fin_h + 1, d=center_bore, anchor=BOTTOM);
    }
}

radial_heatsink();
```

---

## 5. Thermal Calculations (Echo-Based)

OpenSCAD can compute and echo thermal estimates at render time.
Embed these in your `.scad` files as design verification.

```openscad
// ── Thermal Resistance Calculator ───────────────────────────
// Call at top level to echo thermal resistance estimate

// Inputs
Q        = 15;      // W — heat dissipation
k_sink   = 200;     // W/(m·K) — thermal conductivity (Al 6061)
base_A   = 60*60;   // mm² — base contact area
base_t   = 3;       // mm — base thickness
n_fins   = 12;
fin_H    = 25;      // mm — fin height
fin_L    = 60;      // mm — fin length (airflow direction)
fin_t    = 1.5;     // mm — fin thickness
h_conv   = 10;      // W/(m²·K) — natural convection coefficient (typical 5-25)
T_amb    = 25;      // °C

// Calculations (all in SI internally)
base_A_m2  = base_A * 1e-6;
base_t_m   = base_t * 1e-3;
fin_area_per = 2 * fin_H * fin_L * 1e-6;   // m² per fin (both sides)
total_fin_area_m2 = fin_area_per * n_fins;
total_area_m2 = total_fin_area_m2 + base_A_m2;

// Conduction through base
R_base = base_t_m / (k_sink * base_A_m2);  // K/W

// Convection from fin surfaces
R_conv = 1 / (h_conv * total_area_m2);     // K/W

// Fin efficiency (approx for rectangular fin, insulated tip)
m_param = sqrt(2 * h_conv / (k_sink * fin_t * 1e-3));
fin_eff = tanh(m_param * fin_H * 1e-3) / (m_param * fin_H * 1e-3);

// Effective thermal resistance
R_total = R_base + R_conv / fin_eff;

// Temperature rise
dT = Q * R_total;
T_base = T_amb + dT;

echo(str("=== Thermal Estimate ==="));
echo(str("Total fin area: ", total_fin_area_m2 * 1e4, " cm²"));
echo(str("R_base (conduction): ", R_base, " K/W"));
echo(str("R_conv (convection): ", R_conv, " K/W"));
echo(str("Fin efficiency: ", fin_eff * 100, " %"));
echo(str("R_total: ", R_total, " K/W"));
echo(str("Temp rise at ", Q, " W: ", dT, " °C"));
echo(str("Base temp: ", T_base, " °C"));
```

**Usage:** Paste this block into any heat sink `.scad` file, adjust parameters, render with
`openscad -o /dev/null --export-format=echo heatsink.scad` to see thermal estimates without rendering geometry.

---

## 6. Cooling Channel Patterns

Internal cooling channels for liquid-cooled cold plates or mold cooling.

### Serpentine Channel (2.5D — for CNC or SLM)

```openscad
include <BOSL2/std.scad>

// ── Parameters ──────────────────────────────────────────────
plate_w     = 80;    // mm
plate_d     = 60;    // mm
plate_h     = 12;    // mm
ch_w        = 4;     // mm — channel width
ch_h        = 6;     // mm — channel depth
ch_wall     = 3;     // mm — wall between channels
n_passes    = 5;     // number of parallel passes
inlet_d     = 6;     // mm — inlet/outlet port diameter

module serpentine_coldplate() {
    pass_pitch = (plate_d - 2*ch_wall) / n_passes;

    diff() {
        // Solid plate
        cuboid([plate_w, plate_d, plate_h], anchor=BOTTOM);

        // Serpentine channel (cut from top)
        tag("remove")
        up(plate_h - ch_h)
        for (i = [0 : n_passes - 1]) {
            y = -plate_d/2 + ch_wall + pass_pitch/2 + i * pass_pitch;
            // Straight pass
            translate([0, y, 0])
                cuboid([plate_w - 2*ch_wall, ch_w, ch_h + 0.01], anchor=BOTTOM);
            // U-turn connectors
            if (i < n_passes - 1) {
                side = (i % 2 == 0) ? 1 : -1;
                translate([side * (plate_w/2 - ch_wall), (y + pass_pitch/2), 0])
                    cuboid([ch_w, pass_pitch, ch_h + 0.01], anchor=BOTTOM);
            }
        }

        // Inlet/outlet ports (through bottom)
        for (side = [-1, 1]) {
            y_port = (side == -1) ?
                -plate_d/2 + ch_wall + pass_pitch/2 :
                -plate_d/2 + ch_wall + pass_pitch/2 + (n_passes-1) * pass_pitch;
            x_port = (n_passes % 2 == 1 && side == 1) ?
                (plate_w/2 - ch_wall) : -(plate_w/2 - ch_wall);
            tag("remove")
            translate([x_port, y_port, 0])
                cyl(h=plate_h - ch_h + 0.01, d=inlet_d, anchor=BOTTOM);
        }
    }
}

serpentine_coldplate();
```

### Conformal Cooling (SLM/DMLS — fully 3D)

For metal 3D printed parts, channels can follow curved surfaces:

```openscad
include <BOSL2/std.scad>
include <BOSL2/skin.scad>

// Conformal channel along a path
ch_d = 4;  // mm channel diameter
path = [
    [0, -25, 0], [15, -25, 3], [25, -15, 5],
    [25, 15, 5], [15, 25, 3], [0, 25, 0],
    [-15, 25, -3], [-25, 15, -5],
    [-25, -15, -5], [-15, -25, -3], [0, -25, 0]
];

// Use path_sweep for round-section channel
module conformal_channel(path, d) {
    // path_sweep with circle profile
    path_sweep(circle(d=d, $fn=24), path, closed=true);
}

// Example: subtract from a curved body
diff() {
    cyl(h=12, r=30, anchor=BOTTOM);
    tag("remove") up(6) conformal_channel(path, ch_d);
}
```

---

## 7. Thermal Expansion Compensation

For multi-material assemblies or parts operating across temperature ranges.

```openscad
// ── CTE-Aware Dimensioning ──────────────────────────────────
// Compute dimension at operating temperature

function thermal_dim(L_ref, CTE, T_ref, T_op) =
    L_ref * (1 + CTE * (T_op - T_ref));

// Common CTEs (ppm/°C = 1e-6 /°C)
CTE_AL6061   = 23.6e-6;
CTE_STEEL304 = 17.3e-6;
CTE_COPPER   = 16.5e-6;
CTE_PLA      = 68e-6;
CTE_ABS      = 73e-6;
CTE_NYLON    = 80e-6;
CTE_PETG     = 60e-6;
CTE_INVAR    = 1.2e-6;
CTE_TITANIUM = 8.6e-6;
CTE_CARBON_FIBER = 0.5e-6;  // longitudinal, varies by layup

// Example: aluminum bore that must accept a steel shaft at 80°C
shaft_d_ref  = 10.0;   // mm at 20°C
bore_d_ref   = 10.05;  // mm at 20°C (50 µm clearance at ref temp)
T_ref        = 20;
T_op         = 80;

shaft_d_hot = thermal_dim(shaft_d_ref, CTE_STEEL304, T_ref, T_op);
bore_d_hot  = thermal_dim(bore_d_ref, CTE_AL6061, T_ref, T_op);
clearance_hot = bore_d_hot - shaft_d_hot;

echo(str("Shaft at ", T_op, "°C: ", shaft_d_hot, " mm"));
echo(str("Bore at ", T_op, "°C: ", bore_d_hot, " mm"));
echo(str("Hot clearance: ", clearance_hot * 1000, " µm"));
// If clearance_hot < 0, you have interference — redesign!
```

---

## 8. Ventilation & Airflow Geometry

### Parametric Vent Slots

```openscad
include <BOSL2/std.scad>

module vent_slots(area_w, area_h, slot_w=2, slot_spacing=3, slot_r=0.5) {
    // Horizontal slots across a rectangular area
    n = floor(area_h / (slot_w + slot_spacing));
    actual_h = n * (slot_w + slot_spacing) - slot_spacing;
    start_y = -actual_h/2 + slot_w/2;

    open_fraction = (n * slot_w * area_w) / (area_w * area_h);
    echo(str("Vent open area fraction: ", open_fraction * 100, " %"));

    for (i = [0 : n-1]) {
        translate([0, start_y + i*(slot_w + slot_spacing), 0])
            cuboid([area_w, slot_w, 10], rounding=slot_r);  // 10mm = penetration depth
    }
}

// Honeycomb Vent Pattern
module hex_vent(area_w, area_h, hex_d=8, wall=1.5, depth=2) {
    hex_r   = hex_d / 2;
    dx      = hex_d + wall;
    dy      = (hex_d + wall) * sqrt(3) / 2;

    nx = floor(area_w / dx);
    ny = floor(area_h / dy);

    for (ix = [0 : nx], iy = [0 : ny]) {
        offset_x = (iy % 2) * dx / 2;
        x = -area_w/2 + ix * dx + offset_x;
        y = -area_h/2 + iy * dy;
        if (abs(x) < area_w/2 - hex_r && abs(y) < area_h/2 - hex_r) {
            translate([x, y, 0])
                linear_extrude(depth + 0.01)
                    regular_ngon(n=6, d=hex_d);
        }
    }
}
```

### Fan Mount Pattern

```openscad
include <BOSL2/std.scad>

// Standard fan mount holes
// fan_size: 25, 30, 40, 50, 60, 70, 80, 92, 120, 140 mm
function fan_hole_spacing(fan_size) =
    fan_size == 25  ? 20 :
    fan_size == 30  ? 24 :
    fan_size == 40  ? 32 :
    fan_size == 50  ? 40 :
    fan_size == 60  ? 50 :
    fan_size == 70  ? 61.5 :
    fan_size == 80  ? 71.5 :
    fan_size == 92  ? 82.5 :
    fan_size == 120 ? 105 :
    fan_size == 140 ? 124.5 : 0;

module fan_mount_holes(fan_size, screw_d=3.2, depth=10) {
    spacing = fan_hole_spacing(fan_size);
    half = spacing / 2;
    for (x = [-half, half], y = [-half, half]) {
        translate([x, y, 0])
            cyl(h=depth, d=screw_d, anchor=BOTTOM);
    }
}

module fan_cutout(fan_size, depth=5) {
    // Center opening + mount holes
    cyl(h=depth, d=fan_size - 4, anchor=BOTTOM, $fn=64);
    fan_mount_holes(fan_size, depth=depth);
}
```

---

## 9. Thermal Interface Patterns

### TIM Pad Recess

```openscad
// Recess for thermal interface pad between heat sink and component
module tim_recess(w, d, depth=0.5, corner_r=1) {
    // Slight recess to locate TIM pad and control bond line thickness
    translate([0, 0, -depth])
        linear_extrude(depth + 0.01)
            rect([w, d], rounding=corner_r);
}
```

### Spring-Clip Mount Slots

```openscad
// Slots for z-clip or push-pin heat sink retention
module clip_slot(slot_l=12, slot_w=2.5, depth=5) {
    cuboid([slot_l, slot_w, depth + 0.01], rounding=slot_w/4, edges=TOP);
}
```

---

## 10. Material Thermal Properties

Reference table for echo-based calculations. Paste the relevant values into your `.scad` file.

| Material | k (W/m·K) | CTE (µm/m·°C) | ρ (kg/m³) | Cp (J/kg·K) | Max Temp (°C) |
|----------|-----------|----------------|-----------|-------------|---------------|
| Aluminum 6061-T6 | 167 | 23.6 | 2700 | 896 | ~300 (softens) |
| Aluminum 7075 | 130 | 23.4 | 2810 | 960 | ~300 |
| Copper C110 | 390 | 16.5 | 8940 | 385 | ~200 (oxidizes) |
| Stainless 304 | 16.2 | 17.3 | 8000 | 500 | 870 |
| Stainless 316 | 16.3 | 15.9 | 8000 | 500 | 870 |
| Titanium Ti-6Al-4V | 6.7 | 8.6 | 4430 | 526 | 315 (creep) |
| Carbon Steel 1045 | 49.8 | 11.2 | 7850 | 486 | ~500 |
| Brass C360 | 115 | 20.5 | 8500 | 380 | ~260 |
| PLA | 0.13 | 68 | 1240 | 1800 | 50–60 (glass) |
| ABS | 0.17 | 73 | 1050 | 1400 | 80–100 |
| PETG | 0.20 | 60 | 1270 | 1200 | 70–80 |
| Nylon (PA6) | 0.25 | 80 | 1140 | 1700 | 80–120 |
| PC (Polycarbonate) | 0.20 | 65 | 1200 | 1200 | 120–140 |
| PEEK | 0.25 | 47 | 1300 | 1340 | 250 |
| FR-4 (PCB) | 0.30 | 14 (XY) / 60 (Z) | 1850 | 1100 | 130 (Tg) |
| Thermal pad (generic) | 1–6 | — | — | — | 200+ |
| Thermal paste (generic) | 1–12 | — | — | — | 200+ |
| Alumina (Al₂O₃) | 30 | 7.0 | 3900 | 900 | 1700 |
| AlN (aluminum nitride) | 170 | 4.5 | 3260 | 740 | 1000+ |

---

## Design Heuristics

**Heat sink sizing rules of thumb:**
- Natural convection: ~10–20 cm² per watt for ΔT ≈ 40°C above ambient
- Forced convection (1–2 m/s): ~3–5 cm² per watt
- Fin efficiency drops sharply past aspect ratio (h/gap) > 8
- Base thickness: at least √(A_source / π) × 0.5 for adequate spreading

**Channel cooling:**
- Turbulent flow (Re > 4000) gives 3–10× better heat transfer vs. laminar
- Minimum channel diameter for 3D printing: ~1.5 mm (SLM), ~2 mm (FDM)
- Pressure drop scales as L/D⁵ — wider channels reduce pumping power dramatically

**Thermal interface:**
- Bond line thickness dominates interface resistance — keep TIM < 0.1 mm if possible
- Spring-loaded clips maintain compression better than adhesive over thermal cycles
- Always specify mounting torque for bolted heat sinks (typically 0.3–0.5 N·m for M3)
