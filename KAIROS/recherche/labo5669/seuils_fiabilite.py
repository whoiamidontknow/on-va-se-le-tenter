"""25/11 — tableau des seuils de fiabilité 40 → 95 % (Strat5669_FIABLE), une position à la fois, 2 contrats.
« alertes » = trades réellement déclenchés en direct (go56b, score calculé sur la bougie en cours) ;
« graphique » = case Graphique = alertes cochée (go56 ET go56b). Fantôme = trade d'alerte absent du graphique d'origine.
Construction 2019-22 (tables du score apprises dessus) / contrôle 2023-24. Scellé 2025-26 fermé."""
import io, contextlib, sys
import numpy as np, pandas as pd
sys.path.insert(0, "."); from simu56 import simuler
src = open("score_fiabilite.py").read().split("    vp = t.attrs")[0]
def dd(p):
    c = p.cumsum(); return (c.cummax() - c).max() if len(p) else 0
for ins in ("MNQ", "MES"):
    ns = {"__file__": "score_fiabilite.py"}
    with contextlib.redirect_stdout(io.StringIO()):
        exec(src.replace('for ins in ("MNQ", "MES"):', f'for ins in ("{ins}",):'), ns)
    t = ns["t"]
    for s in "LS":
        t[f"go56ab_{s}"] = ((t[f"go56_{s}"] == 1) & (t[f"go56b_{s}"] == 1)).astype(int)
    lignes = []
    for per, m in (("2019-22", t.t1 < "2023-01-01"), ("2023-24", t.t1 >= "2023-01-01")):
        tt = t[m]; mois = (tt.t1.max() - tt.t1.min()).days / 30.4
        for s in [0] + list(range(40, 100, 5)):
            f = tt.score >= s / 100
            a = simuler(tt, lecture="b", filtre=f)
            g = simuler(tt, lecture="ab", filtre=f)
            if len(a) == 0:
                continue
            k = tt.set_index("t1")
            fant = np.mean([k.loc[r.t1, f"go56_{r.sens}"].max() != 1 for r in a.itertuples()]) if len(a) else np.nan
            lignes.append(dict(periode=per, seuil=s, trades_mois=len(a) / mois, fantomes=fant,
                               gagnants=(a.pnl > 0).mean(), alertes_usd=a.pnl.sum(), dd_usd=dd(a.pnl),
                               graphique_n=len(g), graphique_usd=g.pnl.sum()))
    r = pd.DataFrame(lignes)
    print(f"\n===== {ins}")
    print(r.round({"trades_mois": 1, "fantomes": 2, "gagnants": 2, "alertes_usd": 0, "dd_usd": 0, "graphique_usd": 0}).to_string(index=False))
