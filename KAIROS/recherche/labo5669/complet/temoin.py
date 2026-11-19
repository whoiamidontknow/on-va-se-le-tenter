"""C1 — Témoin « tout ou rien » (protocole dans ../HYPOTHESES.md, écrit avant le test).

    uv run -q --with pandas --with openpyxl --with scikit-learn --with scipy python temoin.py
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "dataset"))
from releve_complet import charger, BITS  # noqa: E402
from moteur import issues, sequence, mesures, hasard  # noqa: E402

DEBUT, COUPURE, SCELLE = pd.Timestamp("2019-05-01"), pd.Timestamp("2023-01-01"), pd.Timestamp("2025-01-01")
K_ATR, TPR, NBAR = 2.0, 1.0, 16
NUM = ["clx", "adx", "di", "sgs", "feu", "str", "dirC", "dirM", "dirH", "e1", "e2", "k1", "k4", "b1", "b4",
       "biF", "biI", "pW", "pM", "pA", "fib", "detU", "detD", "vr"]


def variables(B):
    X = B[NUM + BITS].astype(float).copy()
    X["atr_rel"] = B.atr / B.c * 1e4
    X["rng"] = (B.h - B.l) / B.atr
    X["corps"] = (B.c - B.o) / B.atr
    X["ret4"] = (B.c - B.c.shift(4)) / B.atr
    X["ret16"] = (B.c - B.c.shift(16)) / B.atr
    X["heure"] = B.t.dt.hour + B.t.dt.minute / 60
    X["jour"] = B.t.dt.dayofweek
    return X


def main():
    lignes = []
    rng = np.random.default_rng(5669)
    for ins in ("MNQ", "MES"):
        B = charger(ins)
        I = issues(B, K_ATR, TPR, NBAR)
        X = variables(B)
        risque = K_ATR * B.atr.values * B.attrs["val_point"]
        t = B.t.values
        # marge de 20 bougies pour qu'aucun trade d'apprentissage ne déborde sur la période suivante
        marge = pd.Timedelta(hours=5)
        app = (B.t >= DEBUT) & (B.t < COUPURE - marge)
        ctl = (B.t >= COUPURE) & (B.t < SCELLE - marge)
        coupe_val = B.t[app].quantile(0.8)
        tr, va = app & (B.t < coupe_val), app & (B.t >= coupe_val)
        pred = {}
        print(f"\n=== {ins} : apprentissage {int(tr.sum())} bougies, tranche d'arrêt {int(va.sum())} (dès {coupe_val:%d/%m/%Y}), contrôle {int(ctl.sum())}")
        for s in ("L", "S"):
            y = I[f"p1_{s}"] / risque
            ok = np.isfinite(y)
            m_tr, m_va = (tr & ok).values, (va & ok).values
            mod = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=31,
                                                min_samples_leaf=200, early_stopping=False, random_state=0)
            mod.fit(X[m_tr], y[m_tr])
            err = [np.mean((p - y[m_va]) ** 2) for p in mod.staged_predict(X[m_va])]
            best = int(np.argmin(err)) + 1
            mod = HistGradientBoostingRegressor(max_iter=best, learning_rate=0.05, max_leaf_nodes=31,
                                                min_samples_leaf=200, early_stopping=False, random_state=0).fit(X[m_tr], y[m_tr])
            p = mod.predict(X)
            p[~ok] = np.nan
            pred[s] = p
            seuil = np.nanpercentile(p[m_va], 98)
            pred[s + "_seuil"] = seuil
            m_ct = (ctl & ok).values
            rho, pv = spearmanr(p[m_ct], y[m_ct])
            dec = pd.qcut(p[m_ct], 10, labels=False, duplicates="drop")
            moy = pd.Series(y[m_ct]).groupby(dec).mean()
            print(f"  {s} : {best} itérations ; contrôle : Spearman {rho:+.4f} (p = {pv:.3g}) ; R moyen global {np.mean(y[m_ct]):+.4f} ;"
                  f" par décile de prédiction : " + " ".join(f"{v:+.3f}" for v in moy.values))
            lignes.append(dict(instrument=ins, sens=s, iterations=best, spearman=rho, p_spearman=pv,
                               r_moyen=np.mean(y[m_ct]), r_decile_haut=moy.values[-1], r_decile_bas=moy.values[0]))
        # stratégie témoin
        for per, m in (("construction (dans l'échantillon)", app), ("contrôle 2023-2024", ctl)):
            pl, ps = pred["L"], pred["S"]
            okL = (pl >= pred["L_seuil"]) & m.values
            okS = (ps >= pred["S_seuil"]) & m.values
            sens = np.where(okL & okS, np.where(pl >= ps, 1, -1), np.where(okL, 1, -1))
            idx = np.flatnonzero(okL | okS)
            sens = sens[idx]
            pris, ss, pn = sequence(I, idx, sens)
            r = mesures(pn)
            D = hasard(B, I, m.values, idx, sens, 1000, "A", rng)
            p = (np.sum(D.pnl >= r["pnl"]) + 1) / (len(D) + 1)
            print(f"  stratégie témoin, {per} : {r['n']} trades, {r['gain']:.1%}, {r['pnl']:,.0f} $ ({r['par_trade']:+.1f}/trade),"
                  f" baisse max {r['baisse_max']:,.0f} $ | hasard médian {D.pnl.median():,.0f} $ ; p = {p:.4f}")
            lignes.append(dict(instrument=ins, sens="strategie", periode=per, n=r["n"], gain=r["gain"], pnl=r["pnl"],
                               par_trade=r["par_trade"], baisse_max=r["baisse_max"], pnl_hasard_med=D.pnl.median(), p=p))
    pd.DataFrame(lignes).to_csv(os.path.join(os.path.dirname(__file__), "resultats_C1.csv"), index=False)


if __name__ == "__main__":
    main()
