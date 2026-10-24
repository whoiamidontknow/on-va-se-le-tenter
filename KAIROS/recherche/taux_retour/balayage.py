"""Étape 1 : balayage complet des setups de retour à la moyenne (agent WRF).

    ~/venv-quant/bin/python balayage.py            # -> resultats/balayage.csv + resultats/trades_balayage.pkl

Variante = setup (catalogue de setups.py) × stop (ext / 1 ATR / 2 ATR) × objectif (0,5 / 0,75 / 1 / 1,5 R, EMA50,
milieu du range 20 barres) × sortie temporelle (aucune / 8 barres). Chaque variante tourne dans le moteur commun
sur chaque série (une position à la fois, intrajournée 15:59 Chicago, coûts par instrument) ; les trades sont
gardés avec la série et l'indice de la barre signal.
"""
from __future__ import annotations

import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import donnees_wrf as D  # noqa: E402
import setups as ST  # noqa: E402
import moteur as M  # noqa: E402

OUT = os.path.join(ICI, 'resultats')


def lancer_variante(series, sig, stop, cible, temps):
    morceaux = []
    for s in series:
        L, S = sig[s['nom']]
        if not (L.any() or S.any()):
            continue
        g = ST.gestion(s['df'], s['instrument'], stop, cible, temps)
        T = M.backtest(s['df'], long=L, short=S, gestion=g, details=True)
        if len(T):
            T['serie'] = s['nom']; T['instrument'] = s['instrument']
            morceaux.append(T)
    return pd.concat(morceaux, ignore_index=True).sort_values('entree_t').reset_index(drop=True) if morceaux else None


def stats(T):
    if T is None or not len(T):
        return dict(n=0)
    r = T['r'].to_numpy(float)
    g, p = T.loc[T['pnl_usd'] > 0, 'pnl_usd'].sum(), -T.loc[T['pnl_usd'] < 0, 'pnl_usd'].sum()
    return dict(n=len(T), pct_gagnants=float((T['pnl_usd'] > 0).mean()), r_moyen=float(r.mean()),
                pf=float(g / p) if p > 0 else np.nan, net_usd=float(T['pnl_usd'].sum()),
                r_cible_moyen=float((np.abs(T['objectif'] - T['prix_entree']) /
                                     np.abs(T['prix_entree'] - T['stop_initial'])).mean()))


def main():
    os.makedirs(OUT, exist_ok=True)
    series = D.charger_series()
    t0 = time.time()
    lignes, trades = [], {}
    for code, fam, fn in ST.catalogue():
        sig = {s['nom']: ST.signaux(s['df'], s['instrument'], fn) for s in series}
        nsig = sum(int(L.sum() + S.sum()) for L, S in sig.values())
        for stop in ST.STOPS:
            for cible in ST.CIBLES:
                for temps in ST.TEMPS:
                    v = '%s|%s|%s|t%d' % (code, stop, cible, temps)
                    T = lancer_variante(series, sig, stop, cible, temps)
                    trades[v] = T
                    lignes.append(dict(variante=v, setup=code, famille=fam, stop=stop, cible=cible, temps=temps,
                                       n_signaux=nsig, **stats(T)))
        print('%6.0fs %s' % (time.time() - t0, code), flush=True)
    B = pd.DataFrame(lignes)
    B.to_csv(os.path.join(OUT, 'balayage.csv'), index=False)
    pickle.dump(trades, open(os.path.join(OUT, 'trades_balayage.pkl'), 'wb'))
    print('variantes :', len(B), ' avec >= 60 trades :', int((B['n'] >= 60).sum()))


if __name__ == '__main__':
    main()
