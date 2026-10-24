"""Lignes du registre de l'agent SOR (une par recette retenue + le résultat négatif principal).

    ~/venv-quant/bin/python registre_sor.py

À lancer APRÈS etude.py (lit resultats/E_recettes.csv et E_white.pkl). Idempotent : une recette déjà présente
dans le registre (même agent, même texte de recette) n'est pas réécrite.
"""
import os
import pickle
import sys

import pandas as pd

import etude as E

sys.path.insert(0, os.path.join(E.SB, 'moteur'))
from registre import ajouter_test  # noqa: E402

NOMS_DECL = {'clx_buy': 'climax BUY', 'A_clx_trend': 'climax BUY + TREND 1H', 'hei': 'flip Heishinator',
             'clx_sell': 'climax SELL', 'sigF': 'Signator Fort', 'tl': 'cassure de trendline', 'orb': 'cassure ORB',
             'mon': 'cassure Monday'}
NOMS_STOP = {'atr2': 'stop 2 ATR', 'atr3': 'stop 3 ATR', 'atr1.5': 'stop 1,5 ATR',
             'niv:PW:0.25a:0.75-2:saute': 'stop derrière le pivot weekly le plus proche (marge 0,25 ATR, '
                                          'distance 0,75-2 ATR, trade sauté sans pivot)',
             'niv:TOUT:0.1a:0.5-3:2': 'stop derrière le niveau le plus proche toutes familles (marge 0,1 ATR, '
                                      '0,5-3 ATR, repli 2 ATR)'}
NOMS_SORTIE = {'hei': 'sortie flip Heishinator', 'BE1+R3': 'break-even à 1R puis objectif 3R',
               'BE1+R2': 'break-even à 1R puis objectif 2R'}
N_VAR = 257 * 2 + 399          # étape A (257 stops x 2 sorties) + étape B (399 gestions), par déclencheur
FICHIER = 'KAIROS/recherche/sorties/RESULTATS.md'


def deja(recette):
    R = pd.read_csv(os.path.join(E.REG, 'registre_tests.csv'))
    return ((R['agent'] == 'SOR') & (R['recette'] == recette)).any()


def trades(decl, ns, so, decls=None):
    out = []
    for d in (decls or [decl]):
        T = E.tous(d, lambda P: E.lancer(P, d, E.distances_stop(P, ns), so))
        if len(T):
            out.append(T)
    T = pd.concat(out, ignore_index=True)
    T['niveau_stop'] = NOMS_STOP.get(ns, ns)
    return T


def marche(T):
    return ' + '.join(sorted(set(T['serie'].str.split('_').str[0])))


def ecrire(recette, famille, T, p_tradeify, p_ref, verdict):
    if deja(recette):
        print('déjà au registre :', recette[:70]); return None
    id_ = ajouter_test(dict(agent='SOR', famille=famille, recette=recette, marche=marche(T), ut_signal='15m',
                            ut_entree='15m', echantillon=E.ECHANTILLON, n_variantes_testees=N_VAR,
                            p_tradeify=p_tradeify, p_ref_hasard=p_ref, verdict=verdict, fichier=FICHIER,
                            trades=T), prefixe='SOR')
    print(id_, recette[:80]); return id_


def main():
    R = pd.read_csv(os.path.join(E.OUT, 'E_recettes.csv')).set_index('decl')
    W = pickle.load(open(os.path.join(E.OUT, 'E_white.pkl'), 'rb'))
    hz = R.loc['hasard']
    avert = ('White p = %.2f sur %d gestions ; témoin au hasard avec SA meilleure gestion : P %.2f -> P(réussite) '
             'gonflée par le choix' % (W['white_p'], W['white_n'], hz.p_reussite))
    for decl, fam in (('clx_buy', 'gestion/stop ATR'), ('A_clx_trend', 'gestion/break-even'),
                      ('hei', 'gestion/stop niveau')):
        b = R.loc[decl]
        rec = '%s ; %s + %s ; risque fixe %d $/trade (Tradeify Select Flex)' % (
            NOMS_DECL[decl], NOMS_STOP.get(b.stop, b.stop), NOMS_SORTIE.get(b.sortie, b.sortie), b.risque_usd)
        T = trades(decl, b.stop, b.sortie)
        v = ('prometteur, non confirmé : %d trades, R %+.2f, P(1er payout) %.2f, VE %.0f $ contre %.0f $ avec 2 ATR + '
             'Heishinator ; bat la référence hasard (p = %.2f) ; %s' % (
                 b.n, b.r_moyen, b.p_1er_payout, b.ve, b.base_ve, b.p_hasard_ve, avert))
        ecrire(rec, fam, T, b.p_reussite, b.p_ref_hasard, v)
    # résultat négatif principal : stop derrière le niveau le plus proche, toutes familles
    decls = [d for d in E.liste_decl() if d != 'hasard']
    ns = 'niv:TOUT:0.1a:0.5-3:2'
    T = trades(None, ns, 'hei', decls)
    _, best = E.eval_propfirm(T)
    Tr = trades(None, 'atr2', 'hei', decls)
    rec = ('panel 8 déclencheurs 15m ; %s + sortie Heishinator ; risque fixe %d $/trade' % (NOMS_STOP[ns],
                                                                                              best['risque_usd']))
    v = ('rejeté : R %+.2f contre %+.2f avec 2 ATR sur les mêmes signaux ; stop trop près (%.1f ATR en moyenne), '
         '%.0f %% des trades stoppés ; ne bat pas son placebo (distance permutée)' % (
             T['r'].mean(), Tr['r'].mean(), T['dist_atr'].mean(),
             100 * T['motif_sortie'].astype(str).str.contains('stop').mean()))
    ecrire(rec, 'stop/niveau', T, best['p_reussite'], None, v)


if __name__ == '__main__':
    main()
