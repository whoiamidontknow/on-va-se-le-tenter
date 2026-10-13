#!/usr/bin/env python3
"""Recherche du separateur FORT / MOYEN parmi les fleches de l'original.

Entree : oracle_fort_moyen.csv produit par sim_fort_moyen_oracle.py
Sortie : matrices de confusion completes pour chaque candidat.

Etapes (ordre demande) :
  0. deduplication des fleches (les 2 lots se recouvrent) + controle de
     coherence des features entre lots ;
  a. seuil sur une seule grandeur, balayage exhaustif ;
  b. seuil sur le score agrege (hypothese courante Fort >= 50) ;
  c. conjonction de deux conditions ;
  d. comptage « au moins N des 5 termes satures ».
  + validation croisee MES/NQ et 1D/intraday
  + nombre de combinaisons testees
"""
import csv, itertools, math, os, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "oracle_fort_moyen.csv")

NUM = ["s_str", "s_mom", "s_vol", "s_gap", "s_eng", "score5", "score4", "score3",
       "adx", "dip", "dim", "dirdi", "rsi", "rsidir", "cci", "ccidir", "atr",
       "rng_atr", "body_rng", "cpos", "awick", "body_atr", "vol_sma", "dband",
       "d50", "bbw", "bbpos", "gap_atr"]


def fnum(x):
    try:
        v = float(x)
        return None if v != v else v
    except (TypeError, ValueError):
        return None


def load():
    rows = [r for r in csv.DictReader(open(SRC)) if r["grp"] == "g4"]
    for r in rows:
        for k in NUM:
            r[k] = fnum(r.get(k))
        r["run"] = fnum(r.get("run"))
    return rows


def dedup(rows):
    """Une fleche = (sym, tf, time, sens). Priorite au lot `ajust` (il a le
    volume). Les features manquantes sont completees depuis l'autre lot."""
    by = defaultdict(list)
    for r in rows:
        by[(r["sym"], r["tf"], r["time"], r["sens"])].append(r)
    out, mism = [], []
    for k, v in by.items():
        v.sort(key=lambda r: 0 if r["src"] == "ajust" else 1)
        base = dict(v[0])
        if len(v) > 1:
            for f in NUM:
                a, b = v[0][f], v[1][f]
                if a is None and b is not None:
                    base[f] = b
                elif a is not None and b is not None and f not in ("s_vol", "vol_sma",
                                                                   "score5", "score4"):
                    den = max(abs(a), abs(b), 1e-9)
                    if abs(a - b) / den > 0.02:
                        mism.append((k, f, a, b))
            if v[0]["label"] != v[1]["label"]:
                mism.append((k, "LABEL", v[0]["label"], v[1]["label"]))
        out.append(base)
    out.sort(key=lambda r: (r["sym"], r["tf"], r["time"]))
    return out, mism


def confusion(rows, pred_fort):
    """pred_fort(r) -> bool. Renvoie (FF, FM, MF, MM) :
    FF = vrai FORT predit FORT, FM = vrai FORT predit MOYEN,
    MF = vrai MOYEN predit FORT, MM = vrai MOYEN predit MOYEN."""
    FF = FM = MF = MM = 0
    for r in rows:
        p = pred_fort(r)
        if p is None:
            continue
        if r["label"] == "FORT":
            FF += p; FM += not p
        else:
            MF += p; MM += not p
    return FF, FM, MF, MM


def show(name, c, n):
    FF, FM, MF, MM = c
    tot = FF + FM + MF + MM
    err = FM + MF
    print(f"  {name:<46} FORT->F {FF:>3} FORT->M {FM:>3} | "
          f"MOYEN->F {MF:>2} MOYEN->M {MM:>2} | erreurs {err}/{tot}")


def main():
    rows = load()
    data, mism = dedup(rows)
    nF = sum(1 for r in data if r["label"] == "FORT")
    nM = sum(1 for r in data if r["label"] == "MOYEN")
    print(f"=== 0. ORACLE DEDUPLIQUE : {len(data)} fleches — {nF} FORT / {nM} MOYEN "
          f"({100*nM/len(data):.1f} % de MOYEN)")
    if mism:
        print(f"    {len(mism)} incoherence(s) de feature entre les deux lots "
              f"(>2 % d'ecart) ; 5 premieres :")
        for m in mism[:5]:
            print("     ", m)
    else:
        print("    features identiques entre les deux lots sur les 145 fleches communes : OK")
    print("    repartition des MOYEN :")
    for r in data:
        if r["label"] == "MOYEN":
            print(f"      {r['sym']:<4}{r['tf']:>4}  {r['time'][:16]}  {r['sens']:<6}"
                  f" score5={r['score5']:.1f} score4={r['score4'] and round(r['score4'],1)}"
                  f" adx={r['adx'] and round(r['adx'],1)}"
                  f" rng/atr={r['rng_atr'] and round(r['rng_atr'],2)}"
                  f" cpos={r['cpos'] and round(r['cpos'],2)}"
                  f" vol/sma={r['vol_sma'] and round(r['vol_sma'],2)}")
    # couverture des features
    print("\n    couverture (features non nulles) :")
    miss = [(f, sum(1 for r in data if r[f] is None)) for f in NUM]
    for f, n in miss:
        if n:
            print(f"      {f}: {n} manquante(s) sur {len(data)}")

    ncomb = 0

    # ---------- b. score agrege (hypothese courante) ----------
    print("\n=== b. SEUIL SUR LE SCORE AGREGE (hypothese courante)")
    for sc in ("score5", "score4", "score3"):
        for thr in (42, 46, 50, 54, 58):
            ncomb += 1
            show(f"{sc} >= {thr}", confusion(data, lambda r, s=sc, t=thr:
                                             (r[s] is not None and r[s] >= t)), len(data))

    # ---------- a. seuil sur une seule grandeur ----------
    print("\n=== a. SEUIL SUR UNE SEULE GRANDEUR — balayage exhaustif")
    results = []
    for f in NUM:
        vals = sorted({r[f] for r in data if r[f] is not None})
        if len(vals) < 2:
            continue
        cands = [(vals[i] + vals[i + 1]) / 2 for i in range(len(vals) - 1)]
        for thr in cands:
            for sense in (1, -1):
                ncomb += 1
                pred = (lambda r, f=f, t=thr, s=sense:
                        None if r[f] is None else (r[f] >= t if s > 0 else r[f] <= t))
                c = confusion(data, pred)
                FF, FM, MF, MM = c
                if MM + MF == 0:
                    continue
                results.append((FM + MF, MM, f, thr, sense, c))
    results.sort(key=lambda x: (x[0], -x[1]))
    print(f"  {len(results)} couples (grandeur, seuil, sens) evalues ; 12 meilleurs :")
    seenf = set(); shown = 0
    for err, mm, f, thr, sense, c in results:
        if f in seenf:
            continue
        seenf.add(f); shown += 1
        show(f"{f} {'>=' if sense>0 else '<='} {thr:.4g}", c, len(data))
        if shown >= 12:
            break
    perfect = [r for r in results if r[0] == 0]
    print(f"  separateurs PARFAITS (0 erreur) : {len(perfect)}")
    for err, mm, f, thr, sense, c in perfect[:20]:
        print(f"      {f} {'>=' if sense>0 else '<='} {thr:.4g}")

    # ---------- d. comptage de termes satures ----------
    print("\n=== d. COMPTAGE « au moins N des 5 termes satures »")
    SAT = {"s_str": 0.999, "s_mom": 0.999, "s_vol": 0.999, "s_gap": 0.999, "s_eng": 0.999}

    def nsat(r):
        n = 0
        for k, t in SAT.items():
            if r[k] is not None and r[k] >= t:
                n += 1
        return n
    for N in (1, 2, 3, 4):
        ncomb += 1
        show(f"nb termes satures >= {N}", confusion(data, lambda r, N=N: nsat(r) >= N),
             len(data))
    cnt = Counter((nsat(r), r["label"]) for r in data)
    print("   distribution :", dict(sorted(cnt.items())))

    # ---------- c. conjonction de deux conditions ----------
    print("\n=== c. CONJONCTION DE DEUX CONDITIONS")
    # grille grossiere pour limiter l'explosion : 9 quantiles par grandeur
    grid = {}
    for f in NUM:
        vals = sorted({r[f] for r in data if r[f] is not None})
        if len(vals) < 5:
            continue
        grid[f] = [vals[int(q * (len(vals) - 1))] for q in
                   (.02, .05, .1, .2, .3, .5, .7, .9, .98)]
    pairs = []
    keys = sorted(grid)
    for f1, f2 in itertools.combinations(keys, 2):
        for t1 in grid[f1]:
            for s1 in (1, -1):
                for t2 in grid[f2]:
                    for s2 in (1, -1):
                        ncomb += 1
                        def pred(r, f1=f1, t1=t1, s1=s1, f2=f2, t2=t2, s2=s2):
                            a, b = r[f1], r[f2]
                            if a is None or b is None:
                                return None
                            ca = a >= t1 if s1 > 0 else a <= t1
                            cb = b >= t2 if s2 > 0 else b <= t2
                            return ca and cb
                        c = confusion(data, pred)
                        FF, FM, MF, MM = c
                        if FM + MF == 0 and MM + MF > 0:
                            pairs.append((f1, s1, t1, f2, s2, t2, c))
    print(f"  {len(pairs)} conjonctions a 0 erreur sur l'ensemble complet")
    for p in pairs[:8]:
        f1, s1, t1, f2, s2, t2, c = p
        show(f"{f1}{'>=' if s1>0 else '<='}{t1:.4g} ET {f2}{'>=' if s2>0 else '<='}{t2:.4g}",
             c, len(data))

    print(f"\n=== NOMBRE TOTAL DE COMBINAISONS TESTEES : {ncomb}")

    # ---------- validation croisee ----------
    print("\n=== 4. VALIDATION CROISEE — degres de liberte vs nombre de MOYEN")
    for name, sel in (("MES", lambda r: r["sym"] == "MES"),
                      ("NQ", lambda r: r["sym"] == "NQ"),
                      ("1D", lambda r: r["tf"] == "1D"),
                      ("intraday", lambda r: r["tf"] != "1D")):
        sub = [r for r in data if sel(r)]
        m = sum(1 for r in sub if r["label"] == "MOYEN")
        print(f"  {name:<10} {len(sub):>4} fleches, {m:>2} MOYEN")
    print("  -> un seul seuil libre = 1 degre de liberte ; avec N MOYEN dans le pli de"
          " validation, la puissance statistique est ~N.")

    # probabilite qu'un separateur parfait apparaisse par hasard
    nf, nm = nF, nM
    p = 1.0
    for i in range(nm):
        p *= (nm - i) / (nf + nm - i)
    print(f"\n  Hasard : probabilite qu'une grandeur SANS RAPPORT place les {nm} MOYEN "
          f"aux {nm} rangs extremes de {nf+nm} = {p:.2e}")
    print(f"  Mais on balaye {ncomb} combinaisons -> esperance de separateurs parfaits "
          f"par pur hasard ~ {ncomb*p:.2f}")


if __name__ == "__main__":
    main()
