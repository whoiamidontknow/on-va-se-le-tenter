"""Variante 3 (idée 3) : tri des déclencheurs du 56 en lecture b.
Pour chaque instrument, sens et déclencheur (F Signator fort, M moyen, H Heishinator, T trendline,
N niveau, C climax, D divergence) : trades du 56 b dont la bougie signal porte ce déclencheur dans le
sens du trade, enchaînés « une position à la fois », contre 1 000 tirages au hasard (réf. B).
Construction 2019-2022 ; seuil de Bonferroni 0,05 / (7 × 2 × 2) = 0,0018 ; les déclencheurs retenus
forment un 56 b restreint, contrôlé sur 2023-2024 (p < 0,05 / nombre de variantes contrôlées).

    uv run -q --with pandas --with openpyxl python variante3.py
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "dataset"))
from releve import charger  # noqa: E402
from banc import issues, sequence, mesures, tirages  # noqa: E402

COUPURE = pd.Timestamp("2023-01-01")
DECL = "FMHTNCD"
N_TESTS = len(DECL) * 2 * 2
SEUIL = 0.05 / N_TESTS


def subset(C, sens_s, x):
    g = C[f"go56b_{sens_s}"] == 1
    if x is not None:
        g &= C[f"d_{sens_s}"].fillna("").str.contains(x)
    return g


def evaluer(C, masque_L, masque_S, rng, n_tir=1000):
    m = masque_L | masque_S
    idx = np.flatnonzero(m.values)
    sens = np.where(masque_L.values[idx], 1, -1)
    r = mesures(sequence(C, idx, sens))
    if r["n"] < 20:
        return r, np.nan, np.nan
    D, _ = tirages(C, idx, sens, r["n"], "B", rng)
    return r, (np.sum(D.pnl >= r["pnl"]) + 1) / (len(D) + 1), D.pnl.median()


def main():
    rng = np.random.default_rng(5669)
    lignes = []
    for ins in ("MNQ", "MES"):
        C0 = issues(charger(ins, controle=False))
        A = C0[C0.t1 < COUPURE].reset_index(drop=True)
        V = C0[C0.t1 >= COUPURE].reset_index(drop=True)
        retenus = []
        print(f"\n{ins} — construction 2019-2022 (seuil corrigé {SEUIL:.4f})")
        for s in ("L", "S"):
            vide = pd.Series(False, index=A.index)
            for x in DECL:
                mL = subset(A, "L", x) if s == "L" else vide
                mS = subset(A, "S", x) if s == "S" else vide
                r, p, med = evaluer(A, mL, mS, rng)
                ok = p == p and p < SEUIL
                if ok:
                    retenus.append((s, x))
                lignes.append(dict(instrument=ins, sens=s, declencheur=x, periode="construction", n=r["n"], gain=r["gain"],
                                   pnl=r["pnl"], par_trade=r["par_trade"], p=p, pnl_hasard_med=med, retenu=ok))
                print(f"  {s} {x} : {r['n']:4d} trades, {r['gain'] if r['n'] else float('nan'):.1%}, {r['pnl']:>8,.0f} $"
                      f" ({r['par_trade'] if r['n'] else float('nan'):+.1f}/trade) | p = {p:.3f}{'  ← retenu' if ok else ''}")
        if retenus:
            mL = pd.Series(False, index=V.index)
            mS = pd.Series(False, index=V.index)
            for s, x in retenus:
                if s == "L":
                    mL |= subset(V, "L", x)
                else:
                    mS |= subset(V, "S", x)
            r, p, med = evaluer(V, mL, mS, rng, 2000)
            lignes.append(dict(instrument=ins, sens="+".join(s for s, _ in retenus), declencheur="+".join(x for _, x in retenus),
                               periode="contrôle", n=r["n"], gain=r["gain"], pnl=r["pnl"], par_trade=r["par_trade"], p=p,
                               pnl_hasard_med=med, retenu=p < 0.05))
            print(f"  CONTRÔLE 2023-2024 du 56 b restreint à {retenus} : {r['n']} trades, {r['gain']:.1%}, {r['pnl']:,.0f} $ | p = {p:.4f}")
        else:
            print("  aucun déclencheur retenu : pas de contrôle")
    pd.DataFrame(lignes).to_csv(os.path.join(os.path.dirname(__file__), "resultats_variante3.csv"), index=False)


if __name__ == "__main__":
    main()
