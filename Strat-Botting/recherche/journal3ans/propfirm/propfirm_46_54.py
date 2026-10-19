"""Famille 46 (46, 51-54) au simulateur Tradeify, 1 à 3 micros. 19/10/2026."""
import glob, os, sys
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'propfirm'))
import simulateur as S

def charge(f):
    x = pd.ExcelFile(f)
    P = dict(zip(*[x.parse('Propriétés')[c].astype(str) for c in ('name', 'value')]))
    T = x.parse('Trades')
    en = T[T['Type'].str.startswith('Entrer')].set_index('Numéro de trade')
    ex = T[T['Type'].str.startswith('Sortir')].set_index('Numéro de trade')
    q = ex['Taille (qté)'].astype(float)
    tz = lambda s: pd.to_datetime(s).dt.tz_localize('Europe/Paris', ambiguous='NaT', nonexistent='shift_forward')
    t = pd.DataFrame({'entree_t': tz(en['Date et heure']), 'sortie_t': tz(ex['Date et heure']), 'sens': 'long',
                      'pnl_usd': ex['P&L net USD'] / q, 'mae_usd': ex['Excursion adverse USD'] / q,
                      'mfe_usd': ex['Excursion favorable USD'] / q}).dropna().reset_index(drop=True)
    return P.get('Préréglage', '')[:2], t

B = os.path.expanduser('~/Ephore/Strat-Botting-data')
F = glob.glob(os.path.join(glob.escape(B + '/45*46'), '*a9c54*.xlsx')) + sorted(glob.glob(os.path.join(B, 'slcourtoupas', '51-54', '*.xlsx')))
R = S.charge_regles(); KW = dict(max_jours_eval=250, max_jours_funded=250, max_payouts=5, bloc_jours=5, n_sim=2000, ordre='heuristique')
L = []
for f in F:
    pre, t = charge(f)
    for v in ('tradeify_50k_select_flex', 'tradeify_50k_growth'):
        for c in (1, 2, 3):
            r = S.monte_carlo(t, R[v], c, **KW)
            L.append(dict(prereglage=pre, variante=v, micros=c, p_reussite=round(r['p_reussite'], 3), delai_j=r['delai_median_jours'],
                          p_1er_payout=round(r['p_1er_payout'], 3), p_3_payouts=round(r['p_3_payouts'], 3)))
out = pd.DataFrame(L); out.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resultats_46_54.csv'), index=False)
print(out.to_string(index=False))
