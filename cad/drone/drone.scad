// 3" FPV quadcopter gövdesi — FDM baskıya uygun, parametrik (X düzeni)
//
// Parçalar (her biri düz yatırılarak basılır):
//   openscad -D 'parca="alt"'    -o alt_govde.stl drone.scad   (kollar + FC tablası)
//   openscad -D 'parca="ust"'    -o ust_plaka.stl drone.scad   (batarya plakası)
//   openscad -D 'parca="kamera"' -o kamera.stl    drone.scad   (FPV kamera tutucu)
//   parca="montaj" → motor/pervane/FC ile önizleme (baskı için değil)
//
// Malzeme önerisi: PETG veya Naylon (PLA çarpmada kırılgan).

include <BOSL2/std.scad>

/* [Genel] */
dingil_mesafesi = 150;   // çapraz motor-motor mesafesi (mm)
pervane_d       = 76.2;  // 3 inç pervane
parca           = "montaj"; // [montaj, alt, ust, kamera]

/* [Gövde] */
govde           = [36, 56];  // [en, boy] (Y = ileri)
alt_t           = 3;     // gövde plakası kalınlığı
ust_t           = 2.5;   // üst plaka kalınlığı
direk_h         = 22;    // plakalar arası direk (standoff) yüksekliği
direk_delik     = 3.2;   // M3 direk deliği
fc_desen        = 20;    // uçuş kontrolcüsü delik deseni 20x20 (M2)
fc_delik        = 2.2;

/* [Kollar & Motor] */
kol_w           = 10;    // kol genişliği
kol_t           = 5;     // kol kalınlığı (mukavemet için gövdeden kalın)
motor_ped_d     = 19;    // motor oturma pedi çapı
motor_desen     = 9;     // 1404 motor: 9x9 mm kare M2 desen
motor_delik     = 2.2;
mil_delik       = 5.5;   // motor mili / C-klips boşluğu

/* [Kamera] */
kamera_w        = 19;    // micro FPV kamera genişliği
kamera_vida_h   = 12;    // yan vida deliğinin yüksekliği
kamera_duvar    = 2;

/* [Yük & Malzeme] */
motor_itki_N    = 4.0;   // motor başına maks. itki (~400 g, 1404 + 3")
E_malzeme       = 2000;  // MPa (PETG)
akma_malzeme    = 50;    // MPa (PETG)
yogunluk        = 1.27;  // g/cm³ (PETG)

/* [Hidden] */
$fn = 40;
eps = 0.01;
r_motor  = dingil_mesafesi / 2;
motorlar = [for (a = [45, 135, 225, 315]) r_motor * [cos(a), sin(a)]];
direkler = [for (sx = [-1, 1], sy = [-1, 1]) [sx * (govde.x/2 - 5), sy * (govde.y/2 - 5)]];

// ── 2D profiller ───────────────────────────────────────────────
module govde_2d(t = 0) rect(govde + [t, t], rounding = 6);

module kol_2d(p) hull() { circle(d = kol_w); translate(p) circle(d = kol_w); }

module motor_delikleri_2d(p) translate(p) {
    circle(d = mil_delik);
    for (sx = [-1, 1], sy = [-1, 1])
        translate([sx, sy] * motor_desen / 2) circle(d = motor_delik);
}

module direk_delikleri_2d() for (d = direkler) translate(d) circle(d = direk_delik);

module fc_delikleri_2d() for (sx = [-1, 1], sy = [-1, 1])
    translate([sx, sy] * fc_desen / 2) circle(d = fc_delik);

// ── Parçalar ───────────────────────────────────────────────────
module alt_govde() difference() {
    union() {
        linear_extrude(alt_t) govde_2d();
        for (p = motorlar) linear_extrude(kol_t) {
            kol_2d(p);
            translate(p) circle(d = motor_ped_d);
        }
    }
    // Delikler (tam boy kesici: eps taşmalı)
    down(eps) linear_extrude(kol_t + 2*eps) {
        for (p = motorlar) motor_delikleri_2d(p);
        direk_delikleri_2d();
        fc_delikleri_2d();
    }
    // Kolların gövde içindeki kalın kısmını FC alanından temizle (FC düz otursun)
    up(alt_t) linear_extrude(kol_t) rect([fc_desen + 10, fc_desen + 10]);
}

module ust_plaka() linear_extrude(ust_t) difference() {
    govde_2d();
    direk_delikleri_2d();
    // Batarya kayışı yuvaları (15 mm kayış)
    for (sx = [-1, 1]) translate([sx * 11, 0]) rect([2.5, 17], rounding = 1.2);
    // Hafifletme
    rect([10, 24], rounding = 4);
}

module kamera_tutucu() {
    // Taban: arkada direk delikleri (y = 0), önde kamera duvarları
    taban_y = 18;
    ic      = kamera_w + 0.4;   // FDM boşluğu
    duvar_y = [3, 11];          // duvarların y aralığı (delik halkasından uzak)
    difference() {
        union() {
            translate([0, taban_y/2 - 4, 0])
                cuboid([govde.x - 2, taban_y, 2.5], rounding = 1, edges = "Z", anchor = BOTTOM);
            for (sx = [-1, 1]) translate([sx * (ic/2 + kamera_duvar/2), mean(duvar_y), 0])
                cuboid([kamera_duvar, duvar_y[1] - duvar_y[0], kamera_vida_h + 5],
                       rounding = 1, edges = "Z", anchor = BOTTOM);
        }
        for (sx = [-1, 1]) translate([sx * (govde.x/2 - 5), 0, -eps])
            cylinder(h = 3, d = direk_delik);
        // Yan M2 vida delikleri — yatay olduğu için destek gerektirmeyen teardrop
        translate([0, mean(duvar_y), kamera_vida_h]) zrot(90)
            teardrop(d = 2.2, l = ic + 2*kamera_duvar + 2, ang = 45);
    }
}

// ── Montaj önizlemesi ──────────────────────────────────────────
module montaj() {
    color("#3a3f47") alt_govde();
    color("#3a3f47") up(alt_t + direk_h) ust_plaka();
    color("#c0392b") translate([0, govde.y/2 - 5, alt_t]) kamera_tutucu();
    color("#999") for (d = direkler) translate([d.x, d.y, alt_t]) cylinder(h = direk_h, d = 5, $fn = 6);
    color("#1e8449") up(alt_t + 4) cuboid([27, 27, 1.6], rounding = 2, edges = "Z", anchor = BOTTOM);
    color("#222") translate([0, govde.y/2 - 5 + 7, alt_t + kamera_vida_h - kamera_w/2 + 2.5])
        cuboid([kamera_w, 18, kamera_w], anchor = BOTTOM);
    color("#ffb000", 0.85) up(alt_t + direk_h + ust_t) cuboid([30, 50, 18], rounding = 2, anchor = BOTTOM);
    for (p = motorlar) translate([p.x, p.y, kol_t]) {
        color("#666") cylinder(h = 12, d = 18);
        color("#5dade2", 0.35) up(14) cylinder(h = 1, d = pervane_d, $fn = 80);
    }
}

// ── Tasarım kontrolleri ────────────────────────────────────────
function I_rect(b, h) = b * pow(h, 3) / 12;
function deflect_cantilever_point(P, L, E, I) = P * pow(L, 3) / (3 * E * I);
function stress_cantilever(P, L, I, c) = P * L * c / I;

komsu_motor = dingil_mesafesi / sqrt(2);
pervane_bosluk = komsu_motor - pervane_d;
// Pervane ucu ile gövde köşesi arası (en yakın köşe)
kose = [govde.x/2, govde.y/2];
govde_bosluk = min([for (p = motorlar) norm([abs(p.x), abs(p.y)] - kose)]) - pervane_d/2;

// Kol: gövde kenarından motor merkezine konsol kiriş
kol_L = r_motor - min(govde.x, govde.y) / 2 / cos(45);
kol_I = I_rect(kol_w, kol_t);
sehim = deflect_cantilever_point(motor_itki_N, kol_L, E_malzeme, kol_I);
gerilme = stress_cantilever(motor_itki_N, kol_L, kol_I, kol_t / 2);

// Yaklaşık hacim → kütle (alt + üst + kamera)
hacim = govde.x * govde.y * alt_t + 4 * (r_motor * kol_w * kol_t + PI * pow(motor_ped_d/2, 2) * kol_t)
      + govde.x * govde.y * ust_t * 0.8 + 900;
kutle = hacim / 1000 * yogunluk;
ayak_izi = 2 * (r_motor * cos(45) + motor_ped_d / 2);

echo(str("Dingil: ", dingil_mesafesi, " mm, ayak izi (alt parça): ", round(ayak_izi), " x ", round(ayak_izi), " mm"));
echo(str("Komşu pervane boşluğu: ", round(pervane_bosluk*10)/10, " mm", pervane_bosluk < 3 ? "  ⚠ pervaneler çarpışabilir" : "  ✓"));
echo(str("Pervane–gövde boşluğu: ", round(govde_bosluk*10)/10, " mm", govde_bosluk < 2 ? "  ⚠ pervane gövdeye sürtebilir" : "  ✓"));
echo(str("Kol konsol boyu: ", round(kol_L), " mm, maks itkide uç sehim: ", round(sehim*100)/100, " mm",
         sehim > 1 ? "  ⚠ titreşim riski, kol_t'yi artır" : "  ✓"));
echo(str("Kol kök gerilmesi: ", round(gerilme*10)/10, " MPa (akma ", akma_malzeme, " MPa, emniyet katsayısı ",
         round(akma_malzeme / gerilme), ")", gerilme * 3 > akma_malzeme ? "  ⚠ çarpma payı düşük" : "  ✓"));
echo(str("Motor pedi et kalınlığı: ",
         round((motor_ped_d/2 - motor_desen/sqrt(2) - motor_delik/2) * 10) / 10, " mm (FDM min 1.2)"));
echo(str("Tahmini gövde kütlesi: ~", round(kutle), " g (", yogunluk, " g/cm³)"));

// ── Ana ────────────────────────────────────────────────────────
if (parca == "montaj") montaj();
if (parca == "alt")    alt_govde();
if (parca == "ust")    ust_plaka();
if (parca == "kamera") kamera_tutucu();
