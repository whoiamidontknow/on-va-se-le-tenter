"""25/11 — idée de Jeremy : score de fiabilité de la couleur Dashator 1 h / 4 h au moment du signal.
Plus la bougie 1 h / 4 h est avancée et plus son corps est loin de zéro, moins sa couleur devrait changer d'ici la clôture.
p_tf = P(couleur finale = couleur en cours | |valeur en cours|, part écoulée de la bougie), table apprise sur 2019-2022.
score = p1h × p4h. Test sur 2023-2024 (scellé 2025-26 fermé) : trades réellement pris en direct (go56b),
par tranche de score : fantômes (go56 = 0) et résultat (trades indépendants).
"""
import sys, os
sys.path[:0] = [os.path.expanduser("~/ERGON/on-va-se-le-tenter/KAIROS/dataset"), os.path.dirname(os.path.abspath(__file__))]
import numpy as np, pandas as pd
from releve import charger
from simu56 import un_trade, ouvertures

def ecoule(t):
    m, h = t.t1.dt.minute, t.t1.dt.hour
    e1 = np.where(m == 0, 1.0, m / 60)
    q = (h % 4) * 60 + m
    e4 = np.where(q == 0, 1.0, q / 240)
    return e1, e4

for ins in ("MNQ", "MES"):
    t = charger(ins)
    t = t[(t.t1 < "2025-01-01") & t.parcours].copy()
    t["e1"], t["e4"] = ecoule(t)
    construction = t.t1 < "2023-01-01"
    for tf in ("1", "4"):
        b, o = t[f"b{tf}h"], t[f"o{tf}h"]
        t[f"ok{tf}"] = np.sign(b) == np.sign(o)
        t[f"qa{tf}"] = pd.cut(b.abs(), np.r_[0, b[construction].abs().quantile([.2, .4, .6, .8]).values, 99], include_lowest=True)
        t[f"qe{tf}"] = pd.cut(t[f"e{tf}"], [0, .26, .51, .76, 1.0], include_lowest=True)
        tab = t[construction].groupby([f"qa{tf}", f"qe{tf}"], observed=True)[f"ok{tf}"].mean()
        t[f"p{tf}"] = [tab.get((a, e), np.nan) for a, e in zip(t[f"qa{tf}"], t[f"qe{tf}"])]
        if ins == "MNQ":
            print(f"\nMNQ — table {tf} h (2019-22) : P(couleur inchangée à la clôture), lignes = |corps| en quintiles, colonnes = part écoulée")
            print(tab.unstack().round(2).to_string())
    t["score"] = t.p1 * t.p4
    vp = t.attrs["val_point"]; opn = ouvertures(t)
    rows = []
    for s, d in (("L", 1), ("S", -1)):
        u = t[t[f"go56b_{s}"] == 1].copy(); u["d"] = d; u["fant"] = t.loc[u.index, f"go56_{s}"] != 1; rows.append(u)
    u = pd.concat(rows)
    res = [un_trade(r, r.d, opn)[0] for r in u.itertuples(index=False)]
    u["R"] = [(o["sortie"] - o["entree"]) * d / o["sl"] for o, d in zip(res, u.d)]
    u["pnl"] = [(o["sortie"] - o["entree"]) * d * 2 * vp - 5 for o, d in zip(res, u.d)]
    seuils = u[u.t1 < "2023-01-01"].score.quantile([.25, .5, .75]).values
    u["tranche"] = pd.cut(u.score, np.r_[-1, seuils, 2], labels=["Q1 peu fiable", "Q2", "Q3", "Q4 très fiable"])
    u["periode"] = np.where(u.t1 < "2023-01-01", "construction 2019-22", "contrôle 2023-24")
    print(f"\n===== {ins} — trades pris en direct (go56b), par tranche de score de fiabilité")
    g = u.groupby(["periode", "tranche"], observed=True).agg(
        n=("R", "size"), fantomes=("fant", "mean"), gagnants=("R", lambda x: (x > 0).mean()),
        R=("R", "mean"), err=("R", lambda x: x.std() / np.sqrt(len(x))), usd=("pnl", "sum"))
    print(g.round(3).to_string())
