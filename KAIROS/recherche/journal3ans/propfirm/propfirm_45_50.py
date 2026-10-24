"""Préréglages 45, 47, 48, 49, 50 (MNQ1! 15 min, exports testeur 3 ans) au simulateur Tradeify. 19/10/2026."""
import glob, os, sys
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'propfirm'))
import simulateur as S
from propfirm_45_46 import charge

B = os.path.expanduser('~/Ephore/KAIROS-data')
FICHIERS = [glob.glob(os.path.join(B, 'slcourtoupas', '*4eb81*.xlsx'))[0]] + \
    sorted(glob.glob(os.path.join(B, 'slcourtoupas', '47-48', '*.xlsx'))) + sorted(glob.glob(os.path.join(B, 'slcourtoupas', '49-50', '*.xlsx')))
VARIANTES = ['tradeify_50k_select_flex', 'tradeify_50k_growth']
KW = dict(max_jours_eval=250, max_jours_funded=250, max_payouts=5, bloc_jours=5, n_sim=2000, ordre='heuristique')
R = S.charge_regles()
lignes = []
for f in FICHIERS:
    sym, pre, t = charge(f)
    for v in VARIANTES:
        for c in (2, 3, 4):
            res = S.monte_carlo(t, R[v], c, **KW)
            lignes.append(dict(prereglage=pre, variante=v, micros=c, p_reussite=res['p_reussite'],
                               delai_j=res['delai_median_jours'], p_1er_payout=res['p_1er_payout'],
                               p_3_payouts=res.get('p_3_payouts'), valeur_esperee=res.get('valeur_esperee_usd')))
            print(lignes[-1], flush=True)
out = pd.DataFrame(lignes)
out.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resultats_45_50.csv'), index=False)
