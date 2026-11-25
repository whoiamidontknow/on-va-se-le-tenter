"""25/11 — programme NIVEAUX / HORIZON (HYPOTHESES.md, commit 830352a) : P1 réaction aux pivots et au Detector,
P2 biais du jour en lecture terminée pendant la séance US. MNQ / MES, 5 et 15 min, sélection H1, contrôle H2 + plateau.

    uv run --with pandas --with openpyxl python niveaux.py
"""
import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [ICI, os.path.join(ICI, "..", "complet")]
from objectifs import prep, FIN, AN  # noqa: E402
from seuils import DEBUT, MILIEU  # noqa: E402
from moteur import sequence, mesures, hasard, TICK, COMM  # noqa: E402
from decision56 import DECL  # noqa: E402

N_TIR, MIN_TRADES, X = 2000, 30, 0.1
GEO_P1 = (1.5, 1.5, 16)
GRILLE_P1 = {"k": (1.0, 1.5, 2.0), "R": (1.0, 1.5, 2.0), "N": (8, 16, 32)}
STOP_P2 = {5: (4, 8, 12), 15: (2, 4, 6)}


def issues_gen(B, k_atr, tpr, nbar, sortie=None):
    """moteur.issues avec une sortie au marché supplémentaire : à la clôture des bougies où `sortie` est vrai."""
    n = len(B)
    O, H, L = B.o.values, B.h.values, B.l.values
    fin = B.fin.values.astype(bool)
    sortie = np.zeros(n, bool) if sortie is None else sortie
    dist = k_atr * B.atr.values
    vp = B.attrs["val_point"]
    i = np.arange(n)
    e = i + 1
    valide = (e < n) & ~fin & np.isfinite(dist) & (dist > 0)
    ee = np.minimum(e, n - 1)
    out = {}
    for d, s in ((1, "L"), (-1, "S")):
        fill = O[ee] + d * TICK
        p1 = np.full(n, np.nan)
        rs = np.full(n, -1, dtype=np.int8)
        lib = np.full(n, n, dtype=np.int64)
        ouvert = valide.copy()
        for j in range(nbar):
            b = e + j
            act = ouvert & (b < n)
            if not act.any():
                break
            bb = np.minimum(b, n - 1)
            if j == 0:
                nsl, ntp = np.maximum(1, np.round(dist / TICK)), np.maximum(1, np.round(tpr * dist / TICK))
            else:
                nsl, ntp = np.ceil(dist / TICK - 1e-9), np.ceil(tpr * dist / TICK - 1e-9)
            stop, tp = fill - d * nsl * TICK, fill + d * ntp * TICK
            hi, lo = H[bb], L[bb]
            ts = act & ((lo <= stop) if d > 0 else (hi >= stop))
            tt = act & ((hi >= tp) if d > 0 else (lo <= tp)) & ~ts
            p1[ts], p1[tt] = ((stop - d * TICK - fill) * d)[ts], ((tp - fill) * d)[tt]
            rs[ts], rs[tt] = 0, 1
            lib[ts | tt] = bb[ts | tt]
            ouvert &= ~(ts | tt)
            mk = ouvert & (b < n) & (fin[bb] | sortie[bb] | (j == nbar - 1))
            nx = np.minimum(bb + 1, n - 1)
            okx = mk & (bb + 1 < n)
            p1[okx] = ((O[nx] - d * TICK - fill) * d)[okx]
            rs[okx] = 2
            lib[okx] = (bb + 1)[okx]
            ouvert &= ~mk
        out[f"p1_{s}"], out[f"r_{s}"], out[f"lib_{s}"] = p1 * vp - 2 * COMM, rs, lib
    return out


def chicago(B):
    """Heure de clôture de chaque bougie à Chicago (minutes depuis minuit) et date de séance (jour de Chicago)."""
    t = B.t.dt.tz_localize("Europe/Paris", ambiguous="NaT", nonexistent="shift_forward").dt.tz_convert("America/Chicago")
    tc = t + pd.Timedelta(minutes=B.attrs["unite"])
    return (tc.dt.hour * 60 + tc.dt.minute).values, tc.dt.date.values


def evenements_p1(B):
    c, h, l, a = B.c.values, B.h.values, B.l.values, B.atr.values
    cp = np.r_[np.nan, c[:-1]]
    RL = np.zeros(len(B), bool); RS = RL.copy(); CL = RL.copy(); CS = RL.copy()
    for p in ("pW", "pM", "pA"):
        P = c - B[p].values * a
        with np.errstate(invalid="ignore"):
            RL |= (l <= P + X * a) & (cp > P) & (c > P)
            RS |= (h >= P - X * a) & (cp < P) & (c < P)
            CL |= (cp < P) & (c > P + X * a)
            CS |= (cp > P) & (c < P - X * a)
    with np.errstate(invalid="ignore"):
        DL = (B.detD.values <= 0.25) & (c > B.o.values)
        DS = (B.detU.values <= 0.25) & (c < B.o.values)
    return {"PIV-R": (RL, RS), "PIV-C": (CL, CS), "DET-R": (np.nan_to_num(DL).astype(bool), np.nan_to_num(DS).astype(bool))}


def contextes(B):
    k4, dh = B.k4.values, B.dirH.values
    un = np.ones(len(B), bool)
    return {"aucun": (un, un), "k4": (k4 > 0, k4 <= 0), "dirH": (dh == 1, dh == -1)}


def decisions_p2(B, biais, entree, decal=0):
    mn, jour = chicago(B)
    dsel = B[biais].values
    k4 = B.k4.values
    bL, bS = (k4 > 0) & (dsel == 1), (k4 <= 0) & (dsel == -1)
    if entree == "heure":
        m = mn == 8 * 60 + 45 + decal
        return m & bL, m & bS
    Ld = B[[f"{x}_L" for x in DECL]].values.any(axis=1)
    Sd = B[[f"{x}_S" for x in DECL]].values.any(axis=1)
    fen = (mn > 8 * 60 + 30 + decal) & (mn <= 14 * 60)
    cL, cS = fen & bL & Ld & ~Sd, fen & bS & Sd & ~Ld
    prem = pd.Series(cL | cS).groupby(jour).cumsum().values == 1          # première du jour
    return cL & prem, cS & prem


def fin_us(B):
    mn, _ = chicago(B)
    return mn == 15 * 60


def tester(B, I, mL, mS, per, refs, tirer=True):
    idx = np.flatnonzero(per & (mL ^ mS))
    sens = np.where(mL[idx], 1, -1)
    pris, ss, pn = sequence(I, idx, sens)
    r = mesures(pn)
    ans = max((B.t[per].max() - B.t[per].min()).days, 1) / AN
    r["rc"] = (r["pnl"] / ans) / r["baisse_max"] if r["baisse_max"] > 0 else np.nan
    r["pris"], r["ss"], r["pn"] = pris, ss, pn
    for ref in refs:
        r[f"p_{ref}"] = np.nan
        if tirer and r["n"] >= MIN_TRADES and r["pnl"] > 0:
            D = hasard(B, I, per, idx, sens, N_TIR, ref, np.random.default_rng(5669))
            r[f"p_{ref}"] = (np.sum(D.pnl >= r["pnl"]) + 1) / (len(D) + 1)
    return r


def main():
    lignes, cand = [], []
    for u in (5, 15):
        for ins in ("MNQ", "MES"):
            B = prep(ins, u)
            h1 = ((B.t >= DEBUT) & (B.t < MILIEU)).values
            I1 = issues_gen(B, *GEO_P1)
            ev, ctx = evenements_p1(B), contextes(B)
            for e, (L, S) in ev.items():
                for c, (cL, cS) in ctx.items():
                    r = tester(B, I1, L & cL, S & cS, h1, "BL")
                    s = 0.05 / 36
                    ok = r["n"] >= MIN_TRADES and r["pnl"] > 0 and r["p_B"] < s and r["p_L"] < s
                    lignes.append(dict(prog="P1", unite=u, ins=ins, regle=e, variante=c, H1_n=r["n"], H1_pnl=r["pnl"],
                                       H1_rc=r["rc"], H1_pB=r["p_B"], H1_pL=r["p_L"], seuil=s, candidat=ok))
                    print(f"  P1 {u} min {ins} {e} {c:<5} H1 : {r['n']:5d} tr {r['pnl']:>9,.0f} $ p_B {r['p_B']:.4f} p_L {r['p_L']:.4f}"
                          + ("  ← candidat" if ok else ""), flush=True)
                    if ok:
                        cand.append(("P1", u, ins, e, c))
            I2 = issues_gen(B, STOP_P2[u][1], 1e6, 200, fin_us(B))
            for bi in ("dirH", "dirM"):
                for en in ("heure", "premiere"):
                    L, S = decisions_p2(B, bi, en)
                    r = tester(B, I2, L, S, h1, "BL")
                    s = 0.05 / 16
                    ok = r["n"] >= MIN_TRADES and r["pnl"] > 0 and r["p_B"] < s and r["p_L"] < s
                    lignes.append(dict(prog="P2", unite=u, ins=ins, regle=bi, variante=en, H1_n=r["n"], H1_pnl=r["pnl"],
                                       H1_rc=r["rc"], H1_pB=r["p_B"], H1_pL=r["p_L"], seuil=s, candidat=ok))
                    print(f"  P2 {u} min {ins} biais {bi} entrée {en:<8} H1 : {r['n']:5d} tr {r['pnl']:>9,.0f} $ p_B {r['p_B']:.4f} p_L {r['p_L']:.4f}"
                          + ("  ← candidat" if ok else ""), flush=True)
                    if ok:
                        cand.append(("P2", u, ins, bi, en))
    T = pd.DataFrame(lignes)
    print(f"\nCandidats H1 : {len(cand)} sur {len(T)} tests")
    for prog, u, ins, a, b in cand:
        B = prep(ins, u)
        h2 = (B.t >= MILIEU).values
        s = 0.05 / len(cand)
        cases = []
        if prog == "P1":
            L, S = evenements_p1(B)[a]
            cL, cS = contextes(B)[b]
            L, S = L & cL, S & cS
            r = tester(B, issues_gen(B, *GEO_P1), L, S, h2, "BL")
            k0, R0, N0 = GEO_P1
            for g in [(k0, R0, N0)] + [(k, R0, N0) for k in GRILLE_P1["k"] if k != k0] + \
                     [(k0, R, N0) for R in GRILLE_P1["R"] if R != R0] + [(k0, R0, N) for N in GRILLE_P1["N"] if N != N0]:
                x = tester(B, issues_gen(B, *g), L, S, h2, "", tirer=False)
                cases.append((x["pnl"], x["rc"]))
            plateau = sum(p > 0 for p, _ in cases) >= 5 and np.nanmedian([rc for _, rc in cases]) > 0
        else:
            L, S = decisions_p2(B, a, b)
            r = tester(B, issues_gen(B, STOP_P2[u][1], 1e6, 200, fin_us(B)), L, S, h2, "BL")
            for k in STOP_P2[u]:
                I = issues_gen(B, k, 1e6, 200, fin_us(B))
                for dec in (-30, 0, 30):
                    x = tester(B, I, *decisions_p2(B, a, b, dec), h2, "", tirer=False)
                    cases.append((x["pnl"], x["rc"]))
            plateau = sum(p > 0 for p, _ in cases) >= 6 and np.nanmedian([rc for _, rc in cases]) > 0
        passe = r["pnl"] > 0 and r["p_B"] < s and r["p_L"] < s and plateau
        i = T.index[(T.prog == prog) & (T.unite == u) & (T.ins == ins) & (T.regle == a) & (T.variante == b)][0]
        T.loc[i, ["H2_n", "H2_pnl", "H2_rc", "H2_pB", "H2_pL", "plateau", "passe"]] = \
            [r["n"], r["pnl"], r["rc"], r["p_B"], r["p_L"], f"{sum(p > 0 for p, _ in cases)}/{len(cases)}", passe]
        print(f"  H2 {prog} {u} min {ins} {a} {b} : {r['n']} tr {r['pnl']:+,.0f} $ R/C {r['rc']:.2f} p_B {r['p_B']:.4f}"
              f" p_L {r['p_L']:.4f} (seuil {s:.4f}) ; plateau {sum(p > 0 for p, _ in cases)}/{len(cases)} → {'PASSE' if passe else 'non'}", flush=True)
    T.to_csv(os.path.join(ICI, "niveaux_resultats.csv"), index=False)


if __name__ == "__main__":
    main()
