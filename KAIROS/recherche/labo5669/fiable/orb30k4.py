"""25/11 — ORB30-K4 (HYPOTHESES.md, commit 11a81ad) : mesures DESCRIPTIVES sur 17/10/2023 → 13/11/2026 (H2 contaminée),
liste exacte des trades pour un vérificateur indépendant, tailles prop firm, évaluations simulées, plateau sur H1.

    uv run --with pandas --with openpyxl python orb30k4.py
"""
import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [ICI, os.path.join(ICI, "..")]
from effets import Grille, trades, evaluer, mesure, slot, S930, S1555, TICK, COMM, QTY, NS  # noqa: E402
from objectifs import AN  # noqa: E402
from banc import COMPTES, evaluer as eval_compte  # noqa: E402

P = dict(range=30, filtre="k4")


def detail(G, T):
    """Recalcul trade par trade (boucle simple, indépendante du calcul vectorisé) avec les prix et la raison de sortie."""
    et0 = lambda d, s: pd.Timestamp(G.jours[d]) + pd.Timedelta(minutes=480 + 5 * s)
    lignes = []
    for r in T.itertuples():
        d, se, s_ = r.d, r.se, int(r.sens)
        fill = G.O[d, se] + s_ * TICK
        stop = fill - s_ * r.stop
        sortie, px, raison = None, None, None
        for b in range(se, r.x):
            if (G.L[d, b] <= stop) if s_ > 0 else (G.H[d, b] >= stop):
                sortie, px, raison = et0(d, b), stop - s_ * TICK, "stop"
                break
        if px is None:
            sortie, px, raison = et0(d, r.x), G.O[d, r.x] - s_ * TICK, "15:55"
        nr = 6
        lignes.append(dict(jour=G.jours[d].date(), sens="long" if s_ > 0 else "short",
                           range_haut=np.nanmax(G.H[d, S930:S930 + nr]), range_bas=np.nanmin(G.L[d, S930:S930 + nr]),
                           cassure_et=et0(d, se - 1).strftime("%H:%M"), k4=G.K4[d, se - 1],
                           entree_et=et0(d, se).strftime("%H:%M"), prix_entree=fill, stop=stop,
                           sortie_et=sortie.strftime("%H:%M"), prix_sortie=px, raison=raison,
                           pnl_2_contrats=((px - fill) * s_ * G.vp - 2 * COMM) * QTY))
    return pd.DataFrame(lignes)


def jours_pnl(G, X, n):
    """Liste (jour, array des P&L du jour) sur tous les jours de bourse, à n micros."""
    par = X.groupby(pd.to_datetime(X.jour).dt.date).pnl_2_contrats.apply(lambda s: np.array(s) / QTY * n)
    return [(j.date(), par.get(j.date(), np.array([]))) for j in G.jours]


def evals(jours, cpt):
    st = [eval_compte(jours[i:], cpt) for i in range(len(jours))]
    s = pd.Series([x[0] for x in st])
    du = pd.Series([x[1] for x in st])
    return (s == "réussi").mean(), (s == "échec").mean(), du[s == "réussi"].median()


def finance(jours, cpt, n_j=250):
    """Phase financée : depuis chaque jour de départ, 250 jours ; probabilité d'enfreindre une règle."""
    br = []
    for i in range(0, len(jours) - n_j):
        bal = haut = cpt["depart"]
        casse = False
        for _, pn in jours[i:i + n_j]:
            ouv = bal
            for p in pn:
                bal += p
                if cpt["type"] == "ftmo" and (bal < cpt["depart"] - cpt["perte_max"] or bal < ouv - cpt["perte_jour"]):
                    casse = True
                if cpt["type"] == "suiveur" and bal <= haut - cpt["plancher"]:
                    casse = True
            haut = max(haut, bal)
            if casse:
                break
        br.append(casse)
    return float(np.mean(br)) if br else np.nan


def main():
    G = Grille("MNQ")
    T = trades(G, "D2", **P)
    pn = evaluer(G, T)
    X = detail(G, T)
    ecart = np.nanmax(np.abs(X.pnl_2_contrats.values - pn))
    X.to_csv(os.path.join(ICI, "orb30k4_trades.csv"), index=False)
    print(f"Trades : {len(X)} ; écart max entre le calcul vectorisé et la boucle trade par trade : {ecart:.6f} $")
    X["jour"] = pd.to_datetime(X.jour)
    ans_tot = (G.jours.max() - G.jours.min()).days / AN
    for nom, m in (("H1", G.h1), ("H2 (contaminée)", ~G.h1), ("total", np.ones(G.n, bool))):
        r = mesure(G, T, pn, m)
        mois = (G.jours[m].max() - G.jours[m].min()).days / 30.44
        print(f"  {nom:<16} {r['n']:4d} trades ({r['n'] / mois:.1f}/mois), gagnants {r['gain']:.1%}, P&L {r['pnl']:+,.0f} $, R/C {r['rc']:.2f}")
    p1 = X.pnl_2_contrats.values / QTY
    c = np.cumsum(p1)
    dd1 = float(np.max(np.maximum.accumulate(np.r_[0, c])[1:] - c))
    pire_jour = -X.groupby("jour").pnl_2_contrats.sum().min() / QTY
    tailles = {"FTMO 100k 2-step": int(np.floor(min(8000 / dd1, 4000 / pire_jour))), "Tradeify Select 50k": int(np.floor(1600 / dd1))}
    print(f"  par micro : pire creux {dd1:,.0f} $, pire jour {pire_jour:,.0f} $")
    for cpt_nom, n in tailles.items():
        cpt = dict(COMPTES[cpt_nom])
        cap = cpt["depart"]
        mens = X.groupby(X.jour.dt.to_period("M")).pnl_2_contrats.sum() / QTY * n
        mens = mens.reindex(pd.period_range(G.jours.min(), G.jours.max(), freq="M"), fill_value=0)
        print(f"\n  {cpt_nom} : {n} micros → {100 * n * p1.sum() / ans_tot / cap:.1f} % par an, {100 * mens.mean() / cap:.2f} % par mois en moyenne,"
              f" mois positifs {int((mens > 0).sum())}/{len(mens)}, mois ≥ 6 % : {int((mens >= 0.06 * cap).sum())}/{len(mens)}")
        cpt.pop("risque", None)
        for phase, nn in (("rapide (taille max)", n), ("financée (moitié)", max(n // 2, 1))):
            jr = jours_pnl(G, X, nn)
            if phase.startswith("rapide"):
                ok, ko, dmed = evals(jr, cpt)
                print(f"    évaluation, phase {phase}, {nn} micros : réussie {ok:.0%}, échouée {ko:.0%}, {dmed} jours médians pour réussir")
            else:
                print(f"    phase {phase}, {nn} micros : probabilité d'enfreindre une règle en 250 jours {finance(jr, cpt):.0%}")
    print("\n  Plateau sur H1 seulement (range × sortie) :")
    res = []
    for rg in (25, 30, 35):
        for R, nom in ((np.nan, "15:55"), (1.0, "1 R"), (2.0, "2 R")):
            Tq = trades(G, "D2", **dict(P, range=rg, R=R))
            r = mesure(G, Tq, evaluer(G, Tq), G.h1)
            res.append(r)
            print(f"    range {rg} min, sortie {nom:<5} : {r['n']} tr {r['pnl']:+,.0f} $ R/C {r['rc']:.2f}")
    print(f"    positifs {sum(r['pnl'] > 0 for r in res)}/9, R/C médian {np.nanmedian([r['rc'] for r in res]):.2f}")


if __name__ == "__main__":
    main()
