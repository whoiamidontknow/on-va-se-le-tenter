"""Setups de RETOUR À LA MOYENNE (agent WRF). Tout est calculé à la CLÔTURE de la barre signal, sans futur.

Trois familles (long ; le short est le miroir) :

F1 « rejet de niveau » : la MÈCHE basse traverse un niveau de support connu à la barre précédente, mais tout le
   CORPS reste au-dessus (min(open, close) > niveau > low). Niveaux : jour précédent (PDH/PDL), Monday, sessions
   terminées (Asie/Londres/US), ORB 09:30-09:45 NY, pivots weekly classiques (P, R1, S1, R2, S2 sur vrais prix de
   la semaine précédente), ronds de 100, ronds fins (MES 25 / NQ 50), zones Detector (haut de la zone haussière
   sous le prix ; bas de la zone baissière au-dessus pour le short). Option « force » : bougie de la couleur du
   trade (close > open pour un long).
F2 « fausse cassure » : 1re clôture au-delà d'un niveau (niveau inchangé depuis la barre précédente), puis dans
   les N barres suivantes une clôture qui revient de l'autre côté -> trade dans le sens du RETOUR (cassure haute
   ratée = short). Niveaux : ORB, sessions, Monday, jour précédent, pivots weekly, trendline (Breakator : la
   cassure est la flèche de cassure, le « niveau » est la clôture de la barre d'avant la cassure).
F3 « épuisement » : écart à l'EMA50 (Moyenator, sur HA) >= X ATR sur une des 3 dernières barres (8 pour climax,
   flèche et Heishinator, qui arrivent quelques barres après le pic), puis un
   déclencheur OPPOSÉ : climax, flèche Signator (Fort ou Moyen), changement de couleur Heishinator, bougie de
   retournement (close < open et close < low précédent), divergence RSI (nouveau plus haut 20 barres, RSI plus bas
   que son maximum des barres 3 à 20). X = 0 : pas de condition d'écart.

Les signaux tombant sur un créneau d'annonce (blackout) sont retirés.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from donnees_wrf import col, bool_col, prix_signal, jour_cme


# ──────────────────────────────────────────────── niveaux
def pivots_weekly(df):
    """5 pivots classiques de la semaine précédente (vrais prix causaux) : liste de tableaux."""
    _, h, l, c, _ = prix_signal(df)
    j = jour_cme(df.index)
    wk = pd.DatetimeIndex(j).to_period('W-SUN')
    s = pd.DataFrame(dict(h=h, l=l, c=c, w=wk))
    dw = s.groupby('w').agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).shift(1)
    hh, ll, cc = (dw[x].reindex(wk).to_numpy() for x in ('h', 'l', 'c'))
    p = (hh + ll + cc) / 3
    return [p, 2 * p - ll, 2 * p - hh, p + (hh - ll), p - (hh - ll)]


def jour_prec(df):
    _, h, l, c, _ = prix_signal(df)
    j = jour_cme(df.index)
    s = pd.DataFrame(dict(h=h, l=l, j=j))
    dj = s.groupby('j').agg(h=('h', 'max'), l=('l', 'min')).shift(1)
    return dj['h'].reindex(j).to_numpy(), dj['l'].reindex(j).to_numpy()


def niveaux_sr(df, instrument):
    """dict famille -> (liste de supports pour un long, liste de résistances pour un short).
    Chaque tableau donne le niveau connu à la clôture ; on exige plus loin qu'il soit inchangé depuis la
    barre précédente (niveau déjà affiché avant la barre signal)."""
    pdh, pdl = jour_prec(df)
    ses_h = [col(df, k + '_h') for k in ('as', 'ld', 'us')]
    ses_l = [col(df, k + '_l') for k in ('as', 'ld', 'us')]
    piv = pivots_weekly(df)
    N = {
        'pd': ([pdl, pdh], [pdh, pdl]),
        'mon': ([col(df, 'mon_l'), col(df, 'mon_h')], [col(df, 'mon_h'), col(df, 'mon_l')]),
        'sess': (ses_l + ses_h, ses_h + ses_l),
        'orb': ([col(df, 'orb_l'), col(df, 'orb_h')], [col(df, 'orb_h'), col(df, 'orb_l')]),
        'piv': (piv, piv),
        'det': ([col(df, 'zh_inf_h')], [col(df, 'zb_sup_b')]),
    }
    return N


def _stable(v):
    """niveau à la barre i s'il est identique à la barre i-1, sinon NaN."""
    vp = np.r_[np.nan, v[:-1]]
    with np.errstate(invalid='ignore'):
        return np.where(np.isfinite(v) & (v == vp), v, np.nan)


# ──────────────────────────────────────────────── F1 rejet de niveau
def f1_rejet(df, instrument, famille, force=False):
    o, h, l, c, a = prix_signal(df)
    bas_corps, haut_corps = np.minimum(o, c), np.maximum(o, c)
    L = np.zeros(len(df), bool); S = np.zeros(len(df), bool)
    if famille in ('rond', 'rondfin'):
        pas = 100.0 if famille == 'rond' else (25.0 if instrument == 'MES' else 50.0)
        k_bas = np.floor(bas_corps / pas) * pas            # rond juste sous le corps
        L = (l < k_bas) & (k_bas < bas_corps)
        k_haut = np.ceil(haut_corps / pas) * pas           # rond juste au-dessus du corps
        S = (h > k_haut) & (k_haut > haut_corps)
    else:
        N = niveaux_sr(df, instrument)
        fams = list(N) if famille == 'tous' else [famille]
        with np.errstate(invalid='ignore'):
            for f in fams:
                for v in N[f][0]:
                    v = _stable(v)
                    L |= (l < v) & (bas_corps > v)
                for v in N[f][1]:
                    v = _stable(v)
                    S |= (h > v) & (haut_corps < v)
        if famille == 'tous':
            L2, S2 = f1_rejet(df, instrument, 'rond', False)
            L |= L2; S |= S2
    if force:
        L &= c > o; S &= c < o
    return L, S


# ──────────────────────────────────────────────── F2 fausse cassure
def _fausse(c, v, jour, nmax):
    """v : niveau (tableau). Cassure haute (1re clôture au-dessus, niveau stable) puis retour sous v dans les
    nmax barres -> short ; miroir -> long. Une fois par (jour, niveau, sens)."""
    n = len(c); L = np.zeros(n, bool); S = np.zeros(n, bool)
    vs = _stable(v)
    vu = set()
    for j in range(1, n):
        x = vs[j]
        if not np.isfinite(x):
            continue
        if c[j] > x >= c[j - 1]:
            d = 1
        elif c[j] < x <= c[j - 1]:
            d = -1
        else:
            continue
        cle = (jour[j], round(float(x), 4), d)
        if cle in vu:
            continue
        vu.add(cle)
        for i in range(j + 1, min(j + 1 + nmax, n)):
            if jour[i] != jour[j]:
                break
            if d == 1 and c[i] < x:
                S[i] = True; break
            if d == -1 and c[i] > x:
                L[i] = True; break
    return L, S


def f2_fausse_cassure(df, instrument, famille, nmax):
    o, h, l, c, a = prix_signal(df)
    jour = jour_cme(df.index)
    L = np.zeros(len(df), bool); S = np.zeros(len(df), bool)
    if famille in ('tl', 'tous'):
        bh, bb = bool_col(df, 'tl_cassure_haut'), bool_col(df, 'tl_cassure_bas')
        for j in np.flatnonzero(bh | bb):
            if j < 1:
                continue
            x = c[j - 1]; up = bh[j]
            for i in range(j + 1, min(j + 1 + nmax, len(c))):
                if jour[i] != jour[j]:
                    break
                if up and c[i] < x:
                    S[i] = True; break
                if not up and c[i] > x:
                    L[i] = True; break
    if famille != 'tl':
        N = niveaux_sr(df, instrument)
        fams = [f for f in N if f != 'det'] if famille == 'tous' else [famille]
        for f in fams:
            vus = []
            for v in N[f][0] + N[f][1]:
                k = id(v)
                if k in vus:
                    continue
                vus.append(k)
                l2, s2 = _fausse(c, v, jour, nmax)
                L |= l2; S |= s2
    return L, S


# ──────────────────────────────────────────────── F3 épuisement
def ecart_ema(df):
    _, _, _, c, a = prix_signal(df)
    e = col(df, 'ema50')
    with np.errstate(invalid='ignore', divide='ignore'):
        return (c - e) / np.where(a > 0, a, np.nan)


def f3_epuisement(df, instrument, declencheur, x):
    o, h, l, c, a = prix_signal(df)
    n = len(df)
    d = ecart_ema(df)
    s = pd.Series(d)
    fen = 8 if declencheur in ('clx', 'sig', 'hei') else 3   # flèches/couleurs : arrivent après le pic
    haut3 = s.rolling(fen, min_periods=1).max().to_numpy()   # étiré vers le haut récemment
    bas3 = s.rolling(fen, min_periods=1).min().to_numpy()
    if declencheur == 'clx':
        tl, ts = bool_col(df, 'clx_buy'), bool_col(df, 'clx_sell')
    elif declencheur == 'sig':
        tl = bool_col(df, 'sig_long_fort') | bool_col(df, 'sig_long_moyen')
        ts = bool_col(df, 'sig_short_fort') | bool_col(df, 'sig_short_moyen')
    elif declencheur == 'hei':
        tl, ts = bool_col(df, 'hei_flip_haut'), bool_col(df, 'hei_flip_bas')
    elif declencheur == 'retour':
        lp, hp = np.r_[np.nan, l[:-1]], np.r_[np.nan, h[:-1]]
        with np.errstate(invalid='ignore'):
            tl = (c > o) & (c > hp); ts = (c < o) & (c < lp)
    elif declencheur == 'div':
        rsi = col(df, 'rsi')
        H20 = pd.Series(h).rolling(20, min_periods=20).max().to_numpy()
        L20 = pd.Series(l).rolling(20, min_periods=20).min().to_numpy()
        r3max = pd.Series(rsi).rolling(3).max().to_numpy(); r3min = pd.Series(rsi).rolling(3).min().to_numpy()
        rprev_max = pd.Series(rsi).shift(3).rolling(17).max().to_numpy()
        rprev_min = pd.Series(rsi).shift(3).rolling(17).min().to_numpy()
        hh2 = pd.Series(h).rolling(2).max().to_numpy(); ll2 = pd.Series(l).rolling(2).min().to_numpy()
        with np.errstate(invalid='ignore'):
            ts = (hh2 >= H20) & (r3max < rprev_max) & (c < o)
            tl = (ll2 <= L20) & (r3min > rprev_min) & (c > o)
    else:
        raise ValueError(declencheur)
    with np.errstate(invalid='ignore'):
        L = tl & (bas3 <= -x) if x > 0 else tl.copy()
        S = ts & (haut3 >= x) if x > 0 else ts.copy()
    return L, S


# ──────────────────────────────────────────────── catalogue
def catalogue():
    """[(code, famille, fonction(df, instrument) -> (L, S))]."""
    cat = []
    for f in ('pd', 'mon', 'sess', 'orb', 'piv', 'rond', 'rondfin', 'det', 'tous'):
        for fo in (False, True):
            cat.append(('F1_%s%s' % (f, '_force' if fo else ''), 'F1 rejet',
                        (lambda f, fo: lambda df, ins: f1_rejet(df, ins, f, fo))(f, fo)))
    for f in ('orb', 'sess', 'mon', 'pd', 'piv', 'tl', 'tous'):
        for nm in (2, 4):
            cat.append(('F2_%s_n%d' % (f, nm), 'F2 fausse cassure',
                        (lambda f, nm: lambda df, ins: f2_fausse_cassure(df, ins, f, nm))(f, nm)))
    for t in ('clx', 'sig', 'hei', 'retour', 'div'):
        for x in (0.0, 1.5, 2.5):
            cat.append(('F3_%s_x%g' % (t, x), 'F3 épuisement',
                        (lambda t, x: lambda df, ins: f3_epuisement(df, ins, t, x))(t, x)))
    return cat


def signaux(df, instrument, fn):
    L, S = fn(df, instrument)
    bo = bool_col(df, 'blackout')
    L = L & ~bo; S = S & ~bo
    L[:150] = False; S[:150] = False          # chauffe des indicateurs
    amb = L & S
    return L & ~amb, S & ~amb


# ──────────────────────────────────────────────── gestions
def niveaux_cibles(df):
    """objectifs de retour : EMA50 et milieu du range 20 barres (connus à la clôture)."""
    _, h, l, c, a = prix_signal(df)
    e = col(df, 'ema50')
    mid = (pd.Series(h).rolling(20, min_periods=10).max() + pd.Series(l).rolling(20, min_periods=10).min()).to_numpy() / 2
    return {'ema50': e, 'mid20': mid}


def stop_extreme(df):
    """stop derrière l'extrême des 2 dernières barres (signal comprise)."""
    _, h, l, c, a = prix_signal(df)
    lo2 = pd.Series(l).rolling(2, min_periods=1).min().to_numpy()
    hi2 = pd.Series(h).rolling(2, min_periods=1).max().to_numpy()
    return lo2, hi2


STOPS = ('ext', 'a1', 'a2')
CIBLES = ('R0.5', 'R0.75', 'R1', 'R1.5', 'ema50', 'mid20')
TEMPS = (0, 8)


def gestion(df, instrument, stop, cible, temps):
    g = dict(instrument=instrument, heure_sortie='15:59', max_trades_jour=0, sortie_barres=int(temps))
    if stop == 'ext':
        lo2, hi2 = stop_extreme(df)
        g['stop'] = dict(mode='niveau', long=lo2, short=hi2, marge_ticks=0, marge_atr=0.1, min_atr=0.4,
                         max_atr=2.5, sauter=True)
    else:
        g['stop'] = dict(mode='atr', k={'a1': 1.0, 'a2': 2.0}[stop])
    if cible.startswith('R'):
        g['objectif'] = dict(mode='R', k=float(cible[1:]))
    else:
        v = niveaux_cibles(df)[cible]
        g['objectif'] = dict(mode='niveau', long=v, short=v, ratio_min=0.3, marge_ticks=0, si_absent='sauter')
    return g
