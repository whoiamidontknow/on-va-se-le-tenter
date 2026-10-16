"""Analyse a posteriori des sorties de aiguillage.py (à lancer après lui) : surapprentissage et stabilité des choix.

    ~/venv-quant/bin/python analyse.py
"""
import os

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))


def main():
    V = pd.read_csv(os.path.join(ICI, 'walk_forward_variantes.csv'))
    C = pd.read_csv(os.path.join(ICI, 'choix_par_pli.csv'))
    V['decote'] = V['r_dev'] - V['r_oos']
    print('Décote moyenne développement -> pli suivant : %+.3f R par trade (médiane %+.3f) sur %d variantes'
          % (V['decote'].mean(), V['decote'].median(), V['decote'].notna().sum()))
    print('Corrélation R dev / R hors échantillon entre variantes : %.2f'
          % V[['r_dev', 'r_oos']].dropna().corr().iloc[0, 1])
    rows = []
    for (P, t), g in C.groupby(['partition', 't_min']):
        piv = g.pivot(index='etat', columns='pli', values='setup')
        same = [(piv[p] == piv[p + 1]).mean() for p in piv.columns[:-1]]
        rows.append(dict(partition=P, t_min=t, stabilite=float(np.mean(same)),
                         part_pas_de_trade=float((g['setup'] == 'PAS DE TRADE').mean())))
    S = pd.DataFrame(rows)
    S.to_csv(os.path.join(ICI, 'stabilite_choix.csv'), index=False, float_format='%.3f')
    print('\nStabilité (part des états dont le setup choisi est le même d\'un pli au suivant) :')
    print(S.to_string(index=False, float_format=lambda v: '%.2f' % v))


if __name__ == '__main__':
    main()
