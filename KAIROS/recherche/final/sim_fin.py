"""Simulateur de l'optimiseur final (FIN) : issue d'un trade pris sur CHAQUE barre, avec les gestions de
STRATEGIE_V1.pine que le moteur commun ne sait pas faire seul :

  - objectif « Prochain niveau » (f_tp_niveau : familles pivots A/M/W, zone Detector, Monday, sessions ;
    rrMin ; marge de 4 ticks avant le niveau ; repli « Objectif en R » si aucun niveau n'offre le ratio) ;
  - sortie partielle 50 % au 1er niveau, puis stop au prix d'entrée + 4 ticks (partBE), le reste allant
    au 2e niveau (partRest = « 2e niveau ») ou restant sans objectif (« Stop seulement » : break-even,
    sortie Heishinator opposée, fin de séance) ;
  - sortie Heishinator opposée (oppHei), break-even (beR, beTk), sortie après N bougies (tBar).

La boucle de vie du trade est CELLE DE moteur.backtest (mêmes conventions : entrée à l'ouverture suivante
+ 1 tick de glissement, stop prioritaire dans la même barre, ordres limites remplis si le prix dépasse de
1 tick, sorties à la clôture exécutées à l'ouverture suivante, break-even actif à la barre suivante), avec le
partiel posé sur un niveau propre à chaque trade au lieu d'un multiple de R fixe.
Vérifié contre moteur.backtest par `verifier()` (R fixe, break-even, tBar, Heishinator, objectif niveau, partiel).

Comme dans taux_combinatoire/bib_wrx.py : un trade ne dépend que de sa barre de signal, donc la table
« issue d'un trade pris à chaque barre » est exacte ; la règle « une position à la fois » est appliquée
après coup (glouton).
"""
from __future__ import annotations

import math

import numpy as np

NS_MIN = 60_000_000_000


class Jeu:
    """Barres d'un jeu prêtes pour la simulation. `lev[(fam, d)]` : matrice (n, m) des niveaux de la famille
    `fam` utilisables comme objectif d'un trade de sens d (+1 long, -1 short), NaN si absent."""

    def __init__(self, M, df, instrument, fin, interdite, lev, tick_default=0.25):
        b = M.barres(df)
        spec = M.instrument(instrument)
        self.pv, self.tick, self.comm = spec['point'], spec['tick'], spec['commission_cote']
        self.slip = 1 * self.tick
        self.trav = 1 * self.tick
        self.n = b.n
        self.o, self.h, self.l, self.c = (x.tolist() for x in (b.o, b.h, b.l, b.c))
        self.atr = b.atr.tolist()
        self.t_ouv, self.t_clo = b.t_ouv, b.t_clo
        self.fin = fin.tolist(); self.intl = interdite.tolist()
        self.xL = df['hei_flip_bas'].to_numpy(bool).tolist()      # sortie d'un long
        self.xS = df['hei_flip_haut'].to_numpy(bool).tolist()     # sortie d'un short
        self.lev = lev
        self.retard = 0.5 * b.ut * NS_MIN
        self.tcl = b.t_clo
        self.touv = b.t_ouv
        self.ut = b.ut

    # ------------------------------------------------------------------------------------------------
    def niveaux(self, fam, d, i, px, risk, rmin, marge, rnd):
        """-> (t1, l1, t2) : 1er objectif (niveau - marge) offrant >= rmin x risque, et 2e objectif (niveau
        strictement au-delà du 1er), ou (None, None, None). Miroir exact de f_tp_niveau du Pine."""
        row = self.lev[(fam, d)][i]
        v = row[np.isfinite(row)]
        if not len(v):
            return None, None, None
        o_ = np.round((v - d * marge) / self.tick) * self.tick
        dist = d * (o_ - px)
        ok = (dist > 0) & (dist >= rmin * risk) & (d * (v - px) > 0)
        if not ok.any():
            return None, None, None
        j = np.flatnonzero(ok)[np.argmin(dist[ok])]
        t1, l1, d1 = float(o_[j]), float(v[j]), float(dist[j])
        ok2 = (d * (v - l1) > self.tick / 2) & (dist > d1)
        t2 = float(o_[ok2][np.argmin(dist[ok2])]) if ok2.any() else None
        return t1, l1, t2

    # ------------------------------------------------------------------------------------------------
    def trade(self, i, d, g, det=False):
        """Issue du trade de signal i, sens d. -> tuple ou None. g : dict de gestion (voir GESTION_NOMS)."""
        n = self.n
        o, h, l, c = self.o, self.h, self.l, self.c
        tick, slip, trav, pv, comm = self.tick, self.slip, self.trav, self.pv, self.comm
        f = i + 1
        if f >= n - 0 or f > n - 1:
            return None
        if self.fin[f] or self.intl[f]:
            return None
        if self.touv[f] - self.tcl[i] > self.retard:
            return None
        a = self.atr[i]
        if not (a > 0) or a != a:
            return None

        def rnd(x):
            return round(x / tick) * tick

        px = o[f] + d * slip
        s = rnd(px - d * g['k'] * a)
        risk = d * (px - s)
        if not (risk > 0):
            return None
        st = s
        # ---- objectif(s)
        tg = None; pp = None; nom_o = 'R%g' % g.get('R', 0)
        tp = g['tp']
        if tp == 'R':
            tg = rnd(px + d * g['R'] * risk)
        elif tp == 'Rpart':                              # test de vérification seulement
            pp = rnd(px + d * g['R1'] * risk); tg = rnd(px + d * g['R'] * risk)
        else:                                            # 'niv'
            t1, l1, t2 = self.niveaux(g['fam'], d, i, px, risk, g['rr'], g['marge'] * tick, rnd)
            nom_o = 'niveau' if t1 is not None else 'repli_R%g' % g['repliR']
            if t1 is None:
                tg = rnd(px + d * g['repliR'] * risk)    # tpSans = « Objectif en R »
            elif g['part']:
                pp = t1
                tg = t2 if g['part'] == 1 else None
            else:
                tg = t1
        frac = g.get('frac', 0.5)
        tg0, pp0 = tg, pp
        nmax = g['tBar']; hei = g['hei']
        be = g['be']; be_ticks = g.get('be_ticks', 4)
        xl = self.xL if d == 1 else self.xS
        fin, intl = self.fin, self.intl
        best = px; worst = px
        be_ok = False; be_pend = False; nb = 0
        typ = 'stop'
        part = 0.0; rest = 1.0; part_ok = False
        xp = None; motif = None; x = f; kind = 'intra'
        ouv = True                                       # entrée au marché
        j = f
        while True:
            oj, hj, lj, cj = o[j], h[j], l[j], c[j]
            if j > f:
                if intl[j]:
                    xp = oj - d * slip; motif = 'heure'; x = j; kind = 'ouv'
                    best = max(best, oj) if d == 1 else min(best, oj)
                    worst = min(worst, oj) if d == 1 else max(worst, oj)
                    break
                if st is not None and d * (oj - st) <= 0:
                    xp = oj - d * slip; motif = typ; x = j; kind = 'ouv'
                    worst = min(worst, oj) if d == 1 else max(worst, oj)
                    break
                if pp is not None and not part_ok and d * (oj - pp) >= 0 and (tg is None or d * (pp - tg) < 0):
                    part = frac * d * (oj - px); rest = 1.0 - frac; part_ok = True
                    be_pend = True
                if tg is not None and d * (oj - tg) >= 0:
                    xp = oj; motif = 'objectif'; x = j; kind = 'ouv'
                    best = max(best, oj) if d == 1 else min(best, oj)
                    break
            adv = lj if d == 1 else hj
            fav = hj if d == 1 else lj
            if st is not None and d * (adv - st) <= 0:
                xp = st - d * slip; motif = typ; x = j
                best = max(best, fav) if d == 1 else min(best, fav)
                worst = min(worst, st) if d == 1 else max(worst, st)
                break
            if pp is not None and not part_ok and d * (fav - pp) >= trav and (tg is None or d * (pp - tg) < 0):
                part = frac * d * (pp - px); rest = 1.0 - frac; part_ok = True
                be_pend = True
            if tg is not None and d * (fav - tg) >= trav:
                xp = tg; motif = 'objectif'; x = j
                best = max(best, tg) if d == 1 else min(best, tg)
                worst = min(worst, adv) if d == 1 else max(worst, adv)
                break
            best = max(best, fav) if d == 1 else min(best, fav)
            worst = min(worst, adv) if d == 1 else max(worst, adv)
            nb += 1
            if fin[j]:
                xp = cj - d * slip; motif = 'heure'; x = j; kind = 'clo'
                break
            if j + 1 >= n:
                xp = cj - d * slip; motif = 'fin_donnees'; x = j; kind = 'clo'
                break
            if (hei and xl[j]) or (nmax and nb >= nmax):
                motif = 'signal' if (hei and xl[j]) else 'temps'
                x = j + 1; kind = 'ouv'; on = o[x]
                xp = on - d * slip
                best = max(best, on) if d == 1 else min(best, on)
                worst = min(worst, on) if d == 1 else max(worst, on)
                break
            if (be and not be_ok and d * (best - px) >= be * risk) or (be_pend and not be_ok):
                nv = px + d * be_ticks * tick
                if st is None or d * (nv - st) > 0:
                    st = nv; typ = 'stop_be'
                be_ok = True; be_pend = False
            j += 1
        if part_ok:
            motif = 'partiel+' + motif
        pts = part + rest * d * (xp - px)
        pnl = pts * pv - 2 * comm
        risk_usd = risk * pv
        sor = self.t_ouv[x] if kind != 'clo' else self.t_clo[x]
        klibre = x - 1 if kind == 'ouv' else x
        res = (pnl / risk_usd, pnl, risk_usd, min(0.0, d * (worst - px)) * pv, max(0.0, d * (best - px)) * pv,
               int(self.t_ouv[f]), int(sor), klibre, motif)
        if det:
            return res + ((px, s, tg0, pp0, xp, nom_o),)
        return res

    def table(self, g, masque):
        """Tables (2, n) : ok, r, pnl, risque, mae, mfe, ent, sor, klibre (sens 0 = long, 1 = short).
        `masque` : barres où l'on calcule (les autres restent ok=False)."""
        n = self.n
        T = dict(ok=np.zeros((2, n), bool), r=np.zeros((2, n)), pnl=np.zeros((2, n)), risque=np.zeros((2, n)),
                 mae=np.zeros((2, n)), mfe=np.zeros((2, n)), ent=np.zeros((2, n), np.int64),
                 sor=np.zeros((2, n), np.int64), klibre=np.zeros((2, n), np.int64))
        mot = {}
        for i in np.flatnonzero(masque).tolist():
            for di, d in ((0, 1), (1, -1)):
                r = self.trade(i, d, g)
                if r is None:
                    continue
                T['ok'][di, i] = True
                (T['r'][di, i], T['pnl'][di, i], T['risque'][di, i], T['mae'][di, i], T['mfe'][di, i],
                 T['ent'][di, i], T['sor'][di, i], T['klibre'][di, i], m) = r
                mot[m] = mot.get(m, 0) + 1
        T['gagne'] = T['pnl'] > 0
        T['motifs'] = mot
        return T


def gestion_defaut(**kw):
    g = dict(k=2.0, tp='R', R=1.5, R1=1.0, rr=1.5, fam='piv', part=0, hei=0, be=0.0, be_ticks=4, tBar=0,
             marge=4, repliR=1.5, frac=0.5)
    g.update(kw)
    return g
