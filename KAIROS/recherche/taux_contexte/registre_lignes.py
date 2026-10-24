"""Lignes du registre pour le test pré-enregistré H-NUIT (A15R2 et A15R1, nuit) et pour le walk-forward
des contextes. À lancer UNE fois, après test_nuit.py et balayage.py.

    ~/venv-quant/bin/python registre_lignes.py [--source dataset]
"""
import argparse
import json
import os

import pandas as pd

import commun as C  # noqa: F401  (chemins)
import registre as RG

ICI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ICI, 'sorties')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', default=None)
    a = ap.parse_args()
    ech = 'dev_dataset' if a.source == 'dataset' else 'dev_cache'
    tab = pd.read_csv(os.path.join(OUT, 'test_nuit.csv'))
    js = json.load(open(os.path.join(OUT, 'test_nuit.json')))
    for geom, (k, r) in (('A15R2', (1.5, 2)), ('A15R1', (1.5, 1))):
        L = tab[(tab.gestion == geom) & (tab.fenetre == 'nuit') & (tab.serie == 'TOUTES')].iloc[0]
        T = pd.read_csv(os.path.join(OUT, 'trades_nuit_%s_nuit.csv' % geom), parse_dates=['entree_t', 'sortie_t'])
        d = js[geom]
        RG.ajouter_test(dict(
            agent='taux_contexte', famille='Horaire (test pré-enregistré H-NUIT)',
            recette='tous déclencheurs, signal 00:00-08:00 Paris, stop %s ATR objectif %s R' % (k, r),
            marche='MES+MNQ', ut_signal='15', ut_entree='15', echantillon=ech, n_variantes_testees=4,
            p_tradeify=L['p_reussite'], p_ref_hasard=L['ref_p_reussite'],
            verdict='H-NUIT pré-enregistrée : %s. Taux %.1f %% vs placebo nuit %.1f %% (p %.3f) ; R %.3f vs %.3f (p %.3f) ; '
                    'nuit - reste %+.3f R (p %.3f). Idée issue de meta_ml sur les mêmes données : à refaire sur le DATASET'
                    % (js['decision'], 100 * L['pct_gagnants'], 100 * L['pct_gagnants_placebo'], L['p_taux'],
                       L['r_moyen'], L['r_placebo'], L['p_r'], d['delta_r'], d['p_unilateral']),
            trades=T), prefixe='WRR')
    p = os.path.join(OUT, 'trades_wf_oos.csv')
    if os.path.exists(p):
        T = pd.read_csv(p, parse_dates=['entree_t', 'sortie_t'])
        w = json.load(open(os.path.join(OUT, 'walk_forward_resume.json')))
        R = pd.read_csv(os.path.join(OUT, 'balayage_contextes.csv'))
        RG.ajouter_test(dict(
            agent='taux_contexte', famille='Taux de réussite / contexte (walk-forward)',
            recette='contexte choisi sur le passé (taux 60-75 %%, R > 0, meilleur écart au placebo) parmi %d variantes, '
                    'testé sur le bloc suivant (5 plis ancrés)' % len(R),
            marche='MES+MNQ', ut_signal='15', ut_entree='15', echantillon=ech, n_variantes_testees=len(R),
            verdict='hors échantillon : taux %.1f %% vs placebo %.1f %% (p %.3f) ; R %.3f vs %.3f (p %.3f)' % (
                100 * w['pct_gagnants'], 100 * w['pct_placebo'], w['p_taux'], w['r_moyen'], w['r_placebo'], w['p_r']),
            trades=T), prefixe='WRR')


if __name__ == '__main__':
    main()
