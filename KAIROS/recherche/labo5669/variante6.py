"""Variante 6 (idée 6) : géométrie de sortie du 56 en lecture b.
stop 1,5 / 2 / 3 ATR × objectif 0,5 / 0,67 / 1 / 1,5 R × sortie au temps 8 / 16 bougies = 24 cases.
Construction 2019-2022, contrôle 2023-2024. Chaque case est comparée à des entrées au hasard (réf. B)
qui sortent avec la MÊME géométrie. Correction de Bonferroni sur 48 tests (24 cases × 2 instruments).
Retenue seulement si les cases voisines forment un plateau.

Issues calculées en bloc (numpy) avec les règles de simu56.un_trade ; la case (3 ATR, 0,6667 R, 16)
doit redonner exactement les issues de banc.issues (contrôle en tête de main()).
Sortie au temps après N < 16 bougies : remplie à l'ouverture de la bougie N + 1, connue si une ligne
du relevé y commence ou y finit, sinon estimée au milieu de la bougie (compté).

    uv run -q --with pandas --with openpyxl python variante6.py
"""
import itertools
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "dataset"))
from releve import charger  # noqa: E402
from banc import issues, sequence, mesures, tirages  # noqa: E402
from simu56 import ouvertures, COMM, TICK  # noqa: E402

COUPURE = pd.Timestamp("2023-01-01")
STOPS, OBJS, TEMPS = (1.5, 2.0, 3.0), (0.5, 0.6667, 1.0, 1.5), (8, 16)
QUART = np.timedelta64(15, "m")
MINUTE = np.timedelta64(1, "m")


def issues_geo(C, opn, k_atr, tpr, tbar, vp):
    """P&L par contrat, raison, heure de liberté, pour chaque ligne de C et chaque sens."""
    n = len(C)
    H = C[[f"h{i}" for i in range(1, 17)]].values
    Lw = C[[f"l{i}" for i in range(1, 17)]].values
    o1, o17 = C.o1.values, C.o17.values
    t1 = C.t1.values.astype("datetime64[ns]")
    f = np.nan_to_num(C.f.values).astype(int)
    dist = C.sl.values * k_atr / 3.0
    fin = (f > 0) & (f <= tbar)
    dern = np.where(fin, f, tbar)                       # dernière bougie surveillée
    # prix d'ouverture de la bougie de sortie au marché (dern + 1)
    j = dern + 1
    tj = t1 + (j - 1) * QUART
    px_o = np.where(j == 17, o17, pd.Series(pd.DatetimeIndex(tj)).map(opn).values.astype(float))
    approx = np.isnan(px_o)
    jj = np.minimum(j, 16) - 1
    mid = o1 + (H[np.arange(n), jj] + Lw[np.arange(n), jj]) / 2 * TICK
    px_o = np.where(approx, mid, px_o)
    out = {}
    for d, s in ((1, "L"), (-1, "S")):
        fill = o1 + d * TICK
        sortie = np.full(n, np.nan)
        raison = np.full(n, "", dtype=object)
        kx = np.zeros(n, dtype=int)
        ouvert = np.ones(n, dtype=bool)
        for k in range(1, 17):
            act = ouvert & (k <= dern)
            if not act.any():
                break
            if k == 1:
                nsl = np.maximum(1, np.round(dist / TICK))
                ntp = np.maximum(1, np.round(tpr * dist / TICK))
            else:
                nsl = np.ceil(dist / TICK - 1e-9)
                ntp = np.ceil(tpr * dist / TICK - 1e-9)
            stop, tp = fill - d * nsl * TICK, fill + d * ntp * TICK
            hi, lo = o1 + H[:, k - 1] * TICK, o1 + Lw[:, k - 1] * TICK
            ts = act & ((lo <= stop) if d > 0 else (hi >= stop))
            tt = act & ((hi >= tp) if d > 0 else (lo <= tp)) & ~ts     # stop d'abord si les deux
            sortie[ts], raison[ts], kx[ts] = (stop - d * TICK)[ts], "stop", k
            sortie[tt], raison[tt], kx[tt] = tp[tt], "objectif", k
            ouvert &= ~(ts | tt)
        m = ouvert
        sortie[m] = (px_o - d * TICK)[m]
        raison[m] = np.where(fin[m], "fin", "temps")
        lib = np.where(m, tj + MINUTE, t1 + kx * QUART)
        out[f"p1_{s}"] = (sortie - fill) * d * vp - 2 * COMM
        out[f"r_{s}"] = raison
        out[f"lib_{s}"] = lib
    return out, approx


def main():
    rng = np.random.default_rng(5669)
    lignes = []
    for ins in ("MNQ", "MES"):
        R = charger(ins, controle=False)
        vp = R.attrs["val_point"]
        C0 = issues(R)
        opn = ouvertures(R)
        g, _ = issues_geo(C0, opn, 3.0, 0.6667, 16, vp)
        ecart = max(np.nanmax(np.abs(g["p1_L"] - C0.p1_L.values)), np.nanmax(np.abs(g["p1_S"] - C0.p1_S.values)))
        same_lib = (pd.DatetimeIndex(g["lib_L"]) == pd.DatetimeIndex(C0.lib_L)).mean()
        print(f"\n{ins} : contrôle du calcul en bloc contre simu56 (case du 56) : écart max {ecart:.4f} $ ; heures de liberté identiques {same_lib:.1%}")
        for k_atr, tpr, tbar in itertools.product(STOPS, OBJS, TEMPS):
            g, approx = issues_geo(C0, opn, k_atr, tpr, tbar, vp)
            C1 = C0.copy()
            for c, v in g.items():
                C1[c] = v
            for per, m in (("construction", C1.t1 < COUPURE), ("contrôle", C1.t1 >= COUPURE)):
                C = C1[m].reset_index(drop=True)
                idx = np.flatnonzero(((C.go56b_L == 1) | (C.go56b_S == 1)).values)
                sens = np.where(C.go56b_L.values[idx] == 1, 1, -1)
                r = mesures(sequence(C, idx, sens))
                D, _ = tirages(C, idx, sens, r["n"], "B", rng)
                p = (np.sum(D.pnl >= r["pnl"]) + 1) / (len(D) + 1)
                lignes.append(dict(instrument=ins, stop=k_atr, obj=tpr, temps=tbar, periode=per, n=r["n"], gain=r["gain"],
                                   pnl=r["pnl"], par_trade=r["par_trade"], baisse_max=r["baisse_max"],
                                   pnl_hasard_med=D.pnl.median(), p=p, approx_temps=int(approx[m.values].sum())))
            a, b = lignes[-2], lignes[-1]
            print(f"  stop {k_atr} ATR · obj {tpr:g} R · {tbar:2d} b : construction {a['n']} tr {a['gain']:.1%} {a['pnl']:>8,.0f} $ p={a['p']:.3f}"
                  f" | contrôle {b['n']} tr {b['gain']:.1%} {b['pnl']:>8,.0f} $ p={b['p']:.3f}")
    T = pd.DataFrame(lignes)
    T.to_csv(os.path.join(os.path.dirname(__file__), "resultats_variante6.csv"), index=False)


if __name__ == "__main__":
    main()
