"""Bibliothèque EXH : déclencheurs (événements), filtres (états) et sorties, sur les colonnes de donnees_exh.

Déclencheur : f(df) -> (L, S) booléens dans son sens NATUREL (L = achat, S = vente). Le mode « inverse »
du balayage échange L et S (on joue contre l'événement).
Filtre : f(df) -> (okL, okS) : condition vraie pour un trade long / short. NaN -> False (prudent).
Un déclencheur ou filtre dont une colonne manque est simplement absent (renvoie None).
"""
from __future__ import annotations

import numpy as np


def _b(df, k):
    if k not in df:
        return None
    x = df[k].to_numpy()
    if x.dtype == bool:
        return x
    x = x.astype(float)
    return np.where(np.isnan(x), False, x > 0.5)


def _f(df, k):
    return df[k].to_numpy(float) if k in df else None


def _tri(df, k):
    """État directionnel -> (vrai si haussier, vrai si baissier), NaN -> (False, False)."""
    if k not in df:
        return None
    x = df[k].to_numpy(float)
    if k.startswith('s_') or k.startswith('v_'):
        return x > 0, x < 0
    return np.where(np.isnan(x), False, x > 0.5), np.where(np.isnan(x), False, x < 0.5)


def _prev(x, fill=np.nan):
    return np.r_[fill, x[:-1]]


# ════════════════════════════════════════════════════════════════════════════════════════
# DÉCLENCHEURS
# ════════════════════════════════════════════════════════════════════════════════════════
def _paire(a, b):
    def f(df):
        x, y = _b(df, a), _b(df, b)
        if x is None or y is None or (x.sum() + y.sum()) == 0:
            return None
        return x, y
    return f


def _croise_niveau(hk, lk, rejet=False):
    """Cassure : clôture vraie qui franchit le niveau (clôture précédente de l'autre côté).
    Rejet : la mèche dépasse le niveau mais la clôture revient (et la précédente était en deçà) -> sens opposé."""
    def f(df):
        if hk not in df:
            return None
        c, h, l = _f(df, 'c'), _f(df, 'h'), _f(df, 'l')
        H, L = _f(df, hk), _f(df, lk)
        pc = _prev(c)
        with np.errstate(invalid='ignore'):
            if not rejet:
                up = (c > H) & (pc <= H)
                dn = (c < L) & (pc >= L)
            else:
                dn = (h > H) & (c < H) & (pc < H)           # rejet du haut -> vente
                up = (l < L) & (c > L) & (pc > L)           # rejet du bas -> achat
        up = np.nan_to_num(up).astype(bool); dn = np.nan_to_num(dn).astype(bool)
        if up.sum() + dn.sum() == 0:
            return None
        return up, dn
    return f


def _changement(k):
    def f(df):
        x = _tri(df, k)
        if x is None:
            return None
        raw = df[k].to_numpy(float)
        p = _prev(raw)
        up = (raw > 0.5) & (p < 0.5); dn = (raw < 0.5) & (p > 0.5)
        up = np.nan_to_num(up).astype(bool); dn = np.nan_to_num(dn).astype(bool)
        if up.sum() + dn.sum() == 0:
            return None
        return up, dn
    return f


def _croise_ema(k):
    def f(df):
        if k not in df:
            return None
        c = _f(df, 'ha_c') if 'ha_c' in df else _f(df, 'c')
        e = _f(df, k)
        pc, pe = _prev(c), _prev(e)
        with np.errstate(invalid='ignore'):
            up = (c > e) & (pc <= pe); dn = (c < e) & (pc >= pe)
        return np.nan_to_num(up).astype(bool), np.nan_to_num(dn).astype(bool)
    return f


def _feu_seuil(s):
    def f(df):
        x = _f(df, 'feu_net')
        if x is None:
            return None
        p = _prev(x)
        with np.errstate(invalid='ignore'):
            up = (x >= s) & (p < s); dn = (x <= -s) & (p > -s)
        return np.nan_to_num(up).astype(bool), np.nan_to_num(dn).astype(bool)
    return f


def _zone_entree(df):
    a, b = _b(df, 'dans_zh'), _b(df, 'dans_zb')
    if a is None or (a.sum() + b.sum()) == 0:
        return None
    return a & ~_prev(a, False).astype(bool), b & ~_prev(b, False).astype(bool)      # entrée en zone haussière -> achat


def _zone_sortie(df):
    """Sortie d'une zone par le côté du rebond : quitte une zone haussière en clôturant AU-DESSUS -> achat."""
    a, b = _b(df, 'dans_zh'), _b(df, 'dans_zb')
    if a is None or (a.sum() + b.sum()) == 0:
        return None
    c = _f(df, 'ha_c'); pc = _prev(c)
    up = ~a & _prev(a, False).astype(bool) & (c > pc)
    dn = ~b & _prev(b, False).astype(bool) & (c < pc)
    return up, dn


def _adx_croise(s=20):
    def f(df):
        if 'adx' not in df:
            return None
        x = _f(df, 'adx'); p = _prev(x)
        dp, dm = _f(df, 'dip'), _f(df, 'dim')
        with np.errstate(invalid='ignore'):
            ev = (x >= s) & (p < s)
            return np.nan_to_num(ev & (dp > dm)).astype(bool), np.nan_to_num(ev & (dm > dp)).astype(bool)
    return f


def _sig_tous(df):
    a, b, c, d = (_b(df, k) for k in ('sig_long_fort', 'sig_short_fort', 'sig_long_moyen', 'sig_short_moyen'))
    if a is None:
        return None
    return a | c, b | d


DECLENCHEURS = {
    'sig_fort': _paire('sig_long_fort', 'sig_short_fort'),
    'sig_moyen': _paire('sig_long_moyen', 'sig_short_moyen'),
    'sig_tous': _sig_tous,
    'hei_flip': _paire('hei_flip_haut', 'hei_flip_bas'),
    'tl_cassure': _paire('tl_cassure_haut', 'tl_cassure_bas'),
    'climax': _paire('clx_buy', 'clx_sell'),
    'div_rsi': _paire('div_haus', 'div_bais'),
    'zone_entree': _zone_entree,
    'zone_sortie': _zone_sortie,
    'zone_cassee': lambda df: (lambda x: None if x is None else (x[1], x[0]))(_paire('zh_mitigee', 'zb_mitigee')(df)),
    'orb_cassure': _croise_niveau('n_orb_h', 'n_orb_l'),
    'orb_rejet': _croise_niveau('n_orb_h', 'n_orb_l', rejet=True),
    'asie_cassure': _croise_niveau('n_as_h', 'n_as_l'),
    'asie_rejet': _croise_niveau('n_as_h', 'n_as_l', rejet=True),
    'londres_cassure': _croise_niveau('n_ld_h', 'n_ld_l'),
    'londres_rejet': _croise_niveau('n_ld_h', 'n_ld_l', rejet=True),
    'us_cassure': _croise_niveau('n_us_h', 'n_us_l'),
    'us_rejet': _croise_niveau('n_us_h', 'n_us_l', rejet=True),
    'monday_cassure': _croise_niveau('n_mon_h', 'n_mon_l'),
    'monday_rejet': _croise_niveau('n_mon_h', 'n_mon_l', rejet=True),
    'veille_cassure': _croise_niveau('n_pd_h', 'n_pd_l'),
    'veille_rejet': _croise_niveau('n_pd_h', 'n_pd_l', rejet=True),
    'ema50_croise': _croise_ema('ema50'),
    'ema60_croise': _croise_ema('ema60'),
    'trend15_change': _changement('trend_15'),
    'trend60_change': _changement('trend_60'),
    'trend240_change': _changement('trend_240'),
    'hei60_change': _changement('hei_60'),
    'feu_0.3': _feu_seuil(0.3),
    'feu_0.5': _feu_seuil(0.5),
    'adx20_croise': _adx_croise(20),
    'supertrend_flip': _changement('s_supertrend'),
}


# ════════════════════════════════════════════════════════════════════════════════════════
# FILTRES
# ════════════════════════════════════════════════════════════════════════════════════════
def _avec(k, contre=False):
    def f(df):
        x = _tri(df, k)
        if x is None:
            return None
        u, d = x
        return (d, u) if contre else (u, d)
    return f


def _sym(cond):
    def f(df):
        x = cond(df)
        if x is None:
            return None
        return x, x
    return f


def _feu_avec(s):
    def f(df):
        x = _f(df, 'feu_net')
        if x is None:
            return None
        with np.errstate(invalid='ignore'):
            return np.nan_to_num(x >= s).astype(bool), np.nan_to_num(x <= -s).astype(bool)
    return f


def _plage(a, b):
    return _sym(lambda df: (df['min_paris'].to_numpy() >= a) & (df['min_paris'].to_numpy() < b))


def _jour(j, sauf=False):
    return _sym(lambda df: (df['jour_sem'].to_numpy() != j) if sauf else (df['jour_sem'].to_numpy() == j))


def _seuil(k, lo=-np.inf, hi=np.inf):
    def f(df):
        if k not in df:
            return None
        x = df[k].to_numpy(float)
        with np.errstate(invalid='ignore'):
            m = np.nan_to_num((x >= lo) & (x < hi)).astype(bool)
        return m, m
    return f


NIVEAUX = ['n_as_h', 'n_as_l', 'n_ld_h', 'n_ld_l', 'n_us_h', 'n_us_l', 'n_orb_h', 'n_orb_l', 'n_mon_h', 'n_mon_l',
           'n_pd_h', 'n_pd_l', 'zh_inf_b', 'zh_inf_h', 'zh_sup_b', 'zh_sup_h', 'zb_inf_b', 'zb_inf_h', 'zb_sup_b',
           'zb_sup_h']


def espace(df):
    """Distance (en ATR) au niveau le plus proche dans le sens du trade : (long, short)."""
    c, a = _f(df, 'c'), _f(df, 'atr')
    M = np.vstack([df[k].to_numpy(float) for k in NIVEAUX if k in df])
    with np.errstate(invalid='ignore'):
        dessus = np.where(M > c, M, np.inf).min(0); dessous = np.where(M < c, M, -np.inf).max(0)
        return (dessus - c) / a, (c - dessous) / a


def _espace(lo, hi=np.inf):
    def f(df):
        el, es = espace(df)
        return (el >= lo) & (el < hi), (es >= lo) & (es < hi)
    return f


def _hors_annonces(df):
    m = df['min_ny'].to_numpy()
    ok = ~(((m >= 480) & (m < 525)) | ((m >= 585) & (m < 615)))
    if 'blackout' in df:
        ok &= ~_b(df, 'blackout')
    return ok, ok


FILTRES = {}
for _k, _lib in (('trend_15', 'trend15'), ('trend_60', 'trend60'), ('trend_240', 'trend240'), ('trend_1D', 'trend1D'),
                 ('hei_bleu', 'hei'), ('hei_60', 'hei60'), ('hei_240', 'hei240'), ('dash_60', 'dash60'),
                 ('dash_240', 'dash240'), ('au_dessus_ema50', 'ema50'), ('s_supertrend', 'supertrend'),
                 ('s_vwap', 'vwap'), ('s_linreg', 'linreg'), ('s_orb', 'sig_orb'), ('v_trend', 'vidya'),
                 ('v_macd', 'macd10'), ('v_pa3', 'pa15')):
    FILTRES[_lib + '_avec'] = _avec(_k)
    FILTRES[_lib + '_contre'] = _avec(_k, contre=True)
FILTRES.update({
    'feu_avec_0': _feu_avec(0.0001), 'feu_avec_0.3': _feu_avec(0.3), 'feu_avec_0.5': _feu_avec(0.5),
    'feu_contre_0.3': lambda df: (lambda x: None if x is None else (x[1], x[0]))(_feu_avec(0.3)(df)),
    'di_avec': lambda df: None if 'dip' not in df else (lambda d: (d > 0, d < 0))(df['dip'].to_numpy(float) - df['dim'].to_numpy(float)),
    'rsi_avec': lambda df: (lambda x: (x >= 50, x < 50))(df['rsi'].to_numpy(float)),
    'adx_ge20': _seuil('adx', 20), 'adx_ge25': _seuil('adx', 25), 'adx_lt20': _seuil('adx', -np.inf, 20),
    'vol_lt0.9': _seuil('vol_rel', -np.inf, 0.9), 'vol_ge0.9': _seuil('vol_rel', 0.9),
    'vol_0.9_1.2': _seuil('vol_rel', 0.9, 1.2), 'vol_ge1.2': _seuil('vol_rel', 1.2),
    'asie_0_8': _plage(0, 480), 'londres_8_1430': _plage(480, 870), 'hors_londres': _sym(lambda df: ~((df['min_paris'].to_numpy() >= 480) & (df['min_paris'].to_numpy() < 870))),
    'us_1430_22': _plage(870, 1320), 'us_ouv_1530_1730': _plage(930, 1050), 'us_apm_1730_22': _plage(1050, 1320),
    'pas_nuit_8_22': _plage(480, 1320),
    'lundi': _jour(0), 'mardi': _jour(1), 'mercredi': _jour(2), 'jeudi': _jour(3), 'vendredi': _jour(4),
    'sauf_lundi': _jour(0, True), 'sauf_vendredi': _jour(4, True),
    'espace_ge1': _espace(1.0), 'espace_ge2': _espace(2.0), 'espace_lt1': _espace(0.0, 1.0),
    'hors_annonces': _hors_annonces,
})


# ════════════════════════════════════════════════════════════════════════════════════════
# SORTIES
# ════════════════════════════════════════════════════════════════════════════════════════
NIVEAUX_STOP = ['zh_inf_b', 'zb_sup_h', 'n_as_l', 'n_as_h', 'n_ld_l', 'n_ld_h', 'n_us_l', 'n_us_h', 'n_orb_l', 'n_orb_h',
                'n_mon_l', 'n_mon_h', 'n_pd_l', 'n_pd_h']
NIVEAUX_OBJ = ['zb_sup_b', 'zh_inf_h', 'n_as_h', 'n_as_l', 'n_ld_h', 'n_ld_l', 'n_us_h', 'n_us_l', 'n_orb_h', 'n_orb_l',
               'n_mon_h', 'n_mon_l', 'n_pd_h', 'n_pd_l', 'n_rond_haut', 'n_rond_bas']

GESTION_REF = dict(stop=('atr', 2.0), objectif=('R', 2.0), extra='rien')
STOPS = [('atr', 1.0), ('atr', 1.5), ('atr', 2.0), ('atr', 3.0), ('atr', 4.0), ('niveau', None)]
OBJECTIFS = [('R', 1.0), ('R', 1.5), ('R', 2.0), ('R', 3.0), ('R', 4.0), ('aucun', None), ('niveau', None)]
EXTRAS = ['rien', 'be1R', 'suiveur3', 'sortie_hei', 'temps16']


def gestion(df, instrument, stop, objectif, extra):
    """Construit le dict de gestion du moteur. Intrajournée forcée (15:59 Chicago, défaut du moteur)."""
    g = dict(instrument=instrument)
    if stop[0] == 'atr':
        g['stop'] = {'mode': 'atr', 'k': stop[1]}
    else:
        nv = {k: df[k].to_numpy(float) for k in NIVEAUX_STOP if k in df}
        g['stop'] = {'mode': 'niveau', 'long': nv, 'short': nv, 'marge_ticks': 2, 'min_atr': 0.5, 'max_atr': 4.0,
                     'choix': 'proche', 'repli_k': 2.0}
    if objectif[0] == 'R':
        g['objectif'] = {'mode': 'R', 'k': objectif[1]}
    elif objectif[0] == 'aucun':
        g['objectif'] = {'mode': 'aucun'}
    else:
        nv = {k: df[k].to_numpy(float) for k in NIVEAUX_OBJ if k in df}
        g['objectif'] = {'mode': 'niveau', 'long': nv, 'short': nv, 'ratio_min': 1.5, 'si_absent': ('R', 2.0)}
    if extra == 'be1R':
        g['break_even'] = {'R': 1.0, 'ticks': 1}
    elif extra == 'suiveur3':
        g['suiveur'] = {'k': 3.0, 'activation_R': 1.0}
    elif extra == 'sortie_hei':
        g['sortie_signal'] = {'long': df['hei_flip_bas'].to_numpy(bool), 'short': df['hei_flip_haut'].to_numpy(bool)}
    elif extra == 'temps16':
        g['sortie_barres'] = 16
    return g


def nom_sortie(stop, objectif, extra):
    s = 'stop %s' % ('%g ATR' % stop[1] if stop[0] == 'atr' else 'niveau')
    o = {'R': lambda: 'obj %gR' % objectif[1], 'aucun': lambda: 'sans obj', 'niveau': lambda: 'obj niveau'}[objectif[0]]()
    return '%s, %s%s' % (s, o, '' if extra == 'rien' else ', ' + extra)
