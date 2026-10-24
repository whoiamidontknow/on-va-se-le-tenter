"""Affinage d'entrée : contexte / signal sur l'unité S (15m, 30m, 60m), déclenchement fin sur l'unité X
(1m, 2m, 3m, 5m) dans une fenêtre de N minutes après la CLÔTURE de la bougie signal.

Tout est backtesté en mono-UT sur les barres X avec le moteur commun (moteur.backtest) : les signaux S sont
projetés sur X par l'heure de clôture (aucun accès au futur) :
  a(i) = 1re barre X qui OUVRE à/après la clôture de la bougie S i (refus si trou > 0,5 UT X) ;
  - entrée « direct »  : signal posé sur la barre X a-1 -> achat à l'OUVERTURE de a (= ouverture de la
    bougie S suivante, référence) ;
  - entrée « déclencheur » : 1re barre X k de [a, a+W) dont la clôture vérifie la condition -> achat à
    l'ouverture de k+1 ; rien dans la fenêtre -> signal annulé ;
  - entrée « limite » : ordre limite posé à la clôture S (barre a-1), valable W barres X, prix fixé à cet
    instant (milieu de la bougie S, EMA50 X, clôture S - 0,25 ATR S).
Stops (connus à la clôture de la barre de signal X) : swing X (plus bas/haut des 5 dernières barres X),
extrême de la bougie S (« niveau de protection »), 2 ATR X, 2 ATR S (taille de stop de la référence).
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(ICI, '..', '..', 'moteur')]
import moteur as M  # noqa: E402

NS_MIN = M.NS_MIN

# ─────────────────────────────── familles de signaux S (long, short) ───────────────────────────────
def _b(df, *cols):
    out = np.zeros(len(df), bool)
    for c in cols:
        if c in df:
            out |= df[c].fillna(False).to_numpy().astype(bool)
    return out


def _feu(df, seuil=0.6):
    """Bascule du Feu : la part long (ou short) franchit le seuil (première barre)."""
    fl = df['feu_l'].astype(float).to_numpy(); fs = df['feu_s'].astype(float).to_numpy()
    tot = fl + fs
    pl = np.where(tot > 0, fl / np.where(tot > 0, tot, 1), np.nan)
    L = pl >= seuil; S = (1 - pl) >= seuil
    L &= ~np.r_[False, L[:-1]]; S &= ~np.r_[False, S[:-1]]
    return L, S


FAMILLES = {
    'sigF': lambda d: (_b(d, 'sig_long_fort'), _b(d, 'sig_short_fort')),
    'sigFM': lambda d: (_b(d, 'sig_long_fort', 'sig_long_moyen'), _b(d, 'sig_short_fort', 'sig_short_moyen')),
    'hei': lambda d: (_b(d, 'hei_flip_haut'), _b(d, 'hei_flip_bas')),
    'clx': lambda d: (_b(d, 'clx_buy'), _b(d, 'clx_sell')),
    'tl': lambda d: (_b(d, 'tl_cassure_haut'), _b(d, 'tl_cassure_bas')),
    'det': lambda d: (_b(d, 'zb_mitigee'), _b(d, 'zh_mitigee')),      # zone baissière cassée -> long
    'feu': _feu,
}


def signaux_S(dfS, famille, filtre):
    L, S = FAMILLES[famille](dfS)
    if filtre == 'trend':
        # TREND de l'unité au-dessus (1H pour 15m/30m, 4H pour 60m), bougie clôturée
        col = 'trend_60' if (M.barres(dfS).ut < 60) else 'trend_240'
        t = dfS[col].fillna(False).to_numpy().astype(bool)
        okc = 'ok_' + col
        ok = dfS[okc].fillna(False).to_numpy().astype(bool) if okc in dfS else np.ones(len(dfS), bool)
        L = L & t & ok
        S = S & ~t & ok
    return L & ~S, S & ~L


# ─────────────────────────────── projection S -> X ───────────────────────────────
class Contexte:
    """Pré-calculs communs à un couple (dfX, dfS) d'un marché."""

    def __init__(self, dfX, dfS, instrument):
        self.dfX, self.dfS = dfX, dfS
        self.bx, self.bs = M.barres(dfX), M.barres(dfS)
        bx, bs = self.bx, self.bs
        self.instrument = instrument
        self.tick = M.INSTRUMENTS[instrument]['tick']
        a = np.searchsorted(bx.t_ouv, bs.t_clo, side='left')
        ac = np.clip(a, 0, bx.n - 1)
        self.a = a
        self.ok = (a >= 1) & (a < bx.n - 1) & ((bx.t_ouv[ac] - bs.t_clo) <= 0.5 * bx.ut * NS_MIN) & \
                  ((bx.t_ouv[ac] - bs.t_clo) >= 0)
        o, h, l, c = bx.o, bx.h, bx.l, bx.c
        # barre précédente contiguë (pas de trou)
        contig = np.r_[False, np.diff(bx.t_ouv) == int(round(bx.ut * NS_MIN))]
        hp = np.r_[np.nan, h[:-1]]; lp = np.r_[np.nan, l[:-1]]
        e50 = dfX['ema50'].to_numpy(float) if 'ema50' in dfX else M.atr_wilder(h, l, c) * np.nan
        sl = lambda *c_: _b(dfX, *c_)
        bleu = sl('hei_bleu')
        self.declencheurs = {
            'hei_flip': (sl('hei_flip_haut'), sl('hei_flip_bas')),
            'hei_aligne': (bleu, ~bleu),
            'cassure': (contig & (c > hp), contig & (c < lp)),
            'sigX': (sl('sig_long_fort', 'sig_long_moyen'), sl('sig_short_fort', 'sig_short_moyen')),
            'rejet_ema': ((l <= e50) & (c > e50), (h >= e50) & (c < e50)),
        }
        # stops swing X (5 barres) connus à la clôture
        self.swing_bas = pd.Series(l).rolling(5, min_periods=1).min().to_numpy()
        self.swing_haut = pd.Series(h).rolling(5, min_periods=1).max().to_numpy()
        self.e50 = e50
        # ATR S projeté : dernière bougie S CLÔTURÉE à la clôture de chaque barre X
        js = np.searchsorted(bs.t_clo, bx.t_clo, side='right') - 1
        self.atrS_x = np.where(js >= 0, bs.atr[np.clip(js, 0, bs.n - 1)], np.nan)
        self.dfX_atrS = dfX.assign(atr=self.atrS_x)
        # vrais prix S
        self.hS, self.lS, self.cS, self.atrS = bs.h, bs.l, bs.c, bs.atr
        # valeurs « dernière bougie S clôturée » sur chaque barre X (servent aussi à la référence au hasard)
        jc = np.clip(js, 0, bs.n - 1); v = js >= 0
        nanw = lambda x: np.where(v, x[jc], np.nan)
        self.base = dict(stopS_l=nanw(bs.l), stopS_s=nanw(bs.h),
                         lim_milieu_l=nanw(0.5 * (bs.h + bs.l)), lim_milieu_s=nanw(0.5 * (bs.h + bs.l)),
                         lim_ema50_l=e50.copy(), lim_ema50_s=e50.copy(),
                         lim_atr_l=nanw(bs.c - 0.25 * bs.atr), lim_atr_s=nanw(bs.c + 0.25 * bs.atr))
        # segments contigus de X (trou > 3 h = coupure) : un backtest par segment, aucune position ne
        # traverse un trou de données (le cache est fragmenté ; le DATASET n'a que des week-ends)
        coup = np.flatnonzero(np.diff(bx.t_ouv) > 180 * NS_MIN) + 1
        bornes = np.r_[0, coup, bx.n]
        self.segments = [(int(bornes[q]), int(bornes[q + 1])) for q in range(len(bornes) - 1)
                         if bornes[q + 1] - bornes[q] > 20]
        self.seg_df = {False: [dfX.iloc[a_:b_] for a_, b_ in self.segments],
                       True: [self.dfX_atrS.iloc[a_:b_] for a_, b_ in self.segments]}
        self.heure_x = M._dti(bx.t_clo).tz_convert(M.PARIS).hour.to_numpy()

    def evenements(self, L, S):
        """[(i_S, sens)] des signaux S projetables sur X."""
        ev = [(int(i), 1) for i in np.flatnonzero(L & self.ok)] + \
             [(int(i), -1) for i in np.flatnonzero(S & self.ok)]
        ev.sort()
        return ev

    def construire(self, ev, entree, W):
        """Signaux X, prix limites, niveaux de stop et table événement <- barre X de signal.
        entree : 'direct' | nom de déclencheur | 'lim_milieu' | 'lim_ema50' | 'lim_atr'."""
        bx = self.bx; n = bx.n
        Lx = np.zeros(n, bool); Sx = np.zeros(n, bool)
        prix_l = self.base.get(entree + '_l', np.full(n, np.nan)).copy()
        prix_s = self.base.get(entree + '_s', np.full(n, np.nan)).copy()
        stopS_l = self.base['stopS_l'].copy(); stopS_s = self.base['stopS_s'].copy()
        evt = np.full(n, -1, np.int64)
        n_decl = 0
        fen_ns = W * bx.ut * NS_MIN
        for q, (i, d) in enumerate(ev):
            a = int(self.a[i])
            if entree == 'direct' or entree.startswith('lim_'):
                k = a - 1
                px_ = prix_l if d == 1 else prix_s
                if entree == 'lim_milieu':
                    px_[k] = 0.5 * (self.hS[i] + self.lS[i])
                elif entree == 'lim_ema50':
                    px_[k] = self.e50[k]
                elif entree == 'lim_atr':
                    px_[k] = self.cS[i] - d * 0.25 * self.atrS[i]
            else:
                tl, ts = self.declencheurs[entree]
                tr = tl if d == 1 else ts
                k = -1
                fin = min(a + W, n - 1)
                t0 = self.bs.t_clo[i]
                for j in range(a, fin):
                    if bx.t_ouv[j] - t0 >= fen_ns:
                        break
                    if tr[j]:
                        k = j; break
                if k < 0:
                    continue
            n_decl += 1
            (Lx if d == 1 else Sx)[k] = True
            (Sx if d == 1 else Lx)[k] = False
            stopS_l[k] = self.lS[i]; stopS_s[k] = self.hS[i]
            evt[k] = q
        return dict(Lx=Lx, Sx=Sx, prix_l=prix_l, prix_s=prix_s, stopS_l=stopS_l, stopS_s=stopS_s, evt=evt, n_decl=n_decl)

    def gestion(self, cons, entree, W, stop, obj, sortie_S=None):
        """-> (True si exécution avec l'ATR S, gestion sur barres X complètes)."""
        g = dict(instrument=self.instrument, heure_sortie='15:59')
        df = False
        if entree.startswith('lim_'):
            g['entree'] = {'mode': 'limite', 'long': cons['prix_l'], 'short': cons['prix_s'], 'validite': int(W)}
        if stop == 'swing':
            g['stop'] = {'mode': 'niveau', 'long': {'swing5': self.swing_bas}, 'short': {'swing5': self.swing_haut},
                         'marge_ticks': 1, 'min_atr': 0.5, 'max_atr': 8.0, 'repli_k': 1.5}
        elif stop == 'bougieS':
            g['stop'] = {'mode': 'niveau', 'long': {'bougieS': cons['stopS_l']}, 'short': {'bougieS': cons['stopS_s']},
                         'marge_ticks': 1, 'min_atr': 0.5, 'repli_k': 1.5}
        elif stop == 'atrX2':
            g['stop'] = {'mode': 'atr', 'k': 2.0}
        elif stop == 'atrS2':
            g['stop'] = {'mode': 'atr', 'k': 2.0}
            df = True
        else:
            raise ValueError(stop)
        if obj.startswith('R'):
            g['objectif'] = {'mode': 'R', 'k': float(obj[1:])}
        elif obj == 'heiS':
            g['objectif'] = {'mode': 'aucun'}
            g['sortie_signal'] = sortie_S
        return df, g

    def sortie_heiS(self):
        """Sortie sur bascule Heishinator S, posée sur la barre X a-1 (exécutée à l'ouverture de a)."""
        n = self.bx.n
        xl = np.zeros(n, bool); xs = np.zeros(n, bool)
        fb = _b(self.dfS, 'hei_flip_bas'); fh = _b(self.dfS, 'hei_flip_haut')
        k = self.a - 1
        m = self.ok
        xl[k[m & fb]] = True
        xs[k[m & fh]] = True
        return {'long': xl, 'short': xs}


def _tranche(x, a, b, n):
    if isinstance(x, np.ndarray) and len(x) == n:
        return x[a:b]
    if isinstance(x, dict):
        return {k: _tranche(v, a, b, n) for k, v in x.items()}
    return x


def backtest_segments(ctx, Lx, Sx, avec_atrS, g):
    """moteur.backtest segment par segment ; i_signal / k_* remis en indices X globaux."""
    n = ctx.bx.n
    out = []
    for q, (a, b) in enumerate(ctx.segments):
        if not (Lx[a:b].any() or Sx[a:b].any()):
            continue
        T = M.backtest(ctx.seg_df[avec_atrS][q], Lx[a:b], Sx[a:b], _tranche(g, a, b, n), details=True)
        if len(T):
            for c in ('i_signal', 'k_entree', 'k_sortie'):
                T[c] += a
            out.append(T)
    if not out:
        return pd.DataFrame(columns=M.COLONNES_TRADES + ['i_signal', 'k_entree', 'k_sortie'])
    return pd.concat(out, ignore_index=True)


def lancer(ctx, ev, entree, W, stop, obj, cons=None, sortie_S=None):
    """Backtest d'une variante. Renvoie (trades avec colonne evt, cons, avec_atrS, gestion)."""
    cons = cons or ctx.construire(ev, entree, W)
    avec, g = ctx.gestion(cons, entree, W, stop, obj, sortie_S)
    T = backtest_segments(ctx, cons['Lx'], cons['Sx'], avec, g)
    T['evt'] = cons['evt'][T['i_signal'].to_numpy(int)] if len(T) else pd.Series(dtype=int)
    return T, cons, avec, g


def hasard(ctx, cons, entree, avec, g, n_tirages=200, graine=0, garder=False):
    """Référence « entrées au hasard, même gestion » : chaque barre X de signal est remplacée par une barre X
    tirée au hasard à la même heure de Paris (clôture), même sens, dans les segments ; stops / prix limites
    = valeurs de la dernière bougie S clôturée à cet instant (tableaux de base). Renvoie (DataFrame des
    tirages, liste des trades si garder)."""
    rng = np.random.default_rng(graine)
    n = ctx.bx.n
    elig = np.zeros(n, bool)
    for a, b in ctx.segments:
        elig[a:b - 1] = True
    elig &= np.isfinite(ctx.bx.atr) & np.isfinite(ctx.atrS_x)
    pools = {h: np.flatnonzero(elig & (ctx.heure_x == h)) for h in range(24)}
    tous = np.flatnonzero(elig)
    reels = [(ctx.heure_x[k], 1) for k in np.flatnonzero(cons['Lx'])] + \
            [(ctx.heure_x[k], -1) for k in np.flatnonzero(cons['Sx'])]
    g0 = dict(g)
    if entree.startswith('lim_'):
        g0['entree'] = dict(g0['entree'], long=ctx.base[entree + '_l'], short=ctx.base[entree + '_s'])
    st = g0['stop']
    if st.get('mode') == 'niveau' and 'bougieS' in st.get('long', {}):
        g0['stop'] = dict(st, long={'bougieS': ctx.base['stopS_l']}, short={'bougieS': ctx.base['stopS_s']})
    lignes, trs = [], []
    for _ in range(n_tirages):
        Lr = np.zeros(n, bool); Sr = np.zeros(n, bool)
        for h, d in reels:
            pool = pools.get(h)
            pool = pool if pool is not None and len(pool) else tous
            k = pool[rng.integers(len(pool))]
            if d == 1 and not Sr[k]:
                Lr[k] = True
            elif d == -1 and not Lr[k]:
                Sr[k] = True
        T = backtest_segments(ctx, Lr, Sr, avec, g0)
        m = M.metriques(T, n_boot=1) if len(T) else dict(n=0)
        nf, pf_ = a_risque_fixe(T) if len(T) else (np.zeros(0), np.zeros(0))
        lignes.append(dict(n=m['n'], r_moyen=m.get('r_moyen', np.nan), pf=m.get('pf', np.nan),
                           gain_net_usd=m.get('gain_net_usd', 0.0),
                           r_fixe=float(pf_.sum() / (RISQUE_FIXE * max((nf > 0).sum(), 1)))))
        if garder:
            trs.append(T[M.COLONNES_TRADES])
    R = pd.DataFrame(lignes)
    return (R, trs) if garder else R


def enrichir(ctx, ev, T):
    """Ajoute gain d'entrée vs référence (ouverture de la barre X a = ouverture de la bougie S suivante)."""
    if not len(T):
        return T
    spec = M.INSTRUMENTS[ctx.instrument]
    slip = spec['tick']
    q = T['evt'].to_numpy()
    i_s = np.array([ev[x][0] for x in q]); d = np.where(T['sens'] == 'long', 1, -1)
    a = ctx.a[i_s]
    ref = ctx.bx.o[a] + d * slip
    T = T.copy()
    T['i_S'] = i_s
    T['gain_entree_pts'] = d * (ref - T['prix_entree'].to_numpy())
    T['gain_entree_atrS'] = T['gain_entree_pts'] / ctx.atrS[i_s]
    T['stop_pts'] = np.abs(T['prix_entree'] - T['stop_initial'])
    T['cout_R'] = (2 * spec['commission_cote'] + 2 * slip * spec['point']) / T['risque_usd']
    return T


RISQUE_FIXE = 200.0     # $ risqués par trade pour la comparaison « même risque, plus de micros »
MICROS_MAX = 40         # Tradeify 50k : 40 micros


def a_risque_fixe(T, risque=RISQUE_FIXE, cmax=MICROS_MAX):
    n = np.clip(np.floor(risque / T['risque_usd'].to_numpy()), 0, cmax)
    return n, n * T['pnl_usd'].to_numpy()
