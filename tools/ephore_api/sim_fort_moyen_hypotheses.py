#!/usr/bin/env python3
"""Hypotheses STRUCTUREES (pas de balayage aveugle) pour separer FORT de MOYEN,
+ analyse du sous-ensemble 1D ou se concentrent 4 des 6 MOYEN,
+ test de robustesse : une regle doit tenir sur MES et sur NQ, et sur 1D et
  intraday, avec les MEMES parametres.
"""
import csv, itertools, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(HERE, "sim_fort_moyen_search.py")).read().split("def main")[0])

data, _ = dedup(load())


def conf(rows, pred):
    FF = FM = MF = MM = 0
    for r in rows:
        p = pred(r)
        if p is None:
            continue
        if r["label"] == "FORT":
            FF += p; FM += not p
        else:
            MF += p; MM += not p
    return FF, FM, MF, MM


def line(name, rows=data):
    FF, FM, MF, MM = conf(rows, name[1])
    print(f"  {name[0]:<44} FORT->F {FF:>3} FORT->M {FM:>3} | MOYEN->F {MF:>2} "
          f"MOYEN->M {MM:>2} | erreurs {FM+MF}")
    return FM + MF


g = lambda r, k, d=0.0: (r[k] if r[k] is not None else d)

print("=== BASELINE TRIVIALE")
line(("tout FORT (aucune regle)", lambda r: True))
line(("tout MOYEN", lambda r: False))

print("\n=== HYPOTHESE EN PLACE AUJOURD'HUI (Score Minimum = 50 du panneau)")
line(("score5 (5 termes, engulf=0 en HA) >= 50", lambda r: g(r, "score5") >= 50))
line(("score4 (4 poids 25 % du panneau) >= 50", lambda r: g(r, "score4") >= 50))

print("\n=== LES DEUX CLAUSES DE CONVICTION COMME ETIQUETTE DE FORCE")
cb = lambda r: g(r, "dband", -9) >= 0.30
cv = lambda r: r["vol_sma"] is not None and r["vol_sma"] >= 1.0
line(("dband >= 0.3 ET vol >= SMA20 (double conviction)", lambda r: cb(r) and cv(r)))
line(("dband >= 0.3 (conviction de distance seule)", cb))
line(("vol >= SMA20 (conviction de volume seule)", cv))
tab = defaultdict(lambda: [0, 0])
for r in data:
    tab[(cb(r), cv(r) if r["vol_sma"] is not None else None)][r["label"] == "MOYEN"] += 1
print(f"  table croisee  {'dband>=.3':>10}{'vol>=SMA':>10}{'FORT':>7}{'MOYEN':>7}")
for k in sorted(tab, key=str):
    print(f"                 {str(k[0]):>10}{str(k[1]):>10}{tab[k][0]:>7}{tab[k][1]:>7}")

print("\n=== HYPOTHESES ADX (Seuil de Force = 18 lu au panneau)")
for t in (18, 20, 22, 25, 30):
    line((f"adx >= {t}", lambda r, t=t: g(r, "adx", -1) >= t))

print("\n=== 2 CLAUSES V9 + SCORE (3 conditions)")
cm = lambda r: g(r, "rng_atr") >= 0.5
cs = lambda r: g(r, "cpos") >= 0.67
line(("cpos>=0.67 OU score5>=50", lambda r: cs(r) or g(r, "score5") >= 50))
line(("cpos>=0.67 ET score5>=50", lambda r: cs(r) and g(r, "score5") >= 50))
line(("cpos>=0.67 OU rng>=0.5ATR (= V9, declenchement)", lambda r: cs(r) or cm(r)))

print("\n=== OU SONT LES MOYEN : concentration par unite de temps")
print(f"  {'tf':>5}{'fleches':>9}{'FORT':>6}{'MOYEN':>7}{'% MOYEN':>9}")
for tf in ("2", "5", "15", "30", "60", "240", "1D"):
    s = [r for r in data if r["tf"] == tf]
    m = sum(1 for r in s if r["label"] == "MOYEN")
    print(f"  {tf:>5}{len(s):>9}{len(s)-m:>6}{m:>7}{(100*m/len(s) if s else 0):>8.1f}%")

print("\n=== SOUS-ENSEMBLE 1D SEUL (15 fleches : 11 FORT, 4 MOYEN)")
d1 = [r for r in data if r["tf"] == "1D"]
best = []
for f in NUM:
    vals = sorted({r[f] for r in d1 if r[f] is not None})
    if len(vals) < 2:
        continue
    for i in range(len(vals) - 1):
        thr = (vals[i] + vals[i + 1]) / 2
        for s in (1, -1):
            p = (lambda r, f=f, t=thr, s=s: None if r[f] is None
                 else (r[f] >= t if s > 0 else r[f] <= t))
            FF, FM, MF, MM = conf(d1, p)
            best.append((FM + MF, f, thr, s, (FF, FM, MF, MM)))
best.sort()
print(f"  {len(best)} seuils balayes sur le seul sous-ensemble 1D ; parfaits :")
perf = [b for b in best if b[0] == 0 and b[4][3] > 0]
seen = set()
for e, f, thr, s, c in perf:
    if f in seen:
        continue
    seen.add(f)
    print(f"    {f} {'>=' if s>0 else '<='} {thr:.4g}  -> {c}")
print(f"  ({len(perf)} seuils parfaits sur 1D, portant sur {len(seen)} grandeurs "
      f"differentes — avec 4 MOYEN c'est attendu par pur hasard)")

print("\n=== ROBUSTESSE : la regle doit tenir sur MES ET sur NQ, 1D ET intraday")
folds = {"MES": [r for r in data if r["sym"] == "MES"],
         "NQ": [r for r in data if r["sym"] == "NQ"],
         "1D": d1,
         "intraday": [r for r in data if r["tf"] != "1D"]}
for k, v in folds.items():
    print(f"  pli {k:<10} {len(v):>4} fleches, "
          f"{sum(1 for r in v if r['label']=='MOYEN'):>2} MOYEN")
ok = []
ntest = 0
for f in NUM:
    vals = sorted({r[f] for r in data if r[f] is not None})
    if len(vals) < 2:
        continue
    for i in range(len(vals) - 1):
        thr = (vals[i] + vals[i + 1]) / 2
        for s in (1, -1):
            ntest += 1
            p = (lambda r, f=f, t=thr, s=s: None if r[f] is None
                 else (r[f] >= t if s > 0 else r[f] <= t))
            good = True
            for k, v in folds.items():
                FF, FM, MF, MM = conf(v, p)
                nm = sum(1 for r in v if r["label"] == "MOYEN" and r[f] is not None)
                # exige : aucun MOYEN rate ET au plus 1 FORT sacrifie dans CHAQUE pli
                if MF > 0 or FM > 1 or (nm and MM == 0):
                    good = False
                    break
            if good:
                ok.append((f, thr, s))
print(f"  {ntest} regles a un seuil testees ; {len(ok)} passent les 4 plis "
      f"(0 MOYEN rate, <=1 FORT sacrifie par pli)")
for f, thr, s in ok[:10]:
    print(f"    {f} {'>=' if s>0 else '<='} {thr:.4g}")

print("\n=== LES 15 FORT que notre score5>=50 declasse a tort (10 premiers)")
bad = sorted([r for r in data if r["label"] == "FORT" and g(r, "score5") < 50],
             key=lambda r: g(r, "score5"))
for r in bad[:10]:
    print(f"    {r['sym']:<4}{r['tf']:>4} {r['time'][:16]} {r['sens']:<6} "
          f"score5={r['score5']:.1f} score4={r['score4']:.1f} "
          f"vol/sma={r['vol_sma'] if r['vol_sma'] is None else round(r['vol_sma'],2)} "
          f"gap={r['s_gap']:.2f} str={r['s_str']:.2f}")
