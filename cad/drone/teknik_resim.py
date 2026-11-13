#!/usr/bin/env python3
"""drone.scad parçaları için A3 teknik resimler üretir (SVG + PDF + PNG).

Görünüş çizgileri OpenSCAD izdüşümlerinden (projection) alınır; ölçüler ve
toleranslar drone.scad'in yazdırdığı CIZIM{...} JSON satırından okunur, böylece
model değişince resim de güncellenir.

Kullanım:  python3 teknik_resim.py      (çıktılar: teknik_resim/)
PDF/PNG için Node + Playwright (Chromium) gerekir.
"""
import base64, json, math, os, re, subprocess, sys, tempfile, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tolerans_analizi

KOK = os.path.dirname(os.path.abspath(__file__))
SCAD = os.path.join(KOK, "drone.scad")
CIKTI = os.path.join(KOK, "teknik_resim")
TMP = tempfile.mkdtemp(prefix="tr_")
TARIH = datetime.date.today().isoformat()

# ── OpenSCAD yardımcıları ────────────────────────────────────────
def openscad(args, out):
    r = subprocess.run(["openscad", *args, "-o", out, SCAD], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(r.stderr)
    return r.stderr

def olculer():
    log = openscad(["-D", 'parca="ust"', "-D", 'gorunum="ust"'], os.path.join(TMP, "x.svg"))
    m = re.search(r'CIZIM(\{.*\})', log)
    return json.loads(m.group(1)), [l[6:].strip('"') for l in log.splitlines()
                                    if l.startswith("ECHO:") and "CIZIM" not in l]

def izdusum(parca, gorunum):
    f = os.path.join(TMP, f"{parca}_{gorunum}.svg")
    openscad(["-D", f'parca="{parca}"', "-D", f'gorunum="{gorunum}"'], f)
    return " ".join(re.findall(r'<path d="([^"]*)"', open(f).read(), re.S)).replace("\n", " ")

# ── SVG çizim katmanı (sayfa birimi: mm) ────────────────────────
KAL, INCE = 0.5, 0.25           # ISO 128: görünür kenar / ölçü çizgisi
FONT = "Liberation Sans, Arial, Helvetica, sans-serif"

def fmt(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")

class Sayfa:
    def __init__(self, baslik, no, olcek, w=420, h=297, toplam=5):
        self.w, self.h, self.e, self.defs = w, h, [], []
        self.toplam = toplam
        self.baslik, self.no, self.olcek = baslik, no, olcek
        self.clip = 0

    def add(self, s): self.e.append(s)

    def cizgi(self, a, b, w=INCE, dash=None, renk="#000"):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{a[0]:.3f}" y1="{a[1]:.3f}" x2="{b[0]:.3f}" y2="{b[1]:.3f}" '
                 f'stroke="{renk}" stroke-width="{w}"{d}/>')

    def yazi(self, p, t, size=3.5, anchor="middle", rot=0, bold=False, renk="#000"):
        tr = f' transform="rotate({rot:.2f} {p[0]:.3f} {p[1]:.3f})"' if rot else ""
        b = ' font-weight="bold"' if bold else ""
        self.add(f'<text x="{p[0]:.3f}" y="{p[1]:.3f}" font-size="{size}" font-family="{FONT}" '
                 f'text-anchor="{anchor}" fill="{renk}"{b}{tr}>{t}</text>')

    def ok(self, uc, yon):  # yon: uçtan dışarı birim vektör
        L, W = 3.0, 0.9
        n = (-yon[1], yon[0])
        b = (uc[0] + yon[0]*L, uc[1] + yon[1]*L)
        pts = [uc, (b[0]+n[0]*W/2, b[1]+n[1]*W/2), (b[0]-n[0]*W/2, b[1]-n[1]*W/2)]
        self.add('<polygon points="' + " ".join(f"{x:.3f},{y:.3f}" for x, y in pts) + '" fill="#000"/>')

    @staticmethod
    def tol_tspan(nom, tol, size):
        """'nom' + tolerans: tol=None | ('±',v) | (ust, alt) → SVG tspan'lar."""
        if tol is None:
            return nom
        ks = size * 0.68
        if tol[0] == "±":
            return f'{nom}<tspan font-size="{ks}">±{fmt(tol[1])}</tspan>'
        ust = ("+" if tol[0] > 0 else "") + fmt(tol[0])
        alt = ("+" if tol[1] > 0 else "") + fmt(tol[1]) if tol[1] else "0"
        gen = max(len(ust), len(alt)) * ks * 0.56
        return (f'{nom}<tspan font-size="{ks}" dy="{-size*0.42:.2f}">{ust}</tspan>'
                f'<tspan font-size="{ks}" dx="{-len(ust)*ks*0.56:.2f}" dy="{size*0.78:.2f}">{alt}</tspan>')

    def olcu(self, p1, p2, off, nom, tol=None, size=3.0, ic=None):
        """Hizalı ölçü: p1→p2, 'off' kadar normal yönde kaydırılmış."""
        dx, dy = p2[0]-p1[0], p2[1]-p1[1]
        L = math.hypot(dx, dy); u = (dx/L, dy/L); n = (u[1], -u[0])
        sg = 1 if off >= 0 else -1
        q1 = (p1[0]+n[0]*off, p1[1]+n[1]*off); q2 = (p2[0]+n[0]*off, p2[1]+n[1]*off)
        for p, q in ((p1, q1), (p2, q2)):
            self.cizgi((p[0]+n[0]*sg*1.0, p[1]+n[1]*sg*1.0), (q[0]+n[0]*sg*1.5, q[1]+n[1]*sg*1.5))
        ic = L > 9 if ic is None else ic
        if ic:
            self.cizgi(q1, q2); self.ok(q1, u); self.ok(q2, (-u[0], -u[1]))
        else:
            self.cizgi((q1[0]-u[0]*5, q1[1]-u[1]*5), (q2[0]+u[0]*5, q2[1]+u[1]*5))
            self.ok(q1, (-u[0], -u[1])); self.ok(q2, u)
        ang = math.degrees(math.atan2(dy, dx))
        if ang > 90.01 or ang <= -90: ang -= 180 * (1 if ang > 0 else -1)
        a = math.radians(ang); nt = (math.sin(a), -math.cos(a))   # metin "üst" yönü
        m = ((q1[0]+q2[0])/2 + nt[0]*1.2, (q1[1]+q2[1])/2 + nt[1]*1.2)
        if not ic and L < 9:   # dar ölçü: metni okların dışına taşı
            m = (q2[0] + u[0]*10 + nt[0]*1.2, q2[1] + u[1]*10 + nt[1]*1.2)
        self.add(f'<text x="{m[0]:.3f}" y="{m[1]:.3f}" font-size="{size}" font-family="{FONT}" '
                 f'text-anchor="middle" transform="rotate({ang:.2f} {m[0]:.3f} {m[1]:.3f})">'
                 f'{self.tol_tspan(nom, tol, size)}</text>')

    def kilavuz(self, p, q, metin, tol=None, size=3.0, sag=True):
        """Kılavuz (leader) çizgisi: p (özellik) → q (kırılma) → yatay omuz + metin."""
        self.cizgi(p, q)
        d = math.hypot(q[0]-p[0], q[1]-p[1]); self.ok(p, ((q[0]-p[0])/d, (q[1]-p[1])/d))
        uz = len(re.sub(r"<[^>]+>", "", metin)) * size * 0.55 + (6 if tol else 1)
        e = (q[0] + (uz if sag else -uz), q[1])
        self.cizgi(q, e)
        x = q[0] + 0.5 if sag else e[0] + 0.5
        self.add(f'<text x="{x:.3f}" y="{q[1]-1:.3f}" font-size="{size}" font-family="{FONT}">'
                 f'{self.tol_tspan(metin, tol, size)}</text>')

    def eksen(self, c, r, size=None):  # delik eksen çizgileri (ince, kesik-nokta)
        k = r + 1.5
        for a, b in (((c[0]-k, c[1]), (c[0]+k, c[1])), ((c[0], c[1]-k), (c[0], c[1]+k))):
            self.cizgi(a, b, w=0.18, dash="4 1 0.6 1")

    def gorunus(self, v, yol, etiket=None, klip=None):
        g = (f'<g transform="translate({v.ox:.3f} {v.oy:.3f}) scale({v.s})">'
             f'<path d="{yol}" fill="none" fill-rule="evenodd" stroke="#000" '
             f'stroke-width="{KAL / v.s:.4f}" stroke-linejoin="round"/></g>')
        if klip:
            self.clip += 1; cid = f"k{self.no}_{self.clip}"
            self.defs.append(f'<clipPath id="{cid}">{klip}</clipPath>')
            g = f'<g clip-path="url(#{cid})">{g}</g>'
        self.add(g)
        if etiket:
            self.yazi(etiket[0], etiket[1], size=3.5, bold=True)

    def cerceve(self, malzeme, notlar):
        w, h = self.w, self.h
        self.add(f'<rect x="20" y="10" width="{w-30}" height="{h-20}" fill="none" stroke="#000" stroke-width="0.7"/>')
        # Antet (ISO 7200 düzeni, sağ alt)
        x0, y0, bw, bh = w - 190, h - 10 - 40, 180, 40
        R = lambda x, y, ww, hh: self.add(f'<rect x="{x}" y="{y}" width="{ww}" height="{hh}" fill="#fff" stroke="#000" stroke-width="0.5"/>')
        R(x0, y0, bw, bh)
        satirlar = [y0 + 10, y0 + 20, y0 + 30]
        for y in satirlar: self.cizgi((x0, y), (x0 + bw, y), w=0.35)
        for x in (x0 + 45, x0 + 90, x0 + 135): self.cizgi((x, y0 + 20), (x, y0 + 40), w=0.35)
        self.yazi((x0 + 90, y0 + 7.2), self.baslik, size=5, bold=True)
        self.yazi((x0 + 90, y0 + 16.5), "3\" FPV Quadcopter Gövdesi — drone.scad", size=3.2)
        alanlar = [("Malzeme", malzeme), ("Ölçek", self.olcek), ("Resim no", f"DRN-{self.no:03d}"),
                   ("Sayfa", f"{self.no}/{self.toplam}"), ("Tarih", TARIH), ("Birim", "mm"),
                   ("İzdüşüm", "ISO E (1. açı)"), ("Format", "A3")]
        for i, (k, val) in enumerate(alanlar):
            cx, cy = x0 + (i % 4) * 45, y0 + 20 + (i // 4) * 10
            self.yazi((cx + 1.5, cy + 3.2), k, size=2.2, anchor="start", renk="#555")
            self.yazi((cx + 22.5, cy + 8.2), val, size=3.2)
        # Notlar (sol alt)
        if notlar:
            nx, ny = 25, h - 10 - 6 * len(notlar) - 8
            self.yazi((nx, ny), "NOTLAR", size=3.5, anchor="start", bold=True)
            for i, n in enumerate(notlar):
                self.yazi((nx, ny + 6 * (i + 1)), f"{i+1}. {n}", size=2.8, anchor="start")

    def svg(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}mm" height="{self.h}mm" '
                f'viewBox="0 0 {self.w} {self.h}"><defs>{"".join(self.defs)}</defs>'
                f'<rect width="{self.w}" height="{self.h}" fill="#fff"/>{"".join(self.e)}</svg>')

class V:
    """Görünüş yerleşimi: model (mx, my) → sayfa (ox + s·mx, oy − s·my)."""
    def __init__(self, ox, oy, s): self.ox, self.oy, self.s = ox, oy, s
    def P(self, mx, my): return (self.ox + self.s * mx, self.oy - self.s * my)
    def r(self, d): return self.s * d / 2

# ── Ortak notlar ─────────────────────────────────────────────────
def genel_notlar(D):
    return [
        f"Ölçüler mm'dir. Toleransı belirtilmeyen doğrusal ölçüler ±{fmt(D['genel_tol'])} (ISO 2768-c, FDM'e uyarlanmış).",
        f"Delikler nominal ölçüdedir (ISO 273 orta seri geçme). STL modelinde +{fmt(D['fdm_komp'])} mm FDM telafisi vardır;"
        " küçük çıkan delik matkapla düzeltilebilir.",
        "Baskı: PETG, 0.4 mm nozül, 0.25 mm katman (tüm yükseklikler katın tam katı), 4 çevre, %40 gyroid dolgu.",
        "Parça baskı tablasına çizimdeki üstten görünüşteki gibi yatırılır; destek gerekmez.",
    ]

TOL = lambda D: ("±", D["genel_tol"])
DTOL = lambda D: tuple(D["delik_tol"])
PTOL = lambda D: ("±", D["desen_tol"])
KTOL = lambda D: ("±", D["kalinlik_tol"])

# ── Sayfa 1: Alt gövde ──────────────────────────────────────────
def sayfa_alt(D):
    S = Sayfa("ALT GÖVDE (KOLLAR + FC TABLASI)", 1, "1:1 (Detay 2:1, 3:1)")
    gx, gy = D["govde"]; r = D["dingil"] / 2 / math.sqrt(2); ped = D["motor_ped_d"]
    dis = r + ped / 2
    # Ön görünüş (x, z) ve üstten görünüş (x, y) — 1:1
    on = V(112, 52, 1); ust = V(112, 145, 1)
    S.gorunus(on, izdusum("alt", "on"), ((112, 28), "ÖN GÖRÜNÜŞ"))
    S.gorunus(ust, izdusum("alt", "ust"), ((112, 216 + 14), "ÜSTTEN GÖRÜNÜŞ"))
    # Ön görünüş ölçüleri
    S.olcu(on.P(-dis, 0), on.P(-dis, D["kol_t"]), 8, fmt(D["kol_t"]), KTOL(D), ic=False)
    x7 = D["direk_desen"][0] / 2 + D["direk_ped_d"] / 2
    S.olcu(on.P(dis, 0), on.P(dis, D["arka_ped_h"]), -14, fmt(D["arka_ped_h"]), KTOL(D), ic=False)
    S.cizgi(on.P(x7, D["arka_ped_h"]), on.P(dis + 15.5, D["arka_ped_h"]))
    S.kilavuz(on.P(0, D["alt_t"]), (on.P(0, 0)[0] - 30, on.oy - 16), f"gövde t={fmt(D['alt_t'])}", KTOL(D), sag=False)
    # Üstten görünüş ölçüleri
    S.olcu(ust.P(-dis, -dis), ust.P(dis, -dis), -18, fmt(2 * dis), TOL(D))
    S.olcu(ust.P(-r, -r), ust.P(r, -r), -(dis - r) - 8, fmt(2 * r), TOL(D))
    S.olcu(ust.P(-dis, -dis), ust.P(-dis, dis), 14, fmt(2 * dis), TOL(D))
    a = math.radians(45); m = (r * 0.62, r * 0.62); n = (-math.sin(a), math.cos(a))
    k = D["kol_w"] / 2
    S.olcu(ust.P(m[0] - n[0]*k, m[1] - n[1]*k), ust.P(m[0] + n[0]*k, m[1] + n[1]*k), 0.01, fmt(D["kol_w"]), TOL(D), ic=False)
    S.kilavuz(ust.P(-r + 2.2, r + 2.2), (ust.P(-r, r)[0] - 10, 74), f"Motor eksenleri Ø{fmt(D['dingil'])} daire üzerinde (dingil)", TOL(D))
    # Detay işaretleri
    S.add(f'<circle cx="{ust.P(r, r)[0]}" cy="{ust.P(r, r)[1]}" r="{ped/2 + 3}" fill="none" stroke="#000" stroke-width="0.25" stroke-dasharray="3 1.5"/>')
    S.yazi((ust.P(r, r)[0] + 13, ust.P(r, r)[1] - 10), "A", size=4, bold=True)
    b0, b1 = ust.P(-gx/2 - 3, gy/2 + 3), ust.P(gx/2 + 3, -gy/2 - 3)
    S.add(f'<rect x="{b0[0]}" y="{b0[1]}" width="{b1[0]-b0[0]}" height="{b1[1]-b0[1]}" fill="none" stroke="#000" stroke-width="0.25" stroke-dasharray="3 1.5"/>')
    S.yazi((b0[0] - 3, b0[1] - 1), "B", size=4, bold=True)

    # Detay B — gövde merkezi, 2:1
    B = V(300, 84, 2); hw, hh = gx/2 + 3, gy/2 + 3
    k0, k1 = B.P(-hw, hh), B.P(hw, -hh)
    S.gorunus(B, izdusum("alt", "ust"), ((300, 17), "DETAY B (2:1)"),
              klip=f'<rect x="{k0[0]}" y="{k0[1]}" width="{k1[0]-k0[0]}" height="{k1[1]-k0[1]}"/>')
    S.add(f'<rect x="{k0[0]}" y="{k0[1]}" width="{k1[0]-k0[0]}" height="{k1[1]-k0[1]}" fill="none" stroke="#000" stroke-width="0.25" stroke-dasharray="3 1.5"/>')
    dx, dy = D["direk_desen"]; fc = D["fc_desen"]
    for sx in (-1, 1):
        for sy in (-1, 1):
            S.eksen(B.P(sx*dx/2, sy*dy/2), B.r(D["M3"])); S.eksen(B.P(sx*fc/2, sy*fc/2), B.r(D["M2"]))
    S.olcu(B.P(-gx/2, -gy/2), B.P(gx/2, -gy/2), -13, fmt(gx), TOL(D))
    S.olcu(B.P(-dx/2, -dy/2), B.P(dx/2, -dy/2), -15, fmt(dx), PTOL(D))
    S.olcu(B.P(gx/2, -gy/2), B.P(gx/2, gy/2), -14, fmt(gy), TOL(D))
    S.olcu(B.P(dx/2, -dy/2), B.P(dx/2, dy/2), -16, fmt(dy), PTOL(D))
    S.olcu(B.P(-fc/2, fc/2), B.P(fc/2, fc/2), 4, fmt(fc), PTOL(D))
    S.olcu(B.P(-fc/2, -fc/2), B.P(-fc/2, fc/2), 4, fmt(fc), PTOL(D))
    c = B.P(-dx/2, dy/2); q = B.r(D["M3"]) * 0.7071
    S.kilavuz((c[0]-q, c[1]-q), (c[0]-16, c[1]-12), f"4× Ø{fmt(D['M3'])}", DTOL(D), sag=False)
    c = B.P(fc/2, -fc/2); q = B.r(D["M2"]) * 0.7071
    S.kilavuz((c[0]+q, c[1]+q), (c[0]+13, c[1]+30), f"4× Ø{fmt(D['M2'])}", DTOL(D))
    c = B.P(-dx/2, -dy/2); q = B.s * D["direk_ped_d"] / 2 * 0.7071
    S.kilavuz((c[0]-q, c[1]+q), (c[0]-16, c[1]+12), f"4× Ø{fmt(D['direk_ped_d'])} ped", sag=False)
    S.yazi((300, 157.5), f"Ön pedler h={fmt(D['on_ped_h'])}, arka pedler h={fmt(D['arka_ped_h'])} ±{fmt(D['kalinlik_tol'])}", size=2.8)
    S.yazi((300, 161.5), f"FC cebi {fmt(D['fc_cep'])}×{fmt(D['fc_cep'])}, derinlik {fmt(D['alt_t'])} yüzeyine kadar", size=2.8)

    # Detay A — motor pedi, 3:1
    cA = (285, 209); rr = ped/2 + 2.5
    A2 = V(cA[0] - 3*r, cA[1] + 3*r, 3)
    S.gorunus(A2, izdusum("alt", "ust"), ((cA[0], cA[1] - 3*rr - 3), "DETAY A (3:1)"),
              klip=f'<circle cx="{cA[0]}" cy="{cA[1]}" r="{3*rr}"/>')
    S.add(f'<circle cx="{cA[0]}" cy="{cA[1]}" r="{3*rr}" fill="none" stroke="#000" stroke-width="0.25" stroke-dasharray="3 1.5"/>')
    md = D["motor_desen"]
    for sx in (-1, 1):
        for sy in (-1, 1): S.eksen(A2.P(r + sx*md/2, r + sy*md/2), A2.r(D["M2"]))
    S.eksen(A2.P(r, r), A2.r(D["mil_delik"]))
    S.olcu(A2.P(r - md/2, r + md/2), A2.P(r + md/2, r + md/2), 6, fmt(md), PTOL(D))
    S.olcu(A2.P(r + md/2, r - md/2), A2.P(r + md/2, r + md/2), -8, fmt(md), PTOL(D))
    c = A2.P(r + md/2, r - md/2); q = A2.r(D["M2"]) * 0.7071
    S.kilavuz((c[0]+q, c[1]+q), (c[0]+30, c[1]+16), f"4× Ø{fmt(D['M2'])}", DTOL(D))
    c = A2.P(r, r); q = A2.r(D["mil_delik"]) * 0.7071
    S.kilavuz((c[0]-q, c[1]+q), (cA[0]-48, c[1]+24), f"Ø{fmt(D['mil_delik'])}", DTOL(D), sag=False)
    q = A2.s * ped / 2 * 0.7071
    S.kilavuz((c[0]+q*1.0, c[1]-q), (c[0]+48, c[1]-36), f"Ø{fmt(ped)}", TOL(D))
    S.yazi((cA[0] + 45, cA[1] + 3*rr - 2), "4 motor pedi aynıdır", size=2.8, anchor="start")
    S.cerceve("PETG", genel_notlar(D))
    return S

# ── Sayfa 2: Üst plaka ───────────────────────────────────────────
def sayfa_ust(D):
    S = Sayfa("ÜST PLAKA (BATARYA PLAKASI)", 2, "2:1")
    gx, gy = D["govde"]; dx, dy = D["direk_desen"]
    on = V(150, 50, 2); u = V(150, 150, 2)
    S.gorunus(on, izdusum("ust", "on"), ((150, 32), "ÖN GÖRÜNÜŞ"))
    S.gorunus(u, izdusum("ust", "ust"), ((150, 232), "ÜSTTEN GÖRÜNÜŞ"))
    S.olcu(on.P(gx/2, 0), on.P(gx/2, D["ust_t"]), -10, fmt(D["ust_t"]), KTOL(D), ic=False)
    S.olcu(u.P(-gx/2, -gy/2), u.P(gx/2, -gy/2), -14, fmt(gx), TOL(D))
    S.olcu(u.P(-dx/2, -dy/2), u.P(dx/2, -dy/2), -16, fmt(dx), PTOL(D))
    S.olcu(u.P(gx/2, -gy/2), u.P(gx/2, gy/2), -14, fmt(gy), TOL(D))
    S.olcu(u.P(dx/2, -dy/2), u.P(dx/2, dy/2), -16, fmt(dy), PTOL(D))
    for sx in (-1, 1):
        for sy in (-1, 1): S.eksen(u.P(sx*dx/2, sy*dy/2), u.r(D["M3"]))
    c = u.P(-dx/2, dy/2); q = u.r(D["M3"]) * 0.7071
    S.kilavuz((c[0]-q, c[1]-q), (c[0]-22, c[1]-14), f"4× Ø{fmt(D['M3'])}", DTOL(D), sag=False)
    # Kayış yuvaları ve hafifletme
    S.olcu(u.P(-11, 8.5), u.P(11, 8.5), 30, "22", TOL(D))
    S.kilavuz(u.P(-11 - 1.25, -4), (u.P(-gx/2, 0)[0] - 18, u.oy + 22), "2× yuva 2.5", DTOL(D), sag=False)
    S.olcu(u.P(-gx/2, -8.5), u.P(-gx/2, 8.5), 24, "17", TOL(D))
    S.cizgi(u.P(-11, -8.5), u.P(-gx/2 - 1, -8.5), w=0.18); S.cizgi(u.P(-11, 8.5), u.P(-gx/2 - 1, 8.5), w=0.18)
    S.kilavuz(u.P(5, 6), (u.P(gx/2, 0)[0] + 30, u.oy - 40), "Hafifletme 10×24 R4")
    S.yazi((300, 70), "Batarya kayışı yuvaları 15 mm kayış içindir.", size=3, anchor="start")
    S.yazi((300, 76), f"Direk deseni ({fmt(dx)}×{fmt(dy)}) alt gövde ve kamera", size=3, anchor="start")
    S.yazi((300, 82), "tutucu ile ortak fonksiyonel ölçüdür.", size=3, anchor="start")
    S.yazi((300, 88), f"Dış köşe yarıçapı R6.", size=3, anchor="start")
    S.cerceve("PETG", genel_notlar(D))
    return S

# ── Sayfa 3: Kamera tutucu ───────────────────────────────────────
def sayfa_kamera(D):
    S = Sayfa("FPV KAMERA TUTUCU", 3, "3:1")
    bx, by = D["kamera_taban"]; t = D["kamera_taban_t"]; y0 = D["kamera_taban_y0"]
    ic = D["kamera_ic"]; dw = D["kamera_duvar"]; hw = D["duvar_h"]; vh = D["kamera_vida_h"]
    wy = D["kamera_duvar_y"]; dx = D["direk_desen"][0]; ey = D["kamera_eksen_y"]
    ky = D["kamera_kiris_y"]; rw = D["kamera_ray_w"]; y1 = wy[1]
    on = V(135, 92, 3); yan = V(330, 92, 3); u = V(135, 210, 3)
    S.gorunus(on, izdusum("kamera", "on"), ((135, 24), "ÖN GÖRÜNÜŞ"))
    S.gorunus(yan, izdusum("kamera", "yan"), ((300, 24), "SOLDAN GÖRÜNÜŞ"))
    S.gorunus(u, izdusum("kamera", "ust"), ((135, 246), "ÜSTTEN GÖRÜNÜŞ"))
    # Ön görünüşte gizli teardrop delikleri (kesikli)
    dd = D["M2"] / 2
    for sx in (-1, 1):
        x1, x2 = sorted((sx * ic/2, sx * (ic/2 + dw)))
        for z in (vh - dd, vh + dd, vh + dd * 1.414):
            S.cizgi(on.P(x1, z), on.P(x2, z), w=0.3, dash="2 1")
    S.olcu(on.P(-bx/2, 0), on.P(bx/2, 0), -10, fmt(bx), TOL(D))
    S.olcu(on.P(-ic/2, hw), on.P(ic/2, hw), 6, fmt(ic), DTOL(D))
    S.olcu(on.P(ic/2, hw), on.P(ic/2 + dw, hw), 6, fmt(dw), TOL(D), ic=False)
    S.olcu(on.P(bx/2, 0), on.P(bx/2, t), -8, fmt(t), KTOL(D), ic=False)
    S.olcu(on.P(-ic/2 - dw, 0), on.P(-ic/2 - dw, hw), 24, fmt(hw), TOL(D))
    # Soldan görünüş (mx = −y, my = z)
    for m in (0, -ey):   # direk deliği ve kamera ekseni
        S.cizgi(yan.P(m, -3), yan.P(m, (hw + 3) if m else (vh + 3)), w=0.18, dash="4 1 0.6 1")
    S.eksen(yan.P(-ey, vh), yan.r(D["M2"]))
    S.olcu(yan.P(-y1, 0), yan.P(-y1, vh), 10, fmt(vh), PTOL(D))
    c = yan.P(-ey, vh); q = yan.r(D["M2"]) * 0.7071
    S.kilavuz((c[0]+q, c[1]-q), (c[0]+30, c[1]-26), f"Ø{fmt(D['M2'])} teardrop", DTOL(D))
    S.olcu(yan.P(-y1, hw), yan.P(-wy[0], hw), 6, fmt(wy[1]-wy[0]), TOL(D))
    S.olcu(yan.P(-y1, 0), yan.P(-y0, 0), -10, fmt(by), TOL(D))
    S.olcu(yan.P(-ey, 0), yan.P(0, 0), -19, fmt(ey), PTOL(D))
    # Üstten görünüş
    for sx in (-1, 1): S.eksen(u.P(sx*dx/2, 0), u.r(D["M3"]))
    S.eksen(u.P(0, ey), 0)
    S.olcu(u.P(-dx/2, 0), u.P(dx/2, 0), -20, fmt(dx), PTOL(D))
    S.olcu(u.P(bx/2, y0), u.P(bx/2, 0), -8, fmt(-y0), PTOL(D), ic=False)
    S.olcu(u.P(bx/2, y0), u.P(bx/2, ky), -17, fmt(ky - y0), TOL(D))
    S.olcu(u.P(bx/2, 0), u.P(bx/2, ey), -26, fmt(ey), PTOL(D))
    S.olcu(u.P(bx/2, y0), u.P(bx/2, y1), -35, fmt(by), TOL(D))
    S.olcu(u.P(ic/2, y1), u.P(ic/2 + rw, y1), 6, fmt(rw), TOL(D), ic=False)
    c = u.P(-dx/2, 0); q = u.r(D["M3"]) * 0.7071
    S.kilavuz((c[0]-q, c[1]+q), (c[0]-20, c[1]+14), f"2× Ø{fmt(D['M3'])}", DTOL(D), sag=False)
    notlar = [
        f"Kamera yuvası {fmt(ic)} +{fmt(D['delik_tol'][0])}/0 ↔ kamera {fmt(D['kamera_w'])} ±{fmt(D['kamera_tol'])}",
        f"→ boşluklu geçme, boşluk {fmt(D['kam_bosluk'][0])}…{fmt(D['kam_bosluk'][1])} mm (Z3).",
        f"Kamera ekseni direk deliklerinden {fmt(ey)} mm önde ve taban",
        "U biçimlidir (kamera altı açık): kamera 0–40° eğimde",
        "tabana ve üst plakaya çarpmaz (K1, DRN-005).",
        "Yan delikler destek gerektirmeyen teardrop biçimindedir",
        "(sivri uç yukarı, 45°). Dış dikey köşeler R1.",
    ]
    for i, n in enumerate(notlar):
        S.yazi((240, 150 + 6 * i), n, size=3, anchor="start")
    S.cerceve("PETG", genel_notlar(D))
    return S

# ── Sayfa 4: Montaj + tolerans analizi + parça listesi ──────────
def sayfa_montaj(D, kontroller, Z, P, K):
    S = Sayfa("MONTAJ, PARÇA LİSTESİ, TOLERANS ANALİZİ", 4, "—")
    png = os.path.join(KOK, "cikti", "montaj.png")
    if os.path.exists(png):
        b64 = base64.b64encode(open(png, "rb").read()).decode()
        S.add(f'<image x="25" y="18" width="190" height="136" href="data:image/png;base64,{b64}" preserveAspectRatio="xMidYMid meet"/>')
        S.yazi((120, 160), "MONTAJ (izometrik, ölçeksiz — motor/pervane/batarya temsilidir)", size=3)
    def tablo(x, y, baslik, kolon, satirlar, size=2.7, sh=5.5):
        S.yazi((x, y), baslik, size=3.6, anchor="start", bold=True)
        y += 3; W = sum(kolon)
        S.add(f'<rect x="{x}" y="{y}" width="{W}" height="{sh*(len(satirlar))}" fill="none" stroke="#000" stroke-width="0.35"/>')
        for i, row in enumerate(satirlar):
            yy = y + sh * i
            if i: S.cizgi((x, yy), (x + W, yy), w=0.2)
            cx = x
            for j, cell in enumerate(row):
                S.yazi((cx + 1.2, yy + sh - 1.6), cell, size=size, anchor="start", bold=(i == 0))
                cx += kolon[j]
        cx = x
        for k in kolon[:-1]:
            cx += k; S.cizgi((cx, y), (cx, y + sh * len(satirlar)), w=0.2)
        return y + sh * len(satirlar)
    bom = [["No", "Parça", "Malzeme / Standart", "Adet"],
           ["1", "Alt gövde", "PETG baskı (DRN-001)", "1"],
           ["2", "Üst plaka", "PETG baskı (DRN-002)", "1"],
           ["3", "Kamera tutucu", "PETG baskı (DRN-003)", "1"],
           ["4", f"Direk M3×{fmt(D['direk_h'])} (dişi-dişi)", "Alüminyum, ticari", "4"],
           ["5", "Vida M3×12 (alt)", "ISO 7380, çelik (bkz. Z5)", "4"],
           ["6", "Vida M3×6 (üst)", "ISO 7380, çelik", "4"],
           ["7", "Motor vidası M2×7", "ISO 7380 (sargıya değmemeli)", "16"],
           ["8", "Kamera vidası M2×4", "Kamera ile birlikte", "2"],
           ["9", "FC montaj seti 20×20 M2", "Silikon sönümleyicili", "1"],
           ["10", "Batarya kayışı 15 mm", "Ticari", "1"]]
    yb = tablo(225, 20, "PARÇA LİSTESİ", [10, 55, 100, 15], bom)
    tol = [["Kod", "Zincir / kontrol", "Sonuç (WC veya MC)", ""]]
    for z in Z:
        r = z.sonuc
        tol.append([z.kod, z.ad, f"{r['wc'][0]:.2f} … {r['wc'][1]:.2f} mm", r["durum"]])
    tol.append([P["kod"], P["ad"], f"marj ≥ {P['wc'][0]:.2f} mm (WC)", P["durum"]])
    for k in K:
        tol.append([k["kod"], k["ad"], f"min boşluk {k['nom']:.2f} mm", k["durum"]])
    yt = tablo(225, yb + 12, "TOLERANS ANALİZİ ÖZETİ (ayrıntı: DRN-005)", [11, 92, 68, 9], tol, size=2.4, sh=4.8)
    S.yazi((225, yt + 6), "✗ işaretli satırlar eski/değiştirilen tasarımdır; parça listesi ve kamera tutucu düzeltilmiştir.", size=2.4, anchor="start")
    y = 172
    S.yazi((25, y), "TASARIM KONTROLLERİ (drone.scad çıktısı)", size=3.6, anchor="start", bold=True)
    for i, k in enumerate(kontroller):
        S.yazi((25, y + 5.5 * (i + 1)), k.replace("&", "&amp;").replace("<", "&lt;"), size=2.6, anchor="start")
    S.cerceve("—", None)
    return S

# ── PDF/PNG ──────────────────────────────────────────────────────
JS = r"""
const { chromium } = require('playwright');
(async () => {
  const [html, pdf, ...pngs] = process.argv.slice(2);
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1587, height: 1123 } });
  await p.goto('file://' + html);
  await p.pdf({ path: pdf, width: '420mm', height: '297mm', printBackground: true, margin: {top:0,right:0,bottom:0,left:0} });
  const svgs = await p.$$('svg');
  for (let i = 0; i < pngs.length; i++) await svgs[i].screenshot({ path: pngs[i] });
  await b.close();
})();
"""

def main():
    os.makedirs(CIKTI, exist_ok=True)
    D, kontroller = olculer()
    Z, P, K = tolerans_analizi.analiz(D)
    sayfalar = [sayfa_alt(D), sayfa_ust(D), sayfa_kamera(D), sayfa_montaj(D, kontroller, Z, P, K),
                tolerans_analizi.sayfa(D, Z, P, K, Sayfa, 5, 5)]
    adlar = ["DRN-001_alt_govde", "DRN-002_ust_plaka", "DRN-003_kamera_tutucu", "DRN-004_montaj_tolerans",
             "DRN-005_tolerans_analizi"]
    for s, ad in zip(sayfalar, adlar):
        open(os.path.join(CIKTI, ad + ".svg"), "w").write(s.svg())
    html = os.path.join(TMP, "resim.html")
    open(html, "w").write(
        "<!doctype html><meta charset='utf-8'><style>@page{size:420mm 297mm;margin:0}"
        "body{margin:0}svg{display:block;width:420mm;height:297mm;page-break-after:always}</style>"
        + "".join(s.svg() for s in sayfalar))
    js = os.path.join(TMP, "pdf.js"); open(js, "w").write(JS)
    pngs = [os.path.join(CIKTI, a + ".png") for a in adlar]
    r = subprocess.run(["node", js, html, os.path.join(CIKTI, "drone_teknik_resim.pdf"), *pngs],
                       capture_output=True, text=True, env={**os.environ, "NODE_PATH": subprocess.run(
                           ["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()})
    if r.returncode: print("PDF/PNG üretilemedi (Playwright gerekli):", r.stderr[-500:])
    print("Çıktılar:", CIKTI)

if __name__ == "__main__":
    main()
