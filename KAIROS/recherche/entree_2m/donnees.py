"""Accès aux données de l'agent « Entrée 15m -> 2m » (E2M). TOUT l'accès aux données passe par
`charger_donnees(marche, ut)` : passer au DATASET = changer SOURCE (ou E2M_SOURCE=dataset).

Renvoie un DataFrame indexé par l'OUVERTURE de la bougie (Europe/Paris) avec les noms de colonnes de
dataset/charger.py :
  o h l c atr            vrais prix + ATR14 des vrais prix
  ha_o ha_h ha_l ha_c    bougie Heiken Ashi du graphique
  ema50                  Moyenator (EMA50 du close HA)
  hei_bleu hei_flip_haut hei_flip_bas
  sig_long_fort sig_short_fort sig_long_moyen sig_short_moyen
  clx_buy clx_sell tl_cassure_haut tl_cassure_bas zh_mitigee zb_mitigee
  trend_60 trend_240     TREND de l'unité supérieure, bougie CLÔTURÉE (NaN/False si inconnu)
  feu_l feu_s            voix long / short du Feu (sur 29 ; PROXY 12 voix ramené à 29 dans le cache)

Source « cache » : tools/strategie/cache_series.pkl (exports HA ≈ 21/08 -> 15/10/2026, vrais prix
reconstitués depuis le HA : fiables en 15m, PAS en 1-3m — voir MEMOIRE_PROJET §15).
Source « dataset » : exports DATASET.pine dans ~/ERGON/KAIROS-data (dataset/charger.py).
"""
from __future__ import annotations

import glob
import os
import pickle
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
SB = os.path.abspath(os.path.join(ICI, '..', '..'))
RACINE = os.path.abspath(os.path.join(SB, '..'))
STRAT = os.path.join(RACINE, 'tools', 'strategie')
DOSSIER_DATASET = os.path.expanduser('~/ERGON/KAIROS-data')

SOURCE = os.environ.get('E2M_SOURCE', 'cache')        # 'cache' | 'dataset'

_SYM_CACHE = {'MNQ': ['NQZ'], 'MES': ['MES']}         # NQ et MNQ : mêmes prix
_SYM_DATASET = {'MNQ': ['MNQ1!', 'NQ1!'], 'MES': ['MES1!', 'ES1!']}
_MEMO = {}


def charger_donnees(marche: str, ut: int) -> pd.DataFrame | None:
    """Série complète (développement + scellé ; la découpe est faite par l'appelant) ou None."""
    cle = (SOURCE, marche, int(ut))
    if cle not in _MEMO:
        _MEMO[cle] = _depuis_dataset(marche, ut) if SOURCE == 'dataset' else _depuis_cache(marche, ut)
    return _MEMO[cle]


# ───────────────────────────────────────── DATASET ─────────────────────────────────────────
def _depuis_dataset(marche, ut):
    sys.path.insert(0, os.path.join(SB, 'dataset'))
    from charger import charger
    fichiers = []
    for s in _SYM_DATASET[marche]:
        fichiers += glob.glob(os.path.join(DOSSIER_DATASET, '*%s, %d_*.csv' % (s, int(ut))))
    if not fichiers:
        return None
    dfs = [charger(f) for f in sorted(fichiers)]
    df = pd.concat(dfs).sort_index()
    df = df[~df.index.duplicated(keep='last')]
    for k in ('trend_60', 'trend_240'):
        if k not in df:
            df[k] = False
    return df


# ───────────────────────────────────────── CACHE ─────────────────────────────────────────
def _series_cache():
    if 'series' not in _MEMO:
        _MEMO['series'] = pickle.load(open(os.path.join(STRAT, 'cache_series.pkl'), 'rb'))
    return _MEMO['series']


def _vers_df(S):
    sys.path[:0] = [STRAT, os.path.join(RACINE, 'tools', 'ephore_api')]
    import features
    import strat as ST
    n = S['n']
    nanf = lambda x: np.array([np.nan if v is None else v for v in x], float)
    bull = np.array(S['bull'], bool)
    run = np.array(S['run'])
    sig = S['sig']
    d = dict(o=S['ro'], h=S['rh'], l=S['rl'], c=S['rc'], atr=nanf(S['ratr']),
             ha_o=S['o'], ha_h=S['h'], ha_l=S['l'], ha_c=S['c'], ema50=nanf(S['e50']),
             hei_bleu=bull,
             hei_flip_haut=(run == 1) & bull & (np.arange(n) > 0),
             hei_flip_bas=(run == 1) & ~bull & (np.arange(n) > 0),
             sig_long_fort=[bool(x) and x == ('F', 1) for x in sig],
             sig_short_fort=[bool(x) and x == ('F', -1) for x in sig],
             sig_long_moyen=[bool(x) and x == ('M', 1) for x in sig],
             sig_short_moyen=[bool(x) and x == ('M', -1) for x in sig],
             clx_buy=[x == 1 for x in S['clx']], clx_sell=[x == -1 for x in S['clx']],
             tl_cassure_haut=S['rB'], tl_cassure_bas=S['sB'],
             zh_mitigee=S['mitB'], zb_mitigee=S['mitS'])
    for cible in (60, 240):
        if S['tfm'] < cible:
            h = features.resample_real(S, cible)
            d['trend_%d' % cible] = [bool(x and x['trend']) for x in h]
            d['ok_trend_%d' % cible] = [x is not None for x in h]
        else:
            d['trend_%d' % cible] = [False] * n
            d['ok_trend_%d' % cible] = [False] * n
    # Feu : proxy 12 voix de tools/strategie/strat.py, ramené sur 29 voix
    Sx = dict(S)
    try:
        ST.ensure_feu(Sx)
        part = nanf(Sx['feu'])
    except Exception:
        part = np.full(n, np.nan)
    fl = np.round(part * 29)
    d['feu_l'] = fl
    d['feu_s'] = np.where(np.isfinite(fl), 29 - fl, np.nan)
    df = pd.DataFrame(d, index=pd.DatetimeIndex(S['T']).tz_convert('Europe/Paris'))
    df.index.name = 'time'
    return df


def _depuis_cache(marche, ut):
    S = [s for s in _series_cache() if s['sym'] in _SYM_CACHE[marche] and s['tfm'] == int(ut)]
    if not S:
        return None
    S.sort(key=lambda s: -s['n'])                     # en cas de chevauchement : la plus longue gagne
    dfs = [_vers_df(s) for s in S]
    df = pd.concat(dfs)
    df = df[~df.index.duplicated(keep='first')].sort_index()
    df.attrs.update(symbole=marche, ut=str(ut), source='cache')
    return df


if __name__ == '__main__':
    for m in ('MNQ', 'MES'):
        for u in (1, 2, 3, 5, 15, 30, 60):
            df = charger_donnees(m, u)
            if df is None:
                print(m, u, 'absent'); continue
            print(m, u, len(df), df.index[0], df.index[-1],
                  'sigF', int(df.sig_long_fort.sum() + df.sig_short_fort.sum()),
                  'flips', int(df.hei_flip_haut.sum() + df.hei_flip_bas.sum()),
                  'clx', int(df.clx_buy.sum() + df.clx_sell.sum()),
                  'tl', int(df.tl_cassure_haut.sum() + df.tl_cassure_bas.sum()))
