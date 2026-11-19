"""Variantes autorisées par DAEMON le 19/11 : construction 2019-2022, contrôle 2023-2024 (scellé fermé).

V1  : Dashator 1 h / 4 h lu sur la dernière bougie TERMINÉE (k1/k4, logique des préréglages 76/77).
V2b : lecture direct (b) + entrée seulement si la bougie signal clôt à hh:00 (la 1 h vient de finir).
V2k : lecture k + bougie signal à hh:00 (préréglage 76).
Références : le 56 en lecture b (ce que voient les alertes, étape 5) et 1 000 tirages au hasard
(réf. B : sens du déclencheur), tirés parmi les MÊMES bougies candidates que la variante (pour V2 :
seulement les bougies à hh:00), avec la même répartition horaire et le même nombre de trades.

    uv run -q --with pandas --with openpyxl python variantes.py
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from banc import issues, sequence, mesures, tirages  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "dataset"))
from releve import charger  # noqa: E402

COUPURE = pd.Timestamp("2023-01-01")
VARIANTES = {
    "56 b (référence alertes)": ("b", False),
    "V1 k1/k4": ("k", False),
    "V2b b + hh:00": ("b", True),
    "V2k k + hh:00": ("k", True),
}


def choix(C, lecture, godlike=False):
    gl, gs = ("go56_L", "go56_S") if lecture == "o" else (f"go56{lecture}_L", f"go56{lecture}_S")
    m = (C[gl] == 1) | (C[gs] == 1)
    if godlike:
        g = C[f"gd_{lecture}"]
        m &= ((C[gl] == 1) & (g == 1)) | ((C[gs] == 1) & (g == -1))
    idx = np.flatnonzero(m.values)
    return idx, np.where(C[gl].values[idx] == 1, 1, -1)


def main():
    rng = np.random.default_rng(5669)
    lignes = []
    for ins in ("MNQ", "MES"):
        C0 = issues(charger(ins, controle=False))
        # la bougie SIGNAL clôt à hh:00 <=> la bougie de remplissage t1 ouvre à hh:00
        for nom, (lec, hh) in VARIANTES.items():
            for gl in (False, True):
                for per, m in (("construction 2019-2022", C0.t1 < COUPURE), ("contrôle 2023-2024", C0.t1 >= COUPURE)):
                    C = C0[m & ((C0.t1.dt.minute == 0) if hh else True)].reset_index(drop=True)
                    idx, sens = choix(C, lec, gl)
                    m5 = mesures(sequence(C, idx, sens))
                    if m5["n"] < 20:
                        p = np.nan
                        D = pd.DataFrame([dict(pnl=np.nan, gain=np.nan)])
                    else:
                        D, _ = tirages(C, idx, sens, m5["n"], "B", rng)
                        p = (D.pnl >= m5["pnl"]).mean()
                    L = dict(instrument=ins, variante=nom, trades="GODLIKE" if gl else "tous", periode=per, n=m5["n"],
                             gain=m5["gain"], pnl=m5["pnl"], par_trade=m5["par_trade"], baisse_max=m5["baisse_max"],
                             pnl_hasard_med=D.pnl.median(), gain_hasard_med=D.gain.median(), p_hasard=p)
                    lignes.append(L)
                    print(f"{ins} · {nom:<24} · {L['trades']:<7} · {per:<22} : {m5['n']:4d} trades, {m5['gain']:.1%}, "
                          f"{m5['pnl']:>9,.0f} $ ({m5['par_trade']:+.1f}/trade), baisse max {m5['baisse_max']:>7,.0f} | hasard médian "
                          f"{D.pnl.median():>8,.0f} $ ; part >= : {p:.3f}")
    T = pd.DataFrame(lignes)
    T.to_csv(os.path.join(os.path.dirname(__file__), "resultats_variantes_1_2.csv"), index=False)
    return T


if __name__ == "__main__":
    main()
