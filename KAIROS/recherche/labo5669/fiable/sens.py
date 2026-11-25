"""Répartition long / short du gain des alertes pour quelques seuils (contrôle de la dérive haussière)."""
import sys
import numpy as np
import pandas as pd
from seuils import charger56, DECL, tables, issues, sequence, DEBUT, MILIEU, QTY

for u, ins, seuils in ((15, "MNQ", (0, 75)), (15, "MES", (80, 85)), (5, "MNQ", (0, 70, 75, 85)), (5, "MES", (0, 75))):
    B = charger56(ins, u); at = dict(B.attrs)
    B = B[B.t >= DEBUT - pd.Timedelta(days=3)].reset_index(drop=True); B.attrs.update(at)
    trig = B[[f"{d}_{s}" for d in DECL for s in "LS"]].values.any(axis=1)
    _, score = tables(B, trig & (B.t >= DEBUT).values & (B.t < MILIEU).values)
    I = issues(B, 3.0, 0.6667, 16)
    for s in seuils:
        f = (B.t >= DEBUT).values & ((score >= s / 100) if s else True)
        L, S = B.gob_L.values == 1, B.gob_S.values == 1
        idx = np.flatnonzero(f & (L | S))
        pris, ss, pn = sequence(I, idx, np.where(L[idx], 1, -1))
        h1 = B.t.values[pris] < MILIEU
        out = []
        for nom, m in (("1re", h1), ("2de", ~h1)):
            out.append(f"{nom} : longs {int((m & (ss > 0)).sum())} {pn[m & (ss > 0)].sum() * QTY:+,.0f} $, shorts {int((m & (ss < 0)).sum())} {pn[m & (ss < 0)].sum() * QTY:+,.0f} $")
        print(f"{u} min {ins} seuil {s} — " + " | ".join(out))
