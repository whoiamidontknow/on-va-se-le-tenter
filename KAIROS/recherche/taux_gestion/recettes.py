"""Les 3 recettes retenues (gestion FIXE, écrite telle quelle dans un préréglage) : chiffres complets + registre.

    ~/venv-quant/bin/python recettes.py [--registre]   -> resultats/recettes.csv (+ lignes WRS du registre)

Pour chaque recette : trades du développement complet (moteur), placebo EXACT moteur.reference_hasard (1000 tirages,
même gestion, même heure, même sens, limité à la période où l'entrée a des signaux), chiffres des 5 blocs de test
du walk-forward (gestion fixe), walk-forward honnête (gestion choisie à chaque pli, final.csv), Tradeify Select Flex.
"""
import os
import sys

import numpy as np
import pandas as pd

import etude_wrs as W

RECETTES = [
    dict(cle='R1', decl='ML-0001', stop=3.0, sortie='R0.5',
         texte='entrées ML-1 (union des 12 déclencheurs) ; stop 3 ATR ; objectif 0,5 R ; à plat 15:59 Chicago'),
    dict(cle='R2', decl='ML-0001', stop=3.0, sortie='BE0.5t4+R2',
         texte='entrées ML-1 (union des 12 déclencheurs) ; stop 3 ATR ; break-even à 0,5 R (+4 ticks) ; objectif 2 R'),
    dict(cle='R3', decl='A_clx_trend', stop=3.0, sortie='BE0.5t2+R1',
         texte='préréglage A (climax BUY + TREND 1H, long) ; stop 3 ATR ; break-even à 0,5 R (+2 ticks) ; objectif 1 R'),
]
N_TIR = 1000


def evaluer(rc):
    d = rc['decl']; ut, pk = W.DECLS[d]
    reels, tir, blk = [], [[] for _ in range(N_TIR)], []
    for P in W.DW.charger(ut):
        if d not in P['decl']:
            continue
        L, S = P['decl'][d]
        g = W.gestion(P, rc['stop'], rc['sortie'], W.PLAGES[pk])
        T = W.M.backtest(P['df'], L, S, g, details=True)
        if not len(T):
            continue
        bl = W.blocs(P)
        T['serie'] = P['nom']; T['instrument'] = P['instrument']; T['blk'] = bl[T['i_signal'].to_numpy()]
        reels.append(T)
        # placebo exact, limité aux journées qui vont du 1er au dernier signal de l'entrée sur cette série
        sig = np.flatnonzero(L | S)
        j = W.M.barres(P['df']).jour_cme()
        m = (j >= j[sig[0]]) & (j <= j[sig[-1]])
        Pm = dict(P, c=P['c'][m], a=P['a'][m], lv={f: v[m] for f, v in P['lv'].items()})
        gm = W.gestion(Pm, rc['stop'], rc['sortie'], W.PLAGES[pk])
        _, trs = W.M.reference_hasard(P['df'][m], N_TIR, gm, graine=31, long=L[m], short=S[m], garder_trades=True)
        for q, t in enumerate(trs):
            if len(t):
                tir[q].append(t)
    T = pd.concat(reels, ignore_index=True)
    tir = [pd.concat(t, ignore_index=True) for t in tir if t]
    m = W.M.metriques(T, n_boot=1000)
    pw = np.array([(t['pnl_usd'] > 0).mean() for t in tir]); pr = np.array([t['r'].mean() for t in tir])
    r = T['r']
    test = T[T['blk'] >= 3]
    F = pd.read_csv(os.path.join(W.OUT, 'final.csv'))
    wf = F[(F['decl'] == d) & (F['mode'] == 'declencheur')].iloc[0]
    pf = W.propfirm(T, tir)
    row = dict(cle=rc['cle'], recette=rc['texte'], decl=d, stop=rc['stop'], sortie=rc['sortie'],
               n=m['n'], win=m['pct_gagnants'], win_plac=float(pw.mean()), ecart_pts=100 * (m['pct_gagnants'] - pw.mean()),
               p_win=float((1 + (pw >= m['pct_gagnants'] - 1e-12).sum()) / (1 + len(pw))),
               r=m['r_moyen'], r_ic=m['r_ic95'], r_plac=float(pr.mean()),
               p_r=float((1 + (pr >= m['r_moyen'] - 1e-12).sum()) / (1 + len(pr))),
               pf_usd=m['pf'], pf_r=float(r[r > 0].sum() / -r[r < 0].sum()), n_tirages=len(tir),
               n_test=len(test), win_test=float((test['pnl_usd'] > 0).mean()), r_test=float(test['r'].mean()),
               wf_n=int(wf['n']), wf_win=wf['win'], wf_win_plac=wf['win_plac'], wf_r=wf['r'], wf_p_win=wf['p_win'],
               **{'tf_' + k: v for k, v in pf.items()})
    return row, T


def main(registre=False):
    rows, trades = [], {}
    for rc in RECETTES:
        row, T = evaluer(rc)
        rows.append(row); trades[rc['cle']] = T
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items()}, flush=True)
    R = pd.DataFrame(rows)
    R.to_csv(os.path.join(W.OUT, 'recettes.csv'), index=False)
    if registre:
        ecrire_registre(R, trades)
    return R


def ecrire_registre(R, trades):
    sys.path.insert(0, os.path.join(W.DW.SB, 'moteur'))
    from registre import ajouter_test
    import pickle
    Wh = pickle.load(open(os.path.join(W.OUT, 'white.pkl'), 'rb'))
    reg = pd.read_csv(os.path.join(W.DW.SB, 'registre', 'registre_tests.csv'))
    n_var = len(W.GESTIONS) * len(W.DECLS)
    for _, x in R.iterrows():
        rec = x['recette'] + ' ; taille Tradeify %d micros' % x['tf_contrats']
        if ((reg['agent'] == 'WRS') & (reg['recette'] == rec)).any():
            print('déjà au registre :', rec[:60]); continue
        v = ('REJETÉ (critères non remplis) : en échantillon %.0f %% gagnants contre %.0f %% placebo même gestion '
             '(écart %+.1f pts, p %.3f), R %+.3f contre %+.3f ; walk-forward (gestion choisie par pli) %d trades, %.0f %% '
             'contre %.0f %% placebo, R %+.3f ; White RC p %.2f sur %d combinaisons dans la bande ; à revoir sur le DATASET'
             % (100 * x['win'], 100 * x['win_plac'], x['ecart_pts'], x['p_win'], x['r'], x['r_plac'], x['wf_n'],
                100 * x['wf_win'], 100 * x['wf_win_plac'], x['wf_r'], Wh['p_white'], Wh['n_combos']))
        T = trades[x['cle']]
        T = T.drop(columns=[c for c in ('i_signal', 'k_entree', 'k_sortie') if c in T])
        ut = W.DECLS[x['decl']][0]
        id_ = ajouter_test(dict(agent='WRS', famille='taux/gestion', recette=rec, marche='MES + MNQ',
                                ut_signal='%dm' % ut, ut_entree='%dm' % ut, echantillon=W.DW.ECHANTILLON,
                                n_variantes_testees=n_var, p_tradeify=x['tf_p'], p_ref_hasard=x['tf_p_ref'],
                                verdict=v, fichier='KAIROS/recherche/taux_gestion/RESULTATS.md', trades=T),
                           prefixe='WRS')
        print(id_, rec[:70])


if __name__ == '__main__':
    main(registre='--registre' in sys.argv)
