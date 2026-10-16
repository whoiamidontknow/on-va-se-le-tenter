"""Synthèse des études SL / TP (cache_sl.pkl, cache_tp.pkl) : tableaux appariés contre la référence,
apprentissage MES (MES1! avr.-juil. + MESZ sep.-oct.) -> validation NQ, bootstrap par jour."""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.join(HERE, '..', 'maemfe'))
from core import boot_moyenne   # noqa: E402

pd.set_option('display.width', 250); pd.set_option('display.max_rows', 400)
GROUPES = {'Aleatoire': ['Aleatoire'], 'Signaux': ['Trendline', 'Heishinator', 'Climax BUY', 'Fleche Fort'],
           'Preset A': ['Preset A'], 'Preset C': ['Preset C']}


def pf(x):
    g = x[x > 0].sum(); l_ = -x[x <= 0].sum()
    return g / l_ if l_ > 0 else np.inf


def resume(df, ref, key=('trig', 'sym', 'i', 'd')):
    """Par variante : n, sautés, stop, R, $, PF, et écarts appariés à la référence (MES / NQ / tout)."""
    key = list(key)
    R0 = df[df['var'] == ref].set_index(key)
    out = []
    for v, g in df.groupby('var'):
        pris = g[~g['saute']]
        rec = dict(var=v, n=len(pris), saute=float(g['saute'].mean()) if 'saute' in g else 0.0)
        if len(pris) < 30:
            out.append(rec); continue
        rec.update(stop=float(pris['stop'].mean()), R=float(pris['R'].mean()), usd=float(pris['usd'].mean()),
                   pf=float(pf(pris['usd'].values)))
        j = pris.set_index(key).join(R0[['R', 'usd']], rsuffix='_ref', how='inner')
        for nm, m in (('TOUT', slice(None)), ('MES', j['inst'] == 'MES'), ('NQ', j['inst'] == 'NQ')):
            x = j[m] if nm != 'TOUT' else j
            if len(x) < 30:
                rec['dR_' + nm] = np.nan; rec['dusd_' + nm] = np.nan; continue
            yR = (x['R'] - x['R_ref']).values; yU = (x['usd'] - x['usd_ref']).values
            mR, loR, hiR = boot_moyenne(yR, x['jour'].values, B=1000)
            mU, loU, hiU = boot_moyenne(yU, x['jour'].values, B=1000)
            rec['dR_' + nm] = mR; rec['dR_%s_lo' % nm] = loR; rec['dR_%s_hi' % nm] = hiR
            rec['dusd_' + nm] = mU; rec['dusd_%s_lo' % nm] = loU; rec['dusd_%s_hi' % nm] = hiU
            rec['R_' + nm] = float(x['R'].mean()); rec['usd_' + nm] = float(x['usd'].mean())
        out.append(rec)
    return pd.DataFrame(out)


def sl(df):
    res = {}
    for gn, trigs in GROUPES.items():
        for so in ('Heishinator', 'Objectif 2R', 'Objectif 3 ATR'):
            d = df[df['trig'].isin(trigs) & ((df['sortie'] == so) | (df['saute']))]
            # les lignes « sautées » n'ont pas de sortie : on les garde pour le taux de saut
            r = resume(d, 'ATR2.0')
            res[(gn, so)] = r
    return res


def tp(df):
    res = {}
    for gn, trigs in GROUPES.items():
        for st in df['stop_var'].dropna().unique():
            d = df[df['trig'].isin(trigs) & (df['stop_var'] == st)]
            res[(gn, st)] = resume(d, 'Heishinator')
    return res


COLS = ['var', 'n', 'saute', 'stop', 'R', 'usd', 'pf', 'dR_MES', 'dR_NQ', 'dR_TOUT', 'dR_TOUT_lo', 'dR_TOUT_hi',
        'dusd_MES', 'dusd_NQ', 'dusd_TOUT', 'dusd_TOUT_lo', 'dusd_TOUT_hi', 'usd_MES', 'usd_NQ']


def affiche(r, top=None, tri='dR_MES', filtre=None):
    r = r.copy()
    if filtre is not None: r = r[r['var'].str.contains(filtre, regex=False) | ~r['var'].str.startswith('NIV')]
    if tri in r: r = r.sort_values(tri, ascending=False)
    if top: r = pd.concat([r[~r['var'].str.startswith('NIV')], r[r['var'].str.startswith('NIV')].head(top)])
    c = [x for x in COLS if x in r.columns]
    return r[c].to_string(index=False, float_format=lambda x: '%.3f' % x if abs(x) < 10 else '%.0f' % x)


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'sl'
    if which == 'sl':
        df = pd.read_pickle(os.path.join(HERE, 'cache_sl.pkl'))
        R = sl(df)
        pd.to_pickle(R, os.path.join(HERE, 'cache_sl_resume.pkl'))
        for k, r in R.items():
            print('=====', k); print(affiche(r, top=12)); print()
    else:
        df = pd.read_pickle(os.path.join(HERE, 'cache_tp.pkl'))
        R = tp(df)
        pd.to_pickle(R, os.path.join(HERE, 'cache_tp_resume.pkl'))
        for k, r in R.items():
            print('=====', k); print(affiche(r, top=15)); print()
