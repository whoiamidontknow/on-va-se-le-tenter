"""Étape 1 : table candidats × variables × issues (3 gestions), sauvegardée dans cache/candidats.pkl.

    ~/venv-quant/bin/python construire.py [--source dataset]
"""
import argparse
import os
import pickle
import sys
import time

import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import donnees  # noqa: E402
import candidats as CD  # noqa: E402

CACHE = os.path.join(ICI, 'cache', 'candidats.pkl')


def construire(source=None):
    series = donnees.charger_series(source)
    tabs = []
    for s in series:
        t0 = time.time()
        C = CD.candidats(s['df'], s['nom'], s['instrument'])
        G = CD.gestions(s['df'], s['instrument'])
        I = CD.issues_isolees(s['df'], C, G, s['ut_min'])
        C = pd.concat([C, I], axis=1)
        tabs.append(C)
        print('%s : %d barres, %d candidats (%.0f s)' % (s['nom'], len(s['df']), len(C), time.time() - t0))
    T = pd.concat(tabs, ignore_index=True).sort_values(['t_signal', 'serie', 'sens']).reset_index(drop=True)
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    pickle.dump(dict(table=T, groupes=dict(CD.GROUPES), series=[{k: v for k, v in s.items()} for s in series]),
                open(CACHE, 'wb'))
    return T


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', default=None)
    a = ap.parse_args()
    T = construire(a.source)
    print(T.shape)
    print(T[[c for c in T.columns if c.startswith('trig_')]].sum())
    for g in ('A15R2', 'A1R1', 'NIV'):
        r = T['r_' + g]
        print(g, 'résolus', r.notna().sum(), 'R moyen %.3f' % r.mean(), '%% gagnants %.1f' % (100 * (r > 0).mean()))
