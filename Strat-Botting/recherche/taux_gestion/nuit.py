"""Hypothèse FIXÉE À L'AVANCE (CONSIGNES_TAUX) : la nuit (entrées 0 h-8 h Paris) est meilleure.
Testée sur ML-0001 (seule entrée du panel qui trade la nuit), pour CHAQUE gestion du balayage, sans réglage :
taux de gagnants et R, réel contre placebo de même gestion (même heure, même sens), nuit contre jour.
    ~/venv-quant/bin/python nuit.py   -> resultats/nuit_ML-0001.csv
"""
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

import etude_wrs as W

D = 'ML-0001'


def _tache(args):
    k, so = args
    T = TR[(TR['stop'] == k) & (TR['sortie'] == so)].copy()
    tables = {}
    for P in W.DW.charger(15):
        if D not in P['decl']:
            continue
        g = W.gestion(P, k, so, None)
        r1, p1 = W.issues(P, g, 1); r_1, p_1 = W.issues(P, g, -1)
        tables[P['nom']] = dict(r1=r1, p1=p1, r_1=r_1, p_1=p_1, heure=W.heure_clo(P))
    T['nuit'] = pd.to_datetime(T['entree_t']).dt.tz_convert('Europe/Paris').dt.hour < 8
    row = dict(stop=k, sortie=so)
    for nom, t in (('nuit', T[T['nuit']]), ('jour', T[~T['nuit']])):
        st = W.stats_r(t['r'], t['pnl']); pl = W.placebo(t, tables, n_plac=1000, graine=5)
        row.update({'%s_n' % nom: st['n'], '%s_win' % nom: st.get('win'), '%s_r' % nom: st.get('r'),
                    '%s_win_plac' % nom: pl['win'].mean(), '%s_r_plac' % nom: pl['r'].mean(),
                    '%s_p_r' % nom: (1 + (pl['r'] >= st['r']).sum()) / 1001})
    return row


TR = pd.read_pickle(os.path.join(W.OUT, 'trades_balayage.pkl'))
TR = TR[TR['decl'] == D]

if __name__ == '__main__':
    with ProcessPoolExecutor(max_workers=9) as ex:
        rows = list(ex.map(_tache, W.GESTIONS, chunksize=4))
    N = pd.DataFrame(rows)
    N.to_csv(os.path.join(W.OUT, 'nuit_ML-0001.csv'), index=False)
    N['ex_nuit'] = N['nuit_r'] - N['nuit_r_plac']; N['ex_jour'] = N['jour_r'] - N['jour_r_plac']
    print('gestions : %d ; R nuit > R jour : %.0f %% ; écart au placebo nuit > jour : %.0f %%'
          % (len(N), 100 * (N['nuit_r'] > N['jour_r']).mean(), 100 * (N['ex_nuit'] > N['ex_jour']).mean()))
    print(N[['nuit_n', 'nuit_win', 'nuit_win_plac', 'nuit_r', 'nuit_r_plac', 'nuit_p_r', 'jour_n', 'jour_win',
             'jour_win_plac', 'jour_r', 'jour_r_plac', 'jour_p_r']].mean().round(3).to_string())
    print('part des gestions p_r <= 0,05 : nuit %.2f, jour %.2f' % ((N['nuit_p_r'] <= .05).mean(), (N['jour_p_r'] <= .05).mean()))
