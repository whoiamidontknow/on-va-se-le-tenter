"""Lignes WRF du registre (une par recette retenue + la procédure walk-forward globale), depuis resultats/."""
import os, pickle, sys
import pandas as pd
ICI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ICI)
import donnees_wrf as D  # noqa
import registre as RG  # noqa

N_VAR = 1692
OUT = os.path.join(ICI, 'resultats')
F = pd.read_csv(os.path.join(OUT, 'finalistes.csv')).set_index('nom')
C = pd.read_csv(os.path.join(OUT, 'controles_finalistes.csv')).set_index('variante')
TR = pickle.load(open(os.path.join(OUT, 'trades_balayage.pkl'), 'rb'))
OOS = pickle.load(open(os.path.join(OUT, 'wf_oos.pkl'), 'rb'))
ech = 'dev_dataset' if D.SOURCE == 'dataset' else 'dev_cache'

RECETTES = {
    'F3_div_x2.5|ext|R0.75|t8': ('Épuisement : divergence RSI après excès >= 2,5 ATR de l\'EMA50, stop derrière l\'extrême '
                                 '2 bougies + 0,1 ATR (0,4-2,5 ATR sinon sauté), objectif 0,75 R, sortie après 8 bougies'),
    'F3_div_x2.5|a2|R0.5|t0': ('Épuisement : divergence RSI après excès >= 2,5 ATR de l\'EMA50, stop 2 ATR, objectif 0,5 R'),
    'F1_det|a1|R0.5|t0': ('Rejet de zone Detector : mèche dans la zone, corps entier hors zone, stop 1 ATR, objectif 0,5 R'),
}
for v, txt in RECETTES.items():
    f, c = F.loc[v], C.loc[v]
    verdict = ('%.0f %% gagnants vs placebo même géométrie %.0f %% (écart %+.1f pts, p %.3f) ; R %+.3f vs %+.3f ; '
               'MAIS choisie parmi %d variantes : p White studentisé %.2f, walk-forward du setup %s ; '
               'série MES sept. négative. Piste à refaire sur le DATASET, pas une recette prouvée.') % (
        100 * f.pct_gagnants, 100 * f.pct_placebo, f.ecart_pts, f.p_taux, f.r_moyen, f.r_placebo, N_VAR, c.p_white,
        {'F3_div_x2.5|ext|R0.75|t8': '68 %% / +0,23 R sur 53 trades', 'F3_div_x2.5|a2|R0.5|t0': '68 %% / +0,23 R sur 53 trades',
         'F1_det|a1|R0.5|t0': '62 %% / +0,06 R sur 68 trades'}[v].replace('%%', '%'))
    id_ = RG.ajouter_test(dict(agent='taux_retour', famille='Retour à la moyenne', recette=txt + ' [%s]' % v,
                               marche='MES+MNQ', ut_signal='15', ut_entree='15', echantillon=ech,
                               n_variantes_testees=N_VAR, p_tradeify=float(f.p_reussite),
                               p_ref_hasard=float(f.ref_p_reussite), verdict=verdict, trades=TR[v]), prefixe='WRF')
    print(id_, v)
f = F.loc['global']; O = OOS['global'][0]
id_ = RG.ajouter_test(dict(agent='taux_retour', famille='Retour à la moyenne',
                           recette='Procédure walk-forward 5 plis : choix parmi les 1692 variantes (F1 rejet, F2 fausse '
                                   'cassure, F3 épuisement) de la meilleure en R avec 60-75 % de gagnants sur le passé',
                           marche='MES+MNQ', ut_signal='15', ut_entree='15', echantillon=ech, n_variantes_testees=N_VAR,
                           p_tradeify=float(f.p_reussite), p_ref_hasard=float(f.ref_p_reussite),
                           verdict=('ÉCHEC hors échantillon : %.0f %% gagnants (placebo %.0f %%), R %+.3f, n %d ; '
                                    'aucun retour à la moyenne ne passe les 4 critères') % (
                               100 * f.pct_gagnants, 100 * f.pct_placebo, f.r_moyen, f.n), trades=O), prefixe='WRF')
print(id_, 'global')
