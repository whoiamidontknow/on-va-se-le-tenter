import sys
sys.path[:0] = ["/Users/jeremk/ERGON/on-va-se-le-tenter/KAIROS/dataset", "/Users/jeremk/ERGON/on-va-se-le-tenter/KAIROS/recherche/labo5669"]
import numpy as np, pandas as pd
from releve import charger
from simu56 import un_trade, ouvertures
for ins in ("MNQ", "MES"):
    t = charger(ins)
    t = t[(t.t1 < "2025-01-01") & t.parcours].copy()          # scellé 2025-2026 jamais ouvert
    t["vol"] = t.atr / t.c
    t["q"] = pd.qcut(t.vol, 5, labels=["Q1 calme", "Q2", "Q3", "Q4", "Q5 agité"])
    t["h"] = t.t1.dt.hour
    rows = []
    for s, d in (("L", 1), ("S", -1)):
        o, b = t[f"go56_{s}"] == 1, t[f"go56b_{s}"] == 1
        u = t[o | b].assign(o=o[o | b], b=b[o | b], d=d)
        rows.append(u)
    u = pd.concat(rows)
    u["fantome"] = u.b & ~u.o      # le direct le prend, le graphique ne le montre plus
    u["apres"] = u.o & ~u.b        # le graphique le montre, le direct ne l'a jamais pris
    opn = ouvertures(t)
    def R(r):
        tr, _ = un_trade(r, r.d, opn); return (tr["sortie"] - tr["entree"]) * r.d / tr["sl"]
    bb = u[u.b].copy()
    bb["R"] = [R(r) for r in bb.itertuples(index=False)]
    bb["win"] = bb.R > 0
    print(f"\n=== {ins} 2019-2024 : {len(u)} décisions (o ou b), {u.fantome.mean():.0%} fantômes, {u.apres.mean():.0%} nés après coup")
    g = u.groupby("q", observed=True).agg(n=("o", "size"), fantome=("fantome", "mean"), apres=("apres", "mean"))
    g2 = bb.groupby("q", observed=True).agg(n_b=("R", "size"), gagnant=("win", "mean"), R_moy=("R", "mean"), R_sd=("R", "std"))
    g2["R_err"] = g2.R_sd / np.sqrt(g2.n_b)
    print(g.join(g2.drop(columns="R_sd")).round(3).to_string())
    print("  par heure (fantômes %, n) :", u.groupby("h").fantome.agg(["mean", "size"]).query("size>=40").round(2).T.to_string())
    print("  par année :", u.groupby(u.t1.dt.year).agg(f=("fantome","mean"), a=("apres","mean"), n=("o","size")).round(2).T.to_string())
