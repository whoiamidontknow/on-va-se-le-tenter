#!/usr/bin/env python3
"""Puissance statistique : y a-t-il un signal, et est-il exploitable ?

- AUC (Mann-Whitney) de chaque grandeur, p-value normale approchee, et la meme
  p-value corrigee du nombre de grandeurs testees (Bonferroni).
- courbe de compromis du seuil de score : combien de FORT on sacrifie pour
  attraper k MOYEN.
"""
import math, os

HERE = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(HERE, "sim_fort_moyen_search.py")).read().split("def main")[0])

data, _ = dedup(load())
F = [r for r in data if r["label"] == "FORT"]
M = [r for r in data if r["label"] == "MOYEN"]


def phi(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


rows = []
for f in NUM:
    vf = [r[f] for r in F if r[f] is not None]
    vm = [r[f] for r in M if r[f] is not None]
    if len(vm) < 3 or len(vf) < 20:
        continue
    n, m = len(vf), len(vm)
    s = sum(1 if a > b else (0.5 if a == b else 0) for a in vf for b in vm)
    auc = s / (n * m)
    sd = math.sqrt((n + m + 1) / (12.0 * n * m))
    z = (auc - 0.5) / sd
    p = 2 * (1 - phi(abs(z)))
    rows.append((abs(auc - 0.5), f, auc, z, p, n, m))
rows.sort(reverse=True)
K = len(rows)
print(f"=== AUC ET SIGNIFICATIVITE ({K} grandeurs testees)")
print(f"  {'grandeur':<10}{'AUC':>7}{'z':>7}{'p brut':>10}{'p x {}'.format(K):>12}"
      f"{'nFORT':>7}{'nMOY':>6}")
for _, f, auc, z, p, n, m in rows[:12]:
    print(f"  {f:<10}{auc:>7.3f}{z:>7.2f}{p:>10.4f}{min(1,p*K):>12.3f}{n:>7}{m:>6}")
print("  (AUC > 0.5 = la grandeur est PLUS GRANDE chez les FORT)")

print("\n=== COMPROMIS DU SEUIL DE SCORE : prix a payer pour attraper les MOYEN")
for sc in ("score5", "score4"):
    print(f"  {sc} :")
    vals = sorted({r[sc] for r in data if r[sc] is not None})
    print(f"    {'seuil':>7}{'MOYEN attrapes':>16}{'FORT sacrifies':>16}{'erreurs':>9}")
    for k in range(1, 7):
        best = None
        for i in range(len(vals) - 1):
            t = (vals[i] + vals[i + 1]) / 2
            mm = sum(1 for r in M if r[sc] is not None and r[sc] < t)
            fm = sum(1 for r in F if r[sc] is not None and r[sc] < t)
            if mm >= k and (best is None or fm < best[1]):
                best = (t, fm, mm)
        if best:
            print(f"    {best[0]:>7.1f}{best[2]:>16}{best[1]:>16}{best[1]+6-best[2]:>9}")

print("\n=== CONCLUSION CHIFFREE")
nb = 6
print(f"  baseline « tout FORT » : {nb} erreurs sur {len(data)} = "
      f"{100*(1-nb/len(data)):.1f} % d'accord")
print("  aucune regle a 1 ou 2 conditions ne descend sous 4 erreurs, et les 3 qui y")
print("  arrivent reposent sur l'ATR en points absolus (= « NQ en journalier »).")
