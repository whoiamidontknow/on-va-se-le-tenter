"""Variante 5 (idée 5) : prédire au signal si les bougies Dashator 1 h / 4 h EN COURS finiront dans le
sens du trade, puis filtrer le 56 en lecture b sur cette confiance.

- Étiquette : couleur finale de la bougie 1 h (o1h > 0) et 4 h (o4h > 0). C'est l'information que la
  lecture d'origine connaît trop tôt (la fuite).
- Variables connues à la clôture de la bougie signal : corps en cours b (× ATR), minutes écoulées el,
  corps de la dernière bougie terminée k, et leur interaction b × el.
- Modèle : régression logistique par unité (1 h, 4 h) et par instrument, ajustée sur 2019-2022 SEULEMENT.
- Qualité de prédiction mesurée sur 2023-2024 : AUC, Brier, calibration par déciles.
- Confiance d'un trade = P(1 h finit dans le sens) × P(4 h finit dans le sens), comme f_conf.
- Filtre : go56b et cf >= 50 / 60 / 70 % (fixés à l'avance), contre 1 000 tirages au hasard (réf. B).

    uv run -q --with pandas --with openpyxl --with scikit-learn python variante5.py
"""
import os
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "dataset"))
from releve import charger  # noqa: E402
from banc import issues, sequence, mesures, tirages  # noqa: E402

COUPURE = pd.Timestamp("2023-01-01")
SEUILS = (0.50, 0.60, 0.70)
UNITES = {"1h": ("b1h", "el1", "k1h", "o1h", 60.0), "4h": ("b4h", "el4", "k4h", "o4h", 240.0)}


def variables(T, u):
    b, el, k, _, dur = UNITES[u]
    e = T[el] / dur
    return np.column_stack([T[b], T[b] * e, e, T[k]])


def ajuster(T):
    modeles = {}
    for u, (b, el, k, o, _) in UNITES.items():
        m = T[[b, el, k, o]].notna().all(axis=1) & (T[o] != 0)
        X, y = variables(T[m], u), (T.loc[m, o] > 0).astype(int)
        modeles[u] = LogisticRegression(C=1.0, max_iter=1000).fit(X, y)
    return modeles


def proba(modeles, T, u):
    X = variables(T, u)
    p = np.full(len(T), np.nan)
    ok = ~np.isnan(X).any(axis=1)
    p[ok] = modeles[u].predict_proba(X[ok])[:, 1]
    return p


def calibration(p, y, n=10):
    q = pd.qcut(p, n, duplicates="drop")
    g = pd.DataFrame({"p": p, "y": y, "q": q}).groupby("q", observed=True)
    return g.agg(pred=("p", "mean"), obs=("y", "mean"), n=("y", "size"))


def main():
    rng = np.random.default_rng(5669)
    lignes = []
    for ins in ("MNQ", "MES"):
        R = charger(ins, controle=False)
        A, V = R[R.t1 < COUPURE], R[(R.t1 >= COUPURE) & (R.t1 < pd.Timestamp("2025-01-01"))]
        mod = ajuster(A)
        print(f"\n=== {ins} : modèles ajustés sur {len(A)} bougies 2019-2022, évalués sur {len(V)} bougies 2023-2024")
        for u, (b, el, k, o, _) in UNITES.items():
            m = V[[b, el, k, o]].notna().all(axis=1) & (V[o] != 0)
            p, y = proba(mod, V[m], u), (V.loc[m, o] > 0).astype(int).values
            naif = (V.loc[m, b] > 0).astype(int).values     # « la couleur en cours restera » (lecture b)
            print(f"  {u} : AUC {roc_auc_score(y, p):.3f} ; Brier {brier_score_loss(y, p):.3f} ; "
                  f"exactitude du modèle {((p > 0.5) == y).mean():.1%} contre {(naif == y).mean():.1%} pour « la couleur en cours reste »")
            c = calibration(p, y)
            print("     calibration (prédit → observé) : " + " ; ".join(f"{r.pred:.2f}→{r.obs:.2f}" for r in c.itertuples()))
        # confiance du trade sur les signaux go56b 2023-2024 : calibration contre « 1 h ET 4 h finissent dans le sens »
        for T, nom in ((A, "construction"), (V, "contrôle")):
            g = T[(T.go56b_L == 1) | (T.go56b_S == 1)]
            d = np.where(g.go56b_L == 1, 1, -1)
            p1, p4 = proba(mod, g, "1h"), proba(mod, g, "4h")
            cf = np.where(d > 0, p1 * p4, (1 - p1) * (1 - p4))
            y = ((np.sign(g.o1h) == d) & (np.sign(g.o4h) == d)).astype(int).values
            ok = ~np.isnan(cf)
            print(f"  signaux go56b {nom} ({ok.sum()}) : AUC de cf pour « 1 h et 4 h finissent dans le sens » {roc_auc_score(y[ok], cf[ok]):.3f} ;"
                  f" taux de base {y[ok].mean():.1%}")
            if nom == "contrôle":
                c = calibration(cf[ok], y[ok], 5)
                print("     calibration cf (quintiles) : " + " ; ".join(f"{r.pred:.2f}→{r.obs:.2f} (n={r.n})" for r in c.itertuples()))
        # filtre sur le 56 b
        C0 = issues(R)
        d0 = np.where(C0.go56b_L == 1, 1, -1)
        p1, p4 = proba(mod, C0, "1h"), proba(mod, C0, "4h")
        C0["cf"] = np.where(d0 > 0, p1 * p4, (1 - p1) * (1 - p4))
        for per, m in (("construction 2019-2022", C0.t1 < COUPURE), ("contrôle 2023-2024", C0.t1 >= COUPURE)):
            C = C0[m].reset_index(drop=True)
            base = (C.go56b_L == 1) | (C.go56b_S == 1)
            for s in (None,) + SEUILS:
                mm = base & ((C.cf >= s) if s else True)
                idx = np.flatnonzero(mm.values)
                sens = np.where(C.go56b_L.values[idx] == 1, 1, -1)
                r = mesures(sequence(C, idx, sens))
                D, _ = tirages(C, idx, sens, r["n"], "B", rng)
                p = (np.sum(D.pnl >= r["pnl"]) + 1) / (len(D) + 1)
                nom = "56 b" if s is None else f"56 b + cf >= {s:.0%}"
                lignes.append(dict(instrument=ins, variante=nom, periode=per, n=r["n"], gain=r["gain"], pnl=r["pnl"],
                                   par_trade=r["par_trade"], baisse_max=r["baisse_max"], pnl_hasard_med=D.pnl.median(), p=p))
                print(f"  {per:<22} {nom:<18} : {r['n']:4d} trades, {r['gain']:.1%}, {r['pnl']:>8,.0f} $ ({r['par_trade']:+.1f}/trade),"
                      f" baisse {r['baisse_max']:>6,.0f} | hasard médian {D.pnl.median():>7,.0f} $ ; p = {p:.3f}")
    T = pd.DataFrame(lignes)
    T.to_csv(os.path.join(os.path.dirname(__file__), "resultats_variante5.csv"), index=False)


if __name__ == "__main__":
    main()
