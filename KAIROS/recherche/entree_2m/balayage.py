"""Balayage « signal S -> déclenchement X » sur la partie DÉVELOPPEMENT (coupure du cadre d'exécution).

    ~/venv-quant/bin/python balayage.py --marche MNQ --us 15 --ux 2 --niveau complet
    E2M_SOURCE=dataset ~/venv-quant/bin/python balayage.py ...        # sur les exports DATASET

Écrit (au fil de l'eau, une famille à la fois) dans resultats/ :
  balayage_<marche>_<us>_<ux>.csv   une ligne par variante (métriques, gain d'entrée, stop, coûts, risque fixe)
  trades_<marche>_<us>_<ux>.pkl     tous les trades de toutes les variantes (colonne vid), pour l'analyse
"""
from __future__ import annotations

import argparse
import itertools
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import affinage as A  # noqa: E402
import donnees as D   # noqa: E402

M = A.M
SORTIE = os.path.join(ICI, 'resultats')

DECLENCHEURS = ['hei_flip', 'hei_aligne', 'cassure', 'sigX', 'rejet_ema']
LIMITES = ['lim_milieu', 'lim_ema50', 'lim_atr']
NIVEAUX = {
    'complet': dict(familles=list(A.FAMILLES), filtres=['', 'trend'], fenetres=[15, 30],
                    stops=['swing', 'bougieS', 'atrS2'], objs=['R2', 'heiS']),
    'leger': dict(familles=list(A.FAMILLES), filtres=[''], fenetres=[30],
                  stops=['swing', 'atrS2'], objs=['R2']),
}


def preparer(marche, us, ux):
    """(contexte, période) sur le développement, coupure du cadre d'exécution imposée aux deux cadres."""
    dX = D.charger_donnees(marche, ux)
    dS = D.charger_donnees(marche, us)
    if dX is None or dS is None:
        return None
    cut = M.date_coupure(dX)
    dX = M.charger_recherche(dX, coupure=cut, agent='E2M')
    dS = M.charger_recherche(dS, coupure=cut, agent='E2M')
    return A.Contexte(dX, dS, marche)


def stats(T, n_evt, n_decl):
    d = dict(n_evt=n_evt, n_decl=n_decl, n=len(T))
    if not len(T):
        return d
    r = T['r'].to_numpy(float); p = T['pnl_usd'].to_numpy(float)
    g, l_ = p[p > 0].sum(), -p[p < 0].sum()
    nf, pfx = A.a_risque_fixe(T)
    ok = nf > 0
    d.update(pct_g=float((p > 0).mean()), r_moyen=float(r.mean()), pf=float(g / l_) if l_ > 0 else np.inf,
             net_usd=float(p.sum()),
             gain_entree_pts=float(T['gain_entree_pts'].mean()), gain_entree_atrS=float(T['gain_entree_atrS'].mean()),
             stop_pts=float(T['stop_pts'].mean()), risque_usd=float(T['risque_usd'].mean()),
             cout_R=float(T['cout_R'].mean()), micros=float(nf[ok].mean()) if ok.any() else 0.0,
             n_fixe=int(ok.sum()), net_fixe=float(pfx.sum()),
             r_fixe=float(pfx.sum() / (A.RISQUE_FIXE * ok.sum())) if ok.any() else np.nan)
    return d


def balayer(marche, us, ux, niveau='complet', log=print):
    os.makedirs(SORTIE, exist_ok=True)
    ctx = preparer(marche, us, ux)
    if ctx is None:
        log('données absentes', marche, us, ux)
        return
    N = NIVEAUX[niveau]
    base = '%s_%s_%s' % (marche, us, ux)
    f_csv = os.path.join(SORTIE, 'balayage_%s.csv' % base)
    f_pkl = os.path.join(SORTIE, 'trades_%s.pkl' % base)
    sortie_S = ctx.sortie_heiS()
    lignes, trades = [], []
    t0 = time.time()
    entrees = [('direct', 0)] + [(e, w) for e in DECLENCHEURS + LIMITES for w in N['fenetres']]
    for fam in N['familles']:
        for filt in N['filtres']:
            L, S = A.signaux_S(ctx.dfS, fam, filt)
            ev = ctx.evenements(L, S)
            for ent, wmin in entrees:
                W = max(1, int(round(wmin / ctx.bx.ut))) if wmin else 1
                cons = ctx.construire(ev, ent, W)
                for stop, obj in itertools.product(N['stops'], N['objs']):
                    vid = '|'.join([fam, filt or '-', ent, str(wmin), stop, obj])
                    T, _, _, _ = A.lancer(ctx, ev, ent, W, stop, obj, cons=cons, sortie_S=sortie_S)
                    T = A.enrichir(ctx, ev, T)
                    lignes.append(dict(marche=marche, us=us, ux=ux, vid=vid, famille=fam, filtre=filt or '-',
                                       entree=ent, W_min=wmin, stop=stop, obj=obj,
                                       **stats(T, len(ev), cons['n_decl'])))
                    if len(T):
                        T = T.drop(columns=['k_entree', 'k_sortie'])
                        T.insert(0, 'vid', vid)
                        trades.append(T)
        # écriture intermédiaire après chaque famille
        pd.DataFrame(lignes).to_csv(f_csv, index=False)
        with open(f_pkl, 'wb') as fh:
            pickle.dump(pd.concat(trades, ignore_index=True) if trades else pd.DataFrame(), fh)
        log('%s %s : %d variantes, %.0f s' % (base, fam, len(lignes), time.time() - t0))
    meta = dict(debut=str(ctx.dfX.index[0]), fin=str(ctx.dfX.index[-1]), n_barres_X=len(ctx.dfX),
                segments=len(ctx.segments), source=D.SOURCE)
    with open(os.path.join(SORTIE, 'meta_%s.pkl' % base), 'wb') as fh:
        pickle.dump(meta, fh)
    return f_csv


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--marche', default='MNQ')
    ap.add_argument('--us', type=int, default=15)
    ap.add_argument('--ux', type=int, default=2)
    ap.add_argument('--niveau', default='complet')
    a = ap.parse_args()
    balayer(a.marche, a.us, a.ux, a.niveau, log=lambda *x: print(*x, flush=True))
