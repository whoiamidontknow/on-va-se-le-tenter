"""Validation 15 min : décisions o / b reconstituées sur le Relevé complet contre go56 / go56b du Relevé 5669,
bougie par bougie, sur la période commune."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser("~/ERGON/on-va-se-le-tenter/KAIROS/dataset"))
from decision56 import charger56  # noqa: E402
from releve import charger as c5  # noqa: E402

for ins in ("MNQ", "MES"):
    B = charger56(ins, 15).set_index("t")
    R = c5(ins, controle=False)
    R = R[(R.t1 >= B.index.min() + pd.Timedelta(minutes=15)) & (R.t1 <= B.index.max())]
    # Relevé 5669 : t1 = bougie d'entrée (ouverture) ; la décision est prise sur la bougie précédente
    R["tdec"] = R.t1 - pd.Timedelta(minutes=15)
    R = R.set_index("tdec")
    debut, fin = R.index.min(), R.index.max()
    Bc = B.loc[debut:fin]
    for lec, col in (("o", "go56"), ("b", "go56b")):
        n_tot, n_ok, det = 0, 0, []
        for s in "LS":
            r = R[f"{col}_{s}"].reindex(Bc.index).fillna(0).astype(int)
            m = Bc[f"go{lec}_{s}"].astype(int)
            pos = (r == 1) | (m == 1)
            n_tot += pos.sum(); n_ok += (pos & (r == m)).sum()
            det.append(f"{s}: 5669 {int(r.sum())} / complet {int(m.sum())} / communs {int(((r == 1) & (m == 1)).sum())}")
        print(f"{ins} lecture {lec} ({col}) {debut:%d/%m/%Y} → {fin:%d/%m/%Y} : égalité sur les bougies où l'un des deux décide "
              f"{n_ok}/{n_tot} = {n_ok / n_tot:.1%} ; " + " ; ".join(det))
