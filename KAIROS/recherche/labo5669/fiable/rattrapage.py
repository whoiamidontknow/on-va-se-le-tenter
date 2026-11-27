"""27/11 — RATTRAPAGE des trades nés après coup (HYPOTHESES.md, commit 738e62e).

    uv run --with pandas --with openpyxl python rattrapage.py
"""
import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [ICI]
from decision56 import DECL  # noqa: E402
from objectifs import prep, FIN, AN  # noqa: E402
from seuils import DEBUT, MILIEU  # noqa: E402

TICK, COMM, QTY, N_TIR, MIN_TRADES, K, TPR, NB = 0.25, 1.25, 2, 2000, 30, 3.0, 0.6667, 16


class Donnees:
    def __init__(self, ins, u):
        B = prep(ins, u)
        self.B, self.n, self.u = B, len(B), u
        self.O, self.H, self.L, self.C = B.o.values, B.h.values, B.l.values, B.c.values
        self.atr, self.fin = B.atr.values, B.fin.values.astype(bool)
        self.b1, self.b4, self.o1, self.o4 = B.b1.values, B.b4.values, B.o1.values, B.o4.values
        self.g1, self.g4 = pd.factorize(B.bloc1)[0], pd.factorize(B.bloc4)[0]
        self.der1 = pd.Series(np.arange(self.n)).groupby(self.g1).transform("max").values
        self.der4 = pd.Series(np.arange(self.n)).groupby(self.g4).transform("max").values
        self.t = B.t.values
        self.vp = B.attrs["val_point"]
        er = np.round(B.e1.values * 10) / 10
        Ld = B[[f"{x}_L" for x in DECL]].values.any(axis=1)
        Sd = B[[f"{x}_S" for x in DECL]].values.any(axis=1)
        self.Ld, self.Sd = Ld, Sd
        self.baseL = Ld & ~Sd & ~self.fin & (er <= 0.6)
        self.baseS = Sd & ~Ld & ~self.fin & (er >= -0.6)
        self.per = (B.t >= DEBUT).values
        self.fuite = False          # True = définition fautive du 738e62e (filtre sur la couleur finale), pour mémoire

    def trade(self, e, d, nmax, k=K, R=TPR, atr_ref=None, niveaux=None):
        """Un trade entré à l'ouverture de e. niveaux = (stop, objectif) absolus, sinon recalculés depuis le prix d'entrée
        (bougie d'entrée en ticks arrondis, ensuite au premier tick qui atteint le niveau, comme le 56).
        Rend (P&L par contrat, bougie libre, risque en $ par contrat) ou None."""
        if e >= self.n:
            return None
        fill = self.O[e] + d * TICK
        dist = k * atr_ref
        for jb in range(nmax):
            b = e + jb
            if b >= self.n:
                return None
            if niveaux is None:
                nsl = max(1, round(dist / TICK)) if jb == 0 else np.ceil(dist / TICK - 1e-9)
                ntp = max(1, round(R * dist / TICK)) if jb == 0 else np.ceil(R * dist / TICK - 1e-9)
                stop, tp = fill - d * nsl * TICK, fill + d * ntp * TICK
            else:
                stop, tp = niveaux
            if (self.L[b] <= stop) if d > 0 else (self.H[b] >= stop):
                px, lib = stop - d * TICK, b
                break
            if (self.H[b] >= tp) if d > 0 else (self.L[b] <= tp):
                px, lib = tp, b
                break
            if self.fin[b] or jb == nmax - 1:
                if b + 1 >= self.n:
                    return None
                px, lib = self.O[b + 1] - d * TICK, b + 1
                break
        risque = (abs(fill - niveaux[0]) if niveaux else dist) * self.vp
        return (px - fill) * d * self.vp - 2 * COMM, lib, risque

    def rattrapages(self, var, k=K, R=TPR):
        """Liste de dict : i (origine), j (décision de rattrapage), d, nmax, niveaux / atr_ref."""
        out = []
        for d, base, goo, gob in ((1, self.baseL, self.B.goo_L.values, self.B.gob_L.values),
                                  (-1, self.baseS, self.B.goo_S.values, self.B.gob_S.values)):
            # origine : reste du 56 vrai, pas d'alerte (lecture b fausse) ; AUCUNE condition sur la lecture o (fuite)
            cond_o = (goo == 1) if self.fuite else True
            for i in np.flatnonzero(self.per & base & cond_o & (gob == 0)):
                for j in range(i + 1, min(i + NB, self.n - 1)):
                    k1 = self.b1[j] if self.g1[j] == self.g1[i] else self.o1[i]
                    k4 = self.b4[j] if self.g4[j] == self.g4[i] else self.o4[i]
                    ok = (k1 > 0 and k4 > 0) if d > 0 else (k1 <= 0 and k4 <= 0)
                    if not ok:
                        continue
                    if self.fin[j] or not np.isfinite(self.atr[j]):
                        break
                    r = dict(i=i, j=j, d=d, nmax=NB - (j - i), atr_ref=self.atr[j], niveaux=None, k=k, R=R)
                    if var == "b" and not abs(self.C[j] - self.O[i + 1]) < self.atr[i]:
                        break
                    if var == "c":
                        F = self.O[i + 1] + d * TICK
                        st = F - d * np.ceil(K * self.atr[i] / TICK - 1e-9) * TICK
                        tp = F + d * np.ceil(TPR * K * self.atr[i] / TICK - 1e-9) * TICK
                        if not (min(st, tp) < self.C[j] < max(st, tp)):
                            break
                        r["niveaux"] = (st, tp)
                    out.append(r)
                    break
        return sorted(out, key=lambda r: r["j"])

    def sequence(self, decisions):
        """decisions : dict avec j (bougie de décision, entrée à j + 1), d, nmax, atr_ref, niveaux. Une position à la fois."""
        libre, res = -1, []
        for r in decisions:
            if r["j"] < libre:
                continue
            x = self.trade(r["j"] + 1, r["d"], r["nmax"], r.get("k", K), r.get("R", TPR), r["atr_ref"], r["niveaux"])
            if x is None:
                continue
            res.append(dict(r, p1=x[0], lib=x[1], risque=x[2], t=self.t[r["j"]]))
            libre = x[1]
        return pd.DataFrame(res)

    def alertes56(self):
        out = []
        for d, gob in ((1, self.B.gob_L.values), (-1, self.B.gob_S.values)):
            for i in np.flatnonzero(self.per & (gob == 1)):
                out.append(dict(i=i, j=i, d=d, nmax=NB, atr_ref=self.atr[i], niveaux=None, source="56"))
        return sorted(out, key=lambda r: r["j"])


def mesures(T, d0, d1):
    x = T[(T.t >= d0) & (T.t < d1)] if len(T) else T
    if len(x) == 0:
        return dict(n=0, par_mois=0.0, gagnants=np.nan, R=np.nan, ic=np.nan, usd=0.0, creux=0.0, rc=np.nan)
    p = x.p1.values * QTY
    rr = x.p1.values / x.risque.values
    c = np.cumsum(p)
    dd = float(np.max(np.maximum.accumulate(np.r_[0, c])[1:] - c))
    ans = (d1 - d0).days / AN
    return dict(n=len(x), par_mois=len(x) / (ans * 12), gagnants=(p > 0).mean(), R=rr.mean(),
                ic=1.96 * rr.std(ddof=1) / np.sqrt(len(rr)) if len(rr) > 1 else np.nan,
                usd=p.sum(), creux=dd, rc=(p.sum() / ans) / dd if dd > 0 else np.nan)


def hasard(D, T, masque, ref, rng, n_tir=N_TIR):
    """Entrées au hasard (mêmes heures, même nombre), 3 ATR / 0,6667 R de la bougie tirée, durée tirée parmi celles des
    rattrapages ; sens A / B / L. Vectorisé sur tous les tirages ; pas de « une position à la fois » (flux clairsemé)."""
    x = T[masque]
    n = len(x)
    cand = np.flatnonzero(masque_periode(D, x) & ~D.fin & np.isfinite(D.atr) & (D.atr > 0))
    cand = cand[cand + NB + 1 < D.n]
    h = pd.to_datetime(D.t).hour.values
    w = np.bincount(h[x.j.values], minlength=24)[h[cand]].astype(float)
    w /= w.sum()
    sel = rng.choice(cand, (n_tir, n), p=w).ravel()
    nmax = rng.choice(x.nmax.values, sel.size)
    if ref == "L":
        d = np.ones(sel.size)
    elif ref == "A":
        d = np.where(rng.random(sel.size) < (x.d > 0).mean(), 1.0, -1.0)
    else:
        l, s = D.Ld[sel], D.Sd[sel]
        d = np.where(l & ~s, 1.0, np.where(s & ~l, -1.0, np.where(rng.random(sel.size) < 0.5, 1.0, -1.0)))
    e = sel + 1
    fill = D.O[e] + d * TICK
    dist = K * D.atr[sel]
    p = np.full(sel.size, np.nan)
    ouvert = np.ones(sel.size, bool)
    for jb in range(NB):
        b = e + jb
        nsl = np.maximum(1, np.round(dist / TICK)) if jb == 0 else np.ceil(dist / TICK - 1e-9)
        ntp = np.maximum(1, np.round(TPR * dist / TICK)) if jb == 0 else np.ceil(TPR * dist / TICK - 1e-9)
        st, tp = fill - d * nsl * TICK, fill + d * ntp * TICK
        ts = ouvert & np.where(d > 0, D.L[b] <= st, D.H[b] >= st)
        p[ts] = ((st - d * TICK - fill) * d)[ts]
        ouvert &= ~ts
        tt = ouvert & np.where(d > 0, D.H[b] >= tp, D.L[b] <= tp)
        p[tt] = ((tp - fill) * d)[tt]
        ouvert &= ~tt
        mk = ouvert & (D.fin[b] | (jb == nmax - 1))
        p[mk] = ((D.O[b + 1] - d * TICK - fill) * d)[mk]
        ouvert &= ~mk
    p = (p * D.vp - 2 * COMM) * QTY
    return np.nansum(p.reshape(n_tir, n), axis=1)


def masque_periode(D, x):
    t = pd.to_datetime(x.t)
    d0, d1 = t.min(), t.max()
    return (D.t >= np.datetime64(d0)) & (D.t <= np.datetime64(d1))


def anti_fuite(D, R, rng):
    """20 rattrapages au hasard : l'ouverture de j + 1 doit suivre la clôture de toutes les bougies lues."""
    u = np.timedelta64(D.u, "m")
    ok = 0
    ech = R.sample(min(20, len(R)), random_state=5669)
    for r in ech.itertuples():
        lues = [D.t[r.j] + u]
        if D.g1[r.j] != D.g1[r.i]:
            lues.append(D.t[D.der1[r.i]] + u)
        if D.g4[r.j] != D.g4[r.i]:
            lues.append(D.t[D.der4[r.i]] + u)
        ok += D.t[r.j + 1] >= max(lues) and r.j > r.i
    return ok, len(ech)


def main():
    lignes, cand = [], []
    for u in (15, 5):
        for ins in ("MNQ", "MES"):
            D = Donnees(ins, u)
            S56 = D.sequence(D.alertes56())
            for var in "abc":
                dec = D.rattrapages(var)
                R = D.sequence(dec)
                h1 = (R.t < np.datetime64(MILIEU)).values if len(R) else np.array([], bool)
                m1, m2 = mesures(R, DEBUT, MILIEU), mesures(R, MILIEU, FIN)
                pv = {}
                for ref in "ABL":
                    pv[ref] = np.nan
                    if m1["n"] >= MIN_TRADES and m1["usd"] > 0:
                        tot = hasard(D, R, h1, ref, np.random.default_rng(5669))
                        pv[ref] = (np.sum(tot >= m1["usd"]) + 1) / (N_TIR + 1)
                ok = m1["n"] >= MIN_TRADES and m1["usd"] > 0 and all(pv[x] < 0.05 / 12 for x in "ABL")
                comb = D.sequence(sorted([dict(r, source="56") for r in D.alertes56()] + [dict(r, source="R") for r in dec],
                                         key=lambda r: (r["j"], r["source"] != "56")))
                af = anti_fuite(D, R, np.random.default_rng(1)) if len(R) else (0, 0)
                d = dict(unite=u, ins=ins, var=var, origines=len(dec))
                for nom, m in (("H1", m1), ("H2", m2)):
                    d.update({f"{nom}_{k}": v for k, v in m.items()})
                for nom, (d0, d1) in (("H1", (DEBUT, MILIEU)), ("H2", (MILIEU, FIN))):
                    d[f"{nom}_56_seul"] = mesures(S56, d0, d1)["usd"]
                    d[f"{nom}_56_plus_R"] = mesures(comb, d0, d1)["usd"]
                d.update(H1_pA=pv["A"], H1_pB=pv["B"], H1_pL=pv["L"], candidat=ok, anti_fuite=f"{af[0]}/{af[1]}")
                lignes.append(d)
                print(f"  {u} min {ins} ({var}) : {len(dec)} rattrapages possibles ; H1 {m1['n']} tr ({m1['par_mois']:.1f}/mois) "
                      f"{m1['gagnants']:.0%} R {m1['R']:+.3f} ± {m1['ic']:.3f} {m1['usd']:+,.0f} $ creux {m1['creux']:,.0f} | "
                      f"p_A {pv['A']:.4f} p_B {pv['B']:.4f} p_L {pv['L']:.4f} | anti-fuite {af[0]}/{af[1]}"
                      + ("  ← candidat" if ok else ""), flush=True)
                if ok:
                    cand.append((u, ins, var))
    T = pd.DataFrame(lignes)
    T.to_csv(os.path.join(ICI, "rattrapage_resultats.csv"), index=False)
    print(f"\nCandidats H1 : {len(cand)} sur {len(T)}")
    return T, cand


if __name__ == "__main__":
    main()
