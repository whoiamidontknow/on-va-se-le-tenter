"""Moteur d'exécution vectorisé (une position à la fois par graphique), conventions de STRATEGIE_V1.pine et
de tools/strategie/engine.py :

- signal connu à la CLÔTURE de la barre g -> entrée au marché à l'OUVERTURE (vraie) de g+1, +1 tick contre nous ;
  pas d'entrée si g+1 suit une coupure. Entrée « limite au milieu de la bougie signal » : ordre au milieu
  (vrai haut + vrai bas)/2 de la bougie g, valable N barres, rempli si le prix le TRAVERSE d'un tick, au
  niveau (ou à l'ouverture si elle est déjà au-delà) + 1 tick (convention de correlations/confluence) ;
- stop : rempli au stop -1 tick, ou à l'ouverture si elle a sauté le stop ; sur la barre d'entrée, au stop ;
- objectif (mode « prudent », défaut) : rempli seulement si le prix DÉPASSE l'objectif d'un tick, puis -1 tick ;
  mode « tradingview » : rempli au toucher, sans glissement (ordre limite du testeur) ;
- stop ET objectif dans la même barre : STOP ;
- break-even, stop suiveur : recalculés à la CLÔTURE (comme le Pine), actifs à la barre suivante ;
  suiveur ATR = clôture - k x ATR (x_trMode « ATR ») ; suiveur swing = chaque nouveau pivot confirmé ± marge ;
- sorties sur signal (flèche opposée, Heishinator, fin de séance, temps max) : décidées à la clôture,
  exécutées à l'ouverture suivante -1 tick ;
- coût : 1 tick de glissement par côté + 1,25 $ par contrat et par côté.
- un trade encore ouvert à la fin d'une série est ABANDONNÉ (comme engine.py) ; il bloque la série.

Chaque « configuration de trade » (entrée, stop, sortie) est simulée UNE fois pour toutes les paires
(barre signal, sens) possibles : l'issue d'un trade ne dépend pas des autres trades. Le choix des trades
effectivement pris (une position à la fois, maximum par jour) est fait ensuite par `selection`.
"""
import numpy as np

POURQUOI = {1: 'stop', 2: 'objectif', 3: 'signal', 4: 'fin_seance', 5: 'temps', 6: 'stop_depasse', 7: 'plafond'}


def simuler(U, g, d, tc, remplissage='prudent', heishi_mode='flip', plafond=2000, fixes=None):
    A = U.A; N = U.N
    g = np.asarray(g, np.int64); d = np.asarray(d, np.int64)
    P = len(g)
    tick = A['tick'][g]; slip = tick * U.slip_ticks
    comm = 2 * U.comm_cote / A['pv'][g]
    segend = A['seg_end'][g]
    ratr_g = A['ratr'][g]
    filled = np.zeros(P, bool); closed = np.zeros(P, bool)
    fbar = np.full(P, -1, np.int64); xbar = np.full(P, -1, np.int64)
    R = np.full(P, np.nan); pts = np.full(P, np.nan); why = np.zeros(P, np.int8); nbar = np.zeros(P, np.int32)
    free = g.copy()
    # ---------------- remplissage de l'entrée
    if tc['entree'] == 'marche':
        f = g + 1
        okf = (f <= segend)
        fj = np.minimum(f, N - 1)
        okf &= ~A['brk'][fj]
        px = A['ro'][fj] + d * slip
    else:
        n_lim = int(tc['limite_validite'])
        lv = (A['rh'][g] + A['rl'][g]) / 2
        side = d * (A['rc'][g] - lv) > 0
        pend = side.copy()
        f = np.full(P, -1, np.int64); px = np.full(P, np.nan)
        for s in range(1, n_lim + 1):
            j = g + s
            jj = np.minimum(j, N - 1)
            pend &= (j <= segend) & ~A['brk'][jj]
            lo, hi, op = A['rl'][jj], A['rh'][jj], A['ro'][jj]
            hit = pend & np.where(d == 1, lo <= lv - tick, hi >= lv + tick)
            f[hit] = j[hit]
            px[hit] = np.where(d == 1, np.minimum(lv, op) + tick, np.maximum(lv, op) - tick)[hit]
            pend &= ~hit
        okf = f >= 0
        blq = side & ~okf
        free[blq] = np.minimum(g + n_lim, segend)[blq]     # ordre en attente : bloque jusqu'à expiration
    okf &= ratr_g > 0
    # ---------------- stop initial et objectif
    mode = tc['x_stopMode_in']
    k = float(tc['x_atrK_in'])
    if mode == 'ATR × k':
        risk = k * ratr_g; stop = px - d * risk
    elif mode == 'Dernier swing + marge':
        pl, ph, swl, swh = U.pivots(int(tc['x_swL']), int(tc['x_swR']))
        sw = np.where(d == 1, swl[g], swh[g])
        val = ~np.isnan(sw) & (d * (A['rc'][g] - sw) > 0)
        stop = np.where(val, sw - d * tc['x_swMarge'] * tick, A['rc'][g] - d * k * ratr_g)
        risk = d * (px - stop)
    else:
        fp = fixes[g]
        risk = fp.astype(float); stop = px - d * risk
    rnorm = np.where(risk > 0, risk, k * ratr_g)
    tp = float(tc['x_tpR_in'] or 0)
    tgt = px + d * tp * risk if tp > 0 else np.full(P, np.nan)
    tgt = np.where(risk > 0, tgt, np.nan)
    # ---------------- options de sortie
    trm = tc['x_trMode_in']; trK = float(tc['x_trK']); trAct = float(tc['x_trAct'])
    beR = float(tc['x_beR'] or 0); beTk = float(tc['x_beTk'])
    oppA = bool(tc['x_oppArr_in']); oppH = bool(tc['x_oppHei_in'])
    fin = tc.get('fin_min'); tmax = int(tc['temps_max_barres'] or 0)
    if trm == 'Sous chaque nouveau swing' or mode == 'Dernier swing + marge':
        pl, ph, swl, swh = U.pivots(int(tc['x_swL']), int(tc['x_swR']))
    finap = (A['paris_min_close'] >= fin) if fin is not None else None
    tvfill = remplissage == 'tradingview'
    # ---------------- boucle barre par barre sur les trades vivants
    I = np.nonzero(okf)[0]
    filled[I] = True; fbar[I] = f[I]
    j = f[I].copy(); dd = d[I]; st = stop[I].copy(); tg = tgt[I]; rk = risk[I]; pp = px[I]
    best = pp.copy(); bed = np.zeros(len(I), bool); nb = np.zeros(len(I), np.int32)
    sl = slip[I]; tk = tick[I]; se = segend[I]; f0 = f[I]
    bad = rk <= 0
    while len(I):
        # fin de série : abandon (le trade bloque la série)
        end = j >= se
        if end.any():
            free[I[end]] = se[end]
            keep = ~end
            I, j, dd, st, tg, rk, pp, best, bed, nb, sl, tk, se, f0, bad = (x[keep] for x in (I, j, dd, st, tg, rk, pp, best, bed, nb, sl, tk, se, f0, bad))
            if not len(I):
                break
        lo, hi, op, cl = A['rl'][j], A['rh'][j], A['ro'][j], A['rc'][j]
        hs = np.where(dd == 1, lo <= st, hi >= st) & ~bad
        pst = np.where(j == f0, st, np.where(dd == 1, np.minimum(op, st), np.maximum(op, st)))
        with np.errstate(invalid='ignore'):
            if tvfill:
                ht = ~hs & np.where(dd == 1, hi >= tg, lo <= tg)
            else:
                ht = ~hs & np.where(dd == 1, hi >= tg + tk, lo <= tg - tk)
        xp = np.where(hs, pst - dd * sl, np.where(tvfill, tg, tg - dd * sl))
        code = np.where(hs, 1, 2)
        rem = ~hs & ~ht
        # ---- mise à jour à la clôture (barres restantes)
        nb = nb + rem
        best = np.where(rem, np.where(dd == 1, np.maximum(best, hi), np.minimum(best, lo)), best)
        with np.errstate(invalid='ignore', divide='ignore'):
            gain = np.where(rk > 0, dd * (best - pp) / rk, 0.0)
        if beR > 0:
            m = rem & ~bed & (gain >= beR) & ~bad
            be = pp + dd * beTk * tk
            st = np.where(m, np.where(dd == 1, np.maximum(st, be), np.minimum(st, be)), st)
            bed |= m
        if trm == 'ATR':
            m = rem & (gain >= trAct) & ~bad
            cand = cl - dd * trK * A['ratr'][j]
            with np.errstate(invalid='ignore'):
                st = np.where(m & ~np.isnan(cand), np.where(dd == 1, np.maximum(st, cand), np.minimum(st, cand)), st)
        elif trm == 'Sous chaque nouveau swing':
            m = rem & (gain >= trAct) & ~bad
            cand = np.where(dd == 1, pl[j] - tc['x_swMarge'] * tk, ph[j] + tc['x_swMarge'] * tk)
            with np.errstate(invalid='ignore'):
                st = np.where(m & ~np.isnan(cand), np.where(dd == 1, np.maximum(st, cand), np.minimum(st, cand)), st)
        sx = np.zeros(len(I), np.int8)
        sx = np.where(bad, 6, sx)
        if finap is not None:
            sx = np.where((sx == 0) & finap[j], 4, sx)
        if oppA:
            sx = np.where((sx == 0) & (A['fleche'][j] == -dd), 3, sx)
        if oppH:
            hsig = A['flip'][j] if heishi_mode == 'flip' else A['bull'][j]
            sx = np.where((sx == 0) & (hsig == -dd), 3, sx)
        if tmax > 0:
            sx = np.where((sx == 0) & (nb >= tmax), 5, sx)
        sx = np.where((sx == 0) & (nb >= plafond), 7, sx)
        sx = np.where(rem, sx, 0)
        xs = rem & (sx > 0)
        xp = np.where(xs, A['ro'][np.minimum(j + 1, N - 1)] - dd * sl, xp)
        code = np.where(xs, sx, code)
        out = ~rem | xs
        if out.any():
            o = I[out]
            closed[o] = True; xbar[o] = j[out]; free[o] = j[out]
            p_ = dd[out] * (xp[out] - pp[out]) - comm[o]
            pts[o] = p_; R[o] = p_ / rnorm[o]; why[o] = code[out]; nbar[o] = nb[out]
            keep = ~out
            I, j, dd, st, tg, rk, pp, best, bed, nb, sl, tk, se, f0, bad = (x[keep] for x in (I, j, dd, st, tg, rk, pp, best, bed, nb, sl, tk, se, f0, bad))
        j = j + 1
    usd = pts * A['pv'][g]
    return dict(filled=filled, closed=closed, fbar=fbar, xbar=xbar, R=R, pts=pts, usd=usd, why=why, nbar=nbar, free=free,
                px=px, risk=rnorm)


def selection(cand, g, res, maxjour=0, pdate=None, sid=None):
    """Parcourt les paires candidates (triées par barre) : une position à la fois par série ; maximum de
    trades par jour (Paris). Renvoie les indices des paires dont le trade est pris ET clôturé."""
    filled, closed, free = res['filled'], res['closed'], res['free']
    last = -1; cnt = {}; out = []
    gl = g[cand].tolist(); fl = filled[cand].tolist(); cll = closed[cand].tolist(); frl = free[cand].tolist()
    if maxjour:
        kl = (sid[g[cand]].astype(np.int64) * 100000000 + pdate[g[cand]]).tolist()
    for n_, p in enumerate(cand.tolist()):
        gi = gl[n_]
        if gi < last:
            continue
        if not fl[n_] and frl[n_] == gi:
            continue                     # aucun ordre (niveau limite du mauvais côté)
        if maxjour:
            kk = kl[n_]
            c = cnt.get(kk, 0)
            if c >= maxjour:
                continue
            cnt[kk] = c + 1
        last = frl[n_]
        if fl[n_] and cll[n_]:
            out.append(p)
    return np.array(out, np.int64)
