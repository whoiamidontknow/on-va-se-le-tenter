"""PIVC-K4 (HYPOTHESES.md) : test unique sur H2, MNQ 15 min cassure de pivot + k4 ; MES 15 min pour information."""
import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [ICI, os.path.join(ICI, "..", "complet")]
from objectifs import prep, FIN, AN  # noqa: E402
from seuils import MILIEU  # noqa: E402
from niveaux import evenements_p1, contextes, issues_gen, GEO_P1, tester  # noqa: E402

for ins in ("MNQ", "MES"):
    B = prep(ins, 15)
    L, S = evenements_p1(B)["PIV-C"]
    cL, cS = contextes(B)["k4"]
    I = issues_gen(B, *GEO_P1)
    h2 = (B.t >= MILIEU).values
    r = tester(B, I, L & cL, S & cS, h2, "BL")
    pris, ss, pn = r["pris"], r["ss"], r["pn"]
    ans = (FIN - MILIEU).days / AN
    lib = np.minimum(np.where(ss > 0, I["lib_L"][pris], I["lib_S"][pris]), len(B) - 1)
    tx = pd.to_datetime(B.t.values[lib])
    jour = pd.Series(pn).groupby(tx.date).sum()
    dd1 = r["baisse_max"] / 2
    n_f = int(np.floor(min(8000 / dd1, 4000 / max(-jour.min(), 1)))) if dd1 > 0 else 0
    n_t = int(np.floor(1600 / dd1)) if dd1 > 0 else 0
    mois = pd.Series(pn).groupby(tx.to_period("M")).sum()
    succes = r["pnl"] > 0 and r["p_B"] < 0.05 and r["p_L"] < 0.05
    print(f"{ins} 15 min H2 : {r['n']} trades ({r['n'] / (ans * 12):.1f}/mois), gagnants {r['gain']:.1%}, P&L {r['pnl']:+,.0f} $ (2 contrats),"
          f" p_B {r['p_B']:.4f} p_L {r['p_L']:.4f} → {'RÉUSSI' if succes else 'ÉCHOUÉ'}" + ("" if ins == "MNQ" else " (information)"))
    print(f"   creux {r['baisse_max']:,.0f} $, R/C {r['rc']:.2f} ; FTMO {n_f} micros → {100 * n_f * pn.sum() / ans / 100000:.1f} %/an ;"
          f" Tradeify {n_t} micros → {100 * n_t * pn.sum() / ans / 50000:.1f} %/an ; mois positifs {int((mois > 0).sum())}/{len(mois)}")
    if ins == "MNQ" and succes:
        pd.DataFrame({"decision": B.t.values[pris], "sortie": tx, "sens": np.where(ss > 0, "L", "S"),
                      "pnl_1_contrat": pn}).to_csv(os.path.join(ICI, "pivc_k4_trades_H2.csv"), index=False)
