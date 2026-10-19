"""Le 48 avec sortie au temps 12 / 16 bougies / aucune (55-57) au simulateur Tradeify. 19/10/2026."""
import glob, os, sys
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'propfirm'))
import simulateur as S
from propfirm_46_54 import charge

B = os.path.expanduser('~/Ephore/Strat-Botting-data/slcourtoupas')
F = sorted(glob.glob(os.path.join(B, '55-57', '*.xlsx')))
R = S.charge_regles(); KW = dict(max_jours_eval=250, max_jours_funded=250, max_payouts=5, bloc_jours=5, n_sim=2000, ordre='heuristique')
L = []
for f in F:
    pre, t = charge(f)
    for v in ('tradeify_50k_select_flex', 'tradeify_50k_growth'):
        for c in (2, 3, 4):
            r = S.monte_carlo(t, R[v], c, **KW)
            L.append(dict(prereglage=pre, variante=v, micros=c, p_reussite=round(r['p_reussite'], 3), delai_j=r['delai_median_jours'],
                          p_1er_payout=round(r['p_1er_payout'], 3), p_3_payouts=round(r['p_3_payouts'], 3), ve=round(r.get('valeur_esperee_usd') or 0)))
out = pd.DataFrame(L); out.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resultats_55_57.csv'), index=False)
print(out.to_string(index=False))
