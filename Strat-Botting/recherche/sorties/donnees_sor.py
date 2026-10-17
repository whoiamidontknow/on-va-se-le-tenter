"""Accès aux données de l'agent « Sorties et protection » (SOR). TOUT l'accès aux données passe par
`charger_series()` : passer au DATASET = changer SOURCE (ou SOR_SOURCE=dataset), puis tout relancer.

Renvoie une liste de séries {'nom', 'instrument' ('MES'|'MNQ'), 'df'} ; chaque df est indexé par
l'OUVERTURE de la bougie (Europe/Paris) avec les noms de dataset/charger.py :
  o h l c atr                     vrais prix + ATR14 des vrais prix
  hei_bleu hei_flip_haut hei_flip_bas
  sig_long_fort sig_short_fort clx_buy clx_sell tl_cassure_haut tl_cassure_bas
  mon_cassure_haut mon_cassure_bas trend_60 blackout
et les NIVEAUX bruts par famille, colonnes `lv_<FAM>_<j>` (NaN si absent), connus à la clôture :
  DET  bornes des zones Detector (haussières et baissières)
  PW PM PY      pivots Traditionnels weekly / mensuel / annuel calculés sur la bougie HA (comme l'indicateur)
  PWR PMR PYR   les mêmes sur vrais prix
  SES  haut / bas des sessions Asie, Londres, US      MON  Monday High / Low
  ORB  plage d'ouverture US 09:30-09:45 NY (du jour)  TL   prix courant des trendlines (DATASET seulement)
  RD   ronds de 100      RF   ronds fins (NQ 50, MES 25)
  SW   3 derniers plus hauts / plus bas de swing (pivot 3/3 sur vrais prix, confirmé 3 barres après)

Source « cache » : tools/strategie/cache_series.pkl + tools/strategie/preregles/niveaux.py (vrais prix
reconstitués depuis le HA, fiables en 15m). Séries 15m : MES1! avr.-juil. (sans volume : ni Detector ni
climax ; flèches Signator de l'original), MESZ sept.-oct., NQZ sept.-oct. (tradé en MNQ).
Source « dataset » : exports DATASET.pine dans ~/Ephore/Strat-Botting-data (dataset/charger.py).
"""
from __future__ import annotations

import glob
import os
import sys
import math

import warnings
import numpy as np
import pandas as pd

warnings.simplefilter("ignore", category=pd.errors.PerformanceWarning)

ICI = os.path.dirname(os.path.abspath(__file__))
SB = os.path.abspath(os.path.join(ICI, '..', '..'))
RACINE = os.path.abspath(os.path.join(SB, '..'))
STRAT = os.path.join(RACINE, 'tools', 'strategie')
DOSSIER_DATASET = os.path.expanduser('~/Ephore/Strat-Botting-data')

SOURCE = os.environ.get('SOR_SOURCE', 'cache')        # 'cache' | 'dataset'
UT = int(os.environ.get('SOR_UT', '15'))

FAMILLES = ['DET', 'PW', 'PM', 'PY', 'PWR', 'PMR', 'PYR', 'SES', 'MON', 'ORB', 'TL', 'RD', 'RF', 'SW']
_MEMO = {}


def charger_series(ut: int = UT):
    """Point d'accès UNIQUE aux données."""
    cle = (SOURCE, ut)
    if cle not in _MEMO:
        _MEMO[cle] = _depuis_dataset(ut) if SOURCE == 'dataset' else _depuis_cache(ut)
    return _MEMO[cle]


# ───────────────────────────────────────── outils communs ─────────────────────────────────────────
def _swings(h, l, L=3, k=3):
    """k derniers pivots hauts / bas (L barres de chaque côté), connus L barres après le pivot."""
    n = len(h)
    hauts = np.full((n, k), np.nan); bas = np.full((n, k), np.nan)
    dh, db = [], []
    for i in range(n):
        p = i - L
        if p - L >= 0:
            if h[p] > h[p - L:p].max() and h[p] > h[p + 1:i + 1].max():
                dh.append(h[p])
            if l[p] < l[p - L:p].min() and l[p] < l[p + 1:i + 1].min():
                db.append(l[p])
        for j, v in enumerate(dh[-k:][::-1]):
            hauts[i, j] = v
        for j, v in enumerate(db[-k:][::-1]):
            bas[i, j] = v
    return np.hstack([hauts, bas])


def _orb(index, h, l):
    """Plage 09:30-09:45 New York sur vrais prix, disponible de 09:45 à 16:00 NY le même jour."""
    ny = index.tz_convert('America/New_York')
    m = ny.hour * 60 + ny.minute
    jour = ny.normalize()
    out = np.full((len(h), 2), np.nan)
    cur = None; cj = None; pret = False
    for i in range(len(h)):
        if jour[i] != cj:
            cj = jour[i]; cur = None; pret = False
        if 570 <= m[i] < 585:
            cur = [h[i], l[i]] if cur is None else [max(cur[0], h[i]), min(cur[1], l[i])]
            if m[i] + _ut_min(index) >= 585:
                pret = True                 # la plage est complète à la clôture de cette barre
                out[i] = cur
            continue
        if pret and 585 <= m[i] < 960:
            out[i] = cur
    return out


def _ut_min(index):
    return float(np.median(np.diff(index.as_unit('ns').asi8[:50]))) / 6e10


def _ronds(c, pas, nb):
    c0 = np.floor(c / pas) * pas
    return np.column_stack([c0 + pas * k for k in range(-nb + 1, nb + 1)])


def _ajoute(df, fam, mat):
    mat = np.asarray(mat, float)
    if mat.ndim == 1:
        mat = mat[:, None]
    cols = {'lv_%s_%d' % (fam, j): mat[:, j] for j in range(mat.shape[1])}
    neuf = pd.DataFrame(cols, index=df.index)
    for k in neuf.columns:
        df[k] = neuf[k]


def _cassures_niveau(c, haut, bas):
    """1re clôture au-delà d'un niveau (haut/bas) resté identique sur la barre précédente."""
    n = len(c)
    up = np.zeros(n, bool); dn = np.zeros(n, bool)
    for i in range(1, n):
        if np.isfinite(haut[i]) and haut[i] == haut[i - 1] and c[i] > haut[i] >= c[i - 1]:
            up[i] = True
        elif np.isfinite(bas[i]) and bas[i] == bas[i - 1] and c[i] < bas[i] <= c[i - 1]:
            dn[i] = True
    return up, dn


def completer(df, instrument):
    """Colonnes dérivées communes aux deux sources : swings, ORB (si absent), ronds, cassures d'ORB."""
    h, l, c = df['h'].to_numpy(float), df['l'].to_numpy(float), df['c'].to_numpy(float)
    _ajoute(df, 'SW', _swings(h, l))
    if not any(k.startswith('lv_ORB_') for k in df.columns):
        _ajoute(df, 'ORB', _orb(df.index, h, l))
    _ajoute(df, 'RD', _ronds(c, 100.0, 6))
    _ajoute(df, 'RF', _ronds(c, 50.0 if instrument == 'MNQ' else 25.0, 6))
    oh, ol = df['lv_ORB_0'].to_numpy(float), df['lv_ORB_1'].to_numpy(float)
    df['orb_cassure_haut'], df['orb_cassure_bas'] = _cassures_niveau(c, oh, ol)
    for f in FAMILLES:
        if not any(k.startswith('lv_%s_' % f) for k in df.columns):
            df['lv_%s_0' % f] = np.nan
    return df


# ───────────────────────────────────────── DATASET ─────────────────────────────────────────
_SYM_DATASET = {'MNQ': ['MNQ1!', 'NQ1!'], 'MES': ['MES1!', 'ES1!']}


def _depuis_dataset(ut):
    sys.path.insert(0, os.path.join(SB, 'dataset'))
    from charger import charger
    out = []
    for inst, syms in _SYM_DATASET.items():
        fichiers = []
        for s in syms:
            fichiers += glob.glob(os.path.join(DOSSIER_DATASET, '*%s, %d_*.csv' % (s, int(ut))))
        if not fichiers:
            continue
        df = pd.concat([charger(f) for f in sorted(fichiers)]).sort_index()
        df = df[~df.index.duplicated(keep='last')].copy()
        pref = lambda base: [base + suf for suf in ('_p', '_r1', '_s1', '_r2', '_s2', '_r3', '_s3', '_r4', '_s4', '_r5', '_s5')]
        _ajoute(df, 'DET', df[[k for k in ('zh_sup_h', 'zh_sup_b', 'zh_inf_h', 'zh_inf_b', 'zb_sup_h', 'zb_sup_b',
                                          'zb_inf_h', 'zb_inf_b')]].to_numpy(float))
        for fam, base in (('PW', 'pw'), ('PM', 'pm'), ('PY', 'py'), ('PWR', 'pwr'), ('PMR', 'pmr'), ('PYR', 'pyr')):
            _ajoute(df, fam, df[pref(base)].to_numpy(float))
        _ajoute(df, 'SES', df[['as_h_vrai', 'as_l_vrai', 'ld_h_vrai', 'ld_l_vrai', 'us_h_vrai', 'us_l_vrai']].to_numpy(float))
        _ajoute(df, 'MON', df[['mon_h_vrai', 'mon_l_vrai']].to_numpy(float))
        _ajoute(df, 'ORB', df[['orb_h_vrai', 'orb_l_vrai']].to_numpy(float))
        _ajoute(df, 'TL', df[['tl_res', 'tl_sup']].to_numpy(float))
        if 'trend_60' not in df:
            df['trend_60'] = False
        df = completer(df, inst)
        out.append(dict(nom='%s_%s' % (inst, ut), instrument=inst, df=df))
    return out


# ───────────────────────────────────────── CACHE ─────────────────────────────────────────
_GROUPE_CACHE = {'DB': 'DET', 'DS': 'DET', 'PW_HA': 'PW', 'PM_HA': 'PM', 'PY_HA': 'PY', 'PW_REEL': 'PWR',
                 'PM_REEL': 'PMR', 'PY_REEL': 'PYR', 'AS': 'SES', 'LD': 'SES', 'US': 'SES', 'MO': 'MON'}


def _depuis_cache(ut):
    sys.path[:0] = [STRAT, os.path.join(STRAT, 'preregles'), os.path.join(RACINE, 'tools', 'ephore_api')]
    import niveaux as nv
    import features
    out = []
    for S in nv.charger((ut,)):
        n = S['n']
        inst = 'MNQ' if S['inst'] == 'NQ' else 'MES'
        nanf = lambda x: np.array([np.nan if v is None else v for v in x], float)
        bull = np.array(S['bull'], bool); run = np.array(S['run'])
        sig = S['sig']
        idx = pd.DatetimeIndex(S['T']).tz_convert('Europe/Paris')
        d = dict(o=S['ro'], h=S['rh'], l=S['rl'], c=S['rc'], atr=nanf(S['ratr']), hei_bleu=bull,
                 hei_flip_haut=(run == 1) & bull & (np.arange(n) > 0),
                 hei_flip_bas=(run == 1) & ~bull & (np.arange(n) > 0),
                 sig_long_fort=[x == ('F', 1) for x in sig], sig_short_fort=[x == ('F', -1) for x in sig],
                 clx_buy=[x == 1 for x in S['clx']], clx_sell=[x == -1 for x in S['clx']],
                 tl_cassure_haut=S['rB'], tl_cassure_bas=S['sB'],
                 blackout=[features.news(t, S['tfm']) for t in S['T']])
        hh = features.resample_real(S, 60) if S['tfm'] < 60 else [None] * n
        d['trend_60'] = [bool(x and x['trend']) for x in hh]
        df = pd.DataFrame(d, index=idx)
        df.index.name = 'time'
        # niveaux bruts par famille
        par = {}
        for i, L in enumerate(S['LV']):
            for fam, _, v in L:
                g = _GROUPE_CACHE.get(fam)
                if g:
                    par.setdefault(g, {}).setdefault(i, []).append(v)
        for g, dico in par.items():
            m = max(len(v) for v in dico.values())
            mat = np.full((n, m), np.nan)
            for i, v in dico.items():
                mat[i, :len(v)] = v
            _ajoute(df, g, mat)
        # Monday : cassures sur vrais prix (le DATASET les donne sur HA)
        mh = df['lv_MON_0'].to_numpy(float) if 'lv_MON_0' in df else np.full(n, np.nan)
        ml = df['lv_MON_1'].to_numpy(float) if 'lv_MON_1' in df else np.full(n, np.nan)
        df['mon_cassure_haut'], df['mon_cassure_bas'] = _cassures_niveau(df['c'].to_numpy(float), mh, ml)
        df = completer(df, inst)
        nom = {'MES1': 'MES1_avr-juil', 'MES': 'MES_sept-oct', 'NQZ': 'MNQ_sept-oct'}.get(S['sym'], S['sym'])
        out.append(dict(nom=nom, instrument=inst, df=df))
    return out


if __name__ == '__main__':
    for s in charger_series():
        df = s['df']
        fams = {f: int(df[[k for k in df.columns if k.startswith('lv_%s_' % f)]].notna().any(axis=1).sum()) for f in FAMILLES}
        print(s['nom'], s['instrument'], len(df), df.index[0], df.index[-1])
        print('   niveaux dispo (barres) :', fams)
        print('   sigF', int(df.sig_long_fort.sum() + df.sig_short_fort.sum()), 'clx', int(df.clx_buy.sum() + df.clx_sell.sum()),
              'tl', int(df.tl_cassure_haut.sum() + df.tl_cassure_bas.sum()), 'orb', int(df.orb_cassure_haut.sum() + df.orb_cassure_bas.sum()),
              'mon', int(df.mon_cassure_haut.sum() + df.mon_cassure_bas.sum()), 'flips', int(df.hei_flip_haut.sum() + df.hei_flip_bas.sum()))
