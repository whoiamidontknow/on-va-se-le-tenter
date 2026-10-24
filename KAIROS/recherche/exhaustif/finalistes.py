"""EXH — finalistes : Monte-Carlo Tradeify (Select Flex, + Growth) sur le haut du classement, comparé à la
référence « entrées au hasard, même gestion », puis lignes du registre pour les 3 meilleures recettes.

    ~/venv-quant/bin/python KAIROS/recherche/exhaustif/finalistes.py [--k 10] [--registre]
(lancer après balayage.py : lit etat_balayage.pkl)
"""
from __future__ import annotations

import argparse
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import balayage as BA  # noqa: E402
import donnees_exh as D  # noqa: E402
sys.path.insert(0, os.path.join(D.SB, 'propfirm'))
import simulateur as SIM  # noqa: E402
import registre as RG  # noqa: E402
M = D.M

TAILLES = [1, 2, 3, 4, 6, 8, 10, 15]
N_SIM = 1000
N_REF = 20


def choisir(lignes, k):
    L = sorted([l for l in lignes if l['n'] >= BA.N_MIN + 10 and l.get('doublon_de', -1) < 0], key=lambda l: -l['note'])
    out, vus = [], {}
    for l in L:
        cb = BA._cle_base(l)
        if vus.get(cb, 0) >= 1:
            continue
        vus[cb] = vus.get(cb, 0) + 1
        out.append(l)
        if len(out) >= k:
            break
    return out


def mc(trades, regle, tailles=TAILLES):
    tab, best = SIM.optimise_taille(trades, regle, tailles=tailles, critere='valeur_esperee', n_sim=N_SIM,
                                    ordre='prudent')
    pmax = tab.loc[tab['p_reussite'].idxmax()] if len(tab) else None
    return best, pmax


def reference(U, v, contrats, regle):
    tirages = [[] for _ in range(N_REF)]
    rmoy = [[] for _ in range(N_REF)]
    for j in U.jeux_ut(v['ut']):
        s = U.signaux(j, v['ev'], v['mode'], v['sens'], v['filtres'])
        if s is None or not (s[0].any() or s[1].any()):
            continue
        R, trs = M.reference_hasard(j['df'], N_REF, U.gestion(j, v['sortie']), graine=7, long=s[0], short=s[1],
                                    garder_trades=True)
        for k, T in enumerate(trs):
            if len(T):
                tirages[k].append(T)
    tirages = [pd.concat(t, ignore_index=True) for t in tirages if t]
    tirages = [t for t in tirages if len(t)]
    r_ref = np.array([t['r'].mean() for t in tirages])
    ref = SIM.analyse_reference(tirages, regle, contrats, n_sim=N_SIM * 2, ordre='prudent')
    return ref, r_ref


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--k', type=int, default=10)
    ap.add_argument('--registre', action='store_true')
    a = ap.parse_args()
    t0 = time.time()
    with open(os.path.join(ICI, 'etat_balayage.pkl'), 'rb') as fh:
        etat = pickle.load(fh)
    lignes = etat['lignes']
    U = BA.Univers(D.charger_jeux())
    regles = SIM.charge_regles()
    flex, growth = regles['tradeify_50k_select_flex'], regles['tradeify_50k_growth']
    res = []
    for l in choisir(lignes, a.k):
        v = l['_v']
        T = U.trades(v)
        best, pmax = mc(T, flex)
        bg, _ = mc(T, growth)
        c = int(best.get('contrats', 1))
        ref, r_ref = reference(U, v, c, flex)
        p_r = float((1 + (r_ref >= T['r'].mean()).sum()) / (1 + len(r_ref)))
        res.append(dict(id=l['id'], recette=l['recette'], ut=v['ut'], n=len(T), r_moyen=T['r'].mean(),
                        ic95_bas=l['ic95_bas'], ic95_haut=l['ic95_haut'], pf=l['pf'], note=l['note'],
                        frac_blocs_pos=l['frac_blocs_pos'], r_MES=l['r_MES'], r_NQ=l['r_NQ'],
                        contrats=c, p_flex=best.get('p_reussite'), p1_payout=best.get('p_1er_payout'),
                        ve_usd=best.get('valeur_esperee_usd'),
                        p_flex_max=float(pmax['p_reussite']) if pmax is not None else np.nan,
                        contrats_p_max=int(pmax['contrats']) if pmax is not None else 0,
                        p_growth=bg.get('p_reussite'), p_ref_flex=ref.get('p_reussite'),
                        ve_ref_usd=ref.get('valeur_esperee_usd'), r_ref_moyen=float(np.mean(r_ref)) if len(r_ref) else np.nan,
                        p_hasard_r=p_r))
        print('%-90s n=%d R=%+.3f P(flex)=%.3f (ref %.3f) taille %d  p_hasard=%.2f' % (
            l['recette'][:90], len(T), T['r'].mean(), res[-1]['p_flex'], res[-1]['p_ref_flex'], c, p_r), flush=True)
        pd.DataFrame(res).to_csv(os.path.join(ICI, 'finalistes.csv'), index=False, float_format='%.4f')
    F = pd.DataFrame(res)
    if a.registre and len(F):
        n_var = len(lignes)
        F = F.sort_values('note', ascending=False)
        for _, f in F.head(3).iterrows():
            v = lignes[int(f['id'])]['_v']
            T = U.trades(v)
            T = T.drop(columns=['jeu']).rename(columns={'marche': 'marche_trade'})
            verdict = ('non probant (2 mois, n=%d < 200) ; P(flex) %.2f vs hasard %.2f ; p_hasard R %.2f ; '
                       'IC95 R [%+.2f ; %+.2f] — à relancer sur le DATASET' % (
                           f['n'], f['p_flex'], f['p_ref_flex'], f['p_hasard_r'], f['ic95_bas'], f['ic95_haut']))
            RG.ajouter_test(dict(agent='EXH', famille='exhaustif/' + v['ev'], recette=f['recette'],
                                 marche='MES+MNQ (micros)', ut_signal=str(v['ut']), ut_entree=str(v['ut']),
                                 echantillon='dev_cache', n_variantes_testees=n_var, p_tradeify=f['p_flex'],
                                 p_ref_hasard=f['p_ref_flex'], verdict=verdict, trades=T), prefixe='EXH')
    print('finalistes : %.0f s' % (time.time() - t0))


if __name__ == '__main__':
    main()
