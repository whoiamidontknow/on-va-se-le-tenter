"""25/11 — H-SORTIE (HYPOTHESES.md, commit 77e706e) : sortie des fantômes à la clôture de la bougie 1 h / 4 h du signal
(S1, S2), sortie sur b1 / b4 contraires (S3), entrée confirmée à la clôture 1 h (E1). Lecture alertes, sorties du 56.

    uv run --with pandas --with openpyxl python sortie.py
"""
import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [ICI, os.path.join(ICI, "..", "complet")]
from decision56 import DECL  # noqa: E402
from seuils import DEBUT, MILIEU  # noqa: E402
from objectifs import prep, decisions, creux, FIN, AN  # noqa: E402

TICK, COMM = 0.25, 1.25
K, TPR, NB = 3.0, 0.667, 16
N_TIR = 1000
REGLES = ("56", "S1", "S2", "S3", "E1")


class Banc:
    def __init__(self, B):
        self.B = B
        self.n = len(B)
        self.O, self.H, self.L = B.o.values, B.h.values, B.l.values
        self.fin = B.fin.values.astype(bool)
        self.atr = B.atr.values
        self.b1, self.b4 = B.b1.values, B.b4.values
        self.g1 = pd.factorize(B.bloc1)[0]
        self.g4 = pd.factorize(B.bloc4)[0]
        self.last1 = np.r_[self.g1[1:] != self.g1[:-1], True]
        self.last4 = np.r_[self.g4[1:] != self.g4[:-1], True]
        self.vp = B.attrs["val_point"]
        self.t = B.t.values

    def contre(self, v, d):
        return (v <= 0) if d > 0 else (v > 0)

    def simuler(self, idx, sens, regle, hasard_q=None, rng=None):
        """Une position à la fois. regle : '56', 'S1', 'S2', 'S3', 'E1' (E1 = sorties du 56).
        hasard_q : probabilité de sortie anticipée au hasard à chaque point de contrôle de la règle (contrôle
        « sortie au hasard ») au lieu de la condition de couleur. Rend (DataFrame des trades, nb de contrôles)."""
        O, H, L, fin, atr = self.O, self.H, self.L, self.fin, self.atr
        libre, out, controles = -1, [], 0
        for i, d in zip(idx, sens):
            if i < libre:
                continue
            e = i + 1
            if e >= self.n or fin[i] or not np.isfinite(atr[i]) or atr[i] <= 0:
                continue
            dist = K * atr[i]
            fill = O[e] + d * TICK
            px, raison, lib = None, None, None
            for j in range(NB):
                b = e + j
                if b >= self.n:
                    break
                if j == 0:
                    nsl, ntp = max(1, round(dist / TICK)), max(1, round(TPR * dist / TICK))
                else:
                    nsl, ntp = np.ceil(dist / TICK - 1e-9), np.ceil(TPR * dist / TICK - 1e-9)
                stop, tp = fill - d * nsl * TICK, fill + d * ntp * TICK
                if (L[b] <= stop) if d > 0 else (H[b] >= stop):
                    px, raison, lib = stop - d * TICK, "stop", b
                    break
                if (H[b] >= tp) if d > 0 else (L[b] <= tp):
                    px, raison, lib = tp, "objectif", b
                    break
                mk = None
                if fin[b]:
                    mk = "fin"
                elif j == NB - 1:
                    mk = "temps"
                elif regle in ("S1", "S2", "S3"):
                    pts = []
                    if regle in ("S1", "S2") and self.last1[b] and self.g1[b] == self.g1[i]:
                        pts.append(self.b1[b])
                    if regle == "S2" and self.last4[b] and self.g4[b] == self.g4[i]:
                        pts.append(self.b4[b])
                    if regle == "S3":
                        pts = [self.b1[b], self.b4[b]]
                    if pts:
                        controles += 1
                        if hasard_q is not None:
                            if rng.random() < hasard_q:
                                mk = "anticipée"
                        elif any(self.contre(v, d) for v in pts):
                            mk = "anticipée"
                if mk:
                    if b + 1 < self.n:
                        px, raison, lib = O[b + 1] - d * TICK, mk, b + 1
                    break
            if px is None:
                continue
            out.append((i, d, raison, (px - fill) * d * self.vp - 2 * COMM, lib))
            libre = lib
        T = pd.DataFrame(out, columns=["i", "d", "raison", "p1", "lib"])
        T["t"] = self.t[T.i.values] if len(T) else pd.Series(dtype="datetime64[ns]")
        T["tx"] = self.t[np.minimum(T.lib.values, self.n - 1)] if len(T) else pd.Series(dtype="datetime64[ns]")
        return T, controles


def decisions_e1(B, banc, seuil):
    """E1 : à la clôture de chaque bougie 1 h, reste du 56 vrai dans l'heure, confirmé par o1 (= b1 à la clôture) et b4."""
    er = np.round(B.e1 * 10) / 10
    Ld = B[[f"{x}_L" for x in DECL]].values.any(axis=1)
    Sd = B[[f"{x}_S" for x in DECL]].values.any(axis=1)
    bL = Ld & ~Sd & (B.fin.values == 0) & (er.values <= 0.6)
    bS = Sd & ~Ld & (B.fin.values == 0) & (er.values >= -0.6)
    vuL = pd.Series(bL).groupby(banc.g1).cummax().values.astype(bool)
    vuS = pd.Series(bS).groupby(banc.g1).cummax().values.astype(bool)
    per = (B.t >= DEBUT).values & banc.last1 & ~banc.fin
    if seuil:
        per &= B.score.values >= seuil / 100
    L = per & vuL & (banc.b1 > 0) & (banc.b4 > 0)
    S = per & vuS & (banc.b1 <= 0) & (banc.b4 <= 0)
    return L & ~S, S & ~L


def entrees(B, banc, regle, seuil):
    L, S = decisions_e1(B, banc, seuil) if regle == "E1" else decisions(B, "b", seuil)
    idx = np.flatnonzero(L | S)
    return idx, np.where(L[idx], 1, -1)


def mesure(T, d0, d1):
    x = T[(T.t >= d0) & (T.t < d1)]
    p = x.p1.values
    ans = (d1 - d0).days / AN
    dd = creux(p)
    return dict(n=len(p), pnl=p.sum(), rc=(p.sum() / ans) / dd if dd > 0 else np.nan, anticipees=int((x.raison == "anticipée").sum()))


def hasard_entrees(B, banc, regle, idx, sens, per, ref, rng, n_tir=N_TIR):
    """Entrées tirées au hasard (mêmes heures, même nombre de trades), même règle de sortie. ref B : sens du
    déclencheur ; L : long seulement. Pour E1, candidates = clôtures de bougie 1 h."""
    cand = np.flatnonzero(per & ~banc.fin & np.isfinite(banc.atr) & (banc.atr > 0))
    if regle == "E1":
        cand = cand[banc.last1[cand]]
    h = B.t.dt.hour.values
    sel_obs = idx[per[idx]]
    w = np.bincount(h[sel_obs], minlength=24) / np.maximum(np.bincount(h[cand], minlength=24), 1)
    w = w / w.max()
    Ld = B[[f"{x}_L" for x in DECL]].values.any(axis=1)
    Sd = B[[f"{x}_S" for x in DECL]].values.any(axis=1)
    if ref == "B":
        cand = cand[Ld[cand] | Sd[cand]]
    cible = len(banc.simuler(sel_obs, sens[per[idx]], regle)[0])

    def un(c, r):
        s = cand[r.random(len(cand)) < c * w[h[cand]]]
        if ref == "L":
            d = np.ones(len(s), dtype=int)
        else:
            l, sh = Ld[s], Sd[s]
            d = np.where(l & ~sh, 1, np.where(sh & ~l, -1, np.where(r.random(len(s)) < 0.5, 1, -1)))
        return banc.simuler(s, d, regle)[0].p1.values

    lo, hi = 0.0, 1.0
    r0 = np.random.default_rng(1)
    for _ in range(12):
        c = (lo + hi) / 2
        nn = np.mean([len(un(c, r0)) for _ in range(4)])
        lo, hi = (c, hi) if nn < cible else (lo, c)
    c = (lo + hi) / 2
    return np.array([un(c, rng).sum() for _ in range(n_tir)])


if __name__ == "__main__":
    lignes = []
    n_tests = 24
    for ins, u in (("MNQ", 5), ("MNQ", 15), ("MES", 15)):
        B = prep(ins, u)
        banc = Banc(B)
        h2 = (B.t >= MILIEU).values
        for seuil in (0, 70):
            for regle in REGLES:
                idx, sens = entrees(B, banc, regle, seuil)
                T, ctrl = banc.simuler(idx, sens, regle)
                d = dict(cas=f"{u} min {ins}", seuil=seuil, regle=regle)
                for moitie, d0, d1 in (("H1", DEBUT, MILIEU), ("H2", MILIEU, FIN)):
                    d.update({f"{moitie}_{k}": v for k, v in mesure(T, d0, d1).items()})
                ans = (FIN - DEBUT).days / AN
                dd, pnl = creux(T.p1.values), T.p1.sum()
                jour = pd.Series(T.p1.values).groupby(pd.to_datetime(T.tx).dt.date.values).sum()
                n_ftmo = int(np.floor(min(8000 / dd if dd > 0 else 99, 4000 / max(-jour.min(), 1))))
                d.update(rc_total=(pnl / ans) / dd if dd > 0 else np.nan, taille_ftmo=n_ftmo,
                         pct_an_ftmo=100 * n_ftmo * pnl / ans / 100000)
                if regle in ("S1", "S2", "S3") and ctrl:
                    # sortie au hasard : même nombre attendu de sorties anticipées, aux mêmes points de contrôle
                    q = int((T.raison == "anticipée").sum()) / ctrl
                    rng = np.random.default_rng(5669)
                    hz = np.array([banc.simuler(idx, sens, regle, hasard_q=q, rng=rng)[0].pipe(
                        lambda x: x[x.t >= MILIEU].p1.sum()) for _ in range(200)])
                    d["H2_p_sortie_hasard"] = ((hz >= d["H2_pnl"]).sum() + 1) / (len(hz) + 1)
                d["passe_pnl"] = bool(d["H1_pnl"] > 0 and d["H2_pnl"] > 0)
                if d["passe_pnl"] and regle != "56":
                    for ref in "BL":
                        hz = hasard_entrees(B, banc, regle, idx, sens, h2, ref, np.random.default_rng(5669))
                        d[f"H2_p{ref}"] = ((hz >= d["H2_pnl"]).sum() + 1) / (N_TIR + 1)
                    d["passe"] = bool(d["H2_pB"] < 0.05 / n_tests and d["H2_pL"] < 0.05 / n_tests)
                lignes.append(d)
                print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()}, flush=True)
    R = pd.DataFrame(lignes)
    R.to_csv(os.path.join(ICI, "sortie_resultats.csv"), index=False)
    cols = ["cas", "seuil", "regle", "H1_n", "H1_pnl", "H1_rc", "H2_n", "H2_pnl", "H2_rc", "H2_anticipees",
            "H2_p_sortie_hasard", "H2_pB", "H2_pL", "rc_total", "taille_ftmo", "pct_an_ftmo"]
    print("\n" + R.reindex(columns=cols).round(3).to_string(index=False))
