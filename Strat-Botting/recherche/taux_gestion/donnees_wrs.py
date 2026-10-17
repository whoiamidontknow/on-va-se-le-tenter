"""Accès aux données de l'agent « Taux — géométrie et gestion » (WRS).

TOUT l'accès aux données passe par `charger(ut)` : il appelle `recherche/sorties/donnees_sor.charger_series`
(même préparation que l'agent SOR : vrais prix, ATR, Heishinator, niveaux, déclencheurs), garde la partie
DÉVELOPPEMENT seulement (moteur.charger_recherche, scellé jamais lu) et ajoute les entrées publiées au registre
(ML-0001, EXH-0001..0003) reconstruites depuis leurs listes de trades.

Passer au DATASET :  WRS_SOURCE=dataset ~/venv-quant/bin/python etude_wrs.py
(les séries préparées sont mises en cache dans resultats/series_<source>_<ut>.pkl).
"""
from __future__ import annotations

import os
import pickle
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
SB = os.path.abspath(os.path.join(ICI, '..', '..'))
SOURCE = os.environ.get('WRS_SOURCE', 'cache')            # 'cache' | 'dataset'
os.environ['SOR_SOURCE'] = SOURCE
for p in (os.path.join(SB, 'recherche', 'sorties'), os.path.join(SB, 'moteur'), os.path.join(SB, 'propfirm')):
    if p not in sys.path:
        sys.path.insert(0, p)
import etude as E          # noqa: E402  (outils de l'agent SOR, réutilisés tels quels)

OUT = os.path.join(ICI, 'resultats')
os.makedirs(OUT, exist_ok=True)
ECHANTILLON = 'dev_cache' if SOURCE == 'cache' else 'dev_dataset'

# Entrées publiées par les autres agents : id du registre -> UT du signal
ENTREES_REGISTRE = {'ML-0001': 15, 'EXH-0001': 30, 'EXH-0002': 30, 'EXH-0003': 60}

_MEMO = {}


def charger(ut: int = 15):
    """Point d'accès UNIQUE aux données. Liste de séries (dict de etude.preparer) avec P['decl'] complété
    par les entrées du registre dont l'UT correspond."""
    if ut in _MEMO:
        return _MEMO[ut]
    f = os.path.join(OUT, 'series_%s_%d.pkl' % (SOURCE, ut))
    if os.path.exists(f):
        S = pickle.load(open(f, 'rb'))
    else:
        E.OUT = OUT                                   # etude.preparer écrit son cache dans NOTRE dossier
        S = E.preparer(ut)
        for id_, u in ENTREES_REGISTRE.items():
            if u == ut:
                n_ok, n_tot = E.entrees_registre(id_, S)
                print('%s : %d / %d entrées retrouvées' % (id_, n_ok, n_tot))
        pickle.dump(S, open(f, 'wb'))
    _MEMO[ut] = S
    return S


if __name__ == '__main__':
    for ut in (15, 30, 60):
        for P in charger(ut):
            print(ut, P['nom'], len(P['df']), {k: int(l.sum() + s.sum()) for k, (l, s) in P['decl'].items()})
