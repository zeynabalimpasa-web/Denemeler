# BOSL2 Cheatsheet for Mechanical Engineering

> Requires: `include <BOSL2/std.scad>` at top of every file.
> Full docs: https://github.com/BelfrySCAD/BOSL2/wiki

---

## Table of Contents

1. [Primitives & Building Blocks](#1-primitives--building-blocks)
2. [Attachments System](#2-attachments-system)
3. [Boolean Helpers](#3-boolean-helpers)
4. [Gears](#4-gears)
5. [Fasteners & Threads](#5-fasteners--threads)
6. [Rounding, Filleting, Chamfering](#6-rounding-filleting-chamfering)
7. [Transforms & Positioning](#7-transforms--positioning)
8. [2D Shapes for Extrusion](#8-2d-shapes-for-extrusion)
9. [Common Includes](#9-common-includes)

---

## 1. Primitives & Building Blocks

```openscad
include <BOSL2/std.scad>

// Rounded cuboid
cuboid([40, 30, 10], rounding=2);
cuboid([40, 30, 10], rounding=2, edges=TOP);    // only top edges
cuboid([40, 30, 10], chamfer=1, edges=BOTTOM);  // chamfer bottom edges

// Tube (cylinder with hole)
tube(h=20, od=15, id=8);    // outer/inner diameter
tube(h=20, od=15, wall=2);  // via wall thickness

// Prism
prismoid(size1=[40,40], size2=[20,20], h=20);  // tapered box

// Rounded prism
rounding_prism(size=[40,30,20], rounding=3);

// Teardrop (3D-print friendly circular hole)
teardrop(d=10, h=20, angle=45);  // for horizontal holes - self-supporting
```

---

## 2. Attachments System

The attachment system is BOSL2's superpower. It positions children
relative to named anchor points, eliminating manual translate() math.

**Named anchors:** `TOP`, `BOTTOM`, `LEFT`, `RIGHT`, `FRONT`, `BACK`, `CENTER`
**Compound:** `TOP+LEFT`, `FRONT+BOTTOM`, etc.

```openscad
// Basic: attach child to parent
parent_shape()
  attach(parent_anchor, child_anchor) child_shape();

// Example: bolt standoff on top of plate
cuboid([60, 40, 4])
  attach(TOP+FRONT+LEFT, BOTTOM) cylinder(h=12, d=8);

// Attach to multiple anchors at once
cuboid([60, 40, 4])
  attach(TOP, BOTTOM) {
    move([-20, -10, 0]) cylinder(h=12, d=8);
    move([ 20, -10, 0]) cylinder(h=12, d=8);
    move([-20,  10, 0]) cylinder(h=12, d=8);
    move([ 20,  10, 0]) cylinder(h=12, d=8);
  }

// Overlap: how much child buries into parent (for boolean ops)
cuboid([60, 40, 4])
  attach(TOP, BOTTOM, overlap=2) cylinder(h=12, d=8);
```

**Custom anchors** on modules:
```openscad
module my_bracket(w=40, h=30) {
  attachable(anchor, spin, orient, size=[w, 4, h]) {
    // geometry here
    children();
  }
}
```

---

## 3. Boolean Helpers

```openscad
// diff() — shorthand difference with "remove" tagged children
diff()
  cuboid([40, 30, 10])
    attach(TOP, TOP) tag("remove") cylinder(h=11, d=8);

// union shorthand
union() { ... }  // same as standard OpenSCAD

// hull() with rounding
hull() {
  translate([ 15,  0, 0]) sphere(r=5);
  translate([-15,  0, 0]) sphere(r=5);
}
```

---

## 4. Gears

```openscad
include <BOSL2/std.scad>
include <BOSL2/gears.scad>

// Spur gear
spur_gear(
  pitch = 5,         // circular pitch (mm)
  teeth = 20,
  thickness = 8,
  shaft_diam = 5,
  $fn = 72
);

// Meshing pair (use same pitch)
spur_gear(pitch=5, teeth=20, thickness=8, shaft_diam=5);
right(pitch_radius(pitch=5, teeth=20) + pitch_radius(pitch=5, teeth=12))
  spur_gear(pitch=5, teeth=12, thickness=8, shaft_diam=3);

// Bevel gear
bevel_gear(pitch=5, teeth=20, face_width=8, shaft_diam=5);

// Rack and pinion
rack(pitch=5, teeth=20, thickness=8, height=8);
up(pitch_radius(pitch=5, teeth=12))
  spur_gear(pitch=5, teeth=12, thickness=8, shaft_diam=3);

// Worm gear pair
worm(pitch=5, d=20, l=50, shaft_diam=5);
right(20)
  worm_gear(pitch=5, teeth=30, worm_diam=20, shaft_diam=5);

// Utility: compute pitch radius
r = pitch_radius(pitch=5, teeth=20);  // returns number
```

---

## 5. Fasteners & Threads

```openscad
include <BOSL2/std.scad>
include <BOSL2/screws.scad>

// Standard screws (ISO metric)
screw("M3,10");          // M3 x 10mm, default head
screw("M3,10", head="flat");
screw("M3,10", head="pan", drive="phillips");
screw("M4,16", head="socket");

// Nuts
nut("M3");
nut("M4", shape="hex");
nut("M3", shape="square");
nut("M3", shape="nyloc");

// Screw holes (for cutting into parts)
screw_hole("M3,10");           // clearance hole
screw_hole("M3,10", drilled=true, anchor=TOP);  // countersink

// Heat-set insert hole
// (use screw_hole with slightly larger diameter)

// Custom threading
include <BOSL2/threading.scad>
threaded_rod(d=10, l=30, pitch=1.5);
threaded_nut(od=16, id=10, h=8, pitch=1.5);

// Pipe threads (NPT etc.)
```

---

## 6. Rounding, Filleting, Chamfering

```openscad
// On cuboid
cuboid([40, 30, 10], rounding=2);                // all edges
cuboid([40, 30, 10], rounding=2, edges=TOP);     // top only
cuboid([40, 30, 10], chamfer=1.5, edges=BOTTOM); // chamfer bottom

// On cylinder
cyl(h=20, d=15, rounding1=2, rounding2=1);  // different top/bottom
cyl(h=20, d=15, chamfer=1);

// Minkowski rounding (expensive but universal)
minkowski() {
  cube([38, 28, 8], center=true);
  sphere(r=1);
}

// offset_sweep — round extruded 2D profiles
include <BOSL2/skin.scad>
path = rect([30, 20]);
offset_sweep(path, h=10, bottom=[-1,1], top=[-1,1]);  // chamfer bottom, round top
```

---

## 7. Transforms & Positioning

```openscad
// BOSL2 shorthand transforms (cleaner than translate/rotate)
right(10)   cube(5);   // move +X
left(10)    cube(5);   // move -X
fwd(10)     cube(5);   // move -Y (forward)
back(10)    cube(5);   // move +Y
up(10)      cube(5);   // move +Z
down(10)    cube(5);   // move -Z

move([5, 10, 3]) cube(5);  // general

// Rotation shorthands
xrot(45)  cube(5);
yrot(45)  cube(5);
zrot(45)  cube(5);

// Mirroring and copies
xflip()   cube(5);   // mirror across YZ
yflip()   cube(5);   // mirror across XZ

// Patterned copies
xcopies(spacing=20, n=4) cylinder(h=10, d=5);  // 4 copies along X
ycopies(20, 3)            cylinder(h=10, d=5);
zcopies(15, 5)            cylinder(h=10, d=5);

// Circular copies
zrot_copies(n=6, r=25)   cylinder(h=10, d=5);  // 6 around Z at radius 25

// Grid
grid_copies(spacing=20, size=[80, 60])  cylinder(h=10, d=4);
```

---

## 8. 2D Shapes for Extrusion

```openscad
// Rounded rectangle
rect([40, 20], rounding=3);
rect([40, 20], chamfer=2);

// Teardrop 2D
teardrop2d(d=15);

// Rounded polygon
regular_ngon(n=6, d=20, rounding=2);  // hex

// Extrude 2D profiles
linear_extrude(height=10) rect([40, 20], rounding=3);

// Sweep along path
include <BOSL2/skin.scad>
path = [ [0,0,0], [50,0,0], [50,50,0] ];
profile = circle(d=8, $fn=32);
path_extrude2d(profile, path=path);
```

---

## 9. Common Includes

```openscad
include <BOSL2/std.scad>          // Always - core library
include <BOSL2/gears.scad>        // Gears
include <BOSL2/screws.scad>       // Screws and nuts
include <BOSL2/threading.scad>    // Custom threads
include <BOSL2/hinges.scad>       // Printable hinges
include <BOSL2/joiners.scad>      // Snap fits, dovetails
include <BOSL2/metric_screws.scad> // Metric screw tables
include <BOSL2/skin.scad>         // Sweeps and lofts
include <BOSL2/polyhedra.scad>    // Platonic solids etc.
```

---

## Performance Tips

- Use `$fn=32` for most cylinders; only go to 72+ for final export
- Add `--enable=manifold` to OpenSCAD CLI for 10-1000x speedup on complex BOSL2 geometry
- Use `render()` to freeze expensive sub-operations: `render() { expensive_module(); }`
- Profile with `echo(str("t=", $t));` in animations
