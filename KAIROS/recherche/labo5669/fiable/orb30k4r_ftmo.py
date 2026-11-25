"""25/11 — ORB30-K4-R, FTMO 100k : challenge rapide à plusieurs risques et phase financée (descriptif, H2 contaminée).
Depuis chaque jour de départ, et en blocs de 5 jours (1 000 chemins de 500 jours de bourse)."""
import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [ICI, os.path.join(ICI, "..")]
from effets import Grille, QTY  # noqa: E402
from banc import COMPTES, evaluer as eval_compte  # noqa: E402

X = pd.read_csv(os.path.join(ICI, "orb30k4_trades.csv"), parse_dates=["jour"])
X["dist"] = (X.prix_entree - X.stop).abs()
X["p1"] = X.pnl_2_contrats / QTY
G = Grille("MNQ")
CPT = dict(COMPTES["FTMO 100k 2-step"])
rng = np.random.default_rng(5669)


def jours(R):
    p = np.maximum(1, np.floor(R / (X.dist * 2.0))) * X.p1
    par = p.groupby(X.jour.dt.date).apply(np.array)
    return [(j.date(), np.atleast_1d(par.get(j.date(), np.array([])))) for j in G.jours], p


def blocs(jr, longueur=500, n=1000, bloc=5):
    deb = rng.integers(0, len(jr) - bloc, (n, longueur // bloc))
    return [[jr[d + i] for d in ligne for i in range(bloc)] for ligne in deb]


def finance(chemin):
    bal = CPT["depart"]
    for _, pn in chemin:
        ouv = bal
        for x in pn:
            bal += x
            if bal < CPT["depart"] - CPT["perte_max"] or bal < ouv - CPT["perte_jour"]:
                return True
    return False


print("CHALLENGE (phase 1 +10 %, phase 2 +5 %, 4 jours min)")
for R in (1050, 1500, 2000, 2500, 3000):
    jr, _ = jours(R)
    h = [eval_compte(jr[i:], CPT) for i in range(len(jr))]
    b = [eval_compte(c, CPT) for c in blocs(jr)]
    f = lambda res, s: np.mean([x[0] == s for x in res])
    med = lambda res: np.median([x[1] for x in res if x[0] == "réussi"]) if any(x[0] == "réussi" for x in res) else np.nan
    print(f"  risque {R} $ : historique réussi {f(h, 'réussi'):.0%} / échec {f(h, 'échec'):.0%} / médiane {med(h):.0f} j"
          f" | blocs réussi {f(b, 'réussi'):.0%} / échec {f(b, 'échec'):.0%} / médiane {med(b):.0f} j")
print("FINANCÉ (12 mois = 250 jours de bourse)")
for R in (1050, 700):
    jr, p = jours(R)
    h = [finance(jr[i:i + 250]) for i in range(len(jr) - 250)]
    b = [finance(c[:250]) for c in blocs(jr)]
    mens = p.groupby(X.jour.dt.to_period("M")).sum().reindex(pd.period_range(G.jours.min(), G.jours.max(), freq="M"), fill_value=0)
    print(f"  risque {R} $ : règle enfreinte en 12 mois — historique {np.mean(h):.0%}, blocs {np.mean(b):.0%} ;"
          f" % mensuel médian {100 * mens.median() / 100000:.2f} % (moyen {100 * mens.mean() / 100000:.2f} %)")
