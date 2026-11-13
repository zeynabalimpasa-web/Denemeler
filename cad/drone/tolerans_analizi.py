#!/usr/bin/env python3
"""Drone gövdesi — tolerans birikmesi (stack-up) analizi.

Her zincir için üç yöntem:
  WC  : en kötü durum, Σ|t_i|
  RSS : istatistiksel, √Σt_i²  (±t = ±3σ, normal dağılım)
  MC  : Monte Carlo (N örnek); ±t → N(μ, t/3), tek yönlü +a/−b → orta nokta, aralık/6
Doğrusal olmayan iki analiz yalnızca MC ile yapılır:
  P1  : 2B delik hizası (4 delik, en iyi uyum ötelemesi, delik/vida çapı rastgele)
  K1  : kamera eğim aralığında (0–40°) çarpışma boşluğu (eski ve yeni tutucu)

Ölçüler drone.scad'den okunur (CIZIM JSON). Ticari parça değerleri aşağıda
"VARSAYIMLAR" altında; üretici verisiyle güncelleyin.

Kullanım: python3 tolerans_analizi.py     (konsol raporu)
          python3 teknik_resim.py         (5. sayfa olarak A3 çizime ekler)
"""
import math
import numpy as np

N_MC = 200_000
RNG = np.random.default_rng(42)

# ── VARSAYIMLAR (ticari parçalar) ───────────────────────────────
VARSAYIM = {
    "fc_yigin": (15.0, 0.5),       # 20×20 FC+ESC yığını toplam yükseklik (sönümleyiciler dahil)
    "fc_bosluk_min": 2.0,          # üst plaka altında kablo/kondansatör payı
    "vida_L_tol_kisa": 0.29,       # ISO 4759-1 js15, L 6–10 mm
    "vida_L_tol_uzun": 0.35,       # ISO 4759-1 js15, L 10–18 mm
    "M2_dis_cap": (1.886, 1.980),  # 6g dış çap aralığı
    "M3_dis_cap": (2.874, 2.980),
    "motor_dis_derinlik": 2.5,     # 1404 motor taban dişi
    "direk_dis_derinlik": 6.0,     # 22 mm dişi-dişi direk, uç başına
    "kamera_delik_ofset": 0.2,     # kamera yan deliğinin gövde merkezine göre ±
    "kamera_derinlik": 19.0,       # kamera gövdesi (lens hariç), y yönü
    "egim_aralik": (0, 40),        # FPV kamera eğim ayarı, derece
    "egim_bosluk_min": 0.3,
}

# ── Dağılım yardımcıları ────────────────────────────────────────
def sym(nom, t):              # ±t
    return dict(nom=nom, lo=-t, hi=t)

def uni(nom, ust, alt=0.0):   # +ust / +alt (alt ≤ ust), ör. delik +0.2/0
    return dict(nom=nom, lo=alt, hi=ust)

def ornekle(k, n=N_MC):
    mu = k["nom"] + (k["lo"] + k["hi"]) / 2
    sig = (k["hi"] - k["lo"]) / 6
    return RNG.normal(mu, sig, n)

class Zincir:
    """Doğrusal tolerans zinciri: sonuç = Σ yön_i · boyut_i."""
    def __init__(self, kod, ad, birim, LSL=None, USL=None, aciklama=""):
        self.kod, self.ad, self.birim = kod, ad, birim
        self.LSL, self.USL, self.aciklama = LSL, USL, aciklama
        self.halkalar = []   # (ad, yön ±1, dağılım)

    def ekle(self, ad, yon, k):
        self.halkalar.append((ad, yon, k)); return self

    def hesapla(self):
        nom = sum(y * k["nom"] for _, y, k in self.halkalar)
        # Tek yönlü toleransları orta nokta ± yarı aralık olarak yaz
        orta = sum(y * (k["lo"] + k["hi"]) / 2 for _, y, k in self.halkalar)
        yari = [(k["hi"] - k["lo"]) / 2 for _, _, k in self.halkalar]
        merkez = nom + orta
        wc = sum(yari); rss = math.sqrt(sum(t * t for t in yari))
        x = sum(y * ornekle(k) for _, y, k in self.halkalar)
        katki = [(ad, t * t / (rss * rss) if rss else 0) for (ad, _, _), t in zip(self.halkalar, yari)]
        self.sonuc = dict(nom=nom, merkez=merkez, wc=(merkez - wc, merkez + wc),
                          rss=(merkez - rss, merkez + rss), mc=x,
                          katki=sorted(katki, key=lambda a: -a[1]))
        return self._degerlendir(x)

    def _degerlendir(self, x):
        r = self.sonuc
        mu, s = float(x.mean()), float(x.std())
        hata = np.zeros_like(x, dtype=bool)
        if self.LSL is not None: hata |= x < self.LSL
        if self.USL is not None: hata |= x > self.USL
        cpk = min([v for v in (
            (mu - self.LSL) / (3 * s) if self.LSL is not None else None,
            (self.USL - mu) / (3 * s) if self.USL is not None else None) if v is not None])
        wc_ok = (self.LSL is None or r["wc"][0] >= self.LSL) and (self.USL is None or r["wc"][1] <= self.USL)
        r.update(mu=mu, s=s, ppm=hata.mean() * 1e6, cpk=cpk, wc_ok=wc_ok,
                 durum="✓" if wc_ok else ("~" if hata.mean() < 1e-3 else "✗"))
        return r


# ── Zincirler ───────────────────────────────────────────────────
def zincirler(D):
    V = VARSAYIM
    kt, gt = D["kalinlik_tol"], D["genel_tol"]
    Z = []

    Z.append(Zincir("Z1", "FC yığını – üst plaka boşluğu", "mm", LSL=V["fc_bosluk_min"],
                    aciklama="Ön direk yolu: ped + kamera tabanı + direk − gövde − FC yığını")
             .ekle("ön ped", +1, sym(D["on_ped_h"], kt))
             .ekle("kamera tabanı", +1, sym(D["kamera_taban_t"], kt))
             .ekle("direk", +1, sym(D["direk_h"], D["direk_tol"]))
             .ekle("gövde kalınlığı", -1, sym(D["alt_t"], kt))
             .ekle("FC/ESC yığını*", -1, sym(*V["fc_yigin"])))

    Z.append(Zincir("Z2", "Üst plaka düzlemliği (ön − arka direk)", "mm", LSL=-0.8, USL=0.8,
                    aciklama="±0.8 mm ≈ 1° eğim (46 mm direk aralığında)")
             .ekle("ön ped", +1, sym(D["on_ped_h"], kt))
             .ekle("kamera tabanı", +1, sym(D["kamera_taban_t"], kt))
             .ekle("ön direk", +1, sym(D["direk_h"], D["direk_tol"]))
             .ekle("arka ped", -1, sym(D["arka_ped_h"], kt))
             .ekle("arka direk", -1, sym(D["direk_h"], D["direk_tol"])))

    Z.append(Zincir("Z3", "Kamera yuvası yan boşluğu", "mm", LSL=0.1, USL=1.0,
                    aciklama="Boşluklu geçme; vidalar sıkınca kamera sabitlenir")
             .ekle("yuva genişliği", +1, uni(D["kamera_ic"], D["delik_tol"][0], D["delik_tol"][1]))
             .ekle("kamera genişliği", -1, sym(D["kamera_w"], D["kamera_tol"])))

    Z.append(Zincir("Z4", "Motor vidası diş boyu (M2×7)", "mm", LSL=1.5, USL=V["motor_dis_derinlik"],
                    aciklama="Min 0.75·d; maks motor diş derinliği (sargıya değmemeli)")
             .ekle("vida boyu M2×7", +1, sym(7, V["vida_L_tol_kisa"]))
             .ekle("motor pedi", -1, sym(D["kol_t"], kt)))

    for L, kod, etiket in ((10, "Z5a", "mevcut"), (12, "Z5b", "öneri")):
        Z.append(Zincir(kod, f"Alt direk vidası diş boyu (M3×{L}, {etiket})", "mm",
                        LSL=3.0, USL=V["direk_dis_derinlik"],
                        aciklama="Min 1·d (alüminyum direk); maks direk diş derinliği")
                 .ekle(f"vida boyu M3×{L}", +1, sym(L, V["vida_L_tol_uzun"] if L > 10 else V["vida_L_tol_kisa"]))
                 .ekle("ön ped", -1, sym(D["on_ped_h"], kt))
                 .ekle("kamera tabanı", -1, sym(D["kamera_taban_t"], kt)))

    Z.append(Zincir("Z6", "Üst direk vidası diş boyu (M3×6)", "mm", LSL=3.0, USL=V["direk_dis_derinlik"])
             .ekle("vida boyu M3×6", +1, sym(6, V["vida_L_tol_kisa"]))
             .ekle("üst plaka", -1, sym(D["ust_t"], kt)))
    return Z


# ── P1: 2B delik hizası (Monte Carlo) ────────────────────────────
def delik_hizasi(D, n=100_000):
    """Alt gövde ↔ üst plaka direk delikleri. Her plakada 4 delik konumu ±desen_tol
    (x, y bağımsız). Üst plaka serbest olduğu için en iyi uyum ötelemesi çıkarılır.
    Şart (her delik): |Δ| ≤ (H_alt − F)/2 + (H_ust − F)/2."""
    t = D["desen_tol"]; H = D["M3"]; ht = D["delik_tol"]
    s = t / 3
    e1 = RNG.normal(0, s, (n, 4, 2)); e2 = RNG.normal(0, s, (n, 4, 2))
    d = e2 - e1
    d -= d.mean(axis=1, keepdims=True)                 # en iyi uyum ötelemesi
    sap = np.linalg.norm(d, axis=2).max(axis=1)        # en kötü delik
    k = uni(H, ht[0], ht[1])
    H1 = ornekle(k, n); H2 = ornekle(k, n)
    F = RNG.uniform(*VARSAYIM["M3_dis_cap"], n)
    izin = (H1 - F) / 2 + (H2 - F) / 2
    marj = izin - sap
    wc_sap = 2 * math.sqrt(2) * t                       # her iki plaka ters yönde, köşegen
    wc_izin = H + ht[1] - VARSAYIM["M3_dis_cap"][1]
    return dict(kod="P1", ad="Direk delik hizası (2B, M3)", mc=marj, LSL=0.0, USL=None,
                mu=float(marj.mean()), s=float(marj.std()), ppm=float((marj < 0).mean() * 1e6),
                nom=float(H - sum(VARSAYIM["M3_dis_cap"]) / 2), wc=(wc_izin - wc_sap, None),
                durum="✓" if wc_izin - wc_sap >= 0 else "✗",
                aciklama=f"Marj = izin − sapma; WC: sapma {wc_sap:.2f} ≤ izin {wc_izin:.2f}")


# ── K1: kamera eğim boşluğu (2B geometri, Monte Carlo) ───────────
def _kare_cevre(a, b, n=24):
    """Merkezli a (y) × b (z) dikdörtgen çevresi üzerinde noktalar."""
    u = np.linspace(-0.5, 0.5, n, endpoint=False)
    y = np.concatenate([u * a, np.full(n, a / 2), -u * a, np.full(n, -a / 2)])
    z = np.concatenate([np.full(n, -b / 2), u * b, np.full(n, b / 2), -u * b])
    return y, z

def _rect_mesafe(py, pz, r):
    """Noktanın dikdörtgen engele işaretli uzaklığı (içerideyse negatif)."""
    y1, y2, z1, z2 = r
    dy = np.maximum(np.maximum(y1 - py, py - y2), 0); dz = np.maximum(np.maximum(z1 - pz, pz - z2), 0)
    dis = np.hypot(dy, dz)
    ic = np.minimum.reduce([py - y1, y2 - py, pz - z1, z2 - pz])
    return np.where((dy == 0) & (dz == 0), -ic, dis)

def kamera_tasarimlari(D):
    """Kamera tutucu yerel koordinatları: y = ileri (direk delik ekseni 0),
    z = yukarı (taban alt yüzü 0). taban_y: kamera altındaki taban parçasının y aralığı."""
    return [dict(ad="Eski tutucu (eksen y=7, dolu taban)", eksen_y=7.0, taban_y=(-4.0, 14.0)),
            dict(ad=f"Yeni tutucu (eksen y={fmt(D['kamera_eksen_y'])}, U taban)", eksen_y=D["kamera_eksen_y"],
                 taban_y=(D["kamera_taban_y0"], D["kamera_kiris_y"]))]

def kamera_boslugu(D, tasarim, n=4000, aci=np.arange(0, 41, 1.0)):
    V = VARSAYIM
    kt = D["kalinlik_tol"]
    a = ornekle(sym(V["kamera_derinlik"], D["kamera_tol"]), n)
    b = ornekle(sym(D["kamera_w"], D["kamera_tol"]), n)
    tb = ornekle(sym(D["kamera_taban_t"], kt), n)
    zt = tb + ornekle(sym(D["direk_h"], D["direk_tol"]), n)        # üst plaka alt yüzü
    ez = ornekle(sym(D["kamera_vida_h"], D["desen_tol"]), n) + ornekle(sym(0, V["kamera_delik_ofset"]), n)
    ey = ornekle(sym(tasarim["eksen_y"], D["desen_tol"]), n)
    # 0. örnek = nominal (eğri için)
    a[0], b[0], tb[0] = V["kamera_derinlik"], D["kamera_w"], D["kamera_taban_t"]
    zt[0], ez[0], ey[0] = D["kamera_taban_t"] + D["direk_h"], D["kamera_vida_h"], tasarim["eksen_y"]

    BIG = 1e3; on = D["govde"][1] / 2 - D["direk_desen"][1] / 2   # plakaların ön kenarı
    one = np.ones(n); zp = -D["on_ped_h"]
    engeller = [  # (ad, y1, y2, z1[n], z2[n])
        ("üst plaka", -BIG, on, zt, zt + D["ust_t"]),
        ("gövde plakası", -BIG, on, zp * one, (zp + D["alt_t"]) * one),
        ("zemin", -BIG, BIG, -BIG * one, zp * one),
        ("taban", tasarim["taban_y"][0], tasarim["taban_y"][1], 0 * one, tb),
    ]
    uy, uz = _kare_cevre(1.0, 1.0)
    py0 = uy[None, :] * a[:, None]; pz0 = uz[None, :] * b[:, None]        # (n, m)
    egri = np.empty((n, len(aci))); hangi = []
    for j, th in enumerate(np.radians(aci)):
        c, s_ = math.cos(th), math.sin(th)
        py = ey[:, None] + py0 * c - pz0 * s_
        pz = ez[:, None] + py0 * s_ + pz0 * c
        d = np.stack([_rect_mesafe(py, pz, (y1, y2, z1[:, None], z2[:, None])).min(axis=1)
                      for _, y1, y2, z1, z2 in engeller])
        egri[:, j] = d.min(axis=0); hangi.append(engeller[int(d[:, 0].argmin())][0])
    min_bosluk = egri.min(axis=1)
    LSL = V["egim_bosluk_min"]; jk = int(egri[0].argmin())
    return dict(kod="K1", ad=tasarim["ad"], aci=aci, egri=egri[0], mc=min_bosluk, LSL=LSL, USL=None,
                mu=float(min_bosluk.mean()), s=float(min_bosluk.std()),
                ppm=float((min_bosluk < LSL).mean() * 1e6), nom=float(min_bosluk[0]),
                kritik_aci=float(aci[jk]), kritik_engel=hangi[jk],
                durum="✓" if np.quantile(min_bosluk, 0.00135) >= LSL else "✗")


def fmt(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")

def analiz(D):
    Z = zincirler(D)
    for z in Z: z.hesapla()
    P = delik_hizasi(D)
    K = [kamera_boslugu(D, t) for t in kamera_tasarimlari(D)]
    return Z, P, K


def rapor(D):
    Z, P, K = analiz(D)
    print(f"{'Kod':4} {'Zincir':44} {'Nom':>6} {'WC aralığı':>16} {'RSS aralığı':>16} {'MC μ±3σ':>16} {'Şart':>12} {'ppm':>8} {'Cpk':>5}")
    for z in Z:
        r = z.sonuc
        sart = f"{'' if z.LSL is None else fmt(z.LSL)}…{'' if z.USL is None else fmt(z.USL)}"
        print(f"{z.kod:4} {z.ad:44} {r['nom']:6.2f} {r['wc'][0]:7.2f}…{r['wc'][1]:<7.2f} "
              f"{r['rss'][0]:7.2f}…{r['rss'][1]:<7.2f} {r['mu']:6.2f}±{3*r['s']:<5.2f}    {sart:>12} "
              f"{r['ppm']:8.0f} {r['cpk']:5.2f} {r['durum']}   katkı: {r['katki'][0][0]} %{100*r['katki'][0][1]:.0f}")
    print(f"P1   {P['ad']:44} marj μ={P['mu']:.3f}, 3σ={3*P['s']:.3f}, WC marj={P['wc'][0]:.3f}, hata {P['ppm']:.0f} ppm {P['durum']}")
    for k in K:
        print(f"K1   {k['ad']:44} nominal min boşluk {k['nom']:.2f} mm @ {k['kritik_aci']:.0f}°, "
              f"({k['kritik_engel']}), MC μ={k['mu']:.2f}, hata {k['ppm']:.0f} ppm {k['durum']}")
    return Z, P, K


if __name__ == "__main__":
    import teknik_resim
    D, _ = teknik_resim.olculer()
    rapor(D)


# ── A3 sayfa (teknik_resim.Sayfa ile) ───────────────────────────
MAVI, TURUNCU, MUREKKEP, IKINCIL, IZGARA = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#d9d8d4"

def _histogram(S, x, y, w, h, veri, LSL, USL, baslik, alt_baslik):
    S.yazi((x, y - 6.5), baslik, size=2.9, anchor="start", bold=True)
    S.yazi((x, y - 2.5), alt_baslik, size=2.3, anchor="start", renk=IKINCIL)
    q = np.quantile(veri, [0.0005, 0.9995])
    lo = min([q[0]] + [v for v in (LSL, USL) if v is not None])
    hi = max([q[1]] + [v for v in (LSL, USL) if v is not None])
    pad = (hi - lo) * 0.08 or 0.1; lo -= pad; hi += pad
    sayim, kenar = np.histogram(np.clip(veri, lo, hi), bins=34, range=(lo, hi))
    X = lambda v: x + (v - lo) / (hi - lo) * w
    tepe = sayim.max()
    for c, k0, k1 in zip(sayim, kenar[:-1], kenar[1:]):
        if c == 0: continue
        bh = c / tepe * (h - 9)
        S.add(f'<rect x="{X(k0) + 0.15:.2f}" y="{y + h - bh:.2f}" width="{max(X(k1) - X(k0) - 0.3, 0.2):.2f}" '
              f'height="{bh:.2f}" rx="0.4" fill="{MAVI}"/>')
    S.cizgi((x, y + h), (x + w, y + h), w=0.25, renk=IKINCIL)
    for v, etk in ((LSL, "ALT"), (USL, "ÜST")):
        if v is None: continue
        S.cizgi((X(v), y + 1), (X(v), y + h), w=0.35, dash="1.5 1", renk=MUREKKEP)
        S.yazi((X(v), y + 0.2), f"{etk} {fmt(v)}", size=2.2, renk=MUREKKEP)
    for v in (lo + pad, hi - pad):
        S.yazi((X(v), y + h + 3.2), f"{v:.2f}", size=2.1, renk=IKINCIL)
    mu = float(np.mean(veri))
    S.yazi((x + w, y + h + 6.4), f"μ = {mu:.2f}   σ = {np.std(veri):.3f}", size=2.2, anchor="end", renk=IKINCIL)

def _egim_grafigi(S, x, y, w, h, K):
    S.yazi((x, y - 6.5), "K1 — Kamera eğim boşluğu (nominal)", size=2.9, anchor="start", bold=True)
    S.yazi((x, y - 2.5), "En yakın engele uzaklık (mm) — eğim 0–40°; negatif = çarpışma", size=2.3, anchor="start", renk=IKINCIL)
    aci = K[0]["aci"]; tum = np.concatenate([k["egri"] for k in K])
    lo, hi = min(tum.min(), 0) - 0.5, tum.max() + 0.5
    X = lambda a: x + (a - aci[0]) / (aci[-1] - aci[0]) * w
    Y = lambda v: y + h - (v - lo) / (hi - lo) * h
    for t in range(math.ceil(lo), math.floor(hi) + 1):
        S.cizgi((x, Y(t)), (x + w, Y(t)), w=0.15, renk=IZGARA)
        S.yazi((x - 1.5, Y(t) + 0.8), str(t), size=2.1, anchor="end", renk=IKINCIL)
    for a in range(0, 41, 10):
        S.yazi((X(a), y + h + 3.4), f"{a}°", size=2.1, renk=IKINCIL)
    S.cizgi((x, Y(0)), (x + w, Y(0)), w=0.3, renk=IKINCIL)
    L = VARSAYIM["egim_bosluk_min"]
    S.cizgi((x, Y(L)), (x + w, Y(L)), w=0.35, dash="1.5 1", renk=MUREKKEP)
    S.yazi((x + w - 1, Y(L) - 1), f"min boşluk {fmt(L)}", size=2.2, anchor="end", renk=MUREKKEP)
    for k, renk, etk in zip(K, (TURUNCU, MAVI), ("Eski tutucu", "Yeni tutucu")):
        pts = " ".join(f"{X(a):.2f},{Y(v):.2f}" for a, v in zip(aci, k["egri"]))
        S.add(f'<polyline points="{pts}" fill="none" stroke="#fcfcfb" stroke-width="1.6"/>')
        S.add(f'<polyline points="{pts}" fill="none" stroke="{renk}" stroke-width="0.6" stroke-linejoin="round"/>')
        S.yazi((X(aci[-1]) + 1.5, Y(k["egri"][-1]) + 0.9), etk, size=2.3, anchor="start", renk=MUREKKEP)
        j = int(np.argmin(k["egri"]))
        S.add(f'<circle cx="{X(aci[j]):.2f}" cy="{Y(k["egri"][j]):.2f}" r="0.9" fill="{renk}" stroke="#fcfcfb" stroke-width="0.4"/>')
        S.yazi((X(aci[j]), Y(k["egri"][j]) + 4), f"{k['egri'][j]:.2f} mm @ {aci[j]:.0f}° ({k['kritik_engel']})",
               size=2.1, renk=MUREKKEP)
    # lejant
    lx = x
    for renk, etk in ((TURUNCU, K[0]["ad"]), (MAVI, K[1]["ad"])):
        S.add(f'<rect x="{lx}" y="{y + h + 6.2}" width="4" height="1.2" rx="0.4" fill="{renk}"/>')
        S.yazi((lx + 5.5, y + h + 7.4), etk, size=2.2, anchor="start", renk=MUREKKEP)
        lx += 92

def sayfa(D, Z, P, K, Sayfa, no, toplam):
    S = Sayfa("TOLERANS BİRİKMESİ ANALİZİ", no, "—", toplam=toplam)
    # Özet tablo
    kolon = [11, 74, 14, 25, 25, 25, 18, 15, 11, 22]
    bas = ["Kod", "Zincir", "Nom.", "WC aralığı", "RSS aralığı", "MC μ ± 3σ", "Şart", "ppm", "Cpk", "Sonuç"]
    sonuc_y = {"✓": "✓ uygun", "~": "~ sınırda", "✗": "✗ uygun değil"}
    satir = [bas]
    for z in Z:
        r = z.sonuc
        sart = f"{'' if z.LSL is None else fmt(z.LSL)} … {'' if z.USL is None else fmt(z.USL)}"
        satir.append([z.kod, z.ad, f"{r['nom']:.2f}", f"{r['wc'][0]:.2f} … {r['wc'][1]:.2f}",
                      f"{r['rss'][0]:.2f} … {r['rss'][1]:.2f}", f"{r['mu']:.2f} ± {3*r['s']:.2f}",
                      sart, f"{r['ppm']:.0f}", f"{r['cpk']:.2f}", sonuc_y[r["durum"]]])
    satir.append([P["kod"], P["ad"] + " — marj", f"{P['nom']:.2f}", f"min {P['wc'][0]:.2f}", "—",
                  f"{P['mu']:.2f} ± {3*P['s']:.2f}", "≥ 0", f"{P['ppm']:.0f}", "—", sonuc_y[P["durum"]]])
    for k in K:
        satir.append([k["kod"], k["ad"] + " — min boşluk", f"{k['nom']:.2f}", "—", "—",
                      f"{k['mu']:.2f} ± {3*k['s']:.2f}", f"≥ {fmt(k['LSL'])}", f"{k['ppm']:.0f}", "—", sonuc_y[k["durum"]]])
    x0, y0, sh = 25, 22, 5.0
    S.yazi((x0, y0 - 3), "ÖZET (birim mm; WC = en kötü durum, RSS = √Σt², MC = 200 000 örnek Monte Carlo)", size=3.2, anchor="start", bold=True)
    W = sum(kolon)
    S.add(f'<rect x="{x0}" y="{y0}" width="{W}" height="{sh*len(satir)}" fill="none" stroke="#000" stroke-width="0.35"/>')
    for i, row in enumerate(satir):
        yy = y0 + sh * i
        if i: S.cizgi((x0, yy), (x0 + W, yy), w=0.15)
        cx = x0
        for j, c in enumerate(row):
            S.yazi((cx + 1, yy + sh - 1.5), c, size=2.3, anchor="start", bold=(i == 0 or (j == 9 and "değil" in c)))
            cx += kolon[j]
    cx = x0
    for k in kolon[:-1]:
        cx += k; S.cizgi((cx, y0), (cx, y0 + sh * len(satir)), w=0.15)
    # Bulgular
    bx = x0 + W + 6
    S.yazi((bx, y0 - 3), "BULGULAR VE ÖNERİLER", size=3.2, anchor="start", bold=True)
    z5a = next(z for z in Z if z.kod == "Z5a").sonuc; z5b = next(z for z in Z if z.kod == "Z5b").sonuc
    eski, yeni = K
    bul = [
        "1. Alt direk vidası M3×10: diş boyu",
        f"   {z5a['wc'][0]:.2f}…{z5a['wc'][1]:.2f} mm < 3 mm (1·d) → UYGUN DEĞİL.",
        f"   M3×12 ile {z5b['wc'][0]:.2f}…{z5b['wc'][1]:.2f} mm → parça listesi güncellendi.",
        "2. Eski kamera tutucu: kamera tabana",
        f"   çarpıyor ({eski['nom']:.2f} mm @ {eski['kritik_aci']:.0f}°). Yeni tutucuda",
        f"   eksen {fmt(D['kamera_eksen_y'])} mm öne alındı, taban U yapıldı:",
        f"   0–40° boyunca min {yeni['nom']:.2f} mm boşluk.",
        "3. Z1 değişiminin %{:.0f}'i FC/ESC yığınından;".format(100 * Z[0].sonuc['katki'][0][1]),
        "   gövde toleransları kritik değil.",
        "4. Z4 (motor vidası) en dar marjlı zincir:",
        "   vida boyu payın %{:.0f}'i. Pul eklemeyin;".format(100 * Z[3].sonuc['katki'][0][1]),
        "   M2×8 kullanılırsa motor sargısına değer.",
    ]
    for i, t in enumerate(bul):
        S.yazi((bx, y0 + 3.5 + 4.2 * i), t, size=2.4, anchor="start")
    # Histogramlar
    ogeler = [(z.sonuc["mc"], z.LSL, z.USL, f"{z.kod} — {z.ad}",
               f"en büyük katkı: {z.sonuc['katki'][0][0]} (%{100*z.sonuc['katki'][0][1]:.0f})") for z in Z]
    ogeler.append((P["mc"], 0.0, None, f"P1 — {P['ad']}", "marj = izin verilen − gerçek sapma (en kötü delik)"))
    gw, gh = 88, 32
    for i, (v, l, u, b, a) in enumerate(ogeler):
        gx = 27 + (i % 4) * (gw + 8.5); gy = 104 + (i // 4) * (gh + 22)
        _histogram(S, gx, gy, gw, gh, v, l, u, b, a)
    # Eğim grafiği
    _egim_grafigi(S, 34, 222, 168, 44, K)
    # Varsayımlar
    vx, vy = 222, 218
    S.yazi((vx, vy), "VARSAYIMLAR (ticari parçalar)", size=3.0, anchor="start", bold=True)
    V = VARSAYIM
    var = [f"FC/ESC yığını {fmt(V['fc_yigin'][0])} ±{fmt(V['fc_yigin'][1])}; vida boyu ISO 4759-1 js15",
           f"Motor diş derinliği {fmt(V['motor_dis_derinlik'])}; direk diş derinliği {fmt(V['direk_dis_derinlik'])}",
           f"Kamera 19×19×{fmt(V['kamera_derinlik'])} (lens hariç), delik ofseti ±{fmt(V['kamera_delik_ofset'])}",
           "Dağılım: ±t = ±3σ normal; tek yönlü tol. orta nokta",
           "* üretici verisiyle doğrulanmalı"]
    for i, t in enumerate(var):
        S.yazi((vx, vy + 4.5 * (i + 1)), t, size=2.3, anchor="start")
    S.cerceve("—", None)
    return S
