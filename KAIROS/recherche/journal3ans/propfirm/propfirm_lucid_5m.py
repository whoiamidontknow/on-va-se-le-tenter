"""Trades GODLIKE de Strat5669 en 5 min (MNQ1!, 3 ans) au simulateur, comptes Lucid 50k et Tradeify. 23/10/2026.
Sous-ensemble GODLIKE pris dans l'export de Strat5669 (tous les trades du 56) : approximation du 69 en 5 min."""
import glob, os, sys
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'propfirm'))
import simulateur as S

def charge(f, godlike=True):
    x = pd.ExcelFile(f)
    T = x.parse('Trades')
    en = T[T['Type'].str.startswith('Entrer')].set_index('Numéro de trade')
    ex = T[T['Type'].str.startswith('Sortir')].set_index('Numéro de trade')
    q = ex['Taille (qté)'].astype(float)
    tz = lambda s: pd.to_datetime(s).dt.tz_localize('Europe/Paris', ambiguous='NaT', nonexistent='shift_forward')
    t = pd.DataFrame({'entree_t': tz(en['Date et heure']), 'sortie_t': tz(ex['Date et heure']), 'sens': 'long',
                      'pnl_usd': ex['P&L net USD'] / q, 'mae_usd': ex['Excursion adverse USD'] / q,
                      'mfe_usd': ex['Excursion favorable USD'] / q,
                      'gd': en['Signal'].astype(str).str.contains('GODLIKE')}).dropna().reset_index(drop=True)
    return t[t.gd].drop(columns='gd').reset_index(drop=True) if godlike else t.drop(columns='gd')

F = glob.glob(os.path.expanduser('~/Ephore/KAIROS-data/slcourtoupas/5min/*MNQ*.xlsx'))[0]
t = charge(F)
R = S.charge_regles(); KW = dict(max_jours_eval=250, max_jours_funded=250, max_payouts=5, bloc_jours=5, n_sim=2000, ordre='heuristique')
L = []
for v in ('lucid_50k_flex_sans_dll', 'lucid_50k_flex_dll', 'lucid_50k_pro_sans_dll', 'lucid_50k_pro_dll', 'tradeify_50k_select_flex'):
    for c in (2, 3, 4, 6):
        r = S.monte_carlo(t, R[v], c, **KW)
        L.append(dict(compte=v, micros=c, p_reussite=round(r['p_reussite'], 3), delai_j=r['delai_median_jours'],
                      p_1er_payout=round(r['p_1er_payout'], 3), p_3_payouts=round(r['p_3_payouts'], 3),
                      p_5_payouts=round(r.get('p_5_payouts', float('nan')), 3)))
out = pd.DataFrame(L); out.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resultats_lucid_5m.csv'), index=False)
print(out.to_string(index=False))
