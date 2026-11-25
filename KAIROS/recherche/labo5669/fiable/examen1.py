"""EXAMEN-1 (HYPOTHESES.md), écrit et commité AVANT le dépôt de l'export. Un seul passage, aucun réglage modifié ensuite.

Règle gelée : 56 en lecture alertes (b), MNQ 5 min, score de fiabilité p1 × p4 ≥ 70 % avec les tables 5 min FIXES de
2c79a6a (= Strat5669_FIABLE a9301a8, recopiées ci-dessous, jamais réapprises), part écoulée calculée comme le Pine
(heure de Paris), score inconnu = pas de trade ; sorties du 56 (3 ATR, 0,6667 R, 16 bougies), une position à la fois,
2 contrats, moteur complet/moteur.py.
Données : Relevé complet MNQ 5 min, fiable/5min-avant/ (un ou plusieurs morceaux, concaténés, doublons d'horodatage
retirés). Décisions du 07/01/2019 00:00 (une semaine de mise en route) au 16/10/2023 00:00 (début de la période de
recherche, exclue).
Critère (α = 0,05, un seul test) : P&L > 0 ET p_B < 0,05 ET p_L < 0,05, avec moteur.hasard (1 000 tirages, graine 5669,
mêmes heures, même nombre de trades, mêmes sorties) ; p = (tirages ≥ P&L observé + 1) / 1 001.
Rapporté sans être un critère : R/C, % annuel à la taille FTMO 100k dans les règles, P&L par année, fantômes.

    uv run --with pandas --with openpyxl python examen1.py [dossier]      (défaut : ~/ERGON/KAIROS-data/fiable/5min-avant)
"""
import glob
import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [ICI, os.path.join(ICI, "..", "complet"), os.path.expanduser("~/ERGON/on-va-se-le-tenter/KAIROS/dataset")]
from releve_complet import charger  # noqa: E402
from decision56 import complete56  # noqa: E402
from moteur import issues, sequence, hasard, mesures  # noqa: E402

DEBUT, FIN = pd.Timestamp("2019-01-07"), pd.Timestamp("2023-10-16")
SEUIL, QTY, N_TIR = 0.70, 2, 1000
Q1 = np.array([0.060, 0.155, 0.324, 0.637])
T1 = np.array([58.20, 59.98, 68.84, 81.34, 73.06, 78.27, 88.87, 94.97, 88.65, 93.97, 94.71, 99.46, 96.32, 97.87,
               99.20, 99.87, 98.81, 99.10, 99.76, 100.00]).reshape(5, 4) / 100
Q4 = np.array([0.107, 0.217, 0.360, 0.604])
T4 = np.array([60.49, 72.60, 74.51, 80.93, 78.48, 86.56, 89.39, 94.43, 90.25, 92.98, 95.41, 97.72, 96.40, 97.84,
               99.14, 99.57, 99.14, 99.87, 99.87, 100.00]).reshape(5, 4) / 100


def score(B):
    """Même calcul que f_fiP du Pine : ligne = premier quintile ≥ |v| (sinon 5e), colonne = part écoulée ≤ .26/.51/.76/1."""
    tc = B.t + pd.Timedelta(minutes=5)
    m, h = tc.dt.minute.values, tc.dt.hour.values
    q = (h % 4) * 60 + m
    e = {"1": np.where(m == 0, 1.0, m / 60), "4": np.where(q == 0, 1.0, q / 240)}
    p = {}
    for tf, qa, tab in (("1", Q1, T1), ("4", Q4, T4)):
        v = B[f"b{tf}"].values
        a = np.abs(v)
        r = np.minimum(np.searchsorted(qa, a, side="left"), 4)
        c = np.digitize(e[tf], [.26, .51, .76], right=True)
        p[tf] = np.where(np.isfinite(v) & (a <= 99), tab[r, c], np.nan)
    return p["1"] * p["4"]


def charger_examen(dossier):
    fs = sorted(f for f in glob.glob(os.path.join(dossier, "*.xlsx")) if "_MNQ1!_" in f)
    if not fs:
        sys.exit(f"aucun export MNQ dans {dossier}")
    parts = [charger("MNQ", fichier=f) for f in fs]
    for f, P in zip(fs, parts):
        if P.attrs["unite"] != 5:
            sys.exit(f"{os.path.basename(f)} : unité {P.attrs['unite']} min, 5 attendue")
        print(f"  {os.path.basename(f)} : {len(P)} bougies, {P.t.min():%d/%m/%Y %H:%M} → {P.t.max():%d/%m/%Y %H:%M},"
              f" commentaires coupés {P.attrs['coupes']}")
    B = pd.concat(parts).sort_values("t").drop_duplicates("t").reset_index(drop=True)
    B.attrs.update(parts[0].attrs)
    return complete56(B)


def main(dossier):
    B = charger_examen(dossier)
    B["score"] = score(B)
    per = ((B.t >= DEBUT) & (B.t < FIN)).values
    f = per & (B.score.values >= SEUIL)
    L, S = (B.gob_L.values == 1) & f, (B.gob_S.values == 1) & f
    idx = np.flatnonzero(L | S)
    sens = np.where(L[idx], 1, -1)
    I = issues(B, 3.0, 0.6667, 16)
    pris, ss, pn = sequence(I, idx, sens)
    pnl = pn * QTY
    obs = pnl.sum()
    res = {}
    for ref in "BL":
        h = hasard(B, I, per, idx, sens, n_tir=N_TIR, ref=ref, rng=np.random.default_rng(5669))
        res[ref] = (((h.pnl.values >= obs).sum() + 1) / (N_TIR + 1), float(h.pnl.median()))
    m = mesures(pn, QTY)
    t = B.t.values[pris]
    ans = (FIN - DEBUT).days / 365.25
    rc = (obs / ans) / m["baisse_max"] if m["baisse_max"] > 0 else np.nan
    goo = np.where(ss > 0, B.goo_L.values[pris], B.goo_S.values[pris])
    lib = np.minimum(np.where(ss > 0, I["lib_L"][pris], I["lib_S"][pris]), len(B) - 1)
    jour = pd.Series(pn).groupby(pd.to_datetime(B.t.values[lib]).date).sum()      # 1 contrat
    dd1 = m["baisse_max"] / QTY
    n_ftmo = int(np.floor(min(8000 / dd1 if dd1 > 0 else 99, 4000 / max(-jour.min(), 1))))
    an = pd.Series(pnl).groupby(pd.to_datetime(t).year).agg(["count", "sum"])
    succes = bool(obs > 0 and res["B"][0] < 0.05 and res["L"][0] < 0.05)
    print(f"\nEXAMEN-1 — MNQ 5 min, {DEBUT:%d/%m/%Y} → {FIN:%d/%m/%Y}, seuil 70 %, 2 contrats")
    print(f"  trades {len(pris)} ({len(pris) / (ans * 12):.1f} par mois), gagnants {m['gain']:.1%}, P&L {obs:+,.0f} $")
    print(f"  hasard B : p = {res['B'][0]:.4f} (médiane {res['B'][1]:+,.0f} $) ; hasard L : p = {res['L'][0]:.4f} (médiane {res['L'][1]:+,.0f} $)")
    print(f"  CRITÈRE : {'RÉUSSI' if succes else 'ÉCHOUÉ'}")
    print(f"  (hors critère) pire creux {m['baisse_max']:,.0f} $, R/C {rc:.2f}, fantômes {np.mean(goo != 1):.0%},"
          f" taille FTMO 100k {n_ftmo} micros → {100 * n_ftmo * (obs / QTY) / ans / 100000:.1f} % par an")
    print("  P&L par année :\n" + an.to_string())
    return succes


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/ERGON/KAIROS-data/fiable/5min-avant"))
