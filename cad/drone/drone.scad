// 3" FPV quadcopter gövdesi — FDM baskıya uygun, parametrik (X düzeni)
//
// Parçalar (her biri düz yatırılarak basılır):
//   openscad -D 'parca="alt"'    -o alt_govde.stl drone.scad   (kollar + FC tablası)
//   openscad -D 'parca="ust"'    -o ust_plaka.stl drone.scad   (batarya plakası)
//   openscad -D 'parca="kamera"' -o kamera.stl    drone.scad   (FPV kamera tutucu)
//   parca="montaj" → motor/pervane/FC ile önizleme (baskı için değil)
//
// Teknik resim: python3 teknik_resim.py  (gorunum parametresi 2D izdüşüm verir)
// Malzeme önerisi: PETG veya Naylon (PLA çarpmada kırılgan).

include <BOSL2/std.scad>

/* [Genel] */
dingil_mesafesi = 150;   // çapraz motor-motor mesafesi (mm)
pervane_d       = 76.2;  // 3 inç pervane
parca           = "montaj"; // [montaj, alt, ust, kamera]
gorunum         = "3d";  // [3d, ust, on, yan] — teknik resim için 2D izdüşüm

/* [Gövde] */
govde           = [36, 56];  // [en, boy] (Y = ileri)
alt_t           = 3;     // gövde plakası kalınlığı
ust_t           = 2.5;   // üst plaka kalınlığı
direk_h         = 22;    // plakalar arası direk (standoff) yüksekliği, ticari
direk_ped_d     = 7;     // direk oturma pedi çapı
fc_desen        = 20;    // uçuş kontrolcüsü delik deseni 20x20 (M2)

/* [Kollar & Motor] */
kol_w           = 10;    // kol genişliği
kol_t           = 5;     // kol kalınlığı (mukavemet için gövdeden kalın)
motor_ped_d     = 19;    // motor oturma pedi çapı
motor_desen     = 9;     // 1404 motor: 9x9 mm kare M2 desen
mil_delik       = 5.5;   // motor mili / C-klips boşluğu (nominal)

/* [Kamera] */
kamera_w        = 19;    // micro FPV kamera genişliği (nominal)
kamera_vida_h   = 12;    // yan vida deliğinin yüksekliği
kamera_duvar    = 2;
kamera_taban_t  = 2.5;

/* [Tolerans] */
// Delikler nominal ölçüde (ISO 273 orta seri geçme) çizilir; FDM'de delikler
// ~0.1–0.2 mm küçük çıktığı için modele fdm_komp eklenir.
M3_gecme        = 3.4;   // ISO 273 orta: M3
M2_gecme        = 2.4;   // ISO 273 orta: M2
fdm_komp        = 0.1;   // delik/iç ölçü çap telafisi (modelde)
delik_tol       = [0.2, 0];  // delikler: +0.2 / 0
desen_tol       = 0.1;   // delik deseni / konum ±
kalinlik_tol    = 0.1;   // plaka kalınlığı ± (katman yüksekliği katı)
genel_tol       = 0.3;   // diğer doğrusal ölçüler ± (ISO 2768-c, FDM)
kamera_bosluk   = 0.2;   // kamera–duvar boşluğu (taraf başına)
kamera_tol      = 0.1;   // kamera gövde genişliği ± (üretici)
direk_tol       = 0.2;   // ticari direk boyu ±
vida_M3_max     = 3.0;   // vida dış çapı (max)
vida_M2_max     = 2.0;

/* [Yük & Malzeme] */
motor_itki_N    = 4.0;   // motor başına maks. itki (~400 g, 1404 + 3")
E_malzeme       = 2000;  // MPa (PETG)
akma_malzeme    = 50;    // MPa (PETG)
yogunluk        = 1.27;  // g/cm³ (PETG)

/* [Hidden] */
$fn = 48;
eps = 0.01;
r_motor  = dingil_mesafesi / 2;
motorlar = [for (a = [45, 135, 225, 315]) r_motor * [cos(a), sin(a)]];
direk_desen = [govde.x - 10, govde.y - 10];
direkler = [for (sx = [-1, 1], sy = [-1, 1]) [sx * direk_desen.x/2, sy * direk_desen.y/2]];
on_ped_h  = kol_t;                    // ön direkler: üstüne kamera tabanı oturur
arka_ped_h = kol_t + kamera_taban_t;  // arka direkler: aynı düzlem için yükseltilmiş
kamera_ic  = kamera_w + 2*kamera_bosluk;     // nominal kamera yuvası
duvar_h    = kamera_vida_h + 5;
fc_cep     = fc_desen + 10;

// Modellenen (telafili) çaplar
function dm(d) = d + fdm_komp;

// ── 2D profiller ───────────────────────────────────────────────
module govde_2d() rect(govde, rounding = 6);

module kol_2d(p) hull() { circle(d = kol_w); translate(p) circle(d = kol_w); }

module motor_delikleri_2d(p) translate(p) {
    circle(d = dm(mil_delik));
    for (sx = [-1, 1], sy = [-1, 1])
        translate([sx, sy] * motor_desen / 2) circle(d = dm(M2_gecme));
}

module direk_delikleri_2d() for (d = direkler) translate(d) circle(d = dm(M3_gecme));

module fc_delikleri_2d() for (sx = [-1, 1], sy = [-1, 1])
    translate([sx, sy] * fc_desen / 2) circle(d = dm(M2_gecme));

// ── Parçalar ───────────────────────────────────────────────────
module alt_govde() difference() {
    union() {
        linear_extrude(alt_t) govde_2d();
        for (p = motorlar) linear_extrude(kol_t) {
            kol_2d(p);
            translate(p) circle(d = motor_ped_d);
        }
        // Direk pedleri: tüm direkler aynı yükseklikte otursun diye
        for (d = direkler) translate(d)
            cylinder(h = d.y > 0 ? on_ped_h : arka_ped_h, d = direk_ped_d);
    }
    down(eps) linear_extrude(arka_ped_h + 2*eps) {
        for (p = motorlar) motor_delikleri_2d(p);
        direk_delikleri_2d();
        fc_delikleri_2d();
    }
    // FC cebi: kolların kalın kısmını FC alanından temizle (FC düz otursun)
    up(alt_t) linear_extrude(kol_t) rect([fc_cep, fc_cep]);
}

module ust_plaka() linear_extrude(ust_t) difference() {
    govde_2d();
    direk_delikleri_2d();
    // Batarya kayışı yuvaları (15 mm kayış)
    for (sx = [-1, 1]) translate([sx * 11, 0]) rect([2.5 + fdm_komp, 17], rounding = 1.2);
    // Hafifletme
    rect([10, 24], rounding = 4);
}

kamera_taban = [govde.x - 2, 18];
kamera_taban_y0 = -4;              // tabanın arka kenarı (delik ekseni y = 0)
kamera_duvar_y = [3, 11];

module kamera_tutucu() {
    ic = kamera_ic + fdm_komp;
    difference() {
        union() {
            translate([0, kamera_taban_y0 + kamera_taban.y/2, 0])
                cuboid([kamera_taban.x, kamera_taban.y, kamera_taban_t], rounding = 1, edges = "Z", anchor = BOTTOM);
            for (sx = [-1, 1]) translate([sx * (ic/2 + kamera_duvar/2), mean(kamera_duvar_y), 0])
                cuboid([kamera_duvar, kamera_duvar_y[1] - kamera_duvar_y[0], duvar_h],
                       rounding = 1, edges = "Z", anchor = BOTTOM);
        }
        for (sx = [-1, 1]) translate([sx * direk_desen.x/2, 0, -eps])
            cylinder(h = kamera_taban_t + 1, d = dm(M3_gecme));
        // Yan M2 vida delikleri — yatay olduğu için destek gerektirmeyen teardrop
        translate([0, mean(kamera_duvar_y), kamera_vida_h]) zrot(90)
            teardrop(d = dm(M2_gecme), l = ic + 2*kamera_duvar + 2, ang = 45);
    }
}

// ── Montaj önizlemesi ──────────────────────────────────────────
ust_z = on_ped_h + kamera_taban_t + direk_h;   // üst plakanın alt yüzü
module montaj() {
    color("#3a3f47") alt_govde();
    color("#3a3f47") up(ust_z) ust_plaka();
    color("#c0392b") translate([0, direk_desen.y/2, on_ped_h]) kamera_tutucu();
    color("#999") for (d = direkler) translate([d.x, d.y, arka_ped_h]) cylinder(h = direk_h, d = 5, $fn = 6);
    color("#1e8449") up(alt_t + 4) cuboid([27, 27, 1.6], rounding = 2, edges = "Z", anchor = BOTTOM);
    color("#222") translate([0, direk_desen.y/2 + 7, on_ped_h + kamera_vida_h - kamera_w/2 + 2.5])
        cuboid([kamera_w, 18, kamera_w], anchor = BOTTOM);
    color("#ffb000", 0.85) up(ust_z + ust_t) cuboid([30, 50, 18], rounding = 2, anchor = BOTTOM);
    for (p = motorlar) translate([p.x, p.y, kol_t]) {
        color("#666") cylinder(h = 12, d = 18);
        color("#5dade2", 0.35) up(14) cylinder(h = 1, d = pervane_d, $fn = 80);
    }
}

// ── Mühendislik fonksiyonları ──────────────────────────────────
function I_rect(b, h) = b * pow(h, 3) / 12;
function deflect_cantilever_point(P, L, E, I) = P * pow(L, 3) / (3 * E * I);
function stress_cantilever(P, L, I, c) = P * L * c / I;
function topla(v, i = 0) = i >= len(v) ? 0 : v[i] + topla(v, i + 1);
function wc_tol(t)  = topla([for (x = t) abs(x)]);
function rss_tol(t) = sqrt(topla([for (x = t) x * x]));
function r2(x) = round(x * 100) / 100;

// ── Tasarım kontrolleri ────────────────────────────────────────
komsu_motor = dingil_mesafesi / sqrt(2);
pervane_bosluk = komsu_motor - pervane_d;
kose = govde / 2;
govde_bosluk = min([for (p = motorlar) norm([abs(p.x), abs(p.y)] - kose)]) - pervane_d/2;
kol_L = r_motor - min(govde.x, govde.y) / 2 / cos(45);
kol_I = I_rect(kol_w, kol_t);
sehim = deflect_cantilever_point(motor_itki_N, kol_L, E_malzeme, kol_I);
gerilme = stress_cantilever(motor_itki_N, kol_L, kol_I, kol_t / 2);
hacim = govde.x * govde.y * alt_t + 4 * (r_motor * kol_w * kol_t + PI * pow(motor_ped_d/2, 2) * kol_t)
      + govde.x * govde.y * ust_t * 0.8 + 900;
kutle = hacim / 1000 * yogunluk;
ayak_izi = 2 * (r_motor * cos(45) + motor_ped_d / 2);

// ── Tolerans analizi ───────────────────────────────────────────
// 1) Serbest bağlantı elemanı (floating fastener): T = H_min − F_max
T_izin_M3 = M3_gecme - vida_M3_max;
T_izin_M2 = M2_gecme - vida_M2_max;
T_gercek  = 2 * sqrt(2) * desen_tol;        // ±desen_tol (x,y) → çap. konum tol.
// 2) Kamera geçmesi
kam_min = kamera_ic - (kamera_w + kamera_tol);
kam_max = kamera_ic + delik_tol[0] - (kamera_w - kamera_tol);
// 3) Kamera duvarı – üst plaka boşluğu: taban + direk − duvar
bosluk_nom = kamera_taban_t + direk_h - duvar_h;
bosluk_tol = [kalinlik_tol, direk_tol, genel_tol];
// 4) Direk oturma düzlemi farkı (ön: ped + kamera tabanı, arka: yüksek ped)
duzlem_tol = [kalinlik_tol, kalinlik_tol, kalinlik_tol];
egim = atan(wc_tol(duzlem_tol) / direk_desen.y);
// 5) Direk pedi ile kol arası mesafe (direk somunu kola çarpmasın)
kol_eksen_mesafe = min([for (d = direkler) abs(abs(d.x) - abs(d.y)) / sqrt(2)]);

echo(str("Dingil: ", dingil_mesafesi, " mm, ayak izi (alt parça): ", round(ayak_izi), " x ", round(ayak_izi), " mm"));
echo(str("Komşu pervane boşluğu: ", r2(pervane_bosluk), " mm", pervane_bosluk < 3 ? "  ⚠ pervaneler çarpışabilir" : "  ✓"));
echo(str("Pervane–gövde boşluğu: ", r2(govde_bosluk), " mm", govde_bosluk < 2 ? "  ⚠ pervane gövdeye sürtebilir" : "  ✓"));
echo(str("Kol konsol boyu: ", round(kol_L), " mm, maks itkide uç sehim: ", r2(sehim), " mm",
         sehim > 1 ? "  ⚠ titreşim riski, kol_t'yi artır" : "  ✓"));
echo(str("Kol kök gerilmesi: ", r2(gerilme), " MPa (akma ", akma_malzeme, " MPa, emniyet ",
         round(akma_malzeme / gerilme), ")", gerilme * 3 > akma_malzeme ? "  ⚠" : "  ✓"));
echo(str("Motor pedi et kalınlığı: ",
         r2(motor_ped_d/2 - motor_desen/sqrt(2) - M2_gecme/2), " mm (FDM min 1.2)"));
echo(str("Tahmini gövde kütlesi: ~", round(kutle), " g"));
echo("── Tolerans analizi ──");
echo(str("Delik hizası M3: izin verilen çap. konum tol. ", r2(T_izin_M3), " mm, desen ±", desen_tol,
         " → ", r2(T_gercek), " mm", T_gercek <= T_izin_M3 ? "  ✓" : "  ⚠ vidalar girmeyebilir"));
echo(str("Delik hizası M2: izin ", r2(T_izin_M2), " mm, gerçek ", r2(T_gercek), " mm",
         T_gercek <= T_izin_M2 ? "  ✓" : "  ⚠"));
echo(str("Kamera geçmesi: yuva ", kamera_ic, " +", delik_tol[0], "/0, kamera ", kamera_w, " ±", kamera_tol,
         " → boşluk ", r2(kam_min), "…", r2(kam_max), " mm", kam_min > 0 ? "  ✓ (boşluklu geçme)" : "  ⚠ sıkı"));
echo(str("Duvar–üst plaka boşluğu: ", r2(bosluk_nom), " mm, WC ±", r2(wc_tol(bosluk_tol)),
         ", RSS ±", r2(rss_tol(bosluk_tol)), " → min ", r2(bosluk_nom - wc_tol(bosluk_tol)), " mm",
         bosluk_nom - wc_tol(bosluk_tol) > 1 ? "  ✓" : "  ⚠"));
echo(str("Direk düzlem farkı: 0 ± ", r2(wc_tol(duzlem_tol)), " mm (WC) → üst plaka eğimi maks ",
         r2(egim), "°", egim < 1 ? "  ✓" : "  ⚠"));
echo(str("Direk ekseni–kol ekseni: ", r2(kol_eksen_mesafe), " mm (kol yarı gen. ", kol_w/2,
         ", direk ped yarıçapı ", direk_ped_d/2, ") → pedler kolla birleşik, direk somunu ped üstünde oturur"));

// Teknik resim betiği için ölçüler (JSON)
echo(str("CIZIM{",
  "\"govde\":", govde, ",\"alt_t\":", alt_t, ",\"ust_t\":", ust_t, ",\"kol_t\":", kol_t, ",\"kol_w\":", kol_w,
  ",\"dingil\":", dingil_mesafesi, ",\"motor_ped_d\":", motor_ped_d, ",\"motor_desen\":", motor_desen,
  ",\"mil_delik\":", mil_delik, ",\"M3\":", M3_gecme, ",\"M2\":", M2_gecme, ",\"fc_desen\":", fc_desen,
  ",\"fc_cep\":", fc_cep, ",\"direk_desen\":", direk_desen, ",\"direk_ped_d\":", direk_ped_d,
  ",\"on_ped_h\":", on_ped_h, ",\"arka_ped_h\":", arka_ped_h, ",\"direk_h\":", direk_h,
  ",\"kamera_taban\":", kamera_taban, ",\"kamera_taban_t\":", kamera_taban_t, ",\"kamera_taban_y0\":", kamera_taban_y0,
  ",\"kamera_duvar_y\":", kamera_duvar_y, ",\"kamera_ic\":", kamera_ic, ",\"kamera_duvar\":", kamera_duvar,
  ",\"duvar_h\":", duvar_h, ",\"kamera_vida_h\":", kamera_vida_h,
  ",\"fdm_komp\":", fdm_komp, ",\"delik_tol\":", delik_tol, ",\"desen_tol\":", desen_tol,
  ",\"kalinlik_tol\":", kalinlik_tol, ",\"genel_tol\":", genel_tol, ",\"kutle\":", round(kutle),
  ",\"kam_bosluk\":[", r2(kam_min), ",", r2(kam_max), "]",
  ",\"T_izin\":", r2(T_izin_M3), ",\"T_gercek\":", r2(T_gercek),
  ",\"duvar_bosluk\":[", r2(bosluk_nom), ",", r2(wc_tol(bosluk_tol)), ",", r2(rss_tol(bosluk_tol)), "]",
  ",\"egim\":", r2(egim), "}"));

// ── Ana ────────────────────────────────────────────────────────
module secili() {
    if (parca == "montaj") montaj();
    if (parca == "alt")    alt_govde();
    if (parca == "ust")    ust_plaka();
    if (parca == "kamera") kamera_tutucu();
}

if (gorunum == "3d")  secili();
if (gorunum == "ust") projection() secili();                       // (x, y)
if (gorunum == "on")  projection() xrot(-90) secili();             // (x, z)
if (gorunum == "yan") projection() xrot(-90) zrot(90) secili();    // (−y, z)
