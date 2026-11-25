"""25/11 — valeur réelle du bot (LUCIDBOTV2, MNQ 5 min) : 56 + GODLIKE (Dashator 1 h ET 4 h dans le sens, corps ≥ 0,025 ATR),
stop 3 ATR, objectif 2 ATR, 16 bougies, une position à la fois, 2 micros. Lecture graphique (o) contre alertes (b).
Période des exports fiable/5min : 17/10/2023 → 13/11/2026. Arrêt du jour après 2 pertes appliqué en option."""
import os, sys
import numpy as np, pandas as pd
ICI = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [ICI, os.path.join(ICI, "..", "complet")]
from decision56 import charger56
from moteur import issues, sequence, mesures
DEBUT, MILIEU = pd.Timestamp("2023-10-17"), pd.Timestamp("2025-05-01")
G = 0.025
def seq_stop2(B, I, idx, sens):
    """sequence + arrêt du jour (date de Chicago ≈ date Paris décalée de 7 h) après 2 pertes."""
    jour = (B.t - pd.Timedelta(hours=7)).dt.date.values
    pris, ss, pn = [], [], []; libre = -1; pertes = {}
    for i, d in zip(idx, sens):
        if i < libre or pertes.get(jour[i], 0) >= 2: continue
        p = I["p1_L"][i] if d > 0 else I["p1_S"][i]
        if not np.isfinite(p): continue
        pris.append(i); ss.append(d); pn.append(p)
        libre = I["lib_L"][i] if d > 0 else I["lib_S"][i]
        if p < 0: pertes[jour[i]] = pertes.get(jour[i], 0) + 1
    return np.array(pris), np.array(ss), np.array(pn)
for ins in ("MNQ", "MES"):
    B = charger56(ins, 5); I = issues(B, 3.0, 0.6667, 16); per = (B.t >= DEBUT).values
    for lec, c1, c4 in (("o", "o1", "o4"), ("b", "b1", "b4")):
        L = (B[f"go{lec}_L"].values == 1) & (B[c1].values >= G) & (B[c4].values >= G) & per
        S = (B[f"go{lec}_S"].values == 1) & (B[c1].values <= -G) & (B[c4].values <= -G) & per
        idx = np.flatnonzero(L | S); sens = np.where(L[idx], 1, -1)
        for nom, f in (("sans arrêt", sequence), ("arrêt 2 pertes", None)):
            pris, ss, pn = sequence(I, idx, sens) if f else seq_stop2(B, I, idx, sens)
            t = B.t.values[pris]
            for moit, m in (("H1", t < np.datetime64(MILIEU)), ("H2", t >= np.datetime64(MILIEU)), ("total", np.ones(len(t), bool))):
                r = mesures(pn[m], 2)
                print(f"{ins} {'graphique' if lec == 'o' else 'alertes  '} {nom:15s} {moit:5s} n={r['n']:4d} gagnants {r['gain']:.0%} P&L {r['pnl']:+8.0f} $ creux {r['baisse_max']:6.0f} $")
