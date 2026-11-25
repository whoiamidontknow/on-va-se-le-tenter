"""25/11 — H-ORACLE (HYPOTHESES.md, commit 1892fb1) : prévoir la couleur finale (o) du Dashator 1 h / 4 h mieux que la
persistance, sur les bougies qui portent un déclencheur du 56. Appris sur H1, testé sur H2.

    uv run --with pandas --with openpyxl --with scikit-learn python oracle.py
"""
import os
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import log_loss

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [ICI]
from decision56 import DECL  # noqa: E402
from seuils import tables, ecoule_pine, COUPE_E, DEBUT, MILIEU  # noqa: E402
from objectifs import prep  # noqa: E402

NUM = ["clx", "adx", "di", "sgs", "feu", "str", "dirC", "dirM", "dirH", "atr", "e1", "e2", "k1", "k4", "b1", "b4",
       "biF", "biI", "pW", "pM", "pA", "fib", "detU", "detD", "vr"]
BITS = ["ha_up", "hei_L", "hei_S", "sF_L", "sF_S", "sM_L", "sM_S", "tl_L", "tl_S", "lvl_L", "lvl_S", "clx_L", "clx_S",
        "div_L", "div_S", "det_bloque_L", "det_bloque_S", "blackout", "tr3m", "tr5m", "tr15m", "tr1h", "tr4h", "tr1d",
        "da1m", "da5m", "da15m", "da1h", "da4h", "da1d", "macd10", "fin", "go_L", "go_S", "fib_bas"]
EPS = 1e-6


def variables(B):
    X = pd.DataFrame(index=B.index)
    a = B.atr.replace(0, np.nan)
    base = B[NUM + BITS].astype(float).copy()
    base["hl"] = (B.h - B.l) / a
    base["co"] = (B.c - B.o) / a
    for lag in range(4):
        s = base.shift(lag)
        s.columns = [f"{c}_{lag}" for c in s.columns]
        X = pd.concat([X, s], axis=1)
    for tf, bloc in (("1", "bloc1"), ("4", "bloc4")):
        g = B.groupby(bloc)
        ouv = g.o.transform("first")
        X[f"var{tf}"] = (B.c - ouv) / a
        X[f"haut{tf}"] = (g.h.cummax() - ouv) / a
        X[f"bas{tf}"] = (ouv - g.l.cummin()) / a
    X["e1h"], X["e4h"] = B.e1h.values, B.e4h.values
    tc = B.t + pd.Timedelta(minutes=B.attrs["unite"])
    X["heure"], X["minute"] = tc.dt.hour.values, tc.dt.minute.values
    return X


def persistance(B, appr):
    """P(o > 0) selon la table de fiabilité (apprise sur appr) : p si b > 0, 1 − p sinon."""
    tabs, _ = tables(B, appr)
    e = dict(zip("14", ecoule_pine(B)))
    out = {}
    for tf in "14":
        qa, tab = tabs[tf]
        b = B[f"b{tf}"].values
        r = np.minimum(np.searchsorted(qa, np.abs(b), side="left"), 4)
        c = np.digitize(e[tf], COUPE_E[1:-1], right=True)
        p = np.clip(tab[r, c], EPS, 1 - EPS)
        out[tf] = np.where(b > 0, p, 1 - p)
    return out


def modele():
    return HistGradientBoostingClassifier(max_iter=500, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=100,
                                          early_stopping=True, validation_fraction=0.2, n_iter_no_change=30,
                                          random_state=5669)


def un_cas(ins, u):
    B = prep(ins, u)
    trig = B[[f"{d}_{s}" for d in DECL for s in "LS"]].values.any(axis=1)
    per = (B.t >= DEBUT).values
    h1, h2 = per & (B.t < MILIEU).values, (B.t >= MILIEU).values
    X = variables(B)
    P = persistance(B, trig & h1)
    res, prob = [], {}
    for tf in "14":
        y = (B[f"o{tf}"].values > 0).astype(int)
        ok = np.isfinite(B[f"o{tf}"].values) & np.isfinite(B[f"b{tf}"].values)
        tr, te = trig & h1 & ok, trig & h2 & ok
        # colonnes constantes sur l'apprentissage (bits jamais vrais sur les bougies à déclencheur) : retirées,
        # sklearn ne sait pas les découper
        m = modele()
        # arrêt précoce sur la fin de H1 : sklearn tire la validation au hasard -> on la fixe aux 20 % les plus récents
        itr = np.flatnonzero(tr)
        coupe = itr[int(len(itr) * 0.8)]
        # colonnes constantes sur la partie d'apprentissage (bits jamais vrais sur les bougies à déclencheur) :
        # retirées, sklearn ne sait pas les découper
        Xv = X.loc[:, X[tr & (np.arange(len(B)) < coupe)].nunique() >= 2]
        m.set_params(early_stopping=False)
        best, best_ll, it = None, np.inf, 0
        for n_it in (25, 50, 100, 200, 300, 500):
            mm = modele().set_params(early_stopping=False, max_iter=n_it)
            mm.fit(Xv.values[tr & (np.arange(len(B)) < coupe)], y[tr & (np.arange(len(B)) < coupe)])
            v = tr & (np.arange(len(B)) >= coupe)
            ll = log_loss(y[v], np.clip(mm.predict_proba(Xv.values[v])[:, 1], EPS, 1 - EPS), labels=[0, 1])
            if ll < best_ll:
                best_ll, it = ll, n_it
        m = modele().set_params(early_stopping=False, max_iter=it).fit(Xv.values[tr], y[tr])
        pm = m.predict_proba(Xv.values)[:, 1]
        prob[tf] = pm
        pp = P[tf]
        e = B[f"e{tf}h"].values
        q = np.digitize(e, [.26, .51, .76], right=True)
        d = dict(unite=u, ins=ins, tf=f"{tf} h", iterations=it, n_test=int(te.sum()),
                 acc_pers=((pp[te] > .5) == y[te]).mean(), acc_mod=((pm[te] > .5) == y[te]).mean(),
                 ll_pers=log_loss(y[te], pp[te], labels=[0, 1]), ll_mod=log_loss(y[te], np.clip(pm[te], EPS, 1 - EPS), labels=[0, 1]))
        for j in range(4):
            s = te & (q == j)
            d[f"gain_q{j + 1}"] = ((pm[s] > .5) == y[s]).mean() - ((pp[s] > .5) == y[s]).mean() if s.any() else np.nan
        # calibration : écart moyen |prévu − observé| sur les déciles de probabilité du modèle
        dec = pd.qcut(pm[te], 10, duplicates="drop")
        cal = pd.DataFrame({"p": pm[te], "y": y[te], "dec": dec}).groupby("dec", observed=True).mean()
        d["calib_ecart"] = (cal.p - cal.y).abs().mean()
        res.append(d)
        print(f"  {u} min {ins} {tf} h : {it} itérations, précision {d['acc_pers']:.4f} -> {d['acc_mod']:.4f}", flush=True)
    # décision du 56 sur les bougies où le reste du 56 est vrai
    er = np.round(B.e1 * 10) / 10
    L = B[[f"{x}_L" for x in DECL]].values.any(axis=1)
    S = B[[f"{x}_S" for x in DECL]].values.any(axis=1)
    bL = L & ~S & (B.fin.values == 0) & (er.values <= 0.6) & h2
    bS = S & ~L & (B.fin.values == 0) & (er.values >= -0.6) & h2
    mL, mS = (prob["1"] > .5) & (prob["4"] > .5), (prob["1"] <= .5) & (prob["4"] <= .5)
    dec = dict(unite=u, ins=ins, n_bougies=int(bL.sum() + bS.sum()),
               acc_pers=np.r_[(B.gob_L.values == B.goo_L.values)[bL], (B.gob_S.values == B.goo_S.values)[bS]].mean(),
               acc_mod=np.r_[(mL == (B.goo_L.values == 1))[bL], (mS == (B.goo_S.values == 1))[bS]].mean())
    dec["gain_pts"] = 100 * (dec["acc_mod"] - dec["acc_pers"])
    return res, dec, B, prob


if __name__ == "__main__":
    R, D = [], []
    for u in (5, 15):
        for ins in ("MNQ", "MES"):
            r, d, _, _ = un_cas(ins, u)
            R += r
            D.append(d)
            print(pd.DataFrame(r).round(4).to_string(index=False), "\n", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()}, flush=True)
    R, D = pd.DataFrame(R), pd.DataFrame(D)
    R.to_csv(os.path.join(ICI, "oracle_couleur.csv"), index=False)
    D.to_csv(os.path.join(ICI, "oracle_decision.csv"), index=False)
    print("\nCOULEUR (H2)\n" + R.round(4).to_string(index=False))
    print("\nDÉCISION DU 56 (H2)\n" + D.round(4).to_string(index=False))
    print(f"\nGain moyen sur les décisions du 56 : {D.gain_pts.mean():+.2f} points (arrêt si < 2)")
