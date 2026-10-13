#!/usr/bin/env python3
"""Oracle FORT / MOYEN des fleches de l'original + features par bougie de fleche.

Idee de Jeremy (12/10) : nos fleches Signator V9 reproduisent celles de
l'original a 100 %. L'original etiquette chacune FORT ou MOYEN. Le probleme se
reduit donc a une CLASSIFICATION BINAIRE sur un ensemble de fleches connu, sans
aucune question de seuil de declenchement.

Ce script :
  1. extrait l'oracle = toutes les fleches de l'original avec leur etiquette ;
  2. calcule sur la bougie de chaque fleche toutes les grandeurs calculables ;
  3. ecrit un CSV plat (une ligne par fleche) pour la recherche de separateur.

PIEGES respectes :
  - les colonnes `Signal Long/Short Fort|Moyen` apparaissent en 4 GROUPES
    (versions differentes de l'indicateur). Groupes 1 et 3 vides, groupe 2 =
    groupe 4 avec filtre d'annonces, groupe 4 = version la plus recente.
    On extrait les deux et on les tague.
  - les colonnes `Signator ...` sont les NOTRES : jamais utilisees ici.
  - les drapeaux sont des 0/1 numeriques sur TOUTES les lignes : on teste
    float(x) != 0.

Sortie : oracle_fort_moyen.csv dans le meme dossier.
"""
import csv, glob, math, os, re, sys
from datetime import datetime

AJUST = os.path.expanduser("~/Ephore/Base 10:10/Ajustements")
LUN = os.path.expanduser("~/Ephore/Lun12:10")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oracle_fort_moyen.csv")
WARMUP = 120


# ---- semantique Pine (copiee de sig_api.py / signator_sim.py) ---------------
def ema(x, p):
    a = 2 / (p + 1); out = [x[0]]
    for v in x[1:]:
        out.append(a * v + (1 - a) * out[-1])
    return out


def rma(x, p):
    out = [None] * len(x); s = None; buf = []
    for i, v in enumerate(x):
        if v is None:
            continue
        if s is None:
            buf.append(v)
            if len(buf) == p:
                s = sum(buf) / p
        else:
            s = (s * (p - 1) + v) / p
        out[i] = s
    return out


def sma_n(x, p):
    return [sum(x[i - p + 1:i + 1]) / p if i >= p - 1 else None for i in range(len(x))]


def stdev_n(x, p):
    out = [None] * len(x)
    for i in range(p - 1, len(x)):
        w = x[i - p + 1:i + 1]; m = sum(w) / p
        out[i] = math.sqrt(sum((v - m) ** 2 for v in w) / p)
    return out


# ---- lecture ----------------------------------------------------------------
def groups_of(hdr):
    """Renvoie la liste des index de debut de chaque groupe de 4 colonnes
    `Signal Long Fort, Signal Short Fort, Signal Long Moyen, Signal Short Moyen`."""
    out = []
    for i, n in enumerate(hdr):
        if n.strip() == "Signal Long Fort":
            if (i + 3 < len(hdr) and hdr[i + 1].strip() == "Signal Short Fort"
                    and hdr[i + 2].strip() == "Signal Long Moyen"
                    and hdr[i + 3].strip() == "Signal Short Moyen"):
                out.append(i)
    return out


def load(path):
    rows = list(csv.reader(open(path, newline="")))
    hdr = rows[0]
    data = [r for r in rows[1:] if r and r[0]]
    g = groups_of(hdr)
    if len(g) < 2:
        return None
    first = {}
    for i, n in enumerate(hdr):
        first.setdefault(n.strip(), i)
    ivol = first.get("Volume")

    def col(name):
        # Moyenator 1/2 : on prend la PREMIERE occurrence (toutes identiques)
        return first.get(name)
    im1, im2 = col("Moyenator 1"), col("Moyenator 2")

    d = {k: [] for k in ("t", "o", "h", "l", "c", "v", "m1", "m2")}
    flags = {gi: {k: [] for k in ("LF", "SF", "LM", "SM")} for gi in range(len(g))}
    for r in data:
        def num(i, dflt=float("nan")):
            if i is None:
                return dflt
            try:
                return float(r[i])
            except (ValueError, IndexError):
                return dflt
        d["t"].append(datetime.fromisoformat(r[0]))
        d["o"].append(num(1, 0.0)); d["h"].append(num(2, 0.0))
        d["l"].append(num(3, 0.0)); d["c"].append(num(4, 0.0))
        d["v"].append(num(ivol, float("nan")))
        d["m1"].append(num(im1)); d["m2"].append(num(im2))
        for gi, base in enumerate(g):
            for k, off in (("LF", 0), ("SF", 1), ("LM", 2), ("SM", 3)):
                x = num(base + off, 0.0)
                flags[gi][k].append(bool(x) and x == x and float(x) != 0)
    d["flags"] = flags
    d["ngroups"] = len(g)
    d["has_vol"] = ivol is not None and any(v == v for v in d["v"]) and any(
        v == v and v > 0 for v in d["v"])
    return d


def tf_minutes(ts):
    from collections import Counter
    c = Counter(int((ts[i + 1] - ts[i]).total_seconds())
                for i in range(min(len(ts) - 1, 300)))
    return c.most_common(1)[0][0] // 60 if c else 15


def sym_tf(path):
    b = os.path.basename(path)
    sym = "MES" if "MES" in b else ("NQ" if "NQ" in b else "?")
    m = re.search(r",\s*([0-9A-Za-z]+)_", b)
    return sym, (m.group(1) if m else "?")


# ---- features ---------------------------------------------------------------
def features(d):
    """Toutes les grandeurs calculables, sur bougies HA (o/h/l/c du CSV)."""
    N = len(d["c"])
    O, H, L, C, V = d["o"], d["h"], d["l"], d["c"], d["v"]
    hasv = d["has_vol"]
    o4 = [(O[i] + H[i] + L[i] + C[i]) / 4 for i in range(N)]
    e4, e32 = ema(o4, 4), ema(o4, 32)
    bull = [a > b for a, b in zip(e4, e32)]
    run = [1] * N
    for i in range(1, N):
        run[i] = run[i - 1] + 1 if bull[i] == bull[i - 1] else 1

    tr = [H[0] - L[0]] + [max(H[i] - L[i], abs(H[i] - C[i - 1]), abs(L[i] - C[i - 1]))
                          for i in range(1, N)]
    up = [0.0] + [max(H[i] - H[i - 1], 0) if H[i] - H[i - 1] > L[i - 1] - L[i] else 0.0
                  for i in range(1, N)]
    dn = [0.0] + [max(L[i - 1] - L[i], 0) if L[i - 1] - L[i] > H[i] - H[i - 1] else 0.0
                  for i in range(1, N)]
    atr = rma(tr, 14); pu = rma(up, 14); pdn = rma(dn, 14)
    dip = [None if pu[i] is None or not atr[i] else 100 * pu[i] / atr[i] for i in range(N)]
    dim = [None if pdn[i] is None or not atr[i] else 100 * pdn[i] / atr[i] for i in range(N)]
    dx = [None if pu[i] is None else
          (abs(pu[i] - pdn[i]) / (pu[i] + pdn[i]) * 100 if pu[i] + pdn[i] > 0 else 0.0)
          for i in range(N)]
    adx = rma(dx, 14)

    # EMA50/60 : colonnes Moyenator de l'original si dispo (pas de chauffe)
    m1ok = sum(1 for v in d["m1"] if v == v and v) > N * 0.9
    if m1ok:
        e50 = [v if v == v and v else None for v in d["m1"]]
        e60 = [v if v == v and v else None for v in d["m2"]]
    else:
        e50, e60 = ema(C, 50), ema(C, 60)

    sma20c = sma_n(C, 20); sd20 = stdev_n(C, 20)
    vma = sma_n([0.0 if v != v else v for v in V], 20) if hasv else [None] * N

    # RSI(14) sur close HA
    gain = [0.0] + [max(C[i] - C[i - 1], 0) for i in range(1, N)]
    loss = [0.0] + [max(C[i - 1] - C[i], 0) for i in range(1, N)]
    rg, rl = rma(gain, 14), rma(loss, 14)
    rsi = [None if rg[i] is None else
           (100.0 if not rl[i] else 100 - 100 / (1 + rg[i] / rl[i])) for i in range(N)]

    # CCI(20) sur hlc3 HA
    tp = [(H[i] + L[i] + C[i]) / 3 for i in range(N)]
    stp = sma_n(tp, 20)
    cci = [None] * N
    for i in range(19, N):
        md = sum(abs(tp[j] - stp[i]) for j in range(i - 19, i + 1)) / 20
        cci[i] = (tp[i] - stp[i]) / (0.015 * md) if md else 0.0

    F = []
    for i in range(N):
        rng = max(H[i] - L[i], 1e-12)
        b = bull[i]
        br = abs(C[i] - O[i]) / rng
        cpos = (C[i] - L[i]) / rng if b else (H[i] - C[i]) / rng
        awick = (H[i] - C[i]) / rng if b else (C[i] - L[i]) / rng
        a = atr[i] or 1e-12
        # --- 5 termes continus du CQF (MEMOIRE §5) ---
        s_str = (min(br / 0.5, 1.0) + (1.0 - min(awick / 0.35, 1.0))
                 + min(cpos / 0.67, 1.0)) / 3.0
        s_mom = min((H[i] - L[i]) / max(0.5 * a, 1e-12), 1.0)
        s_vol = (min(V[i] / vma[i], 1.0) if (hasv and vma[i]) else None)
        s_gap = min(abs(O[i] - C[i - 1]) / max(0.3 * a, 1e-12), 1.0) if i else 0.0
        eng = (((C[i] > O[i - 1] and O[i] < C[i - 1]) if b
                else (O[i] > C[i - 1] and C[i] < O[i - 1]))
               and H[i] > H[i - 1] and L[i] < L[i - 1]) if i else False
        s_eng = 1.0 if eng else 0.0
        sv = s_vol if s_vol is not None else 0.0
        score5 = (s_str + s_mom + sv + s_gap + s_eng) / 5.0 * 100.0
        score4 = (s_str + s_mom + sv + s_gap) / 4.0 * 100.0
        score3 = (s_str + s_mom + s_gap) / 3.0 * 100.0  # sans volume ni engulf
        dband = (((C[i] - max(e50[i], e60[i])) if b else (min(e50[i], e60[i]) - C[i])) / a
                 if (e50[i] is not None and e60[i] is not None) else None)
        d50 = ((C[i] - e50[i]) / a * (1 if b else -1)) if e50[i] is not None else None
        bbw = (4 * sd20[i] / sma20c[i] * 100) if (sd20[i] and sma20c[i]) else None
        bbpos = ((C[i] - (sma20c[i] - 2 * sd20[i])) / (4 * sd20[i])
                 if (sd20[i] and sd20[i] > 0) else None)
        F.append(dict(
            bull=b, run=run[i],
            s_str=s_str, s_mom=s_mom, s_vol=s_vol, s_gap=s_gap, s_eng=s_eng,
            score5=score5, score4=score4, score3=score3,
            adx=adx[i], dip=dip[i], dim=dim[i],
            dirdi=(dip[i] - dim[i]) * (1 if b else -1) if dip[i] is not None else None,
            rsi=rsi[i], rsidir=(rsi[i] - 50) * (1 if b else -1) if rsi[i] is not None else None,
            cci=cci[i], ccidir=cci[i] * (1 if b else -1) if cci[i] is not None else None,
            atr=atr[i], rng_atr=(H[i] - L[i]) / a, body_rng=br, cpos=cpos, awick=awick,
            body_atr=abs(C[i] - O[i]) / a,
            vol_sma=(V[i] / vma[i] if (hasv and vma[i]) else None),
            dband=dband, d50=d50, bbw=bbw, bbpos=bbpos,
            gap_atr=(abs(O[i] - C[i - 1]) / a if i else 0.0),
        ))
    return F


# ---- extraction -------------------------------------------------------------
FIELDS = ["src", "sym", "tf", "time", "grp", "sens", "label",
          "bull", "run", "s_str", "s_mom", "s_vol", "s_gap", "s_eng",
          "score5", "score4", "score3", "adx", "dip", "dim", "dirdi",
          "rsi", "rsidir", "cci", "ccidir", "atr", "rng_atr", "body_rng",
          "cpos", "awick", "body_atr", "vol_sma", "dband", "d50", "bbw",
          "bbpos", "gap_atr", "has_vol"]


def run_dir(root, tag, rows, stats):
    for path in sorted(glob.glob(os.path.join(root, "*.csv"))):
        d = load(path)
        if d is None:
            continue
        sym, tf = sym_tf(path)
        F = features(d)
        ng = d["ngroups"]
        # groupe le plus recent = DERNIER groupe non vide ; groupe filtre = avant-dernier
        nonempty = [gi for gi in range(ng) if any(
            d["flags"][gi][k][i] for k in ("LF", "SF", "LM", "SM")
            for i in range(len(d["t"])))]
        if not nonempty:
            continue
        g_last = nonempty[-1]
        g_filt = nonempty[-2] if len(nonempty) > 1 else None
        for gi, gname in ((g_last, "g4"), (g_filt, "g2")):
            if gi is None:
                continue
            fl = d["flags"][gi]
            for i in range(len(d["t"])):
                lf, sf, lm, sm = fl["LF"][i], fl["SF"][i], fl["LM"][i], fl["SM"][i]
                if not (lf or sf or lm or sm):
                    continue
                label = "FORT" if (lf or sf) else "MOYEN"
                sens = "long" if (lf or lm) else "short"
                r = dict(F[i])
                r.update(src=tag, sym=sym, tf=tf, time=d["t"][i].isoformat(),
                         grp=gname, sens=sens, label=label,
                         has_vol=int(d["has_vol"]))
                rows.append(r)
                if gname == "g4":
                    stats.setdefault((tag, sym, tf), {"FORT": 0, "MOYEN": 0})
                    stats[(tag, sym, tf)][label] += 1


def main():
    rows, stats = [], {}
    run_dir(AJUST, "ajust", rows, stats)
    run_dir(LUN, "lun", rows, stats)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"ecrit : {OUT}  ({len(rows)} lignes, 2 groupes confondus)\n")
    print(f"{'lot':<7}{'sym':<5}{'tf':>5}{'FORT':>7}{'MOYEN':>7}")
    tot = {"FORT": 0, "MOYEN": 0}
    for k in sorted(stats, key=lambda x: (x[0], x[1], len(x[2]), x[2])):
        s = stats[k]
        print(f"{k[0]:<7}{k[1]:<5}{k[2]:>5}{s['FORT']:>7}{s['MOYEN']:>7}")
        tot["FORT"] += s["FORT"]; tot["MOYEN"] += s["MOYEN"]
    print(f"{'TOTAL groupe 4':<17}{tot['FORT']:>7}{tot['MOYEN']:>7}")
    g2 = [r for r in rows if r["grp"] == "g2"]
    print(f"groupe 2 (filtre) : {sum(1 for r in g2 if r['label']=='FORT')} FORT / "
          f"{sum(1 for r in g2 if r['label']=='MOYEN')} MOYEN")


if __name__ == "__main__":
    main()
