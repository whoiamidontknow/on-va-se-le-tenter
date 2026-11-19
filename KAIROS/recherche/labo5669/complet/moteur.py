"""Moteur générique sur toutes les bougies du Relevé complet (jalon B).

Règles (celles de Strat5669, validées par simu56 contre le testeur) :
  - décision à la clôture de la bougie i, remplissage à l'ouverture de i + 1 avec 1 tick de glissement ;
  - pas d'entrée sur une bougie `fin` (fenêtre 00:20-22:15 Paris dépassée ou à plat 15:59 Chicago) ;
  - stop = entrée ∓ k × ATR, objectif = entrée ± R × k × ATR (ATR des vrais prix de la bougie signal) ;
    sur la bougie de remplissage en ticks entiers arrondis, ensuite au premier tick qui atteint le niveau ;
  - stop d'abord si stop et objectif tombent dans la même bougie ; le stop prend 1 tick de glissement ;
  - sortie forcée : bougie `fin` -> remplie à l'ouverture suivante (testée avant la sortie au temps) ;
  - sortie au temps : clôture demandée à la N-ième bougie en position, remplie à l'ouverture suivante ;
  - commission 1,25 $ par contrat et par côté ; une position à la fois par instrument ;
  - après un stop / objectif sur la bougie j, une nouvelle décision est possible dès la clôture de j ;
    après une sortie au marché remplie à l'ouverture de m, dès la clôture de m.

Usage : I = issues(B, k_atr, R, N) calcule, pour CHAQUE bougie et chaque sens, l'issue d'un trade décidé
à sa clôture ; puis sequence(I, idx, sens) enchaîne une suite de décisions (une position à la fois).
"""
import numpy as np
import pandas as pd

TICK = 0.25
COMM = 1.25


def issues(B, k_atr, tpr, nbar, pas_max=None):
    """Retourne un dict de tableaux (longueur = nb de bougies) : p1_L, p1_S (P&L par contrat),
    r_L, r_S (raison : 0 stop, 1 objectif, 2 temps, 3 fin, -1 impossible), lib_L, lib_S (index de la
    première bougie dont la clôture peut décider une nouvelle entrée)."""
    n = len(B)
    O, H, L = B.o.values, B.h.values, B.l.values
    fin = B.fin.values.astype(bool)
    dist = k_atr * B.atr.values
    vp = B.attrs["val_point"]
    i = np.arange(n)
    e = i + 1                                           # bougie de remplissage
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
                nsl = np.maximum(1, np.round(dist / TICK))
                ntp = np.maximum(1, np.round(tpr * dist / TICK))
            else:
                nsl = np.ceil(dist / TICK - 1e-9)
                ntp = np.ceil(tpr * dist / TICK - 1e-9)
            stop, tp = fill - d * nsl * TICK, fill + d * ntp * TICK
            hi, lo = H[bb], L[bb]
            ts = act & ((lo <= stop) if d > 0 else (hi >= stop))
            tt = act & ((hi >= tp) if d > 0 else (lo <= tp)) & ~ts
            p1[ts] = ((stop - d * TICK - fill) * d)[ts]
            p1[tt] = ((tp - fill) * d)[tt]
            rs[ts], rs[tt] = 0, 1
            lib[ts | tt] = bb[ts | tt]
            ouvert &= ~(ts | tt)
            # sortie au marché demandée à la clôture de b : fin (prioritaire) ou temps (N-ième bougie)
            mk = ouvert & (b < n) & (fin[bb] | (j == nbar - 1))
            nx = np.minimum(bb + 1, n - 1)
            okx = mk & (bb + 1 < n)
            p1[okx] = ((O[nx] - d * TICK - fill) * d)[okx]
            rs[okx] = np.where(fin[bb], 3, 2)[okx]
            lib[okx] = (bb + 1)[okx]
            ouvert &= ~mk
        out[f"p1_{s}"] = p1 * vp - 2 * COMM
        out[f"r_{s}"] = rs
        out[f"lib_{s}"] = lib
    return out


def sequence(I, idx, sens):
    """idx : index de bougies de décision, triés ; sens : +1 / -1. Retourne (idx pris, sens, P&L / contrat)."""
    libL, libS, pL, pS = I["lib_L"], I["lib_S"], I["p1_L"], I["p1_S"]
    libre = -1
    pris, ss, pn = [], [], []
    for i, d in zip(idx, sens):
        if i < libre:
            continue
        p = pL[i] if d > 0 else pS[i]
        if not np.isfinite(p):
            continue
        pris.append(i)
        ss.append(d)
        pn.append(p)
        libre = libL[i] if d > 0 else libS[i]
    return np.array(pris, dtype=np.int64), np.array(ss), np.array(pn)


def mesures(pn, qty=2):
    pn = np.asarray(pn) * qty
    if len(pn) == 0:
        return dict(n=0, gain=np.nan, pnl=0.0, par_trade=np.nan, baisse_max=0.0)
    cum = np.cumsum(pn)
    dd = np.max(np.maximum.accumulate(np.concatenate([[0], cum]))[1:] - cum)
    return dict(n=len(pn), gain=float((pn > 0).mean()), pnl=float(pn.sum()), par_trade=float(pn.mean()), baisse_max=float(dd))


def hasard(B, I, periode, idx, sens, n_tir=1000, ref="A", rng=None):
    """Tirages au hasard calés sur une stratégie (idx, sens) : mêmes bougies candidates (période, hors fin),
    même répartition horaire, même nombre de trades (densité réglée), même part de longs (réf. A) ou
    sens tiré parmi les déclencheurs de la bougie (réf. B : bits hei / sF / sM / tl / lvl / clx / div)."""
    rng = rng or np.random.default_rng(5669)
    cand = np.flatnonzero(periode & ~B.fin.values.astype(bool) & np.isfinite(I["p1_L"]))
    h = B.t.dt.hour.values
    w56 = np.bincount(h[idx], minlength=24).astype(float)
    wc = np.bincount(h[cand], minlength=24).astype(float)
    w = np.where(wc > 0, w56 / np.maximum(wc, 1), 0)
    w = w / w.max()
    p_long = (np.asarray(sens) > 0).mean() if len(sens) else 0.5
    if ref == "B":
        L = B[["hei_L", "sF_L", "sM_L", "tl_L", "lvl_L", "clx_L", "div_L"]].values.any(axis=1)
        S = B[["hei_S", "sF_S", "sM_S", "tl_S", "lvl_S", "clx_S", "div_S"]].values.any(axis=1)
        cand = cand[L[cand] | S[cand]]
    n_cible = len(sequence(I, idx, sens)[0])

    def un(c, r):
        sel = cand[r.random(len(cand)) < c * w[h[cand]]]
        if ref == "A":
            s = np.where(r.random(len(sel)) < p_long, 1, -1)
        else:
            l, sh = L[sel], S[sel]
            s = np.where(l & ~sh, 1, np.where(sh & ~l, -1, np.where(r.random(len(sel)) < 0.5, 1, -1)))
        return sequence(I, sel, s)[2]

    lo, hi = 0.0, 1.0
    r0 = np.random.default_rng(1)
    for _ in range(16):
        c = (lo + hi) / 2
        n = np.mean([len(un(c, r0)) for _ in range(10)])
        lo, hi = (c, hi) if n < n_cible else (lo, c)
    c = (lo + hi) / 2
    return pd.DataFrame([mesures(un(c, rng)) for _ in range(n_tir)])
