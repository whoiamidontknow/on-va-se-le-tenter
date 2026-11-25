"""25/11 — tableau demandé par Jeremy : seuils 0 → 95 % par 5, période 17/10/2023 → 13/11/2026, 2 contrats,
une position à la fois. Trois lectures : « TradingView » = graphique d'origine filtré par le score (case décochée),
« Graphique = alertes » = o ET b (case cochée), « Alertes » = ce qui part en direct (b). Différence = écart au seuil 0.
15 min MNQ et MES, 5 min MNQ."""
import os, sys
import numpy as np, pandas as pd
ICI = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [ICI, os.path.join(ICI, "..", "complet")]
from seuils import charger56, DECL, issues, sequence, tables, DEBUT, MILIEU, QTY
out = []
for u, ins in ((15, "MNQ"), (15, "MES"), (5, "MNQ")):
    B = charger56(ins, u); at = dict(B.attrs)
    B = B[B.t >= DEBUT - pd.Timedelta(days=3)].reset_index(drop=True); B.attrs.update(at)
    trig = B[[f"{d}_{s}" for d in DECL for s in "LS"]].values.any(axis=1)
    _, score = tables(B, trig & (B.t >= DEBUT).values & (B.t < MILIEU).values)
    I = issues(B, 3.0, 0.6667, 16); per = (B.t >= DEBUT).values
    goo = {"L": B.goo_L.values == 1, "S": B.goo_S.values == 1}; gob = {"L": B.gob_L.values == 1, "S": B.gob_S.values == 1}
    mois = (B.t.max() - DEBUT).days / 30.44
    for s in range(0, 100, 5):
        f = per & ((score >= s / 100) if s else True)
        r = dict(unite=f"{u} min", instrument=ins, seuil=s)
        for nom, L, S in (("tv", goo["L"], goo["S"]), ("ga", gob["L"] & goo["L"], gob["S"] & goo["S"]), ("al", gob["L"], gob["S"])):
            idx = np.flatnonzero(f & (L | S)); pris, ss, pn = sequence(I, idx, np.where(L[idx], 1, -1))
            r[nom] = pn.sum() * QTY; r[nom + "_n"] = len(pris)
            if nom == "al":
                r["fantomes"] = np.mean([not goo["L" if d == 1 else "S"][i] for i, d in zip(pris, ss)]) if len(pris) else np.nan
                r["trades_mois"] = len(pris) / mois
        out.append(r)
R = pd.DataFrame(out)
for c in ("tv", "ga", "al"):
    R[c + "_diff"] = R[c] - R.groupby(["unite", "instrument"])[c].transform("first")
R.to_csv(os.path.join(ICI, "tableau_jeremy.csv"), index=False)
for (u, i), g in R.groupby(["unite", "instrument"], sort=False):
    print(f"\n{u} {i}"); print(g[["seuil", "tv", "tv_diff", "ga", "al", "al_diff", "fantomes", "trades_mois"]].round(2).to_string(index=False))
