"""25/11 — contrôle au hasard du candidat 5 min MNQ (seuils 0, 70, 75 %), sur chaque moitié de la période de Jeremy.
Références (complet/moteur.hasard) : mêmes bougies candidates (hors fin), même répartition horaire, même nombre de
trades, même géométrie (3 ATR, 0,6667 R, 16 bougies), une position à la fois, 2 contrats :
  A = bougies et sens au hasard (même part de longs) ; B = sens du déclencheur de la bougie ; L = long seulement.
p = (nombre de tirages au moins aussi bons + 1) / (N + 1), sur le P&L net.
"""
import numpy as np
import pandas as pd
from seuils import charger56, DECL, tables, issues, sequence, DEBUT, MILIEU, QTY
from moteur import hasard

N = 1000
B = charger56("MNQ", 5); at = dict(B.attrs)
B = B[B.t >= DEBUT - pd.Timedelta(days=3)].reset_index(drop=True); B.attrs.update(at)
trig = B[[f"{d}_{s}" for d in DECL for s in "LS"]].values.any(axis=1)
_, score = tables(B, trig & (B.t >= DEBUT).values & (B.t < MILIEU).values)
I = issues(B, 3.0, 0.6667, 16)
L, S = B.gob_L.values == 1, B.gob_S.values == 1
lignes = []
for s in (0, 70, 75):
    for moitie, per in (("1re moitié", (B.t >= DEBUT) & (B.t < MILIEU)), ("2de moitié", B.t >= MILIEU)):
        per = per.values
        f = per & ((score >= s / 100) if s else True)
        idx = np.flatnonzero(f & (L | S))
        sens = np.where(L[idx], 1, -1)
        pris, ss, pn = sequence(I, idx, sens)
        obs = pn.sum() * QTY
        d = dict(seuil=s, moitie=moitie, trades=len(pris), pnl=obs)
        for ref in "ABL":
            h = hasard(B, I, per, idx, sens, n_tir=N, ref=ref, rng=np.random.default_rng(5669))
            d[f"p_{ref}"] = ((h.pnl >= obs).sum() + 1) / (N + 1)
            d[f"med_{ref}"] = h.pnl.median()
            d[f"n_{ref}"] = h.n.mean()
        lignes.append(d)
        print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()}, flush=True)
pd.DataFrame(lignes).to_csv("resultats_hasard5.csv", index=False)
