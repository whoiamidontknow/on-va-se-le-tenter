"""Familles F1-F4 (protocole dans ../HYPOTHESES.md, écrit avant le test).

    uv run -q --with pandas --with openpyxl python familles.py
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "dataset"))
from releve_complet import charger  # noqa: E402
from moteur import issues, sequence, mesures, hasard  # noqa: E402

DEBUT, COUPURE, SCELLE = pd.Timestamp("2019-05-01"), pd.Timestamp("2023-01-01"), pd.Timestamp("2025-01-01")
GEO = {"F1": (2.0, 1.5, 16), "F2": (1.5, 1.0, 8), "F3": (2.0, 1.5, 16)}
TIRAGES, MIN_TRADES = 2000, 30


def hypotheses(B):
    """{nom: (famille, masque long, masque short)} — définitions de HYPOTHESES.md."""
    g = lambda c: B[c].values.astype(bool)
    k1, k4, e1 = B.k1.values, B.k4.values, B.e1.values
    T1L = g("tr1h") & g("tr4h") & (k1 > 0) & (k4 > 0) & g("hei_L")
    T1S = ~g("tr1h") & ~g("tr4h") & (k1 < 0) & (k4 < 0) & g("hei_S")
    fib, fbas = B.fib.values, g("fib_bas")
    zone = (fib >= 0.5) & (fib <= 0.786)
    H = {
        "T1": ("F1", T1L, T1S),
        "T2": ("F1", T1L & g("tr15m") & (B.dirH.values == 1), T1S & ~g("tr15m") & (B.dirH.values == -1)),
        "T3": ("F1", T1L & (e1 >= 0) & (e1 <= 1), T1S & (e1 <= 0) & (e1 >= -1)),
        "M1": ("F2", g("clx_L"), g("clx_S")),
        "M2": ("F2", g("div_L"), g("div_S")),
        "M3": ("F2", (B.pW.values <= -2) & g("hei_L"), (B.pW.values >= 2) & g("hei_S")),
        "M4": ("F2", ~fbas & zone & g("hei_L"), fbas & zone & g("hei_S")),
        "M5": ("F2", (B.detD.values <= 0.5) & g("hei_L"), (B.detU.values <= 0.5) & g("hei_S")),
        "B1": ("F3", g("tl_L"), g("tl_S")),
        "B2": ("F3", g("lvl_L"), g("lvl_S")),
        "B3": ("F3", (g("tl_L") | g("lvl_L")) & (B.feu.values >= 60) & (B.str.values >= 60),
               (g("tl_S") | g("lvl_S")) & (B.feu.values <= 40) & (B.str.values <= 40)),
    }
    return {k: (f, np.nan_to_num(L).astype(bool) if L.dtype != bool else L, S) for k, (f, L, S) in H.items()}


def tester(B, I, mL, mS, periode, rng, refs):
    m = periode & (mL ^ mS)
    idx = np.flatnonzero(m)
    sens = np.where(mL[idx], 1, -1)
    pris, ss, pn = sequence(I, idx, sens)
    r = mesures(pn)
    r["longs"] = float((ss > 0).mean()) if len(ss) else np.nan
    for ref in refs:
        if r["n"] < MIN_TRADES:
            r[f"p_{ref}"], r[f"med_{ref}"] = np.nan, np.nan
            continue
        D = hasard(B, I, periode, idx, sens, TIRAGES, ref, rng)
        r[f"p_{ref}"] = (np.sum(D.pnl >= r["pnl"]) + 1) / (len(D) + 1)
        r[f"med_{ref}"] = D.pnl.median()
    return r


def main():
    rng = np.random.default_rng(5669)
    lignes = []
    for ins in ("MNQ", "MES"):
        B = charger(ins)
        refs = ("A", "L") if ins == "MNQ" else ("A",)
        I = {f: issues(B, *geo) for f, geo in GEO.items()}
        H = hypotheses(B)
        per = {"construction": ((B.t >= DEBUT) & (B.t < COUPURE)).values, "contrôle": ((B.t >= COUPURE) & (B.t < SCELLE)).values}
        regimes = {"": np.ones(len(B), bool), "R1 vr>=1,2": (B.vr.values >= 1.2), "R2 ADX>=25": (B.adx.values >= 25)}
        print(f"\n=== {ins}")
        for h, (fam, mL, mS) in H.items():
            for reg, mr in regimes.items():
                famille = fam if reg == "" else "F4"
                for p_nom, pm in per.items():
                    r = tester(B, I[fam], mL & mr, mS & mr, pm, rng, refs)
                    lignes.append(dict(instrument=ins, famille=famille, hypothese=h, regime=reg, periode=p_nom, **r))
                a, b = lignes[-2], lignes[-1]
                fmt = lambda x: (f"{x['n']:4d} tr {x['gain']:.1%} {x['pnl']:>8,.0f} $ p={x['p_A']:.4f}"
                                 + (f" (long seul p={x['p_L']:.3f})" if "p_L" in x else "")) if x["n"] else "   0 tr"
                print(f"  {famille} {h} {reg:<11} | construction {fmt(a)} | contrôle {fmt(b)}")
    T = pd.DataFrame(lignes)
    T.to_csv(os.path.join(os.path.dirname(__file__), "resultats_familles.csv"), index=False)
    # seuils corrigés et candidats
    ntests = {"F1": 6, "F2": 10, "F3": 6, "F4": 44}
    C = T[T.periode == "construction"].copy()
    C["seuil"] = C.famille.map(lambda f: 0.05 / ntests[f])
    retenus = C[C.p_A < C.seuil]
    print(f"\nRetenus en construction : {len(retenus)}")
    for f, g in retenus.groupby("famille"):
        seuil_ctl = 0.05 / len(g)
        for r in g.itertuples():
            k = T[(T.periode == "contrôle") & (T.instrument == r.instrument) & (T.hypothese == r.hypothese) & (T.regime == r.regime)].iloc[0]
            ok = k.p_A < seuil_ctl
            print(f"  {r.instrument} {f} {r.hypothese} {r.regime} : construction p = {r.p_A:.4f} ; contrôle p = {k.p_A:.4f} (seuil {seuil_ctl:.4f})"
                  f"{'  ← PASSE construction ET contrôle : ARRÊT' if ok else ''}")


if __name__ == "__main__":
    main()
