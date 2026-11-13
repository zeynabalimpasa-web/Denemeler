// 3D baskıya uygun Türk plakası — index.html'deki modelin OpenSCAD karşılığı
// Gerçek ölçü 520 x 110 mm; plan ölçüleri `olcek` ile küçültülür,
// kalınlıklar ise baskı için mutlak (mm) kalır.
//
// Çok renkli baskı: `parca` parametresiyle her rengi ayrı STL olarak al:
//   openscad -D 'parca="govde"' -o govde.stl plaka.scad   (beyaz)
//   openscad -D 'parca="siyah"' -o siyah.stl plaka.scad   (çerçeve + yazı)
//   openscad -D 'parca="mavi"'  -o mavi.stl  plaka.scad   (TR şeridi)
//   openscad -D 'parca="tr"'    -o tr.stl    plaka.scad   (beyaz "TR")

include <BOSL2/std.scad>

/* [Yazı] */
yazi        = "34 ABC 123";
font        = "Liberation Sans:style=Bold";

/* [Ölçek & Kalınlık] */
olcek       = 0.4;    // 0.4 → 208 x 44 mm (çoğu tablaya sığar); 1 → gerçek boy
govde_t     = 2.0;    // gövde kalınlığı (mm, ölçeklenmez)
kabartma_h  = 0.8;    // yazı/çerçeve kabartma yüksekliği (mm)
serit_h     = 0.4;    // mavi şerit yüksekliği (mm)
delik_d     = 6.5;    // vida deliği çapı, gerçek boyda (mm)

/* [Parça] */
parca       = "hepsi"; // [hepsi, govde, siyah, mavi, tr]

/* [Hidden] */
$fn = 48;
W = 520; H = 110; R = 8;            // gerçek plaka ölçüleri (mm)
cerceve_ic = 3.5; cerceve_w = 2.5; cerceve_r = 7.5;
serit_x = 4.5; serit_w = 40; serit_r = 5.5;
yazi_x0 = 52;  yazi_alan_w = 455;   // yazı alanı (soldan)
yazi_h  = 62;                       // karakter yüksekliği
kar_w   = 40;                       // karakter başına genişlik (boşluk dahil)
vida_x  = W/2 - 35;

s = olcek;
yazi_w = min(yazi_alan_w * 0.9, len(yazi) * kar_w);

// ── 2D profiller (gerçek ölçü, merkez orijinde) ─────────────────
module dis_profil()  rect([W, H], rounding=R);
module delikler()    for (sx = [-1, 1]) translate([sx * vida_x, 0]) circle(d = delik_d);

module cerceve_2d() {
    o = [W - 2*cerceve_ic, H - 2*cerceve_ic];
    difference() {
        rect(o, rounding = cerceve_r);
        rect(o - [2,2]*cerceve_w, rounding = cerceve_r - cerceve_w);
    }
}

module serit_2d() translate([-W/2 + serit_x + serit_w/2, 0])
    rect([serit_w, H - 2*serit_x], rounding = serit_r);

module tr_2d() translate([-W/2 + serit_x + serit_w/2, -H/2 + 14.5])
    text("TR", size = 20, font = font, halign = "center", valign = "baseline");

module plaka_yazi_2d() translate([-W/2 + yazi_x0 + yazi_alan_w/2, -3.5])
    resize([yazi_w, yazi_h])
        text(yazi, size = 10, font = font, halign = "center", valign = "center");

module siyah_2d() difference() { union() { cerceve_2d(); plaka_yazi_2d(); } delikler(); }
module mavi_2d()  difference() { serit_2d(); tr_2d(); cerceve_2d(); delikler(); }
module tr_ic_2d() difference() { tr_2d(); delikler(); }

// ── 3D parçalar ─────────────────────────────────────────────────
module katman(z0, h) up(z0) linear_extrude(h) scale(s) children();

module govde()  color("#fbfbf8") katman(0, govde_t) difference() { dis_profil(); delikler(); }
module siyah()  color("#111")    katman(govde_t, kabartma_h) siyah_2d();
module mavi()   color("#123a9c") katman(govde_t, serit_h) mavi_2d();
module tr_ic()  color("white")   katman(govde_t, serit_h) tr_ic_2d();

// ── Tasarım kontrolleri (FDM) ──────────────────────────────────
echo(str("Plaka boyutu: ", W*s, " x ", H*s, " x ", govde_t + kabartma_h, " mm"));
echo(str("Çerçeve çizgi genişliği: ", cerceve_w*s, " mm",
         cerceve_w*s < 0.8 ? "  ⚠ FDM için < 0.8 mm, olcek'i artır" : "  ✓"));
echo(str("Yazı yüksekliği: ", yazi_h*s, " mm, vida deliği: ", delik_d*s, " mm",
         delik_d*s < 2 ? "  ⚠ delik çok küçük" : "  ✓"));
if (W*s > 250) echo("⚠ Uzun kenar 250 mm'yi aşıyor — tablaya sığmayabilir");

// ── Ana ────────────────────────────────────────────────────────
if (parca == "hepsi" || parca == "govde") govde();
if (parca == "hepsi" || parca == "siyah") siyah();
if (parca == "hepsi" || parca == "mavi")  mavi();
if (parca == "hepsi" || parca == "tr")    tr_ic();
