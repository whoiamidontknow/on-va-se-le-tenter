"""Jalon B : le moteur générique doit redonner simu56 en lecture k (validé contre le testeur via o / b)
sur le 56 (3 ATR, 0,6667 R, 16 bougies), à partir des bits go_L / go_S du Relevé complet."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "dataset"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from releve_complet import charger as cc  # noqa: E402
from releve import charger as c5  # noqa: E402
from simu56 import simuler  # noqa: E402
from moteur import issues, sequence, mesures  # noqa: E402

for ins in ("MNQ", "MES"):
    B = cc(ins)
    I = issues(B, 3.0, 0.6667, 16)
    idx = np.flatnonzero(((B.go_L == 1) | (B.go_S == 1)).values)
    sens = np.where(B.go_L.values[idx] == 1, 1, -1)
    pris, ss, pn = sequence(I, idx, sens)
    M = pd.DataFrame({"t1": B.t.values[pris + 1], "sens": np.where(ss > 0, "L", "S"), "pnl": pn * 2,
                      "raison": np.where(ss > 0, I["r_L"][pris], I["r_S"][pris])})
    M["raison"] = M.raison.map({0: "stop", 1: "objectif", 2: "temps", 3: "fin"})
    S = simuler(c5(ins, controle=False), lecture="k")
    c = M.merge(S, on="t1", how="outer", suffixes=("_m", "_s"), indicator=True)
    idem = (c._merge == "both") & (c.sens_m == c.sens_s) & (c.raison_m == c.raison_s)
    both = (c._merge == "both") & (c.sens_m == c.sens_s)
    d = (c.pnl_m - c.pnl_s)[both]
    print(f"{ins} : moteur {len(M)} trades, simu56 k {len(S)} ; identiques (bougie, sens, sortie) {idem.sum()} ;"
          f" seulement moteur {int((c._merge == 'left_only').sum())}, seulement simu56 {int((c._merge == 'right_only').sum())} ;"
          f" P&L moteur {M.pnl.sum():,.0f} $ / simu56 {S.pnl.sum():,.0f} $ ; trades identiques avec |écart P&L| > 1 $ : {int((d.abs() > 1).sum())}")
    print(f"   dont sorties fin à ouverture estimée par simu56 : {int((c[both & (d.abs() > 1)].approx == True).sum())}")
    x = c[both & (d.abs() > 1) & (c.approx != True)]
    if len(x):
        print(x[["t1", "sens_m", "raison_m", "raison_s", "pnl_m", "pnl_s", "approx"]].head(8).to_string(index=False))
