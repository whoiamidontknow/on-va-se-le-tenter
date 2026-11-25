"""25/11 — programme « objectifs de Jeremy » (HYPOTHESES.md, écrit avant les tests, commit 30c8a66).

Étape 1, `selection` : pistes A (MNQ 5 min, lecture b + score, grille de sorties), B (lecture k), C (filtres sur les
cases retenues en A et B), D (combinaisons avec MNQ 15 / MES 15). Choix sur la 1re moitié (H1) seulement.
Étape 2, `controle` : P&L sur les deux moitiés et hasard A / B / L des finalistes sur H2.
Étape 3, `mesures` : taille dans les règles, % par an / par mois, évaluations FTMO et Tradeify.

    uv run --with pandas --with openpyxl python objectifs.py selection|controle|mesures
"""
import itertools
import json
import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [ICI, os.path.join(ICI, "..", "complet"), os.path.join(ICI, "..")]
from decision56 import charger56, DECL  # noqa: E402
from seuils import tables, DEBUT, MILIEU  # noqa: E402
from moteur import issues, sequence, hasard  # noqa: E402

CACHE = os.environ.get("CACHE_OBJ", "/private/tmp/claude-501/-Users-jeremk-Ephore/5255c912-f232-4044-9510-5af2888db584/scratchpad")
FIN = pd.Timestamp("2026-11-14")
AN = 365.25
KS, RS, NS, SEUILS = (1, 1.5, 2, 3, 4), (0.5, 0.667, 1, 1.5, 2), (8, 16, 32, 64), (0, 60, 70, 80)
GEO56 = (3, 0.667, 16)
MIN_TRADES = 60


def prep(ins, u, debut=DEBUT, milieu=MILIEU, dossier=None):
    """Bougies coupées à la période, score de fiabilité (tables apprises sur [debut, milieu))."""
    cle = os.path.join(CACHE, f"obj_{ins}_{u}_{debut:%Y%m%d}.pkl")
    if os.path.exists(cle):
        return pd.read_pickle(cle)
    B = charger56(ins, u) if dossier is None else charger56(ins, u, dossier=dossier)
    at = dict(B.attrs)
    B = B[B.t >= debut - pd.Timedelta(days=3)].reset_index(drop=True)
    B.attrs.update(at)
    trig = B[[f"{d}_{s}" for d in DECL for s in "LS"]].values.any(axis=1)
    _, B["score"] = tables(B, trig & (B.t >= debut).values & (B.t < milieu).values)
    B.to_pickle(cle)
    return B


def trades(B, I, L, S):
    """Décisions (masques long / court) -> trades (une position à la fois) : bougie de décision, de sortie, sens, P&L / contrat."""
    idx = np.flatnonzero(L | S)
    sens = np.where(L[idx], 1, -1)
    pris, ss, pn = sequence(I, idx, sens)
    lib = np.where(ss > 0, I["lib_L"][pris], I["lib_S"][pris])
    lib = np.minimum(lib, len(B) - 1)
    return pd.DataFrame({"i": pris, "t": B.t.values[pris], "tx": B.t.values[lib], "d": ss, "p1": pn})


def creux(p):
    c = np.cumsum(p)
    return float(np.max(np.maximum.accumulate(np.r_[0, c])[1:] - c)) if len(p) else 0.0


def note(T, d0, d1):
    """Mesures d'une liste de trades (1 contrat) sur [d0, d1) : n, P&L, P&L annualisé, creux, rapport R/C."""
    x = T[(T.t >= d0) & (T.t < d1)]
    p = x.p1.values
    ans = (d1 - d0).days / AN
    dd = creux(p)
    pnl = p.sum()
    return dict(n=len(p), pnl=pnl, an=pnl / ans, creux=dd, rc=(pnl / ans) / dd if dd > 0 else np.nan,
                gagnants=(p > 0).mean() if len(p) else np.nan)


def decisions(B, lec, seuil=0, filtres=None):
    L, S = B[f"go{lec}_L"].values == 1, B[f"go{lec}_S"].values == 1
    per = (B.t >= DEBUT).values
    f = per & ((B.score.values >= seuil / 100) if seuil else True)
    if filtres:
        dr, cr, ax = filtres
        te = B.t + pd.Timedelta(minutes=B.attrs["unite"])          # heure d'entrée (ouverture suivante)
        hm = te.dt.hour.values * 60 + te.dt.minute.values
        if dr:
            L = L & (B.dirH.values == 1)
            S = S & (B.dirH.values == -1)
        if cr == "Londres+US":
            f = f & (((hm >= 540) & (hm < 720)) | ((hm >= 930) & (hm < 1080)))
        elif cr == "09-22":
            f = f & (hm >= 540) & (hm < 1320)
        if ax:
            f = f & (B.adx.values >= ax)
    return L & f, S & f


def plateau(df, cle):
    """Médiane de R/C sur la case et ses voisines immédiates (k, R, N ± 1 cran), même seuil / même piste."""
    pos = {(a, b, c): (KS.index(a), RS.index(b), NS.index(c)) for a in KS for b in RS for c in NS}
    g = df.set_index(cle + ["k", "R", "N"]).rc_valide
    out = []
    for r in df.itertuples():
        i, j, l = pos[(r.k, r.R, r.N)]
        v = []
        for di, dj, dl in ((0, 0, 0), (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            a, b, c = i + di, j + dj, l + dl
            if 0 <= a < len(KS) and 0 <= b < len(RS) and 0 <= c < len(NS):
                v.append(g.get(tuple(getattr(r, x) for x in cle) + (KS[a], RS[b], NS[c]), np.nan))
        out.append(np.nanmedian(v) if np.isfinite(v).any() else np.nan)
    return out


def selection():
    B5 = prep("MNQ", 5)
    lignes = []
    for k, R, N in itertools.product(KS, RS, NS):
        I = issues(B5, k, R, N)
        for s in SEUILS:
            T = trades(B5, I, *decisions(B5, "b", s))
            lignes.append(dict(piste="A", seuil=s, k=k, R=R, N=N, **note(T, DEBUT, MILIEU)))
        T = trades(B5, I, *decisions(B5, "k"))
        lignes.append(dict(piste="B", seuil=0, k=k, R=R, N=N, **note(T, DEBUT, MILIEU)))
    G = pd.DataFrame(lignes)
    G["rc_valide"] = np.where((G.n >= MIN_TRADES), G.rc, np.nan)
    G["plateau"] = plateau(G, ["piste", "seuil"])
    G["eligible"] = (G.n >= MIN_TRADES) & (G.pnl > 0)
    G.to_csv(os.path.join(ICI, "obj_grille_AB.csv"), index=False)
    best = {}
    for p in "AB":
        g = G[(G.piste == p) & G.eligible].sort_values("plateau", ascending=False)
        best[p] = g.iloc[0].to_dict() if len(g) else None
        print(f"\nPiste {p} : {int(G[G.piste == p].eligible.sum())} cases éligibles sur {int((G.piste == p).sum())} ; 5 meilleures (plateau) :")
        print(g.head(5)[["seuil", "k", "R", "N", "n", "pnl", "an", "creux", "rc", "plateau", "gagnants"]].round(2).to_string(index=False))
    # C : filtres sur les cases retenues en A et B
    lc = []
    for p in "AB":
        b = best[p]
        if b is None:
            continue
        I = issues(B5, b["k"], b["R"], b["N"])
        for dr, cr, ax in itertools.product((False, True), (None, "Londres+US", "09-22"), (0, 20, 25)):
            if not dr and cr is None and not ax:
                continue
            T = trades(B5, I, *decisions(B5, "b" if p == "A" else "k", b["seuil"], (dr, cr, ax)))
            lc.append(dict(piste="C", base=p, seuil=b["seuil"], k=b["k"], R=b["R"], N=b["N"], dirH=dr, creneau=cr or "",
                           adx=ax, **note(T, DEBUT, MILIEU)))
    C = pd.DataFrame(lc)
    C["eligible"] = (C.n >= MIN_TRADES) & (C.pnl > 0)
    C.to_csv(os.path.join(ICI, "obj_grille_C.csv"), index=False)
    gc = C[C.eligible].sort_values("rc", ascending=False)
    print("\nPiste C : 5 meilleures (R/C sur H1) :")
    print(gc.head(5)[["base", "dirH", "creneau", "adx", "n", "pnl", "an", "creux", "rc", "gagnants"]].round(2).to_string(index=False))
    best["C"] = gc.iloc[0].to_dict() if len(gc) else None
    # D : combinaisons
    B15 = prep("MNQ", 15)
    I15 = issues(B15, *GEO56)
    m15 = []
    for s in SEUILS:
        T = trades(B15, I15, *decisions(B15, "b", s))
        m15.append(dict(seuil=s, **note(T, DEBUT, MILIEU)))
    m15 = pd.DataFrame(m15)
    print("\nMNQ 15 min (sorties du 56, lecture b), choix du seuil sur H1 :")
    print(m15.round(2).to_string(index=False))
    s15 = int(m15[(m15.n >= MIN_TRADES) & (m15.pnl > 0)].sort_values("rc", ascending=False).seuil.iloc[0]) \
        if ((m15.n >= MIN_TRADES) & (m15.pnl > 0)).any() else 0
    mnq5 = max((best["A"], best["C"] if best["C"] and best["C"]["base"] == "A" else None),
               key=lambda b: -np.inf if b is None else (b["rc"] if np.isfinite(b["rc"]) else -np.inf))
    comp = {"MNQ5": composante_mnq5(B5, mnq5), "MNQ15": trades(B15, I15, *decisions(B15, "b", s15))}
    BE = prep("MES", 15)
    comp["MES15"] = trades(BE, issues(BE, *GEO56), *decisions(BE, "b", 80))
    ld = []
    for nom, parts in (("D1", ("MNQ5", "MNQ15")), ("D2", ("MNQ5", "MES15")), ("D3", ("MNQ5", "MNQ15", "MES15"))):
        T = pd.concat([comp[c] for c in parts]).sort_values("tx").reset_index(drop=True)
        ld.append(dict(piste="D", nom=nom, parts="+".join(parts), **note(T.assign(t=T.tx), DEBUT, MILIEU)))
    D = pd.DataFrame(ld)
    print(f"\nPiste D (MNQ 5 = {'C' if mnq5 is best['C'] else 'A'}, MNQ 15 seuil {s15}, MES 15 seuil 80) :")
    print(D.round(2).to_string(index=False))
    gd = D[(D.n >= MIN_TRADES) & (D.pnl > 0)].sort_values("rc", ascending=False)
    best["D"] = dict(gd.iloc[0].to_dict(), mnq5=mnq5, s15=s15) if len(gd) else None
    # finalistes : meilleur de chaque piste + le suivant (A ou B) au plateau le plus haut
    fin = {p: b for p, b in best.items() if b is not None}
    reste = G[G.eligible].sort_values("plateau", ascending=False)
    for r in reste.itertuples():
        d = r._asdict()
        if not any(f.get("piste") == d["piste"] and all(f.get(x) == d[x] for x in ("seuil", "k", "R", "N")) for f in fin.values()):
            fin["suivant"] = {kk: v for kk, v in d.items() if kk != "Index"}
            break
    json.dump(fin, open(os.path.join(ICI, "obj_finalistes.json"), "w"), indent=1, default=float)
    n_essais = len(G) + len(C) + len(D) + len(m15)
    print(f"\nEssais de la sélection : {n_essais} (A {int((G.piste == 'A').sum())}, B {int((G.piste == 'B').sum())},"
          f" C {len(C)}, D {len(D)}, seuils MNQ 15 {len(m15)})")
    print(json.dumps({p: {k: f.get(k) for k in ("piste", "base", "seuil", "k", "R", "N", "dirH", "creneau", "adx", "nom",
                                                "n", "pnl", "rc", "plateau")} for p, f in fin.items()}, indent=1, default=str))


def composante_mnq5(B5, b):
    I = issues(B5, b["k"], b["R"], b["N"])
    lec = "b" if b.get("piste", "A") == "A" or b.get("base") == "A" else "k"
    filt = (b["dirH"], b["creneau"] or None, b["adx"]) if b.get("piste") == "C" else None
    return trades(B5, I, *decisions(B5, lec, b["seuil"], filt))


if __name__ == "__main__":
    if sys.argv[1] == "selection":
        selection()


def composantes(f):
    """Liste de (B, I, L, S) d'un finaliste (une seule pour A / B / C / suivant, trois pour D)."""
    B5 = prep("MNQ", 5)
    if f["piste"] != "D":
        I = issues(B5, f["k"], f["R"], f["N"])
        lec = "k" if f["piste"] == "B" or f.get("base") == "B" else "b"
        filt = (f["dirH"], f["creneau"] or None, f["adx"]) if f["piste"] == "C" else None
        return [("MNQ5", B5, I, *decisions(B5, lec, f["seuil"], filt))]
    m = f["mnq5"]
    out = composantes(m)
    B15, BE = prep("MNQ", 15), prep("MES", 15)
    I15 = issues(B15, *GEO56)
    parts = f["parts"].split("+")
    if "MNQ15" in parts:
        out.append(("MNQ15", B15, I15, *decisions(B15, "b", f["s15"])))
    if "MES15" in parts:
        out.append(("MES15", BE, issues(BE, *GEO56), *decisions(BE, "b", 80)))
    return out


def trades_finaliste(f):
    return pd.concat([trades(B, I, L, S).assign(comp=c, vp=B.attrs["val_point"]) for c, B, I, L, S in composantes(f)]) \
        .sort_values("tx").reset_index(drop=True)


def controle(N_TIR=1000):
    fins = json.load(open(os.path.join(ICI, "obj_finalistes.json")))
    k = len(fins)
    lignes = []
    for nom, f in fins.items():
        T = trades_finaliste(f)
        d = dict(finaliste=nom, piste=f["piste"])
        for moitie, d0, d1 in (("H1", DEBUT, MILIEU), ("H2", MILIEU, FIN)):
            m = note(T.assign(t=T.tx), d0, d1)
            d.update({f"{moitie}_{x}": m[x] for x in ("n", "pnl", "an", "creux", "rc")})
            for ref in "ABL":
                tot = np.zeros(N_TIR)
                for c, B, I, L, S in composantes(f):
                    per = ((B.t >= d0) & (B.t < d1)).values
                    idx = np.flatnonzero(per & (L | S))
                    sens = np.where(L[idx], 1, -1)
                    h = hasard(B, I, per, idx, sens, n_tir=N_TIR, ref=ref, rng=np.random.default_rng(5669))
                    tot += h.pnl.values / 2                      # hasard() compte 2 contrats
                d[f"{moitie}_p{ref}"] = ((tot >= m["pnl"]).sum() + 1) / (N_TIR + 1)
        d["passe"] = bool(d["H1_pnl"] > 0 and d["H2_pnl"] > 0 and d["H2_pB"] < 0.05 / k and d["H2_pL"] < 0.05 / k)
        lignes.append(d)
        print({x: (round(v, 4) if isinstance(v, float) else v) for x, v in d.items()}, flush=True)
    R = pd.DataFrame(lignes)
    R.to_csv(os.path.join(ICI, "obj_controle.csv"), index=False)
    print(f"\nSeuil corrigé sur H2 : 0,05 / {k} = {0.05 / k:.3f}")
    print(R[["finaliste", "piste", "H1_pnl", "H1_rc", "H2_n", "H2_pnl", "H2_rc", "H1_pB", "H1_pL", "H2_pA", "H2_pB", "H2_pL", "passe"]]
          .round(3).to_string(index=False))


if __name__ == "__main__" and sys.argv[1] == "controle":
    controle()
