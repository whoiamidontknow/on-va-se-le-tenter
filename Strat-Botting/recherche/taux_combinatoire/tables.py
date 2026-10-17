"""Étape 1 : tables d'issues (moteur commun) pour chaque jeu × géométrie, + vérification contre moteur.backtest.

    ~/venv-quant/bin/python tables.py [--source cache|dataset]
Écrit sorties/tables_<source>.pkl (relancer est inutile si le fichier existe, sauf --recalcul).
"""
from __future__ import annotations

import argparse
import os
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import bib_wrx as B  # noqa: E402
import donnees_wrx as D  # noqa: E402

M = D.M
SORTIES = os.path.join(ICI, 'sorties')
os.makedirs(SORTIES, exist_ok=True)

_J = None


def _init(source):
    global _J
    _J = D.charger_jeux(source)


def _travail(args):
    ji, g = args
    j = _J[ji]
    return ji, g, B.table_issues(j['df'], j['instrument'], g, j['ut'])


def construire(source, recalcul=False):
    chemin = os.path.join(SORTIES, 'tables_%s.pkl' % source)
    if os.path.exists(chemin) and not recalcul:
        with open(chemin, 'rb') as fh:
            return pickle.load(fh)
    jeux = D.charger_jeux(source)
    taches = [(ji, g) for ji in range(len(jeux)) for g in B.geometries()]
    T = {}
    t0 = time.time()
    with ProcessPoolExecutor(8, initializer=_init, initargs=(source,)) as ex:
        for ji, g, tab in ex.map(_travail, taches, chunksize=4):
            T[(ji, g)] = tab
    print('tables : %d en %.0f s' % (len(T), time.time() - t0), flush=True)
    with open(chemin, 'wb') as fh:
        pickle.dump(T, fh)
    return T


def trades_table(tab, L, S):
    """Trades (indices de barre, sens 0/1) d'une variante à partir de la table (règle une position à la fois)."""
    both = L & S
    L = L & ~both; S = S & ~both
    iL = np.flatnonzero(L & tab['ok'][0]); iS = np.flatnonzero(S & tab['ok'][1])
    idx = np.concatenate([iL, iS]); d = np.concatenate([np.zeros(len(iL), np.int64), np.ones(len(iS), np.int64)])
    o = np.argsort(idx, kind='stable'); idx, d = idx[o], d[o]
    g = B.glouton(idx, d, tab['klibre'])
    return idx[g], d[g]


def verifier(T, source):
    """Compare table + glouton au moteur sur les signaux réels (tous déclencheurs, les deux sens)."""
    jeux = D.charger_jeux(source)
    rng = np.random.default_rng(0)
    geos = B.geometries()
    ecarts = 0; total = 0
    for ji, j in enumerate(jeux):
        df = j['df']
        for g in [geos[k] for k in rng.choice(len(geos), 6, replace=False)]:
            for dec in ('tous', 'hei_flip', 'clx'):
                L, S = B.declencheur(df, dec)
                tab = T[(ji, g)]
                idx, d = trades_table(tab, L, S)
                ref = M.backtest(df, long=L, short=S, gestion=B.gestion(df, j['instrument'], g, j['ut']), details=True)
                a = list(zip(idx.tolist(), np.where(d == 0, 'long', 'short').tolist(),
                             np.round(tab['r'][d, idx], 9).tolist()))
                b = list(zip(ref['i_signal'].tolist(), ref['sens'].tolist(), np.round(ref['r'].to_numpy(), 9).tolist()))
                total += 1
                if a != b:
                    ecarts += 1
                    print('ÉCART', j['nom'], g, dec, len(a), len(b))
    print('vérification table vs moteur : %d / %d cas identiques' % (total - ecarts, total), flush=True)
    return ecarts == 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', default=D.SOURCE)
    ap.add_argument('--recalcul', action='store_true')
    a = ap.parse_args()
    T = construire(a.source, a.recalcul)
    verifier(T, a.source)
