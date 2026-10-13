#!/usr/bin/env python3
"""Pourquoi aucun seuil de score ne peut separer FORT de MOYEN : rangs des 6
MOYEN dans la distribution de chaque grandeur, et test des clauses V9
(range >= 0.5 ATR, cpos >= 0.67) comme separateur de classe.
"""
import csv, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys_path = os.path.join(HERE, "oracle_fort_moyen.csv")
exec(open(os.path.join(HERE, "sim_fort_moyen_search.py")).read().split("def main")[0])

rows = load()
data, _ = dedup(rows)
F = [r for r in data if r["label"] == "FORT"]
M = [r for r in data if r["label"] == "MOYEN"]

print("=== RANG DES 6 MOYEN dans chaque grandeur (1 = la plus basse valeur)")
print("   si un MOYEN est au milieu ou en haut du classement, aucun seuil "
      "monotone ne peut l'isoler\n")
for f in ("score5", "score4", "score3", "s_str", "s_mom", "s_gap", "s_vol",
          "cpos", "rng_atr", "body_rng", "adx", "dband", "d50", "vol_sma"):
    vals = sorted(r[f] for r in data if r[f] is not None)
    n = len(vals)
    rk = []
    for r in M:
        if r[f] is None:
            rk.append("-")
        else:
            rk.append(f"{sum(1 for v in vals if v < r[f])+1}/{n}")
    print(f"  {f:<10} rangs des MOYEN : {', '.join(rk)}")

print("\n=== CLAUSES V9 PRISES COMME ETIQUETTE DE FORCE")
print("  cMom = range >= 0.5 x ATR14      (s_mom sature)")
print("  cStr = cpos  >= 0.67             (position de cloture saturee)\n")


def cm(r):
    return r["rng_atr"] is not None and r["rng_atr"] >= 0.5


def cs(r):
    return r["cpos"] is not None and r["cpos"] >= 0.67


tab = defaultdict(lambda: {"FORT": 0, "MOYEN": 0})
for r in data:
    tab[(cm(r), cs(r))][r["label"]] += 1
print(f"  {'cMom':>6}{'cStr':>6}{'FORT':>7}{'MOYEN':>7}")
for k in sorted(tab):
    print(f"  {str(k[0]):>6}{str(k[1]):>6}{tab[k]['FORT']:>7}{tab[k]['MOYEN']:>7}")


def conf(pred):
    FF = FM = MF = MM = 0
    for r in data:
        p = pred(r)
        if r["label"] == "FORT":
            FF += p; FM += not p
        else:
            MF += p; MM += not p
    return FF, FM, MF, MM


print("\n  candidats (pred = FORT) :")
for name, p in (
    ("cStr seule (cpos >= 0.67)", cs),
    ("cMom seule (range >= 0.5 ATR)", cm),
    ("cMom ET cStr", lambda r: cm(r) and cs(r)),
    ("cMom OU cStr", lambda r: cm(r) or cs(r)),
):
    FF, FM, MF, MM = conf(p)
    print(f"    {name:<34} FORT->F {FF:>3} FORT->M {FM:>3} | MOYEN->F {MF:>2} "
          f"MOYEN->M {MM:>2} | erreurs {FM+MF}")

print("\n=== BALAYAGE DU SEUIL DE cpos ET DE rng_atr (recherche d'un vrai separateur)")
best = []
for tc in [i / 100 for i in range(20, 101, 1)]:
    for tr in [i / 100 for i in range(20, 201, 2)]:
        for mode in ("et", "ou", "cpos", "rng"):
            if mode == "cpos":
                p = lambda r, tc=tc: r["cpos"] is not None and r["cpos"] >= tc
            elif mode == "rng":
                p = lambda r, tr=tr: r["rng_atr"] is not None and r["rng_atr"] >= tr
            elif mode == "et":
                p = lambda r, tc=tc, tr=tr: (r["cpos"] or 0) >= tc and (r["rng_atr"] or 0) >= tr
            else:
                p = lambda r, tc=tc, tr=tr: (r["cpos"] or 0) >= tc or (r["rng_atr"] or 0) >= tr
            FF, FM, MF, MM = conf(p)
            best.append((FM + MF, mode, tc, tr, (FF, FM, MF, MM)))
best.sort()
print(f"  {len(best)} combinaisons ; 8 meilleures :")
seen = set()
for err, mode, tc, tr, c in best:
    k = (mode, round(err))
    if k in seen:
        continue
    seen.add(k)
    print(f"    err={err:<3} {mode:<5} cpos>={tc:.2f} rng>={tr:.2f}  -> {c}")
    if len(seen) >= 8:
        break
