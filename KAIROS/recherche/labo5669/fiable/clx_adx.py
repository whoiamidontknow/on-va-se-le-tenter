"""CLX-ADX (HYPOTHESES.md, commit e60bd3d) : test unique sur H2 de MNQ 5 min climax + ADX ≥ 25, géométrie F2."""
import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [ICI, os.path.join(ICI, "..", "complet")]
from objectifs import prep, FIN, AN  # noqa: E402
from seuils import MILIEU  # noqa: E402
from moteur import issues, sequence, mesures, hasard  # noqa: E402

B = prep("MNQ", 5)
I = issues(B, 1.5, 1.0, 8)
per = (B.t >= MILIEU).values
adx = B.adx.values >= 25
mL, mS = B.clx_L.values.astype(bool) & adx, B.clx_S.values.astype(bool) & adx
m = per & (mL ^ mS)
idx = np.flatnonzero(m)
sens = np.where(mL[idx], 1, -1)
pris, ss, pn = sequence(I, idx, sens)
r = mesures(pn)                                     # 2 contrats
p = {}
for ref in "BL":
    D = hasard(B, I, per, idx, sens, 1000, ref, np.random.default_rng(5669))
    p[ref] = (np.sum(D.pnl >= r["pnl"]) + 1) / 1001
ans = (FIN - MILIEU).days / AN
lib = np.minimum(np.where(ss > 0, I["lib_L"][pris], I["lib_S"][pris]), len(B) - 1)
tx = pd.to_datetime(B.t.values[lib])
jour = pd.Series(pn).groupby(tx.date).sum()           # 1 contrat
dd1 = r["baisse_max"] / 2
n = int(np.floor(min(8000 / dd1, 4000 / max(-jour.min(), 1))))
mois = pd.Series(pn).groupby(tx.to_period("M")).sum()
succes = r["pnl"] > 0 and p["B"] < 0.05 and p["L"] < 0.05
print(f"H2 : {r['n']} trades, gagnants {r['gain']:.1%}, P&L {r['pnl']:+,.0f} $ (2 contrats) ; p_B {p['B']:.4f} p_L {p['L']:.4f} → {'RÉUSSI' if succes else 'ÉCHOUÉ'}")
print(f"gain par trade et par contrat {pn.mean():+.2f} $ ; pire creux {r['baisse_max']:,.0f} $ ; R/C {(r['pnl'] / ans) / r['baisse_max']:.2f} ;"
      f" taille FTMO {n} micros → {100 * n * pn.sum() / ans / 100000:.1f} % par an ; mois positifs {int((mois > 0).sum())}/{len(mois)}")
