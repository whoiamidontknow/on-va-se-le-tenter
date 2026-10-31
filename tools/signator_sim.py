#!/usr/bin/env python3
"""Simulateur de la regle SIGNATOR V8 (TABLEAU.pine, lignes 285-395).

Reconstruit depuis le Pine le 2026-10-10 : les scripts d'origine
(signator_final/final_v8.py, grid_v8.py, signator_v9/NOTES.md) vivaient dans un
scratchpad /tmp et ont ete perdus. Ne plus jamais laisser ce code hors du depot.

Regle V8 :
  Heishinator = ema(ohlc4,4) > ema(ohlc4,32)          [sur bougies HA]
  fleche      = 2e bougie du nouvel etat Heishinator
                + ADX(14,14) >= 18
                + cloture du bon cote de l'EMA50
                + conviction : (cloture a >= 0.3 ATR au-dela de la bande
                  EMA50/EMA60) OU (volume >= SMA20)
                + si filtre actif : pas de fleche sur une bougie contenant
                  14:30 ou 16:00 (Paris)
  Score (CQF) = moyenne de 5 filtres continus x 100 ; engulfing = 0 en HA,
                donc plafond 80.  Fort >= 50, Moyen >= 18, Faible en dessous.

Attendu (MEMOIRE_PROJET.md §5) :
  Singal  (filtre decoche) : 112/113 exactes, 5 en trop
  Filtres (filtre coche)   :  65/65  exactes, 5 en trop

Usage :
  python3 tools/signator_sim.py ~/ERGON/Singal            # filtre OFF
  python3 tools/signator_sim.py --filtre ~/ERGON/Filtres  # filtre ON
"""
import csv, glob, os, sys
from datetime import datetime

ADX_MIN, SCORE_FORT, SCORE_MOYEN, WARMUP = 18.0, 50.0, 18.0, 120
NEWS_HHMM = (("14", "30"), ("16", "00"))


# ---- semantique Pine (reprise de tools/ephore_api/sig_api.py) ----------------
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


# ---- lecture CSV -------------------------------------------------------------
def load(path):
    """Renvoie les colonnes utiles. Les en-tetes sont dupliques dans les exports
    TradingView : on garde la DERNIERE occurrence (cf. MEMOIRE_PROJET.md §7)."""
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    hdr, data = rows[0], [r for r in rows[1:] if r and r[0]]
    idx = {}
    for i, name in enumerate(hdr):
        idx[name.strip()] = i          # derniere occurrence gagne
    need = ("Signal Long Fort", "Signal Short Fort",
            "Signal Long Moyen", "Signal Short Moyen")
    if not all(k in idx for k in need):
        return None
    has_vol = "Volume" in idx
    out = {k: [] for k in ("t", "o", "h", "l", "c", "v", "oL", "oS", "oLM", "oSM",
                           "m1", "m2")}
    for r in data:
        def num(i, d=0.0):
            try: return float(r[i])
            except (ValueError, IndexError): return d
        out["t"].append(datetime.fromisoformat(r[0]))
        out["o"].append(num(1)); out["h"].append(num(2))
        out["l"].append(num(3)); out["c"].append(num(4))
        out["v"].append(num(idx["Volume"]) if has_vol else 0.0)
        # Moyenator 1/2 de l'original = EMA50/EMA60 EXACTES : evite toute chauffe
        # d'EMA de notre cote (MEMOIRE_PROJET.md §4.4).
        out["m1"].append(num(idx["Moyenator 1"], float("nan")) if "Moyenator 1" in idx else float("nan"))
        out["m2"].append(num(idx["Moyenator 2"], float("nan")) if "Moyenator 2" in idx else float("nan"))
        # Les colonnes de fleches sont des drapeaux 0/1 presents sur CHAQUE ligne :
        # il faut tester la valeur, pas la presence de la chaine. Les en-tetes sont
        # dupliques et seul le DERNIER groupe porte les donnees (le premier est a 0).
        def flag(k):
            try: return float(r[idx[k]]) != 0
            except (ValueError, IndexError): return False
        out["oL"].append(flag("Signal Long Fort"))
        out["oS"].append(flag("Signal Short Fort"))
        out["oLM"].append(flag("Signal Long Moyen"))
        out["oSM"].append(flag("Signal Short Moyen"))
    out["has_vol"] = has_vol
    return out


def tf_seconds(ts):
    from collections import Counter
    d = Counter(int((ts[i + 1] - ts[i]).total_seconds()) for i in range(min(len(ts) - 1, 200)))
    return d.most_common(1)[0][0] if d else 900


# ---- la regle ---------------------------------------------------------------
def simulate(d, use_filter):
    N = len(d["c"])
    O, H, L, C, V, T = d["o"], d["h"], d["l"], d["c"], d["v"], d["t"]
    tf = tf_seconds(T)

    o4 = [(O[i] + H[i] + L[i] + C[i]) / 4 for i in range(N)]
    bull = [a > b for a, b in zip(ema(o4, 4), ema(o4, 32))]

    run = [1] * N
    for i in range(1, N):
        run[i] = run[i - 1] + 1 if bull[i] == bull[i - 1] else 1

    tr = [H[0] - L[0]] + [max(H[i] - L[i], abs(H[i] - C[i - 1]), abs(L[i] - C[i - 1]))
                          for i in range(1, N)]
    up = [0] + [max(H[i] - H[i - 1], 0) if H[i] - H[i - 1] > L[i - 1] - L[i] else 0
                for i in range(1, N)]
    dn = [0] + [max(L[i - 1] - L[i], 0) if L[i - 1] - L[i] > H[i] - H[i - 1] else 0
                for i in range(1, N)]
    atr, pu, pd = rma(tr, 14), rma(up, 14), rma(dn, 14)
    dx = [None if pu[i] is None else
          (abs(pu[i] - pd[i]) / (pu[i] + pd[i]) * 100 if pu[i] + pd[i] > 0 else 0)
          for i in range(N)]
    adx = rma(dx, 14)
    # EMA50/60 : on prefere les colonnes Moyenator de l'original quand elles sont
    # presentes et non nulles ; sinon on les recalcule (et il faut alors chauffer).
    import math as _m
    m1, m2 = d.get("m1") or [], d.get("m2") or []
    ok = (len(m1) == N and sum(1 for v in m1 if v and not _m.isnan(v)) > N * 0.9)
    if ok:
        e50 = [v if v and not _m.isnan(v) else None for v in m1]
        e60 = [v if v and not _m.isnan(v) else None for v in m2]
        src_ema = "original"
    else:
        e50, e60 = ema(C, 50), ema(C, 60)
        src_ema = "calcule"
    vma = sma_n(V, 20)

    def news_bar(i):
        if not use_filter:
            return False
        t0 = T[i]
        for hh, mm in NEWS_HHMM:
            tn = t0.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
            if 0 <= (tn - t0).total_seconds() < tf:
                return True
        return False

    def score(i):
        rng = max(H[i] - L[i], 1e-12)
        br = min(abs(C[i] - O[i]) / rng / 0.5, 1.0)
        cpos = (C[i] - L[i]) / rng if bull[i] else (H[i] - C[i]) / rng
        awick = (H[i] - C[i]) / rng if bull[i] else (C[i] - L[i]) / rng
        s_str = (br + (1.0 - min(awick / 0.35, 1.0)) + min(cpos / 0.67, 1.0)) / 3.0
        s_mom = min((H[i] - L[i]) / max(0.5 * atr[i], 1e-12), 1.0)
        s_vol = min(V[i] / vma[i], 1.0) if vma[i] else 0.0
        s_gap = min(abs(O[i] - C[i - 1]) / max(0.3 * atr[i], 1e-12), 1.0)
        eng = ((C[i] > O[i - 1] and O[i] < C[i - 1]) if bull[i]
               else (O[i] > C[i - 1] and C[i] < O[i - 1])) \
            and H[i] > H[i - 1] and L[i] < L[i - 1]
        return (s_str + s_mom + s_vol + s_gap + (1.0 if eng else 0.0)) / 5.0 * 100.0

    tp = fp = fn = cls = 0; ecarts = []
    for i in range(WARMUP, N):
        b = bull[i]
        ours_fort = ours_moyen = False
        if (run[i] == 2 and adx[i] is not None and adx[i] >= ADX_MIN
                and e50[i] is not None and e60[i] is not None
                and ((C[i] > e50[i]) if b else (C[i] < e50[i])) and not news_bar(i)):
            db = ((C[i] - max(e50[i], e60[i])) if b else (min(e50[i], e60[i]) - C[i])) / atr[i]
            if db >= 0.3 or (vma[i] is not None and V[i] >= vma[i]):
                sc = score(i)
                ours_fort = sc >= SCORE_FORT
                ours_moyen = SCORE_MOYEN <= sc < SCORE_FORT
        ours = ours_fort or ours_moyen
        orig_fort = d["oL"][i] or d["oS"][i]
        orig_moyen = d["oLM"][i] or d["oSM"][i]
        orig = orig_fort or orig_moyen
        if ours and orig:
            tp += 1
            # desaccord de CLASSE : la fleche existe des deux cotes mais Fort vs Moyen
            if (ours_fort and orig_moyen) or (ours_moyen and orig_fort):
                cls += 1
                ecarts.append(("CLASSE", T[i].isoformat(),
                               ("nous=Fort" if ours_fort else "nous=Moyen")))
        elif ours: fp += 1; ecarts.append(("TROP", T[i].isoformat()))
        elif orig: fn += 1; ecarts.append(("MANQ", T[i].isoformat(),
                                           "Fort" if orig_fort else "Moyen"))
    return tp, fp, fn, cls, ecarts, tf, src_ema


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    use_filter = "--filtre" in sys.argv
    root = os.path.expanduser(args[0]) if args else os.path.expanduser("~/ERGON/Singal")
    files = sorted(glob.glob(os.path.join(root, "*.csv")))
    print(f"{root}  —  filtre annonces : {'ON' if use_filter else 'OFF'}  —  {len(files)} fichier(s)\n")
    hdr = f"{'fichier':<26}{'TF':>6}{'vol':>5}{'ema':>6}{'exactes':>9}{'trop':>6}{'manq':>6}{'classe':>8}"
    print(hdr); print("-" * len(hdr))
    TP = FP = FN = CL = 0; all_ec = []
    for f in files:
        d = load(f)
        if d is None:
            print(f"{os.path.basename(f)[:25]:<26}{'—':>6}{'—':>5}{'colonnes absentes':>22}")
            continue
        tp, fp, fn, cls, ec, tf, src = simulate(d, use_filter)
        TP += tp; FP += fp; FN += fn; CL += cls
        all_ec += [(os.path.basename(f),) + e for e in ec]
        print(f"{os.path.basename(f)[:25]:<26}{tf//60:>5}m{('oui' if d['has_vol'] else 'NON'):>5}{src[:4]:>6}"
              f"{tp:>9}{fp:>6}{fn:>6}{cls:>8}")
    print("-" * len(hdr))
    print(f"{'TOTAL':<26}{'':>6}{'':>5}{TP:>9}{FP:>6}{FN:>6}{CL:>8}")
    tot = TP + FN
    if tot:
        print(f"\nrappel {TP}/{tot} = {100*TP/tot:.1f} %   |   "
              f"precision {TP}/{TP+FP} = {100*TP/max(TP+FP,1):.1f} %")
    if all_ec:
        print(f"\n{len(all_ec)} ecart(s), 12 premiers :")
        for e in all_ec[:12]:
            print("   ", " ".join(str(x) for x in e))


if __name__ == "__main__":
    main()
