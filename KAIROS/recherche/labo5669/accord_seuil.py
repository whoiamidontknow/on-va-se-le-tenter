"""25/11 — accord alertes / graphique selon le seuil de fiabilité (Strat5669_FIABLE). 2019-2024.
Accord = décisions prises à la fois en direct (go56b) et sur le graphique (go56) / décisions prises par l'un ou l'autre,
parmi les signaux dont le score (calculé sur la bougie en cours) dépasse le seuil."""
import runpy, sys, io, contextlib
import numpy as np, pandas as pd
sys.argv = ["x"]
src = open("score_fiabilite.py").read().split("    vp = t.attrs")[0]   # tables et score seulement
for ins in ("MNQ", "MES"):
    ns = {"__file__": "score_fiabilite.py"}
    with contextlib.redirect_stdout(io.StringIO()):
        exec(src.replace('for ins in ("MNQ", "MES"):', f'for ins in ("{ins}",):'), ns)
    t = ns["t"]
    mois = (t.t1.max() - t.t1.min()).days / 30.4
    print(f"\n{ins} : seuil | accord | alertes affichées | trades affichés alertés | décisions par mois")
    for s in (0, .5, .6, .7, .8, .9):
        k = t.score >= s
        o = pd.concat([(t[f"go56_{x}"] == 1) & k for x in "LS"]); b = pd.concat([(t[f"go56b_{x}"] == 1) & k for x in "LS"])
        print(f"  {s:>4.0%} | {(o & b).sum() / (o | b).sum():.0%} | {(o & b).sum() / b.sum():.0%} | {(o & b).sum() / o.sum():.0%} | {b.sum() / mois:.1f}")
