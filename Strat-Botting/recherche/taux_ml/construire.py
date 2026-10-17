"""Étape 1 (taux_ml) : table candidats x variables x issues pour les géométries « taux de réussite ».

Réutilise recherche/meta_ml (donnees, candidats) sans le modifier :
- candidats et 64 variables : candidats.candidats() (union des 12 déclencheurs, variables au moment du signal) ;
- issues : candidats.issues_isolees() avec NOS gestions (chaque candidat seul dans le moteur, intrajournée 15:59).
Ajoute des interactions simples : séance x déclencheur, distance aux niveaux x sens, niveau le plus proche
devant / derrière le trade.

    ~/venv-quant/bin/python construire.py [--source dataset]
"""
import argparse
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
META = os.path.join(os.path.dirname(ICI), 'meta_ml')
sys.path[:0] = [META]
import candidats as CD  # noqa: E402  (recherche/meta_ml)
import donnees  # noqa: E402          (recherche/meta_ml : point d'accès unique aux données)

CACHE = os.path.join(ICI, 'cache', 'table_taux.pkl')

# Géométries FIXÉES À L'AVANCE (stop ATR x k, objectif en R, break-even optionnel)
GEOMETRIES = {
    'S1R1': dict(stop=1.0, obj=1.0, be=None),
    'S1R1_BE': dict(stop=1.0, obj=1.0, be=0.5),
    'S15R1': dict(stop=1.5, obj=1.0, be=None),
    'S15R1_BE': dict(stop=1.5, obj=1.0, be=0.5),
    'S2R1': dict(stop=2.0, obj=1.0, be=None),
    'S2R1_BE': dict(stop=2.0, obj=1.0, be=0.5),
    'S2R05': dict(stop=2.0, obj=0.5, be=None),
}
SEANCES = ('nuit', 'londres', 'us')


def gestion(instrument, geo):
    g = GEOMETRIES[geo]
    out = dict(instrument=instrument, heure_sortie='15:59', stop={'mode': 'atr', 'k': g['stop']},
               objectif={'mode': 'R', 'k': g['obj']})
    if g['be']:
        out['break_even'] = {'R': g['be'], 'ticks': 1}
    return out


def gestions(instrument):
    return {k: gestion(instrument, k) for k in GEOMETRIES}


def interactions(C):
    """Interactions simples, ajoutées en place ; renvoie {colonne: groupe}."""
    grp = {}
    for s in SEANCES:
        for t in CD.TYPES:
            k = 'x_%s_%s' % (s, t)
            C[k] = C['seance_' + s] * C['trig_' + t]
            grp[k] = 'Séance x déclencheur'
    dcols = [c for c in C.columns if c.startswith('d_')]
    for c in dcols:
        k = 'x_long_' + c
        C[k] = C[c] * C['sens_long']
        grp[k] = 'Niveaux x sens'
    D = C[dcols].to_numpy(float)
    with np.errstate(invalid='ignore'):
        dev = np.where(D > 0, D, np.inf).min(1)
        der = np.where(D < 0, D, -np.inf).max(1)
    C['d_devant_min'] = np.where(np.isfinite(dev), dev, np.nan)
    C['d_derriere_min'] = np.where(np.isfinite(der), -der, np.nan)   # distance (> 0) au niveau derrière
    grp['d_devant_min'] = grp['d_derriere_min'] = 'Niveaux (le plus proche)'
    return grp


def construire(source=None):
    series = donnees.charger_series(source)
    tabs = []
    for s in series:
        t0 = time.time()
        C = CD.candidats(s['df'], s['nom'], s['instrument'])
        I = CD.issues_isolees(s['df'], C, gestions(s['instrument']), s['ut_min'])
        tabs.append(pd.concat([C, I], axis=1))
        print('%s : %d barres, %d candidats (%.0f s)' % (s['nom'], len(s['df']), len(C), time.time() - t0), flush=True)
    T = pd.concat(tabs, ignore_index=True).sort_values(['t_signal', 'serie', 'sens']).reset_index(drop=True)
    groupes = dict(CD.GROUPES)
    groupes.update(interactions(T))
    T = pd.concat([T, pd.DataFrame({'y_' + g: np.where(T['r_' + g].notna(), (T['pnl_' + g] > 0).astype(float), np.nan)
                                    for g in GEOMETRIES}, index=T.index)], axis=1)
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    pickle.dump(dict(table=T, groupes=groupes, source=source or 'cache'), open(CACHE, 'wb'))
    return T


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', default=None)
    a = ap.parse_args()
    T = construire(a.source)
    print(T.shape)
    for g in GEOMETRIES:
        r = T['r_' + g]
        print('%-9s résolus %d  R moyen %+.3f  gagnants %.1f %%' % (g, r.notna().sum(), r.mean(), 100 * T['y_' + g].mean()))
