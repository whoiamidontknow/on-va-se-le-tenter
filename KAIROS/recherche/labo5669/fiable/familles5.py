"""25/11 — programme 5 min (HYPOTHESES.md, commit 78ff118) : familles F1-F4 (définitions du 19/11), F5 (entrées seules)
et témoin C1, en MNQ et MES 5 min, 17/10/2023 → 13/11/2026, sélection H1 / contrôle H2 + plateau.

    uv run --with pandas --with openpyxl --with scikit-learn --with scipy python familles5.py
"""
import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [ICI, os.path.join(ICI, "..", "complet")]
from objectifs import prep, creux, FIN, AN, KS, RS, NS  # noqa: E402
from seuils import DEBUT, MILIEU  # noqa: E402
from moteur import issues, sequence, mesures, hasard  # noqa: E402
from familles import hypotheses, GEO  # noqa: E402

GEO = dict(GEO, F5=(2.0, 1.0, 16))
N_TIR, MIN_TRADES = 1000, 30
NTESTS = {"F1": 6, "F2": 10, "F3": 6, "F4": 44, "F5": 18}


def f5(B):
    g = lambda c: B[c].values.astype(bool)
    dc, dh = B.dirC.values, B.dirH.values
    dc1, dh1 = np.r_[np.nan, dc[:-1]], np.r_[np.nan, dh[:-1]]
    k1, k4 = B.k1.values, B.k4.values
    k1p = np.r_[np.nan, k1[:-1]]
    fib, fbas = B.fib.values, g("fib_bas")
    zone = (fib >= 0.5) & (fib <= 0.786)
    return {
        "SF": ("F5", g("sF_L"), g("sF_S")),
        "SM": ("F5", g("sM_L"), g("sM_S")),
        "HEI": ("F5", g("hei_L"), g("hei_S")),
        "DIR": ("F5", (dc == 1) & (dc1 != 1), (dc == -1) & (dc1 != -1)),
        "DIRH": ("F5", (dh == 1) & (dh1 != 1), (dh == -1) & (dh1 != -1)),
        "PIV": ("F5", B.pW.values <= -2, B.pW.values >= 2),
        "FIB": ("F5", ~fbas & zone, fbas & zone),
        "DET": ("F5", B.detD.values <= 0.5, B.detU.values <= 0.5),
        "DK": ("F5", (k1 > 0) & (k1p <= 0) & (k4 > 0), (k1 <= 0) & (k1p > 0) & (k4 <= 0)),
    }


def tester(B, I, mL, mS, per, refs, tirer=True):
    m = per & (mL ^ mS)
    idx = np.flatnonzero(m)
    sens = np.where(mL[idx], 1, -1)
    pris, ss, pn = sequence(I, idx, sens)
    r = mesures(pn)
    r["idx"], r["sens"] = idx, sens
    for ref in refs:
        r[f"p_{ref}"] = np.nan
        if tirer and r["n"] >= MIN_TRADES and r["pnl"] > 0:
            D = hasard(B, I, per, idx, sens, N_TIR, ref, np.random.default_rng(5669))
            r[f"p_{ref}"] = (np.sum(D.pnl >= r["pnl"]) + 1) / (len(D) + 1)
    return r


def voisins(geo):
    k, R, N = geo
    R = min(RS, key=lambda x: abs(x - R))
    i, j, l = KS.index(k), RS.index(R), NS.index(N)
    out = [(k, R, N)]
    for di, dj, dl in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
        a, b, c = i + di, j + dj, l + dl
        if 0 <= a < len(KS) and 0 <= b < len(RS) and 0 <= c < len(NS):
            out.append((KS[a], RS[b], NS[c]))
    return out


def familles():
    lignes, cand = [], []
    for ins in ("MNQ", "MES"):
        B = prep(ins, 5)
        I = {f: issues(B, *geo) for f, geo in GEO.items()}
        H = dict(hypotheses(B))
        H.update(f5(B))
        regimes = {"": np.ones(len(B), bool), "R1 vr>=1,2": B.vr.values >= 1.2, "R2 ADX>=25": B.adx.values >= 25}
        h1 = ((B.t >= DEBUT) & (B.t < MILIEU)).values
        h2 = (B.t >= MILIEU).values
        for h, (fam, mL, mS) in H.items():
            mL, mS = np.nan_to_num(mL).astype(bool), np.nan_to_num(mS).astype(bool)
            for reg, mr in regimes.items():
                if fam == "F5" and reg:
                    continue
                famille = fam if reg == "" else "F4"
                r = tester(B, I[fam], mL & mr, mS & mr, h1, "BL")
                seuil = 0.05 / NTESTS[famille]
                ok = r["n"] >= MIN_TRADES and r["pnl"] > 0 and r["p_B"] < seuil and r["p_L"] < seuil
                d = dict(instrument=ins, famille=famille, hypothese=h, regime=reg, H1_n=r["n"], H1_pnl=r["pnl"],
                         H1_gain=r["gain"], H1_pB=r["p_B"], H1_pL=r["p_L"], seuil_H1=seuil, candidat=ok)
                lignes.append(d)
                print(f"  {ins} {famille} {h:<5} {reg:<11} H1 : {r['n']:5d} tr {r['pnl']:>9,.0f} $ p_B {r['p_B']:.4f} p_L {r['p_L']:.4f}"
                      + ("  ← candidat" if ok else ""), flush=True)
                if ok:
                    cand.append((ins, famille, h, reg, mL & mr, mS & mr, d, GEO[fam]))
    T = pd.DataFrame(lignes)
    # contrôle H2 des candidats
    for ins, famille, h, reg, mL, mS, d, geo in cand:
        B = prep(ins, 5)
        h2 = (B.t >= MILIEU).values
        I = issues(B, *geo)
        r = tester(B, I, mL, mS, h2, "BL")
        seuil = 0.05 / len(cand)
        pv = []
        for g in voisins(geo):
            x = tester(B, issues(B, *g), mL, mS, h2, "", tirer=False)
            ans = (FIN - MILIEU).days / AN
            pv.append((x["pnl"], (x["pnl"] / ans) / x["baisse_max"] if x["baisse_max"] > 0 else np.nan))
        plateau = sum(p > 0 for p, _ in pv) >= 5 and np.nanmedian([rc for _, rc in pv]) > 0
        passe = r["pnl"] > 0 and r["p_B"] < seuil and r["p_L"] < seuil and plateau
        i = T.index[(T.instrument == ins) & (T.hypothese == h) & (T.regime == reg)][0]
        T.loc[i, ["H2_n", "H2_pnl", "H2_pB", "H2_pL", "plateau_pos", "passe"]] = [r["n"], r["pnl"], r["p_B"], r["p_L"],
                                                                                 sum(p > 0 for p, _ in pv), passe]
        print(f"  H2 {ins} {famille} {h} {reg} : {r['n']} tr {r['pnl']:+,.0f} $ p_B {r['p_B']:.4f} p_L {r['p_L']:.4f}"
              f" (seuil {seuil:.4f}) ; plateau {sum(p > 0 for p, _ in pv)}/{len(pv)} positifs → {'PASSE' if passe else 'non'}", flush=True)
    T.to_csv(os.path.join(ICI, "familles5_resultats.csv"), index=False)
    print(f"\nCandidats H1 : {len(cand)} sur {len(T)} tests")
    return T


def temoin():
    from scipy.stats import spearmanr
    from sklearn.ensemble import HistGradientBoostingRegressor
    from temoin import variables
    K, TPR, NBAR = 2.0, 1.0, 16
    out = []
    for ins in ("MNQ", "MES"):
        B = prep(ins, 5)
        I = issues(B, K, TPR, NBAR)
        X = variables(B)
        risque = K * B.atr.values * B.attrs["val_point"]
        marge = pd.Timedelta(hours=2)
        app = ((B.t >= DEBUT) & (B.t < MILIEU - marge)).values
        ctl = (B.t >= MILIEU).values
        coupe = B.t[app].quantile(0.8)
        tr, va = app & (B.t < coupe).values, app & (B.t >= coupe).values
        pred = {}
        for s in "LS":
            y = I[f"p1_{s}"] / risque
            ok = np.isfinite(y)
            mod = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=200,
                                                early_stopping=False, random_state=0).fit(X[tr & ok], y[tr & ok])
            err = [np.mean((p - y[va & ok]) ** 2) for p in mod.staged_predict(X[va & ok])]
            best = int(np.argmin(err)) + 1
            mod = HistGradientBoostingRegressor(max_iter=best, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=200,
                                                early_stopping=False, random_state=0).fit(X[tr & ok], y[tr & ok])
            p = mod.predict(X)
            p[~ok] = np.nan
            pred[s], pred[s + "_seuil"] = p, np.nanpercentile(p[va & ok], 98)
            rho, pv = spearmanr(p[ctl & ok], y[ctl & ok])
            print(f"  C1 {ins} {s} : {best} itérations, Spearman H2 {rho:+.4f} (p = {pv:.3g})", flush=True)
        for per, m in (("H1", app), ("H2", ctl)):
            okL, okS = (pred["L"] >= pred["L_seuil"]) & m, (pred["S"] >= pred["S_seuil"]) & m
            idx = np.flatnonzero(okL | okS)
            sens = np.where(okL & okS, np.where(pred["L"] >= pred["S"], 1, -1), np.where(okL, 1, -1))[idx]
            r = tester(B, I, np.isin(np.arange(len(B)), idx[sens > 0]), np.isin(np.arange(len(B)), idx[sens < 0]), m, "BL")
            out.append(dict(instrument=ins, periode=per, n=r["n"], pnl=r["pnl"], p_B=r["p_B"], p_L=r["p_L"]))
            print(f"  C1 {ins} stratégie {per} : {r['n']} tr {r['pnl']:+,.0f} $ p_B {r['p_B']:.4f} p_L {r['p_L']:.4f}", flush=True)
    pd.DataFrame(out).to_csv(os.path.join(ICI, "temoin5_resultats.csv"), index=False)


if __name__ == "__main__":
    familles()
    temoin()
