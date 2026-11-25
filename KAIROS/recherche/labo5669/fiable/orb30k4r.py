"""25/11 — ORB30-K4-R (HYPOTHESES.md, commit 34a34a1) : taille à risque fixe, mesures DESCRIPTIVES (H2 contaminée),
et corrélation journalière avec D5 (tournant du mois MNQ) et le 56 en alertes 15 min MNQ (information)."""
import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [ICI, os.path.join(ICI, ".."), os.path.join(ICI, "..", "complet")]
from effets import Grille, trades as trades_effets, evaluer, jours_tom, QTY  # noqa: E402
from objectifs import prep, decisions, trades as trades_56, AN  # noqa: E402
from moteur import issues  # noqa: E402
from banc import COMPTES, evaluer as eval_compte  # noqa: E402

X = pd.read_csv(os.path.join(ICI, "orb30k4_trades.csv"), parse_dates=["jour"])
X["dist"] = (X.prix_entree - X.stop).abs()
X["p1"] = X.pnl_2_contrats / QTY
G = Grille("MNQ")
ans = (G.jours.max() - G.jours.min()).days / AN


def avec_risque(R):
    n = np.maximum(1, np.floor(R / (X.dist * 2.0)))
    p = n * X.p1
    c = np.cumsum(p.values)
    dd = float(np.max(np.maximum.accumulate(np.r_[0, c])[1:] - c))
    pj = -p.groupby(X.jour).sum().min()
    return n, p, dd, pj


def taille(limite_dd, limite_jour):
    best = None
    for R in range(50, 10001, 50):
        n, p, dd, pj = avec_risque(R)
        if dd < limite_dd and pj < limite_jour:
            best = R
    return best


for nom, cap, ldd, lj in (("FTMO 100k", 100000, 8000, 4000), ("Tradeify 50k", 50000, 1600, np.inf)):
    R = taille(ldd, lj)
    if R is None:
        n, p, dd, pj = avec_risque(50)
        print(f"{nom} : aucun risque ne tient (même à 50 $, minimum 1 micro : creux {dd:,.0f} $)")
        continue
    n, p, dd, pj = avec_risque(R)
    mens = p.groupby(X.jour.dt.to_period("M")).sum().reindex(pd.period_range(G.jours.min(), G.jours.max(), freq="M"), fill_value=0)
    print(f"{nom} : risque {R} $ par trade (micros moyen {n.mean():.1f}, de {int(n.min())} à {int(n.max())}) ; P&L {p.sum():+,.0f} $,"
          f" creux {dd:,.0f} $, pire jour {pj:,.0f} $, R/C {(p.sum() / ans) / dd:.2f}")
    print(f"   {100 * p.sum() / ans / cap:.1f} % par an, {100 * mens.mean() / cap:.2f} % par mois, mois positifs {int((mens > 0).sum())}/{len(mens)},"
          f" mois ≥ 6 % : {int((mens >= 0.06 * cap).sum())}/{len(mens)}")
    if nom.startswith("FTMO"):
        par = p.groupby(X.jour.dt.date).apply(np.array)
        jr = [(j.date(), np.atleast_1d(par.get(j.date(), np.array([])))) for j in G.jours]
        cpt = dict(COMPTES["FTMO 100k 2-step"])
        st = [eval_compte(jr[i:], cpt) for i in range(len(jr))]
        s = pd.Series([x[0] for x in st]); du = pd.Series([x[1] for x in st])
        print(f"   challenge FTMO depuis chaque jour : réussi {(s == 'réussi').mean():.0%}, échoué {(s == 'échec').mean():.0%},"
              f" {du[s == 'réussi'].median()} jours médians")

# corrélations journalières (par contrat)
orb = X.groupby(X.jour.dt.date).p1.sum()
T5 = trades_effets(G, "D5", tom=jours_tom(G))
p5 = evaluer(G, T5) / QTY
d5 = pd.Series(p5, index=[G.jours[d].date() for d in T5.d]).groupby(level=0).sum()
B = prep("MNQ", 15)
T56 = trades_56(B, issues(B, 3.0, 0.6667, 16), *decisions(B, "b", 0))
s56 = T56.groupby(pd.to_datetime(T56.tx).dt.date).p1.sum()
cal = [j.date() for j in G.jours]
S = pd.DataFrame({"ORB": orb, "D5": d5, "56_15min": s56}).reindex(cal).fillna(0)
print("\nCorrélation journalière (tous les jours de bourse, 0 sans trade) :")
print(S.corr().round(3).to_string())
for a in ("D5", "56_15min"):
    m = (S.ORB != 0) & (S[a] != 0)
    print(f"  ORB / {a} sur les {int(m.sum())} jours où les deux tradent : {S.ORB[m].corr(S[a][m]):+.3f}")
