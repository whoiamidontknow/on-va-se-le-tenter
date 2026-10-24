"""Étape 3 : pour les (au plus) 3 meilleures recettes du balayage, placebo à 1 000 tirages (trades complets),
simulateur Tradeify Select Flex, et lignes du registre.

Règle de choix (fixée avant de lire le balayage complet) : n >= 60, taux de gagnants 60-75 %, R moyen > 0,
PF > 1, écart positif dans au moins (mois_n - 1) mois ; classement par z du taux contre le placebo ;
contextes distincts (une seule géométrie par contexte).

    ~/venv-quant/bin/python finaliser.py [--source dataset] [--registre] [--variantes "a|g" "b|g"]
"""
import argparse
import json
import multiprocessing as mp
import os
import pickle

import numpy as np
import pandas as pd

import balayage as BL
import commun as C
import moteur as M
import registre as RG

ICI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ICI, 'sorties')
N = 1000


def choisir(R, k=3):
    ok = R[(R.n >= 60) & R.pct_gagnants.between(0.60, 0.75) & (R.r_moyen > 0) & (R.pf > 1)
           & (R.mois_positifs >= R.mois_n - 1)].sort_values('z_taux', ascending=False)
    out, vus = [], set()
    for _, L in ok.iterrows():
        if L['contexte'] in vus:
            continue
        vus.add(L['contexte']); out.append(L['variante'])
        if len(out) == k:
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', default=None)
    ap.add_argument('--registre', action='store_true')
    ap.add_argument('--variantes', nargs='*')
    a = ap.parse_args()
    R = pd.read_csv(os.path.join(OUT, 'balayage_contextes.csv'))
    noms = a.variantes or choisir(R)
    print('recettes :', noms)
    BL.PP = [C.preparer(s) for s in C.charger_series(a.source)]
    V = {v[0]: v for v in BL.variantes()}
    q0 = {v[0]: q for q, v in enumerate(BL.variantes())}
    lignes = []
    for nom in noms:
        _, T, pc, full = BL.tourner((q0[nom] + 7777, V[nom], N, True))
        m = M.metriques(T)
        wr_pl = np.array([(t['pnl_usd'] > 0).mean() for t in full])
        r_pl = np.array([t['r'].mean() for t in full])
        sim = C.simuler(T, full)
        L = dict(variante=nom, contexte=R.set_index('variante').at[nom, 'contexte'], n=m['n'],
                 pct_gagnants=m['pct_gagnants'], pct_placebo=float(wr_pl.mean()),
                 ecart_pts=100 * (m['pct_gagnants'] - wr_pl.mean()),
                 p_taux=float((1 + (wr_pl >= m['pct_gagnants']).sum()) / (1 + N)),
                 r_moyen=m['r_moyen'], r_ic95=m['r_ic95'], r_placebo=float(r_pl.mean()),
                 p_r=float((1 + (r_pl >= m['r_moyen']).sum()) / (1 + N)), pf=m['pf'], net_usd=m['gain_net_usd'],
                 dd_max_usd=m['dd_max_usd'], p_taux_ajustee=R.set_index('variante').at[nom, 'p_taux_ajustee'],
                 **sim)
        lignes.append(L)
        T.to_csv(os.path.join(OUT, 'trades_recette_%s.csv' % nom.replace('|', '_').replace('=', '').replace('+', '_')),
                 index=False)
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in L.items()}, flush=True)
        if a.registre:
            RG.ajouter_test(dict(
                agent='taux_contexte', famille='Taux de réussite / contexte',
                recette='tous déclencheurs (union meta_ml), contexte %s, stop %s ATR objectif %s R, 15:59 Chicago'
                        % (L['contexte'], *C.GEOMETRIES[V[nom][1]]),
                marche='MES+MNQ', ut_signal='15', ut_entree='15',
                echantillon='dev_dataset' if a.source == 'dataset' else 'dev_cache',
                n_variantes_testees=int(R['n_variantes'].iloc[0]) + 4,
                p_tradeify=L.get('p_reussite'), p_ref_hasard=L.get('ref_p_reussite'),
                verdict='taux %.1f %% vs placebo même contexte %.1f %% (+%.1f pts, p %.3f ; p ajustée %d variantes %.2f) ; '
                        'R %.3f vs %.3f (p %.3f) ; en échantillon, %s' % (
                            100 * L['pct_gagnants'], 100 * L['pct_placebo'], L['ecart_pts'], L['p_taux'],
                            int(R['n_variantes'].iloc[0]), L['p_taux_ajustee'], L['r_moyen'], L['r_placebo'], L['p_r'],
                            'ne survit pas à la correction du balayage' if L['p_taux_ajustee'] > 0.05 else 'à confirmer sur le DATASET'),
                trades=T), prefixe='WRR')
    pd.DataFrame(lignes).to_csv(os.path.join(OUT, 'recettes.csv'), index=False)


if __name__ == '__main__':
    main()
