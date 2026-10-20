"""56 + seuil de corps du Dashator (58-68) au simulateur Tradeify Select Flex. 20/10/2026."""
import glob, os, sys, re
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'propfirm'))
import simulateur as S

def charge(f):
    x = pd.ExcelFile(f)
    T = x.parse('Trades')
    en = T[T['Type'].str.startswith('Entrer')].set_index('Numéro de trade')
    ex = T[T['Type'].str.startswith('Sortir')].set_index('Numéro de trade')
    q = ex['Taille (qté)'].astype(float)
    tz = lambda s: pd.to_datetime(s).dt.tz_localize('Europe/Paris', ambiguous='NaT', nonexistent='shift_forward')
    t = pd.DataFrame({'entree_t': tz(en['Date et heure']), 'sortie_t': tz(ex['Date et heure']), 'sens': 'long',
                      'pnl_usd': ex['P&L net USD'] / q, 'mae_usd': ex['Excursion adverse USD'] / q,
                      'mfe_usd': ex['Excursion favorable USD'] / q}).dropna().reset_index(drop=True)
    return None, t

D = os.path.expanduser('~/Ephore/Strat-Botting-data/slcourtoupas/58-68')
R = S.charge_regles(); KW = dict(max_jours_eval=250, max_jours_funded=250, max_payouts=5, bloc_jours=5, n_sim=2000, ordre='heuristique')
L = []
for f in sorted(glob.glob(os.path.join(D, '*.xlsx'))):
    P = dict(zip(*[pd.read_excel(f, 'Propriétés')[c].astype(str) for c in ('name', 'value')]))
    m = re.search(r'≥ ([\d,]+) ATR', P.get('Préréglage', '')); seuil = float(m.group(1).replace(',', '.')) if m else 0.0
    if seuil not in (0.0, 0.01, 0.02, 0.03, 0.04):
        continue
    _, t = charge(f)
    for c in (2, 3, 4):
        r = S.monte_carlo(t, R['tradeify_50k_select_flex'], c, **KW)
        L.append(dict(seuil=seuil, micros=c, p_reussite=round(r['p_reussite'], 3), delai_j=r['delai_median_jours'],
                      p_1er_payout=round(r['p_1er_payout'], 3), p_3_payouts=round(r['p_3_payouts'], 3), ve=round(r.get('valeur_esperee_usd') or 0)))
out = pd.DataFrame(L).sort_values(['seuil', 'micros']); out.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resultats_seuils_bas.csv'), index=False)
print(out.to_string(index=False))
