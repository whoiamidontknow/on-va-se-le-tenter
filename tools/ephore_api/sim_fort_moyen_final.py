#!/usr/bin/env python3
"""Verdict final.

1. Comparaison EQUITABLE des scores : uniquement sur les fleches dont la bougie
   a un volume exploitable (sinon le terme volume vaut 0 et ecrase le score —
   artefact de nos donnees, pas de l'original).
2. Toutes les regles a 1 ou 2 conditions qui font MIEUX que la baseline
   triviale « tout FORT », et leur tenue en validation croisee.
3. Puissance statistique disponible.
"""
import itertools, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(HERE, "sim_fort_moyen_search.py")).read().split("def main")[0])

data, _ = dedup(load())
VOL = [r for r in data if r["vol_sma"] is not None]


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


def line(nm, p, rows):
    FF, FM, MF, MM = conf(rows, p)
    print(f"  {nm:<40} FORT->F {FF:>3} FORT->M {FM:>3} | MOYEN->F {MF:>2} "
          f"MOYEN->M {MM:>2} | erreurs {FM+MF}/{FF+FM+MF+MM}")


nm = sum(1 for r in VOL if r["label"] == "MOYEN")
print(f"=== 1. SOUS-ENSEMBLE A VOLUME EXPLOITABLE : {len(VOL)} fleches, "
      f"{len(VOL)-nm} FORT / {nm} MOYEN")
g = lambda r, k, d=0.0: (r[k] if r[k] is not None else d)
line("tout FORT (baseline)", lambda r: True, VOL)
for t in (42, 46, 50, 54):
    line(f"score5 >= {t}  (5 termes, engulf=0)", lambda r, t=t: g(r, "score5") >= t, VOL)
for t in (42, 46, 50, 54):
    line(f"score4 >= {t}  (4 poids 25 % du panneau)", lambda r, t=t: g(r, "score4") >= t, VOL)

print("\n=== 2. TOUTES LES REGLES QUI BATTENT LA BASELINE (< 6 erreurs sur 203)")
folds = {"MES": [r for r in data if r["sym"] == "MES"],
         "NQ": [r for r in data if r["sym"] == "NQ"],
         "1D": [r for r in data if r["tf"] == "1D"],
         "intraday": [r for r in data if r["tf"] != "1D"]}

winners = []
n1 = 0
for f in NUM:
    vals = sorted({r[f] for r in data if r[f] is not None})
    for i in range(len(vals) - 1):
        thr = (vals[i] + vals[i + 1]) / 2
        for s in (1, -1):
            n1 += 1
            p = (lambda r, f=f, t=thr, s=s: None if r[f] is None
                 else (r[f] >= t if s > 0 else r[f] <= t))
            FF, FM, MF, MM = conf(data, p)
            if FM + MF < 6 and MM > 0:
                winners.append((FM + MF, f"{f} {'>=' if s>0 else '<='} {thr:.4g}", p,
                                (FF, FM, MF, MM)))
# conjonctions (grille en quantiles, comme l'etape c)
grid = {}
for f in NUM:
    vals = sorted({r[f] for r in data if r[f] is not None})
    if len(vals) >= 5:
        grid[f] = [vals[int(q * (len(vals) - 1))] for q in
                   (.02, .05, .1, .2, .3, .5, .7, .9, .98)]
n2 = 0
for f1, f2 in itertools.combinations(sorted(grid), 2):
    for t1 in grid[f1]:
        for s1 in (1, -1):
            for t2 in grid[f2]:
                for s2 in (1, -1):
                    n2 += 1
                    def p(r, f1=f1, t1=t1, s1=s1, f2=f2, t2=t2, s2=s2):
                        a, b = r[f1], r[f2]
                        if a is None or b is None:
                            return None
                        return ((a >= t1 if s1 > 0 else a <= t1)
                                and (b >= t2 if s2 > 0 else b <= t2))
                    FF, FM, MF, MM = conf(data, p)
                    if FM + MF < 6 and MM > 0:
                        winners.append((FM + MF,
                                        f"{f1}{'>=' if s1>0 else '<='}{t1:.4g} ET "
                                        f"{f2}{'>=' if s2>0 else '<='}{t2:.4g}", p,
                                        (FF, FM, MF, MM)))
winners.sort(key=lambda x: x[0])
print(f"  {n1} regles a 1 seuil + {n2} conjonctions = {n1+n2} combinaisons testees")
print(f"  {len(winners)} battent la baseline. Les 12 meilleures, avec leur tenue "
      f"dans les 4 plis (erreurs par pli) :")
seen = set()
shown = 0
for err, nmm, p, c in winners:
    key = nmm.split()[0]
    if key in seen:
        continue
    seen.add(key); shown += 1
    det = []
    for k, v in folds.items():
        FF, FM, MF, MM = conf(v, p)
        det.append(f"{k}:{FM+MF}e/{MM}M")
    print(f"    err={err}  {nmm:<46} {' '.join(det)}")
    if shown >= 12:
        break

print("\n=== 3. PUISSANCE STATISTIQUE")
nF = sum(1 for r in data if r["label"] == "FORT")
nM = len(data) - nF
print(f"  {nM} MOYEN pour {nF} FORT. Un seuil = 1 degre de liberte, une conjonction = 2.")
print(f"  Avec {n1+n2} combinaisons balayees, on trouve par construction des regles")
print(f"  a 0-4 erreurs : ce n'est pas une preuve, c'est du bruit selectionne.")
p0 = 1.0
for i in range(nM):
    p0 *= (nM - i) / (len(data) - i)
print(f"  P(une grandeur sans rapport isole les {nM} MOYEN parfaitement) = {p0:.2e}")
print(f"  Esperance de separateurs parfaits par hasard sur {n1+n2} essais = "
      f"{(n1+n2)*p0:.3f}  -> un separateur PARFAIT serait credible...")
print("  ... mais on n'en a trouve AUCUN. Les regles a 4-5 erreurs, elles, sont")
print("  attendues en grand nombre par hasard et ne prouvent rien.")
